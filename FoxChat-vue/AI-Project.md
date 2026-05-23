# FoxChat (狐狸 RAG) 项目介绍

## 1. 项目概述
**项目名称**：FoxChat (狐狸 RAG)
**项目用途**：一个集成实时通讯与 AI 知识库 (RAG) 的全栈聊天系统。支持高效的私聊、群聊，并具备强大的 AI 模型对话与文档向量化查询功能（RAG）。

## 2. 技术栈
- **前端框架**：Vue 3 (Composition API)
- **构建工具**：Vite 7
- **UI 组件库**：Element Plus
- **通讯协议**：WebSocket (WS)
- **序列化方案**：Protobuf (自定义 16 字节二进制头 + Protobuf Body)
- **网络请求**：Axios (支持请求/响应拦截器)
- **跨端支持**：Electron (可选/内置支持)
- **样式处理**：Sass / CSS Variables
- **其他工具**：Snowflake ID (分布式唯一 ID)、Vue Cropper (头像剪裁)

## 3. 整体架构与目录结构

### 3.1 核心架构
项目采用**插件化**与**分层设计**：
- **API 层**：统一管理 HTTP 请求，通过 Axios 拦截器处理 Token 注入与全局错误提示。
- **Proto 层**：通过 Protobuf 定义消息协议，实现高效、省流量的二进制数据传输。
- **Utils 层**：封装底层逻辑，包括雪花 ID 生成、二进制协议编解码、WS 心跳维护等。
- **Views 层**：采用 Vue 3 单文件组件 (SFC) 构建页面，逻辑高度复用。

### 3.2 目录结构
```text
src/
├── api/          # 接口定义 (auth, friend, group, message, user)
├── assets/       # 静态资源 (图片、图标)
├── components/   # 公用组件 (头像剪裁、全局弹窗等)
├── proto/        # 协议定义 (.proto 文件及生成的 .js 编解码器)
├── router/       # 路由配置
├── utils/        # 工具函数 (protocol.js 二进制转换, request.js 请求封装, snowflake.js)
├── views/        # 业务页面 (Home 主界面, Login 登录, Register 注册)
├── App.vue       # 根组件
└── main.js       # 入口文件
```

## 4. 编码规范与风格指导

### 4.1 命名风格
- **变量与函数**：采用 `camelCase` (小驼峰) 命名。
  - 示例：`const messageList = ref([]);`, `function sendMessage() {}`
- **组件命名**：采用 `PascalCase` (大驼峰) 命名。
  - 示例：`AvatarCropper.vue`, `Home.vue`
- **CSS 类名**：采用 `kebab-case` (短横线) 命名。
  - 示例：`.chat-area`, `.friend-item`

### 4.2 编码准则
- **Vue 3 风格**：强制使用 `<script setup>` 语法糖，充分利用组合式 API。
- **WebSocket 交互**：所有即时消息必须走二进制协议，消息类型需严格匹配 `MsgType` (如 1101 为私聊, 1102 为签收)。
- **响应式处理**：优先使用 `ref` 处理基础类型和数组，使用 `reactive` 处理复杂的对象结构。
- **错误处理**：所有的 API 请求应包含 `try...catch` 块，并使用 `ElMessage` 给用户友好的反馈。

### 4.3 注释要求
- **文件头**：重要业务文件应简述其功能。
- **复杂逻辑**：在涉及二进制位运算、WS 重连逻辑、历史消息分页等复杂场景下，必须添加行内注释。
- **API 定义**：每个导出的 API 函数需通过注释说明其用途。

---
*本文件由 AI 生成，旨在帮助模型快速理解 FoxChat 项目的核心逻辑与开发规范。*
