# 记忆架构 V1 验证执行框架

> 生成时间: 2026-05-03
> 状态: 框架就绪，待执行

---

## 框架资产

### 已准备资产

| 资产 | 路径 | 状态 |
|------|------|------|
| 验证场景集 | `docs/validation_scenarios.md` | 就绪 |
| 验证执行脚本 | `scripts/memory_validation_runner.py` | 就绪 |
| Token评估脚本 | `scripts/token_baseline_evaluator.py` | 可复用 |
| 状态生命周期测试 | `scripts/test_current_state_lifecycle.py` | 可复用 |
| Time node激活测试 | `scripts/test_time_node_activation.py` | 可复用 |
| 阶段3路由测试 | `scripts/test_phase3_routing.py` | 可复用 |

### 执行步骤

1. **启动验证执行**
   ```bash
   cd FoxChatRAG-python
   python scripts/memory_validation_runner.py --all
   ```

2. **审查执行报告**
   - 查看 `docs/validation_execution_report.md`
   - 识别失败场景和失败层

3. **按优先级修复**
   - A2 边界失效 → 检查 `_enforce_conflict_priority()`
   - Time node 提前激活 → 检查实时注入方案
   - 历史检索误射 → 检查 V2 混合检索

4. **复测相邻场景**
   - 修复后重新执行受影响场景
   - 记录回归情况

5. **循环直到收敛**
   - 持续修复-验证循环
   - 无法解决的失败标记为已知限制

---

## 失败层分类与修复指引

### A2 层失败

**症状:** 边界被违反，模型使用禁忌称呼或行为

**检查点:**
1. `_parse_a2_boundaries()` 是否正确提取边界
2. `_enforce_conflict_priority()` 是否正确检测冲突
3. Payload builder 是否正确注入 A2 块

**修复路径:**
- 增强 boundary_markers 关键词列表
- 提高 B/C 层冲突抑制阈值
- 确保空块抑制不误删有效边界

### B 层失败

**症状:** 状态抖动、重复注入、默认值污染

**检查点:**
1. `_parse_current_state()` 空块返回值
2. B 层内部去重（current_focus vs unfinished_items）
3. 状态延续逻辑

**修复路径:**
- 确认 `_build_default_state_summary()` 返回空字符串
- 调整去重阈值
- 增加状态稳定性检查

### T 层失败

**症状:** Time node 提前激活、双入口不一致

**检查点:**
1. `runtime_state_extractor.py` 使用实时注入方案
2. `memory_summary_service.py` 使用相同方案
3. 到期检查逻辑

**修复路径:**
- 确认两路径统一使用 `write_unfinished_item_from_time_expression()`
- 检查 `check_due_time_nodes()` 到期判定

### C 层失败

**症状:** 检索未触发、召回质量差、与D层重复

**检查点:**
1. `should_trigger_history_retrieval()` 触发条件
2. V2 混合检索执行路径
3. `deduplicate_with_recent_window()` 阈值

**修复路径:**
- 增强触发词列表
- 调整 BM25/向量权重
- 调整去重阈值

### D 层失败

**症状:** 最近窗口重复注入

**检查点:**
1. `_build_history_message()` 转换逻辑
2. 与 C 层去重

**修复路径:**
- 已在 C 层去重逻辑处理

### Prompt Layout 失败

**症状:** 跨层重复、空块处理不一致

**检查点:**
1. `_suppress_duplicates_across_layers()` 执行
2. `_is_empty_block()` 判断
3. Payload builder 调用

**修复路径:**
- 调整 overlap_threshold
- 增加空块判断规则
- 确保 payload builder 正确调用

---

## 验证收敛标准

- **通过率 >= 80%**: 核心场景通过
- **无高严重度失败**: A2-1、T-1、T-3、P-1、P-3 已解决
- **已知限制已记录**: 无法解决的失败已归档

---

## 回退策略

参见 `docs/rollback_strategy.md`:
- Git 备份已创建
- 阶段性提交可回退
- 问题记录在 `docs/memory_validation_issues.md`