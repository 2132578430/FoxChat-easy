import { ref } from 'vue';

// 当前聊天对象
const currentFriend = ref({});
const currentGroup = ref({});
const currentChatType = ref('private'); // 'private' or 'group'

// 消息列表
const messageList = ref([]);
const inputMessage = ref('');

// 历史记录状态
const isLoadingHistory = ref(false);
const hasMoreHistory = ref(true);
const lastTimestamp = ref(null);
const lastMsgId = ref(null);

// 消息选择模式
const isSelectionMode = ref(false);
const selectedMessageIds = ref([]);

// LLM 状态
const isLlmTyping = ref(false);
const llmPendingCount = ref(0);

export function useChatStore() {
  return {
    currentFriend,
    currentGroup,
    currentChatType,
    messageList,
    inputMessage,
    isLoadingHistory,
    hasMoreHistory,
    lastTimestamp,
    lastMsgId,
    isSelectionMode,
    selectedMessageIds,
    isLlmTyping,
    llmPendingCount
  };
}
