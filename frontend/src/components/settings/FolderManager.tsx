'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Trash2, Edit, Plus, Check } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { FolderCategory, CreateFolderRequest, UpdateFolderRequest } from '@/types/folder';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * Predefined color palette for folder categories
 */
const COLOR_PALETTE = [
  { name: 'Red', value: '#ef4444' },
  { name: 'Orange', value: '#f97316' },
  { name: 'Yellow', value: '#eab308' },
  { name: 'Green', value: '#22c55e' },
  { name: 'Teal', value: '#14b8a6' },
  { name: 'Blue', value: '#3b82f6' },
  { name: 'Indigo', value: '#6366f1' },
  { name: 'Purple', value: '#a855f7' },
  { name: 'Pink', value: '#ec4899' },
  { name: 'Gray', value: '#64748b' },
];

/**
 * Default category suggestions for first-time setup
 */
const DEFAULT_CATEGORIES = [
  {
    name: 'Important',
    keywords: ['urgent', 'deadline', 'wichtig', 'срочно', 'терміново'],
    color: '#ef4444',
  },
  {
    name: 'Government',
    keywords: ['finanzamt', 'tax', 'visa', 'behörde', 'steuer', 'налог', 'державний'],
    color: '#f97316',
  },
  {
    name: 'Clients',
    keywords: ['meeting', 'project', 'contract', 'client', 'kunde', 'клієнт'],
    color: '#3b82f6',
  },
  {
    name: 'Newsletters',
    keywords: ['unsubscribe', 'newsletter', 'marketing', 'рассылка', 'розсилка'],
    color: '#64748b',
  },
];

/**
 * Form validation schema
 */
const folderFormSchema = z.object({
  name: z
    .string()
    .min(1, 'Category name is required')
    .max(50, 'Category name must be 50 characters or less')
    .trim(),
  keywords: z.string().optional(),
  color: z.string().regex(/^#[0-9A-Fa-f]{6}$/, 'Invalid color format').optional(),
});

type FolderFormData = z.infer<typeof folderFormSchema>;

/**
 * FolderManager Component
 * Manages CRUD operations for email folder categories
 */
export default function FolderManager() {
  const [folders, setFolders] = useState<FolderCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Dialog states
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  // Current folder being edited/deleted
  const [currentFolder, setCurrentFolder] = useState<FolderCategory | null>(null);

  // Selected color in color picker
  const [selectedColor, setSelectedColor] = useState<string>(COLOR_PALETTE[0]?.value || '#3b82f6');

  // Real-time duplicate name validation state
  const [duplicateNameError, setDuplicateNameError] = useState<string>('');
  const [isCheckingName, setIsCheckingName] = useState(false);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Form handling
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<FolderFormData>({
    resolver: zodResolver(folderFormSchema),
    defaultValues: {
      name: '',
      keywords: '',
      color: COLOR_PALETTE[0]?.value || '#3b82f6',
    },
  });

  // Watch name field for real-time validation
  const watchedName = watch('name');

  /**
   * Check if folder name is unique (case-insensitive)
   * Memoized to prevent unnecessary re-creation in useEffect
   * MUST be defined before useEffect that uses it (hoisting fix)
   */
  const isNameUnique = useCallback((name: string, excludeFolderId?: number): boolean => {
    const normalizedName = name.toLowerCase().trim();
    return !folders.some(
      (folder) =>
        folder.name.toLowerCase().trim() === normalizedName &&
        folder.id !== excludeFolderId
    );
  }, [folders]);

  /**
   * Fetch folders on component mount
   */
  useEffect(() => {
    fetchFolders();
  }, []);

  /**
   * Debounced duplicate name validation (runs while user types)
   * Debounces validation to avoid excessive checks during typing
   */
  useEffect(() => {
    // Clear previous timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Reset error if name is empty
    if (!watchedName || watchedName.trim().length === 0) {
      setDuplicateNameError('');
      setIsCheckingName(false);
      return;
    }

    // Set checking state
    setIsCheckingName(true);

    // Debounce validation by 400ms
    debounceTimerRef.current = setTimeout(() => {
      const excludeId = isEditDialogOpen ? currentFolder?.id : undefined;
      const isDuplicate = !isNameUnique(watchedName, excludeId);

      if (isDuplicate) {
        setDuplicateNameError('A folder with this name already exists');
      } else {
        setDuplicateNameError('');
      }

      setIsCheckingName(false);
    }, 400);

    // Cleanup timer on unmount
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [watchedName, folders, isEditDialogOpen, currentFolder, isNameUnique]);

  /**
   * Fetch folders from backend
   */
  const fetchFolders = async () => {
    try {
      setLoading(true);
      const response = await apiClient.getFolders();
      setFolders(response.data || []);
    } catch (error) {
      toast.error('Failed to load folders. Please try again.');
      console.error('Failed to fetch folders:', error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Open create dialog
   */
  const handleOpenCreateDialog = () => {
    const randomColor = COLOR_PALETTE[Math.floor(Math.random() * COLOR_PALETTE.length)]?.value || '#3b82f6';
    reset({
      name: '',
      keywords: '',
      color: randomColor,
    });
    setSelectedColor(randomColor);
    setDuplicateNameError(''); // Clear duplicate error
    setIsCheckingName(false);
    setIsCreateDialogOpen(true);
  };

  /**
   * Open edit dialog
   */
  const handleOpenEditDialog = (folder: FolderCategory) => {
    setCurrentFolder(folder);
    reset({
      name: folder.name,
      keywords: folder.keywords.join(', '),
      color: folder.color,
    });
    setSelectedColor(folder.color);
    setDuplicateNameError(''); // Clear duplicate error
    setIsCheckingName(false);
    setIsEditDialogOpen(true);
  };

  /**
   * Open delete confirmation dialog
   */
  const handleOpenDeleteDialog = (folder: FolderCategory) => {
    setCurrentFolder(folder);
    setIsDeleteDialogOpen(true);
  };

  /**
   * Handle folder creation
   */
  const handleCreateFolder = async (data: FolderFormData) => {
    // Validate name uniqueness (final check on submit)
    if (!isNameUnique(data.name)) {
      setDuplicateNameError('A folder with this name already exists');
      toast.error('A folder with this name already exists');
      return;
    }

    // Clear any previous duplicate error
    setDuplicateNameError('');

    try {
      setSubmitting(true);

      // Parse keywords from comma-separated string
      const keywords = data.keywords
        ? data.keywords.split(',').map((k) => k.trim()).filter(Boolean)
        : [];

      const createData: CreateFolderRequest = {
        name: data.name.trim(),
        keywords,
        color: selectedColor,
      };

      const response = await apiClient.createFolder(createData);

      if (response.data) {
        // Optimistic UI update
        setFolders([...folders, response.data]);
        toast.success(`Category '${response.data.name}' created!`);
        setIsCreateDialogOpen(false);
        reset();
      }
    } catch (error) {
      console.error('Failed to create folder:', error);
      toast.error('Failed to create category. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  /**
   * Handle folder update
   */
  const handleUpdateFolder = async (data: FolderFormData) => {
    if (!currentFolder) return;

    // Validate name uniqueness (excluding current folder) (final check on submit)
    if (!isNameUnique(data.name, currentFolder.id)) {
      setDuplicateNameError('A folder with this name already exists');
      toast.error('A folder with this name already exists');
      return;
    }

    // Clear any previous duplicate error
    setDuplicateNameError('');

    try {
      setSubmitting(true);

      // Parse keywords from comma-separated string
      const keywords = data.keywords
        ? data.keywords.split(',').map((k) => k.trim()).filter(Boolean)
        : [];

      const updateData: UpdateFolderRequest = {
        name: data.name.trim(),
        keywords,
        color: selectedColor,
      };

      const response = await apiClient.updateFolder(currentFolder.id, updateData);

      if (response.data) {
        // Update folder in local state
        setFolders(
          folders.map((folder) =>
            folder.id === currentFolder.id ? response.data : folder
          )
        );
        toast.success(`Category '${response.data.name}' updated!`);
        setIsEditDialogOpen(false);
        setCurrentFolder(null);
        reset();
      }
    } catch (error) {
      console.error('Failed to update folder:', error);
      toast.error('Failed to update category. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  /**
   * Handle folder deletion
   */
  const handleDeleteFolder = async () => {
    if (!currentFolder) return;

    try {
      setSubmitting(true);
      await apiClient.deleteFolder(currentFolder.id);

      // Remove folder from local state
      setFolders(folders.filter((folder) => folder.id !== currentFolder.id));
      toast.success(`Category '${currentFolder.name}' deleted`);
      setIsDeleteDialogOpen(false);
      setCurrentFolder(null);
    } catch (error) {
      console.error('Failed to delete folder:', error);
      toast.error('Failed to delete category. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  /**
   * Add default category
   */
  const handleAddDefaultCategory = async (defaultCategory: typeof DEFAULT_CATEGORIES[0]) => {
    // Check if category with same name already exists
    if (!isNameUnique(defaultCategory.name)) {
      toast.error(`Category '${defaultCategory.name}' already exists`);
      return;
    }

    try {
      const createData: CreateFolderRequest = {
        name: defaultCategory.name,
        keywords: defaultCategory.keywords,
        color: defaultCategory.color,
      };

      const response = await apiClient.createFolder(createData);

      if (response.data) {
        setFolders([...folders, response.data]);
        toast.success(`Category '${response.data.name}' created!`);
      }
    } catch (error) {
      console.error('Failed to create default category:', error);
      toast.error(`Failed to create '${defaultCategory.name}'. Please try again.`);
    }
  };

  /**
   * Handle color selection
   */
  const handleColorSelect = (color: string) => {
    setSelectedColor(color);
    setValue('color', color);
  };

  // Loading state
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-4 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // Empty state with default category suggestions
  const showDefaultSuggestions = folders.length === 0;

  return (
    <div className="space-y-6">
      {/* Add Category Button */}
      <div className="flex justify-between items-center">
        <div>
          <p className="text-sm text-muted-foreground">
            {folders.length} {folders.length === 1 ? 'category' : 'categories'}
          </p>
        </div>
        <Button onClick={handleOpenCreateDialog}>
          <Plus className="mr-2 h-4 w-4" />
          Add Category
        </Button>
      </div>

      {/* Default Category Suggestions (Empty State) */}
      {showDefaultSuggestions && (
        <div className="border-2 border-dashed rounded-lg p-8">
          <div className="text-center mb-6">
            <h3 className="text-lg font-semibold mb-2">No folders yet. Create your first category!</h3>
            <p className="text-sm text-muted-foreground">
              Get started quickly with these default categories, or create your own custom ones.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {DEFAULT_CATEGORIES.map((category) => (
              <Card key={category.name} className="border-2">
                <CardHeader>
                  <CardTitle className="flex items-center text-base">
                    <div
                      className="w-3 h-3 rounded-full mr-2"
                      style={{ backgroundColor: category.color }}
                    />
                    {category.name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-1 mb-3">
                    {category.keywords.slice(0, 3).map((keyword) => (
                      <span
                        key={keyword}
                        className="text-xs bg-secondary px-2 py-1 rounded-full"
                      >
                        {keyword}
                      </span>
                    ))}
                    {category.keywords.length > 3 && (
                      <span className="text-xs text-muted-foreground">
                        +{category.keywords.length - 3} more
                      </span>
                    )}
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full"
                    onClick={() => handleAddDefaultCategory(category)}
                  >
                    <Plus className="mr-2 h-3 w-3" />
                    Add
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Folder Cards */}
      {folders.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {folders.map((folder) => (
            <Card key={folder.id} data-folder-name={folder.name}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-lg">
                  <div className="flex items-center">
                    <div
                      className="w-3 h-3 rounded-full mr-2"
                      style={{ backgroundColor: folder.color }}
                    />
                    <span className="font-semibold">{folder.name}</span>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => handleOpenEditDialog(folder)}
                      title="Edit category"
                      aria-label="Edit category"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => handleOpenDeleteDialog(folder)}
                      title="Delete category"
                      aria-label="Delete category"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {folder.keywords.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {folder.keywords.map((keyword) => (
                      <span
                        key={keyword}
                        className="text-xs bg-secondary px-2 py-1 rounded-full"
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No keywords</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Folder Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Category</DialogTitle>
            <DialogDescription>
              Create a new email folder category with custom keywords and color.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(handleCreateFolder)} className="space-y-4">
            {/* Category Name */}
            <div className="space-y-2">
              <Label htmlFor="create-name">Category Name *</Label>
              <Input
                id="create-name"
                placeholder="e.g., Work, Personal, Important"
                {...register('name')}
                disabled={submitting}
                className={duplicateNameError ? 'border-destructive' : ''}
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
              {!errors.name && duplicateNameError && (
                <p className="text-sm text-destructive">{duplicateNameError}</p>
              )}
              {!errors.name && !duplicateNameError && isCheckingName && (
                <p className="text-sm text-muted-foreground">Checking availability...</p>
              )}
            </div>

            {/* Keywords */}
            <div className="space-y-2">
              <Label htmlFor="create-keywords">
                Keywords (comma-separated, optional)
              </Label>
              <Input
                id="create-keywords"
                placeholder="e.g., urgent, deadline, important"
                {...register('keywords')}
                disabled={submitting}
              />
              <p className="text-xs text-muted-foreground">
                Separate multiple keywords with commas
              </p>
              {errors.keywords && (
                <p className="text-sm text-destructive">{errors.keywords.message}</p>
              )}
            </div>

            {/* Color Picker */}
            <div className="space-y-2">
              <Label>Color</Label>
              <div className="grid grid-cols-5 gap-2">
                {COLOR_PALETTE.map((color) => (
                  <button
                    key={color.value}
                    type="button"
                    className={`w-12 h-12 rounded-lg border-2 transition-all ${
                      selectedColor === color.value
                        ? 'border-primary ring-2 ring-primary ring-offset-2'
                        : 'border-transparent hover:border-primary/50'
                    }`}
                    style={{ backgroundColor: color.value }}
                    onClick={() => handleColorSelect(color.value)}
                    disabled={submitting}
                    title={color.name}
                  >
                    {selectedColor === color.value && (
                      <Check className="h-4 w-4 text-white mx-auto" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsCreateDialogOpen(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={submitting || !!duplicateNameError || isCheckingName}>
                {submitting ? 'Creating...' : 'Create Category'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Folder Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Category</DialogTitle>
            <DialogDescription>
              Update category name, keywords, and color.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(handleUpdateFolder)} className="space-y-4">
            {/* Category Name */}
            <div className="space-y-2">
              <Label htmlFor="edit-name">Category Name *</Label>
              <Input
                id="edit-name"
                placeholder="e.g., Work, Personal, Important"
                {...register('name')}
                disabled={submitting}
                className={duplicateNameError ? 'border-destructive' : ''}
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
              {!errors.name && duplicateNameError && (
                <p className="text-sm text-destructive">{duplicateNameError}</p>
              )}
              {!errors.name && !duplicateNameError && isCheckingName && (
                <p className="text-sm text-muted-foreground">Checking availability...</p>
              )}
            </div>

            {/* Keywords */}
            <div className="space-y-2">
              <Label htmlFor="edit-keywords">
                Keywords (comma-separated, optional)
              </Label>
              <Input
                id="edit-keywords"
                placeholder="e.g., urgent, deadline, important"
                {...register('keywords')}
                disabled={submitting}
              />
              <p className="text-xs text-muted-foreground">
                Separate multiple keywords with commas
              </p>
              {errors.keywords && (
                <p className="text-sm text-destructive">{errors.keywords.message}</p>
              )}
            </div>

            {/* Color Picker */}
            <div className="space-y-2">
              <Label>Color</Label>
              <div className="grid grid-cols-5 gap-2">
                {COLOR_PALETTE.map((color) => (
                  <button
                    key={color.value}
                    type="button"
                    className={`w-12 h-12 rounded-lg border-2 transition-all ${
                      selectedColor === color.value
                        ? 'border-primary ring-2 ring-primary ring-offset-2'
                        : 'border-transparent hover:border-primary/50'
                    }`}
                    style={{ backgroundColor: color.value }}
                    onClick={() => handleColorSelect(color.value)}
                    disabled={submitting}
                    title={color.name}
                  >
                    {selectedColor === color.value && (
                      <Check className="h-4 w-4 text-white mx-auto" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsEditDialogOpen(false);
                  setCurrentFolder(null);
                }}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={submitting || !!duplicateNameError || isCheckingName}>
                {submitting ? 'Updating...' : 'Update Category'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Category</AlertDialogTitle>
            <AlertDialogDescription>
              Delete &apos;{currentFolder?.name}&apos; folder? This will also remove the Gmail label. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => {
                setIsDeleteDialogOpen(false);
                setCurrentFolder(null);
              }}
              disabled={submitting}
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteFolder}
              disabled={submitting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {submitting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
