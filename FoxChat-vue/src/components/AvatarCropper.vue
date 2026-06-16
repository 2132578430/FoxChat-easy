<template>
  <FoxModal v-model="dialogVisible" title="修改头像" width="620px" :close-on-overlay="false">
    <div class="cropper-container">
      <div class="cropper-wrapper" v-if="imageUrl">
        <vue-cropper
          ref="cropperRef"
          :img="imageUrl"
          :outputSize="option.size"
          :outputType="option.outputType"
          :info="true"
          :full="option.full"
          :canMove="option.canMove"
          :canMoveBox="option.canMoveBox"
          :fixedBox="option.fixedBox"
          :original="option.original"
          :autoCrop="option.autoCrop"
          :autoCropWidth="option.autoCropWidth"
          :autoCropHeight="option.autoCropHeight"
          :centerBox="option.centerBox"
          :high="option.high"
          :infoTrue="option.infoTrue"
          :maxImgSize="option.maxImgSize"
          :fixed="option.fixed"
          :fixedNumber="option.fixedNumber"
        ></vue-cropper>
      </div>
      <div class="upload-placeholder" v-else>
        <el-upload
          class="avatar-uploader"
          action="#"
          :show-file-list="false"
          :auto-upload="false"
          :on-change="handleFileChange"
          accept=".jpg,.jpeg,.png,.gif"
          drag
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处，或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              只能上传 jpg/png 文件，且不超过 5MB
            </div>
          </template>
        </el-upload>
      </div>
    </div>

    <div class="cropper-actions" v-if="imageUrl">
      <div class="cropper-tools">
        <FoxButton size="small" type="ghost" @click="changeScale(1)">🔍 放大</FoxButton>
        <FoxButton size="small" type="ghost" @click="changeScale(-1)">🔍 缩小</FoxButton>
        <FoxButton size="small" type="ghost" @click="rotateLeft">↺ 左转</FoxButton>
        <FoxButton size="small" type="ghost" @click="rotateRight">↻ 右转</FoxButton>
      </div>
      <el-upload
        class="re-upload-btn"
        action="#"
        :show-file-list="false"
        :auto-upload="false"
        :on-change="handleFileChange"
        accept=".jpg,.jpeg,.png,.gif"
      >
        <FoxButton size="small" type="ghost">📷 重选</FoxButton>
      </el-upload>
    </div>

    <template #footer>
      <FoxButton type="ghost" @click="handleClose">取消</FoxButton>
      <FoxButton type="primary" :loading="loading" :disabled="!imageUrl" @click="handleUpload">确认上传</FoxButton>
    </template>
  </FoxModal>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';
import { FoxModal, FoxButton, FoxToast } from '@/components/FoxUI';
import { UploadFilled } from '@element-plus/icons-vue';
import 'vue-cropper/dist/index.css'
import { VueCropper } from "vue-cropper";
import { uploadAvatar } from '@/api/user';

const props = defineProps({
  visible: { type: Boolean, default: false },
  type: { type: String, default: 'user', validator: (value) => ['user', 'llm'].includes(value) }
});

const emit = defineEmits(['update:visible', 'success', 'blob']);

const dialogVisible = ref(false);
const imageUrl = ref('');
const cropperRef = ref(null);
const loading = ref(false);

const option = reactive({
  size: 1, full: false, outputType: 'png', canMove: true, fixedBox: false,
  original: false, canMoveBox: true, autoCrop: true, autoCropWidth: 200,
  autoCropHeight: 200, centerBox: true, high: true, maxImgSize: 2000,
  fixed: true, fixedNumber: [1, 1], canScale: true, infoTrue: true,
  mode: 'cover', fillColor: ''
});

watch(() => props.visible, (val) => { dialogVisible.value = val; });

const handleClose = () => { emit('update:visible', false); };

const handleFileChange = (file) => {
  const isLt5M = file.raw.size / 1024 / 1024 < 5;
  if (!isLt5M) { FoxToast.error('上传头像图片大小不能超过 5MB!'); return; }
  const reader = new FileReader();
  reader.readAsDataURL(file.raw);
  reader.onload = (e) => { imageUrl.value = e.target.result; };
};

const changeScale = (num) => { cropperRef.value.changeScale(num); };
const rotateLeft = () => { cropperRef.value.rotateLeft(); };
const rotateRight = () => { cropperRef.value.rotateRight(); };

const handleUpload = () => {
  loading.value = true;
  cropperRef.value.getCropBlob((blob) => {
    if (!blob) { FoxToast.error('图片处理失败，请重试'); loading.value = false; return; }
    if (props.type === 'llm') { loading.value = false; emit('blob', blob); handleClose(); return; }
    const formData = new FormData();
    formData.append('file', blob, 'avatar.png');
    uploadAvatar(formData).then(res => {
      loading.value = false;
      const avatarUrl = (typeof res === 'string') ? res : (res.data || res);
      if (avatarUrl && typeof avatarUrl === 'string' && avatarUrl.startsWith('http')) {
        FoxToast.success('头像上传成功啦 ✨');
        emit('success', avatarUrl);
        handleClose();
      } else if (res.code === 1000) {
        FoxToast.success('头像上传成功啦 ✨');
        emit('success', res.data);
        handleClose();
      } else {
        FoxToast.error(res.msg || '上传失败了呢');
      }
    }).catch(err => { loading.value = false; console.error(err); FoxToast.error('上传出错啦，请稍后再试'); });
  });
};
</script>

<style scoped>
.cropper-container { height: 400px; display: flex; justify-content: center; align-items: center; background-color: #f0f2f5; border-radius: 8px; overflow: hidden; }
:deep(.cropper-view-box) { border-radius: 50%; outline: 2px solid #fff; outline-color: rgba(255, 255, 255, 1); }
:deep(.cropper-face) { background-color: transparent; border-radius: 50%; }
.cropper-wrapper { width: 100%; height: 100%; }
.upload-placeholder { width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }
.cropper-actions { margin-top: 20px; display: flex; justify-content: space-between; align-items: center; }
.cropper-tools { display: flex; gap: 6px; }
.re-upload-btn { display: inline-block; }
:deep(.el-upload-dragger) { width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; border: none; background: transparent; }
</style>
