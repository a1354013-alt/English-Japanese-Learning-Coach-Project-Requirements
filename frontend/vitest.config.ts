import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    coverage: {
      provider: 'v8',
      reportsDirectory: './coverage',
      reporter: [
        'text',
        'json',
        'json-summary',
        'lcovonly',
        'cobertura',
        'html',
      ],
      exclude: [
        'src/env.d.ts',
        'src/main.ts',
        'src/router.ts',
        'src/**/*.test.ts',
        'e2e/**',
      ],
    },
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
    setupFiles: ['./vitest.setup.ts'],
    testTimeout: 5000,
    hookTimeout: 5000,
    teardownTimeout: 5000,
    pool: 'forks',
    fileParallelism: false,
    isolate: true,
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
