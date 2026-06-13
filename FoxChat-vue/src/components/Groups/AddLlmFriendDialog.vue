<template>
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
        <el-button type="primary" @click="onAddLlmFriend" :loading="isAddingLlmFriend">创造</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue';
import { useUiStore } from '@/stores/uiStore';
import { useGroupStore } from '@/stores/groupStore';
import { useGroups } from '@/composables/useGroups';

const { showAddLlmFriendDialog } = useUiStore();
const { addLlmFriendForm } = useGroupStore();
const { isAddingLlmFriend, handleAddLlmFriend } = useGroups();
const addLlmFriendFormRef = ref(null);

const onAddLlmFriend = () => {
  handleAddLlmFriend(addLlmFriendFormRef.value);
};
</script>
