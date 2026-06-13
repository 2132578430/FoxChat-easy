# Java Agent 迁移设计文档

> v0.1 — 确定技术选型、架构策略与分阶段搬迁路线。后续各 Phase 细节独立成文。

---

## 一、为什么需要迁移？

### 1.1 现状

当前 AI Agent 核心逻辑位于 **FoxChatRAG-python** 模块，通过 gRPC 流式 RPC 暴露给 Java 后端调用：

```
HTTP Request → Java (Spring Boot) ──gRPC streaming──→ Python (LangGraph Agent)
```

Python 端积累了 4 个月的迭代成果：
- **11 节点 LangGraph DAG**（含条件路由 + 4 路并行后处理）
- **BM25 + ChromaDB + Cross-Encoder 混合检索**
- **A/B/C 三层认知记忆体系**
- **LiteLLM 多模型适配**

### 1.2 迁移动机

| 维度 | Python 端现状 | Java 端优势 |
|------|-------------|-----------|
| **生态成熟度** | ✅ Python LangChain/LangGraph 成熟 | ✅ 2025 年 Java AI 生态已爆发 |
| **企业级可靠性** | ⚠️ GIL、异步、内存管理 | ✅ JVM 稳定性、类型安全、编译期检查 |
| **新功能扩展** | ⚠️ MCP/Multi-Agent 需另起炉灶 | ✅ LangGraph4j 原生支持 |
| **团队技术栈** | ⚠️ Java 为主，Python 维护成本高 | ✅ 统一技术栈 |
| **运维部署** | ⚠️ 双语言双容器 | ✅ 单 JVM 部署（可选） |
| **Skill 注入** | ⚠️ 自研机制 | ✅ LangGraph4j Hook 系统 |

### 1.3 核心原则

> **不推倒重来，而是"翻译"——Python 代码就是活文档，每一步都有参照物。**

- **双引擎并行**：Python 保留为生产安全网，Java 渐进式接管
- **1:1 节点映射**：每个 Python 节点翻译为对应的 Java 节点，逻辑不变
- **增量验证**：每完成一个 Phase，对比两个引擎的输出质量

---

## 二、技术选型

### 2.1 候选框架对比

| | LangChain4j + LangGraph4j | Spring AI | Spring AI Alibaba |
|---|---|---|---|
| **Python LangGraph API 映射** | ✅ **1:1 几乎完全相同** | ⚠️ 需适配 | ⚠️ 概念类似但API不同 |
| **迁移成本** | ⭐ **最低**（逐行翻译） | ⭐⭐ 中 | ⭐⭐ 中 |
| **StateGraph** | ✅ 完整支持 | ⚠️ 基础 | ✅（fork LangGraph4j） |
| **条件路由** | ✅ `addConditionalEdges` | ⚠️ | ✅ |
| **并行执行** | ✅ 原生支持 | ❌ | ✅ |
| **Checkpointer** | ✅ Memory/MySQL/PG/Redis | ⚠️ | ✅ |
| **ReAct Agent** | ✅ `AgentExecutor` 开箱即用 | ⚠️ | ✅ `ReactAgent` |
| **MCP 支持** | ✅ `langchain4j-mcp` | ✅ | ✅ |
| **LLM 模型支持** | ✅ **20+ 提供商** | 10+ | 阿里系为主 |
| **Spring Boot 集成** | ✅ 良好 | ✅ 一级公民 | ✅ 一级公民 |
| **社区活跃度** | ⭐⭐⭐⭐⭐ 最活跃 | ⭐⭐⭐ | ⭐⭐ |
| **GitHub Stars** | 15k+ | 3k+ | 2k+ |

### 2.2 最终选择：LangChain4j + LangGraph4j

```
第一选择：LangChain4j + LangGraph4j
──────────────────────────────────
✅ Python→Java 逐行翻译，迁移成本最低
✅ 11个节点 + 条件路由 + 4路并行 → 完全照搬
✅ AgentExecutor 自带 ReAct 循环
✅ MCP 支持（langchain4j-mcp）
✅ 社区最成熟，文档最全面
✅ 与现有 Spring Boot 不冲突

备注：Spring AI Alibaba 的 graph-core 本身是 fork LangGraph4j 的。
      先用原版，后续若有阿里系深度绑定需求再切换。
```

---

## 三、架构策略：双引擎并行

### 3.1 目标架构

```
┌──────────────────────────────────────────────────────────┐
│                    FoxChat-java (Spring Boot)              │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              AgentRouter (feature flag)            │   │
│  └─────┬──────────────────────────────┬──────────────┘   │
│        │                              │                   │
│  ┌─────▼──────────┐    ┌──────────────▼──────────────┐   │
│  │  Python Agent   │    │  Java Agent (LangGraph4j)    │   │
│  │  (gRPC 调用)    │    │                              │   │
│  │  ✅ 生产稳定版   │    │  🔨 创新试验田               │   │
│  │  🔒 仅维护不新增 │    │  🆕 所有新功能在此开发       │   │
│  └────────────────┘    └──────────────────────────────┘   │
│                                                          │
│  新功能（全走 Java Agent）：                               │
│  ├─ MCP 联网搜索 + 工具调用                               │
│  ├─ ReAct 多层思考循环                                    │
│  ├─ Skill 动态注入                                        │
│  ├─ Multi-Agent 协作                                      │
│  └─ Human-in-the-Loop                                     │
└──────────────────────────────────────────────────────────┘
```

### 3.2 切换策略

```java
// AgentRouter.java — 灰度路由
if (featureFlag.isJavaAgentEnabled(userId)) {
    return javaAgentService.chat(llmId, msgContent, userId);  // 新引擎
} else {
    return pythonGrpcClient.chat(llmId, msgContent, userId);  // 旧引擎（安全网）
}
```

灰度节奏：`1% → 10% → 50% → 100%`，每阶段对比两个引擎输出质量。

### 3.3 Python 端的归宿

- **混合检索（BM25 + ChromaDB + Rerank）**：封装为 gRPC Tool，Java Agent 远程调用
- **其他能力**：逐步由 Java 侧接管
- **最终状态**：Python 缩身为"RAG 检索微服务"或完全冷备

---

## 四、节点搬迁清单

### 4.1 当前 Python DAG 拓扑

```
START → pre_flight → fetch_memory → parse_memory → classify_intent
    → [retrieve | skip_retrieval] → invoke_llm
    → [save_message ∥ format_output ∥ classify_emotion ∥ trigger_summary]
    → unlock → END
```

### 4.2 搬家清单

| # | 节点 | 操作 | 方式 |
|---|------|------|------|
| 1 | `pre_flight` | ✅ 搬 | Java Redis 直连 incr，3 行代码 |
| 2 | `fetch_memory` | ✅ 搬 | Java RedisTemplate pipeline 批量拉取 |
| 3 | `parse_memory` | ✅ 搬 | 纯 JSON/字符串解析，Java 原生能力 |
| 4 | `classify_intent` | 🔄 变 Tool | 封装为 `@Tool`，Agent 按需调用 |
| 5 | `retrieve` | ⚠️ 暂留 Python | gRPC Tool 远程调用混合检索服务 |
| 6 | `skip_retrieval` | ✅ 搬 | 条件路由空操作，LangGraph4j 原生 |
| 7 | `invoke_llm` | ✅ 核心搬 | LangChain4j `ChatLanguageModel` |
| 8 | `save_message` | ✅ 搬 | Java Redis 直写 |
| 9 | `format_output` | ✅ 搬 | 纯字符串解析 |
| 10 | `classify_emotion` | 🔄 变 Tool | 封装为 `@Tool` |
| 11 | `trigger_summary` | 🔄 变 Tool | 封装为 `@Tool` + `afterThink` Hook |
| 12 | `unlock` | ✅ 搬 | 汇聚节点，空操作 |

> **核心结论**：12 个节点中，真正必须留在 Python 的只有 `retrieve`（混合检索）。其余 11 个 Java 全能做。

---

## 五、代码映射：Python → Java 1:1 翻译

### 5.1 State 定义

**Python** (`state.py`)：
```python
class ChatState(TypedDict, total=False):
    user_id: str
    llm_id: str
    msg_content: str
    current_round: int
    memories: ChatMemories
    parsed: ParsedMemories
    intent_result: Dict[str, Any]
    relevant_memories_text: str
    ai_response: str
    blocks: List[dict]
    emotion: str
```

**Java** (`ChatState.java`)：
```java
public class ChatState extends AgentState {

    public static final Map<String, Channel<?>> SCHEMA = Map.of(
        "user_id", Channel.value(),
        "llm_id", Channel.value(),
        "msg_content", Channel.value(),
        "current_round", Channel.value(),
        "memories", Channel.value(),
        "parsed", Channel.value(),
        "intent_result", Channel.value(),
        "relevant_memories_text", Channel.value(),
        "ai_response", Channel.value(),
        "blocks", Channel.appender(ArrayList::new),
        "emotion", Channel.value()
    );

    public ChatState(Map<String, Object> initData) { super(initData); }

    public String userId() { return value("user_id").orElse(""); }
    public String llmId() { return value("llm_id").orElse(""); }
    public String aiResponse() { return value("ai_response").orElse(""); }
    // ... 其余 getter
}
```

### 5.2 Graph 构建

**Python** (`graph.py`)：
```python
def build_main_graph() -> StateGraph:
    builder = StateGraph(ChatState)
    builder.add_node("pre_flight", pre_flight)
    # ...
    builder.add_conditional_edges(
        "classify_intent",
        need_retrieval,
        {"retrieve": "retrieve", "skip_retrieval": "skip_retrieval"},
    )
    return builder.compile(checkpointer=checkpointer)
```

**Java** (`ChatGraphBuilder.java`)：
```java
public CompiledGraph<ChatState> build() {
    var builder = new StateGraph<>(
        ChatState.SCHEMA,
        initData -> new ChatState(initData)
    );

    builder
        .addNode("pre_flight", node_async(this::preFlight))
        .addNode("fetch_memory", node_async(this::fetchMemory))
        .addNode("classify_intent", node_async(this::classifyIntentNode))
        .addNode("retrieve", node_async(this::retrieve))
        .addNode("skip_retrieval", node_async(this::skipRetrieval))
        .addNode("invoke_llm", node_async(this::invokeLlm))
        .addNode("save_message", node_async(this::saveMessage))
        .addNode("format_output", node_async(this::formatOutput))
        .addNode("classify_emotion", node_async(this::classifyEmotion))
        .addNode("trigger_summary", node_async(this::triggerSummary))
        .addNode("unlock", node_async(this::unlock))

        // 主干
        .addEdge(START, "pre_flight")
        .addEdge("pre_flight", "fetch_memory")
        .addEdge("fetch_memory", "parse_memory")
        .addEdge("parse_memory", "classify_intent")

        // ★ 条件路由（与 Python 完全一致）
        .addConditionalEdges("classify_intent", this::needRetrieval, Map.of(
            "retrieve", "retrieve",
            "skip_retrieval", "skip_retrieval"
        ))

        .addEdge("retrieve", "invoke_llm")
        .addEdge("skip_retrieval", "invoke_llm")

        // ★ 4 路并行后处理（与 Python 完全一致）
        .addEdge("invoke_llm", "save_message")
        .addEdge("invoke_llm", "format_output")
        .addEdge("invoke_llm", "classify_emotion")
        .addEdge("invoke_llm", "trigger_summary")

        // 汇聚
        .addEdge("save_message", "unlock")
        .addEdge("format_output", "unlock")
        .addEdge("classify_emotion", "unlock")
        .addEdge("trigger_summary", "unlock")
        .addEdge("unlock", END);

    return builder.compile(
        CompileConfig.builder()
            .checkpointSaver(new MemorySaver())
            .build()
    );
}
```

### 5.3 Prompt 注入链

**Python** 端当前的注入链：
```python
memories = await fetch_all_memories(user_id, llm_id)  # 拉取
parsed = parse(character_card, core_anchor, ...)       # 解析
payload = build_prompt_payload(parsed, ...)            # 构建注入块
system_prompt = template.format(**payload)             # 注入到模板
messages = [system_prompt] + history + [user_msg]      # 拼装
response = await litellm.acompletion(messages)         # 调用
```

**Java** 端对应实现：

```java
@Component
public class MemoryInjectionHook {

    private final RedisTemplate<String, String> redis;
    private final PromptManager promptManager;

    /**
     * 在 Agent 每次 THINK 前执行：拉取记忆 → 解析 → 注入
     */
    public String buildSystemPrompt(String userId, String llmId, String relevantMemories) {
        // 1. Redis pipeline 批量拉取（对应 fetch_all_memories）
        Memories memories = fetchAllMemories(userId, llmId);

        // 2. 解析（对应 parse_memory 节点）
        ParsedMemories parsed = parseMemories(memories);

        // 3. 加载模板 + 渲染（对应 PromptManager + format）
        String template = promptManager.getPrompt("chat_system");
        Map<String, String> vars = buildInjectionVars(parsed, relevantMemories);

        return StrSubstitutor.replace(template, vars);
    }
}
```

### 5.4 ReAct 升级（Phase 4）

当简单 DAG 完成后，用 LangGraph4j 自带的 `AgentExecutor` 升级为 ReAct 循环：

```java
var agent = AgentExecutor.builder()
    .chatModel(model)
    .tools(List.of(
        new McpWebSearchTool(),      // MCP 联网搜索
        new PythonRAGTool(),         // gRPC 调用 Python 混合检索
        new IntentClassifierTool(),  // 意图分类
        new EmotionClassifierTool(), // 情绪分类
        new SummaryTriggerTool()     // 摘要触发
    ))
    .systemPrompt(systemPrompt)      // Skill 注入的入口
    .build()
    .compile();

// ReAct 循环自动完成：Think → Act → Observe → Think → ...
var result = agent.invoke(Map.of(
    "messages", userMessage,
    "user_id", userId,
    "llm_id", llmId
));
```

---

## 六、分阶段实施路线

### Phase 0：基础设施（当前）

**目标**：新模块搭建 + 依赖引入

```
FoxChat-java/
├── foxChat-agent/          ← 新增模块
│   ├── build.gradle        ← LangGraph4j + LangChain4j 依赖
│   └── src/main/java/com/bedfox/agent/
│       ├── config/          ← Agent 配置
│       ├── graph/           ← StateGraph + 节点实现
│       ├── memory/          ← 记忆拉取/解析
│       ├── prompt/          ← Prompt 模板管理
│       └── tool/            ← @Tool 定义（MCP/RAG/情绪等）
```

**依赖**：
```gradle
implementation 'org.bsc.langgraph4j:langgraph4j-core:1.8.18'
implementation 'org.bsc.langgraph4j:langgraph4j-langchain4j-agent:1.8.18'
implementation 'dev.langchain4j:langchain4j:1.0.0-beta1'
implementation 'dev.langchain4j:langchain4j-open-ai:1.0.0-beta1'
```

### Phase 1：最小骨架（1周）

**目标**：Java Agent 能完成最简链路

```
pre_flight → fetch_memory → parse_memory → invoke_llm → format_output
```

- Redis 直连操作记忆
- LangChain4j 调 LLM
- 不涉及检索、情绪、摘要
- 此时 Python 端不动

### Phase 2：补齐检索（1周）

**目标**：混合检索接入 + 条件路由生效

- Python 混合检索封装为 gRPC Tool
- 意图分类变为 `@Tool`，LLM 自主决定是否检索
- 完整链路跑通：`pre_flight → ... → classify_intent → [retrieve | skip] → invoke_llm → ...`

### Phase 3：后处理完整（3-5天）

**目标**：4 路并行后处理在 Java 侧完成

- 情绪分类 → `@Tool`
- 摘要触发 → 异步 Hook
- 消息保存 → Java Redis 直写
- 格式输出 → 字符串解析

### Phase 4：ReAct 升级（1周）

**目标**：从线性 DAG 升级为 ReAct 循环

- 用 `AgentExecutor` 替代手动构建的 StateGraph
- 所有 Tool 统一注册
- Think→Act→Observe 循环自动完成
- MCP 联网搜索等新 Tool 直接加入

### Phase 5：高级特性（持续）

- Skill 动态注入（Hook 机制）
- Multi-Agent 协作（Subgraph）
- Human-in-the-Loop（高危操作审批）
- A/B 质量对比（Java vs Python 输出）
- Python 逐步退场

---

## 七、不改动的内容

| 内容 | 决策 | 原因 |
|------|------|------|
| Python 混合检索服务 | 保留，封装为 gRPC Tool | Python ChromaDB/BERT/Rerank 生态最成熟 |
| gRPC 协议定义（`ai_chat.proto`） | 保留，Java 侧复用 | 已有 Java proto 编译产物 |
| Redis Key 设计 | 完全照搬 | 两边共享 Redis，无需变动 |
| MySQL 表结构 | 完全照搬 | Java MyBatis 已对接 |
| Prompt 模板（`*.md`） | 完全照搬 | 纯文本，两边共用 |
| 前端/Desktop | 零改动 | 接口不变 |

---

## 八、风险与应对

| 风险 | 概率 | 应对 |
|------|------|------|
| LangGraph4j API 与 Python 有细微差异 | 中 | Phase 1 最小链路快速验证差异 |
| Java LLM 调用效果与 Python LiteLLM 不一致 | 中 | 相同 prompt + 相同模型，对比输出 |
| 人力不足，工期拖延 | 低 | 每 Phase 独立可交付，随时可暂停 |
| Python 端需要 bug 修复 | 低 | Python 端冻结，只修不增 |
| 灰度切换时用户体验波动 | 低 | 1% 起步，逐步放量 |

---

## 九、暂不涉及的内容（留给后续）

- ❌ Python 端完全退役方案
- ❌ 混合检索的 Java 原生实现（替代 Python ChromaDB）
- ❌ 跨 Agent 通信协议（A2A）
- ❌ AgentScope Studio 可视化调试的 Java 版实现

---

> **设计原则**：LangGraph4j 是 Python LangGraph 的 Java 精神续作，API 几乎一致。这不是"重构"，是"翻译"——Python 代码的每一行都是 Java 代码的活文档。双引擎并行，灰度切换，零风险迁移。
