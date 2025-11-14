import FolderManager from '@/components/settings/FolderManager';

/**
 * Folder Management Settings Page
 * Server Component (default) - delegates client interactions to FolderManager
 */
export default function FoldersSettingsPage() {
  return (
    <div className="container mx-auto py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Folder Categories</h1>
        <p className="text-muted-foreground mt-2">
          Create and manage your email folder categories. Categories help organize your emails with custom labels in Gmail.
        </p>
      </div>
      <FolderManager />
    </div>
  );
}
