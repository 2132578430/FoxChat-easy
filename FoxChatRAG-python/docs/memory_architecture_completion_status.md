# 记忆架构 V1 收尾状态记录

> 生成时间: 2026-05-03
> 依据: `docs/memory_architecture_implementation_plan.md`

---

## 阶段完成状态总览

| 阶段 | 定义 | 代码状态 | 未完成项 |
|------|------|----------|----------|
| 阶段 0 | 建立基线与评估标准 | **部分完成** | 缺少完整样本集、错误类型标注口径未落地 |
| 阶段 1 | 定义对象契约和信息路由 | **已完成** | `docs/layer_definition.md`、`docs/memory_routing.md` 已存在 |
| 阶段 2 | 扩展 emotion_state 为 current_state 容器 | **已完成** | `current_state.py`、`state_manager.py`、time node 运行时均已落地 |
| 阶段 3 | 改造提取流程 | **已完成** | 四路候选分流已接入 `memory_summary_service.py` |
| 阶段 4 | History Retrieval V1 | **已完成** | `history_event_retrieval_service.py` 已接入主流程 |
| 阶段 5 | History Retrieval V2 | **未完成** | 混合检索、rerank、collection 拆分均未落地 |
| 阶段 6 | Prompt Layout V2 | **部分完成** | 模板已改为 4 块结构，但空块抑制、冲突优先级、跨层去重未完整收敛 |
| 阶段 7 | 验证与回滚准备 | **未完成** | 无样本集、无验收记录、无回退说明文档 |

---

## 阶段 5 未完成项清单

### 5.1 混合检索未实现

**现状:** 当前检索仍以 `memory_bank` + Chroma summary fallback 为主，`retrieve_history_events_from_memory_bank()` 仅做规则过滤和排序。

**目标:** 引入 BM25 + 向量检索混合召回，保持 `historical_context` 输出契约稳定。

**关键代码:**
- `FoxChatRAG-python/app/service/chat/history_event_retrieval_service.py`
- `FoxChatRAG-python/app/util/chroma_util.py`

### 5.2 Rerank 未实现

**现状:** 无 rerank 层，仅按 `importance` + `freshness` 排序。

**目标:** 在混合召回后引入轻量 rerank，提升相关性判断质量。

### 5.3 类型化衰减 / activity_score 未完整接入

**现状:** `activity_score` 字段已定义但未在检索排序中实际使用。

**目标:** 让老事件的权重随时间衰减，防止过旧事件持续占据检索结果。

### 5.4 Summary 与 Event 检索隔离未完成

**现状:** 两者共用 Chroma CHAT collection，可能互相污染。

**目标:** 明确是否拆分 collection 或用 metadata 强隔离。

---

## 阶段 6 未完成项清单

### 6.1 统一 Payload Builder 未引入

**现状:** Prompt 组装逻辑分散在 `_parse_*` 函数和 `_invoke_llm()` 中，空块处理、默认值注入、去重逻辑散落多处。

**目标:** 引入统一 payload builder 或 assembly entry，在 LLM 调用前一次性决定块注入。

### 6.2 空块抑制不完整

**现状:** `_parse_current_state()` 在空状态时返回默认值 `平静/中性/闲聊`，与设计目标"空块省略"不一致。

**目标:** 实现 stable empty-block suppression，让 A2、C、B 在无有效内容时完全省略。

### 6.3 跨层去重未实现

**现状:** 同一信息可能在 A2（硬边界）、B（当前状态）、C（历史事件）、D（最近窗口）中重复出现，无统一去重机制。

**目标:** 在 payload builder 中实现跨层去重，优先保留高层信息。

### 6.4 冲突优先级规则未强制执行

**现状:** 无显式机制保证 `A2 > B > C > D` 的冲突优先级。

**目标:** 在 payload builder 中 enforce conflict priority rules。

---

## 阶段 7 未完成项清单

### 7.1 新旧架构切换开关未实现

**裁剪决策:** 个人项目不强制要求生产级开关，用 git 备份 + 回退步骤替代。

**待办:** 编写回退操作说明文档。

### 7.2 样本集未建立

**现状:** 无正式验证样本集，验证依赖临时人工测试。

**目标:** 建立覆盖关键场景的样本集，包括：
- 普通闲聊
- 连续安慰/陪伴
- 有承诺的对话
- 跨日跟进
- 冲突后缓和
- 用户问"你记得吗"
- 提及禁忌话题

### 7.3 验收记录未建立

**现状:** 无正式验收记录格式和通过门槛。

**目标:** 每个场景记录：输入片段、注入块、模型输出、人工判断。

### 7.4 回滚准备未文档化

**目标:** 明确 git 回退步骤、备份策略和问题归因口径。

---

## 已知验证问题清单

| 问题层 | 具体问题 | 严重程度 |
|--------|----------|----------|
| A2 | 硬边界约束力不足，有时仍被历史事件冲掉 | 高 |
| B | 默认状态值注入可能过度污染输出 | 中 |
| B | `current_focus` 与 `unfinished_items` 重复表达同一事项 | 中 |
| T | time node 提前激活导致模型过度关注未完成事件 | 高 |
| T | 总结流程中直接写 `unfinished_items` 与 pending→active 路径存在双入口 | 中 |
| C | 历史检索触发条件偏粗糙（`split()` 对中文效果弱） | 中 |
| C | 历史检索结果可能与最近窗口重复 | 中 |
| D | `{user_message}` 曾重复注入（已修复） | 低 |
| Prompt | 同一信息跨层重复注入 | 高 |
| Token | 动态注入部分可能不可解释增长 | 中 |

---

## 下一步行动

1. 先统一 Prompt/payload 契约（阶段 6.1 ~ 6.4）
2. 再升级检索后端（阶段 5.1 ~ 5.4）
3. 再按问题分类回流修复
4. 建立验证样本和验收记录
5. 最终判定是否完成记忆架构 V1