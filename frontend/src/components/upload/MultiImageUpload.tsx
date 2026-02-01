'use client';

import { useState, useCallback, useRef } from 'react';
import { Upload, X, Loader2, ImageIcon, Star } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useMultiFileUpload } from '@/hooks/use-file-upload';
import { UploadCategory, UploadResponse } from '@/lib/api/upload';

interface ImageItem {
  id: string;
  url: string;
  thumbnail_url?: string;
  is_primary?: boolean;
}

interface MultiImageUploadProps {
  value: ImageItem[];
  onChange: (images: ImageItem[]) => void;
  category?: UploadCategory;
  label?: string;
  description?: string;
  className?: string;
  disabled?: boolean;
  maxFiles?: number;
}

export function MultiImageUpload({
  value = [],
  onChange,
  category = 'products',
  label,
  description,
  className,
  disabled = false,
  maxFiles = 10,
}: MultiImageUploadProps) {
  const [previews, setPreviews] = useState<{ id: string; url: string }[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { upload, remove, isUploading, progress } = useMultiFileUpload({
    category,
    maxFiles,
    onSuccess: (results) => {
      const newImages: ImageItem[] = results.map((r) => ({
        id: crypto.randomUUID(),
        url: r.url,
        thumbnail_url: r.thumbnail_url,
        is_primary: value.length === 0 && results.indexOf(r) === 0,
      }));
      onChange([...value, ...newImages]);
      setPreviews([]);
    },
    onError: () => {
      setPreviews([]);
    },
  });

  const handleFilesSelect = useCallback(
    async (files: File[]) => {
      const remaining = maxFiles - value.length;
      const filesToUpload = files.slice(0, remaining);

      if (filesToUpload.length === 0) return;

      // Show previews immediately
      const newPreviews: { id: string; url: string }[] = [];
      for (const file of filesToUpload) {
        const reader = new FileReader();
        const previewUrl = await new Promise<string>((resolve) => {
          reader.onload = (e) => resolve(e.target?.result as string);
          reader.readAsDataURL(file);
        });
        newPreviews.push({ id: crypto.randomUUID(), url: previewUrl });
      }
      setPreviews(newPreviews);

      // Upload files
      await upload(filesToUpload);
    },
    [upload, maxFiles, value.length]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length > 0) {
        handleFilesSelect(files);
      }
      e.target.value = '';
    },
    [handleFilesSelect]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (disabled || isUploading) return;

      const files = Array.from(e.dataTransfer.files).filter((f) =>
        f.type.startsWith('image/')
      );
      if (files.length > 0) {
        handleFilesSelect(files);
      }
    },
    [disabled, isUploading, handleFilesSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleRemove = useCallback(
    async (index: number) => {
      const image = value[index];
      await remove(image.url);
      const newImages = value.filter((_, i) => i !== index);
      // If we removed the primary, make the first one primary
      if (image.is_primary && newImages.length > 0) {
        newImages[0].is_primary = true;
      }
      onChange(newImages);
    },
    [value, remove, onChange]
  );

  const handleSetPrimary = useCallback(
    (index: number) => {
      const newImages = value.map((img, i) => ({
        ...img,
        is_primary: i === index,
      }));
      onChange(newImages);
    },
    [value, onChange]
  );

  const handleClick = useCallback(() => {
    if (!disabled && !isUploading && value.length < maxFiles) {
      fileInputRef.current?.click();
    }
  }, [disabled, isUploading, value.length, maxFiles]);

  const canAddMore = value.length < maxFiles;

  return (
    <div className={cn('space-y-2', className)}>
      {label && (
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">{label}</label>
          <span className="text-xs text-gray-500">
            {value.length}/{maxFiles} images
          </span>
        </div>
      )}

      {/* Image Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {/* Existing Images */}
        {value.map((image, index) => (
          <div
            key={image.id}
            className="relative aspect-square border rounded-lg overflow-hidden group bg-gray-50"
          >
            <img
              src={image.thumbnail_url || image.url}
              alt={`Image ${index + 1}`}
              className="absolute inset-0 w-full h-full object-cover"
            />

            {/* Primary Badge */}
            {image.is_primary && (
              <div className="absolute top-1 left-1 px-1.5 py-0.5 bg-yellow-500 text-white text-xs rounded flex items-center gap-0.5">
                <Star className="h-3 w-3 fill-current" />
                Primary
              </div>
            )}

            {/* Hover Actions */}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
              {!image.is_primary && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSetPrimary(index);
                  }}
                  className="p-1.5 bg-yellow-500 text-white rounded-full hover:bg-yellow-600 transition-colors"
                  title="Set as primary"
                >
                  <Star className="h-4 w-4" />
                </button>
              )}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemove(index);
                }}
                className="p-1.5 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                title="Remove"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}

        {/* Preview Images (uploading) */}
        {previews.map((preview) => (
          <div
            key={preview.id}
            className="relative aspect-square border rounded-lg overflow-hidden bg-gray-50"
          >
            <img
              src={preview.url}
              alt="Uploading"
              className="absolute inset-0 w-full h-full object-cover opacity-50"
            />
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/30">
              <Loader2 className="h-6 w-6 text-white animate-spin" />
              <span className="mt-1 text-white text-xs">{progress}%</span>
            </div>
          </div>
        ))}

        {/* Add More Button */}
        {canAddMore && !isUploading && (
          <div
            onClick={handleClick}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className={cn(
              'aspect-square border-2 border-dashed rounded-lg transition-colors cursor-pointer',
              'border-gray-300 hover:border-blue-400 bg-gray-50 hover:bg-blue-50',
              'flex flex-col items-center justify-center',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
          >
            <div className="p-2 bg-gray-100 rounded-full mb-1">
              <Upload className="h-5 w-5 text-gray-400" />
            </div>
            <span className="text-xs text-gray-500">Add Image</span>
          </div>
        )}
      </div>

      {description && <p className="text-xs text-gray-500">{description}</p>}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/svg+xml"
        multiple
        onChange={handleInputChange}
        className="hidden"
        disabled={disabled || isUploading}
      />
    </div>
  );
}
