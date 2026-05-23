import axios from 'axios';
import { ElMessage, ElLoading } from 'element-plus';
import router from '../router';

// 创建 axios 实例
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000, // 稍微延长一点超时时间，给服务器多一点耐心~
  withCredentials: true // 跨域请求携带 Cookie
});

// Loading 实例
let loadingInstance = null;
let requestCount = 0;

// 开启 Loading
const startLoading = () => {
  if (requestCount === 0) {
    loadingInstance = ElLoading.service({
      lock: true,
      text: '拼命加载中... Ciallo~OvO',
      background: 'rgba(255, 255, 255, 0.7)',
    });
  }
  requestCount++;
};

// 关闭 Loading
const closeLoading = () => {
  if (requestCount <= 0) return;
  requestCount--;
  if (requestCount === 0) {
    loadingInstance?.close();
  }
};

// 请求拦截器
request.interceptors.request.use(
  config => {
    // 只有在非静默模式下才显示 loading (可以通过 config.silent = true 来静默请求)
    if (!config.silent) {
      startLoading();
    }

    // Cookie 自动携带 token，无需手动注入 header
    return config;
  },
  error => {
    closeLoading();
    return Promise.reject(error);
  }
);

// 响应拦截器
let isRedirectingToLogin = false;

request.interceptors.response.use(
  response => {
    // 关闭 loading
    if (!response.config.silent) {
      closeLoading();
    }

    // Cookie 自动携带 token，无需处理 new-token header

    const res = response.data;

    // 标准化响应处理：code 为 1000 表示成功
    if (res.code === 1000) {
      // 智能解包：如果有 data 字段就返回 data，否则返回整个 res 以便获取 code
      if (res.data === null || res.data === undefined) {
        return res;
      }
      return res.data;
    } else {
      // 业务错误处理：展示 msg 中的错误信息
      const msg = res.msg || '哎呀，出错了呢... (未知错误)';
      ElMessage.error(msg);
      return Promise.reject(new Error(msg));
    }
  },
  error => {
    closeLoading();
    
    let msg = '网络连接异常';
    if (error.response) {
      const { status, data } = error.response;
      if (status === 401) {
        msg = '登录已过期，请重新登录呀~';
        localStorage.removeItem('token');
        localStorage.removeItem('userInfo');
        
        // 避免多次提示和重复跳转
        if (!isRedirectingToLogin) {
          isRedirectingToLogin = true;
          ElMessage.error(msg);
          router.push('/login');
          // 延迟重置标志位，确保所有并发请求都已完成
          setTimeout(() => {
            isRedirectingToLogin = false;
          }, 1000);
        }
        return Promise.reject(error);
      } else {
        msg = data.msg || '服务器开小差了...';
      }
    }
    
    ElMessage.error(msg);
    return Promise.reject(error);
  }
);

export default request;
