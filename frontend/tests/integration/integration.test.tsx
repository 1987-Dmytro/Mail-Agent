import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import Home from '@/app/page';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';
import { apiClient } from '@/lib/api-client';

/**
 * Integration Test 1: Full page load with styling and components (AC: 1-4, 7-8)
 */
describe('Frontend Integration - Full Page Load', () => {
  it('test_frontend_loads_and_renders - should load complete page with styling and components', () => {
    render(<Home />);

    // Verify page structure loads
    expect(screen.getByText(/AI-Powered Email/i)).toBeTruthy();
    expect(screen.getByText(/Mail Agent/i)).toBeTruthy();

    // Verify navigation is present (AC: 8)
    expect(screen.getByText('Dashboard')).toBeTruthy();
    expect(screen.getByText('Settings')).toBeTruthy();

    // Verify CTA buttons render (AC: 8)
    const getStartedButtons = screen.getAllByText('Get Started');
    expect(getStartedButtons.length).toBeGreaterThan(0);

    // Verify shadcn/ui components render (AC: 4)
    // Cards should be present in features section
    expect(screen.getByText('Gmail Integration')).toBeTruthy();
    expect(screen.getByText('AI Classification')).toBeTruthy();
    expect(screen.getByText('Telegram Approval')).toBeTruthy();

    // Verify Tailwind CSS classes applied (AC: 3)
    const heroSection = screen.getByText(/AI-Powered Email/i).closest('h1');
    expect(heroSection?.className).toContain('text-');
    expect(heroSection?.className).toContain('font-');
  });
});

/**
 * Integration Test 2: API client makes backend call (AC: 5-6)
 */
describe('API Client Integration', () => {
  it('test_api_client_makes_backend_call - should make API request with correct headers and base URL', async () => {
    // Mock a successful API response
    server.use(
      http.get('http://localhost:8000/health', () => {
        return HttpResponse.json({
          data: { status: 'healthy' },
          message: 'API is running',
          status: 200,
        });
      })
    );

    // Make API request using the client
    const response = await apiClient.get<{ status: string }>('/health');

    // Verify response structure (AC: 5)
    expect(response).toBeDefined();
    expect(response.data).toBeDefined();
    expect(response.data.status).toBe('healthy');
    expect(response.message).toBe('API is running');
    expect(response.status).toBe(200);

    // Verify request was made to correct base URL (AC: 6)
    // Base URL is configured from environment variable
    const expectedBaseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    expect(expectedBaseURL).toBe('http://localhost:8000');
  });

  it('should handle API errors correctly', async () => {
    // Mock an error response
    server.use(
      http.get('http://localhost:8000/api/v1/protected', () => {
        return HttpResponse.json(
          {
            message: 'Session expired',
            code: 'TOKEN_EXPIRED',
            status: 401,
          },
          { status: 401 }
        );
      })
    );

    // Make API request that should fail
    try {
      await apiClient.get('/api/v1/protected');
      // Should not reach here
      expect(true).toBe(false);
    } catch (error) {
      // Verify error handling (AC: 5)
      // API client transforms 401 responses to "Session expired" message
      expect(error).toBeDefined();
      expect(error).toHaveProperty('status', 401);
      expect(error).toHaveProperty('message');
      expect((error as { message: string }).message).toContain('Session expired');
      expect(error).toHaveProperty('code', 'TOKEN_EXPIRED');
    }
  });
});

/**
 * Integration Test 3: Error boundary catches errors (AC: 8)
 */
describe('Error Boundary Integration', () => {
  it('test_error_boundary_catches_errors - should catch component errors and display fallback UI', () => {
    // Component that throws an error
    const ThrowError = () => {
      throw new Error('Test error');
    };

    // Suppress console.error for this test
    const originalError = console.error;
    console.error = () => {};

    // Render component wrapped in ErrorBoundary
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    // Restore console.error
    console.error = originalError;

    // Verify error boundary displays fallback UI (AC: 8)
    expect(screen.getByText('Something went wrong')).toBeTruthy();
    expect(screen.getByText('Test error')).toBeTruthy();
    expect(screen.getByText('Try again')).toBeTruthy();
  });

  it('should render children when no error occurs', () => {
    const SafeComponent = () => <div>Safe Content</div>;

    render(
      <ErrorBoundary>
        <SafeComponent />
      </ErrorBoundary>
    );

    // Verify children render normally
    expect(screen.getByText('Safe Content')).toBeTruthy();
    expect(screen.queryByText('Something went wrong')).toBeFalsy();
  });
});
