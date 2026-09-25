import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// In dev, API calls go to FastAPI on :8000. "/store" alone is the dashboard page, so only
// "/store/..." sub-paths are proxied.
const api = 'http://localhost:8000'
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/search': api,
      '/feedback': api,
      '/eval': api,
      '^/store/.+': api,
    },
  },
})
