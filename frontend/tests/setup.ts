// CRITICAL: Set environment variables BEFORE any imports that might use them
process.env.NODE_ENV = 'test';
if (!process.env.NEXT_PUBLIC_API_URL) {
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
}

import '@testing-library/jest-dom';
import { afterEach, beforeAll, afterAll } from 'vitest';
import { cleanup } from '@testing-library/react';
import { server } from './mocks/server';

// Start MSW server before all tests
beforeAll(async () => {
  // Start MSW server with comprehensive logging
  server.listen({
    onUnhandledRequest: (req) => {
      console.warn(`⚠️  Unhandled ${req.method} request to ${req.url}`);
      console.warn(`   Headers:`, Object.fromEntries(req.headers.entries()));
    },
  });

  // Debug: Log that MSW is started
  console.log('✅ MSW Server started');
  console.log(`📍 API_URL configured as: ${process.env.NEXT_PUBLIC_API_URL}`);

  // Wait a bit for MSW to fully initialize
  await new Promise(resolve => setTimeout(resolve, 100));
});

// Reset handlers after each test
afterEach(() => {
  server.resetHandlers();
  cleanup();
});

// Clean up after all tests
afterAll(() => {
  server.close();
  console.log('🛑 MSW Server closed');
});
