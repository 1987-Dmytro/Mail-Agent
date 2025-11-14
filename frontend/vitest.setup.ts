import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  })),
  useSearchParams: vi.fn(() => ({
    get: vi.fn(),
  })),
  usePathname: vi.fn(() => '/'),
}));

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
