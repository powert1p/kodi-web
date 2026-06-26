import { defineConfig } from 'vitest/config'

// Конфиг vitest: jsdom-среда для тестов логики (не рендер).
export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/test/**/*.test.ts'],
  },
})
