'use client';

import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  uploadImage,
  uploadImages,
  uploadDocument,
  deleteFile,
  UploadCategory,
  UploadResponse,
} from '@/lib/api/upload';

interface UseFileUploadOptions {
  category?: UploadCategory;
  onSuccess?: (result: UploadResponse) => void;
  onError?: (error: Error) => void;
}

interface UseFileUploadReturn {
  upload: (file: File) => Promise<UploadResponse | null>;
  remove: (url: string) => Promise<boolean>;
  isUploading: boolean;
  progress: number;
  error: Error | null;
}

/**
 * Hook for single file upload
 */
export function useFileUpload(options: UseFileUploadOptions = {}): UseFileUploadReturn {
  const { category = 'logos', onSuccess, onError } = options;

  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<Error | null>(null);

  const upload = useCallback(
    async (file: File): Promise<UploadResponse | null> => {
      setIsUploading(true);
      setProgress(0);
      setError(null);

      try {
        const result = await uploadImage(file, category, setProgress);
        toast.success('File uploaded successfully');
        onSuccess?.(result);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Upload failed');
        setError(error);
        toast.error(error.message || 'Upload failed');
        onError?.(error);
        return null;
      } finally {
        setIsUploading(false);
      }
    },
    [category, onSuccess, onError]
  );

  const remove = useCallback(async (url: string): Promise<boolean> => {
    try {
      const result = await deleteFile(url);
      if (result.success) {
        toast.success('File deleted');
        return true;
      }
      return false;
    } catch {
      toast.error('Failed to delete file');
      return false;
    }
  }, []);

  return { upload, remove, isUploading, progress, error };
}

interface UseMultiFileUploadOptions {
  category?: UploadCategory;
  maxFiles?: number;
  onSuccess?: (results: UploadResponse[]) => void;
  onError?: (error: Error) => void;
}

interface UseMultiFileUploadReturn {
  upload: (files: File[]) => Promise<UploadResponse[]>;
  remove: (url: string) => Promise<boolean>;
  isUploading: boolean;
  progress: number;
  error: Error | null;
}

/**
 * Hook for multiple file upload
 */
export function useMultiFileUpload(
  options: UseMultiFileUploadOptions = {}
): UseMultiFileUploadReturn {
  const { category = 'products', maxFiles = 10, onSuccess, onError } = options;

  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<Error | null>(null);

  const upload = useCallback(
    async (files: File[]): Promise<UploadResponse[]> => {
      if (files.length > maxFiles) {
        const error = new Error(`Maximum ${maxFiles} files allowed`);
        toast.error(error.message);
        onError?.(error);
        return [];
      }

      setIsUploading(true);
      setProgress(0);
      setError(null);

      try {
        const result = await uploadImages(files, category, setProgress);
        toast.success(`${result.total} files uploaded successfully`);
        onSuccess?.(result.files);
        return result.files;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Upload failed');
        setError(error);
        toast.error(error.message || 'Upload failed');
        onError?.(error);
        return [];
      } finally {
        setIsUploading(false);
      }
    },
    [category, maxFiles, onSuccess, onError]
  );

  const remove = useCallback(async (url: string): Promise<boolean> => {
    try {
      const result = await deleteFile(url);
      if (result.success) {
        toast.success('File deleted');
        return true;
      }
      return false;
    } catch {
      toast.error('Failed to delete file');
      return false;
    }
  }, []);

  return { upload, remove, isUploading, progress, error };
}

interface UseDocumentUploadOptions {
  category?: UploadCategory;
  onSuccess?: (result: UploadResponse) => void;
  onError?: (error: Error) => void;
}

/**
 * Hook for document (PDF) upload
 */
export function useDocumentUpload(
  options: UseDocumentUploadOptions = {}
): UseFileUploadReturn {
  const { category = 'documents', onSuccess, onError } = options;

  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<Error | null>(null);

  const upload = useCallback(
    async (file: File): Promise<UploadResponse | null> => {
      setIsUploading(true);
      setProgress(0);
      setError(null);

      try {
        const result = await uploadDocument(file, category, setProgress);
        toast.success('Document uploaded successfully');
        onSuccess?.(result);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Upload failed');
        setError(error);
        toast.error(error.message || 'Upload failed');
        onError?.(error);
        return null;
      } finally {
        setIsUploading(false);
      }
    },
    [category, onSuccess, onError]
  );

  const remove = useCallback(async (url: string): Promise<boolean> => {
    try {
      const result = await deleteFile(url);
      if (result.success) {
        toast.success('Document deleted');
        return true;
      }
      return false;
    } catch {
      toast.error('Failed to delete document');
      return false;
    }
  }, []);

  return { upload, remove, isUploading, progress, error };
}
