import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// The API is reached through a relative `/api` base; in development the Vite server proxies it to the
// local FastAPI (DT-070 points 8 and 23). FastAPI does not enable CORS.
const apiProxy = {
  '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
};

export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy: apiProxy },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true, proxy: apiProxy },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    restoreMocks: true,
  },
});
