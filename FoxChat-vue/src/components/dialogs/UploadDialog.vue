<template>
  <FoxModal v-model="showUploadDialog" title="狐狸知识库上传" width="500px">
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
      <FoxButton type="ghost" @click="showUploadDialog = false">关闭</FoxButton>
      <FoxButton type="primary" :loading="isUploading" @click="submitBatchUpload">开始上传</FoxButton>
    </template>
  </FoxModal>
</template>

<script setup>
import { watch } from 'vue';
import { UploadFilled } from '@element-plus/icons-vue';
import { FoxModal, FoxButton } from '@/components/FoxUI';
import { useUiStore } from '@/stores/uiStore';
import { useRag } from '@/composables/useRag';

const { showUploadDialog } = useUiStore();
const { isUploading, pendingFiles, handleBeforeUpload, handleUploadRequest, submitBatchUpload } = useRag();

watch(showUploadDialog, (val) => {
  if (!val) {
    pendingFiles.value = [];
  }
});
</script>

<style scoped>
.upload-dialog-content {
  display: flex;
  justify-content: center;
}
.fox-uploader {
  width: 100%;
}
</style>
