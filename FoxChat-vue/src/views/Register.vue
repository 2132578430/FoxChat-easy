<template>
  <div class="register-container">
    <el-card class="register-card">
      <template #header>
        <div class="card-header">
          <span>FoxChat 注册</span>
        </div>
      </template>
      <el-form :model="registerForm" ref="registerFormRef" label-width="0px">
        <el-form-item prop="nickname">
          <el-input v-model="registerForm.nickname" placeholder="昵称" prefix-icon="UserFilled"></el-input>
        </el-form-item>
        <el-form-item prop="username">
          <el-input v-model="registerForm.username" placeholder="用户名" prefix-icon="User"></el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="registerForm.password" type="password" placeholder="密码" prefix-icon="Lock" show-password></el-input>
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input v-model="registerForm.confirmPassword" type="password" placeholder="确认密码" prefix-icon="Lock" show-password></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width: 100%" @click="handleRegister" :loading="loading">注册</el-button>
        </el-form-item>
        <div class="form-footer">
          <router-link to="/login">已有账号？去登录</router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { User, Lock, UserFilled } from '@element-plus/icons-vue';
import { register } from '../api/auth';
import { ElMessage } from 'element-plus';

const router = useRouter();
const registerFormRef = ref(null);
const loading = ref(false);

const registerForm = reactive({
  nickname: '',
  username: '',
  password: '',
  confirmPassword: ''
});

const handleRegister = async () => {
  loading.value = true;
  try {
    await register({
        nickname: registerForm.nickname,
        username: registerForm.username,
        password: registerForm.password
    });
    ElMessage.success('注册成功，请登录');
    router.push('/login');
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}

.register-card {
  width: 400px;
}

.card-header {
  text-align: center;
  font-size: 20px;
  font-weight: bold;
}

.form-footer {
  text-align: center;
  font-size: 14px;
}
</style>
