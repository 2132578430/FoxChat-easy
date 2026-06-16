<template>
  <FoxModal v-model="showCreateGroupDialog" title="新建狐狸窝" width="400px">
    <FoxInput v-model="createGroupForm.groupName" placeholder="给狐狸窝起个名字吧" />
    <template #footer>
      <FoxButton type="ghost" @click="showCreateGroupDialog = false">取消</FoxButton>
      <FoxButton type="primary" :loading="isCreatingGroup" @click="onCreateGroup">创建</FoxButton>
    </template>
  </FoxModal>
</template>

<script setup>
import { ref } from 'vue';
import { FoxModal, FoxInput, FoxButton, FoxToast } from '@/components/FoxUI';
import { useUiStore } from '@/stores/uiStore';
import { useGroupStore } from '@/stores/groupStore';
import { useGroups } from '@/composables/useGroups';

const { showCreateGroupDialog } = useUiStore();
const { createGroupForm } = useGroupStore();
const { isCreatingGroup, handleCreateGroup } = useGroups();
const createGroupFormRef = ref(null);

const onCreateGroup = () => {
  if (!createGroupForm.groupName.trim()) {
    FoxToast.warning('请输入狐狸窝名字');
    return;
  }
  handleCreateGroup(createGroupFormRef.value);
};
</script>
