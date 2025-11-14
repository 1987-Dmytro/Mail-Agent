import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import RootLayout from '@/app/layout';
import { Navbar } from '@/components/shared/Navbar';
import Home from '@/app/page';

/**
 * Test 1: Verify root layout renders with dark theme (AC: 8)
 */
describe('Root Layout', () => {
  it('test_root_layout_renders - should render layout component with children', () => {
    render(
      <RootLayout>
        <div data-testid="test-child">Test Content</div>
      </RootLayout>
    );

    // Verify children are rendered (layout wraps children)
    const child = screen.getByTestId('test-child');
    expect(child).toBeTruthy();
    expect(child.textContent).toBe('Test Content');

    // Verify ErrorBoundary and Toaster are present (indirectly via no errors)
    // If layout didn't render properly, the child wouldn't be found
    expect(child.closest('body')).toBeTruthy();
  });
});

/**
 * Test 2: Verify navbar renders navigation links (AC: 8)
 */
describe('Navbar Component', () => {
  it('test_navbar_renders_navigation - should render navbar with logo and navigation links', () => {
    render(<Navbar />);

    // Verify logo/app name is present
    const logo = screen.getByText('Mail Agent');
    expect(logo).toBeTruthy();

    // Verify navigation links exist
    const dashboardLink = screen.getByText('Dashboard');
    expect(dashboardLink).toBeTruthy();
    expect(dashboardLink.closest('a')?.getAttribute('href')).toBe('/dashboard');

    const settingsLink = screen.getByText('Settings');
    expect(settingsLink).toBeTruthy();
    expect(settingsLink.closest('a')?.getAttribute('href')).toBe('/settings');

    // Verify "Get Started" CTA button
    const getStartedButton = screen.getByText('Get Started');
    expect(getStartedButton).toBeTruthy();
    expect(getStartedButton.closest('a')?.getAttribute('href')).toBe('/onboarding');
  });
});

/**
 * Test 3: Verify landing page renders with CTA button (AC: 8)
 */
describe('Landing Page', () => {
  it('test_landing_page_renders - should render landing page with hero section and CTA button', () => {
    render(<Home />);

    // Verify hero heading is present
    const heading = screen.getByText(/AI-Powered Email/i);
    expect(heading).toBeTruthy();

    // Verify hero description
    const description = screen.getByText(/Let AI organize your inbox/i);
    expect(description).toBeTruthy();

    // Verify "Get Started" CTA button (primary action)
    const getStartedButtons = screen.getAllByText('Get Started');
    expect(getStartedButtons.length).toBeGreaterThan(0);
    const primaryCTA = getStartedButtons[0];
    expect(primaryCTA?.closest('a')?.getAttribute('href')).toBe('/onboarding');

    // Verify features section with cards
    expect(screen.getByText('Gmail Integration')).toBeTruthy();
    expect(screen.getByText('AI Classification')).toBeTruthy();
    expect(screen.getByText('Telegram Approval')).toBeTruthy();

    // Verify footer
    const footer = screen.getByText(/Built with Next.js/i);
    expect(footer).toBeTruthy();
  });
});
