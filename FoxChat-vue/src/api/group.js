import request from '@/utils/request';

/**
 * 获取群组列表
 */
export function getGroupList() {
  return request.get('/group/list');
}

/**
 * 搜索群组
 * @param {string} keyword - 搜索关键词
 */
export function searchGroup(keyword) {
  return request.get('/group/search', {
    params: { keyword }
  });
}

/**
 * 创建群组
 * @param {Object} data - 群组信息 { groupName: string }
 */
export function createGroup(data) {
  return request.post('/group/add', data);
}

/**
 * 加入群组
 * @param {string} groupId - 群组ID
 */
export function joinGroup(groupId) {
  return request.post('/group/join', { groupId });
}

/**
 * 获取群聊历史记录
 * @param {Object} data - { groupId, lastTimestamp }
 */
export function getGroupChatHistory(data) {
  return request.post('/groupMsg/history', data);
}
