import json, os

batchImportData = {
    "FoxChatRAG-python/app/service/chat/common/json_parser.py": [],
    "FoxChatRAG-python/app/service/chat/common/redis_keys.py": ["FoxChatRAG-python/app/common/constant/LLMChatConstant.py"],
    "FoxChatRAG-python/app/service/chat/common/similarity.py": [],
    "FoxChatRAG-python/app/service/chat/emotion_classifier.py": ["FoxChatRAG-python/app/core/db/mysql_client.py", "FoxChatRAG-python/app/core/prompts/prompt_manager.py", "FoxChatRAG-python/app/schemas/current_state.py", "FoxChatRAG-python/app/service/chat/state_manager.py", "FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "FoxChatRAG-python/app/util/template_util.py"],
    "FoxChatRAG-python/app/service/chat/graph/graph.py": ["FoxChatRAG-python/app/service/chat/graph/nodes.py", "FoxChatRAG-python/app/service/chat/graph/router.py", "FoxChatRAG-python/app/service/chat/graph/state.py"],
    "FoxChatRAG-python/app/service/chat/graph/nodes.py": ["FoxChatRAG-python/app/service/chat/chat_redis_service.py", "FoxChatRAG-python/app/service/chat/common/__init__.py", "FoxChatRAG-python/app/service/chat/emotion_classifier.py", "FoxChatRAG-python/app/service/chat/graph/state.py", "FoxChatRAG-python/app/service/chat/intent_classifier.py", "FoxChatRAG-python/app/service/chat/llm_invoke_service.py", "FoxChatRAG-python/app/service/chat/memory_parser.py", "FoxChatRAG-python/app/service/chat/memory_summary_service.py", "FoxChatRAG-python/app/service/chat/response_parser.py", "FoxChatRAG-python/app/service/chat/state_manager.py", "FoxChatRAG-python/app/service/chat/timer_scheduler.py", "FoxChatRAG-python/app/service/chat/types.py", "FoxChatRAG-python/app/util/__init__.py"],
    "FoxChatRAG-python/app/service/chat/graph/router.py": ["FoxChatRAG-python/app/service/chat/graph/state.py"],
    "FoxChatRAG-python/app/service/chat/graph/state.py": ["FoxChatRAG-python/app/service/chat/types.py"],
    "FoxChatRAG-python/app/service/chat/history_event_retrieval_service.py": ["FoxChatRAG-python/app/common/constant/LLMChatConstant.py", "FoxChatRAG-python/app/core/db/redis_client.py", "FoxChatRAG-python/app/schemas/memory_event.py", "FoxChatRAG-python/app/service/chat/common/__init__.py", "FoxChatRAG-python/app/util/chroma_util.py"],
    "FoxChatRAG-python/app/service/chat/llm_invoke_service.py": ["FoxChatRAG-python/app/common/constant/ChromaTypeConstant.py", "FoxChatRAG-python/app/core/db/mysql_client.py", "FoxChatRAG-python/app/core/prompts/prompt_manager.py", "FoxChatRAG-python/app/service/chat/history_event_retrieval_service.py", "FoxChatRAG-python/app/service/chat/prompt_payload_builder.py", "FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "FoxChatRAG-python/app/service/llm_config_service.py", "FoxChatRAG-python/app/util/__init__.py", "FoxChatRAG-python/app/util/chroma_util.py", "FoxChatRAG-python/app/util/template_util.py"],
    "FoxChatRAG-python/app/service/chat/memory_parser.py": ["FoxChatRAG-python/app/service/chat/common/__init__.py"],
    "FoxChatRAG-python/app/service/chat/memory_summary_service.py": ["FoxChatRAG-python/app/common/constant/ChromaTypeConstant.py", "FoxChatRAG-python/app/common/constant/FileTypeConstant.py", "FoxChatRAG-python/app/common/constant/LLMChatConstant.py", "FoxChatRAG-python/app/core/db/mysql_client.py", "FoxChatRAG-python/app/core/db/redis_client.py", "FoxChatRAG-python/app/core/prompts/prompt_manager.py", "FoxChatRAG-python/app/service/chat/common/__init__.py", "FoxChatRAG-python/app/service/chat/history_event_retrieval_service.py", "FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "FoxChatRAG-python/app/service/chat/user_profile_service.py", "FoxChatRAG-python/app/util/__init__.py", "FoxChatRAG-python/app/util/chroma_util.py", "FoxChatRAG-python/app/util/loader_util.py", "FoxChatRAG-python/app/util/template_util.py"],
    "FoxChatRAG-python/app/service/chat/memory_upload_service.py": ["FoxChatRAG-python/app/common/constant/LLMChatConstant.py", "FoxChatRAG-python/app/core/__init__.py", "FoxChatRAG-python/app/core/db/mysql_client.py", "FoxChatRAG-python/app/core/prompts/prompt_manager.py", "FoxChatRAG-python/app/service/chat/common/__init__.py", "FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "FoxChatRAG-python/app/service/llm_config_service.py", "FoxChatRAG-python/app/util/__init__.py", "FoxChatRAG-python/app/util/chroma_util.py", "FoxChatRAG-python/app/util/template_util.py"],
    "FoxChatRAG-python/app/service/chat/prompt_payload_builder.py": [],
    "FoxChatRAG-python/app/service/chat/session_lock.py": ["FoxChatRAG-python/app/core/db/redis_client.py"],
    "FoxChatRAG-python/app/service/chat/state_manager.py": ["FoxChatRAG-python/app/common/constant/LLMChatConstant.py", "FoxChatRAG-python/app/core/db/redis_client.py", "FoxChatRAG-python/app/schemas/current_state.py", "FoxChatRAG-python/app/service/chat/common/__init__.py", "FoxChatRAG-python/app/util/redis_json_util.py"],
    "FoxChatRAG-python/app/service/chat/strategy/base_strategy.py": [],
    "FoxChatRAG-python/app/service/chat/streaming_tag_parser.py": [],
    "FoxChatRAG-python/app/service/chat/timer_scheduler.py": ["FoxChatRAG-python/app/common/constant/LLMChatConstant.py", "FoxChatRAG-python/app/core/db/redis_client.py"],
    "FoxChatRAG-python/app/service/chat/types.py": [],
    "FoxChatRAG-python/app/service/chat/user_profile_service.py": ["FoxChatRAG-python/app/common/constant/LLMChatConstant.py", "FoxChatRAG-python/app/common/constant/MsgStatusConstant.py", "FoxChatRAG-python/app/core/db/mysql_client.py", "FoxChatRAG-python/app/core/db/redis_client.py", "FoxChatRAG-python/app/core/prompts/prompt_manager.py", "FoxChatRAG-python/app/exception/BusinessException.py", "FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "FoxChatRAG-python/app/util/template_util.py"],
    "FoxChatRAG-python/app/service/llm_config_service.py": ["FoxChatRAG-python/app/models/llm_config.py"],
    "FoxChatRAG-python/app/service/rag/__init__.py": ["FoxChatRAG-python/app/service/rag/rag_search_service.py", "FoxChatRAG-python/app/service/rag/vector_upload_service.py"],
    "FoxChatRAG-python/app/service/rag/vector_upload_service.py": ["FoxChatRAG-python/app/common/__init__.py", "FoxChatRAG-python/app/common/constant/ChromaTypeConstant.py", "FoxChatRAG-python/app/common/constant/LLMChatConstant.py", "FoxChatRAG-python/app/core/db/redis_client.py", "FoxChatRAG-python/app/core/net/__init__.py", "FoxChatRAG-python/app/models/rag_file.py", "FoxChatRAG-python/app/util/__init__.py", "FoxChatRAG-python/app/util/chroma_util.py", "FoxChatRAG-python/app/util/loader_util.py"],
    "FoxChatRAG-python/app/util/__init__.py": ["FoxChatRAG-python/app/util/redis_json_util.py", "FoxChatRAG-python/app/util/template_util.py"],
    "FoxChatRAG-python/app/util/chroma_util.py": ["FoxChatRAG-python/app/chroma/__init__.py", "FoxChatRAG-python/app/common/constant/__init__.py", "FoxChatRAG-python/app/common/constant/ChromaTypeConstant.py"],
    "FoxChatRAG-python/app/util/loader_util.py": ["FoxChatRAG-python/app/common/__init__.py"],
    "FoxChatRAG-python/app/util/redis_json_util.py": [],
    "FoxChatRAG-python/app/util/template_util.py": []
}

nodes = []
edges = []

def add_node(nid, ntype, name, fp, summary, tags, complexity, line_range=None, lang_notes=None):
    n = {"id": nid, "type": ntype, "name": name, "filePath": fp, "summary": summary, "tags": tags, "complexity": complexity}
    if line_range:
        n["lineRange"] = line_range
    if lang_notes:
        n["languageNotes"] = lang_notes
    nodes.append(n)

def add_edge(src, tgt, etype, weight=0.7):
    edges.append({"source": src, "target": tgt, "type": etype, "direction": "forward", "weight": weight})

def add_fn(fp, name, start, end, summary, tags, complexity="simple"):
    nid = f"function:{fp}:{name}"
    add_node(nid, "function", name, fp, summary, tags, complexity, [start, end])
    add_edge(f"file:{fp}", nid, "contains", 1.0)
    return nid

def add_cls(fp, name, start, end, summary, tags, complexity="moderate"):
    nid = f"class:{fp}:{name}"
    add_node(nid, "class", name, fp, summary, tags, complexity, [start, end])
    add_edge(f"file:{fp}", nid, "contains", 1.0)
    return nid

# ============================================================
# FILE 1: json_parser.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/common/json_parser.py"
add_node(f"file:{fp}", "file", "json_parser.py", fp,
    "JSON 安全解析工具，提供带默认值和自定义解析器的容错 JSON 解析功能，防止 LLM 返回格式异常导致崩溃。",
    ["utility", "json", "error-handling"], "simple")
add_fn(fp, "safe_json_parse", 14, 53,
    "带容错的 JSON 解析函数，支持自定义解析器和默认值，解析失败时返回默认值并记录警告日志。",
    ["utility", "json", "error-handling"], "moderate")

# ============================================================
# FILE 2: redis_keys.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/common/redis_keys.py"
add_node(f"file:{fp}", "file", "redis_keys.py", fp,
    "Redis 键名构建工具，为聊天记忆系统各模块生成统一格式的 Redis 键（初始记忆、最近消息、状态、轮次计数器等）。",
    ["utility", "redis", "key-builder"], "simple")
# All functions are 2-3 lines (trivial one-liners), skip function nodes

# ============================================================
# FILE 3: similarity.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/common/similarity.py"
add_node(f"file:{fp}", "file", "similarity.py", fp,
    "文本相似度计算工具，提供 Jaccard 相似度和词重叠率两种算法，用于记忆去重和事件匹配。",
    ["utility", "similarity", "text-processing"], "simple")
add_fn(fp, "calc_jaccard_similarity", 10, 39,
    "计算两段文本的 Jaccard 相似度，基于字符级 n-gram 集合的交并比。",
    ["utility", "similarity", "algorithm"], "moderate")
add_fn(fp, "calc_word_overlap_ratio", 42, 65,
    "计算两段文本的词级重叠比率，基于分词后的交集与并集之比。",
    ["utility", "similarity", "algorithm"], "simple")

# ============================================================
# FILE 4: emotion_classifier.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/emotion_classifier.py"
add_node(f"file:{fp}", "file", "emotion_classifier.py", fp,
    "情感分类服务，通过 LLM 分析模型回复来识别用户当前情感状态，并将结果写入 CurrentState。",
    ["service", "emotion", "llm-invoke", "state-management"], "moderate")
add_fn(fp, "classify_emotion", 27, 72,
    "调用 LLM 对模型回复进行情感分类，使用 EmotionInvokeStrategy 获取情感标签和置信度。",
    ["service", "emotion", "llm-invoke"], "moderate")
add_fn(fp, "_parse_emotion_result", 75, 125,
    "解析 LLM 返回的情感分类结果文本，支持 JSON 格式和纯文本格式，提取情感标签和置信度。",
    ["parser", "emotion", "json"], "moderate")
add_fn(fp, "classify_and_update_emotion", 128, 165,
    "情感分类的主入口函数，调用 LLM 分类后将结果更新到 CurrentState 的 emotion 字段。",
    ["service", "emotion", "state-update"], "moderate")

# ============================================================
# FILE 5: graph/graph.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/graph/graph.py"
add_node(f"file:{fp}", "file", "graph.py", fp,
    "LangGraph 状态图构建器，定义聊天处理的完整工作流图（预检→记忆获取→解析→意图分类→检索/跳过→LLM调用→保存→格式化→情感分类→摘要触发→解锁）。",
    ["orchestration", "langgraph", "workflow"], "moderate")
add_fn(fp, "build_main_graph", 39, 90,
    "构建 LangGraph StateGraph 主图，注册 12 个处理节点并定义节点间的边和条件路由。",
    ["orchestration", "langgraph", "graph-builder"], "complex")
add_fn(fp, "_get_default_checkpointer", 101, 117,
    "获取图的默认检查点存储，优先使用 SQLite 持久化，回退到内存存储。",
    ["infrastructure", "checkpointer"], "simple")

# ============================================================
# FILE 6: graph/nodes.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/graph/nodes.py"
add_node(f"file:{fp}", "file", "nodes.py", fp,
    "LangGraph 图节点实现，包含聊天工作流各阶段的处理函数：预检、记忆获取与解析、意图分类、历史检索、LLM调用、消息保存、输出格式化、情感分类和摘要触发。",
    ["orchestration", "langgraph", "node-handler"], "complex")
add_fn(fp, "pre_flight", 49, 64, "预检节点，递增轮次计数器并构建最近消息 Redis 键。", ["node", "preprocessing"], "simple")
add_fn(fp, "parse_memory", 76, 100, "解析从 Redis 获取的各类记忆数据（角色卡、核心锚点、用户画像、记忆库、当前状态），构建 ParsedMemories 对象。", ["node", "memory", "parser"], "moderate")
add_fn(fp, "classify_intent_node", 104, 116, "意图分类图节点，调用 classify_intent 分析用户消息意图并写入 state。", ["node", "intent", "classification"], "simple")
add_fn(fp, "retrieve", 119, 132, "历史记忆检索节点，调用 search_relevant_memories 获取与用户消息相关的记忆片段。", ["node", "retrieval", "memory"], "simple")
add_fn(fp, "invoke_llm", 144, 184, "LLM 调用核心节点，支持流式和非流式两种模式，组装上下文后调用 LLM 生成回复。", ["node", "llm", "invoke"], "moderate")
add_fn(fp, "trigger_summary", 219, 233, "摘要触发节点，检查最近消息列表长度，超过阈值时触发异步摘要任务。", ["node", "summary", "trigger"], "simple")

# ============================================================
# FILE 7: graph/router.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/graph/router.py"
add_node(f"file:{fp}", "file", "router.py", fp,
    "LangGraph 条件路由函数，根据意图分类结果决定是否需要执行历史记忆检索。",
    ["utility", "router", "langgraph"], "simple")
# need_retrieval is only 7 lines, skip

# ============================================================
# FILE 8: graph/state.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/graph/state.py"
add_node(f"file:{fp}", "file", "state.py", fp,
    "LangGraph 状态定义，ChatState TypedDict 包含聊天工作流的全部状态字段（用户ID、消息内容、记忆、意图、AI回复等）。",
    ["type-definition", "langgraph", "state"], "simple")
add_cls(fp, "ChatState", 12, 38,
    "聊天工作流状态 TypedDict，定义了 user_id、llm_id、msg_content、memories、parsed、intent_result、ai_response、blocks、emotion 等 13 个状态字段。",
    ["type-definition", "state", "typeddict"], "simple")

# ============================================================
# FILE 9: history_event_retrieval_service.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/history_event_retrieval_service.py"
add_node(f"file:{fp}", "file", "history_event_retrieval_service.py", fp,
    "历史事件检索服务，实现 BM25+向量混合检索、去重、融合排序和重排，从记忆库中检索与查询最相关的历史事件。",
    ["service", "retrieval", "search", "hybrid-search"], "complex")
add_fn(fp, "should_deduplicate", 55, 84, "判断两个历史事件是否应去重，基于事件类型、内容相似度和时间窗口。", ["utility", "dedup"], "moderate")
add_fn(fp, "_dict_to_memory_event", 87, 133, "将 Redis 中的事件字典转换为 MemoryEvent 对象，解析各字段并构建完整的事件数据结构。", ["parser", "conversion"], "moderate")
add_fn(fp, "deduplicate_with_recent_window", 136, 173, "基于最近消息窗口对事件进行关键词重叠去重，避免检索到与当前对话重复的历史信息。", ["dedup", "filtering"], "moderate")
add_fn(fp, "format_history_events", 176, 213, "将历史事件列表格式化为可读文本，包含事件类型标签、时间戳和内容摘要。", ["formatter", "output"], "moderate")
add_fn(fp, "_bm25_retrieve_from_memory_bank", 220, 338, "从 Redis 记忆库中使用 BM25 算法检索相关事件，包含分词、TF-IDF 计算和评分排序。", ["retrieval", "bm25", "search"], "complex")
add_fn(fp, "_vector_retrieve_from_chroma", 341, 389, "从 ChromaDB 向量数据库中检索语义相关的历史事件。", ["retrieval", "vector", "chroma"], "moderate")
add_fn(fp, "_is_generic_summary", 392, 419, "判断事件内容是否为通用摘要（缺乏具体信息），通过关键词密度和长度启发式判断。", ["filtering", "heuristic"], "simple")
add_fn(fp, "_compute_specificity_bonus", 422, 443, "计算事件的具体性加分，长内容和非通用摘要获得更高评分。", ["scoring", "ranking"], "simple")
add_fn(fp, "_merge_and_rank_candidates", 446, 555, "融合 BM25 和向量检索结果，去重后按综合分数（相关性+重要性+时间衰减+具体性）排序。", ["fusion", "ranking", "scoring"], "complex")
add_fn(fp, "_rerank_candidates", 558, 615, "使用 FlashrankRerank 模型对候选事件进行二次重排，提升检索精度。", ["reranking", "ml-model"], "moderate")
add_fn(fp, "retrieve_history_events_v2", 618, 707, "历史事件检索主入口，编排 BM25 检索、向量检索、融合排序、重排和去重的完整流程。", ["service", "retrieval", "entry-point"], "complex")

# ============================================================
# FILE 10: llm_invoke_service.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/llm_invoke_service.py"
add_node(f"file:{fp}", "file", "llm_invoke_service.py", fp,
    "LLM 调用服务，负责组装聊天消息上下文（角色卡、记忆、历史消息等）并调用 LLM 生成回复，支持流式和非流式模式，同时提供相关记忆检索功能。",
    ["service", "llm", "invoke", "context-building"], "complex")
add_fn(fp, "_build_chat_messages", 37, 147,
    "组装 LLM 调用所需的完整消息列表，包含系统提示（角色卡+锚点+用户画像+记忆+状态+行为指南）、历史消息和用户输入。",
    ["service", "prompt", "context"], "complex")
add_fn(fp, "invoke_llm_with_retrieval", 150, 191,
    "非流式 LLM 调用入口，组装消息后通过 ChatInvokeStrategy 调用 LLM 获取完整回复。",
    ["service", "llm", "invoke"], "moderate")
add_fn(fp, "stream_llm_with_retrieval", 194, 267,
    "流式 LLM 调用入口，使用 litellm.acompletion 进行流式请求，支持重试和错误处理。",
    ["service", "llm", "streaming"], "complex")
add_fn(fp, "search_relevant_memories", 270, 348,
    "检索与用户消息相关的记忆，结合意图分类结果调用历史事件检索和 ChromaDB 向量检索，合并去重后返回格式化文本。",
    ["service", "retrieval", "memory"], "complex")

# ============================================================
# FILE 11: memory_parser.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/memory_parser.py"
add_node(f"file:{fp}", "file", "memory_parser.py", fp,
    "记忆解析器，将 Redis 中存储的各类 JSON 记忆数据解析为结构化文本，包括角色卡、核心锚点、用户画像、记忆库和当前状态。",
    ["parser", "memory", "json"], "complex")
add_fn(fp, "parse_character_card", 20, 72, "解析角色卡 JSON，提取名称、性格、说话风格、行为指南和 temperature 等字段，拼接为可读文本。", ["parser", "character"], "moderate")
add_fn(fp, "parse_core_anchor", 75, 99, "从角色卡描述中通过正则提取角色声明和核心锚点文本。", ["parser", "regex", "extraction"], "simple")
add_fn(fp, "build_static_anchors", 102, 140, "将灵魂、角色声明、核心锚点、角色卡详情和示例组装为静态锚点文本块。", ["builder", "prompt"], "moderate")
add_fn(fp, "parse_user_profile", 163, 198, "解析用户画像 JSON，遍历多维属性并过滤占位符，生成用户特征摘要文本。", ["parser", "user-profile"], "moderate")
add_fn(fp, "parse_memory_bank", 201, 228, "解析记忆库 JSON 数组，提取每条记忆的时间、类型和内容，拼接为摘要文本。", ["parser", "memory-bank"], "moderate")
add_fn(fp, "parse_current_state", 231, 276, "解析当前状态 JSON，验证为 CurrentState 模型后提取有效字段注入 prompt，包含情感和时间信息。", ["parser", "state"], "moderate")

# ============================================================
# FILE 12: memory_summary_service.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/memory_summary_service.py"
add_node(f"file:{fp}", "file", "memory_summary_service.py", fp,
    "记忆摘要服务，负责从聊天消息中提取记忆事件、去重合并、向 ChromaDB 同步、记忆库压缩和用户画像更新，是记忆系统的核心编排服务。",
    ["service", "memory", "summary", "extraction"], "complex")
add_fn(fp, "_extract_memory_events", 156, 218, "使用 LLM 从最近聊天消息中提取结构化记忆事件，为每个事件生成唯一 ID 和时间戳。", ["service", "extraction", "llm"], "moderate")
add_fn(fp, "_check_duplicate_or_continuation", 230, 267, "检查新事件是否与已有事件重复或是其延续（同一类型+高内容相似度）。", ["dedup", "merge"], "moderate")
add_fn(fp, "_sync_event_to_chroma", 282, 304, "将单个记忆事件同步上传到 ChromaDB 向量数据库。", ["sync", "chroma"], "simple")
add_fn(fp, "_deduplicate_and_append_events", 322, 361, "对新提取的事件进行去重检查，合并延续事件后追加到记忆库并同步 ChromaDB。", ["dedup", "merge", "sync"], "moderate")
add_fn(fp, "_compress_memory_bank_if_needed", 368, 428, "当记忆库超过阈值时，使用 LLM 压缩合并低重要性事件，减少记忆库体积。", ["compression", "memory", "llm"], "complex")
add_fn(fp, "_summary_and_upload", 450, 497, "使用 LLM 对聊天消息生成摘要文档并上传到 ChromaDB。", ["summary", "upload", "llm"], "moderate")
add_fn(fp, "async_summary_msg_parallel", 504, 534, "并行执行摘要上传、事件提取压缩和用户画像更新三个任务。", ["async", "parallel", "orchestration"], "moderate")
add_fn(fp, "trigger_summary_with_counter", 541, 563, "基于 Redis 计数器的摘要触发机制，防止重复触发。", ["trigger", "counter", "redis"], "simple")
add_fn(fp, "execute_summary_loop", 566, 599, "摘要执行循环，处理 Redis 消息队列中的所有待摘要消息。", ["loop", "queue", "summary"], "moderate")

# ============================================================
# FILE 13: memory_upload_service.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/memory_upload_service.py"
add_node(f"file:{fp}", "file", "memory_upload_service.py", fp,
    "记忆上传服务（聊天初始化），在新对话创建时使用 LLM 从经验文本中提取核心锚点、用户画像、初始记忆和角色卡，并写入 Redis 和 ChromaDB。",
    ["service", "memory", "initialization", "upload"], "complex")
add_fn(fp, "_call_llm", 33, 75, "通用 LLM 调用封装，根据场景选择策略构建 prompt 并调用 LLM。", ["service", "llm", "invoke"], "moderate")
add_fn(fp, "_process_memory_task", 131, 165, "单个记忆处理任务的通用流程：调用提取器→写入 Redis→上传 ChromaDB。", ["service", "task", "pipeline"], "moderate")
add_fn(fp, "chat_init", 168, 260, "聊天初始化主函数，验证 LLM 连接后并行提取 4 类记忆数据（核心锚点、用户画像、初始记忆、角色卡），写入 Redis 和 ChromaDB。", ["service", "initialization", "orchestration"], "complex")

# ============================================================
# FILE 14: prompt_payload_builder.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/prompt_payload_builder.py"
add_node(f"file:{fp}", "file", "prompt_payload_builder.py", fp,
    "Prompt 载荷构建器，负责组装 LLM 调用所需的多层上下文块（静态锚点、用户画像、历史上下文、当前状态、行为指南），并执行跨层去重和冲突优先级处理。",
    ["service", "prompt", "builder", "dedup"], "complex")
add_cls(fp, "PromptPayload", 37, 51, "Prompt 载荷数据类，包含静态锚点、用户画像、历史上下文、当前状态、行为指南等 11 个字段。", ["data-model", "prompt"], "simple")
add_fn(fp, "_suppress_duplicates_across_layers", 101, 168, "跨层去重，使用 n-gram 关键词重叠检测并移除低优先级层中与高优先级层重复的内容行。", ["dedup", "filtering", "prompt"], "complex")
add_fn(fp, "_enforce_conflict_priority", 171, 261, "冲突优先级处理，检测行为指南中的边界标记，移除记忆库中与之冲突的内容，并在状态层添加冲突警告。", ["conflict", "priority", "prompt"], "complex")
add_fn(fp, "build_prompt_payload", 264, 387, "Prompt 载荷构建主函数，组装 7 层上下文块，执行空块过滤、跨层去重和冲突处理，返回 PromptPayload 对象。", ["builder", "prompt", "orchestration"], "complex")

# ============================================================
# FILE 15: session_lock.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/session_lock.py"
add_node(f"file:{fp}", "file", "session_lock.py", fp,
    "会话锁管理，基于 Redis 实现分布式会话锁，防止同一用户的并发聊天请求产生竞态条件。",
    ["service", "lock", "redis", "concurrency"], "simple")
add_fn(fp, "acquire_session_lock", 14, 47, "获取会话锁，使用 Redis 分布式锁实现，支持超时和异步等待，获取失败抛出 RuntimeError。", ["lock", "redis", "async"], "moderate")

# ============================================================
# FILE 16: state_manager.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/state_manager.py"
add_node(f"file:{fp}", "file", "state_manager.py", fp,
    "状态管理器，通过 RedisJSON 存储和管理 CurrentState 对象，支持字段级原子更新、过期检查、来源优先级覆盖规则和从旧格式迁移。",
    ["service", "state", "redis", "json"], "complex")
add_fn(fp, "get_current_state", 77, 108, "获取当前状态，从 RedisJSON 读取并反序列化为 CurrentState 对象，不存在时创建默认状态或从旧格式迁移。", ["state", "read", "redis"], "moderate")
add_fn(fp, "update_current_state", 222, 294, "更新当前状态字段，应用来源优先级覆盖规则和置信度比较，支持字段级原子更新。", ["state", "update", "priority"], "complex")
add_fn(fp, "_apply_state_overwrite_rules", 297, 355, "状态覆盖规则引擎，根据更新来源优先级、置信度和轮次有效期决定是否允许覆盖现有值。", ["rule-engine", "priority", "state"], "complex")
add_fn(fp, "check_and_expire_fields", 358, 386, "检查并过期超期的状态字段，将过期字段重置为默认值。", ["state", "expire", "cleanup"], "moderate")
add_fn(fp, "increment_round_counter", 396, 406, "递增 Redis 中的轮次计数器，用于跟踪对话轮次。", ["counter", "redis"], "simple")

# ============================================================
# FILE 17: strategy/base_strategy.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/strategy/base_strategy.py"
add_node(f"file:{fp}", "file", "base_strategy.py", fp,
    "LLM 调用策略基类，使用策略模式封装不同场景（聊天、记忆、摘要、提取、情感）的 LLM 调用参数配置和重试逻辑。",
    ["strategy", "llm", "invoke", "pattern"], "complex")
add_cls(fp, "LLMInvokeStrategy", 30, 170,
    "LLM 调用策略基类，包含场景配置、模型参数获取、调用重试、错误分类和 JSON 输出解析，是 Chat/Memory/Summary/Extraction/Emotion 策略的父类。",
    ["strategy", "base-class", "llm", "retry"], "complex")
# Sub-classes (ChatInvokeStrategy etc.) are trivial 5-line subclasses, skip

# ============================================================
# FILE 18: streaming_tag_parser.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/streaming_tag_parser.py"
add_node(f"file:{fp}", "file", "streaming_tag_parser.py", fp,
    "流式标签解析器，实时解析 LLM 流式输出中的动作标签（如思考、动作等），将流式 token 分类为普通文本或标签内容。",
    ["parser", "streaming", "tag", "real-time"], "moderate")
add_cls(fp, "StreamingTagParser", 42, 179,
    "流式标签解析器核心类，维护解析状态机，逐字符处理输入流，识别动作标签的开始/结束边界，输出 StreamToken 序列。",
    ["parser", "state-machine", "streaming"], "complex")

# ============================================================
# FILE 19: timer_scheduler.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/timer_scheduler.py"
add_node(f"file:{fp}", "file", "timer_scheduler.py", fp,
    "定时摘要调度器，定期扫描活跃会话并在超过时间阈值时触发自动摘要，防止长时间未摘要导致消息丢失。",
    ["service", "scheduler", "timer", "summary"], "moderate")
add_fn(fp, "get_active_sessions", 66, 92, "通过 Redis SCAN 扫描所有活跃会话的计数器键，解析出 user_id 和 llm_id 对。", ["scanner", "redis", "session"], "moderate")
add_fn(fp, "timer_summary_check_single", 95, 136, "对单个会话检查是否需要触发定时摘要，比较距上次摘要的时间间隔。", ["timer", "check", "summary"], "moderate")
add_fn(fp, "timer_scheduler", 139, 175, "定时调度主循环，周期性扫描所有活跃会话并触发超时摘要。", ["scheduler", "loop", "async"], "moderate")

# ============================================================
# FILE 20: types.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/types.py"
add_node(f"file:{fp}", "file", "types.py", fp,
    "聊天记忆系统的数据类型定义，包含 ChatMemories（原始记忆数据）和 ParsedMemories（解析后的结构化记忆）两个 TypedDict。",
    ["type-definition", "data-model", "typeddict"], "simple")
add_cls(fp, "ChatMemories", 12, 20, "原始聊天记忆 TypedDict，包含 init_memory、recent_msg、character_card_json 等 7 个字段。", ["type-definition", "data-model"], "simple")
add_cls(fp, "ParsedMemories", 24, 34, "解析后记忆 TypedDict，包含 character_card_examples、behavior_guide_text、user_profile_summary 等 10 个结构化字段。", ["type-definition", "data-model"], "simple")

# ============================================================
# FILE 21: user_profile_service.py
# ============================================================
fp = "FoxChatRAG-python/app/service/chat/user_profile_service.py"
add_node(f"file:{fp}", "file", "user_profile_service.py", fp,
    "用户画像服务，负责从聊天消息中使用 LLM 提取和更新用户画像，支持增量更新和结构验证。",
    ["service", "user-profile", "llm", "extraction"], "moderate")
add_fn(fp, "_build_profile_updater_chain", 65, 89, "构建用户画像更新的 LLM Chain，配置 MemoryJSONInvokeStrategy 和 ChatPromptTemplate。", ["builder", "chain", "llm"], "moderate")
add_fn(fp, "_update_user_profile", 101, 157, "使用 LLM 从最近消息中提取用户画像增量，与现有画像合并后验证结构。", ["service", "update", "llm"], "complex")
add_fn(fp, "update_user_profile_in_summary", 160, 207, "用户画像更新主入口，并行获取现有画像和构建 Chain，然后调用 LLM 更新并保存。", ["service", "entry-point", "async"], "moderate")

# ============================================================
# FILE 22: llm_config_service.py
# ============================================================
fp = "FoxChatRAG-python/app/service/llm_config_service.py"
add_node(f"file:{fp}", "file", "llm_config_service.py", fp,
    "LLM 配置管理服务，提供 LLM 模型配置的 CRUD 操作、连接测试和场景完整性校验，支持按场景（聊天、记忆、摘要等）分组管理多个 LLM 配置。",
    ["service", "config", "llm", "crud"], "complex")
add_fn(fp, "test_llm_connection", 21, 74, "测试 LLM 连接，发送简单请求验证 API Key、Base URL 和模型名称是否有效。", ["service", "test", "connection"], "moderate")
add_fn(fp, "get_llm_configs_batch", 77, 109, "批量获取指定 LLM 的所有场景配置，返回 scenario→config 映射字典。", ["service", "config", "batch-read"], "moderate")
add_fn(fp, "save_llm_config", 112, 171, "保存单条 LLM 配置，支持新增和更新（基于 llm_id+scenario 唯一键）。", ["service", "config", "upsert"], "moderate")
add_fn(fp, "delete_llm_config", 200, 226, "删除指定场景的 LLM 配置。", ["service", "config", "delete"], "simple")
add_fn(fp, "validate_config_count", 229, 252, "校验 LLM 配置完整性，检查是否所有必要场景都已配置。", ["service", "config", "validation"], "moderate")

# ============================================================
# FILE 23: rag/__init__.py
# ============================================================
fp = "FoxChatRAG-python/app/service/rag/__init__.py"
add_node(f"file:{fp}", "file", "__init__.py", fp,
    "RAG 服务包初始化文件，导入并暴露 rag_search_service 和 vector_upload_service 模块。",
    ["barrel", "re-export"], "simple")

# ============================================================
# FILE 24: vector_upload_service.py
# ============================================================
fp = "FoxChatRAG-python/app/service/rag/vector_upload_service.py"
add_node(f"file:{fp}", "file", "vector_upload_service.py", fp,
    "RAG 文件上传服务，处理文件下载、内容摘要和向量化上传到 ChromaDB，支持多种文件格式。",
    ["service", "upload", "rag", "vector"], "moderate")
add_fn(fp, "upload_file", 65, 125, "文件上传主函数，下载文件→加载文档→LLM 摘要→分块→上传 ChromaDB→更新状态。", ["service", "upload", "pipeline"], "complex")

# ============================================================
# FILE 25: util/__init__.py
# ============================================================
fp = "FoxChatRAG-python/app/util/__init__.py"
add_node(f"file:{fp}", "file", "__init__.py", fp,
    "工具包初始化文件，导入并暴露 redis_json_util 和 template_util 模块。",
    ["barrel", "re-export"], "simple")

# ============================================================
# FILE 26: chroma_util.py
# ============================================================
fp = "FoxChatRAG-python/app/util/chroma_util.py"
add_node(f"file:{fp}", "file", "chroma_util.py", fp,
    "ChromaDB 向量数据库工具库，封装向量存储的增删查操作，支持通用文档上传、历史事件批量上传和语义搜索。",
    ["utility", "chroma", "vector-db", "crud"], "complex")
add_fn(fp, "search", 35, 103, "向量相似度搜索，支持元数据过滤、嵌入预计算、空集合探测和结果格式化。", ["search", "vector", "chroma"], "complex")
add_fn(fp, "upload", 113, 136, "通用文档上传，对文档分块后批量写入 ChromaDB，使用 MD5 生成文档 ID。", ["upload", "vector", "chunking"], "moderate")
add_fn(fp, "upload_history_events_batch", 142, 202, "历史事件批量上传，将事件列表转换为 Document 对象并批量写入 ChromaDB，包含丰富的元数据。", ["upload", "batch", "history"], "moderate")
add_fn(fp, "upload_history_event", 205, 266, "单条历史事件上传，构建完整元数据后调用通用 upload 函数。", ["upload", "single", "history"], "moderate")
add_fn(fp, "search_history_events", 269, 309, "历史事件语义搜索，构建元数据过滤条件后调用通用 search 函数。", ["search", "history", "semantic"], "moderate")

# ============================================================
# FILE 27: loader_util.py
# ============================================================
fp = "FoxChatRAG-python/app/util/loader_util.py"
add_node(f"file:{fp}", "file", "loader_util.py", fp,
    "文件加载工具，提供 TXT/CSV/PDF/DOCX/Markdown 等多格式文档加载器，支持元数据增强和标题层级提取。",
    ["utility", "loader", "document", "multi-format"], "moderate")
# No function exceeds 10 lines significantly except load_file which is a simple dispatcher (9 lines)

# ============================================================
# FILE 28: redis_json_util.py
# ============================================================
fp = "FoxChatRAG-python/app/util/redis_json_util.py"
add_node(f"file:{fp}", "file", "redis_json_util.py", fp,
    "Redis JSON 安全写入工具，提供 JSON 值序列化和 RedisJSON SET 命令的安全封装。",
    ["utility", "redis", "json"], "simple")
# Functions are trivial (5 and 2 lines), skip

# ============================================================
# FILE 29: template_util.py
# ============================================================
fp = "FoxChatRAG-python/app/util/template_util.py"
add_node(f"file:{fp}", "file", "template_util.py", fp,
    "模板和文本处理工具，提供 prompt 模板转义、思考标签清除、Markdown 代码块剥离和 JSON 文本提取等功能。",
    ["utility", "template", "text-processing", "json"], "moderate")
add_fn(fp, "escape_template", 9, 35, "转义 prompt 模板中的花括号，将非变量占位符的 {} 替换为 {{}}，防止 LangChain 模板解析报错。", ["utility", "template", "escape"], "moderate")
add_fn(fp, "strip_all_tags", 60, 80, "清除文本中所有标签（思考标签、动作标签等），返回纯文本内容。", ["utility", "text", "cleanup"], "simple")
add_fn(fp, "strip_think_only", 83, 96, "仅清除思考标签，保留其他标签内容。", ["utility", "text", "cleanup"], "simple")
add_fn(fp, "extract_json_text", 99, 131, "从原始文本中提取 JSON 字符串，支持 Markdown 代码块和嵌套括号匹配。", ["utility", "json", "extraction"], "moderate")
add_fn(fp, "try_parse_json", 134, 167, "安全 JSON 解析，依次尝试直接解析、提取 JSON 文本解析和正则清理后解析，全部失败返回 None。", ["utility", "json", "parsing"], "moderate")

# ============================================================
# IMPORT EDGES
# ============================================================
for src_fp, targets in batchImportData.items():
    for tgt_fp in targets:
        add_edge(f"file:{src_fp}", f"file:{tgt_fp}", "imports", 0.7)

# ============================================================
# EXPORT EDGES for significant exported items
# ============================================================
export_edges = [
    # json_parser.py
    ("FoxChatRAG-python/app/service/chat/common/json_parser.py", "safe_json_parse"),
    # similarity.py
    ("FoxChatRAG-python/app/service/chat/common/similarity.py", "calc_jaccard_similarity"),
    ("FoxChatRAG-python/app/service/chat/common/similarity.py", "calc_word_overlap_ratio"),
    # emotion_classifier.py
    ("FoxChatRAG-python/app/service/chat/emotion_classifier.py", "classify_emotion"),
    ("FoxChatRAG-python/app/service/chat/emotion_classifier.py", "classify_and_update_emotion"),
    # graph.py
    ("FoxChatRAG-python/app/service/chat/graph/graph.py", "build_main_graph"),
    # nodes.py
    ("FoxChatRAG-python/app/service/chat/graph/nodes.py", "pre_flight"),
    ("FoxChatRAG-python/app/service/chat/graph/nodes.py", "parse_memory"),
    ("FoxChatRAG-python/app/service/chat/graph/nodes.py", "classify_intent_node"),
    ("FoxChatRAG-python/app/service/chat/graph/nodes.py", "retrieve"),
    ("FoxChatRAG-python/app/service/chat/graph/nodes.py", "invoke_llm"),
    ("FoxChatRAG-python/app/service/chat/graph/nodes.py", "trigger_summary"),
    # state.py
    ("FoxChatRAG-python/app/service/chat/graph/state.py", "ChatState"),
    # history_event_retrieval_service.py
    ("FoxChatRAG-python/app/service/chat/history_event_retrieval_service.py", "retrieve_history_events_v2"),
    ("FoxChatRAG-python/app/service/chat/history_event_retrieval_service.py", "format_history_events"),
    # llm_invoke_service.py
    ("FoxChatRAG-python/app/service/chat/llm_invoke_service.py", "invoke_llm_with_retrieval"),
    ("FoxChatRAG-python/app/service/chat/llm_invoke_service.py", "stream_llm_with_retrieval"),
    ("FoxChatRAG-python/app/service/chat/llm_invoke_service.py", "search_relevant_memories"),
    # memory_parser.py
    ("FoxChatRAG-python/app/service/chat/memory_parser.py", "parse_character_card"),
    ("FoxChatRAG-python/app/service/chat/memory_parser.py", "parse_core_anchor"),
    ("FoxChatRAG-python/app/service/chat/memory_parser.py", "build_static_anchors"),
    ("FoxChatRAG-python/app/service/chat/memory_parser.py", "parse_user_profile"),
    ("FoxChatRAG-python/app/service/chat/memory_parser.py", "parse_memory_bank"),
    ("FoxChatRAG-python/app/service/chat/memory_parser.py", "parse_current_state"),
    # memory_summary_service.py
    ("FoxChatRAG-python/app/service/chat/memory_summary_service.py", "async_summary_msg_parallel"),
    ("FoxChatRAG-python/app/service/chat/memory_summary_service.py", "trigger_summary_with_counter"),
    # memory_upload_service.py
    ("FoxChatRAG-python/app/service/chat/memory_upload_service.py", "chat_init"),
    # prompt_payload_builder.py
    ("FoxChatRAG-python/app/service/chat/prompt_payload_builder.py", "PromptPayload"),
    ("FoxChatRAG-python/app/service/chat/prompt_payload_builder.py", "build_prompt_payload"),
    # session_lock.py
    ("FoxChatRAG-python/app/service/chat/session_lock.py", "acquire_session_lock"),
    ("FoxChatRAG-python/app/service/chat/session_lock.py", "release_session_lock"),
    # state_manager.py
    ("FoxChatRAG-python/app/service/chat/state_manager.py", "get_current_state"),
    ("FoxChatRAG-python/app/service/chat/state_manager.py", "update_current_state"),
    ("FoxChatRAG-python/app/service/chat/state_manager.py", "increment_round_counter"),
    ("FoxChatRAG-python/app/service/chat/state_manager.py", "get_current_round"),
    # base_strategy.py
    ("FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "LLMInvokeStrategy"),
    ("FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "ChatInvokeStrategy"),
    ("FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "MemoryInvokeStrategy"),
    ("FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "SummaryInvokeStrategy"),
    ("FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "ExtractionInvokeStrategy"),
    ("FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "EmotionInvokeStrategy"),
    ("FoxChatRAG-python/app/service/chat/strategy/base_strategy.py", "format_model_name"),
    # streaming_tag_parser.py
    ("FoxChatRAG-python/app/service/chat/streaming_tag_parser.py", "StreamingTagParser"),
    ("FoxChatRAG-python/app/service/chat/streaming_tag_parser.py", "StreamToken"),
    # timer_scheduler.py
    ("FoxChatRAG-python/app/service/chat/timer_scheduler.py", "timer_scheduler"),
    ("FoxChatRAG-python/app/service/chat/timer_scheduler.py", "reset_timer"),
    ("FoxChatRAG-python/app/service/chat/timer_scheduler.py", "trigger_summary_with_counter"),
    # types.py
    ("FoxChatRAG-python/app/service/chat/types.py", "ChatMemories"),
    ("FoxChatRAG-python/app/service/chat/types.py", "ParsedMemories"),
    # user_profile_service.py
    ("FoxChatRAG-python/app/service/chat/user_profile_service.py", "update_user_profile_in_summary"),
    # llm_config_service.py
    ("FoxChatRAG-python/app/service/llm_config_service.py", "get_llm_configs_batch"),
    ("FoxChatRAG-python/app/service/llm_config_service.py", "test_llm_connection"),
    ("FoxChatRAG-python/app/service/llm_config_service.py", "save_llm_config"),
    ("FoxChatRAG-python/app/service/llm_config_service.py", "save_llm_configs_batch"),
    # vector_upload_service.py
    ("FoxChatRAG-python/app/service/rag/vector_upload_service.py", "upload_file"),
    # chroma_util.py
    ("FoxChatRAG-python/app/util/chroma_util.py", "search"),
    ("FoxChatRAG-python/app/util/chroma_util.py", "upload"),
    ("FoxChatRAG-python/app/util/chroma_util.py", "upload_history_events_batch"),
    ("FoxChatRAG-python/app/util/chroma_util.py", "upload_history_event"),
    ("FoxChatRAG-python/app/util/chroma_util.py", "search_history_events"),
    ("FoxChatRAG-python/app/util/chroma_util.py", "delete"),
    # template_util.py
    ("FoxChatRAG-python/app/util/template_util.py", "escape_template"),
    ("FoxChatRAG-python/app/util/template_util.py", "strip_all_tags"),
    ("FoxChatRAG-python/app/util/template_util.py", "strip_think_only"),
    ("FoxChatRAG-python/app/util/template_util.py", "try_parse_json"),
    ("FoxChatRAG-python/app/util/template_util.py", "extract_json_text"),
]

for fp, name in export_edges:
    nid = f"function:{fp}:{name}"
    if nid in [n["id"] for n in nodes]:
        add_edge(f"file:{fp}", nid, "exports", 0.8)
    else:
        nid = f"class:{fp}:{name}"
        if nid in [n["id"] for n in nodes]:
            add_edge(f"file:{fp}", nid, "exports", 0.8)

# ============================================================
# WRITE OUTPUT - SPLIT IF NEEDED
# ============================================================
node_count = len(nodes)
edge_count = len(edges)
print(f"Total nodes: {node_count}, Total edges: {edge_count}")

if node_count <= 60 and edge_count <= 120:
    with open("E:/WorkSpace/ProjectCode/.understand-anything/intermediate/batch-3.json", "w", encoding="utf-8") as f:
        json.dump({"nodes": nodes, "edges": f}, f, indent=2, ensure_ascii=False)
    print("Single file written")
else:
    import math
    parts = math.ceil(max(node_count / 60, edge_count / 120))
    print(f"Splitting into {parts} parts")

    # Sort files alphabetically
    file_paths = sorted(set(n["filePath"] for n in nodes))
    chunk_size = math.ceil(len(file_paths) / parts)

    os.makedirs("E:/WorkSpace/ProjectCode/.understand-anything/intermediate", exist_ok=True)

    for part_idx in range(parts):
        start = part_idx * chunk_size
        end = min(start + chunk_size, len(file_paths))
        part_files = set(file_paths[start:end])

        part_nodes = [n for n in nodes if n["filePath"] in part_files]
        part_node_ids = set(n["id"] for n in part_nodes)
        part_edges = [e for e in edges if e["source"] in part_node_ids]

        fname = f"E:/WorkSpace/ProjectCode/.understand-anything/intermediate/batch-3-part-{part_idx+1}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump({"nodes": part_nodes, "edges": part_edges}, f, indent=2, ensure_ascii=False)
        print(f"Part {part_idx+1}: {len(part_nodes)} nodes, {len(part_edges)} edges -> {fname}")
