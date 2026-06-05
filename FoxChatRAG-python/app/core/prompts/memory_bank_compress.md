将以下记忆库压缩到 {target_size} 条核心事件。

## 必须保留的高重要性事件（不得删除或合并，原样保留）
以下事件的 importance >= 0.7，属于关键事件（如用户红线、承诺约定、身份信息等），必须在压缩结果中原样保留，不得合并、不得省略：
{pinned_events_json}

## 压缩要求
- 合并相似事件（但不能合并上述高重要性事件）
- 保留最重要的关键事件
- 保持 time、type、actor、content、keywords、importance 字段
- actor 字段必须保留，明确主体归属
- keywords 字段合并相似关键词
- importance 字段必须保留原值，不能修改
- 输出 JSON 数组格式
- 只输出 JSON 数组，不要其他文字

## 当前记忆库
{memory_bank_json}

压缩后的记忆库：