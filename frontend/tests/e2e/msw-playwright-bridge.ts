import { Page } from '@playwright/test';
import { RequestHandler } from 'msw';

/**
 * MSW-Playwright Bridge
 *
 * Converts MSW request handlers to Playwright route mocks
 * Allows us to maintain a single source of truth for API mocking
 *
 * Architecture:
 * - MSW handlers define the contract (handlers.ts)
 * - Integration tests use MSW Node server (setupServer)
 * - E2E tests use this bridge to convert MSW → Playwright routes
 *
 * Benefits:
 * - DRY: Single mock definition for all test types
 * - Type-safe: MSW provides excellent TypeScript support
 * - Maintainable: Changes to API mocks only need to happen in one place
 * - Production-ready: Industry standard mocking solution
 */

/**
 * Extract path pattern from MSW handler info
 * Converts MSW path format to Playwright glob pattern
 */
function convertPathToPlaywrightPattern(path: string): string {
  return path
    .replace(/^https?:\/\/[^/]+/, '**') // Replace protocol + domain with **
    .replace(/:(\w+)/g, '*'); // Replace path params with wildcard
}

/**
 * Extract path parameters from URL based on MSW pattern
 */
function extractPathParams(pattern: string, url: string): Record<string, string> {
  const params: Record<string, string> = {};

  const patternParts = new URL(pattern.startsWith('http') ? pattern : `http://localhost${pattern}`).pathname.split('/');
  const urlParts = new URL(url).pathname.split('/');

  patternParts.forEach((part, index) => {
    if (part.startsWith(':')) {
      const paramName = part.slice(1);
      params[paramName] = urlParts[index] || '';
    }
  });

  return params;
}

/**
 * Setup MSW handlers as Playwright routes
 *
 * @param page - Playwright page instance
 * @param handlers - MSW request handlers
 */
export async function setupMSWForPlaywright(page: Page, handlers: RequestHandler[]) {
  let installedRoutes = 0;

  for (const handler of handlers) {
    try {
      // Access MSW handler internal structure
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const handlerInfo = (handler as any).info;

      if (!handlerInfo) {
        console.warn('⚠️ MSW Bridge: Handler missing info, skipping');
        continue;
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const method = (handlerInfo as any).method;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const path = (handlerInfo as any).path;
      const playwrightPattern = convertPathToPlaywrightPattern(path);

      // Install Playwright route that delegates to MSW handler
      await page.route(playwrightPattern, async (route) => {
        const request = route.request();
        const requestMethod = request.method();

        // Only handle matching HTTP methods
        if (requestMethod.toLowerCase() !== method.toLowerCase()) {
          return route.continue();
        }

        // Extract path parameters
        const params = extractPathParams(path, request.url());

        // Get request body
        const postData = request.postData();

        // Create MSW-compatible request object
        const mswRequest = new Request(request.url(), {
          method: requestMethod,
          headers: request.headers(),
          body: postData || undefined,
        });

        try {
          // Call MSW resolver
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const resolverFn = (handler as any).resolver;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const response: any = await resolverFn({
            request: mswRequest,
            params,
            cookies: {},
            requestId: crypto.randomUUID(),
          });

          // Handle MSW HttpResponse
          if (response) {
            const responseBody = await response.text();
            const status = response.status;
            const headers: Record<string, string> = {};

            response.headers.forEach((value: string, key: string) => {
              headers[key] = value;
            });

            // Log interception for debugging
            console.log(`🔵 MSW→PW: ${requestMethod} ${new URL(request.url()).pathname} → ${status}`);

            await route.fulfill({
              status,
              headers,
              body: responseBody,
            });
          } else {
            // No response from handler, continue
            await route.continue();
          }
        } catch (error) {
          console.error(`❌ MSW→PW: Handler error for ${requestMethod} ${path}:`, error);
          await route.continue();
        }
      });

      installedRoutes++;
    } catch (error) {
      console.error('❌ MSW→PW: Failed to install handler:', error);
    }
  }

  console.log(`✅ MSW→Playwright Bridge: Installed ${installedRoutes}/${handlers.length} routes`);
}
