import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// Dev-only mock so the login page can show the demo button without a backend.
// It never runs in a production build.
function devDemoConfig(): Plugin {
  return {
    name: 'dev-demo-config',
    configureServer(server) {
      server.middlewares.use('/config', (_req, res) => {
        res.setHeader('Content-Type', 'application/json')
        res.end(
          JSON.stringify({
            demo: {
              enabled: true,
              username: 'demo-admin',
              password: 'demo-admin-2026',
            },
          }),
        )
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), devDemoConfig()],
  server: {
    proxy: {
      // Forward API calls to the FastAPI dev server so the React app can
      // talk to the backend during development (until T12 serves the build).
      '/auth': 'http://localhost:8000',
      '/trucks': 'http://localhost:8000',
      '/devices': 'http://localhost:8000',
      '/trips': 'http://localhost:8000',
      '/chargers': 'http://localhost:8000',
      '/depots': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
