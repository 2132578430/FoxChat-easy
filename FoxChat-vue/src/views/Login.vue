<template>
  <div class="login-container">
    <div class="login-card">
      <div class="card-header">
        <span class="card-title">🦊 FoxChat</span>
        <span class="card-subtitle">登录</span>
      </div>
      <div class="card-body">
        <FoxInput v-model="loginForm.username" placeholder="用户名" />
        <FoxInput v-model="loginForm.password" type="password" placeholder="密码" />
        <FoxButton type="primary" block :loading="loading" @click="handleLogin">登录</FoxButton>
        <div class="form-footer">
          <router-link to="/register">没有账号？去注册</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { FoxInput, FoxButton, FoxToast } from '@/components/FoxUI';
import { login } from '../api/auth';

const router = useRouter();
const loading = ref(false);

const loginForm = reactive({ username: '', password: '' });

const handleLogin = async () => {
  if (!loginForm.username.trim() || !loginForm.password.trim()) {
    FoxToast.warning('请填写用户名和密码');
    return;
  }
  loading.value = true;
  try {
    const response = await login(loginForm);
    const data = response.data;
    FoxToast.success('登录成功');
    const userInfo = {
      username: data.username,
      userId: data.userId,
      face_image: data.face_image || 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'
    };
    localStorage.setItem('userInfo', JSON.stringify(userInfo));
    router.push('/');
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-container {
  display: flex; justify-content: center; align-items: center;
  height: 100vh; background: #e8f0fe;
}
.login-card {
  width: 380px; background: rgba(255,255,255,0.85);
  border-radius: 16px; box-shadow: 0 8px 40px rgba(0,0,0,0.08);
  backdrop-filter: blur(10px); overflow: hidden;
}
.card-header {
  padding: 32px 32px 0; text-align: center;
}
.card-title { font-size: 28px; font-weight: 700; color: #4a90d9; display: block; }
.card-subtitle { font-size: 18px; color: #666; margin-top: 4px; display: block; }
.card-body {
  padding: 24px 32px 32px; display: flex; flex-direction: column; gap: 14px;
}
.form-footer { text-align: center; font-size: 13px; }
.form-footer a { color: #4a90d9; text-decoration: none; }
</style>
