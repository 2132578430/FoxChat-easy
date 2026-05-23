# 记忆库总结与长期记忆管理设计

## 目标

优化 FoxChatRAG 的总结记忆流程，将对话中的关键事件提取到 `memory_bank`（记忆库），实现长期记忆管理，并防止记忆库无限增长导致模型性能下降。

## 背景

### 现状
- `memory_bank` 已存储在 Redis 中，包含初始化时提取的事件记忆
- 当前总结任务 `_async_summary_msg` 仅将对话摘要存入 Chroma
- 需要扩展总结任务，增加事件提取和记忆库管理功能

### 痛点
- 长期对话积累会导致 `memory_bank` 无限增长
- 过长的上下文会导致 LLM 性能下降（"降智"现象）
- 需要主动管理记忆库容量

## 设计决策

### 1. 事件提取策略
- **策略**：每次总结时增量提取新事件
- **粒度**：从最近 20 条对话中提取关键事件和状态变化
- **格式**：直接输出 JSON 数组，格式：`[{"time": "YYYY-MM-DD", "type": "event|state", "content": "..."}]`
- **时间字段**：使用当前时间自动填充

### 2. 追加策略
- **方式**：追加而非覆盖
- **触发时机**：每次总结任务执行时
- **位置**：追加到 Redis 的 `memory_bank` key

### 3. 压缩策略
- **触发条件**：`memory_bank` 长度 >= 50 条
- **压缩目标**：精简到 20-30 条
- **方式**：使用 LLM 合并相似事件，提炼核心记忆
- **触发时机**：追加新事件后检查长度
- **位置**：在总结任务内部完成，无需独立定时任务

### 4. 实现方案
- **选择**：方案一（最小改动）
- **思路**：修改现有 `_async_summary_msg`，增加事件提取和压缩逻辑
- **优点**：代码集中，改动最小，快速验证

## 实现计划

### 修改点 1：新增 Prompt 模板
在 `prompt_template.py` 中新增：

```python
MEMORY_EVENT_EXTRACTOR_PROMPT = """
从对话历史中提取关键事件和状态变化。

要求：
- 只提取重要的、新的话题或事件
- 忽略日常闲聊和问候
- 每条事件包含：time（当前日期）、type（event或state）、content（事件描述）
- 输出 JSON 数组格式
- 只输出 JSON，不要其他文字

对话历史：
{chat_history}

输出：
"""
```

### 修改点 2：修改 `_async_summary_msg` 函数
修改 `chat_msg_service.py` 的 `_async_summary_msg` 函数：

```python
async def _async_summary_msg(recent_msg_key: str, recent_msg_size: int, user_id: str, llm_id: str) -> None:
    # 原有逻辑：检查是否需要总结
    if recent_msg_size < 30:
        return

    # 获取待总结的消息
    pip = redis_client.pipeline()
    pip.lrange(recent_msg_key, 9, -1)
    pip.ltrim(recent_msg_key, 0, 9)
    result = pip.execute()

    recent_msg_list = result[0]
    recent_msg_list.reverse()

    # 1. 原有逻辑：总结对话（存入 Chroma）
    summary_chain = await _build_summary_chain()
    summary_msg = await summary_chain.ainvoke({"chat_history_msg": recent_msg_list})
    documents = await loader_util.load_file(summary_msg, FileTypeConstant.STR)
    source_id = user_id + llm_id + summary_msg
    await chroma_util.upload(ChromaTypeConstant.CHAT, documents, source_id, user_id=user_id, llm_id=llm_id)

    # 2. 新增：从对话中提取事件
    events = await _extract_memory_events(recent_msg_list)

    # 3. 新增：追加到 memory_bank
    if events:
        await _append_to_memory_bank(events, user_id, llm_id)

    # 4. 新增：检查并压缩（如果需要）
    await _compress_memory_bank_if_needed(user_id, llm_id)
```

### 修改点 3：新增辅助函数

#### 3.1 `_extract_memory_events`
```python
async def _extract_memory_events(recent_msg_list: List[str]) -> List[dict]:
    """从对话中提取关键事件"""
    chain = await _build_event_extractor_chain()
    result = await chain.ainvoke({"chat_history": recent_msg_list})
    # 解析 JSON 字符串为 Python 对象
    return json.loads(result)
```

#### 3.2 `_build_event_extractor_chain`
```python
async def _build_event_extractor_chain():
    """构建事件提取 chain"""
    template = ChatPromptTemplate([
        ("system", PromptTemplate.MEMORY_EVENT_EXTRACTOR_PROMPT),
        ("human", "{chat_history}")
    ])
    str_parser = StrOutputParser()
    llm = await llm_model.get_llm_model("qwen4b_model")
    return template | llm | str_parser
```

#### 3.3 `_append_to_memory_bank`
```python
async def _append_to_memory_bank(events: List[dict], user_id: str, llm_id: str) -> None:
    """追加事件到 memory_bank"""
    memory_bank_key = build_memory_key(LLMChatConstant.MEMORY_BANK, user_id, llm_id)

    # 获取现有 memory_bank
    existing = redis_client.get(memory_bank_key)
    if existing:
        memory_bank = json.loads(existing)
    else:
        memory_bank = []

    # 追加新事件
    memory_bank.extend(events)

    # 保存回 Redis
    redis_client.set(memory_bank_key, json.dumps(memory_bank, ensure_ascii=False))
```

#### 3.4 `_compress_memory_bank_if_needed`
```python
async def _compress_memory_bank_if_needed(user_id: str, llm_id: str) -> None:
    """如果 memory_bank 过长，执行压缩"""
    memory_bank_key = build_memory_key(LLMChatConstant.MEMORY_BANK, user_id, llm_id)

    # 获取当前 memory_bank
    existing = redis_client.get(memory_bank_key)
    if not existing:
        return

    memory_bank = json.loads(existing)

    # 检查是否需要压缩
    if len(memory_bank) < 50:
        return

    # 构建压缩 prompt
    compress_prompt = f"""将以下记忆库压缩到 20-30 条核心事件。

要求：
- 合并相似事件
- 保留最重要的关键事件
- 保持 time、type、content 字段
- 输出 JSON 数组

当前记忆库：
{json.dumps(memory_bank, ensure_ascii=False, indent=2)}

压缩后的记忆库：
"""

    # 调用 LLM 压缩
    llm = await llm_model.get_llm_model("qwen4b_model")
    compressed = await llm.ainvoke(compress_prompt)

    # 解析并保存
    compressed_memory_bank = json.loads(compressed)
    redis_client.set(memory_bank_key, json.dumps(compressed_memory_bank, ensure_ascii=False))
```

## 数据流图

```
用户发送消息
    ↓
chat_msg 函数处理
    ↓
background_tasks.add_task(_async_summary_msg, ...)
    ↓
┌─────────────────────────────────┐
│  _async_summary_msg 执行        │
│                                 │
│  1. 获取最近 20 条对话          │
│  2. 总结存入 Chroma（原有）      │
│  3. 提取事件                    │──→ 新增
│  4. 追加到 memory_bank         │──→ 新增
│  5. 检查并压缩（如需要）        │──→ 新增
└─────────────────────────────────┘
    ↓
任务完成
```

## 配置常量

建议添加配置到 `LLMChatConstant.py`：

```python
class LLMChatConstant(StrEnum):
    # ... 现有常量 ...

    # 新增配置
    MEMORY_BANK_SUMMARY_THRESHOLD = 30  # 触发总结的对话数量
    MEMORY_BANK_MAX_SIZE = 50           # 触发压缩的最大条数
    MEMORY_BANK_COMPRESS_TARGET = 25     # 压缩后的目标条数
```

## 测试计划

1. **单元测试**
   - 测试 `_extract_memory_events` 解析 JSON 格式
   - 测试 `_append_to_memory_bank` 追加逻辑
   - 测试 `_compress_memory_bank_if_needed` 触发条件

2. **集成测试**
   - 模拟多次对话，验证 memory_bank 增长
   - 验证超过 50 条时触发压缩
   - 验证压缩后 memory_bank 长度在 20-30 条

3. **手动测试**
   - 实际对话测试，检查 Redis 中的 memory_bank 数据

## 风险与注意事项

1. **JSON 解析失败**：LLM 输出的 JSON 可能格式不正确
   - 应对：添加 try-except 捕获解析错误，记录日志
   - 应对：提示词中强调"只输出 JSON，不要其他文字"

2. **重复事件**：多次总结可能提取相似事件
   - 应对：在压缩阶段合并相似事件
   - 应对：可在追加时检查内容相似度（可选优化）

3. **压缩丢失信息**：压缩过程可能丢失重要细节
   - 应对：压缩 prompt 要求"保留最重要的关键事件"
   - 应对：设置目标为 20-30 条，保留足够信息

4. **Redis 数据一致性**：并发操作可能导致数据问题
   - 应对：使用 Redis pipeline 保证原子性
   - 应对：追加操作使用 GET + SET（非覆盖场景）

## 后续优化方向

1. **分层存储**：超过 100 条后移动到向量库
2. **智能去重**：追加时检测并跳过重复事件
3. **权重系统**：为记忆添加重要性权重，优先保留重要记忆
4. **时间衰减**：定期评估记忆相关性，删除过时信息

## 文件改动清单

1. `app/core/prompts/prompt_template.py`
   - 新增 `MEMORY_EVENT_EXTRACTOR_PROMPT` 常量

2. `app/common/constant/LLMChatConstant.py`
   - 新增配置常量（可选）

3. `app/service/chat_msg_service.py`
   - 修改 `_async_summary_msg` 函数
   - 新增 `_build_event_extractor_chain` 函数
   - 新增 `_extract_memory_events` 函数
   - 新增 `_append_to_memory_bank` 函数
   - 新增 `_compress_memory_bank_if_needed` 函数

---

**作者**：Claude Code  
**日期**：2026-04-10  
**版本**：1.0
