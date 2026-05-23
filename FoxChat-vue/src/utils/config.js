// 全局配置文件
// 用于集中管理请求地址、证书指纹等配置

// 后端服务器基础地址 (WebSocket)
// 优先级: 环境变量 > 自动推断
let wsBaseUrl;

// 建议开发环境下也使用相对路径以触发 Vite Proxy，
// 这样连接的就是 frontend_port/chat，再由 Vite 转发给 backend_port/chat
if (import.meta.env.DEV) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  wsBaseUrl = `${protocol}//${window.location.host}`;
} else if (import.meta.env.VITE_WS_BASE_URL) {
  // 1. 如果配置了环境变量，使用配置
  wsBaseUrl = import.meta.env.VITE_WS_BASE_URL;
} else if (import.meta.env.PROD) {
  // 2. 生产环境：根据当前页面的协议和域名自动推断
  // http -> ws, https -> wss
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  wsBaseUrl = `${protocol}//${window.location.host}`;
} else {
  // 3. 兜底：开发环境默认本地
  wsBaseUrl = 'ws://localhost:13000';
}

export const WS_BASE_URL = wsBaseUrl;

// WebSocket 聊天服务地址
// 如果是自动推断的生产环境地址，由于 Nginx 转发规则通常是 /chat，所以需要拼接
// 如果是手动配置的完整 URL (如 ws://localhost:13000)，则直接拼接 /chat 路径
export const CHAT_SERVICE_URL = `${WS_BASE_URL}/chat`;

// 文件服务器基础地址 (OSS)
// 优先级: 环境变量 > 默认配置
// 生产环境通常配置为 /oss (Nginx 转发)
// 开发环境配置为 http://182.92.222.243/oss (直接访问)
export const OSS_BASE_URL = import.meta.env.VITE_OSS_BASE_URL || (import.meta.env.PROD ? '/oss' : 'http://182.92.222.243/oss');

// WebTransport 配置 (暂时保留，以备后续切换回 QUIC)
/*
export const QUIC_BASE_URL = 'https://172.17.248.127:13000';
export const SERVER_CERT_FINGERPRINTS = [
  "mZkOKtTm8s9LHnen312sFcvguwymoNxqqvnMobo=" 
];
export const getWebTransportOptions = () => { ... }
*/

