import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    base: './', // 确保 Electron 打包时资源路径正确
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:12000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        },
        '/chat': {
          target: env.VITE_WS_BASE_URL || 'ws://localhost:13000',
          changeOrigin: true,
          ws: true
        }
      }
    },
    preview: {
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:12000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        },
        '/chat': {
          target: env.VITE_WS_BASE_URL || 'ws://localhost:13000',
          changeOrigin: true,
          ws: true
        }
      }
    }
  }
})
