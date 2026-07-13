import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// Приложение монтируется под /app/ (nginx проксирует туда статику).
export default defineConfig({
  base: '/app/',
  // Дев-прокси на локальный backend (:8000) — нужен только для `npm run dev`,
  // чтобы живые скриншоты/ручная проверка снимались на vite :5173 против
  // реального /api. Прод отдаёт /api через nginx same-origin, этой строки не
  // видит (влияет только на `server`, не на `vite build`).
  server: { proxy: { '/api': 'http://localhost:8000' } },
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
        name: 'Работа над ошибками',
        short_name: 'Над ошибками',
        description: 'Тренажёр разбора ошибок по математике — где растёт мозг.',
        start_url: '/app/',
        scope: '/app/',
        display: 'standalone',
        orientation: 'portrait',
        lang: 'ru',
        // v6 «Тетрадь чемпиона»: доминанта — тёплая бумага; статус-бар PWA
        // сливается с фоном (--paper #FAF7F2), оранж бережём под действие/маршрут.
        theme_color: '#faf7f2',
        background_color: '#faf7f2',
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: 'icons/icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Прекэш только оболочки (вкл. шрифты приложения и шрифты KaTeX).
        globPatterns: ['**/*.{js,css,html,woff2,svg,png,ico}'],
        // НЕ кэшировать API — всегда живой запрос.
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [{ urlPattern: /\/api\//, handler: 'NetworkOnly' }],
      },
      devOptions: { enabled: false },
    }),
  ],
})
