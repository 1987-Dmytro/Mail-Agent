import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FolderKanban, Plus, Check, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import type { StepProps } from './OnboardingWizard';
import type { FolderCategory } from '@/types/folder';

/**
 * Default folder suggestions for quick setup
 * Users can add these with one click or create custom folders
 */
const DEFAULT_FOLDERS = [
  {
    name: 'Important',
    keywords: ['urgent', 'важно', 'wichtig'],
    color: '#EF4444', // red
    description: 'Urgent emails requiring immediate attention',
  },
  {
    name: 'Government',
    keywords: ['finanzamt', 'ausländerbehörde', 'tax', 'visa'],
    color: '#F97316', // orange
    description: 'Government, tax, and legal correspondence',
  },
  {
    name: 'Clients',
    keywords: ['meeting', 'project', 'client'],
    color: '#3B82F6', // blue
    description: 'Client communications and project updates',
  },
];

/**
 * FolderSetupStep - Step 4 of onboarding wizard
 *
 * Simplified folder creation interface (subset of full folder management from Story 4.4)
 *
 * Features:
 * - Display 3 suggested default folders
 * - "Add These Defaults" button to create all 3 at once
 * - "+ Add Custom Folder" button for manual creation
 * - Show current folder count
 * - Validate: At least 1 folder required before proceeding
 * - Call apiClient.createFolder() for each folder creation
 * - Automatically enable "Next" when folders.length >= 1
 *
 * AC5: Step 4 (Folders) - Folder setup page (simplified category creation, minimum 1 folder required, suggests 3 defaults)
 * AC8: Steps cannot proceed until required actions completed (at least 1 folder created before Step 5)
 */
export default function FolderSetupStep({ onStepComplete, currentState }: StepProps) {
  const [isCreatingDefaults, setIsCreatingDefaults] = useState<boolean>(false);
  const [createdFolders, setCreatedFolders] = useState<FolderCategory[]>(currentState.folders);
  const [showCustomForm, setShowCustomForm] = useState<boolean>(false);
  const [customName, setCustomName] = useState<string>('');
  const [customKeywords, setCustomKeywords] = useState<string>('');
  const [isCreatingCustom, setIsCreatingCustom] = useState<boolean>(false);
  const [isLoadingFolders, setIsLoadingFolders] = useState<boolean>(false);

  /**
   * Fetch existing folders from API on component mount
   * This ensures that if user created folders earlier and refreshed the page,
   * the folders will be loaded from the database and displayed
   */
  useEffect(() => {
    console.log('FolderSetupStep: useEffect running, fetching folders...');
    const loadExistingFolders = async () => {
      try {
        setIsLoadingFolders(true);
        console.log('FolderSetupStep: Calling apiClient.getFolders()');
        const response = await apiClient.getFolders();
        console.log('FolderSetupStep: Got response:', response);

        // The response IS the array directly, not wrapped in {data: ...}
        const foldersData = (response as unknown) as any[];
        console.log('FolderSetupStep: foldersData:', foldersData);
        console.log('FolderSetupStep: Is array?', Array.isArray(foldersData));
        console.log('FolderSetupStep: Length:', foldersData?.length);

        if (foldersData && Array.isArray(foldersData) && foldersData.length > 0) {
          console.log('FolderSetupStep: Mapping folders...');
          // Map API response to FolderCategory type
          const folders: FolderCategory[] = foldersData.map((folder) => {
            console.log('FolderSetupStep: Mapping folder:', folder);
            return {
              id: folder.id,
              user_id: folder.user_id,
              name: folder.name,
              gmail_label_id: folder.gmail_label_id,
              keywords: folder.keywords || [],
              color: folder.color || '#6B7280',
              is_default: folder.is_default,
              created_at: folder.created_at,
              updated_at: folder.updated_at,
            };
          });

          console.log('FolderSetupStep: Mapped folders:', folders);

          // Update local state
          console.log('FolderSetupStep: Calling setCreatedFolders...');
          setCreatedFolders(folders);

          // Update wizard state so validation passes and localStorage is updated
          console.log('FolderSetupStep: Calling onStepComplete...');
          onStepComplete({
            ...currentState,
            folders,
          });

          console.log(`Loaded ${folders.length} existing folders from API`);
        } else {
          console.log('FolderSetupStep: No folders found or invalid response');
        }
      } catch (error) {
        console.error('FolderSetupStep: Failed to load existing folders:', error);
        console.error('FolderSetupStep: Error stack:', (error as Error).stack);
        // Don't show error toast - just log it. User can still create new folders.
      } finally {
        console.log('FolderSetupStep: Finally block - setting isLoadingFolders to false');
        setIsLoadingFolders(false);
      }
    };

    loadExistingFolders();
  }, []); // Run once on mount

  /**
   * Handle "Add These Defaults" button click
   * Creates all 3 default folders via API
   */
  const handleAddDefaults = async () => {
    setIsCreatingDefaults(true);

    try {
      const newFolders: FolderCategory[] = [];

      // Create each default folder sequentially
      for (const folder of DEFAULT_FOLDERS) {
        const response = await apiClient.createFolder({
          name: folder.name,
          keywords: folder.keywords,
          color: folder.color || '#6B7280',
        });

        newFolders.push(response.data as FolderCategory);
      }

      // Update state
      setCreatedFolders([...createdFolders, ...newFolders]);

      // Notify wizard
      onStepComplete({
        ...currentState,
        folders: [...createdFolders, ...newFolders],
      });

      toast.success(`Created ${newFolders.length} folder categories successfully!`);
    } catch (error) {
      console.error('Failed to create default folders:', error);
      toast.error('Failed to create default folders. Please try again.');
    } finally {
      setIsCreatingDefaults(false);
    }
  };

  /**
   * Handle custom folder creation
   * Validates input and creates folder via API
   */
  const handleCreateCustom = async () => {
    if (!customName.trim()) {
      toast.error('Folder name is required');
      return;
    }

    if (customName.length > 50) {
      toast.error('Folder name must be 50 characters or less');
      return;
    }

    setIsCreatingCustom(true);

    try {
      const keywords = customKeywords
        .split(',')
        .map((k) => k.trim())
        .filter((k) => k.length > 0);

      const response = await apiClient.createFolder({
        name: customName.trim(),
        keywords: keywords.length > 0 ? keywords : undefined,
        color: '#6B7280', // default gray
      });

      const newFolder = response.data as FolderCategory;

      // Update state
      setCreatedFolders([...createdFolders, newFolder]);

      // Notify wizard
      onStepComplete({
        ...currentState,
        folders: [...createdFolders, newFolder],
      });

      toast.success(`Folder "${customName}" created successfully!`);

      // Reset form
      setCustomName('');
      setCustomKeywords('');
      setShowCustomForm(false);
    } catch (error) {
      console.error('Failed to create custom folder:', error);
      toast.error('Failed to create folder. Please try again.');
    } finally {
      setIsCreatingCustom(false);
    }
  };

  return (
    <div className="flex flex-col items-center text-center space-y-6">
      {/* Header */}
      <div className="w-full space-y-3">
        <h2 className="text-2xl font-bold">Setup Your Folders</h2>
        <p className="text-muted-foreground">
          Create at least one folder category to organize your emails. You can add more later.
        </p>
      </div>

      {/* Folder count indicator */}
      {createdFolders.length > 0 && (
        <Card className="border-primary/50 bg-primary/5">
          <CardContent className="flex items-center gap-2 py-3">
            <Check className="h-5 w-5 text-primary" />
            <span className="font-semibold">
              {createdFolders.length} folder{createdFolders.length !== 1 ? 's' : ''} configured
            </span>
          </CardContent>
        </Card>
      )}

      {/* Default folders suggestion */}
      {createdFolders.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderKanban className="h-5 w-5" />
              Suggested Folders
            </CardTitle>
            <CardDescription>
              Start with these 3 popular categories (you can customize them later)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {DEFAULT_FOLDERS.map((folder) => (
              <div key={folder.name} className="flex items-start gap-3 rounded-lg border p-3">
                <div
                  className="mt-1 h-4 w-4 flex-shrink-0 rounded-full"
                  style={{ backgroundColor: folder.color || '#6B7280' }}
                />
                <div className="flex-1">
                  <h4 className="font-semibold">{folder.name}</h4>
                  <p className="text-sm text-muted-foreground">{folder.description}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Keywords: {folder.keywords.join(', ')}
                  </p>
                </div>
              </div>
            ))}

            <Button
              onClick={handleAddDefaults}
              disabled={isCreatingDefaults}
              className="w-full"
              size="lg"
            >
              {isCreatingDefaults ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating folders...
                </>
              ) : (
                <>
                  <Plus className="mr-2 h-4 w-4" />
                  Add These 3 Folders
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Custom folder creation */}
      <Card>
        <CardHeader>
          <CardTitle>Custom Folder</CardTitle>
          <CardDescription>Create your own folder category</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!showCustomForm ? (
            <Button
              onClick={() => setShowCustomForm(true)}
              variant="outline"
              className="w-full"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Custom Folder
            </Button>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="folderName">Folder Name *</Label>
                <Input
                  id="folderName"
                  placeholder="e.g., Newsletters, Family, Work"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  maxLength={50}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="keywords">
                  Keywords (optional, comma-separated)
                </Label>
                <Input
                  id="keywords"
                  placeholder="e.g., newsletter, updates, digest"
                  value={customKeywords}
                  onChange={(e) => setCustomKeywords(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  AI uses these keywords to automatically sort emails into this folder
                </p>
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={handleCreateCustom}
                  disabled={isCreatingCustom || !customName.trim()}
                  className="flex-1"
                >
                  {isCreatingCustom ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Create Folder'
                  )}
                </Button>
                <Button
                  onClick={() => {
                    setShowCustomForm(false);
                    setCustomName('');
                    setCustomKeywords('');
                  }}
                  variant="outline"
                  disabled={isCreatingCustom}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Created folders list */}
      {createdFolders.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Your Folders</CardTitle>
            <CardDescription>
              {createdFolders.length} folder{createdFolders.length !== 1 ? 's' : ''} ready for email
              sorting
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {createdFolders.map((folder) => (
                <div
                  key={folder.id}
                  className="flex items-center gap-3 rounded-lg border p-3"
                >
                  <div
                    className="h-4 w-4 flex-shrink-0 rounded-full"
                    style={{ backgroundColor: folder.color || '#6B7280' }}
                  />
                  <div className="flex-1">
                    <span className="font-medium">{folder.name}</span>
                    {folder.keywords && folder.keywords.length > 0 && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        ({folder.keywords.join(', ')})
                      </span>
                    )}
                  </div>
                  <Check className="h-4 w-4 text-green-600" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
