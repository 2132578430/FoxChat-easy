/**
 * FoxToast — 轻量顶部滑入提示（替代 ElMessage）
 *
 * 用法：
 *   import { FoxToast } from '@/components/FoxUI/FoxToast';
 *   FoxToast.success('登录成功');
 *   FoxToast.error('网络连接异常');
 *   FoxToast.warning('请填写昵称');
 *   FoxToast.info('正在加载...');
 */

const ICONS = {
  success: '✅',
  error: '❌',
  warning: '⚠️',
  info: 'ℹ️',
};

const COLORS = {
  success: '#67c23a',
  error: '#f56c6c',
  warning: '#e6a23c',
  info: '#909399',
};

let container = null;

function ensureContainer() {
  if (container) return;
  container = document.createElement('div');
  container.className = 'fox-toast-container';
  document.body.appendChild(container);
}

function show(message, type = 'info', duration = 3000) {
  ensureContainer();

  const el = document.createElement('div');
  el.className = `fox-toast fox-toast--${type}`;
  el.innerHTML = `<span class="fox-toast__icon">${ICONS[type]}</span><span>${message}</span>`;

  container.appendChild(el);

  // 入场动画
  requestAnimationFrame(() => {
    el.style.transform = 'translateY(0)';
    el.style.opacity = '1';
  });

  // 自动消失
  setTimeout(() => {
    el.style.transform = 'translateY(-12px)';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 200);
  }, duration);
}

// 注入全局样式（只执行一次）
let styleInjected = false;
function injectStyle() {
  if (styleInjected) return;
  styleInjected = true;
  const style = document.createElement('style');
  style.textContent = `
    .fox-toast-container {
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 9999;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      pointer-events: none;
    }
    .fox-toast {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 20px;
      border-radius: 10px;
      background: #fff;
      box-shadow: 0 4px 20px rgba(0,0,0,0.1);
      font-size: 14px;
      color: #333;
      pointer-events: auto;
      transform: translateY(-12px);
      opacity: 0;
      transition: all 0.2s ease-out;
    }
    .fox-toast__icon { font-size: 16px; }
    .fox-toast--error   { }
    .fox-toast--success { }
    .fox-toast--warning { }
    .fox-toast--info    { }
  `;
  document.head.appendChild(style);
}

injectStyle();

export const FoxToast = {
  success: (msg, dur) => show(msg, 'success', dur),
  error: (msg, dur) => show(msg, 'error', dur),
  warning: (msg, dur) => show(msg, 'warning', dur),
  info: (msg, dur) => show(msg, 'info', dur),
};

export default FoxToast;
