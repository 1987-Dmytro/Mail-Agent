/**
 * Folder category model
 */
export interface FolderCategory {
  id: number;
  user_id: number;
  name: string;
  gmail_label_id: string;
  keywords: string[];
  color: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Request payload for creating folder category
 */
export interface CreateFolderRequest {
  name: string;
  keywords?: string[];
  color?: string;
}

/**
 * Request payload for updating folder category
 */
export interface UpdateFolderRequest {
  name?: string;
  keywords?: string[];
  color?: string;
  is_default?: boolean;
}
