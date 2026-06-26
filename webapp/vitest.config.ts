import { defineConfig } from 'vitest/config'

// Конфиг vitest: jsdom-среда для тестов логики (не рендер).
// url обязателен чтобы jsdom инициализировал рабочий localStorage.
export default defineConfig({
  test: {
    environment: 'jsdom',
    environmentOptions: {
      jsdom: {
        url: 'http://localhost',
      },
    },
    globals: true,
    include: ['src/test/**/*.test.ts'],
  },
})
