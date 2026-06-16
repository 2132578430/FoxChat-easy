<template>
  <div class="register-container">
    <div class="register-card">
      <div class="card-header">
        <span class="card-title">🦊 FoxChat</span>
        <span class="card-subtitle">注册</span>
      </div>
      <div class="card-body">
        <FoxInput v-model="registerForm.nickname" placeholder="昵称" />
        <FoxInput v-model="registerForm.username" placeholder="用户名" />
        <FoxInput v-model="registerForm.password" type="password" placeholder="密码" />
        <FoxInput v-model="registerForm.confirmPassword" type="password" placeholder="确认密码" />
        <FoxButton type="primary" block :loading="loading" @click="handleRegister">注册</FoxButton>
        <div class="form-footer">
          <router-link to="/login">已有账号？去登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { FoxInput, FoxButton, FoxToast } from '@/components/FoxUI';
import { register } from '../api/auth';

const router = useRouter();
const loading = ref(false);

const registerForm = reactive({
  nickname: '', username: '', password: '', confirmPassword: ''
});

const handleRegister = async () => {
  if (!registerForm.nickname.trim() || !registerForm.username.trim()) {
    FoxToast.warning('请填写昵称和用户名');
    return;
  }
  if (registerForm.password !== registerForm.confirmPassword) {
    FoxToast.warning('两次密码不一致');
    return;
  }
  loading.value = true;
  try {
    await register({
      nickname: registerForm.nickname,
      username: registerForm.username,
      password: registerForm.password
    });
    FoxToast.success('注册成功，请登录');
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
  display: flex; justify-content: center; align-items: center;
  height: 100vh; background: #e8f0fe;
}
.register-card {
  width: 380px; background: rgba(255,255,255,0.85);
  border-radius: 16px; box-shadow: 0 8px 40px rgba(0,0,0,0.08);
  backdrop-filter: blur(10px); overflow: hidden;
}
.card-header { padding: 28px 32px 0; text-align: center; }
.card-title { font-size: 28px; font-weight: 700; color: #4a90d9; display: block; }
.card-subtitle { font-size: 18px; color: #666; margin-top: 4px; display: block; }
.card-body { padding: 24px 32px 32px; display: flex; flex-direction: column; gap: 14px; }
.form-footer { text-align: center; font-size: 13px; margin-top: 4px; }
.form-footer a { color: #4a90d9; text-decoration: none; }
</style>
