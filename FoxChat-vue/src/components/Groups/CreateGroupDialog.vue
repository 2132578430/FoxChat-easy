<template>
  <el-dialog v-model="showCreateGroupDialog" title="新建狐狸窝" width="400px" center destroy-on-close>
    <el-form :model="createGroupForm" ref="createGroupFormRef" label-width="100px">
      <el-form-item label="狐狸窝名" prop="groupName" :rules="[{ required: true, message: '请输入狐狸窝名字', trigger: 'blur' }]">
        <el-input v-model="createGroupForm.groupName" placeholder="给狐狸窝起个名字吧"></el-input>
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="showCreateGroupDialog = false">取消</el-button>
        <el-button type="primary" @click="onCreateGroup" :loading="isCreatingGroup">创建</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue';
import { useUiStore } from '@/stores/uiStore';
import { useGroupStore } from '@/stores/groupStore';
import { useGroups } from '@/composables/useGroups';

const { showCreateGroupDialog } = useUiStore();
const { createGroupForm } = useGroupStore();
const { isCreatingGroup, handleCreateGroup } = useGroups();
const createGroupFormRef = ref(null);

const onCreateGroup = () => {
  handleCreateGroup(createGroupFormRef.value);
};
</script>
