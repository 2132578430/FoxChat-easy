<template>
  <FoxModal v-model="showAddLlmFriendDialog" title="创造 AI 陪伴者" width="440px">
    <el-form :model="addLlmFriendForm" ref="addLlmFriendFormRef" label-width="60px">
      <el-form-item label="昵称" prop="nickname" :rules="[{ required: true, message: '请输入昵称', trigger: 'blur' }, { max: 30, message: '昵称不能超过30个字', trigger: 'blur' }]">
        <FoxInput v-model="addLlmFriendForm.nickname" placeholder="我的网名叫什么" />
      </el-form-item>
      <el-form-item label="你是" prop="myName" :rules="[{ required: true, message: '请输入创造者名字', trigger: 'blur' }, { max: 30, message: '名字不能超过30个字', trigger: 'blur' }]">
        <FoxInput v-model="addLlmFriendForm.myName" placeholder="我的创造者叫什么名字" />
      </el-form-item>
      <el-form-item label="我是" prop="partnerName" :rules="[{ required: true, message: '请输入我的名字', trigger: 'blur' }, { max: 30, message: '名字不能超过30个字', trigger: 'blur' }]">
        <FoxInput v-model="addLlmFriendForm.partnerName" placeholder="我是谁？" />
      </el-form-item>
      <el-form-item label="经历" prop="experience" :rules="[{ required: true, message: '请输入经历', trigger: 'blur' }, { max: 10000, message: '经历不能超过10000个字', trigger: 'blur' }]">
        <FoxInput v-model="addLlmFriendForm.experience" type="textarea" :rows="5" placeholder="你想要和我有什么经历？" />
      </el-form-item>
    </el-form>
    <template #footer>
      <FoxButton type="ghost" @click="showAddLlmFriendDialog = false">取消</FoxButton>
      <FoxButton type="primary" :loading="isAddingLlmFriend" @click="onAddLlmFriend">创造</FoxButton>
    </template>
  </FoxModal>
</template>

<script setup>
import { ref } from 'vue';
import { FoxModal, FoxInput, FoxButton } from '@/components/FoxUI';
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
