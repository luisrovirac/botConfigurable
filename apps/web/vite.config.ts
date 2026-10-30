import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo, /api se reenvia a la API local (ver scripts/dev-ports.bat).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': env.VITE_API_PROXY_TARGET ?? 'http://localhost:8010',
      },
    },
  }
})
