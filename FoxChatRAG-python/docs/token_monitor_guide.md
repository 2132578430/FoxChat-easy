# Token 监控工具使用指南

## 1. 实时监控（集成到代码）

在 `chat_msg_service.py` 中添加监控：

```python
from app.util.token_monitor import token_monitor

# 动态调整 memory_bank 条数（测试不同配置）
token_monitor.set_memory_bank_limit(10)  # 改为注入10条

# 在 _invoke_llm 调用后查看报告
print(token_monitor.generate_report())
```

## 2. 批量对比测试（推荐）

运行测试脚本，对比不同 memory_bank 条数的效果：

```bash
# 使用你的真实用户ID和模型ID
python scripts/test_memory_bank_limits.py \
  --user-id 2021923959349370882 \
  --llm-id 2051212504046882817

# 自定义测试范围（测试 0, 2, 4, 6, 8, 10 条）
python scripts/test_memory_bank_limits.py \
  --user-id <你的ID> \
  --llm-id <模型ID> \
  --limits 0 2 4 6 8 10

# 指定报告输出路径
python scripts/test_memory_bank_limits.py \
  --user-id <ID> \
  --llm-id <ID> \
  --output docs/my_comparison_report.md
```

## 3. 测试输出示例

测试脚本会输出对比表格：

| MB条数限制 | 平均Prompt | 平均Completion | MB字符占比 |
|-----------|-----------|---------------|-----------|
| 0 | 450.3 | 180.2 | 0.0% |
| 3 | 520.7 | 185.5 | 5.2% |
| 5 | 590.1 | 190.8 | 8.7% |
| 7 | 660.5 | 195.2 | 12.3% |
| 10 | 730.9 | 200.1 | 15.8% |

**推荐配置**：
- Token增长控制在 20% 以内
- 同时提供足够的上下文
- 通常推荐 **3-5 条**

## 4. 关键指标说明

- **Prompt Tokens**: 输入提示词消耗的 token 数
- **Completion Tokens**: 模型回复消耗的 token 数
- **MB字符占比**: Memory Bank 占总提示词的比例
- **Token增长率**: 相对于 0 条基线的增长百分比

## 5. 与 Token 报告对比

现有 Token 报告（[docs/token_baseline_report.md](../docs/token_baseline_report.md)）显示：
- Memory Bank 条数始终为 0（因为测试只有 5 轮，summary 未触发）
- History 占比过高（60.7%）

现在已实现：
- ✅ Memory Bank 按需检索（向量检索优先，最多 4 条）
- ✅ Memory Bank 保底注入（最多 5 条）
- ✅ 可动态调整测试不同配置

## 6. 下一步测试建议

1. **真实场景测试**：使用你的真实用户 ID，积累更多轮对话
2. **长对话测试**：触发 summary 后，memory_bank 有数据时再测试
3. **对比配置**：测试 0/3/5/7/10 条，找到最优配置
4. **成本分析**：根据 token 消耗计算 API 调用成本