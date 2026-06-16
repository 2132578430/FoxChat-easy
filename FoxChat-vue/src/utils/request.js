import axios from 'axios';
import { FoxToast } from '@/components/FoxUI';
import router from '../router';
import { startLoadingBar, stopLoadingBar } from './loadingBar';

// 创建 axios 实例
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
  withCredentials: true
});

// 请求拦截器
request.interceptors.request.use(
  config => {
    // 非静默请求 → 显示顶部轻量进度条（替代全屏 ElLoading）
    if (!config.silent) {
      startLoadingBar();
    }
    return config;
  },
  error => {
    stopLoadingBar();
    return Promise.reject(error);
  }
);

// 响应拦截器
let isRedirectingToLogin = false;

request.interceptors.response.use(
  response => {
    if (!response.config.silent) {
      stopLoadingBar();
    }

    const res = response.data;

    if (res.code === 1000) {
      return res;
    } else {
      const msg = res.msg || '哎呀，出错了呢... (未知错误)';
      FoxToast.error(msg);
      return Promise.reject(new Error(msg));
    }
  },
  error => {
    stopLoadingBar();

    let msg = '网络连接异常';
    if (error.response) {
      const { status, data } = error.response;
      if (status === 401) {
        msg = '登录已过期，请重新登录呀~';
        localStorage.removeItem('token');
        localStorage.removeItem('userInfo');

        if (!isRedirectingToLogin) {
          isRedirectingToLogin = true;
          FoxToast.error(msg);
          router.push('/login');
          setTimeout(() => {
            isRedirectingToLogin = false;
          }, 1000);
        }
        return Promise.reject(error);
      } else {
        msg = data.msg || '服务器开小差了...';
      }
    }

    FoxToast.error(msg);
    return Promise.reject(error);
  }
);

export default request;
