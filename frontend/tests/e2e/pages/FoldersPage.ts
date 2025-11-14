import { Page, expect } from '@playwright/test';
import { mockFolderCategories, createMockFolder, FolderCategory } from '../fixtures/data';
import { setupAuthenticatedSession, mockAuthEndpoints } from '../fixtures/auth';

/**
 * Page Object for Folder Management Page
 * Story 4.8: End-to-End Onboarding Testing and Polish
 *
 * Represents the folder categories configuration page with:
 * - Folder list display
 * - Create new folder
 * - Edit existing folder
 * - Delete folder
 * - Drag-drop reordering
 */
export class FoldersPage {
  private folders: FolderCategory[] = [...mockFolderCategories];

  constructor(private page: Page) {}

  /**
   * Navigate to folder management page (requires authentication)
   * NOTE: Auth setup is done in test beforeEach, not here
   */
  async goto() {
    // Navigate to folders page (auth already set up in test beforeEach)
    await this.page.goto('/settings/folders');

    // Wait for page to load (auth check happens client-side)
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Set up mock API routes for folder operations
   */
  private async setupFolderAPIRoutes() {
    // GET /api/v1/folders - List folders
    await this.page.route('**/api/v1/folders', (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(this.folders),
        });
      } else if (route.request().method() === 'POST') {
        // POST /api/v1/folders - Create folder
        const newFolder = route.request().postDataJSON();
        const folder = createMockFolder({
          ...newFolder,
          order: this.folders.length + 1,
        });
        this.folders.push(folder);

        route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify(folder),
        });
      }
    });

    // PATCH /api/v1/folders/:id - Update folder
    await this.page.route('**/api/v1/folders/*', (route) => {
      const id = route.request().url().split('/').pop();

      if (route.request().method() === 'PATCH') {
        const updates = route.request().postDataJSON();
        const folderIndex = this.folders.findIndex((f) => f.id === id);

        if (folderIndex !== -1) {
          this.folders[folderIndex] = { ...this.folders[folderIndex], ...updates };
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(this.folders[folderIndex]),
          });
        } else {
          route.fulfill({ status: 404 });
        }
      } else if (route.request().method() === 'DELETE') {
        // DELETE /api/v1/folders/:id - Delete folder
        this.folders = this.folders.filter((f) => f.id !== id);
        route.fulfill({ status: 204 });
      }
    });
  }

  /**
   * Verify folder list is displayed
   */
  async verifyFolderListDisplayed() {
    for (const folder of this.folders.slice(0, 3)) {
      await expect(this.page.getByText(folder.name)).toBeVisible();
    }
  }

  /**
   * Create a new folder
   */
  async createFolder(name: string, keywords: string, color: string = '#3b82f6') {
    // Click "Add Folder" or "Create Folder" button
    const addButton = this.page.getByRole('button', { name: /add folder|create folder/i });
    await expect(addButton).toBeVisible();
    await addButton.click();

    // Wait for dialog/form to appear
    await expect(this.page.getByRole('dialog')).toBeVisible();

    // Fill in folder details
    await this.page.fill('input[name="name"]', name);
    await this.page.fill('input[name="keywords"]', keywords);

    // Optionally select color
    // await this.page.click(`[data-color="${color}"]`);

    // Save folder
    const saveButton = this.page.getByRole('button', { name: /save|create/i });
    await saveButton.click();

    // Wait for success toast or folder to appear in list
    await expect(this.page.getByText(name)).toBeVisible({ timeout: 5000 });
  }

  /**
   * Edit an existing folder
   */
  async editFolder(oldName: string, newName: string) {
    // Find folder row and click edit button
    const folderRow = this.page.locator(`[data-folder-name="${oldName}"]`).or(
      this.page.getByText(oldName).locator('xpath=ancestor::tr|ancestor::div[contains(@class, "folder")]')
    );

    const editButton = folderRow.getByRole('button', { name: /edit/i });
    await expect(editButton).toBeVisible();
    await editButton.click();

    // Wait for edit dialog
    await expect(this.page.getByRole('dialog')).toBeVisible();

    // Update folder name
    const nameInput = this.page.locator('input[name="name"]');
    await nameInput.clear();
    await nameInput.fill(newName);

    // Save changes
    const saveButton = this.page.getByRole('button', { name: /save|update/i });
    await saveButton.click();

    // Verify updated name is displayed
    await expect(this.page.getByText(newName)).toBeVisible({ timeout: 5000 });
    await expect(this.page.getByText(oldName)).not.toBeVisible();
  }

  /**
   * Delete a folder
   */
  async deleteFolder(name: string) {
    // Find folder row and click delete button
    const folderRow = this.page.locator(`[data-folder-name="${name}"]`).or(
      this.page.getByText(name).locator('xpath=ancestor::tr|ancestor::div[contains(@class, "folder")]')
    );

    const deleteButton = folderRow.getByRole('button', { name: /delete|remove/i });
    await expect(deleteButton).toBeVisible();
    await deleteButton.click();

    // Confirm deletion
    const confirmButton = this.page.getByRole('button', { name: /confirm|yes|delete/i });
    await expect(confirmButton).toBeVisible();
    await confirmButton.click();

    // Verify folder is removed from list
    await expect(this.page.getByText(name)).not.toBeVisible({ timeout: 5000 });
  }

  /**
   * Reorder folders via drag-drop
   * Note: Playwright drag-drop can be complex; this is a simplified version
   */
  async reorderFolder(folderName: string, targetIndex: number) {
    // Get the source folder element
    const sourceFolder = this.page.getByText(folderName).locator('xpath=ancestor::div[contains(@class, "folder")]');

    // Get all folder elements
    const folders = this.page.locator('[data-folder-item]');

    // Get target position
    const targetFolder = folders.nth(targetIndex);

    // Perform drag-drop
    await sourceFolder.dragTo(targetFolder);

    // Wait for reorder to complete
    await this.page.waitForTimeout(1000);
  }

  /**
   * Verify folder order
   */
  async verifyFolderOrder(expectedOrder: string[]) {
    const folderElements = this.page.locator('[data-folder-name]');
    const count = await folderElements.count();

    for (let i = 0; i < Math.min(count, expectedOrder.length); i++) {
      const folderName = await folderElements.nth(i).getAttribute('data-folder-name');
      expect(folderName).toBe(expectedOrder[i]);
    }
  }

  /**
   * Verify folder persists after page refresh
   */
  async verifyFolderPersistence(folderName: string) {
    await this.page.reload();
    await expect(this.page.getByText(folderName)).toBeVisible();
  }
}
