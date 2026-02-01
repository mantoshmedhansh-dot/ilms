/**
 * Upload API client for file uploads to Supabase Storage
 */
import { apiClient } from './client';

// Upload categories matching backend
export type UploadCategory = 'logos' | 'products' | 'categories' | 'brands' | 'documents' | 'signatures';

// Response types
export interface UploadResponse {
  url: string;
  thumbnail_url?: string;
  file_name: string;
  file_size: number;
  content_type: string;
}

export interface MultiUploadResponse {
  files: UploadResponse[];
  total: number;
}

export interface DeleteResponse {
  success: boolean;
  message: string;
}

// Progress callback type
export type ProgressCallback = (progress: number) => void;

/**
 * Upload a single image file
 */
export async function uploadImage(
  file: File,
  category: UploadCategory = 'logos',
  onProgress?: ProgressCallback
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', category);

  const response = await apiClient.post<UploadResponse>('/uploads/image', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });

  return response.data;
}

/**
 * Upload multiple image files
 */
export async function uploadImages(
  files: File[],
  category: UploadCategory = 'products',
  onProgress?: ProgressCallback
): Promise<MultiUploadResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });
  formData.append('category', category);

  const response = await apiClient.post<MultiUploadResponse>('/uploads/images', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });

  return response.data;
}

/**
 * Upload a document file (PDF)
 */
export async function uploadDocument(
  file: File,
  category: UploadCategory = 'documents',
  onProgress?: ProgressCallback
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', category);

  const response = await apiClient.post<UploadResponse>('/uploads/document', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });

  return response.data;
}

/**
 * Delete a file by URL
 */
export async function deleteFile(url: string): Promise<DeleteResponse> {
  const response = await apiClient.delete<DeleteResponse>('/uploads', {
    data: { url },
  });

  return response.data;
}

// Export all functions as a single object for convenience
export const uploadApi = {
  uploadImage,
  uploadImages,
  uploadDocument,
  deleteFile,
};
