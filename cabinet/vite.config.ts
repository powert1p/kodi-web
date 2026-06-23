import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// SPA-конфиг: React + Tailwind v4 через официальный vite-плагин (без tailwind.config.js)
export default defineConfig({
  plugins: [react(), tailwindcss()],
})
