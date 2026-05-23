# History Retrieval V2 升级审计

> 生成时间: 2026-05-03

---

## 当前检索链路分析

### 数据源

| 数据源 | 存储位置 | 检索方式 | 问题 |
|--------|----------|----------|------|
| memory_bank | Redis | 规则过滤 + importance/freshness 排序 | 无向量语义检索 |
| Chroma 事件 | CHAT collection + `is_event: True` metadata | 向量检索 + metadata 过滤 | 与 summary 共用 collection |
| Chroma summary | CHAT collection (无 is_event 标记) | 向量检索 | 与事件共用 collection |

### 当前检索流程

```text
_user_input
    ↓
should_trigger_history_retrieval() → True?
    ↓ Yes
retrieve_history_events_from_memory_bank()
    → Redis memory_bank → 规则过滤 → 排序 → 去重 → 返回事件列表
    ↓ 如果返回空
chroma_util.search(CHAT, query, {user_id, llm_id})  # 无 is_event 过滤
    → 返回 summary 文档（可能包含事件）
    ↓ 如果返回空
memory_bank_summary 降级保底
```

---

## 问题识别

### 问题 1: 事件与 summary 共用 CHAT collection

**现象:** 
- `upload_history_event()` 写入时标记 `is_event: True`
- `search_history_events()` 读取时过滤 `is_event: True`
- 但 fallback 时调用 `chroma_util.search()` 无此过滤，导致事件和 summary 混在一起返回

**风险:**
- 当 memory_bank 无结果时，fallback 可能返回事件而非真正的 summary
- 或 summary 污染事件检索结果

### 问题 2: 无混合检索（BM25 + 向量）

**现状:** 只有向量检索，无 BM25 关键词召回。

**风险:**
- 纯语义检索可能漏掉精确关键词匹配的事件
- 对"用户名/地点/具体事件名"等硬匹配不够敏感

### 问题 3: 无 rerank

**现状:** 排序仅靠 importance + freshness 或向量相似度。

**风险:**
- 相似度高但重要性低的事件可能排在前面
- 无二次相关性判断

### 问题 4: activity_score 未使用

**现状:** `activity_score` 字段已定义但未参与排序。

**风险:**
- 过旧事件持续占据检索结果

---

## 升级方案

### 3.1: 检索隔离（metadata 强隔离）

**方案:** 
- 保持 CHAT collection 共用，但严格用 `is_event` metadata 区分
- fallback 时也应过滤 `is_event: False` 以排除事件

**实现:**
```python
# fallback 时只查 summary
documents = await search(
    ChromaTypeConstant.CHAT,
    msg_content,
    {"user_id": user_id, "llm_id": llm_id, "is_event": False},  # 新增过滤
)
```

### 3.2: 混合检索（BM25 + 向量）

**方案:**
- 对 memory_bank 事件用关键词 + 向量混合召回
- 用 `BM25Retriever` 从 memory_bank 建关键词索引
- 合并两路结果后 rerank

**实现路径:**
- 从 Redis memory_bank 建临时 BM25 索引
- 或预建 memory_bank 的文本索引

### 3.3: Rerank

**方案:**
- 使用 FlashrankRerank 或类似轻量 rerank
- 在混合召回后做二次排序

**现有资源:**
- `chroma_util.py` 已导入 `FlashrankRerank`

### 3.4: 类型化衰减

**方案:**
- 将 `activity_score` 纳入排序权重
- 对超过 MAX_AGE_DAYS 的事件应用衰减因子

---

## 隐含约束

- 保持 `historical_context` 输出契约稳定
- 不改变 `format_history_events()` 输出格式
- 不新增 Prompt 占位符

---

## 实施顺序

1. 先加强 metadata 过滤隔离（3.4）
2. 再引入 activity_score 排序权重（3.3）
3. 再引入混合召回框架（3.2）
4. 最后引入 rerank（3.2）