import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { readFileSync } from 'fs';
import { join } from 'path';
import { Button } from '@/components/ui/button';

/**
 * Test 1: Verify Tailwind dark theme is active (AC: 3)
 */
describe('Tailwind CSS Dark Theme', () => {
  it('test_tailwind_dark_theme_active - should have dark theme styles configured', () => {
    const globalsPath = join(__dirname, '..', 'src', 'app', 'globals.css');
    const globalsCss = readFileSync(globalsPath, 'utf-8');

    // Verify Tailwind CSS import
    expect(globalsCss).toContain('@import "tailwindcss"');

    // Verify dark theme color tokens are defined
    expect(globalsCss).toContain('--background: #0f172a'); // Slate 900
    expect(globalsCss).toContain('--foreground: #f8fafc'); // Slate 50
    expect(globalsCss).toContain('--primary: #3b82f6'); // Blue 500
    expect(globalsCss).toContain('--success: #34d399'); // Green 400
    expect(globalsCss).toContain('--error: #f87171'); // Red 400

    // Verify @theme configuration for Tailwind v4
    expect(globalsCss).toContain('@theme inline');
    expect(globalsCss).toContain('--color-background: var(--background)');
    expect(globalsCss).toContain('--color-primary: var(--primary)');

    // Verify body styles use dark theme
    expect(globalsCss).toContain('background: var(--background)');
    expect(globalsCss).toContain('color: var(--foreground)');
  });
});

/**
 * Test 2: Verify shadcn/ui Button component renders (AC: 4)
 */
describe('shadcn/ui Components', () => {
  it('test_shadcn_components_render - should render Button component with correct styles', () => {
    // Render Button component
    const { container } = render(<Button>Test Button</Button>);

    const button = container.querySelector('button');

    // Verify button exists
    expect(button).toBeTruthy();

    // Verify button has data-slot attribute (shadcn/ui convention)
    expect(button?.getAttribute('data-slot')).toBe('button');

    // Verify button contains the text
    expect(button?.textContent).toBe('Test Button');

    // Verify button has expected classes (Tailwind utilities)
    const buttonClasses = button?.className || '';
    expect(buttonClasses).toContain('inline-flex');
    expect(buttonClasses).toContain('items-center');
    expect(buttonClasses).toContain('justify-center');
    expect(buttonClasses).toContain('rounded-md');

    // Test Button with variant
    const { container: container2 } = render(<Button variant="outline">Outline Button</Button>);
    const outlineButton = container2.querySelector('button');

    // Verify outline variant classes
    const outlineClasses = outlineButton?.className || '';
    expect(outlineClasses).toContain('border');
    expect(outlineClasses).toContain('bg-background');
  });
});
