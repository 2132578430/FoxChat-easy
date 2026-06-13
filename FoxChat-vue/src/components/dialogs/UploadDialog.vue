<template>
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
</template>

<script setup>
import { watch } from 'vue';
import { UploadFilled } from '@element-plus/icons-vue';
import { useUiStore } from '@/stores/uiStore';
import { useRag } from '@/composables/useRag';

const { showUploadDialog } = useUiStore();
const { isUploading, pendingFiles, handleBeforeUpload, handleUploadRequest, submitBatchUpload } = useRag();

// 监听对话框关闭，清空文件队列
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
