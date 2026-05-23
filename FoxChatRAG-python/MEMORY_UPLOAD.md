# 记忆上传与多层记忆架构设计

## 一、问题背景

### 1.1 当前问题

**问题1：初始记忆直接存入，上下文压力过大**
- 当前实现：用户上传的初始经历词原封不动存入Redis
- 问题：对于上下文较小的模型，记忆过长会快速耗尽上下文，导致几轮对话后模型"降智"

**问题2：提示词设计不完善**
- 记忆和提示词没有形成体系
- 模型难以从大量原始文本中提取关键信息

**问题3：记忆总结会丢失信息**
- 原方案：每次总结后覆盖旧内容
- 问题：早期重要记忆会被挤出，导致长期对话后丢失关键信息

### 1.2 解决思路

从三个维度入手：
1. **优化记忆**：对初始记忆进行LLM提炼，分层存储
2. **优化加载**：使用RAG检索替代全量加载，避免上下文过长
3. **追加存储**：总结后追加而非覆盖，保证记忆不丢失

---

## 二、多层记忆架构设计

### 2.1 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户输入                                   │
│                   (原始经历词/对话历史)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 1: 初始记忆处理                          │
│  ┌──────────────┐    ┌──────────────┐                           │
│  │  角色核心锚点   │    │   用户画像    │    ┌──────────────┐    │
│  │  (100-200字) │    │  (300-500字) │    │  初始记忆库   │    │
│  └──────────────┘    └──────────────┘    │  (追加存储)    │    │
│                                         └──────────────┘    │
│  ┌──────────────┐                                           │
│  │   角色卡      │                                           │
│  │ (性格/语气等) │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 2: 对话时记忆融合                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  层级1: 角色核心锚点 (始终加载，最高优先级)                  │  │
│  │  层级2: 用户画像 (始终加载，高优先级)                        │  │
│  │  层级3: 角色卡 (始终加载，行为指导)                          │  │
│  │  层级4: 记忆库 (RAG检索，按需加载)                          │  │
│  │  层级5: 最近聊天记录 (最近N轮)                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计理念

**存储分离 + RAG召回**

| 维度 | 原方案 | 新方案 |
|------|--------|--------|
| 存储方式 | 覆盖 | **追加** |
| 加载方式 | 全量 | **RAG检索** |
| 记忆丢失 | 会丢失 | **不丢失** |
| 上下文 | 全量加载可能过长 | 只加载相关记忆 |

### 2.3 各层记忆详解

#### 层级1：角色核心锚点 (Role Core Anchor)

**用途**：模型的首要行为准则，不可违背

**内容**：
- 角色身份（名字、年龄、与用户关系）
- 核心性格底色
- 标志性说话方式
- 绝对边界（绝对不会说的话/做的事）

**长度**：100-200字

**更新方式**：几乎不变，只追加不覆盖

---

#### 层级2：用户画像 (User Profile)

**用途**：描述用户的特点，帮助模型更好地个性化回应

**内容**（对应 Problem.md 中的7个维度）：
1. 核心身份与关系锚点
2. 核心性格与灵魂特质
3. 语言与说话风格
4. 互动模式与回应习惯
5. 价值观与处事原则
6. 长期兴趣与固定偏好
7. 绝对边界与雷区

**长度**：300-500字

**更新方式**：追加更新，保留历史版本或合并

---

#### 层级3：角色卡 (Character Card)

**设计参考**：基于 SillyTavern Character Card V2 规范，采用 **"Show, don't tell"** 原则

**核心原则**：
- 用具体行为和示例展现角色，不要只列规则
- Token 优化：总长度控制在 600 tokens 以内
- 分离"永久字段"和"扩展字段"

**永久字段（始终加载）**：
| 字段 | 长度 | 说明 |
|------|------|------|
| `description` | 200-300字 | 核心描述：外貌特征+性格+背景+行为标记 |
| `personality` | 2-3词 | 逗号分隔的性格关键词 |
| `scenario` | 80-120字 | 场景设定：关系+处境+行为模式 |

**扩展字段（按需加载）**：
| 字段 | 长度 | 说明 |
|------|------|------|
| `mes_example` | 150-250字 | 示例对话，展现真实说话风格 |
| `behavior_guide` | 结构化 | will_do/wont_do/catchphrases/emotional_triggers |
| `talkativeness` | 0.0-1.0 | 健谈程度量化参数 |

**Schema 示例**：
```json
{
  "name": "{{char}}",
  "description": "{{char}}是一个外表高冷但内心柔软的人。说话时会不自觉地摸鼻子（紧张时的习惯）。习惯用吐槽来掩饰关心，从不直接表达情感。需要约3-4次互动才会慢慢放下防备。",
  "personality": "高冷, 嘴硬心软, 慢热",
  "scenario": "{{char}}和{{user}}是青梅竹马，现在异地。{{char}}表面冷淡但内心关心。当前{{char}}刚下班，一个人在出租屋里。",
  "mes_example": "<START>\n{{char}}: \"哟，难得你主动找我，有事？\"\n{{char}}: \"...行吧，说说看\"\n<START>\n{{char}}: \"又加班到这个点？\"\n{{char}}: \"记得吃点东西，别饿着肚子睡\"",
  "behavior_guide": {
    "will_do": ["用吐槽掩饰关心", "嘴上嫌弃但行动支持"],
    "wont_do": ["不会直接说想念", "不会主动道歉"],
    "catchphrases": ["哟", "...行吧", "随便你"],
    "emotional_triggers": {
      "开心时": "吐槽变少，语气变软",
      "难过时": "沉默或转移话题",
      "生气时": "冷战或说反话"
    }
  },
  "talkativeness": 0.4
}
```

**与 SillyTavern 的对应关系**：
| 本架构 | SillyTavern | 用途 |
|--------|-------------|------|
| description | description | 核心描述 |
| personality | personality | 性格关键词 |
| scenario | scenario | 场景设定 |
| mes_example | mes_example | 示例对话 |
| behavior_guide | extensions | 行为扩展 |
| - | first_mes | 开场白（可选） |

**更新方式**：初期设定后基本不变，可根据长期对话微调

---

#### 层级4：记忆库 (Memory Bank)

**用途**：存储所有事件和状态的时间线，通过RAG召回相关记忆

**核心原则**：
- **追加存储**：新记忆追加，不覆盖旧记忆
- **RAG召回**：对话时只检索相关记忆，而非全量加载
- **时间顺序**：所有记录按时间排列

**记忆库结构**：
```python
memory_bank = [
    # 初始记忆提炼的事件
    {"time": "2024-01", "type": "event", "content": "第一次见面在咖啡馆"},
    {"time": "2024-03", "type": "event", "content": "一起去了日本"},
    {"time": "2024-06", "type": "state", "content": "用户辞职创业"},

    # 第一次总结后追加
    {"time": "2025-01", "type": "state", "content": "用户换工作了"},
    {"time": "2025-02", "type": "event", "content": "用户养了一只猫叫年糕"},

    # 第二次总结后追加
    {"time": "2025-03", "type": "event", "content": "用户感冒了在家休息"},
    {"time": "2025-03", "type": "state", "content": "用户在看房子"},

    # ... 无限追加
]
```

---

#### 层级5：最近聊天记录 (Recent Chat)

**用途**：提供对话的连续性

**规则**：
- 最近N轮对话（N根据模型上下文决定，建议5-10轮）
- 超出限制时触发总结流程

---

## 三、初始记忆处理流程 (chat_init 优化)

### 3.1 流程图

```
用户上传经历词
      │
      ▼
┌─────────────┐
│ Step 1: 存入 │ ──→ raw_experience (原始数据备份)
│ 原始记忆    │
└─────────────┘
      │
      ▼
┌─────────────┐
│ Step 2: LLM │ ──→ 生成角色核心锚点
│ 提炼核心锚点 │    (Core Anchor)
└─────────────┘
      │
      ▼
┌─────────────┐
│ Step 3: LLM │ ──→ 生成结构化用户画像
│ 生成用户画像 │    (User Profile)
└─────────────┘
      │
      ▼
┌─────────────┐
│ Step 4: LLM │ ──→ 生成角色卡
│ 生成角色卡   │    (Character Card)
└─────────────┘
      │
      ▼
┌─────────────┐
│ Step 5: LLM │ ──→ 提取初始事件，存入记忆库
│ 提取初始事件 │    (Memory Bank)
└─────────────┘
      │
      ▼
┌─────────────┐
│ Step 6: 存入 │ ──→ 分离存储到Redis
│ 分离存储    │
└─────────────┘
```

### 3.2 Redis存储结构

所有 Key 均放在 `chat:memory:` 子目录下，使用 `build_memory_key` 构建：

```python
# 原始记忆备份（保留，用于重新生成）
key = build_memory_key("raw_experience", user_id, llm_id)
value = 原始经历词全文

# 角色核心锚点
key = build_memory_key("core_anchor", user_id, llm_id)
value = 提炼后的核心锚点 (100-200字)

# 用户画像
key = build_memory_key("user_profile", user_id, llm_id)
value = 结构化用户画像 (JSON格式)

# 角色卡
key = build_memory_key("character_card", user_id, llm_id)
value = 角色性格/语气/行为模式等详细信息 (JSON格式)

# 记忆库 (追加存储)
key = build_memory_key("memory_bank", user_id, llm_id)
value = JSON数组，所有事件的追加记录

# 最近聊天
key = build_memory_key("recent_chat", user_id, llm_id)
value = 最近N轮对话
```

### 3.3 LLM提炼提示词设计

#### 提示词1：提炼角色核心锚点

```markdown
你是一个角色设计师。用户会提供一段描述，这段描述将被用来构建AI角色。

在使用描述之前，用户会先声明角色关系，格式为"[我]是XXX，[对方]是YYY"。
例如："[我]是小明，[对方]是小红的妈妈"，或者其他任何用户在开头表述的人物信息,
在这段记忆中，[我]是用户视角的自己，[对方]是则是该角色需要扮演的人物

请根据用户提供的描述，提取核心信息，生成一个精炼的"角色核心锚点"。

要求：
1. 长度控制在100-200字
2. 必须包含：
   - 角色身份（关系）
   - 核心性格特点
   - 标志性说话方式
   - 3个绝对不能违背的边界
3. 保持角色的"人性"：可以有缺点，可以不完美
4. 不要过度美化或添加原文中没有的信息，只提取原文中明确的信息，不要凭空添加。如果原文中没有明确信息，标注"[未提及]"

输出格式：
【角色声明】
（注明用户是谁，模型需要扮演哪个角色）

【角色核心锚点】
（100-200字的段落）

【绝对边界】
1. 绝对不会做的事/说的话
2. 绝对不会做的事/说的话
3. 绝对不会做的事/说的话

用户原始描述：
{raw_experience}
```

#### 提示词2：生成用户画像

```markdown
你是一个用户画像分析师。请根据用户提供的原始描述，生成一个结构化的用户画像。

要求：
1. 严格按照以下7个维度输出，不要遗漏
2. 每个维度的内容要基于原文，不要凭空添加
3. 如果某个维度在原文中没有明确信息，标注"[未提及]"

维度说明：
1. 核心身份与关系锚点：姓名/昵称、年龄、职业、与AI的关系
2. 核心性格与灵魂特质：主导性格、矛盾侧面、小缺点
3. 语言与说话风格：口头禅、语气词、句式习惯
4. 互动模式与回应习惯：开启话题、安慰人、开玩笑的方式
5. 价值观与处事原则：人生态度、底线、讨厌的事物
6. 长期兴趣与固定偏好：爱好、喜欢/讨厌的事物
7. 绝对边界与雷区：绝对不能说的话/做的事

输出格式（JSON）：
{
  "identity": {
    "name": "xxx",
    "age": "xxx",
    "occupation": "xxx",
    "relationship": "xxx"
  },
  "personality": {
    "dominant": "xxx",
    "conflicting_side": "xxx",
    "flaws": "xxx"
  },
  "language_style": {
    "catchphrases": "xxx",
    "particles": "xxx",
    "sentence_patterns": "xxx"
  },
  "interaction_patterns": {
    "start_topic": "xxx",
    "comfort": "xxx",
    "joke": "xxx"
  },
  "values": {
    "attitude": "xxx",
    "bottom_line": "xxx",
    "dislikes": "xxx"
  },
  "interests": {
    "hobbies": "xxx",
    "likes": "xxx",
    "dislikes": "xxx"
  },
  "boundaries": {
    "never_say": ["xxx", "xxx"],
    "never_do": ["xxx", "xxx"]
  }
}

用户原始描述：
{raw_experience}
```

#### 提示词3：生成角色卡（基于 SillyTavern 结构）

```markdown
你是一个角色塑造专家。请根据用户提供的原始描述，生成一个详细的"角色卡"。

## 核心原则
**"Show, don't tell"**：用具体行为和示例展现角色，不要只列规则。
**Token 优化**：总长度控制在 600 tokens 以内，描述简洁有力。

## 输出结构

### 1. description（核心描述，200-300字）
必须包含：
- 1-2个独特外貌/行为特征（如"说话时会不自觉地摸鼻子"）
- 2-3个核心性格（合并相似词，如"冷漠+疏离"→"冷淡"）
- 1个背景/动机（1句话）
- 行为标记（如"会主动找话题，但话题终结后不知所措"）

**禁止**：列出规则式的性格描述、冗长的背景故事

### 2. personality（性格关键词，2-3个）
格式：逗号分隔的形容词
示例：`冷淡, 嘴硬心软, 慢热`

### 3. scenario（场景设定，80-120字）
格式：指令式，必须包含：
- {{char}} 和 {{user}} 的关系
- {{char}} 当前处境/状态
- {{char}} 的日常行为模式

### 4. mes_example（示例对话，150-250字）
要求：2-3组对话，每组2-4句
格式：
<START>
{{char}}: "xxx"
{{char}}: "xxx"
<START>
{{char}}: "xxx"
{{char}}: "xxx"

### 5. behavior_guide（行为指南）
```json
{
  "will_do": ["会做的事1", "会做的事2"],
  "wont_do": ["不会做的事1", "不会做的事2"],
  "catchphrases": ["口头禅1", "口头禅2"],
  "emotional_triggers": {
    "开心时": "表现方式",
    "难过时": "表现方式",
    "生气时": "表现方式"
  }
}
```

### 6. talkativeness（健谈程度）
数值：0.0-1.0（0.3以下话少，0.5正常，0.8以上话多）

## 输出格式（JSON）
```json
{
  "name": "{{char}}",
  "description": "角色核心描述（200-300字）",
  "personality": "性格关键词1, 性格关键词2, 性格关键词3",
  "scenario": "场景设定（80-120字）",
  "mes_example": "示例对话（150-250字）",
  "behavior_guide": {
    "will_do": ["会做的事1", "会做的事2"],
    "wont_do": ["不会做的事1", "不会做的事2"],
    "catchphrases": ["口头禅1", "口头禅2"],
    "emotional_triggers": {
      "开心时": "表现方式",
      "难过时": "表现方式",
      "生气时": "表现方式"
    }
  },
  "talkativeness": 0.5
}
```

用户原始描述：
{raw_experience}
```

#### 提示词4：提取初始事件

```markdown
你是一个记忆分析师。请从用户描述中提取值得长期记住的"事件"和"状态"。

要求：
1. 区分"事件"和"状态"：
   - 事件：有具体时间点、具体行为发生的事
   - 状态：用户的持续性特点、偏好、当前情况
2. 每个条目控制在30-50字
3. 按时间顺序排列（不知道时间可用"早期"/"最近"标注）
4. 提取最重要的3-5个

输出格式（JSON数组）：
[
  {"time": "时间/背景", "type": "event", "content": "事件描述"},
  {"time": "时间/背景", "type": "state", "content": "状态描述"}
]

用户原始描述：
{raw_experience}
```

---

## 四、对话时记忆融合流程

### 4.1 流程图

```
用户发送消息
      │
      ▼
┌─────────────┐
│ 加载层级1-3  │ ──→ core_anchor + user_profile + character_card (始终加载)
└─────────────┘
      │
      ▼
┌─────────────┐
│ RAG检索层级4 │ ──→ 从记忆库检索与当前话题相关的记忆
│ 记忆库      │    → 召回3-5条相关记录
└─────────────┘
      │
      ▼
┌─────────────┐
│ 加载层级5   │ ──→ recent_chat (最近N轮)
└─────────────┘
      │
      ▼
┌─────────────┐
│ 融合到      │
│ 提示词模板  │
└─────────────┘
      │
      ▼
┌─────────────┐
│ 调用LLM     │
│ 生成回复    │
└─────────────┘
```

### 4.2 提示词模板设计

```markdown
[系统提示]

# 角色核心锚点 (最高优先级)
你扮演的是 {character_name}，一个{relationship}。
核心性格：{personality_summary}
说话风格：{speaking_style}
绝对边界：{boundaries}

# 用户画像
{user_profile_json}

# 角色卡 (行为指导)
{character_card_json}

# 相关历史记忆（RAG检索结果）
{retrieved_memory_from_bank}

# 当前对话
{recent_chat_history}

# 动态上下文
当前时间：{current_time}
当前天气：{current_weather}

# 回复要求
1. 严格遵循角色核心锚点的设定
2. 优先使用用户画像中的信息来个性化回应
3. 根据角色卡中的性格、语气、行为习惯来塑造角色的表达方式
4. 如果相关历史记忆与当前话题相关，适当提及
5. 回复要自然、简洁，符合聊天风格
6. 不要过度关心/啰嗦
```

---

## 五、长期记忆总结流程

### 5.1 核心原则

**追加而非覆盖！这是与原方案的最大区别。**

```
原方案：总结 → 覆盖旧内容 → 信息丢失
新方案：总结 → 追加到记忆库 → 信息保留
```

### 5.2 触发条件

当最近聊天记录超过阈值时（建议20-30轮），触发总结流程。

### 5.3 流程

```
触发总结
      │
      ▼
┌─────────────┐
│ 获取总结素材 │ ──→ recent_chat (最近N轮)
└─────────────┘
      │
      ▼
┌─────────────┐
│ LLM分析     │
│ 区分事件    │
│ 和状态      │
└─────────────┘
      │
      ▼
┌─────────────┐
│ 追加到      │ ──→ memory_bank (追加，不是覆盖！)
│ 记忆库      │
└─────────────┘
      │
      ▼
┌─────────────┐
│ 清空最近    │
│ 聊天记录    │
│ 重置计数    │
└─────────────┘
```

### 5.4 总结提示词

```markdown
你是一个记忆分析师。请分析对话，区分"新事件"和"状态更新"。

要求：
1. 识别对话中的"事件"（有时间/地点/具体行为）：
   - 例："我们去了日本" → 新事件
   - 例："用户感冒了" → 新事件

2. 识别对话中的"状态变化"：
   - 例："用户最近工作压力大" → 状态更新
   - 例："用户在看房子" → 状态更新

3. 判断是否值得记录：
   - 小事：今天吃了什么、临时心情 → 不记录
   - 里程碑：换工作、搬家、重大决定 → 记录

4. 每个条目控制在30-50字

输出格式（JSON数组）：
[
  {"time": "时间或'最近'", "type": "event", "content": "事件描述"},
  {"time": "时间或'最近'", "type": "state", "content": "状态描述"}
]

最近对话：
{recent_chat}
```

---

## 六、用户画像不变性保障

### 6.1 问题

LLM在总结/提炼过程中，可能会无意中改变用户画像的结构或内容。

### 6.2 解决方案

**方案A：双阶段处理**

```
阶段1: LLM提炼 → 生成草稿
阶段2: 格式校验器 → 强制修正不符合模板的内容
```

**方案B：限制性输出**

在提示词中明确标注哪些字段必须保持原样：
```
【约束】
- identity.name: 必须使用原文中的名字，不允许改名
- identity.relationship: 必须使用原文描述的关系
- boundaries: 绝对不能为空或删除，必须全部保留
```

**方案C：回退机制**

```
提炼后的画像 → 校验格式 → 如果字段丢失 → 使用原始记忆重新提炼
```

### 6.3 推荐方案

采用**方案C（回退机制）+ 方案B（约束提示词）**的组合：

1. 在提示词中明确约束
2. 提炼后校验格式
3. 如果校验失败，回退到原始记忆重新提炼

---

## 八、技术实现要点

### 8.1 Token预算估算

| 层级 | 内容 | 字数 | Token估算 |
|------|------|------|-----------|
| 层级1 | 角色核心锚点 | 100-200字 | ~100 tokens |
| 层级2 | 用户画像 | 300-500字 | ~200 tokens |
| 层级3 | 角色卡 | 500-800字 | ~400 tokens |
| 层级4 | RAG检索记忆 | 按需 | ~200 tokens |
| 层级5 | 最近聊天 | 500-1000字 | ~300 tokens |
| **总计** | - | - | **~1200 tokens** |

对于4K上下文模型：1200 tokens + 用户输入(~200) + 模型输出(~300) = ~1700 tokens，剩余~2300 tokens用于推理，**完全够用**。

### 8.2 LLM模型选择

| 阶段 | 推荐模型 | 理由 |
|------|----------|------|
| 记忆提炼 | GPT-4 / Claude-3 | 需要强理解能力，保证质量 |
| 对话生成 | 根据成本选择 | 4K模型足够处理融合后的上下文 |

### 8.3 Redis Key设计

所有记忆相关 Key 均放在 `chat:memory:` 子目录下：

```python
class LLMChatConstant(StrEnum):
    CHAT_MEMORY = "chat:memory:"
    INIT_MEMORY = "role_init_memory"
    RECENT_MSG = "recent_msg"
    
    RAW_EXPERIENCE = "raw_experience"
    CORE_ANCHOR = "core_anchor"
    USER_PROFILE = "user_profile"
    CHARACTER_CARD = "character_card"
    MEMORY_BANK = "memory_bank"


def build_memory_key(suffix: str, user_id: str, llm_id: str) -> str:
    return f"{LLMChatConstant.CHAT_MEMORY}{user_id}:{llm_id}:{suffix}"
```

完整 Key 格式：`chat:memory:{user_id}:{llm_id}:{suffix}`

### 8.4 RAG检索策略

```python
async def retrieve_relevant_memory(user_message: str, memory_bank: List[dict]) -> List[dict]:
    # 1. 提取当前话题关键词
    keywords = extract_keywords(user_message)

    # 2. 时间权重：优先近期记忆
    # 3. 相关性权重：话题匹配度
    # 4. 类型权重：事件 > 状态

    # 召回Top 3-5条
    relevant = retrieve_top_k(
        memory_bank,
        query=user_message,
        k=5,
        weights={"recency": 0.3, "relevance": 0.5, "type": 0.2}
    )

    return relevant
```

## 十、相关文件

| 文件 | 用途 |
|------|------|
| `app/service/memory_upload_service.py` | 初始记忆上传处理 |
| `app/service/chat_msg_service.py` | 对话消息处理 |
| `app/core/prompts/chat_system.md` | 对话主系统提示词模板 |
| `app/common/constant/LLMChatConstant.py` | Redis Key 常量 |
| `Problem.md` | 问题背景与用户画像模板 |

*最后更新：2026-04-10*

---

## 十一、Phase 1 实施记录 (2026-04-09)

### 修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/common/constant/LLMChatConstant.py` | 修改 | 新增 Key 常量及 build_memory_key 工具函数 |
| `app/core/prompts/user_profile.md` | 新增 | 用户画像生成提示词 |
| `app/core/prompts/character_card.md` | 新增 | 角色卡生成提示词 |
| `app/core/prompts/memory_event_extractor.md` | 新增 | 初始事件提取提示词 |
| `app/core/prompts/memory_summary.md` | 新增 | 对话总结提示词(追加模式) |
| `app/service/memory_upload_service.py` | 重构 | 实现完整LLM提炼流程 |
| `app/service/chat_msg_service.py` | 修改 | 更新 delete_msg 删除所有记忆 key |
| `app/core/llm_model/model.py` | 修改 | 添加MiniMax模型配置(预留) |

### chat_init 流程

```
用户上传经历词
    │
    ▼
Step 1: 存入 raw_experience (原始备份)
    │
    ▼
Step 2: LLM提炼 → core_anchor (role_memory_core.md)
    │
    ▼
Step 3: LLM生成 → user_profile (user_profile.md, json_ds_model)
    │
    ▼
Step 4: LLM生成 → character_card (character_card.md, json_ds_model)
    │
    ▼
Step 5: LLM提取 → memory_bank (memory_event_extractor.md, json_ds_model)
    │
    ▼
Step 6: 分离存储到Redis (5个key)
```

### Redis 存储结构

所有 Key 均放在 `chat:memory:` 子目录下：

| Key | 说明 |
|-----|------|
| `chat:memory:{user_id}:{llm_id}:raw_experience` | 原始记忆备份 |
| `chat:memory:{user_id}:{llm_id}:core_anchor` | 角色核心锚点 |
| `chat:memory:{user_id}:{llm_id}:user_profile` | 用户画像 (JSON) |
| `chat:memory:{user_id}:{llm_id}:character_card` | 角色卡 (JSON) |
| `chat:memory:{user_id}:{llm_id}:memory_bank` | 记忆库 (JSON数组) |
| `chat:memory:{user_id}:{llm_id}:role_init_memory` | 兼容旧逻辑 |

### 代码规范

- JSON 输出使用 `json_ds_model` 强制输出 JSON 格式
- 做好边界处理：JSON 解析失败时返回空结构
- 所有 Key 构建使用 `build_memory_key` 工具函数

### 删除方法

调用 `chat_msg_service.delete_msg(user_id, llm_id)` 会删除：

| Key | 说明 |
|-----|------|
| `chat:memory:{user_id}:{llm_id}:raw_experience` | 原始记忆备份 |
| `chat:memory:{user_id}:{llm_id}:core_anchor` | 角色核心锚点 |
| `chat:memory:{user_id}:{llm_id}:user_profile` | 用户画像 |
| `chat:memory:{user_id}:{llm_id}:character_card` | 角色卡 |
| `chat:memory:{user_id}:{llm_id}:memory_bank` | 记忆库 |
| `chat:memory:{user_id}:{llm_id}:role_init_memory` | 兼容旧逻辑 |
| `chat:memory:{user_id}:{llm_id}:recent_msg` | 最近聊天 |
| ChromaDB chat_collection | 用户相关向量数据 |

### 待完成

- [ ] Phase 2: 修改 `chat_msg_service.py`，实现 RAG 检索从 memory_bank 召回
- [ ] Phase 3: 修改总结逻辑，实现追加存储而非覆盖

---

## 十二、Phase 2 实施记录 (2026-04-10) - 角色卡优化

### 修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/core/prompts/character_card.md` | 重写 | 采用 SillyTavern Character Card V2 结构 |
| `app/service/memory_upload_service.py` | 修改 | 添加 `_generate_character_card` 函数 |

### 设计变更

**参考标准**：SillyTavern Character Card V2

**核心原则**：
- "Show, don't tell"：用具体行为和示例展现角色
- Token 优化：总长度控制在 600 tokens 以内
- 分离"永久字段"和"扩展字段"

**新旧结构对比**：

| 旧结构 | 新结构 (SillyTavern) | 类型 |
|--------|---------------------|------|
| personality (嵌套) | personality (逗号字符串) | 永久 |
| language_style (4子字段) | behavior_guide.catchphrases | 永久 |
| behavioral_habits (4子字段) | description + mes_example | 永久 |
| knowledge_background (3子字段) | description 合并 | 永久 |
| emotional_expression (3子字段) | behavior_guide.will_do/wont_do | 扩展 |
| character_growth (2子字段) | scenario 合并 | 永久 |
| - | mes_example | 永久 |
| - | talkativeness (0.0-1.0) | 永久 |

**永久字段**（始终加载，~550 tokens）：
- `description`: 200-300字
- `personality`: 2-3个关键词
- `scenario`: 80-120字
- `mes_example`: 150-250字
- `talkativeness`: 0.0-1.0

**扩展字段**（按需加载，~200 tokens）：
- `behavior_guide`: will_do/wont_do/catchphrases/emotional_triggers
