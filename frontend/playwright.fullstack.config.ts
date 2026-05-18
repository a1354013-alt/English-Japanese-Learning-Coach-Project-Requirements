import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  testMatch: /full-stack\.spec\.ts/,
  timeout: 120_000,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  webServer: [
    {
      command: 'python -m uvicorn main:app --host 127.0.0.1 --port 8000',
      cwd: '../backend',
      env: {
        ...process.env,
        ENABLE_RAG: 'false',
        MAX_UPLOAD_SIZE_MB: '10',
        DATA_DIR: '.playwright-data',
        DB_PATH: '.playwright-data/language_coach.db',
        CHROMA_DB_PATH: '.playwright-data/chroma_db',
        CORS_ORIGINS: 'http://127.0.0.1:4273',
      },
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: process.env.PLAYWRIGHT_REUSE_SERVER === '1',
      timeout: 120_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 4273 --strictPort',
      env: {
        ...process.env,
        VITE_API_TARGET: 'http://127.0.0.1:8000',
        VITE_WS_TARGET: 'ws://127.0.0.1:8000',
      },
      url: 'http://127.0.0.1:4273',
      reuseExistingServer: process.env.PLAYWRIGHT_REUSE_SERVER === '1',
      timeout: 120_000,
    },
  ],
  use: {
    baseURL: 'http://127.0.0.1:4273',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
