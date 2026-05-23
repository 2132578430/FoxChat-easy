# FoxChat 🦊
它不仅仅是一个聊天工具，更是一个集成了向量检索能力的“聪明”伙伴，能够通过你上传的文档为你提供精准的 AI 问答支持！

---

## 🌟 项目亮点 (Features)

- **🚀 极致性能**:
  - **Netty 核心**: 采用非阻塞 IO，轻松应对高并发连接。
  - **自定义二进制协议**: 16 字节精简头部，结合 **Protobuf** 序列化，消息传输快如闪电。
  - **多线程加速**: 深度优化文件上传逻辑，采用并行流 (Parallel Stream) 实现 MiniO 极速批量上传。

- **🧠 RAG 智能知识库**:
  - **批量 Upsert 逻辑**: 智能识别重复文件，实现“存在即更新，不存在即添加”的丝滑体验。
  - **异步数据富化**: 采用 RabbitMQ 削峰填谷，后台自动完成文档向量化。
  - **内存关联优化**: 检索结果自动匹配数据库文件名，让 AI 回答不再冷冰冰。

- **💬 丰富社交体验**:
  - **私聊 & 群聊**: 全功能支持，包含消息签收、在线状态实时推送（上线/下线）。
  - **好友/群组管理**: 完善的申请、审批流程，支持历史消息同步。

- **🔒 稳如泰山**:
  - **多维度安全**: Spring Security + JWT 双重保护，敏感操作无忧。
  - **分布式存储**: Minio 存储大文件，Redis 维护实时状态与心跳。

---

## 🛠️ 技术栈 (Tech Stack)

| 维度 | 技术选型 |
| :--- | :--- |
| **核心框架** | Spring Boot 3.5.10 (JDK 17) |
| **即时通讯** | Netty 4.1.x + WebSocket + Protobuf 3 |
| **数据库** | MySQL 8.0 + MyBatis Plus |
| **缓存/队列** | Redis + RabbitMQ |
| **文件存储** | Minio (支持批量、并行上传) |
| **安全/工具** | Spring Security, JJWT, FastJSON2, Lombok |

---

## 📂 核心模块 (Module Structure)

```text
com.bedfox.common
├── config          # ⚙️ 核心配置 (Security, Redis, RabbitMQ, ThreadPool)
├── netty           # ⚡ Netty 服务核心 (Server, Decoder, Encoder)
├── handler         # 🎯 业务逻辑处理器 (私聊、群聊、签收、心跳)
├── service         # 💼 业务接口 (RAG, File, User, Friend, Group)
│   └── impl        # 💡 深度优化的业务实现 (包含 Upsert 逻辑)
├── util            # 🛠️ 全能工具类 (MinioUtil, JwtUtil, MqUtil)
├── domain          # 📝 数据库实体 (RagFile, ChatMsg, Users 等)
└── vo/dto          # 📦 数据传输与展示对象
```

---

## 🚀 快速上手 (Getting Started)

### 1. 环境准备
- **JDK 17+** (推荐使用 GraalVM 或 OpenJDK)
- **MySQL 8.0**
- **Redis 6.x+**
- **RabbitMQ** (需开启延时队列插件或普通模式)
- **Minio** (需预先创建 Bucket)

### 2. 配置文件
修改 `src/main/resources/application.yaml`：
- 配置数据库连接、Redis 地址、RabbitMQ 凭据。
- **重点**: 配置 Minio 的 `endpoint` 和 `public-endpoint`，确保文件路径可访问。

### 3. 运行项目
```bash
./gradlew bootRun
```
- **Netty 端口**: `13000` (WebSocket + Protobuf)
- **API 端口**: `12000` (RESTful API)

---

## 📜 通信协议 (Protocol Detail)

### 1. 消息头 (Binary Header - 16 Bytes)
| Magic (4B) | Version (1B) | Serial (1B) | MsgType (2B) | Length (4B) | Reserved (4B) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0xCAFEBABE` | `0x01` | `0x01` (PB) | `1101/1201...` | `Body Size` | `0x00` |

### 2. 消息类型 (MsgType)
- `1101`: 私聊消息 (Private)
- `1201`: 群聊消息 (Group)
- `1102`: 消息签收 (Ack)
- `1103`: 心跳探测 (Ping/Pong)
- `1104/1105`: 好友申请与通知

---