import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  base: '/ReLearn/',

  server: {
    port: 5173,
    allowedHosts: true,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
