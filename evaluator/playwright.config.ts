import path from 'node:path';
import { defineConfig } from '@playwright/test';

const workspace = process.env.FRONTEND_WORKSPACE;
const taskId = process.env.FRONTEND_TASK_ID;
if (!workspace) throw new Error('FRONTEND_WORKSPACE is required');
if (!taskId) throw new Error('FRONTEND_TASK_ID is required');
const port = Number(process.env.FRONTEND_EVAL_PORT ?? '4273');

export default defineConfig({
  testDir: './tests',
  testMatch: `${taskId}.spec.ts`,
  timeout: 15_000,
  expect: { timeout: 5_000 },
  retries: 0,
  workers: 1,
  reporter: [['json', { outputFile: path.join(workspace, 'hidden-results.json') }], ['line']],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    actionTimeout: 5_000,
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `npm run dev -- --port ${port}`,
    cwd: workspace,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
