/**
 * 轻量顶部进度条（替代全屏 ElLoading）
 *
 * 用法：
 *   startLoadingBar()  — 开始加载（进度条从 0 → 80% 自动推进）
 *   stopLoadingBar()   — 完成加载（瞬间到 100% 然后淡出）
 *
 * 支持并发请求：内部计数，最后一个请求完成才隐藏
 */

let count = 0;
let barElement = null;
let timer = null;

function ensureBar() {
  if (barElement) return;
  barElement = document.createElement('div');
  barElement.className = 'fox-loading-bar';
  // 内层动画条
  const inner = document.createElement('div');
  inner.className = 'fox-loading-bar__inner';
  barElement.appendChild(inner);
  document.body.appendChild(barElement);
}

function removeBar() {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  if (barElement) {
    barElement.remove();
    barElement = null;
  }
}

export function startLoadingBar() {
  count++;
  ensureBar();
  // 模拟自然进度（永远不到 100%，给人"还在加载"的感觉）
  barElement.style.width = Math.min(80, 20 + count * 15) + '%';
  barElement.style.opacity = '1';
  barElement.style.transition = 'width 0.4s ease, opacity 0.2s ease';
}

export function stopLoadingBar() {
  count = Math.max(0, count - 1);
  if (count > 0) return; // 还有并发请求在进行

  // 瞬间到 100%，然后淡出
  if (barElement) {
    barElement.style.width = '100%';
    barElement.style.transition = 'width 0.15s ease, opacity 0.3s ease';
    timer = setTimeout(() => {
      barElement.style.opacity = '0';
      timer = setTimeout(removeBar, 300);
    }, 150);
  }
}
