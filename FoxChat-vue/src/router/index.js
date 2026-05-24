import { createRouter, createWebHistory } from 'vue-router';
import Login from '../views/Login.vue';
import Register from '../views/Register.vue';
import Home from '../views/Home.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    },
    {
      path: '/login',
      name: 'login',
      component: Login
    },
    {
      path: '/register',
      name: 'register',
      component: Register
    }
  ]
});

// Navigation Guard (token 由 HTTPOnly Cookie 管理，改用 userInfo 判断登录状态)
router.beforeEach((to, from, next) => {
  const userInfo = localStorage.getItem('userInfo');
  if (to.name !== 'login' && to.name !== 'register' && !userInfo) {
    next({ name: 'login' });
  } else {
    next();
  }
});

export default router;
