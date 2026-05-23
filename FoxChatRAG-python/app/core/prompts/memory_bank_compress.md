将以下记忆库压缩到 {target_size} 条核心事件。
要求：
- 合并相似事件
- 保留最重要的关键事件
- 保持 time、type、actor、content、keywords 字段
- actor 字段必须保留，明确主体归属
- keywords 字段合并相似关键词
- 输出 JSON 数组格式
- 只输出 JSON 数组，不要其他文字

当前记忆库：
{memory_bank_json}

压缩后的记忆库：