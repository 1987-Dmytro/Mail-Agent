import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import FolderManager from '@/components/settings/FolderManager';
import { apiClient } from '@/lib/api-client';
import type { ApiResponse } from '@/types/api';
import type { FolderCategory } from '@/types/folder';

// Mock API client
vi.mock('@/lib/api-client', () => ({
  apiClient: {
    getFolders: vi.fn(),
    createFolder: vi.fn(),
    updateFolder: vi.fn(),
    deleteFolder: vi.fn(),
  },
}));

// Mock toast notifications
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('FolderManager Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Reset all API mocks to default behavior
    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: [],
      status: 200,
    } as ApiResponse<FolderCategory[]>);
  });

  /**
   * Integration Test 1: Complete CRUD flow (AC: 1-11)
   */
  it('test_complete_folder_crud_flow', async () => {

    // Initial state: empty folders
    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: [],
      status: 200,
    } as ApiResponse<FolderCategory[]>);

    const user = userEvent.setup();
    render(<FolderManager />);

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByText('Add Category')).toBeInTheDocument();
    });

    // ===== STEP 1: CREATE folder =====
    const createdFolder: FolderCategory = {
      id: 1,
      user_id: 1,
      name: 'TestFolder',
      gmail_label_id: 'Label_1',
      keywords: ['test', 'demo'],
      color: '#3b82f6',
      is_default: false,
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    };

    vi.mocked(apiClient.createFolder).mockResolvedValue({
      data: createdFolder,
      status: 200,
    } as ApiResponse<FolderCategory>);

    // Open create dialog
    const addButton = screen.getByRole('button', { name: /add category/i });
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Fill form and create folder
    const nameInput = screen.getByLabelText(/category name/i);
    const keywordsInput = screen.getByLabelText(/keywords/i);

    await user.type(nameInput, 'TestFolder');
    await user.type(keywordsInput, 'test, demo');

    // Wait for debounce validation to complete (400ms + buffer)
    await new Promise(resolve => setTimeout(resolve, 500));

    const submitButton = screen.getByRole('button', { name: /create category/i });
    await user.click(submitButton);

    // Verify creation success
    await waitFor(() => {
      expect(apiClient.createFolder).toHaveBeenCalled();
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('TestFolder'));
    });

    // Verify folder appears in list
    await waitFor(() => {
      expect(screen.getByText('TestFolder')).toBeInTheDocument();
      expect(screen.getByText('test')).toBeInTheDocument();
      expect(screen.getByText('demo')).toBeInTheDocument();
    });

    // ===== STEP 2: EDIT folder =====
    const updatedFolder: FolderCategory = {
      ...createdFolder,
      name: 'UpdatedFolder',
      keywords: ['updated', 'new'],
      updated_at: '2025-01-02T00:00:00Z',
    };

    vi.mocked(apiClient.updateFolder).mockResolvedValue({
      data: updatedFolder,
      status: 200,
    } as ApiResponse<FolderCategory>);

    // Click edit button
    const editButton = screen.getByTitle('Edit category');
    await user.click(editButton);

    await waitFor(() => {
      expect(screen.getByText('Edit Category')).toBeInTheDocument();
    });

    // Update folder name
    const editNameInput = screen.getByLabelText(/category name/i);
    await user.clear(editNameInput);
    await user.type(editNameInput, 'UpdatedFolder');

    const editKeywordsInput = screen.getByLabelText(/keywords/i);
    await user.clear(editKeywordsInput);
    await user.type(editKeywordsInput, 'updated, new');

    // Wait for debounce validation to complete (400ms + buffer)
    await new Promise(resolve => setTimeout(resolve, 500));

    const updateButton = screen.getByRole('button', { name: /update category/i });
    await user.click(updateButton);

    // Verify update success
    await waitFor(() => {
      expect(apiClient.updateFolder).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          name: 'UpdatedFolder',
          keywords: ['updated', 'new'],
        })
      );
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('UpdatedFolder'));
    });

    // Verify updated folder appears in list
    await waitFor(() => {
      expect(screen.getByText('UpdatedFolder')).toBeInTheDocument();
      expect(screen.getByText('updated')).toBeInTheDocument();
      expect(screen.getByText('new')).toBeInTheDocument();
    });

    // ===== STEP 3: DELETE folder =====
    vi.mocked(apiClient.deleteFolder).mockResolvedValue({
      data: undefined,
      status: 200,
    } as ApiResponse<void>);

    // Click delete button
    const deleteButton = screen.getByTitle('Delete category');
    await user.click(deleteButton);

    // Confirm deletion
    await waitFor(() => {
      expect(screen.getByText('Delete Category')).toBeInTheDocument();
    });

    const confirmDeleteButton = screen.getByRole('button', { name: /^delete$/i });
    await user.click(confirmDeleteButton);

    // Verify deletion success
    await waitFor(() => {
      expect(apiClient.deleteFolder).toHaveBeenCalledWith(1);
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('deleted'));
    });

    // Verify folder removed from list
    await waitFor(() => {
      expect(screen.queryByText('UpdatedFolder')).not.toBeInTheDocument();
    });
  });

  /**
   * Integration Test 2: Name uniqueness validation (AC: 4)
   */
  it('test_folder_name_uniqueness_validation', async () => {

    // Mock existing folder
    const existingFolder: FolderCategory = {
      id: 1,
      user_id: 1,
      name: 'Work',
      gmail_label_id: 'Label_1',
      keywords: ['office'],
      color: '#ef4444',
      is_default: false,
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    };

    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: [existingFolder],
    } as ApiResponse<FolderCategory[]>);

    const user = userEvent.setup();
    render(<FolderManager />);

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByText('Work')).toBeInTheDocument();
    });

    // Try to create duplicate folder (case-insensitive)
    const addButton = screen.getByRole('button', { name: /add category/i });
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Try with exact same name
    const nameInput = screen.getByLabelText(/category name/i);
    await user.type(nameInput, 'Work');

    // Wait for debounce validation to complete (400ms + buffer)
    await new Promise(resolve => setTimeout(resolve, 500));

    // Verify duplicate name error appears inline (real-time validation)
    await waitFor(() => {
      expect(screen.getByText(/a folder with this name already exists/i)).toBeInTheDocument();
    });

    // Submit button should be disabled due to duplicate name
    const submitButton = screen.getByRole('button', { name: /create category/i });
    expect(submitButton).toBeDisabled();

    // Verify API was NOT called
    expect(apiClient.createFolder).not.toHaveBeenCalled();

    // Try with case-insensitive duplicate
    await user.clear(nameInput);
    await user.type(nameInput, 'WORK'); // Different case

    // Wait for debounce validation to complete
    await new Promise(resolve => setTimeout(resolve, 500));

    // Verify duplicate name error (case-insensitive)
    await waitFor(() => {
      expect(screen.getByText(/a folder with this name already exists/i)).toBeInTheDocument();
    });

    // Submit button should still be disabled
    expect(submitButton).toBeDisabled();

    expect(apiClient.createFolder).not.toHaveBeenCalled();
  });

  /**
   * Integration Test 3: Adding single default category (AC: 9)
   */
  it('test_add_default_category', async () => {
    // Explicitly reset mocks for this test
    vi.clearAllMocks();

    // Mock empty folders to show default category suggestions
    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: [],
      status: 200,
    } as ApiResponse<FolderCategory[]>);

    const newFolder: FolderCategory = {
      id: 1,
      user_id: 1,
      name: 'Important',
      gmail_label_id: 'Label_1',
      keywords: ['urgent', 'deadline', 'wichtig'],
      color: '#ef4444',
      is_default: false,
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    };

    vi.mocked(apiClient.createFolder).mockResolvedValueOnce({
      data: newFolder,
      status: 200,
    } as ApiResponse<FolderCategory>);

    const user = userEvent.setup();
    render(<FolderManager />);

    // Wait for component to load with empty state
    await waitFor(() => {
      expect(screen.getByText(/no folders yet/i)).toBeInTheDocument();
    });

    // Verify default category suggestions are shown
    expect(screen.getByText('Important')).toBeInTheDocument();
    expect(screen.getByText('Government')).toBeInTheDocument();
    expect(screen.getByText('Clients')).toBeInTheDocument();
    expect(screen.getByText('Newsletters')).toBeInTheDocument();

    // Find and click "Add" button for "Important" category
    const addButtons = screen.getAllByRole('button', { name: /^add$/i });
    expect(addButtons.length).toBe(4);

    await user.click(addButtons[0]!);

    // Verify API was called to create the folder
    await waitFor(() => {
      expect(apiClient.createFolder).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Important',
          keywords: expect.arrayContaining(['urgent', 'deadline', 'wichtig']),
        })
      );
    });

    // Verify success toast was shown
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('Important'));
    });

    // Verify folder appears in the list
    await waitFor(() => {
      const importantCards = screen.getAllByText('Important');
      expect(importantCards.length).toBeGreaterThan(0);
    });
  });

  /**
   * Integration Test 4: Folder persists across navigation (AC: 10)
   */
  it('test_folder_persists_across_navigation', async () => {
    const existingFolder: FolderCategory = {
      id: 1,
      user_id: 1,
      name: 'Persistent',
      gmail_label_id: 'Label_1',
      keywords: ['test'],
      color: '#22c55e',
      is_default: false,
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    };

    // Mock API to return folder
    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: [existingFolder],
    } as ApiResponse<FolderCategory[]>);

    const { unmount } = render(<FolderManager />);

    // Wait for folder to load
    await waitFor(() => {
      expect(screen.getByText('Persistent')).toBeInTheDocument();
    });

    // Simulate navigation away (unmount component)
    unmount();

    // Simulate navigation back (re-render component)
    render(<FolderManager />);

    // Verify API is called again to fetch folders
    await waitFor(() => {
      expect(apiClient.getFolders).toHaveBeenCalled();
    });

    // Verify folder still appears after "navigation"
    await waitFor(() => {
      expect(screen.getByText('Persistent')).toBeInTheDocument();
      expect(screen.getByText('test')).toBeInTheDocument();
    });
  });

  /**
   * Integration Test 5: API error handling (AC: 11)
   */
  it('test_api_error_handling', async () => {
    // Explicitly reset mocks for this test
    vi.clearAllMocks();

    // Mock empty folders
    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: [],
      status: 200,
    } as ApiResponse<FolderCategory[]>);

    // Mock API to throw error
    vi.mocked(apiClient.createFolder).mockRejectedValueOnce(
      new Error('Network error')
    );

    const user = userEvent.setup();
    render(<FolderManager />);

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByText('Add Category')).toBeInTheDocument();
    });

    // Open create dialog
    const addButton = screen.getByRole('button', { name: /add category/i });
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Fill form with valid data
    const nameInput = screen.getByLabelText(/category name/i);
    await user.type(nameInput, 'TestFolder');

    // Wait for debounce validation to complete (400ms + buffer)
    await new Promise(resolve => setTimeout(resolve, 500));

    const submitButton = screen.getByRole('button', { name: /create category/i });
    await user.click(submitButton);

    // Wait for API call to fail
    await waitFor(() => {
      expect(apiClient.createFolder).toHaveBeenCalled();
    });

    // Verify folder was NOT added to the list (because API failed)
    expect(screen.queryByText('TestFolder')).not.toBeInTheDocument();

    // Note: In real implementation, dialog stays open and shows error toast,
    // allowing user to retry. This is verified by unit tests.
  });
});
