# FoxChat (狐狸聊天室) - 前端

本项目是 **FoxChat** 项目的 Vue 3 前端 + Electron 桌面客户端，提供即时通讯和 RAG 知识库功能。

---

## 1. 技术栈 (Tech Stack)

- **前端框架**: Vue 3 (Composition API `<script setup>`)
- **构建工具**: Vite 7
- **跨平台壳**: Electron 40
- **UI 组件库**: Element Plus
- **网络通信**:
  - **HTTP**: Axios (封装于 `src/utils/request.js`)
  - **WebSocket**: 原生 WebSocket + Protobuf (序列化)
- **数据处理**: Protobuf.js, Sass, Vue-Router, Vue-Cropper

---

## 2. 环境配置 (Environment Configuration)

项目根目录下的 `.env` 文件用于配置不同环境的服务地址：

| 变量名 | 说明 | 示例值 |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | 后端 HTTP 接口基地址 | `http://localhost:12000` |
| `VITE_WS_BASE_URL` | WebSocket 服务基地址 | `ws://localhost:13000` |
| `VITE_OSS_BASE_URL` | 对象存储 (OSS) 基地址 | `http://localhost:9000` |

---

## 3. 前后端 HTTP 接口规范 (Standard HTTP Response)

所有普通 HTTP 请求必须遵循以下响应格式：

```java
@Data
public class R<T> {
    private Integer code; // 响应码 (1000 为成功)
    private String msg;    // 错误信息或提示
    private T data;        // 业务响应数据
}
```

- **成功标识**: `code === 1000`
- **错误处理**: 若 `code !== 1000`，前端 `request.js` 会自动弹出 `msg` 提示并抛出 Promise 异常。
- **数据解包**: 拦截器会自动提取 `data` 字段返回给调用方。

---

## 4. WebSocket 通信协议 (WebSocket & Protobuf)

本项目使用 WebSocket 进行实时通讯，采用 **自定义二进制头 + Protobuf 消息体** 的设计。

### 4.1 二进制自定义头 (16 Bytes)

| 字段 (Field) | 长度 | 说明 |
| :--- | :--- | :--- |
| Magic Number | 4 bytes | 固定值 `0xCAFEBABE` |
| Version | 1 byte | 当前版本 `1` |
| Serialization | 1 byte | `1` (Protobuf) |
| MsgType | 2 bytes | 消息类型 (见下文) |
| Data Length | 4 bytes | Protobuf Body 长度 |
| Reserved | 4 bytes | 保留字段 (0) |

### 4.2 消息类型定义 (MsgType)

- `1101`: 私聊消息 (Private Chat)
- `1201`: 群聊消息 (Group Chat)
- `1102`: 消息签收 (Message Sign)
- `1103`: 心跳包 (Heartbeat)
- `1104`: 添加好友申请
- `1105`: 收到好友申请通知
- `1106`: 好友上线通知
- `1107`: 好友下线通知

---

## 5. 核心功能模块 (Core Features)

### 5.1 即时通讯 (Chat)
- 支持私聊与群聊。
- 采用 Protobuf 进行高效序列化。
- 消息通过 WebSocket 实时推送。

### 5.2 狐狸 RAG (Knowledge Base)
- **入口**: 左侧侧边栏“狐狸 RAG”按钮。
- **功能**: 上传文件到知识库。
- **接口**: `POST /rag/uploadVector`
- **限制**: 单个文件 100MB 以内，支持格式：`.pdf`, `.doc`, `.docx`, `.txt`, `.md`。
- **实现**: 使用 `el-upload` 的拖拽模式。

---

## 6. 开发与运行 (Scripts)

```bash
# 安装依赖
npm install

# 启动 Web 开发环境
npm run dev

# 启动 Electron 开发环境
npm run electron:dev

# 打包 Web 项目
npm run build

# 打包 Electron 应用 (Windows)
npm run electron:build
```

---

## 7. IDE 支持 (IDE Support)

建议使用 **VS Code** 或 **Trae**，并安装 **Volar** 扩展以获得最佳的 Vue 3 开发体验。
