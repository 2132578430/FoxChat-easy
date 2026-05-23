import request from '@/utils/request';

// 获取未读消息计数
export function getUnreadCounts() {
  return request.get('/msg/unreadCounts');
}

// 获取聊天历史记录
export function getChatHistory(data) {
  return request.post('/msg/history', data);
}

// 撤回消息
export function withdrawMessages(msgIds) {
  return request.post('/msg/withdraw', { msgIds });
}

// 删除消息
export function deleteMessages(msgIds) {
  return request.post('/msg/delete', { msgIds });
}

// 获取未签收消息ID列表
export function getUnsignedMessages(friendId) {
  return request.post('/msg/noSignMsg', { friendId });
}
