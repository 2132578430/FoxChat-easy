import { ref } from 'vue';
import request from '@/utils/request';
import { FoxToast } from '@/components/FoxUI';

const ragFiles = ref([]);
const isSearchingRag = ref(false);
const hasRagSearchResults = ref(false);
const isUploading = ref(false);
const pendingFiles = ref([]);

/**
 * 获取 RAG 文件列表
 */
const fetchRagFiles = async () => {
  try {
    hasRagSearchResults.value = false;
    const res = await request.get('/rag/listFile');
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

/**
 * 重置 RAG 搜索结果
 */
const resetRagResults = () => {
  fetchRagFiles();
};

/**
 * 处理文件点击
 */
const handleFileClick = (file) => {
  if (file.filePath) {
    window.open(file.filePath, '_blank');
  }
};

/**
 * 搜索 RAG 文件内容
 */
const searchRagFiles = async (content) => {
  if (!content || !content.trim()) return;
  isSearchingRag.value = true;
  try {
    const res = await request.get('/rag/searchRagFile', {
      params: { msg: content }
    });
    if (Array.isArray(res)) {
      ragFiles.value = res;
    } else if (res && res.data && Array.isArray(res.data)) {
      ragFiles.value = res.data;
    }
    hasRagSearchResults.value = true;
    FoxToast.success('搜索完成啦！看看匹配的结果吧~ ✨');
  } catch (error) {
    console.error('RAG 搜索失败:', error);
    FoxToast.error('搜索出错了呢，请稍后再试吧~');
  } finally {
    isSearchingRag.value = false;
  }
};

/**
 * 上传前校验
 */
const handleBeforeUpload = (file) => {
  const maxSize = 100 * 1024 * 1024;
  if (file.size > maxSize) {
    FoxToast.warning(`文件 ${file.name} 太重啦，狐狸抱不动... (不能超过 100MB 哦~)`);
    return false;
  }
  return true;
};

/**
 * 收集上传请求中的文件
 */
const handleUploadRequest = (options) => {
  pendingFiles.value.push(options);
};

/**
 * 提交批量上传
 */
const submitBatchUpload = async () => {
  if (pendingFiles.value.length === 0) {
    FoxToast.warning('还没有选择任何文件呢~');
    return;
  }
  isUploading.value = true;
  const formData = new FormData();
  if (pendingFiles.value.length === 1) {
    formData.append('file', pendingFiles.value[0].file);
  } else {
    pendingFiles.value.forEach(item => {
      formData.append('file', item.file);
    });
  }
  try {
    await request.post('/rag/uploadVector', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    FoxToast.success('文件上传成功啦！狐狸正在努力学习中... ✨');
    pendingFiles.value = [];
    fetchRagFiles();
  } catch (error) {
    console.error('批量上传失败:', error);
    FoxToast.error('上传出错了呢，请稍后再试吧~');
  } finally {
    isUploading.value = false;
  }
};

export function useRag() {
  return {
    ragFiles,
    isSearchingRag,
    hasRagSearchResults,
    isUploading,
    pendingFiles,
    fetchRagFiles,
    searchRagFiles,
    resetRagResults,
    handleFileClick,
    handleBeforeUpload,
    handleUploadRequest,
    submitBatchUpload
  };
}
