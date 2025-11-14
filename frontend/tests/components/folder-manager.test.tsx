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

// Sample folder data
const mockFolders: FolderCategory[] = [
  {
    id: 1,
    user_id: 1,
    name: 'Work',
    gmail_label_id: 'Label_1',
    keywords: ['urgent', 'deadline'],
    color: '#ef4444',
    is_default: false,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 2,
    user_id: 1,
    name: 'Personal',
    gmail_label_id: 'Label_2',
    keywords: ['family', 'friends'],
    color: '#3b82f6',
    is_default: false,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 3,
    user_id: 1,
    name: 'Important',
    gmail_label_id: 'Label_3',
    keywords: ['critical', 'urgent'],
    color: '#f97316',
    is_default: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
];

describe('FolderManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Test 1: Folder list renders existing folders (AC: 1)
   */
  it('test_folder_list_renders_existing_folders', async () => {
    // Mock API to return 3 folders
    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: mockFolders,
      status: 200,
    } as ApiResponse<FolderCategory[]>);

    render(<FolderManager />);

    // Wait for folders to load
    await waitFor(() => {
      expect(screen.getByText('Work')).toBeInTheDocument();
    });

    // Verify all 3 folders are displayed
    expect(screen.getByText('Work')).toBeInTheDocument();
    expect(screen.getByText('Personal')).toBeInTheDocument();
    expect(screen.getByText('Important')).toBeInTheDocument();

    // Verify folder cards show keywords as badges (use getAllByText for duplicate keywords)
    const urgentBadges = screen.getAllByText('urgent');
    expect(urgentBadges.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('deadline')).toBeInTheDocument();
    expect(screen.getByText('family')).toBeInTheDocument();
    expect(screen.getByText('friends')).toBeInTheDocument();

    // Verify edit and delete buttons are present
    const editButtons = screen.getAllByTitle('Edit category');
    const deleteButtons = screen.getAllByTitle('Delete category');
    expect(editButtons).toHaveLength(3);
    expect(deleteButtons).toHaveLength(3);
  });

  /**
   * Test 2: "Add Category" button opens dialog (AC: 2)
   */
  it('test_add_category_button_opens_dialog', async () => {
    // Mock API to return empty folders
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

    // Click "Add Category" button
    const addButton = screen.getByRole('button', { name: /add category/i });
    await user.click(addButton);

    // Verify dialog opens with form fields
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Verify form fields are visible
    expect(screen.getByLabelText(/category name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/keywords/i)).toBeInTheDocument();
    expect(screen.getByText('Color')).toBeInTheDocument();
  });

  /**
   * Test 3: Form validation (AC: 3-5)
   */
  it('test_create_folder_form_validation', async () => {
    // Mock API to return existing folders
    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: mockFolders,
      status: 200,
    } as ApiResponse<FolderCategory[]>);

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

    // Test 1: Empty name validation
    const submitButton = screen.getByRole('button', { name: /create category/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/category name is required/i)).toBeInTheDocument();
    });

    // Test 2: Name too long (max 50 chars)
    const nameInput = screen.getByLabelText(/category name/i);
    await user.clear(nameInput);
    await user.type(nameInput, 'a'.repeat(51));
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/must be 50 characters or less/i)).toBeInTheDocument();
    });

    // Test 3: Duplicate name validation (debounced real-time check + submit validation)
    await user.clear(nameInput);
    await user.type(nameInput, 'Work'); // Existing folder name

    // Wait for debounce validation to complete (400ms + buffer)
    await new Promise(resolve => setTimeout(resolve, 500));

    // Wait for duplicate error message to appear
    await waitFor(() => {
      expect(screen.getByText(/a folder with this name already exists/i)).toBeInTheDocument();
    });

    // Submit button should be disabled due to duplicate name
    expect(submitButton).toBeDisabled();
  });

  /**
   * Test 4: Create folder success (AC: 10-11)
   */
  it('test_create_folder_success', async () => {

    // Mock API to return empty folders initially
    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: [],
      status: 200,
    } as ApiResponse<FolderCategory[]>);

    // Mock create folder API
    const newFolder: FolderCategory = {
      id: 4,
      user_id: 1,
      name: 'NewFolder',
      gmail_label_id: 'Label_4',
      keywords: ['test', 'new'],
      color: '#22c55e',
      is_default: false,
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    };

    vi.mocked(apiClient.createFolder).mockResolvedValue({
      data: newFolder,
      status: 200,
    } as ApiResponse<FolderCategory>);

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

    // Fill form
    const nameInput = screen.getByLabelText(/category name/i);
    const keywordsInput = screen.getByLabelText(/keywords/i);

    await user.type(nameInput, 'NewFolder');
    await user.type(keywordsInput, 'test, new');

    // Wait for debounce validation to complete (400ms + buffer)
    await new Promise(resolve => setTimeout(resolve, 500));

    // Submit form
    const submitButton = screen.getByRole('button', { name: /create category/i });
    await user.click(submitButton);

    // Verify API was called with correct data
    await waitFor(() => {
      expect(apiClient.createFolder).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'NewFolder',
          keywords: ['test', 'new'],
        })
      );
    });

    // Verify success toast was shown
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('NewFolder'));
    });

    // Verify dialog closes
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    // Verify folder is added to list
    await waitFor(() => {
      expect(screen.getByText('NewFolder')).toBeInTheDocument();
    });
  });

  /**
   * Test 5: Edit folder pre-fills form (AC: 7)
   */
  it('test_edit_folder_pre_fills_form', async () => {
    // Mock API to return existing folders
    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: mockFolders,
      status: 200,
    } as ApiResponse<FolderCategory[]>);

    const user = userEvent.setup();
    render(<FolderManager />);

    // Wait for folders to load
    await waitFor(() => {
      expect(screen.getByText('Work')).toBeInTheDocument();
    });

    // Click edit button on "Work" folder
    const editButtons = screen.getAllByTitle('Edit category');
    expect(editButtons[0]).toBeDefined();
    await user.click(editButtons[0]!); // First folder is "Work"

    // Verify edit dialog opens
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Edit Category')).toBeInTheDocument();
    });

    // Verify form is pre-filled with current folder data
    const nameInput = screen.getByLabelText(/category name/i) as HTMLInputElement;
    const keywordsInput = screen.getByLabelText(/keywords/i) as HTMLInputElement;

    expect(nameInput.value).toBe('Work');
    expect(keywordsInput.value).toBe('urgent, deadline');
  });

  /**
   * Test 6: Delete folder shows confirmation (AC: 8)
   */
  it('test_delete_folder_shows_confirmation', async () => {
    // Mock API to return existing folders
    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: mockFolders,
      status: 200,
    } as ApiResponse<FolderCategory[]>);

    const user = userEvent.setup();
    render(<FolderManager />);

    // Wait for folders to load
    await waitFor(() => {
      expect(screen.getByText('Work')).toBeInTheDocument();
    });

    // Click delete button on "Work" folder
    const deleteButtons = screen.getAllByTitle('Delete category');
    expect(deleteButtons[0]).toBeDefined();
    await user.click(deleteButtons[0]!);

    // Verify confirmation dialog appears
    await waitFor(() => {
      expect(screen.getByText('Delete Category')).toBeInTheDocument();
    });

    // Verify confirmation message mentions folder name
    expect(screen.getByText(/delete 'work' folder/i)).toBeInTheDocument();
    expect(screen.getByText(/this action cannot be undone/i)).toBeInTheDocument();

    // Verify Cancel and Delete buttons are present
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
  });

  /**
   * Test 7: Default categories suggestions (AC: 9)
   */
  it('test_default_categories_suggestions', async () => {
    // Mock API to return empty folders (first-time setup)
    vi.mocked(apiClient.getFolders).mockResolvedValue({
      data: [],
      status: 200,
    } as ApiResponse<FolderCategory[]>);

    render(<FolderManager />);

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByText(/no folders yet/i)).toBeInTheDocument();
    });

    // Verify 4 default category suggestions are displayed
    expect(screen.getByText('Important')).toBeInTheDocument();
    expect(screen.getByText('Government')).toBeInTheDocument();
    expect(screen.getByText('Clients')).toBeInTheDocument();
    expect(screen.getByText('Newsletters')).toBeInTheDocument();

    // Verify each suggestion has an "Add" button
    const addButtons = screen.getAllByRole('button', { name: /^add$/i });
    expect(addButtons).toHaveLength(4);

    // Verify suggestions show keywords
    expect(screen.getByText('urgent')).toBeInTheDocument();
    expect(screen.getByText('deadline')).toBeInTheDocument();
    expect(screen.getByText('finanzamt')).toBeInTheDocument();
    expect(screen.getByText('tax')).toBeInTheDocument();
  });

  /**
   * Test 8: Color picker selection (AC: 3)
   */
  it('test_color_picker_selection', async () => {
    // Mock API to return empty folders
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

    // Open create dialog
    const addButton = screen.getByRole('button', { name: /add category/i });
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Verify color picker is displayed
    expect(screen.getByText('Color')).toBeInTheDocument();

    // Find all color buttons
    const colorButtons = screen.getAllByRole('button').filter((button) => {
      const style = window.getComputedStyle(button);
      const buttonElement = button as HTMLButtonElement;
      return style.backgroundColor && button.title && buttonElement.type === 'button';
    });

    // Verify at least 10 color options exist
    expect(colorButtons.length).toBeGreaterThanOrEqual(10);

    // Click on a color (e.g., Blue)
    const blueButton = colorButtons.find(
      (button) => button.title === 'Blue'
    );
    expect(blueButton).toBeDefined();

    if (blueButton) {
      await user.click(blueButton);

      // Verify color is selected (has checkmark)
      await waitFor(() => {
        // Lucide icons don't have data-testid by default, so check if Check icon is rendered
        expect(blueButton.querySelector('svg')).toBeInTheDocument();
      });
    }
  });
});
