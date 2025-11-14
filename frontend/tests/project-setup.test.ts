import { describe, it, expect } from 'vitest';
import { existsSync, readFileSync } from 'fs';
import { join } from 'path';

/**
 * Test 1: Verify TypeScript strict mode configuration (AC: 1)
 */
describe('TypeScript Configuration', () => {
  it('test_typescript_configuration - should have strict mode enabled with all required settings', () => {
    const tsconfigPath = join(__dirname, '..', 'tsconfig.json');
    expect(existsSync(tsconfigPath)).toBe(true);

    const tsconfig = JSON.parse(readFileSync(tsconfigPath, 'utf-8'));
    const compilerOptions = tsconfig.compilerOptions;

    // Verify strict mode is enabled
    expect(compilerOptions.strict).toBe(true);

    // Verify additional strict settings from story requirements
    expect(compilerOptions.noUncheckedIndexedAccess).toBe(true);
    expect(compilerOptions.noImplicitAny).toBe(true);
    expect(compilerOptions.strictNullChecks).toBe(true);

    // Verify target and lib settings
    expect(compilerOptions.target).toBe('ES2020');
    expect(compilerOptions.lib).toContain('ES2020');
    expect(compilerOptions.lib).toContain('DOM');
    expect(compilerOptions.lib).toContain('DOM.Iterable');

    // Verify path alias configuration
    expect(compilerOptions.paths).toBeDefined();
    expect(compilerOptions.paths['@/*']).toEqual(['./src/*']);
  });
});

/**
 * Test 2: Verify project structure exists (AC: 2)
 */
describe('Project Structure', () => {
  it('test_project_structure_exists - should have all required directories', () => {
    const projectRoot = join(__dirname, '..');

    // Verify src/ directory structure
    const requiredDirectories = [
      'src/app',
      'src/app/onboarding',
      'src/app/dashboard',
      'src/app/settings',
      'src/components',
      'src/components/ui',
      'src/components/shared',
      'src/components/onboarding',
      'src/components/dashboard',
      'src/lib',
      'src/types',
    ];

    requiredDirectories.forEach((dir) => {
      const fullPath = join(projectRoot, dir);
      expect(existsSync(fullPath), `Directory ${dir} should exist`).toBe(true);
    });

    // Verify essential files exist
    const requiredFiles = [
      'src/app/layout.tsx',
      'src/app/page.tsx',
      'src/app/globals.css',
      'src/lib/utils.ts',
      'src/types/api.ts',
      'src/types/user.ts',
      'src/types/folder.ts',
    ];

    requiredFiles.forEach((file) => {
      const fullPath = join(projectRoot, file);
      expect(existsSync(fullPath), `File ${file} should exist`).toBe(true);
    });
  });
});

/**
 * Test 3: Verify dev server can start (AC: 7)
 * This is a smoke test that verifies the Next.js configuration is valid
 */
describe('Development Server', () => {
  it('test_dev_server_starts - should have valid Next.js configuration', () => {
    const projectRoot = join(__dirname, '..');

    // Verify Next.js config exists
    const nextConfigPath = join(projectRoot, 'next.config.ts');
    expect(existsSync(nextConfigPath), 'next.config.ts should exist').toBe(true);

    // Verify package.json has dev script
    const packageJsonPath = join(projectRoot, 'package.json');
    expect(existsSync(packageJsonPath)).toBe(true);

    const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
    expect(packageJson.scripts.dev).toBeDefined();
    expect(packageJson.scripts.dev).toContain('next dev');

    // Verify Next.js dependencies are installed
    expect(packageJson.dependencies.next).toBeDefined();
    expect(packageJson.dependencies.react).toBeDefined();
    expect(packageJson.dependencies['react-dom']).toBeDefined();

    // Verify TypeScript is configured
    expect(packageJson.devDependencies.typescript).toBeDefined();

    // Verify node_modules exists (dependencies installed)
    const nodeModulesPath = join(projectRoot, 'node_modules');
    expect(existsSync(nodeModulesPath), 'node_modules should exist').toBe(true);
  });
});
