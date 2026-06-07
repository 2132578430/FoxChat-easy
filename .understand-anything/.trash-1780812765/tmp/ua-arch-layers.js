const fs = require('fs');

const resultsPath = 'E:/WorkSpace/ProjectCode/.understand-anything/tmp/ua-arch-results.json';
const inputPath = 'E:/WorkSpace/ProjectCode/.understand-anything/tmp/ua-arch-file-data.json';
const outputPath = 'E:/WorkSpace/ProjectCode/.understand-anything/intermediate/layers.json';

const results = JSON.parse(fs.readFileSync(resultsPath, 'utf-8'));
const input = JSON.parse(fs.readFileSync(inputPath, 'utf-8'));
const { fileNodes } = input;
const { directoryGroups } = results;

// Build node ID to group mapping
const nodeToGroup = {};
for (const [group, ids] of Object.entries(directoryGroups)) {
  for (const id of ids) nodeToGroup[id] = group;
}

// Layer assignment rules
// For split groups, we need to look at the individual file paths
function assignLayer(nodeId) {
  const group = nodeToGroup[nodeId];
  const node = fileNodes.find(n => n.id === nodeId);
  if (!node) return null;
  const fp = node.filePath;
  const name = node.name;
  const type = node.type;

  // === Non-split groups (whole group goes to one layer) ===

  // FoxChat-java:foxChat-common → utility
  if (group === 'FoxChat-java:foxChat-common') return 'layer:utility';

  // FoxChat-java:foxChat-netty → middleware
  if (group === 'FoxChat-java:foxChat-netty') return 'layer:middleware';

  // FoxChat-java:foxChat-pojo → types
  if (group === 'FoxChat-java:foxChat-pojo') return 'layer:types';

  // FoxChat-java:foxChat-web → api
  if (group === 'FoxChat-java:foxChat-web') return 'layer:api';

  // FoxChatRAG-python:app/common → utility
  if (group === 'FoxChatRAG-python:app/common') return 'layer:utility';

  // FoxChatRAG-python:app/exception → middleware
  if (group === 'FoxChatRAG-python:app/exception') return 'layer:middleware';

  // FoxChatRAG-python:app/grpc → api
  if (group === 'FoxChatRAG-python:app/grpc') return 'layer:api';

  // FoxChatRAG-python:app/models → data
  if (group === 'FoxChatRAG-python:app/models') return 'layer:data';

  // FoxChatRAG-python:app/schemas → types
  if (group === 'FoxChatRAG-python:app/schemas') return 'layer:types';

  // FoxChatRAG-python:app/service → service
  if (group === 'FoxChatRAG-python:app/service') return 'layer:service';

  // FoxChatRAG-python:app/service/chat → service
  if (group === 'FoxChatRAG-python:app/service/chat') return 'layer:service';

  // FoxChatRAG-python:app/service/rag → service
  if (group === 'FoxChatRAG-python:app/service/rag') return 'layer:service';

  // FoxChatRAG-python:app/util → utility
  if (group === 'FoxChatRAG-python:app/util') return 'layer:utility';

  // FoxChatRAG-python:app/chroma → data
  if (group === 'FoxChatRAG-python:app/chroma') return 'layer:data';

  // FoxChatRAG-python:app/api → api
  if (group === 'FoxChatRAG-python:app/api') return 'layer:api';

  // FoxChatRAG-python:app/retriever → data
  if (group === 'FoxChatRAG-python:app/retriever') return 'layer:data';

  // FoxChat-vue:src/router → api
  if (group === 'FoxChat-vue:src/router') return 'layer:api';

  // FoxChat-vue:src/utils → utility
  if (group === 'FoxChat-vue:src/utils') return 'layer:utility';

  // FoxChat-vue:src/views → ui
  if (group === 'FoxChat-vue:src/views') return 'layer:ui';

  // FoxChat-vue:src/components → ui
  if (group === 'FoxChat-vue:src/components') return 'layer:ui';

  // FoxChat-vue:src/composables → service
  if (group === 'FoxChat-vue:src/composables') return 'layer:service';

  // FoxChat-vue:src/proto → types
  if (group === 'FoxChat-vue:src/proto') return 'layer:types';

  // FoxChatRAG-python:app → utility
  if (group === 'FoxChatRAG-python:app') return 'layer:utility';

  // FoxChatRAG-python:proto → types
  if (group === 'FoxChatRAG-python:proto') return 'layer:types';

  // FoxChatRAG-python:test → test
  if (group === 'FoxChatRAG-python:test') return 'layer:test';

  // === Split groups ===

  // FoxChat-java:foxChat-service → split: service / data / types
  if (group === 'FoxChat-java:foxChat-service') {
    if (type === 'schema') return 'layer:types'; // proto schema
    if (fp.includes('/mapper/') || fp.includes('/resources/mapper/') || name === 'build.gradle') return 'layer:data';
    if (fp.includes('/config/RagRabbitMqConfig')) return 'layer:data';
    return 'layer:service'; // service interfaces, impls, remote, client, grpc, task
  }

  // FoxChatRAG-python:app/core → split: middleware / infrastructure / utility
  if (group === 'FoxChatRAG-python:app/core') {
    if (fp.includes('/mq/')) return 'layer:middleware';
    if (fp.includes('/db/') || name === 'settings.py' || name === 'config.py' || name === 'health_check.py') return 'layer:infrastructure';
    return 'layer:utility'; // llm_model, net, prompts, __init__
  }

  // FoxChat-java:root → split: infrastructure / documentation / config
  if (group === 'FoxChat-java:root') {
    if (type === 'service') return 'layer:infrastructure'; // Dockerfiles
    if (type === 'document') return 'layer:documentation';
    return 'layer:config'; // build.gradle, gradle.properties, settings.gradle, etc.
  }

  // FoxChat-vue:root → split: infrastructure / documentation / config / ui
  if (group === 'FoxChat-vue:root') {
    if (type === 'service') return 'layer:infrastructure'; // Dockerfiles
    if (type === 'document') return 'layer:documentation';
    if (name === 'index.html') return 'layer:ui';
    return 'layer:config'; // .env.*, package.json, vite.config.js
  }

  // FoxChatRAG-python:root → split: api / infrastructure / documentation / config
  if (group === 'FoxChatRAG-python:root') {
    if (name === 'main.py') return 'layer:api';
    if (type === 'service') return 'layer:infrastructure'; // Dockerfiles
    if (name.startsWith('requirements')) return 'layer:config';
    return 'layer:documentation'; // README, MEMORY_UPLOAD, Problem
  }

  // root → split: data / documentation / infrastructure
  if (group === 'root') {
    if (type === 'table') return 'layer:data';
    if (type === 'document') return 'layer:documentation';
    return 'layer:infrastructure'; // docker-compose services, .env.example
  }

  // deploy:local-middleware → split: infrastructure / documentation
  if (group === 'deploy:local-middleware') {
    if (type === 'document') return 'layer:documentation';
    return 'layer:infrastructure';
  }

  // deploy:root → documentation
  if (group === 'deploy:root') return 'layer:documentation';

  // deploy:frp → infrastructure
  if (group === 'deploy:frp') return 'layer:infrastructure';

  // ci-cd → infrastructure
  if (group === 'ci-cd') return 'layer:infrastructure';

  // FoxChat-vue:src → ui (App.vue, main.js, style.css)
  if (group === 'FoxChat-vue:src') return 'layer:ui';

  // tooling → split: config / documentation
  if (group === 'tooling') {
    if (type === 'document') return 'layer:documentation';
    return 'layer:config';
  }

  // Default
  return 'layer:config';
}

// Assign all nodes
const layerMap = {};
for (const node of fileNodes) {
  const layer = assignLayer(node.id);
  if (!layer) {
    console.error('No layer for:', node.id, node.filePath);
    process.exit(1);
  }
  if (!layerMap[layer]) layerMap[layer] = [];
  layerMap[layer].push(node.id);
}

// Verify total
const totalAssigned = Object.values(layerMap).reduce((sum, ids) => sum + ids.length, 0);
console.log('Total file nodes:', fileNodes.length);
console.log('Total assigned:', totalAssigned);
if (totalAssigned !== fileNodes.length) {
  console.error('MISMATCH! Expected', fileNodes.length, 'got', totalAssigned);
  process.exit(1);
}

// Build layers array
const layers = [
  {
    id: 'layer:api',
    name: 'API 层',
    description: 'HTTP REST 控制器、gRPC 服务端、WebSocket 路由和应用入口点，负责接收和分发外部请求',
    nodeIds: layerMap['layer:api'] || []
  },
  {
    id: 'layer:service',
    name: '服务层',
    description: '核心业务逻辑，包括 IM 好友/消息/群组服务、AI 对话 LangGraph 编排、RAG 记忆管理和 Vue composables',
    nodeIds: layerMap['layer:service'] || []
  },
  {
    id: 'layer:data',
    name: '数据层',
    description: '数据持久化，包括 MyBatis Mapper 接口与 XML 映射、SQL 表定义、SQLAlchemy ORM 模型、ChromaDB 向量库和 RAG 检索器',
    nodeIds: layerMap['layer:data'] || []
  },
  {
    id: 'layer:types',
    name: '类型层',
    description: '数据类型定义，包括 Java Entity/DTO/VO、Python Pydantic Schema、Protobuf 协议定义和 gRPC 生成代码',
    nodeIds: layerMap['layer:types'] || []
  },
  {
    id: 'layer:middleware',
    name: '中间件层',
    description: '传输与横切关注点，包括 Netty WebSocket 编解码器与消息处理器、RabbitMQ 消费者和全局异常处理',
    nodeIds: layerMap['layer:middleware'] || []
  },
  {
    id: 'layer:utility',
    name: '工具层',
    description: '共享工具与常量，包括 Java 常量/工具类、Python 通用模块/工具函数、LLM 模型封装、Prompt 模板管理和 Vue 工具函数',
    nodeIds: layerMap['layer:utility'] || []
  },
  {
    id: 'layer:infrastructure',
    name: '基础设施层',
    description: '部署与运维配置，包括 Dockerfile、docker-compose、CI/CD 流水线、FRP 内网穿透、数据库/Redis 连接客户端和健康检查',
    nodeIds: layerMap['layer:infrastructure'] || []
  },
  {
    id: 'layer:config',
    name: '配置层',
    description: '项目构建与环境配置，包括 Gradle/npm 构建文件、环境变量、Vite 配置和工具元数据',
    nodeIds: layerMap['layer:config'] || []
  },
  {
    id: 'layer:documentation',
    name: '文档层',
    description: '项目文档，包括各子项目 README、部署指南、API 接口文档、数据库设计说明和项目介绍',
    nodeIds: layerMap['layer:documentation'] || []
  },
  {
    id: 'layer:ui',
    name: 'UI 层',
    description: 'Vue 3 前端界面，包括页面视图、聊天/LLM 配置组件、Electron 壳和样式资源',
    nodeIds: layerMap['layer:ui'] || []
  },
  {
    id: 'layer:test',
    name: '测试层',
    description: '自动化测试，包括 Python RAG 服务的记忆压力测试、去重测试和结构注入测试',
    nodeIds: layerMap['layer:test'] || []
  }
];

// Filter out empty layers
const nonEmptyLayers = layers.filter(l => l.nodeIds.length > 0);

// Final verification
const finalTotal = nonEmptyLayers.reduce((sum, l) => sum + l.nodeIds.length, 0);
console.log('\nLayer summary:');
for (const l of nonEmptyLayers) {
  console.log(`  ${l.name}: ${l.nodeIds.length} files`);
}
console.log(`  Total: ${finalTotal}`);

if (finalTotal !== fileNodes.length) {
  console.error('FINAL MISMATCH!');
  process.exit(1);
}

fs.writeFileSync(outputPath, JSON.stringify(nonEmptyLayers, null, 2), 'utf-8');
console.log('\nLayers written to', outputPath);
