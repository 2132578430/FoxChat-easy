# FoxChat 🦊

一个集成 **AI 对话记忆系统** 的即时通讯平台。Java 负责核心 IM 架构，Python 端实现多阶段记忆与状态管理。

---

## 🌟 项目定位

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FoxChat                                       │
├──────────────────┬────────────────────────┬─────────────────────────────┤
│    FoxChat-vue   │     FoxChat-java       │     FoxChatRAG-python       │
│    (前端/桌面端)  │    (IM 核心后端)        │    (AI 记忆对话服务)         │
└──────────────────┴────────────────────────┴─────────────────────────────┘
         │                    │                          │
         └────────────────────┴──────────────────────────┘
                              │
                 ┌────────────┼────────────┐
                 │   MySQL    │   Redis    │  ← 持久化 + 缓存
                 │            │   RabbitMQ │  ← 消息队列
                 │            │   Minio    │  ← 文件存储
                 └────────────┴────────────┘
```

**核心分工**：
- **Java 端**：用户体系、好友关系、群组管理、WebSocket 长连接、Protobuf 二进制协议
- **Python 端**：AI 对话、多阶段记忆架构、RAG 知识库、情绪状态管理

---

## 🧠 AI 记忆架构（Python 端核心）

这是 FoxChat 的核心亮点——一个完整的 **多阶段记忆系统**，让 AI 具备长期记忆和上下文理解能力。

### 分层记忆设计

```text
┌─────────────────────────────────────────────────────────────────┐
│                     A. 常驻稳定层                                │
├─────────────────────────────────────────────────────────────────┤
│  A1. 静态锚点    │  soul / core_anchor / character_card          │
│  A2. 稳定画像    │  user_profile / 长期禁忌 / 高优先级边界        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     B. 当前工作状态层                            │
├─────────────────────────────────────────────────────────────────┤
│  emotion          │  情绪状态（happy/sad/anger...）              │
│  relation_state   │  关系态势（亲近/疏远/紧张...）               │
│  current_focus    │  当前对话焦点                                │
│  unfinished_items │  未完成事项（带过期机制）                     │
│  interaction_mode │  互动方式（正式/随意/亲密...）               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     T. 时间节点层（运行时激活）                   │
├─────────────────────────────────────────────────────────────────┤
│  未来跟进事项    │  "明天提醒你..." / "下周三开会"               │
│  到期自动激活    │  时间到达后自动注入对话上下文                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     C. 历史事件检索层                            │
├─────────────────────────────────────────────────────────────────┤
│  memory_bank      │  过去重要事件（结构化存储）                   │
│  Chroma 检索      │  BM25 + 向量 + Rerank 混合检索               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     D. 最近对话窗口                              │
├─────────────────────────────────────────────────────────────────┤
│  recent_messages  │  最近 4~6 轮原始消息（Redis List）           │
└─────────────────────────────────────────────────────────────────┘
```

### 记忆流水线

每 9 轮对话触发一次记忆总结，将对话内容分流到四个候选通道：

```text
                    对话总结文本
                         ↓
                    候选路由器（规则优先）
                         ↓
    ┌────────────┬────────────┬────────────┬────────────┐
    │ A2候选     │ 状态候选   │ 时间候选   │ 事件候选   │
    │ (边界/偏好)│ (情绪/焦点)│ (明天/下周)│ (历史事实) │
    └────────────┴────────────┴────────────┴────────────┘
         ↓              ↓              ↓              ↓
    A2容器        current_state   time_node      memory_bank
   (立即写入)     (轮数过期)      (到期激活)     (去重入库)
```

### 核心服务组件

| 服务 | 职责 | 文件 |
|:-----|:-----|:-----|
| **chat_msg_service** | 对话主入口，协调记忆获取、LLM 调用、后台任务 | `chat_msg_service.py` |
| **memory_summary_service** | 每 9 轮触发总结，执行候选分流与写回 | `memory_summary_service.py` |
| **state_manager** | 管理 current_state 存储，支持轮数过期与覆盖 | `state_manager.py` |
| **time_node_service** | 时间节点创建、到期检查、自动激活 | `time_node_service.py` |
| **history_event_retrieval** | BM25 + 向量 + Rerank 混合检索 | `history_event_retrieval_service.py` |
| **prompt_payload_builder** | 统一 Prompt 构建，支持去重、冲突优先级 | `prompt_payload_builder.py` |

---

## 🏗️ Java 核心架构

FoxChat-java 负责 IM 系统的核心能力：

### 模块划分

```text
foxChat-java/
├── foxChat-web/        # Controller 层，RESTful API
├── foxChat-service/    # Service 业务层
├── foxChat-netty/      # Netty WebSocket 长连接服务
├── foxChat-common/     # 公共模块（工具类、常量）
└── foxChat-pojo/       # 实体类、DTO
```

### 通信协议

**WebSocket 二进制协议 (16 Bytes)**

| Magic (4B) | Ver (1B) | Serial (1B) | MsgType (2B) | Length (4B) | Reserved (4B) |
|:-----------|:---------|:------------|:-------------|:------------|:--------------|
| `0xCAFEBABE` | `1` | `1` (PB) | `1101/1201...` | Body Size | `0x00` |

**MsgType 定义**

| 类型 | 说明 |
|:-----|:-----|
| 1101 | 私聊消息 |
| 1201 | 群聊消息 |
| 1102 | 消息签收 |
| 1103 | 心跳 |
| 1104 | 添加好友申请 |
| 1105 | 好友申请通知 |
| 1106/1107 | 好友上/下线通知 |

---

## 🛠️ 技术栈

| 模块 | 技术 | 端口 |
|:-----|:-----|:-----|
| **FoxChat-vue** | Vue 3 + Vite + Electron | 5173 (Web) |
| **FoxChat-java** | Spring Boot 3 + Netty + MySQL | 12000 (HTTP), 13000 (WebSocket) |
| **FoxChatRAG-python** | FastAPI + LangChain + ChromaDB | 8000 |

### 中间件

- **MySQL 8.0** - 持久化数据
- **Redis** - 缓存、会话、心跳（需 RedisJSON 模块）
- **RabbitMQ** - 消息队列（异步向量处理）
- **Minio** - 对象存储（文件/图片）

---

## 🚀 快速启动

### 1. 启动中间件

```bash
docker-compose up -d
```

### 2. 启动后端 (FoxChat-java)

```bash
cd FoxChat-java
./gradlew bootRun
```

### 3. 启动 RAG 服务 (FoxChatRAG-python)

```bash
cd FoxChatRAG-python
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. 启动前端 (FoxChat-vue)

```bash
cd FoxChat-vue
npm install
npm run dev
```

### 5. 打包 Electron 桌面端

```bash
cd FoxChat-vue
npm run electron:build
```

---

## 📂 项目结构

```text
FoxChat/
├── FoxChat-vue/           # Vue 3 前端 + Electron 桌面端
│   ├── src/
│   │   ├── api/          # API 接口
│   │   ├── components/   # 组件
│   │   ├── views/        # 页面视图
│   │   ├── utils/        # 工具函数
│   │   └── proto/        # Protobuf 定义
│   ├── electron/         # Electron 主进程
│   └── README.md
│
├── FoxChat-java/         # Spring Boot 后端（IM 核心）
│   ├── foxChat-web/      # Controller 层
│   ├── foxChat-service/  # Service 业务层
│   ├── foxChat-netty/    # Netty WebSocket 服务
│   ├── foxChat-common/   # 公共模块
│   ├── foxChat-pojo/     # 实体类
│   └── README.md
│
├── FoxChatRAG-python/    # FastAPI RAG 服务（AI 记忆）
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── service/      # 业务逻辑（记忆、状态、时间节点）
│   │   ├── core/         # 核心配置（Prompts、DB、LLM）
│   │   ├── schemas/      # 数据模型定义
│   │   ├── common/       # 常量定义
│   │   └── exception/    # 异常处理
│   ├── scripts/          # 测试脚本
│   ├── docs/             # 设计文档
│   ├── store/            # Chroma 向量库（本地）
│   └── README.md
│
├── docker-compose.yml    # 中间件配置
└── README.md             # 本文件
```

---

## 🔐 敏感配置

以下文件包含密钥、密码等敏感信息，**请勿提交至 Git**（已列入 `.gitignore`）：

| 文件 | 说明 |
|------|------|
| `FoxChatRAG-python/.env` | LLM API Key、MySQL/Redis/RabbitMQ 密码 |
| `FoxChat-java/deploy/.env` | MySQL/Redis 密码 |
| `FoxChat-java/**/application-local.yml` | 数据库密码、JWT 密钥、MinIO、邮件授权码 |
| `FoxChat-vue/.env` | 本地 API 地址 |

首次配置时，参考各模块下的 `.env.example` 文件复制并填写实际值。

---

## 🔧 相关文档

- [FoxChat-vue 前端文档](./FoxChat-vue/README.md)
- [FoxChat-java 后端文档](./FoxChat-java/README.md)
- [FoxChatRAG-python RAG 文档](./FoxChatRAG-python/README.md)
