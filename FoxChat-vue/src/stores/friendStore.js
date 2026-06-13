import { ref, computed } from 'vue';

// 好友列表
const friendList = ref([]);

// 好友请求列表
const friendRequestList = ref([]);

// 创造物列表（role === 1 或 isOldFriend）
const llmFriendList = computed(() => {
  return friendList.value.filter(friend => friend.role === 1 || friend.isOldFriend);
});

export function useFriendStore() {
  return {
    friendList,
    friendRequestList,
    llmFriendList
  };
}
