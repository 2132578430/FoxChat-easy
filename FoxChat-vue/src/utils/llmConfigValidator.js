export function validateBaseUrl(raw) {
  const value = (raw || '').trim();
  if (!value) return 'Base URL 不能为空';
  let url;
  try {
    url = new URL(value);
  } catch {
    return 'Base URL 格式不正确，示例：https://api.openai.com/v1';
  }
  if (!['http:', 'https:'].includes(url.protocol)) {
    return 'Base URL 只支持 http:// 或 https://';
  }
  if (!url.hostname) return 'Base URL 缺少主机名';
  return '';
}

export function normalizeBaseUrl(raw) {
  return (raw || '').trim().replace(/\/+$/, '');
}
