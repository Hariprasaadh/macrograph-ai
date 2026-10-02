import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/finance-sector': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/real-sector': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/a2a': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
