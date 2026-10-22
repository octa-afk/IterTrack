import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forward API calls to the FastAPI dev server so the React app can
      // talk to the backend during development (until T12 serves the build).
      '/auth': 'http://localhost:8000',
      '/trucks': 'http://localhost:8000',
      '/devices': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
