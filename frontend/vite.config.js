import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // In dev, /api/* is proxied to the local FastAPI server, so the browser sees a
    // single origin (no CORS). In production VITE_API_URL points at the HF Space.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
