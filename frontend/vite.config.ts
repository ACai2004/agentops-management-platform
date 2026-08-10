import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // 前端 /api 代理到后端 8000
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    // 大依赖显式预打包，避免 dev 启动时 optimizer 卡住
    include: ['react', 'react-dom', 'react-router-dom', 'antd', '@ant-design/icons', '@xyflow/react', 'axios'],
  },
})
