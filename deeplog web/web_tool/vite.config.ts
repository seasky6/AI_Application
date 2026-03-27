import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'node:path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') }
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      // -------------------------------
      // ① PQAT Viewer 页面代理（保持原样）
      // -------------------------------
      '/pqat': {
        target: 'https://common-qtools.sero.wh.rnd.internal.ericsson.com/PQATViewer',
        changeOrigin: true,
        secure: false,
        rewrite: p => p.replace(/^\/pqat/, '')
      },

      // -------------------------------
      // ② PQAT API 代理（保持原样）
      // -------------------------------
      '/pqat-api': {
        target: 'https://rbs-pqat.sero.wh.rnd.internal.ericsson.com/pqat_viewer_api/v0.6_b',
        changeOrigin: true,
        secure: false,
        rewrite: p => p.replace(/^\/pqat-api/, '')
      },

      // -------------------------------
      // ③ 新增 ML 后端 API 代理（Flask）
      //
      // 前端通过 /mlapi/* 调用：
      //   VITE_PREDICT_API_BASE=/mlapi
      //
      // 自动代理到： http://127.0.0.1:8000/*
      // -------------------------------
      '/mlapi': {
        target: 'http://127.0.0.1:8000',  // ← Flask 后端 API 地址
        changeOrigin: true,
        secure: false,
        rewrite: p => p.replace(/^\/mlapi/, '')
      }
    }
  }
});
