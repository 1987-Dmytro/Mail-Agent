import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./vitest.setup.ts', './tests/setup.ts'],
    include: ['**/*.test.{ts,tsx}'],
    // Use threads instead of forks to prevent hanging processes
    // Threads are lighter and properly cleaned up after tests
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: true, // Required for MSW to work properly
      },
    },
    // Add reasonable timeouts
    testTimeout: 10000,
    hookTimeout: 10000,
    teardownTimeout: 5000,
    // Force vitest to exit after tests complete
    // This ensures all resources are cleaned up
    fileParallelism: false, // Disable for MSW compatibility
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'dist/',
        '.next/',
        '**/*.config.*',
        '**/types/**',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
