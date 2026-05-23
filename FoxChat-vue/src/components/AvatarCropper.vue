<template>
  <el-dialog
    v-model="dialogVisible"
    title="修改头像"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose"
    append-to-body
  >
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
      <el-button-group>
        <el-button type="primary" :icon="ZoomIn" @click="changeScale(1)" plain>放大</el-button>
        <el-button type="primary" :icon="ZoomOut" @click="changeScale(-1)" plain>缩小</el-button>
        <el-button type="primary" :icon="RefreshLeft" @click="rotateLeft" plain>左旋转</el-button>
        <el-button type="primary" :icon="RefreshRight" @click="rotateRight" plain>右旋转</el-button>
      </el-button-group>
      <el-upload
        class="re-upload-btn"
        action="#"
        :show-file-list="false"
        :auto-upload="false"
        :on-change="handleFileChange"
        accept=".jpg,.jpeg,.png,.gif"
      >
        <el-button type="warning" plain>重新选择</el-button>
      </el-upload>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleUpload" :disabled="!imageUrl">
          确认上传
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { UploadFilled, ZoomIn, ZoomOut, RefreshLeft, RefreshRight } from '@element-plus/icons-vue';
import 'vue-cropper/dist/index.css'
import { VueCropper } from "vue-cropper";
import { uploadAvatar } from '@/api/user';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  type: {
    type: String,
    default: 'user',
    validator: (value) => ['user', 'llm'].includes(value)
  }
});

const emit = defineEmits(['update:visible', 'success', 'blob']);

const dialogVisible = ref(false);
const imageUrl = ref('');
const cropperRef = ref(null);
const loading = ref(false);

// Cropper options
const option = reactive({
  size: 1,
  full: false,
  outputType: 'png',
  canMove: true,
  fixedBox: false, // 固定截图框大小 不允许改变
  original: false,
  canMoveBox: true,
  autoCrop: true,
  // 只有自动截图开启 宽度高度才生效
  autoCropWidth: 200,
  autoCropHeight: 200,
  centerBox: true,
  high: true,
  maxImgSize: 2000,
  fixed: true, // 是否开启截图框宽高固定比例
  fixedNumber: [1, 1], // 截图框的宽高比例
  full: false, // 是否输出原图比例的截图
  canScale: true,
  fixedBox: false,
  original: false,
  canMoveBox: true,
  infoTrue: true,
  mode: 'cover', // 图片默认渲染方式
  outputType: 'png', // 输出格式，png 支持透明
  fillColor: '' // 关键：将填充色设置为空，确保裁剪后透明区域不填充颜色
});

watch(() => props.visible, (val) => {
  dialogVisible.value = val;
  if (!val) {
    // Clear image when closed? Maybe keep it.
    // imageUrl.value = '';
  }
});

const handleClose = () => {
  emit('update:visible', false);
};

const handleFileChange = (file) => {
  const isLt5M = file.raw.size / 1024 / 1024 < 5;
  if (!isLt5M) {
    ElMessage.error('上传头像图片大小不能超过 5MB!');
    return;
  }
  
  // Use FileReader to preview
  const reader = new FileReader();
  reader.readAsDataURL(file.raw);
  reader.onload = (e) => {
    imageUrl.value = e.target.result;
  };
};

const changeScale = (num) => {
  cropperRef.value.changeScale(num);
};

const rotateLeft = () => {
  cropperRef.value.rotateLeft();
};

const rotateRight = () => {
  cropperRef.value.rotateRight();
};

const handleUpload = () => {
  loading.value = true;
  // 使用 getCropBlob 确保获取裁剪后的数据
  cropperRef.value.getCropBlob((blob) => {
    // 检查 blob 是否生成成功
    if (!blob) {
      ElMessage.error('图片处理失败，请重试');
      loading.value = false;
      return;
    }
    
    // 如果是模型头像，不上传到 /user/updateAvatar，而是触发 blob 事件
    if (props.type === 'llm') {
      loading.value = false;
      emit('blob', blob);
      handleClose();
      return;
    }
    
    const formData = new FormData();
    // 强制指定文件名后缀为 .png，配合 outputType: 'png'
    formData.append('file', blob, 'avatar.png');
    
    uploadAvatar(formData).then(res => {
      loading.value = false;
      // 经过 request.js 拦截器处理后，res 直接就是 data (即图片URL字符串)
      // 或者如果后端返回结构特殊，可能在这里需要做一些判断
      // 用户反馈的响应是: { code: 1000, data: "http...", msg: "响应成功" }
      // request.js 拦截器逻辑是：如果 code==1000，且 data 不是 null，则返回 res.data
      // 所以这里的 res 应该直接就是 "http://..." 这个字符串
      
      // 我们稍微做个兼容判断：如果 res 是字符串，说明拦截器已经解包了
      // 如果 res 是对象且包含 code，说明可能没解包或者解包逻辑有变
      
      const avatarUrl = (typeof res === 'string') ? res : (res.data || res);
      
      if (avatarUrl && typeof avatarUrl === 'string' && avatarUrl.startsWith('http')) {
        ElMessage.success('头像上传成功啦 ✨');
        emit('success', avatarUrl);
        handleClose();
      } else if (res.code === 1000) {
         // 兜底：如果 res 还是原始对象
         ElMessage.success('头像上传成功啦 ✨');
         emit('success', res.data);
         handleClose();
      } else {
        // 既然拦截器会拦截非 1000 的响应并抛出错误，能走到这里说明肯定是成功的
        // 除非拦截器逻辑变了。为了保险，我们把这里的 else 保留
        ElMessage.error(res.msg || '上传失败了呢');
      }
    }).catch(err => {
      loading.value = false;
      console.error(err);
      ElMessage.error('上传出错啦，请稍后再试');
    });
  });
};
</script>

<style scoped>
.cropper-container {
  height: 400px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f0f2f5;
  border-radius: 4px;
  overflow: hidden;
}

/* 覆盖 vue-cropper 的样式，实现圆形遮罩效果 */
:deep(.cropper-view-box) {
  border-radius: 50%;
  outline: 2px solid #fff;
  outline-color: rgba(255, 255, 255, 1);
}

:deep(.cropper-face) {
  background-color: transparent;
  border-radius: 50%;
}

.cropper-wrapper {
  width: 100%;
  height: 100%;
}

.upload-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.cropper-actions {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.re-upload-btn {
  display: inline-block;
}

:deep(.el-upload-dragger) {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border: none;
  background: transparent;
}
</style>
