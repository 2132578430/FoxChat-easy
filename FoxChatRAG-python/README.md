# FoxChatRAG (狐狸聊天室 RAG 后端)

Ciallo~ 欢迎来到 FoxChatRAG 的后端世界！本项目是一个基于 **FastAPI** 和 **LangChain** 构建的高性能 RAG (Retrieval-Augmented Generation) 知识库系统。

它专门为 **FoxChat** 即时通讯应用提供强大的文档处理、语义检索及大模型问答能力，并实现了**多阶段记忆架构优化**。

---

## 🌟 核心特性 (Core Features)

- **🚀 高性能异步框架**: 基于 FastAPI 构建，全面支持异步 IO。
- **📚 多格式文档支持**: 支持 `.docx`, `.pdf`, `.txt`, `.csv` 等多种格式的自动加载与切分。
- **🔍 两阶段检索架构**:
  - **初筛**: 使用 Chroma 向量数据库进行语义相似度搜索。
  - **精筛**: 集成 `FlashRank` (ms-marco-MiniLM-L-12-v2) 进行 Cross-Encoder 重排序。
- **🤖 本地模型集成**: 深度对接 Ollama，支持 Llama3、Qwen 等本地大模型。
- **🧠 记忆架构优化**:
  - **阶段2**: 当前状态容器 (`current_state`) + 时间节点运行时 (`time_node`)
  - **阶段3**: 总结候选四路分流 (A2 / 状态 / 时间节点 / 历史事件)
  - 支持跨日跟进、情绪状态延续、用户边界记忆
- **📩 异步处理架构**: 集成 RabbitMQ 消息队列，实现文档上传与向量化的解耦处理。
- **🛠️ 完善的异常处理**: 仿 Java `@RestControllerAdvice` 风格的全局异常捕获机制。

---

## 🧠 记忆架构 (Memory Architecture)

### 分层设计

```text
A. 常驻稳定层
   A1. 静态锚点: soul / core_anchor / character_card
   A2. 稳定画像与关键边界: user_profile / 长期禁忌 / 高优先级边界

B. 当前工作状态层
   - emotion（情绪）
   - relation_state（关系态势）
   - current_focus（当前焦点）
   - unfinished_items（未完成事项）
   - interaction_mode（互动方式）

T. 时间节点层（运行时激活）
   - 未来跟进事项
   - 到期自动激活

C. 历史事件检索层
   - 过去重要事件（memory_bank）
   - Chroma 对话总结检索

D. 最近对话窗口
   - 最近 4~6 轮原始消息
```

### 阶段3候选分流

每 9 轮总结触发时，系统会将对话内容分流到四个候选通道：

```text
对话总结文本
    ↓
候选路由器（rule-based）
    ↓
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ A2候选     │ │ 状态候选   │ │ 时间候选   │ │ 事件候选   │
│ (边界/偏好)│ │ (情绪/焦点)│ │ (明天/下周)│ │ (历史事实) │
└────────────┘ └────────────┘ └────────────┘ └────────────┘
    ↓              ↓              ↓              ↓
A2容器        current_state   time_node      memory_bank
(立即/待证)                    (到期激活)     (去重入库)
```

---

## 🏗️ 项目结构 (Project Structure)

```text
FoxChatRAG-python/
├── app/
│   ├── api/                    # 路由层：定义 RESTful 接口
│   ├── service/chat/           # 业务层：核心对话服务
│   │   ├── chat_msg_service.py         # 对话主流程入口
│   │   ├── memory_summary_service.py   # 记忆总结与候选分流
│   │   ├── candidate_router_service.py # 阶段3候选路由
│   │   ├── a2_candidate_service.py     # A2边界提取
│   │   ├── state_manager.py            # 当前状态容器管理
│   │   ├── time_node_service.py        # 时间节点运行时
│   │   ├── runtime_state_extractor.py  # runtime状态提取
│   │   ├── emotion_classifier.py       # 情绪分类
│   │   ├── user_profile_service.py     # 用户画像更新
│   │   ├── history_event_retrieval_service.py # 历史事件检索（阶段4）
│   │   └── prompt_payload_builder.py   # Prompt构建器（阶段6）
│   ├── core/
│   │   ├── prompts/            # Prompt 模板
│   │   │   ├── soul.md                 # 角色灵魂定义
│   │   │   ├── memory_event_extractor.md # 历史事件提取
│   │   │   ├── chat_system.md            # 对话主系统 Prompt
│   │   │   ├── memory_summary.md         # 对话总结 Prompt
│   │   │   ├── memory_event_extractor.md # 历史事件提取 Prompt
│   │   │   ├── memory_bank_compress.md   # Memory Bank 压缩 Prompt
│   │   │   ├── emotion_classifier.md     # 情绪分类 Prompt
│   │   │   ├── focus_extractor.md        # 焦点提取 Prompt
│   │   │   └── soul.md                   # 角色灵魂定义
│   │   ├── llm_model/          # LLM 模型管理
│   │   ├── mq/                 # RabbitMQ 消息队列
│   │   └── db/                 # 数据库连接（Redis、MySQL）
│   ├── schemas/                # 数据模型：Pydantic 模型定义
│   │   ├── current_state.py    # 当前状态容器 Schema
│   │   ├── time_node.py        # 时间节点 Schema
│   │   ├── memory_event.py     # 历史事件 Schema
│   │   └── summary_candidate.py # 候选数据结构
│   ├── common/constant/        # 公共模块：常量定义
│   ├── exception/              # 异常处理
│   ├── util/                   # 工具类（Chroma、文本处理）
│   └── models/                 # ORM 模型
├── scripts/                    # 测试/验证脚本
│   ├── test_history_event_retrieval_service_compile.py
│   ├── verify_history_event_indexing.py
│   └── memory_validation_runner.py
├── docs/                       # 设计文档与审计报告
├── main.py                     # 入口文件
└── README.md                   # 项目说明文档
```

---

## 🛠️ 技术栈 (Tech Stack)

- **语言**: Python 3.12+
- **Web 框架**: FastAPI
- **RAG 框架**: LangChain
- **向量数据库**: ChromaDB
- **缓存**: Redis (RedisJSON)
- **消息队列**: RabbitMQ (aio-pika)
- **模型推理**: DeepSeek / Ollama
- **重排序**: FlashRank
- **日志记录**: Loguru

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备
确保已安装 Python 3.12+ 并配置好虚拟环境。

### 2. 依赖安装
```bash
pip install -r requirements.txt
```

### 3. 服务启动
```bash
# 启动 Redis（需要 RedisJSON 模块）
# 启动 ChromaDB
# 启动 RabbitMQ（可选）

# 启动后端服务
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 📝 开发指南 (Development Notes)

### 记忆架构实施进度

| 阶段 | 状态 | 功能 |
|------|------|------|
| 阶段0 | ✅ 完成 | 基线建立 |
| 阶段1 | ✅ 完成 | 对象契约定义 |
| 阶段2 | ✅ 完成 | current_state容器 + time_node运行时 |
| 阶段3 | ✅ 完成 | 总结候选四路分流 |
| 阶段4 | ⚠️ 基本完成 | History Retrieval V1（BM25 + 向量 + Rerank） |
| 阶段5 | ⚠️ 基本完成 | Prompt Layout V2 + A2边界注入 + 未完成事项时间上下文 |
| 阶段6 | ⚠️ 基本完成 | Payload Builder 统一构建 + 空块省略 + 去重 |

### 关键文件说明

**核心服务**
- **`chat_msg_service.py`**: 对话主入口，负责记忆获取、LLM调用、后台任务触发
- **`memory_summary_service.py`**: 每9轮触发总结，执行候选分流与写回
- **`state_manager.py`**: 管理 Redis 中的 current_state 存储，支持覆盖与过期
- **`time_node_service.py`**: 时间节点创建、到期检查、激活逻辑
- **`candidate_router_service.py`**: 阶段3核心分流器，规则优先路由

**检索与构建（阶段4-6）**
- **`history_event_retrieval_service.py`**: 历史事件检索，BM25 + 向量混合检索 + Rerank
- **`prompt_payload_builder.py`**: 统一 Prompt Payload 构建，支持去重、冲突优先级、空块省略
- **`runtime_state_extractor.py`**: LLM 返回状态提取，更新 current_state

### 全局异常处理
项目使用 `BusinessException` 配合 `MsgStatusConstant` 进行业务错误管理。所有异常都会被 `GlobalExceptionHandler` 捕获并返回统一格式的 JSON。

---

## 📚 参考文档

详细设计文档见 `.opencode/plans/1777189857003-curious-otter.md`

---