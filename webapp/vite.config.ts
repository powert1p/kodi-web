import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

const apiProxy = process.env.VITE_API_PROXY ?? 'http://localhost:8000'

// Приложение монтируется под /app/ (nginx проксирует туда статику).
export default defineConfig({
  base: '/app/',
  // Дев-прокси на локальный backend (:8000) — нужен только для `npm run dev`,
  // чтобы живые скриншоты/ручная проверка снимались на vite :5173 против
  // реального /api. Прод отдаёт /api через nginx same-origin, этой строки не
  // видит (влияет только на `server`, не на `vite build`).
  server: { proxy: { '/api': apiProxy } },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: [
        'favicon.svg',
        'favicon.png',
        'icons/apple-touch-icon.png',
      ],
      manifest: {
        name: 'AiPlus — учусь математике',
        short_name: 'AiPlus',
        description: 'Пошаговое обучение математике: пример, практика, самостоятельное решение и перенос.',
        start_url: '/app/',
        scope: '/app/',
        display: 'standalone',
        orientation: 'portrait',
        lang: 'ru',
        theme_color: '#f5f1e7',
        background_color: '#f5f1e7',
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: 'icons/icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Прекэш только оболочки (вкл. шрифты приложения и шрифты KaTeX).
        globPatterns: [
          '**/*.{js,css,html,woff2,svg,png,ico}',
          '**/squirrel-*.webp',
        ],
        // НЕ кэшировать API — всегда живой запрос.
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [{ urlPattern: /\/api\//, handler: 'NetworkOnly' }],
      },
      devOptions: { enabled: false },
    }),
  ],
})
