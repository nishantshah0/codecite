import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

// Dev server proxies /api to `codecite serve` (or scripts/dev_server.py).
// VITE_BASE_PATH sets the public path for hosting under a sub-path (GitHub
// Pages serves this repo at /codecite/); see .github/workflows/pages.yml.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'VITE_')
  return {
    base: env.VITE_BASE_PATH || '/',
    plugins: [react()],
    server: {
      proxy: { '/api': 'http://127.0.0.1:8000' },
    },
    test: {
      environment: 'node',
      include: ['src/**/*.test.ts'],
    },
  }
})
