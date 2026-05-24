<template>
  <div class="home-container theme-qq">
    <!-- Sidebar -->
    <div class="sidebar">
      <div class="avatar-container" @click="toggleProfile">
        <div class="avatar-wrapper">
          <el-avatar :size="50" :src="resolveAvatarUrl(userInfo.faceImage || userInfo.face_image) || defaultUserAvatar"></el-avatar>
        </div>
        <div class="username">{{ userInfo.nickname || '未设置昵称' }}</div>
      </div>
      <div class="menu-items">
        <div class="menu-item" :class="{ active: !showFriendList && !showGroupList && !showProfile && !showRag }" @click="showFriendList = false; showGroupList = false; showProfile = false; showRag = false">
          <el-icon><ChatDotRound /></el-icon>
        </div>
        <div class="menu-item" :class="{ active: showFriendList }" @click="showFriendList = !showFriendList; showGroupList = false; showProfile = false;">
          <el-icon><User /></el-icon>
        </div>
        <div class="menu-item" :class="{ active: showGroupList }" @click="showGroupList = !showGroupList; showFriendList = false; showProfile = false;">
          <el-icon><ChatSquare /></el-icon>
        </div>
        <div class="menu-item" :class="{ active: showRag }" @click="toggleRag">
          <el-icon><Reading /></el-icon>
        </div>
        <div class="menu-item" :class="{ active: showLlmConfigPanel }" @click="toggleLlmConfigPanel">
          <el-icon><Setting /></el-icon>
        </div>
        <div class="menu-item" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
        </div>
      </div>
    </div>

    <!-- Chat Area -->
    <div class="chat-area" :class="{ 'shrink-right': showFriendList || showGroupList || showProfile }">
      <!-- LLM Config Panel -->
      <LlmConfigPanel
        v-if="showLlmConfigPanel"
        :friend-list="llmFriendList"
        @close="showLlmConfigPanel = false"
      />
      
      <!-- Normal Chat Interface -->
      <template v-else>
        <div class="chat-header">
          <span class="chat-title" v-if="showRag">狐狸RAG</span>
          <span class="chat-title" v-else-if="currentChatType === 'group'">{{ currentGroup.groupName || currentGroup.name || '群聊' }}</span>
          <span class="chat-title" v-else>
            {{ currentFriend.nickname || currentFriend.username || '选择好友开始聊天' }}
            <span v-if="currentFriend.emotion && (currentFriend.role === 1 || currentFriend.isOldFriend)" class="emotion-emoji">{{ emotionToEmoji(currentFriend.emotion) }}</span>
            <span v-if="isLlmTyping && (currentFriend.role === 1 || currentFriend.isOldFriend)" class="typing-indicator">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
            </span>
          </span>
          <!-- 仅私聊显示多选操作，群聊暂不支持（需要额外表结构支持） -->
          <div class="chat-actions" v-if="!showRag && currentChatType === 'private' && (currentFriend.userId || currentFriend.id)">
            <transition name="fade-scale" mode="out-in">
              <div v-if="!isSelectionMode" key="normal">
                <el-tooltip content="多选消息" placement="bottom">
                  <el-button circle class="action-btn" @click="toggleSelectionMode">
                    <el-icon><Select /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
              <div class="selection-actions" v-else key="selection">
                <el-button round size="small" @click="cancelSelectionMode">取消</el-button>
                <el-button 
                  type="danger" 
                  round 
                  size="small" 
                  @click="handleDeleteMessages" 
                  :disabled="selectedMessageIds.length === 0"
                  class="withdraw-btn delete-btn"
                >
                  删除 ({{ selectedMessageIds.length }})
                </el-button>
                <el-button 
                  type="warning" 
                  round 
                  size="small" 
                  @click="handleWithdrawMessages" 
                  :disabled="selectedMessageIds.length === 0"
                  class="withdraw-btn"
                >
                  撤回 ({{ selectedMessageIds.length }})
                </el-button>
              </div>
            </transition>
          </div>
        </div>
        <!-- Message List -->
        <MessageList
          ref="messageListRef"
          :messages="messageList"
          :current-friend="currentFriend"
          :current-group="currentGroup"
          :current-chat-type="currentChatType"
          :user-info="userInfo"
          :is-selection-mode="isSelectionMode"
          :selected-message-ids="selectedMessageIds"
          :show-rag="showRag"
          :rag-files="ragFiles"
          :has-rag-search-results="hasRagSearchResults"
          @load-more="loadMoreHistory"
          @scroll-bottom="scrollToBottom"
          @open-upload="showUploadDialog = true"
          @reset-rag="resetRagResults"
          @file-click="handleFileClick"
        />

        <!-- Chat Input -->
        <ChatInput
          v-model="inputMessage"
          :show-rag="showRag"
          :is-searching-rag="isSearchingRag"
          @send="sendMessage"
          @open-upload="showUploadDialog = true"
        />
      </template>
    </div>

    <!-- Profile Detail -->
    <transition name="slide-fade">
      <div class="profile-detail" v-show="showProfile">
        <div class="profile-header">
          <h3>个人信息</h3>
        </div>
        <div class="profile-content">
          <div class="profile-avatar-section">
            <el-avatar :size="100" :src="resolveAvatarUrl(profileInfo.faceImage) || defaultUserAvatar"></el-avatar>
            <el-button type="primary" size="small" class="edit-avatar-btn" @click="handleEditAvatar">修改头像</el-button>
          </div>
          
          <div class="info-list">
            <div class="info-item-input">
              <label>昵称</label>
              <el-input v-model="profileInfo.nickname" placeholder="请输入昵称" size="small"></el-input>
            </div>
            <div class="info-item-input">
              <label>邮箱</label>
              <el-input v-model="profileInfo.email" placeholder="请输入邮箱" size="small"></el-input>
            </div>
          </div>

          <div class="profile-actions-vertical">
            <el-button type="primary" @click="handleUpdateProfile">修改信息</el-button>
            <el-button type="info" plain @click="handleEditPassword">修改密码</el-button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Group List -->
    <GroupList
      ref="groupListRef"
      v-model="showGroupList"
      :groups="groupList"
      :current-group-id="currentGroup.id"
      :user-info="userInfo"
      :is-group-loading="isGroupLoading"
      @select-group="handleGroupClick"
      @join-group="handleJoinGroup"
      @create-group="showCreateGroupDialog = true"
      @search="handleGroupSearch"
    />

    <!-- Create Group Dialog -->
    <el-dialog v-model="showCreateGroupDialog" title="新建狐狸窝" width="400px" center destroy-on-close>
      <el-form :model="createGroupForm" ref="createGroupFormRef" label-width="100px">
        <el-form-item label="狐狸窝名" prop="groupName" :rules="[{ required: true, message: '请输入狐狸窝名字', trigger: 'blur' }]">
          <el-input v-model="createGroupForm.groupName" placeholder="给狐狸窝起个名字吧"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateGroupDialog = false">取消</el-button>
          <el-button type="primary" @click="handleCreateGroup" :loading="isCreatingGroup">创建</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Add LLM Friend Dialog -->
    <el-dialog v-model="showAddLlmFriendDialog" title="创造" width="400px" center destroy-on-close>
      <el-form :model="addLlmFriendForm" ref="addLlmFriendFormRef" label-width="80px">
        <el-form-item label="昵称" prop="nickname" :rules="[{ required: true, message: '请输入昵称', trigger: 'blur' }, { max: 30, message: '昵称不能超过30个字', trigger: 'blur' }]">
          <el-input v-model="addLlmFriendForm.nickname" placeholder="我的网名叫什么" maxlength="30" show-word-limit></el-input>
        </el-form-item>
        <el-form-item label="你是" prop="myName" :rules="[{ required: true, message: '请输入创造者名字', trigger: 'blur' }, { max: 30, message: '名字不能超过30个字', trigger: 'blur' }]">
          <el-input v-model="addLlmFriendForm.myName" placeholder="我的创造者叫什么名字" maxlength="30" show-word-limit></el-input>
        </el-form-item>
        <el-form-item label="我是" prop="partnerName" :rules="[{ required: true, message: '请输入我的名字', trigger: 'blur' }, { max: 30, message: '名字不能超过30个字', trigger: 'blur' }]">
          <el-input v-model="addLlmFriendForm.partnerName" placeholder="我是谁？" maxlength="30" show-word-limit></el-input>
        </el-form-item>
        <el-form-item label="经历" prop="experience" :rules="[{ required: true, message: '请输入经历', trigger: 'blur' }, { max: 10000, message: '经历不能超过10000个字', trigger: 'blur' }]">
          <el-input v-model="addLlmFriendForm.experience" type="textarea" :rows="6" placeholder="你想要和我有什么经历？" maxlength="10000" show-word-limit></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddLlmFriendDialog = false">取消</el-button>
          <el-button type="primary" @click="handleAddLlmFriend" :loading="isAddingLlmFriend">创造</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Edit LLM Friend Dialog -->
    <el-dialog v-model="showEditLlmFriendDialog" title="修改模型" width="400px" center destroy-on-close>
      <div class="edit-llm-avatar-section">
        <div class="edit-llm-avatar-wrapper" @click="openLlmAvatarCropper">
          <el-avatar :size="100" :src="resolveAvatarUrl(editLlmFriendForm.faceImage) || defaultUserAvatar"></el-avatar>
          <div class="edit-llm-avatar-mask">
            <el-icon :size="24"><UploadFilled /></el-icon>
            <span>修改头像</span>
          </div>
        </div>
        <div class="edit-llm-nickname">
          <el-input v-model="editLlmFriendForm.nickname" placeholder="模型昵称" maxlength="30" show-word-limit></el-input>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showEditLlmFriendDialog = false">取消</el-button>
          <el-button type="primary" @click="handleUpdateLlmFriend">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Upload Document Dialog -->
    <el-dialog v-model="showUploadDialog" title="狐狸知识库上传" width="500px" center destroy-on-close>
      <div class="upload-dialog-content">
        <el-upload
          class="fox-uploader"
          drag
          action=""
          :http-request="handleUploadRequest"
          :before-upload="handleBeforeUpload"
          multiple
          accept=".pdf,.doc,.docx,.txt,.md"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 PDF, DOC, TXT, MD 格式，单文件大小不超过 100MB 喔~
            </div>
          </template>
        </el-upload>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showUploadDialog = false">关闭</el-button>
          <el-button type="primary" :loading="isUploading" @click="submitBatchUpload">开始上传</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Friend List -->
    <FriendList
      ref="friendListRef"
      v-model="showFriendList"
      v-model:search-text="searchText"
      :friends="friendList"
      :friend-requests="friendRequestList"
      :user-info="userInfo"
      :current-friend-id="currentFriend.userId || currentFriend.id"
      @select-friend="selectFriend"
      @accept-request="handleAcceptFriend"
      @add-friend="handleAddFriend"
      @add-llm-friend="showAddLlmFriendDialog = true"
      @delete-friend="handleDeleteFriend"
      @edit-llm-friend="handleEditLlmFriend"
      @search="handleFriendSearch"
      @director-mode-change="handleDirectorModeChange"
    />
    <!-- Avatar Cropper Dialog -->
    <AvatarCropper v-model:visible="showAvatarCropper" :type="isAvatarCropperForLlm ? 'llm' : 'user'" @success="handleAvatarSuccess" @blob="handleAvatarBlob" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ChatDotRound, User, SwitchButton, Select, ChatSquare, Reading, Setting } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { encodeProtocol, decodeProtocol } from '@/utils/protocol'; // 引入协议编解码器
import snowflake from '@/utils/snowflake'; // 引入雪花ID生成器
import * as userApi from '@/api/user';
import * as friendApi from '@/api/friend';
import * as messageApi from '@/api/message';
import * as groupApi from '@/api/group';
import request from '@/utils/request';

import AvatarCropper from '@/components/AvatarCropper.vue';
import ChatInput from '@/components/Chat/ChatInput.vue';
import MessageList from '@/components/Chat/MessageList.vue';
import FriendList from '@/components/Chat/FriendList.vue';
import GroupList from '@/components/Chat/GroupList.vue';
import LlmConfigPanel from '@/components/LlmConfig/LlmConfigPanel.vue';

const defaultUserAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png';

const router = useRouter();
const userInfo = reactive(JSON.parse(localStorage.getItem('userInfo') || '{}'));
const showAvatarCropper = ref(false);

const emotionEmojiMap = {
  '开心': '😊',
  '快乐': '😊',
  'happy': '😊',
  '悲伤': '😢',
  '难过': '😢',
  'sad': '😢',
  '愤怒': '😠',
  '生气': '😠',
  'anger': '😠',
  'angry': '😠',
  '惊讶': '😲',
  'surprise': '😲',
  'surprised': '😲',
  '恐惧': '😨',
  '害怕': '😨',
  'fear': '😨',
  'fearful': '😨',
  '厌恶': '🤢',
  'disgust': '🤢',
  'disgusted': '🤢',
  'neutral': '😐',
  '平静': '😐'
};

const emotionToEmoji = (emotion) => {
  return emotionEmojiMap[emotion] || emotionEmojiMap[emotion?.toLowerCase()] || '😊';
};
const isAvatarCropperForLlm = ref(false); // 头像裁剪是否用于模型编辑
const ws = ref(null);
const currentFriend = ref({});
const currentGroup = ref({});
const currentChatType = ref('private'); // 'private' or 'group'
const messageList = ref([]);
const inputMessage = ref('');
const messageListRef = ref(null);
const friendListRef = ref(null);
const groupListRef = ref(null);
const isLoadingHistory = ref(false);
const hasMoreHistory = ref(true);
const lastTimestamp = ref(null);
const lastMsgId = ref(null);
const uploadingAvatar = ref(false);
const searchText = ref('');
const showFriendList = ref(false);
const showGroupList = ref(false);
const showProfile = ref(false);
const profileInfo = ref({
  faceImage: '',
  nickname: '',
  email: ''
});
const showCreateGroupDialog = ref(false);
const showAddLlmFriendDialog = ref(false);
const showEditLlmFriendDialog = ref(false);
const showLlmConfigPanel = ref(false);
const editLlmFriendForm = reactive({
  llmId: '',
  nickname: '',
  faceImage: ''
});
const showRag = ref(false);
const ragFiles = ref([]); // RAG 文件列表
const showUploadDialog = ref(false);

const handleDeleteFriend = async (friend) => {
  if (!friend) return;
  const friendId = friend.userId || friend.id || friend.llmId;
  const role = friend.role || 0;
  try {
    await friendApi.deleteFriend(friendId, role);
    ElMessage.success('好友已删除');
    getFriendList();
    const currentId = currentFriend.value?.userId || currentFriend.value?.id;
    if (currentId && String(currentId) === String(friendId)) {
      currentFriend.value = {};
      messageList.value = [];
    }
  } catch (error) {
    console.error('删除好友失败:', error);
    ElMessage.error('删除好友失败');
  }
};

const handleEditLlmFriend = (friend) => {
  const f = friend;
  if (!f) return;
  editLlmFriendForm.llmId = f.userId || f.id || f.llmId;
  editLlmFriendForm.nickname = f.nickname || '';
  editLlmFriendForm.faceImage = f.faceImage || f.face_image || '';
  isAvatarCropperForLlm.value = true;
  showEditLlmFriendDialog.value = true;
};

const handleUpdateLlmFriend = async () => {
  try {
    await friendApi.updateLlmFriend({
      llmId: editLlmFriendForm.llmId,
      nickname: editLlmFriendForm.nickname,
      faceImage: editLlmFriendForm.faceImage
    });
    ElMessage.success('模型已更新');
    getFriendList();
    // 如果当前聊天对象就是这个模型，刷新当前好友信息
    const currentId = currentFriend.value?.userId || currentFriend.value?.id;
    if (currentId && String(currentId) === String(editLlmFriendForm.llmId)) {
      currentFriend.value.nickname = editLlmFriendForm.nickname;
      currentFriend.value.faceImage = editLlmFriendForm.faceImage;
    }
  } catch (error) {
    console.error('更新模型失败:', error);
    ElMessage.error('更新模型失败');
  } finally {
    showEditLlmFriendDialog.value = false;
  }
};

const isSearchingRag = ref(false); // RAG 搜索状态
const hasRagSearchResults = ref(false); // 是否显示搜索结果
const isUploading = ref(false); // 是否正在上传
const pendingFiles = ref([]); // 等待上传的文件队列
const isLlmTyping = ref(false); // LLM 正在回复的状态
const llmPendingCount = ref(0); // LLM 待处理请求计数

// 获取 RAG 文件列表
const fetchRagFiles = async () => {
  try {
    hasRagSearchResults.value = false;
    // 改为请求 /rag/listFile
    const res = await request.get('/rag/listFile');
    // 根据拦截器逻辑，如果是成功返回 R<T>，这里拿到的就是 res.data
    // 如果 data 是列表对象
    if (Array.isArray(res)) {
      ragFiles.value = res;
    } else if (res && res.data && Array.isArray(res.data)) {
      ragFiles.value = res.data;
    }
  } catch (error) {
    console.error('获取 RAG 文件列表失败:', error);
    ragFiles.value = [];
  }
};

// 重置 RAG 搜索结果
const resetRagResults = () => {
  fetchRagFiles();
};

// 处理文件点击
const handleFileClick = (file) => {
  if (file.filePath) {
    window.open(file.filePath, '_blank');
  }
};

// 搜索 RAG 文件内容
const searchRagFiles = async (content) => {
  if (!content || !content.trim()) return;
  
  isSearchingRag.value = true;
  try {
    // 向 /rag/searchRagFile 发送请求，携带消息信息
    const res = await request.get('/rag/searchRagFile', {
      params: {
        msg: content
      }
    });
    
    // 响应结果结构与 listFile 类似，但带上 score 字段
    if (Array.isArray(res)) {
      ragFiles.value = res;
    } else if (res && res.data && Array.isArray(res.data)) {
      ragFiles.value = res.data;
    }
    
    hasRagSearchResults.value = true;
    ElMessage.success('搜索完成啦！看看匹配的结果吧~ ✨');
  } catch (error) {
    console.error('RAG 搜索失败:', error);
    ElMessage.error('搜索出错了呢，请稍后再试吧~');
  } finally {
    isSearchingRag.value = false;
  }
};

const isSelectionMode = ref(false);
const selectedMessageIds = ref([]);

const toggleRag = () => {
  showRag.value = !showRag.value;
  if (showRag.value) {
    // 开启 RAG 时，不强制关闭侧边栏，但需要重置当前选中的聊天
    showLlmConfigPanel.value = false;
    currentFriend.value = {};
    currentGroup.value = {};
    // 开启 RAG 时拉取文件列表
    fetchRagFiles();
  }
};

const toggleLlmConfigPanel = () => {
  showLlmConfigPanel.value = !showLlmConfigPanel.value;
  if (showLlmConfigPanel.value) {
    // Close other panels when opening config
    showFriendList.value = false;
    showGroupList.value = false;
    showProfile.value = false;
    showRag.value = false;
  }
};

const handleBeforeUpload = (file) => {
  // 限制 100MB
  const maxSize = 100 * 1024 * 1024;
  if (file.size > maxSize) {
    ElMessage.warning(`文件 ${file.name} 太重啦，狐狸抱不动... (不能超过 100MB 哦~)`);
    return false;
  }
  return true;
};

// 收集上传请求中的文件
const handleUploadRequest = (options) => {
  pendingFiles.value.push(options);
};

// 提交批量上传
const submitBatchUpload = async () => {
  if (pendingFiles.value.length === 0) {
    ElMessage.warning('还没有选择任何文件呢~');
    return;
  }

  isUploading.value = true;
  const formData = new FormData();
  
  // 如果只有一个文件，后端识别为单文件上传
  if (pendingFiles.value.length === 1) {
    formData.append('file', pendingFiles.value[0].file);
  } else {
    // 多个文件，后端识别为 List 集合
    pendingFiles.value.forEach(item => {
      formData.append('file', item.file); // 这里的 key 通常和后端参数名一致，比如 'files' 或 'file'
    });
  }

  try {
    await request.post('/rag/uploadVector', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    
    ElMessage.success('文件上传成功啦！狐狸正在努力学习中... ✨');
    showUploadDialog.value = false;
    pendingFiles.value = [];
    fetchRagFiles();
  } catch (error) {
    console.error('批量上传失败:', error);
    ElMessage.error('上传出错了呢，请稍后再试吧~');
  } finally {
    isUploading.value = false;
  }
};

// 监听对话框关闭，清空文件队列
watch(showUploadDialog, (val) => {
  if (!val) {
    pendingFiles.value = [];
  }
});

watch(showAvatarCropper, (val) => {
  if (!val) {
    isAvatarCropperForLlm.value = false;
  }
});



// Mock Friend Data (Will replace with API call)
const friendList = ref([]);
const friendRequestList = ref([]);

// 创造物列表 (role === 1 或 isOldFriend)
const llmFriendList = computed(() => {
  return friendList.value.filter(friend => friend.role === 1 || friend.isOldFriend);
});


onMounted(() => {
  if (!userInfo.username) {
    router.push('/login');
    return;
  }
  getUserInfo(); // 进入主页立即获取用户信息
  getFriendList();
  getFriendRequests();
  initWebSocket();
});

const getUnreadCounts = async () => {
  try {
    const response = await messageApi.getUnreadCounts();
    // 适配拦截器返回的完整响应结构 {code, msg, data}
    const countsMap = response.code === 1000 ? response.data : response;
    if (countsMap) {
      friendList.value.forEach(friend => {
        const fid = String(friend.userId || friend.id);
        if (countsMap[fid]) {
          friend.unreadCount = countsMap[fid];
        }
      });
    }
  } catch (error) {
    console.error('获取未读数失败:', error);
  }
};

onUnmounted(() => {
  if (ws.value) {
    try {
      ws.value.close();
    } catch (e) {
      console.error('Error closing WebSocket on unmount:', e);
    }
  }
  stopHeartbeat();
});

const toggleProfile = () => {
  showProfile.value = !showProfile.value;
  if (showProfile.value) {
    showFriendList.value = false;
    showGroupList.value = false;
    // 侧边栏展开 Profile 时，不强制关闭中间的 RAG 视图
  }
  getUserInfo(); // 每次点击头像切换时都请求一次，保证数据最新
};

const getUserInfo = async () => {
  try {
    const response = await userApi.getUserInfo();
    // 适配拦截器返回的完整响应结构 {code, msg, data}
    const data = response.code === 1000 ? response.data : response;
    profileInfo.value = data;
    // 同步更新顶层展示用的 userInfo
    if (data.nickname) userInfo.nickname = data.nickname;
    if (data.faceImage) userInfo.faceImage = data.faceImage;
    if (data.email) userInfo.email = data.email;
      
    // 更新本地存储以持久化
    localStorage.setItem('userInfo', JSON.stringify(userInfo));
  } catch (error) {
    console.error('获取个人信息失败:', error);
  }
};

const toggleSelectionMode = () => {
  isSelectionMode.value = true;
  selectedMessageIds.value = [];
  // Reset selection state
  messageList.value.forEach(msg => {
    if (msg.isMine) msg.selected = false;
  });
};

const cancelSelectionMode = () => {
  isSelectionMode.value = false;
  selectedMessageIds.value = [];
  messageList.value.forEach(msg => msg.selected = false);
};

const handleWithdrawMessages = async () => {
  if (selectedMessageIds.value.length === 0) return;

  try {
    await messageApi.withdrawMessages(selectedMessageIds.value.map(String));
    ElMessage.success('消息撤回成功');
      
    // Update local message list to show withdrawn status
    selectedMessageIds.value.forEach(id => {
      const msg = messageList.value.find(m => m.id === id);
      if (msg) {
        msg.isWithdrawn = true;
        msg.type = 'system'; // Change type to system message
      }
    });
      
    cancelSelectionMode();
  } catch (error) {
    console.error('撤回消息失败:', error);
  }
};

const handleDeleteMessages = async () => {
  if (selectedMessageIds.value.length === 0) return;

  try {
    await messageApi.deleteMessages(selectedMessageIds.value.map(String));
    ElMessage.success('消息删除成功');
      
    // Update local message list: remove deleted messages
    messageList.value = messageList.value.filter(msg => !selectedMessageIds.value.includes(msg.id));
      
    cancelSelectionMode();
  } catch (error) {
    console.error('删除消息失败:', error);
  }
};

const handleEditAvatar = () => {
  isAvatarCropperForLlm.value = false;
  showAvatarCropper.value = true;
};

const openLlmAvatarCropper = () => {
  isAvatarCropperForLlm.value = true;
  showAvatarCropper.value = true;
};

const handleAvatarSuccess = (newAvatarUrl) => {
  if (!newAvatarUrl) return;
  if (isAvatarCropperForLlm.value) {
    // 模型编辑头像更新
    editLlmFriendForm.faceImage = newAvatarUrl;
  } else {
    // 个人资料头像更新
    userInfo.faceImage = newAvatarUrl;
    profileInfo.value.faceImage = newAvatarUrl;
    localStorage.setItem('userInfo', JSON.stringify(userInfo));
  }
};

const handleAvatarBlob = async (blob) => {
  if (!blob) return;
  
  uploadingAvatar.value = true;
  try {
    const formData = new FormData();
    formData.append('file', blob, 'avatar.png');
    
    const res = await friendApi.uploadLlmAvatar(formData);
    
    uploadingAvatar.value = false;
    
    if (res && typeof res === 'string' && res.startsWith('http')) {
      editLlmFriendForm.faceImage = res;
      ElMessage.success('模型头像上传成功啦 ✨');
    } else if (res && res.data) {
      editLlmFriendForm.faceImage = res.data;
      ElMessage.success('模型头像上传成功啦 ✨');
    } else {
      ElMessage.error('上传失败');
    }
  } catch (error) {
    uploadingAvatar.value = false;
    console.error('上传模型头像失败:', error);
    ElMessage.error('上传失败，请稍后再试');
  }
};

const handleUpdateProfile = async () => {
  if (!profileInfo.value.nickname.trim()) {
    ElMessage.warning('昵称不能为空哦');
    return;
  }
  try {
    await userApi.updateProfile({
      nickname: profileInfo.value.nickname,
      email: profileInfo.value.email
    });
    ElMessage.success('个人信息更新成功啦 ✨');
    // 同步更新侧边栏显示的昵称
    userInfo.nickname = profileInfo.value.nickname;
    localStorage.setItem('userInfo', JSON.stringify(userInfo));
  } catch (error) {
    console.error('更新个人信息失败:', error);
  }
};

const handleEditPassword = () => {
  ElMessage.info('修改密码功能开发中...');
};

import { CHAT_SERVICE_URL, OSS_BASE_URL } from '@/utils/config';

// 辅助函数：处理头像URL
const resolveAvatarUrl = (url) => {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  // 如果是相对路径（如 /bedfox-chat/xxx.jpg），拼接 OSS_BASE_URL
  // 此时 OSS_BASE_URL 在生产环境是 /oss，开发环境是 http://IP/oss
  // 假设后端返回的是 bedfox-chat/xxx.jpg 或者 /bedfox-chat/xxx.jpg
  // 我们需要确保拼接正确
  const cleanUrl = url.startsWith('/') ? url.substring(1) : url;
  // 如果 OSS_BASE_URL 已经包含 /oss，且 cleanUrl 是 bedfox-chat/xxx，则拼起来是 /oss/bedfox-chat/xxx
  // 如果 cleanUrl 已经是 oss/bedfox-chat/xxx (有些后端可能返回这个)，则需要去重
  
  if (cleanUrl.startsWith('oss/')) {
     return `${OSS_BASE_URL.replace('/oss', '')}/${cleanUrl}`;
  }
  
  return `${OSS_BASE_URL}/${cleanUrl}`;
};

// WebSocket 变量
// ws 已在 setup 顶部声明: const ws = ref(null);
let heartbeatTimer = null;

const stopHeartbeat = () => {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
};

const sendBinaryMessage = (protocolData) => {
  console.log('[WS Send] Preparing to send binary data:', protocolData);
  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    try {
      ws.value.send(protocolData);
      console.log('[WS Send] Data sent successfully');
    } catch (error) {
      console.error('[WS Send] Error sending message:', error);
    }
  } else {
    console.error('[WS Send] WebSocket not connected. Current readyState:', ws.value?.readyState);
  }
};

const startHeartbeat = () => {
  stopHeartbeat();
  heartbeatTimer = setInterval(() => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      const heartbeatMsg = {
        type: 1103,
        chatMsg: {},
        extend: 'ping'
      };
      try {
        const binaryData = encodeProtocol(heartbeatMsg);
        sendBinaryMessage(binaryData);
      } catch (e) {
        console.error('发送心跳包失败:', e);
      }
    }
  }, 30000);
};

const initWebSocket = async () => {
  try {
    // token 由 HTTPOnly Cookie 管理，无需 localStorage 检查
    if (!userInfo?.userId) {
      ElMessage.error('未登录，无法连接服务器');
      router.push('/login');
      return;
    }

    const url = CHAT_SERVICE_URL;
    console.log(`Connecting to WebSocket: ${url}`);

    if (ws.value) {
      ws.value.close();
    }

    ws.value = new WebSocket(url);
    ws.value.binaryType = 'arraybuffer'; // 重要：接收二进制数据

    ws.value.onopen = async () => {
      console.log('WebSocket connected successfully!');

      // Cookie 在握手时自动完成认证，auth message 作为兼容保留
      const legacyToken = localStorage.getItem('token');
      if (legacyToken) {
        const authMsg = {
          type: 1100,
          chatMsg: {},
          extend: legacyToken
        };

        try {
          console.log('[WS] Sending legacy auth message for compatibility');
          const binaryData = encodeProtocol(authMsg);
          sendBinaryMessage(binaryData);
        } catch (e) {
          console.error('[WS] Error sending auth message:', e);
        }
      }

      startHeartbeat();
    };

    ws.value.onerror = (error) => {
      console.error('[WS] WebSocket error:', error);
    };

    ws.value.onmessage = async (event) => {
      try {
        const data = event.data;
        // WebSocket 的 binaryType 设为 arraybuffer 后，data 就是 ArrayBuffer
        await handleMessage(data);
      } catch (e) {
        console.error('处理消息出错:', e);
      }
    };

    ws.value.onclose = (event) => {
      console.log('WebSocket closed:', event);
      stopHeartbeat();
      // 可以添加重连逻辑
    };

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error);
      ElMessage.error('服务器连接发生错误');
    };

  } catch (error) {
    console.error('WebSocket connection failed:', error);
    ElMessage.error('连接服务器失败');
  }
};

// 移除 readMessages 函数，因为 WebSocket 使用 onmessage 事件回调
// const readMessages = async () => { ... }

const handleMessage = async (rawInput) => {
  try {
    let buffer = rawInput;

    // 🔍 调试诊断：检查收到的数据类型
    if (typeof rawInput === 'string') {
      console.warn('⚠️ [WebSocket] 收到字符串消息 (TextFrame)，预期应为二进制 (BinaryFrame)。尝试 Base64 解码兼容...');
      try {
        // 尝试 Base64 解码
        const binaryString = window.atob(rawInput);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        buffer = bytes.buffer;
      } catch (e) {
        console.error('❌ Base64 解码失败，无法处理该文本消息:', rawInput);
        return;
      }
    } else if (!(rawInput instanceof ArrayBuffer)) {
      console.error('❌ [WebSocket] 收到不支持的数据类型:', rawInput);
      return;
    }

    // 解析二进制协议
    const data = decodeProtocol(buffer);
    if (!data) return;

    console.log('收到解码后的消息:', data);

    // 使用 == 兼容字符串 "1105" 和数字 1105
    if (data.type == '1105') {
      // 只有当消息里的 acceptUserId 是自己时，才提示收到申请
      // 避免自己发送好友申请时也弹窗
      const isForMe = String(data.chatMsg?.acceptUserId) === String(userInfo.userId);
      
      if (isForMe) {
        ElMessage({
          message: '收到好友申请',
          type: 'info',
          duration: 5000
        });
        // 刷新好友申请列表
        getFriendRequests(); 
      }
    } else if (data.type == '1101') {
      // 收到聊天消息
      const chatMsg = data.chatMsg;
      const msgId = data.extend; // 获取数据库中的 msgId
      
      console.log('收到1101消息内容:', chatMsg);

      // 实时渲染与签收逻辑
      const currentFriendId = String(currentFriend.value?.userId || currentFriend.value?.id || '');
      // 适配 UserDef sender
      const senderId = String(chatMsg.sender?.userId || chatMsg.sendUserId || '');
      const myId = String(userInfo.userId || '');

      // 情况A：如果是当前聊天对象发来的消息
      if (currentFriendId && currentFriendId === senderId) {
        // 只有在当前聊天框中，才立即发送签收回执
        if (msgId && ws.value && ws.value.readyState === WebSocket.OPEN) {
          const signMsg = {
            type: 1102,
            chatMsg: {
              sender: { userId: senderId } // 发送给好友的ID（即消息的原始发送者）
            },
            extend: String(msgId)
          };
          // 发送二进制签收帧
          await sendBinaryMessage(encodeProtocol(signMsg));
        }

        // 尝试解析 msg 是否为结构化 blocks 格式
        let blocks = null;
        let emotion = null;
        let content = chatMsg.msg;
        try {
          const parsed = typeof chatMsg.msg === 'string' ? JSON.parse(chatMsg.msg) : chatMsg.msg;
          if (Array.isArray(parsed)) {
            blocks = parsed;
            content = null;
          } else if (parsed?.blocks && Array.isArray(parsed.blocks)) {
            blocks = parsed.blocks;
            emotion = parsed.emotion || null;
            content = null;
          }
        } catch (e) {
          // 解析失败，保持原有 content 格式
        }

        messageList.value.push({
            id: msgId || Date.now(),
            content: content,
            blocks: blocks,
            emotion: emotion,
            isMine: false,
            type: 'text',
            createTime: chatMsg.createTime || new Date().toISOString(), // 确保有时间
            senderId: senderId,
            senderName: currentFriend.value.nickname || currentFriend.value.username || '好友',
            senderAvatar: currentFriend.value.faceImage || currentFriend.value.face_image
          });
        nextTick(() => {
          scrollToBottom(true);
        });
      } 
      // 情况B：如果是自己发的消息（多端同步或服务器回显）
      else if (senderId === myId) {
        // 自己发的消息通常由发送方或服务器处理状态，这里只需负责渲染
        // 但如果只是为了本地回显，不需要msgId，只需要content匹配即可认为是同一条
        // 或者是刚发出去的消息，还没有msgId，现在补上了
        
        const isDuplicate = messageList.value.some(m => m.id === msgId);
        if (!isDuplicate) {
          // 如果消息列表里已经有"发送中"的消息（临时ID），尝试替换它或者直接追加
          // 这里简化处理：直接追加，但实际应该去重
          // 更好的做法是发送时先 push 到 list，收到回显时更新状态。
          // 但现在用户反馈是"发送后不显示"，说明发送时没 push，或者 push 了但被覆盖/清空？
          // 检查 sendMsg 逻辑：sendMsg 确实 push 了。
          
          // 如果收到回显，说明服务器处理成功了。
          // 检查当前列表里有没有刚才发的那条（可能还没有 id，只有临时 id）
          // 这里简单做：如果是自己发的，且已经在列表里（内容相同，且是最近一条），就不再 push
          
          const lastMsg = messageList.value[messageList.value.length - 1];
          if (lastMsg && lastMsg.isMine && lastMsg.content === chatMsg.msg && (Date.now() - lastMsg.id < 5000)) {
              // 认为是同一条，更新 ID 即可
              lastMsg.id = msgId || lastMsg.id;
              console.log('更新己方消息 ID:', msgId);
          } else {
             messageList.value.push({
              id: msgId || Date.now(),
              content: chatMsg.msg,
              isMine: true,
              type: 'text',
              senderName: userInfo.nickname || userInfo.username,
              senderAvatar: userInfo.faceImage || userInfo.face_image
            });
            nextTick(() => {
              scrollToBottom(true);
            });
          }
        }
      }
      // 情况C：其他好友发来的消息（不在当前聊天框）
      else {
        // 不发送 1102 签收信号，消息保持未读状态
        // 增加对应好友的未读计数（前端临时计数）
        const targetFriend = friendList.value.find(f => 
          String(f.userId || f.id) === senderId
        );
        if (targetFriend) {
          targetFriend.unreadCount = (targetFriend.unreadCount || 0) + 1;
          
          // 如果能找到好友昵称，则提示；否则不提示
          const friendName = targetFriend.nickname || targetFriend.username;
          if (friendName) {
            ElMessage({
              message: `收到 ${friendName} 的新消息`,
              type: 'success',
              duration: 3000
            });
          }
        }
      }
    } else if (data.type == '1106') {
       // 上线通知
       // 确保 sender.userId 转为字符串比较，并增加空值保护
       const onlineUserId = String(data.chatMsg?.sender?.userId || data.chatMsg?.sendUserId || '');
       
       // 更新好友列表状态
       const friend = friendList.value.find(f => String(f.userId || f.id) === onlineUserId);
       if (friend) {
         friend.online = true;
         ElMessage.success(`${friend.nickname || friend.username} 上线啦`);
       }
    } else if (data.type == '1107') {
      // 下线通知 (如果后端实现了)
       const offlineUserId = String(data.chatMsg?.sender?.userId || data.chatMsg?.sendUserId || '');
 
       const friend = friendList.value.find(f => String(f.userId || f.id) === offlineUserId);
       if (friend) {
         friend.online = false;
         // ElMessage.info(`${friend.nickname || friend.username} 下线了`); // 可选提示
       }
    } else if (data.type == '1201') {
      // 收到群聊消息
      const groupMsg = data.groupMsg;
      
      // --- 日志监控：确认群聊消息送达 ---
      const msgSenderId = String(groupMsg.sender?.userId || groupMsg.sendUserId || '');
      const isFromMe = msgSenderId === String(userInfo.userId);
      
      console.log(`%c[群聊消息] ${isFromMe ? '发送成功(同步)' : '收到成员消息'}`, 'color: #1890ff; font-weight: bold; font-size: 12px;');
      console.table({
        '群组ID': groupMsg.groupId,
        '发送者ID': msgSenderId,
        '发送者昵称': groupMsg.sender?.nickname || groupMsg.sender?.username || '未知',
        '消息内容': groupMsg.msg || groupMsg.content,
        '消息类型': groupMsg.msgType || '1'
      });
      // --------------------------------

      if (groupMsg) {
        const currentGroupId = String(currentGroup.value?.groupId || currentGroup.value?.id || '');
        const msgGroupId = String(groupMsg.groupId || '');
        // 适配 UserDef sender
        const senderId = String(groupMsg.sender?.userId || groupMsg.sendUserId || '');
        const myId = String(userInfo.userId || '');

        // 如果是当前正在聊天的群组
        if (currentChatType.value === 'group' && currentGroupId && currentGroupId === msgGroupId) {
          // 如果是自己发的消息，且已经在本地显示过了（通过 msgId 或其他机制去重），这里可以忽略
          if (senderId !== myId) {
             messageList.value.push({
              id: groupMsg.id || Date.now(),
              content: groupMsg.msg || groupMsg.content,
              isMine: false,
              type: 'text',
              createTime: groupMsg.createTime || new Date().toISOString(), // 确保有时间
              senderId: senderId, // 用于显示发送者名字
              // 优先获取昵称，其次用户名，最后 fallback 到 ID (在模板中处理)
              senderName: groupMsg.sender?.nickname || groupMsg.sender?.username || groupMsg.nickname || groupMsg.username,
              senderAvatar: groupMsg.sender?.faceImage || groupMsg.faceImage
            });
            
            nextTick(() => {
              scrollToBottom(true);
            });
          }
        } else {
          // 增加群组未读消息计数
          const targetGroup = groupList.value.find(g => String(g.id) === msgGroupId);
          if (targetGroup) {
            targetGroup.unreadCount = (targetGroup.unreadCount || 0) + 1;
            
            // 可选：如果不在当前群聊，也可以弹出提示
            // ElMessage({
            //   message: `收到 ${targetGroup.groupName} 的新消息`,
            //   type: 'info',
            //   duration: 3000
            // });
          }
        }
      }
    }
  } catch (error) {
    console.error('处理消息失败:', error);
  }
};

const getFriendList = async () => {
  try {
    const response = await friendApi.getFriendList();
    console.log('好友列表原始响应:', response);
    
    let list = [];
    // 适配拦截器返回的完整响应结构 {code, msg, data}
    if (response.code === 1000 && response.data) {
      list = response.data;
    } else if (Array.isArray(response)) {
      // 兼容旧格式：直接返回数组
      list = response;
    } else if (response && response.list) {
      // 兼容其他格式
      list = response.list;
    } else if (response && (response.userId || response.id)) {
      list = [response];
    }
      
    // 确保每个好友对象都有 online 字段处理
    friendList.value = list.map(f => ({
      ...f,
      // 如果后端没传 online，默认为 false，否则保留后端的值
      online: f.online !== undefined ? f.online : false,
      unreadCount: 0, // 初始化未读数为 0
      directorMode: f.directorMode !== undefined ? f.directorMode : false // 初始化导演模式为关闭
    }));
    // 获取好友列表后，立即去查未读数
    getUnreadCounts();
  } catch (error) {
    console.error('获取好友列表出错:', error);
  }
};

// 处理导演模式切换
const handleDirectorModeChange = (friend) => {
  const friendId = String(friend.userId || friend.id);
  const targetFriend = friendList.value.find(f => String(f.userId || f.id) === friendId);
  
  if (targetFriend) {
    targetFriend.directorMode = friend.directorMode;
    console.log(`导演模式切换: ${friend.nickname || friend.username} -> ${friend.directorMode ? '开启' : '关闭'}`);
  }
  
  // 如果当前正在和这个模型聊天，也更新 currentFriend 的状态
  const currentId = String(currentFriend.value?.userId || currentFriend.value?.id || '');
  if (currentId === friendId) {
    currentFriend.value.directorMode = friend.directorMode;
  }
};

const getFriendRequests = async () => {
  try {
    const res = await friendApi.getFriendRequests();
    // 兼容处理：如果没有 code 或者 code 为 1000/200 都视为成功
    // request.js 拦截器可能已经处理了直接返回 data 的情况
    // 这里 res 可能是数组（被拦截器处理过）或者包含 data 的对象
    let list = [];
    if (Array.isArray(res)) {
      list = res;
    } else if (res && Array.isArray(res.data)) {
      list = res.data;
    } else if (res && res.list) {
      list = res.list;
    }
    
    console.log('好友申请列表:', list);

    friendRequestList.value = list.map(item => ({
      ...item,
      // 适配字段：如果后端返回的是 sendUserId，映射为 userId 以便统一渲染
      userId: item.sendUserId || item.userId || item.id,
      username: item.sendNickname || item.sendUsername || item.nickname || item.username || ('用户' + (item.sendUserId || item.userId)),
      faceImage: item.sendFaceImage || item.faceImage || item.face_image,
      isRequest: true
    }));
  } catch (error) {
    console.error('获取好友申请失败:', error);
  }
};

const handleGroupSearch = async (text) => {
  if (!groupListRef.value) return;
  if (!text.trim()) {
    groupListRef.value.isSearching = false;
    groupListRef.value.searchResultList = [];
    return;
  }
  groupListRef.value.isSearching = true;
  groupListRef.value.searchResultList = [];
  try {
    const localResult = groupList.value
      .filter(g => g.groupName && g.groupName.includes(text))
      .map(g => ({ ...g, isJoined: true, isGroup: true }));
    if (localResult.length > 0) {
      groupListRef.value.searchResultList = localResult;
    } else {
      const response = await groupApi.searchGroup(text);
      // 适配拦截器返回的完整响应结构 {code, msg, data}
      const data = response.code === 1000 ? response.data : response;
      let results = Array.isArray(data) ? data : (data && data.list ? data.list : (data ? [data] : []));
      groupListRef.value.searchResultList = results.map(g => ({
        ...g,
        id: g.id || g.groupId,
        groupName: g.groupName || g.name,
        faceImage: g.faceImage || g.avatar,
        isJoined: g.isJoined !== undefined ? g.isJoined : false,
        isGroup: true
      }));
    }
  } catch (error) {
    console.error('搜索群组失败:', error);
    groupListRef.value.searchResultList = [];
  }
};

const handleFriendSearch = async (text) => {
  if (!friendListRef.value) return;
  if (!text.trim()) {
    friendListRef.value.isSearching = false;
    friendListRef.value.searchResultList = [];
    return;
  }
  friendListRef.value.isSearching = true;
  friendListRef.value.searchResultList = [];
  try {
    const localResult = friendList.value
      .filter(f =>
        (f.nickname && f.nickname.includes(text)) ||
        (f.username && f.username.includes(text))
      )
      .map(f => ({ ...f, isFriend: true, isGroup: false }));
    if (localResult.length > 0) {
      friendListRef.value.searchResultList = localResult;
    } else {
      const response = await friendApi.searchFriend(text);
      // 适配拦截器返回的完整响应结构 {code, msg, data}
      const data = response.code === 1000 ? response.data : response;
      let results = Array.isArray(data) ? data : (data && data.list ? data.list : (data ? [data] : []));
      friendListRef.value.searchResultList = results.map(user => {
        const targetId = String(user.userId || user.id);
        const isAlreadyFriend = friendList.value.some(f => String(f.userId || f.id) === targetId);
        return { ...user, isFriend: isAlreadyFriend, isGroup: false };
      });
    }
  } catch (error) {
    console.error('搜索好友失败:', error);
    friendListRef.value.searchResultList = [];
  }
};

const handleAddFriend = async (friend) => {
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
    ElMessage.error('服务器连接已断开');
    return;
  }

  const addFriendMsg = {
    type: 1104,
    chatMsg: {
      sender: { userId: userInfo.userId },
      acceptUserId: friend.userId || friend.id
    },
    extend: ''
  };

  try {
    // 使用二进制协议发送
    await sendBinaryMessage(encodeProtocol(addFriendMsg));
    ElMessage.success('好友申请已发送');
  } catch (error) {
    console.error(error);
    ElMessage.error('发送失败');
  }
};

const handleAcceptFriend = async (friend) => {
  const targetId = friend.userId || friend.sendUserId || friend.id;
  
  if (!targetId) {
    ElMessage.error('无法获取用户ID');
    return;
  }

  try {
    const res = await friendApi.acceptFriend(targetId);
    // 兼容处理：code 1000 或 200 均视为成功
    if (res.code === 1000 || res.code === 200) {
      ElMessage.success('已添加好友');
      getFriendList();
      getFriendRequests(); // 刷新好友申请列表
    } else {
      ElMessage.error(res.msg || '操作失败');
    }
  } catch (error) {
    console.error(error);
    ElMessage.error('操作失败');
  }
};

const selectFriend = async (friend) => {
  if (friend.isRequest) return; // 如果是好友申请，点击不进入聊天

  // 选中好友时，关闭 RAG 视图，切换回聊天模式
  showRag.value = false;
  
  currentChatType.value = 'private';
  currentGroup.value = {}; // 清空群组选择

  console.log('选择好友:', friend);
  currentFriend.value = friend;
  const targetId = friend.userId || friend.id;

  // 点击好友后，立即清空该好友的未读计数
  friend.unreadCount = 0;

  // 重置分页状态
  messageList.value = [];
  lastTimestamp.value = Date.now(); // 初始请求使用当前时间戳
  lastMsgId.value = null;
  hasMoreHistory.value = true;

  if (targetId) {
    // 如果是老朋友 LLM，从 /llm/history 获取聊天历史
    if (friend.role === 1 || friend.isOldFriend) {
      try {
        const res = await request.post('/llm/history', {
          llmId: targetId,
          lastTime: Date.now(),
          lastId: null
        });

        let historyList = [];
        if (res && res.data && Array.isArray(res.data)) {
          historyList = res.data;
        } else if (Array.isArray(res)) {
          historyList = res;
        }

        // 将后端返回的 LlmMsgHistoryVo 转换为前端需要的消息格式（后端返回DESC需reverse成oldest在顶）
        const mapped = historyList.map(msg => {
          // 尝试解析 msgContent 是否为结构化 blocks 格式
          let blocks = null;
          let emotion = null;
          let content = msg.msgContent;
          try {
            const parsed = typeof msg.msgContent === 'string' ? JSON.parse(msg.msgContent) : msg.msgContent;
            if (Array.isArray(parsed)) {
              blocks = parsed;
              content = null;
            } else if (parsed?.blocks && Array.isArray(parsed.blocks)) {
              blocks = parsed.blocks;
              emotion = parsed.emotion || null;
              content = null;
            }
          } catch (e) {
            // 解析失败，保持原有 content 格式
          }

          return {
            id: msg.id,
            content: content,
            blocks: blocks,
            emotion: emotion,
            isMine: msg.isHuman,
            type: 'text',
            createTime: msg.createTime,
            senderId: msg.isHuman ? msg.sendUserId : msg.llmId,
            senderName: msg.isHuman ? (userInfo.nickname || userInfo.username) : (friend.nickname || friend.username),
            senderAvatar: msg.isHuman ? resolveAvatarUrl(userInfo.faceImage || userInfo.face_image) : resolveAvatarUrl(friend.faceImage || friend.face_image)
          };
        }).reverse();

        messageList.value = mapped;

        // 更新分页游标（reverse后，第一条是最旧的）
        if (mapped.length > 0) {
          lastMsgId.value = mapped[0].id;
          const timeValue = mapped[0].createTime;
          lastTimestamp.value = !isNaN(timeValue) && typeof timeValue !== 'boolean'
            ? Number(timeValue)
            : new Date(timeValue).getTime();
        }

        nextTick(() => {
          scrollToBottom(true);
        });
      } catch (error) {
        console.error('获取 LLM 历史记录失败:', error);
      }
    } else {
      // 1. 获取聊天历史
      await getChatHistory(targetId, true);
      // 2. 签收未读消息，带上当前好友 ID
      await signUnreadMessages(targetId);
    }
  } else {
    console.error('无法从好友对象中获取 ID:', friend);
    ElMessage.error('获取好友信息失败');
  }
};

const selectGroup = async (group) => {
  // 选中群组时，关闭 RAG 视图，切换回聊天模式
  showRag.value = false;
  
  currentChatType.value = 'group';
  currentFriend.value = {}; // 清空好友选择
  
  console.log('选择群组:', group);
  currentGroup.value = group;
  const targetId = group.id || group.groupId;
  
  // 重置分页状态
  messageList.value = [];
  lastTimestamp.value = Date.now(); // 初始请求使用当前时间戳
  hasMoreHistory.value = true;
  isLoadingHistory.value = false; // 确保加载状态被重置

  if (targetId) {
    // 1. 获取群聊历史
    console.log('准备发起群聊历史请求...', targetId);
    try {
      await getChatHistory(targetId, true);
    } catch (e) {
      console.error('群聊历史请求异常:', e);
    }
    // 2. 签收群聊消息（如有需要）
    // await signGroupUnreadMessages(targetId); // 暂不处理群聊签收
  } else {
    console.error('无法从群组对象中获取 ID:', group);
    ElMessage.error('获取群组信息失败');
  }
};

const signUnreadMessages = async (friendId) => {
    try {
      // 请求未签收消息接口，带上 friendId
      const res = await messageApi.getUnsignedMessages(friendId);
      console.log('未签收消息接口原始响应:', res);
      
      // Axios response interceptor usually returns the data part directly if code is 1000/200
      // Let's handle both possible structures: {code, data, msg} or just the data string
      let msgIds = null;
      
      if (res && res.code === 1000 && res.data) {
        msgIds = typeof res.data === 'object' ? res.data.msgId : res.data;
      } else if (typeof res === 'string') {
        // Interceptor might have stripped the outer wrapper and returned the data directly
        msgIds = res;
      } else if (res && typeof res === 'object' && res.msgId) {
        msgIds = res.msgId;
      }
      
      console.log('解析到的待签收 msgIds:', msgIds);
        
      if (msgIds && ws.value && ws.value.readyState === WebSocket.OPEN) {
        const signMsg = {
          type: 1102,
          chatMsg: {
            sender: { userId: String(friendId) } // 发送给好友的ID
          },
          extend: String(msgIds) // 确保是字符串
        };
        // 发送二进制签收帧
        await sendBinaryMessage(encodeProtocol(signMsg));
        console.log('WS 批量签收发送成功, extend:', signMsg.extend);
      } else {
        console.warn('未发送 WS 签收请求: msgIds 为空或 WS 未连接', { msgIds, wsReadyState: ws.value?.readyState });
      }
    } catch (error) {
      console.error('批量签收未读消息失败:', error);
    }
};

const getChatHistory = async (targetId, isFirstLoad = false) => {
  if (isLoadingHistory.value || (!hasMoreHistory.value && !isFirstLoad)) {
    console.warn('跳过历史记录加载: loading=', isLoadingHistory.value, 'hasMore=', hasMoreHistory.value, 'firstLoad=', isFirstLoad);
    return;
  }

  try {
    isLoadingHistory.value = true;
    console.log(`发起历史记录请求 -> targetId: ${targetId}, type: ${currentChatType.value}, timestamp: ${lastTimestamp.value}`);
    
    let data;
    if (currentFriend.value && (currentFriend.value.role === 1 || currentFriend.value.isOldFriend)) {
      // LLM 聊天历史（滚动分页）
      const res = await request.post('/llm/history', {
        llmId: targetId,
        lastTime: lastTimestamp.value,
        lastId: lastMsgId.value
      });
      // 适配拦截器返回的完整响应结构 {code, msg, data}
      data = (res && res.code === 1000 && res.data) ? res.data : (res && res.data) ? res.data : (Array.isArray(res) ? res : []);
    } else if (currentChatType.value === 'group') {
      console.log('调用 groupApi.getGroupChatHistory...');
      const res = await groupApi.getGroupChatHistory({
        groupId: targetId,
        lastTimestamp: lastTimestamp.value
      });
      // 适配拦截器返回的完整响应结构 {code, msg, data}
      data = (res && res.code === 1000) ? res.data : res;
    } else {
      const res = await messageApi.getChatHistory({
        friendId: targetId,
        lastTimestamp: lastTimestamp.value
      });
      // 适配拦截器返回的完整响应结构 {code, msg, data}
      data = (res && res.code === 1000) ? res.data : res;
    }
    
    // 因为拦截器已经处理了 code != 1000 的情况（抛出异常），所以能走到这里说明请求成功
    // 我们直接处理数据即可
    const rawList = Array.isArray(data) ? data : (data?.list || []);
    
    if (rawList.length < 20) {
      hasMoreHistory.value = false;
    }

    // 后端通常返回最新的在前（倒序），但前端聊天框显示需要旧的在前（正序）
    // 所以我们将获取到的这批数据进行反转
    const formattedMsgs = rawList.map(item => {
        const myId = String(userInfo.userId || '');
        // 适配新的扁平化发送者信息字段 (sendUserId) 以及旧的嵌套 sender 对象
        const senderId = String(item.sendUserId || item.sender?.userId || '');
        // 优先使用后端返回的 msgId，如果没有则尝试使用 id
        const msgId = item.msgId || item.id;

        // 适配群聊/私聊字段差异: 优先使用 msgContent (新群聊字段)
        const msgContent = item.msgContent || item.msg || item.content || item.groupMsg?.msg || '';
        const msgType = item.msgType || '1'; // 默认 text (1)

        // isHuman 字段：true=用户发的，false=AI发的（LLM聊天用isHuman判断）
        // 没有isHuman字段时（如普通WebSocket聊天），用sendUserId判断
        const isMine = item.isHuman !== undefined && item.isHuman !== null
          ? item.isHuman === true
          : senderId === myId;

        // 尝试从好友列表匹配昵称（针对私聊历史记录，后端可能只返回ID）
        let matchedNickname = '';
        let matchedAvatar = '';
        if (currentChatType.value !== 'group' && !isMine) {
          const friend = friendList.value.find(f => String(f.userId || f.id) === senderId);
          if (friend) {
            matchedNickname = friend.nickname || friend.username;
            matchedAvatar = friend.faceImage || friend.face_image;
          }
        } else if (isMine) {
          // 如果是自己，直接从 userInfo 获取最新昵称和头像
          matchedNickname = userInfo.nickname || userInfo.username;
          matchedAvatar = userInfo.faceImage || userInfo.face_image;
        }

        // 解析 LLM 消息的 msgContent（可能是 blocks JSON 数组或对象）
        let blocks = null;
        let emotion = null;
        let content = msgContent;
        if (msgContent) {
          try {
            const parsed = typeof msgContent === 'string' ? JSON.parse(msgContent) : msgContent;
            if (Array.isArray(parsed)) {
              blocks = parsed;
              content = null;
            } else if (parsed?.blocks && Array.isArray(parsed.blocks)) {
              blocks = parsed.blocks;
              emotion = parsed.emotion || null;
              content = null;
            }
          } catch (e) {
            // 解析失败，保持原有 content 格式
          }
        }

        return {
          id: msgId,
          content: content,
          blocks: blocks,
          emotion: emotion,
          createTime: item.createTime,
          isMine: isMine,
          // 兼容数字和字符串类型的 msgType (1=text, 2=image, 3=video)
          type: String(msgType) === '2' ? 'image' : (String(msgType) === '3' ? 'video' : 'text'),
          // 状态为 false 时表示已删除，不显示
          isVisible: item.status !== false && item.status !== 'false',
          senderId: senderId,
          // 优先使用消息自带的昵称，其次使用好友列表匹配的昵称，最后 fallback 到 ID
          senderName: item.nickname || item.username || item.sender?.nickname || item.sender?.username || matchedNickname || senderId,
          senderAvatar: item.faceImage || item.sender?.faceImage || matchedAvatar,
          // 保留原始数据以备不时之需
          raw: item
        };
      })
        .filter(msg => msg.isVisible) // 过滤掉不可见（已删除）的消息
        .reverse(); // DESC 返回 newest 在前，反转成 oldest 在顶

      if (isFirstLoad) {
        messageList.value = formattedMsgs;
        nextTick(() => {
          scrollToBottom(true);
        });
      } else {
        // 向上滚动加载更多时
        const container = messageListRef.value?.$el;
        if (container) {
          const previousHeight = container.scrollHeight;
          
          // 将旧消息批次整体插入到现有消息列表的顶部
          messageList.value = [...formattedMsgs, ...messageList.value];
          
          nextTick(() => {
            container.scrollTop = container.scrollHeight - previousHeight;
          });
        } else {
          messageList.value = [...formattedMsgs, ...messageList.value];
        }
      }

      // 更新“最旧”的消息时间戳，用于下次加载更早的消息
      if (formattedMsgs.length > 0) {
        // 反转后，formattedMsgs[0] 是这批数据中最旧的一条
        const oldestMsg = formattedMsgs[0]; 
        const timeValue = oldestMsg.createTime;
        
        // 尝试解析时间戳
        let timestamp;
        if (!isNaN(timeValue) && typeof timeValue !== 'boolean') {
          timestamp = Number(timeValue);
        } else {
          timestamp = new Date(timeValue).getTime();
        }

        if (!isNaN(timestamp)) {
          lastTimestamp.value = timestamp;
          lastMsgId.value = oldestMsg.id;
          console.log('更新 lastTimestamp 为:', lastTimestamp.value);
          console.log('更新 lastMsgId 为:', lastMsgId.value);
        } else {
          console.warn('无法解析的时间戳格式:', timeValue);
        }
      }
  } catch (error) {
    console.error('加载历史记录失败:', error);
    // 只有在真正的网络错误或其他异常时才提示
    // ElMessage.error('获取历史记录失败'); 
  } finally {
    isLoadingHistory.value = false;
  }
};

const sendMessage = async () => {
  console.log('[Send] sendMessage called');
  if (!inputMessage.value.trim()) {
    console.warn('[Send] Message content is empty');
    return;
  }

  // 如果是在 RAG 模式下，执行 RAG 搜索逻辑
  if (showRag.value) {
    await searchRagFiles(inputMessage.value);
    // 搜索完后清空输入框，但保持按钮禁用状态（根据用户要求）
    inputMessage.value = '';
    return;
  }

  // 如果当前是“老朋友”聊天（LLM 模式），使用 HTTP POST 请求
  if (currentFriend.value && (currentFriend.value.role === 1 || currentFriend.value.isOldFriend)) {
    const msgContent = inputMessage.value;
    const msgId = snowflake.nextId();
    const myId = String(userInfo.userId || '');
    const llmId = currentFriend.value.userId || currentFriend.value.id;
    
    // 1. 立即渲染自己的消息
    messageList.value.push({
      id: msgId,
      content: msgContent,
      isMine: true,
      type: 'text',
      createTime: new Date().toISOString(),
      senderId: myId,
      senderName: userInfo.nickname || userInfo.username,
      senderAvatar: userInfo.faceImage || userInfo.face_image
    });

    inputMessage.value = '';
    nextTick(() => {
      scrollToBottom(true);
    });

    // 2. 发送 HTTP POST 请求给 LLM 接口，静默模式不触发全局 loading
    llmPendingCount.value++;
    isLlmTyping.value = true;
    try {
      // 记录发送请求时的好友 ID
      const requestFriendId = llmId;
      
      // 根据导演模式状态选择不同的接口
      const isDirectorMode = currentFriend.value.directorMode === true;
      const apiEndpoint = isDirectorMode ? '/llm/superChat' : '/llm/chat';
      console.log(`[LLM Chat] 使用${isDirectorMode ? '导演模式' : '普通模式'}接口: ${apiEndpoint}`);

      const res = await request.post(apiEndpoint, {
        llmId: llmId,
        msgContent: msgContent
      }, {
        silent: true, // 告诉 request.js 拦截器：这个请求悄悄发，不要全屏加载
        timeout: 120000 // 针对大模型单独设置 120 秒超时时间
      });

      console.log('[LLM Chat] 原始响应 res:', res, typeof res);

      // 3. 渲染回复
      let replyBlocks = null;
      let replyEmotion = null;

      // 拦截器现在返回完整响应 {code, msg, data}
      // 需要先提取 res.data，然后处理
      let actualResponse = res;
      if (res && res.code === 1000 && res.data) {
        actualResponse = res.data;
      }

      // 后端返回的是消息列表数组，需要找到 AI 回复的那条
      if (Array.isArray(actualResponse)) {
        // 找到 isHuman: false 的消息（AI回复）
        const aiMsg = actualResponse.find(m => m.isHuman === false);
        if (aiMsg && aiMsg.msgContent) {
          try {
            const parsed = JSON.parse(aiMsg.msgContent);
            if (parsed.blocks) {
              replyBlocks = parsed.blocks;
              replyEmotion = parsed.emotion;
            } else if (Array.isArray(parsed)) {
              replyBlocks = parsed;
            } else {
              replyBlocks = [{ type: 'text', text: aiMsg.msgContent }];
            }
          } catch (e) {
            replyBlocks = [{ type: 'text', text: aiMsg.msgContent }];
          }
        }
      } else if (actualResponse && actualResponse.msgId && actualResponse.data) {
        // M.get_msg 包装格式 { msgId, data }
        const innerData = actualResponse.data;
        if (Array.isArray(innerData)) {
          const aiMsg = innerData.find(m => m.isHuman === false);
          if (aiMsg && aiMsg.msgContent) {
            try {
              const parsed = JSON.parse(aiMsg.msgContent);
              if (parsed.blocks) {
                replyBlocks = parsed.blocks;
                replyEmotion = parsed.emotion;
              } else {
                replyBlocks = [{ type: 'text', text: aiMsg.msgContent }];
              }
            } catch (e) {
              replyBlocks = [{ type: 'text', text: aiMsg.msgContent }];
            }
          }
        } else if (innerData.blocks) {
          replyBlocks = innerData.blocks;
          replyEmotion = innerData.emotion;
        }
      } else if (actualResponse && actualResponse.msg) {
        // actualResponse.msg 是 JSON 字符串，需要解析是否为 blocks 格式
        try {
          const parsed = typeof actualResponse.msg === 'string' ? JSON.parse(actualResponse.msg) : actualResponse.msg;
          if (parsed && parsed.blocks && Array.isArray(parsed.blocks)) {
            replyBlocks = parsed.blocks;
            replyEmotion = parsed.emotion || null;
          } else if (Array.isArray(parsed)) {
            replyBlocks = parsed;
          } else {
            replyBlocks = [{ type: 'text', text: actualResponse.msg }];
          }
        } catch (e) {
          replyBlocks = [{ type: 'text', text: actualResponse.msg }];
        }
      } else if (typeof actualResponse === 'string') {
        replyBlocks = [{ type: 'text', text: actualResponse }];
      } else {
        replyBlocks = [{ type: 'text', text: JSON.stringify(actualResponse) }];
      }

      // 只有当当前选中的好友还是刚才发请求的那位时，才把消息推入当前的 messageList
      if (currentFriend.value && (currentFriend.value.userId || currentFriend.value.id) === requestFriendId) {
        messageList.value.push({
          id: snowflake.nextId(),
          content: null,
          blocks: replyBlocks,
          emotion: replyEmotion,
          isMine: false,
          type: 'text',
          createTime: new Date().toISOString(),
          senderId: llmId,
          senderName: currentFriend.value.nickname || currentFriend.value.username,
          senderAvatar: resolveAvatarUrl(currentFriend.value.faceImage || currentFriend.value.face_image) || defaultUserAvatar
        });

        // 更新好友列表中的emotion
        if (replyEmotion) {
          currentFriend.value.emotion = replyEmotion;
          const friend = friendList.value.find(f => String(f.userId || f.id) === String(requestFriendId));
          if (friend) {
            friend.emotion = replyEmotion;
          }
        }

        nextTick(() => {
          scrollToBottom(true);
        });
      }
    } catch (error) {
      console.error('LLM 聊天请求失败:', error);

      // 处理配置不完整错误（15001）
      if (error && error.code === 15001) {
        ElMessage.warning('请先完成模型配置后再开始聊天（点击侧边栏设置按钮进行配置）');
        return;
      }

      // 处理其他 LLM 配置错误
      if (error && error.code >= 15002 && error.code <= 15005) {
        ElMessage.error(error.msg || '模型调用失败，请检查配置');
        return;
      }

      ElMessage.error('他/她好像暂时没法回应你，请稍后再试吧~');
    } finally {
      llmPendingCount.value--;
      if (llmPendingCount.value <= 0) {
        llmPendingCount.value = 0;
        isLlmTyping.value = false;
      }
    }
    return;
  }

  const myId = String(userInfo.userId || '');
  const msgContent = inputMessage.value;
  const msgId = snowflake.nextId();
  
  console.log('[Send] msgId:', msgId, 'content:', msgContent, 'currentChatType:', currentChatType.value);

  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
    console.error('[Send] WebSocket not connected or not ready. readyState:', ws.value?.readyState);
    ElMessage.error('服务器连接已断开，请刷新页面');
    return;
  }

  try {
    if (currentChatType.value === 'private') {
      const targetFriend = currentFriend.value;
      const targetId = targetFriend.userId || targetFriend.id;
      console.log('[Send] Private chat. targetId:', targetId);

      if (!targetId) {
          console.warn('[Send] No target friend selected');
          ElMessage.warning('请先选择好友');
          return;
      }

      const chatData = {
        type: 1101, // 私聊消息
        targetType: 1, // 目标种类：1私聊
        chatMsg: {
          id: msgId,
          sender: { userId: myId },
          acceptUserId: String(targetId),
          msg: msgContent
        },
        extend: ""
      };

      console.log('[Send] Encoding protocol data:', chatData);
      const binaryData = encodeProtocol(chatData);
      console.log('[Send] Protocol data encoded successfully, length:', binaryData.byteLength);
      
      sendBinaryMessage(binaryData);
      
      console.log('[Send] Adding to messageList');
      messageList.value.push({
        id: msgId,
        content: msgContent,
        isMine: true,
        type: 'text',
        createTime: new Date().toISOString(),
        senderId: myId,
        senderName: userInfo.nickname || userInfo.username,
        senderAvatar: userInfo.faceImage || userInfo.face_image
      });

      inputMessage.value = '';
      nextTick(() => {
        scrollToBottom(true);
      });

    } else if (currentChatType.value === 'group') {
      const targetGroup = currentGroup.value;
      const groupId = targetGroup.groupId || targetGroup.id;

      console.log('[Send] Group chat. groupId:', groupId);

      if (!groupId) {
        console.warn('[Send] No target group selected');
        ElMessage.warning('请先选择群组');
        return;
      }

      const groupData = {
        type: 1201, // 群聊消息
        targetType: 2, // 目标种类：2群聊
        groupMsg: {
          id: msgId,
          groupId: String(targetGroup.id),
          sender: {
            userId: myId,
            username: userInfo.username || '',
            nickname: userInfo.nickname || '',
            faceImage: userInfo.faceImage || userInfo.face_image || ''
          },
          msg: msgContent,
          msgType: '1', // 1:文本, 2:图片, 3:视频 (字符串类型)
          createTime: String(Date.now())
        }
      };
      
      console.log('[Send] Encoding protocol data (group):', groupData);
      const binaryData = encodeProtocol(groupData);
      console.log('[Send] Protocol data encoded successfully (group), length:', binaryData.byteLength);

      sendBinaryMessage(binaryData);
      
      console.log('[Send] Adding to messageList (group)');
      messageList.value.push({
        id: msgId,
        content: msgContent,
        isMine: true,
        type: 'text',
        createTime: new Date().toISOString(),
        senderId: myId,
        senderName: userInfo.nickname || userInfo.username,
        senderAvatar: userInfo.faceImage || userInfo.face_image
      });

      inputMessage.value = '';
      nextTick(() => {
        scrollToBottom(true);
      });

    }
  } catch (error) {
    console.error('发送消息失败:', error);
    ElMessage.error('发送失败');
  }
};

const scrollToBottom = (force = false) => {
  nextTick(() => {
    // 调用子组件的 scrollToBottom 方法
    if (messageListRef.value?.scrollToBottom) {
      messageListRef.value.scrollToBottom(force);
    }
  });
};

// 加载更多历史消息
const loadMoreHistory = () => {
  const targetId = currentChatType.value === 'group' 
    ? (currentGroup.value.id || currentGroup.value.groupId)
    : (currentFriend.value.userId || currentFriend.value.id);
  
  if (targetId) {
    getChatHistory(targetId, false);
  }
};

const groupList = ref([]);
const isGroupLoading = ref(false);

const getGroupList = async () => {
  try {
    isGroupLoading.value = true;
    const response = await groupApi.getGroupList();
    console.log('群组列表原始响应:', response);
    
    // 适配拦截器返回的完整响应结构 {code, msg, data}
    const data = response.code === 1000 ? response.data : response;
    
    let list = [];
    if (Array.isArray(data)) {
      list = data;
    } else if (data && data.list) {
      list = data.list;
    }
    
    groupList.value = list.map(g => ({
      ...g,
      // 适配 GroupVo 结构
      id: g.id || g.groupId,
      groupName: g.groupName || g.name,
      faceImage: g.faceImage || g.avatar,
      ownerUserId: g.ownerUserId,
      role: g.role,
      isJoined: g.isJoined !== undefined ? g.isJoined : true, // 获取列表通常意味着已加入
      unreadCount: 0 // 初始化未读数
    }));

  } catch (error) {
    console.error('获取群组列表出错:', error);
  } finally {
    isGroupLoading.value = false;
  }
};

watch(showGroupList, (newVal) => {
  if (newVal) {
    getGroupList();
  }
});
const isCreatingGroup = ref(false);
const createGroupForm = reactive({
  groupName: ''
});
const createGroupFormRef = ref(null);
const addLlmFriendForm = reactive({
  nickname: '',
  myName: '',
  partnerName: '',
  experience: ''
});
const addLlmFriendFormRef = ref(null);
const isAddingLlmFriend = ref(false);

const handleCreateGroup = async () => {
  if (!createGroupFormRef.value) return;
  
  await createGroupFormRef.value.validate(async (valid) => {
    if (valid) {
      isCreatingGroup.value = true;
      try {
        const groupDto = {
          groupName: createGroupForm.groupName
        };
        await groupApi.createGroup(groupDto);
        ElMessage.success('狐狸窝创建成功！');
        showCreateGroupDialog.value = false;
        createGroupForm.groupName = ''; // Reset form
        getGroupList(); // Refresh group list
      } catch (error) {
        console.error('创建狐狸窝失败:', error);
        ElMessage.error(error.message || '网络错误，创建失败');
      } finally {
        isCreatingGroup.value = false;
      }
    }
  });
};

const handleAddLlmFriend = async () => {
  if (!addLlmFriendFormRef.value) return;

  await addLlmFriendFormRef.value.validate(async (valid) => {
    if (valid) {
      isAddingLlmFriend.value = true;
      try {
        const dto = {
          nickname: addLlmFriendForm.nickname,
          myName: addLlmFriendForm.myName,
          partnerName: addLlmFriendForm.partnerName,
          experience: addLlmFriendForm.experience
        };
        const response = await request.post('/llm/add', dto);
        ElMessage.success('陪伴者创建成功！请配置模型参数');
        showAddLlmFriendDialog.value = false;
        addLlmFriendForm.nickname = '';
        addLlmFriendForm.myName = '';
        addLlmFriendForm.partnerName = '';
        addLlmFriendForm.experience = '';
        getFriendList();
      } catch (error) {
        console.error('添加陪伴者失败:', error);
      } finally {
        isAddingLlmFriend.value = false;
      }
    }
  });
};

const handleJoinGroup = async (group) => {
  if (group.isJoining) return;
  if (!group || !group.id) {
    ElMessage.error('无法加入群组：群组ID缺失');
    return;
  }
  
  group.isJoining = true;
  try {
    await groupApi.joinGroup(group.id);
    ElMessage.success(`成功加入 ${group.groupName}！✨`);
    // 刷新群组列表
    getGroupList();
    // 更新搜索结果中的加入状态
    const targetGroup = groupListRef.value?.searchResultList?.find(g => g.id === group.id);
    if (targetGroup) {
      targetGroup.isJoined = true;
    }
  } catch (error) {
    console.error('加入群组失败:', error);
    ElMessage.error(error.message || '加入群组失败，请稍后重试');
  } finally {
    group.isJoining = false;
  }
};

const handleGroupClick = async (group) => {
  selectGroup(group);
};

// 移除重复声明的 selectGroup，保留之前的逻辑
// const selectGroup = async (group) => { ... } 
// 已经在前面定义过了，或者我们可以把逻辑整合到 handleGroupClick 中，或者确保只定义一次。
// 鉴于之前可能在 997 行附近已经定义过 selectGroup，这里我们直接移除这段重复的代码。

const handleLogout = () => {
  if (ws.value) {
    try {
      ws.value.close(); // 主动关闭
    } catch (e) {
      console.error('Error closing WebSocket:', e);
    }
  }
  stopHeartbeat();
  localStorage.removeItem('token');
  localStorage.removeItem('userInfo');
  router.push('/login');
};
</script>

<style scoped>
.home-container {
  /* Default QQ Theme Variables */
  --bg-gradient: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  --sidebar-bg: rgba(255, 255, 255, 0.2);
  --sidebar-border: rgba(255, 255, 255, 0.3);
  --text-primary: #333;
  --text-secondary: #666;
  --text-light: #999;
  --accent-color: #0084ff;
  --accent-hover: rgba(0, 132, 255, 0.2); /* For list item hover */
  --accent-active: rgba(0, 132, 255, 0.1); /* For list item active */
  --button-bg: #0084ff;
  --button-text: #fff;
  --button-hover: #0066cc;
  --border-strong: rgba(255, 255, 255, 0.5); /* 明显的边框 */
}

/* RAG Styles */
.rag-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.rag-files-list {
  padding: 30px;
  height: 100%;
  overflow-y: auto;
}

.rag-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rag-files-grid {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.rag-files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
}

.rag-file-card {
  background: rgba(255, 255, 255, 0.7);
  /* backdrop-filter removed for performance */
  padding: 18px;
  border-radius: 12px;
  display: flex;
  flex-direction: row; /* 改为横向布局 */
  align-items: center;
  gap: 15px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  cursor: default;
}

.rag-file-card.clickable {
  cursor: pointer;
}

.rag-file-card.clickable:hover {
  transform: translateX(5px); /* 横向微移 */
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  background: #fff;
}

.file-icon-wrapper {
  width: 44px;
  height: 44px;
  background: var(--button-bg);
  border-radius: 10px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #fff;
  font-size: 20px;
  opacity: 0.9;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  text-align: left;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  display: block;
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  font-weight: 600;
}

.file-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.file-tags {
  display: flex;
  gap: 5px;
  align-items: center;
}

.score-tag {
  font-size: 10px;
  height: 18px;
  padding: 0 4px;
  border-radius: 4px;
}

.file-time {
  font-size: 12px;
  color: #999;
}

.status-tag {
  font-size: 10px;
  height: 18px;
  padding: 0 6px;
  border-radius: 4px;
}

.rag-welcome {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  padding: 20px;
}

.rag-card {
  background: rgba(255, 255, 255, 0.6);
  /* backdrop-filter removed for performance */
  padding: 40px;
  border-radius: 20px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  max-width: 400px;
  width: 100%;
}

.rag-logo-wrapper {
  width: 80px;
  height: 80px;
  background: var(--button-bg);
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 0 auto 20px;
  box-shadow: 0 4px 12px var(--accent-hover);
}

.rag-logo {
  font-size: 40px;
  color: #fff;
}

.rag-card h2 {
  margin: 0 0 10px;
  color: var(--text-primary);
}

.rag-card p {
  color: var(--text-secondary);
  margin-bottom: 20px;
}

.rag-tips {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: var(--text-light);
}

.fox-btn, .upload-btn, .send-btn {
  height: 44px;
  min-width: 90px;
  padding: 10px 24px;
  font-size: 15px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: var(--button-bg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  font-weight: 600;
  letter-spacing: 1px;
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
  margin: 0;
  line-height: normal;
}

.fox-btn:hover, .upload-btn:hover, .send-btn:hover {
  background: var(--button-bg) !important;
  opacity: 1 !important;
}

.fox-btn:active, .send-btn:active {
  transform: translateY(1px);
}

.upload-dialog-content {
  padding: 10px 0;
}

.fox-uploader :deep(.el-upload-dragger) {
  border-radius: 16px;
  border: 2px dashed var(--sidebar-border);
  background: rgba(255, 255, 255, 0.4);
  transition: all 0.3s ease;
}

.fox-uploader :deep(.el-upload-dragger):hover {
  border-color: var(--accent-color);
  background: var(--accent-active);
}

.fox-uploader .el-icon--upload {
  font-size: 60px;
  color: var(--accent-color);
  margin-bottom: 10px;
}

.fox-uploader .el-upload__text em {
  color: var(--accent-color);
  font-style: normal;
  font-weight: bold;
}

.fox-uploader .el-upload__tip {
  text-align: center;
  margin-top: 15px;
  color: var(--text-light);
}

.home-container.theme-qq {
  --chat-bg: rgba(255, 255, 255, 0.6);
  --chat-header-bg: rgba(255, 255, 255, 0.3);
  --chat-header-border: rgba(255, 255, 255, 0.3);
  --message-bg-mine: #0084ff;
  --message-text-mine: #fff;
  --message-bg-other: rgba(255, 255, 255, 0.8);
  --message-text-other: #333;
  --panel-bg: rgba(255, 255, 255, 0.4);
  --input-bg: rgba(255, 255, 255, 0.3);
  --input-border: rgba(255, 255, 255, 0.3);
  --input-inner-bg: rgba(255, 255, 255, 0.5);
  --badge-bg: #ff4d4f;
  --menu-icon-color: #666;
  --menu-icon-active: #0084ff;

  display: flex;
  height: 100vh;
  width: 100vw;
  background: var(--bg-gradient);
  overflow: hidden;
  transition: background 0.5s ease;
  position: relative; /* Prevent absolute children from expanding bounds */
}

/* Sidebar */
.sidebar {
  width: 70px;
  background-color: var(--sidebar-bg);
  /* backdrop-filter removed for performance */
  border-right: 1px solid var(--sidebar-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 30px;
}

.avatar-container {
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  width: 100%;
}

.send-btn {
  min-width: 90px;
  position: relative;
  overflow: hidden;
}

.loading-icon {
  animation: rotating 2s linear infinite;
  font-size: 18px;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.avatar-wrapper {
  padding: 3px;
  border-radius: 50%;
  background: transparent;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-container:hover .avatar-wrapper {
  transform: scale(1.1);
}

.avatar-container .el-avatar {
  border: 2px solid #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.username {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-items {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.menu-item {
  width: 40px;
  height: 40px;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 15px;
  cursor: pointer;
  color: var(--menu-icon-color);
  font-size: 24px;
  transition: all 0.3s;
}

.menu-item:hover, .menu-item.active {
  color: var(--menu-icon-active);
}

/* Chat Area */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--chat-bg);
  /* backdrop-filter removed for performance */
  position: relative;
  transition: margin-right 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden; /* Prevent scrollbars when sidebar is toggled */
}

.chat-area.shrink-right {
  margin-right: 300px;
}

.chat-header {
  height: 70px;
  /* backdrop-filter removed for performance */
  background-color: var(--chat-header-bg);
  border-bottom: 1px solid var(--chat-header-border);
  display: flex;
  align-items: center;
  justify-content: space-between; /* Space out title and actions */
  padding: 0 30px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.emotion-emoji {
  font-size: 18px;
  line-height: 1;
}

/* Typing indicator animation */
.typing-indicator {
  display: inline-flex;
  gap: 4px;
  margin-left: 8px;
}

.typing-dot {
  width: 6px;
  height: 6px;
  background: var(--accent-color);
  border-radius: 50%;
  animation: typing-bounce 1.4s infinite ease-in-out;
}

.typing-dot:nth-child(1) { animation-delay: 0s; }
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

.chat-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.action-btn {
  border: none;
  background-color: transparent;
  color: #666;
  font-size: 18px;
  transition: all 0.3s;
}

.action-btn:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #0084ff;
  transform: scale(1.1);
}

.selection-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.withdraw-btn {
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.withdraw-btn:not(.is-disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.4);
}

.withdraw-btn:not(.is-disabled):active {
  transform: translateY(0);
}

/* Fade Scale Transition */
.fade-scale-enter-active, .fade-scale-leave-active {
  transition: all 0.3s ease;
}

.fade-scale-enter-from, .fade-scale-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

/* Friend List - 已移至 FriendList.vue 组件 */

/* Element Plus Button Override */
:deep(.el-button--primary) {
  background-color: var(--button-bg);
  border-color: var(--button-bg);
  color: var(--button-text);
}

:deep(.el-button--primary:hover),
:deep(.el-button--primary:focus) {
  background-color: var(--button-bg);
  border-color: var(--button-bg);
  color: var(--button-text);
}

:deep(.el-button--primary.is-disabled) {
  background-color: var(--button-bg);
  border-color: var(--button-bg);
  opacity: 0.5;
}

:deep(.el-button--primary.is-disabled:hover) {
  background-color: var(--button-bg);
  border-color: var(--button-bg);
  opacity: 0.5;
}

/* Checkbox Override */
:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--accent-color);
  border-color: var(--accent-color);
}

:deep(.el-checkbox__input.is-checked + .el-checkbox__label) {
  color: var(--accent-color);
}

.owner-badge {
  font-size: 16px;
  margin-left: 5px;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

/* Profile Detail Styles */
.profile-detail {
  background: rgba(255, 255, 255, 0.7);
  /* backdrop-filter removed for performance */
  display: flex;
  flex-direction: column;
  border-left: 1px solid rgba(255, 255, 255, 0.3);
  position: absolute;
  top: 0;
  right: 0;
  height: 100%;
  width: 300px;
  z-index: 10;
  box-shadow: -4px 0 15px rgba(0,0,0,0.05);
  overflow-y: auto;
}

.profile-header {
  padding: 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  text-align: center;
}

.profile-header h3 {
  margin: 0;
  font-weight: 600;
  color: #262626;
}

.profile-content {
  padding: 30px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.profile-avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 30px;
}

.edit-avatar-btn {
  margin-top: 15px;
}

.edit-avatar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.edit-llm-avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0 30px;
}

.edit-llm-avatar-wrapper {
  position: relative;
  cursor: pointer;
  border-radius: 50%;
}

.edit-llm-avatar-wrapper .el-avatar {
  display: block;
}

.edit-llm-avatar-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  font-size: 13px;
}

.edit-llm-avatar-wrapper:hover .edit-llm-avatar-mask {
  opacity: 1;
}

.edit-llm-avatar-mask .el-icon {
  margin-bottom: 4px;
}

.edit-llm-nickname {
  margin-top: 16px;
  width: 200px;
  text-align: center;
}

.info-list {
  width: 100%;
  margin-bottom: 30px;
}

.info-item-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.info-item-input label {
  color: #8e8e8e;
  font-size: 13px;
  padding-left: 4px;
}

.profile-actions-vertical {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 20px;
}

.profile-actions-vertical .el-button {
  width: 100%;
  margin-left: 0;
}

/* Slide Fade Transition */
.slide-fade-enter-active, .slide-fade-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-enter-from, .slide-fade-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

.no-result {
  padding: 20px;
  text-align: center;
  color: rgba(0, 0, 0, 0.4);
  font-size: 14px;
}

/* Group Title Styling */
.group-title {
  padding: 8px 16px;
  background: linear-gradient(90deg, var(--button-bg), var(--button-hover));
  color: var(--button-text);
  border-radius: 20px;
  margin: 10px 15px;
  font-weight: bold;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  display: block;
  font-size: 14px;
  letter-spacing: 1px;
  transition: all 0.3s ease;
}

.group-title:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}
</style>
