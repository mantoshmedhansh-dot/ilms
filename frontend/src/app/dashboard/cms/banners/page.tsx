'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Plus,
  GripVertical,
  Pencil,
  Trash2,
  Eye,
  EyeOff,
  Calendar,
  Image as ImageIcon,
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { cmsApi, CMSBanner, CMSBannerCreate } from '@/lib/api/cms';
import { cn } from '@/lib/utils';

function SortableBannerItem({
  banner,
  onEdit,
  onDelete,
  onToggleActive,
}: {
  banner: CMSBanner;
  onEdit: (banner: CMSBanner) => void;
  onDelete: (id: string) => void;
  onToggleActive: (id: string, active: boolean) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: banner.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const isScheduled = banner.starts_at || banner.ends_at;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-4 p-4 bg-card border rounded-lg',
        isDragging && 'opacity-50 shadow-lg',
        !banner.is_active && 'opacity-60'
      )}
    >
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground"
      >
        <GripVertical className="h-5 w-5" />
      </button>

      <div className="w-24 h-16 bg-muted rounded overflow-hidden flex-shrink-0">
        {banner.thumbnail_url || banner.image_url ? (
          <img
            src={banner.thumbnail_url || banner.image_url}
            alt={banner.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <ImageIcon className="h-6 w-6 text-muted-foreground" />
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="font-medium truncate">{banner.title}</h3>
          {isScheduled && (
            <Badge variant="outline" className="text-xs">
              <Calendar className="h-3 w-3 mr-1" />
              Scheduled
            </Badge>
          )}
        </div>
        {banner.subtitle && (
          <p className="text-sm text-muted-foreground truncate">
            {banner.subtitle}
          </p>
        )}
        {banner.cta_text && (
          <p className="text-xs text-muted-foreground mt-1">
            CTA: {banner.cta_text}
          </p>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onToggleActive(banner.id, !banner.is_active)}
          title={banner.is_active ? 'Deactivate' : 'Activate'}
        >
          {banner.is_active ? (
            <Eye className="h-4 w-4 text-green-600" />
          ) : (
            <EyeOff className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onEdit(banner)}
        >
          <Pencil className="h-4 w-4" />
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="icon">
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Banner</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete &quot;{banner.title}&quot;? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => onDelete(banner.id)}>
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}

interface BannerFormProps {
  banner?: CMSBanner | null;
  onSubmit: (data: CMSBannerCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

function BannerForm({ banner, onSubmit, onCancel, isLoading }: BannerFormProps) {
  const [formData, setFormData] = useState<CMSBannerCreate>({
    title: banner?.title || '',
    subtitle: banner?.subtitle || '',
    image_url: banner?.image_url || '',
    thumbnail_url: banner?.thumbnail_url || '',
    mobile_image_url: banner?.mobile_image_url || '',
    cta_text: banner?.cta_text || '',
    cta_link: banner?.cta_link || '',
    text_position: banner?.text_position || 'left',
    text_color: banner?.text_color || 'white',
    is_active: banner?.is_active ?? true,
    starts_at: banner?.starts_at || '',
    ends_at: banner?.ends_at || '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <Label htmlFor="title">Title *</Label>
          <Input
            id="title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            required
          />
        </div>
        <div className="col-span-2">
          <Label htmlFor="subtitle">Subtitle</Label>
          <Textarea
            id="subtitle"
            value={formData.subtitle || ''}
            onChange={(e) => setFormData({ ...formData, subtitle: e.target.value })}
            rows={2}
          />
        </div>
        <div className="col-span-2">
          <Label htmlFor="image_url">Image URL *</Label>
          <Input
            id="image_url"
            value={formData.image_url}
            onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
            placeholder="https://..."
            required
          />
        </div>
        <div>
          <Label htmlFor="mobile_image_url">Mobile Image URL</Label>
          <Input
            id="mobile_image_url"
            value={formData.mobile_image_url || ''}
            onChange={(e) => setFormData({ ...formData, mobile_image_url: e.target.value })}
            placeholder="https://..."
          />
        </div>
        <div>
          <Label htmlFor="thumbnail_url">Thumbnail URL</Label>
          <Input
            id="thumbnail_url"
            value={formData.thumbnail_url || ''}
            onChange={(e) => setFormData({ ...formData, thumbnail_url: e.target.value })}
            placeholder="https://..."
          />
        </div>
        <div>
          <Label htmlFor="cta_text">CTA Button Text</Label>
          <Input
            id="cta_text"
            value={formData.cta_text || ''}
            onChange={(e) => setFormData({ ...formData, cta_text: e.target.value })}
            placeholder="Shop Now"
          />
        </div>
        <div>
          <Label htmlFor="cta_link">CTA Button Link</Label>
          <Input
            id="cta_link"
            value={formData.cta_link || ''}
            onChange={(e) => setFormData({ ...formData, cta_link: e.target.value })}
            placeholder="/products"
          />
        </div>
        <div>
          <Label htmlFor="text_position">Text Position</Label>
          <Select
            value={formData.text_position}
            onValueChange={(v) => setFormData({ ...formData, text_position: v as 'left' | 'center' | 'right' })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="left">Left</SelectItem>
              <SelectItem value="center">Center</SelectItem>
              <SelectItem value="right">Right</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="text_color">Text Color</Label>
          <Select
            value={formData.text_color}
            onValueChange={(v) => setFormData({ ...formData, text_color: v as 'white' | 'dark' })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="white">White</SelectItem>
              <SelectItem value="dark">Dark</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="starts_at">Start Date</Label>
          <Input
            id="starts_at"
            type="datetime-local"
            value={formData.starts_at ? formData.starts_at.slice(0, 16) : ''}
            onChange={(e) => setFormData({ ...formData, starts_at: e.target.value ? new Date(e.target.value).toISOString() : '' })}
          />
        </div>
        <div>
          <Label htmlFor="ends_at">End Date</Label>
          <Input
            id="ends_at"
            type="datetime-local"
            value={formData.ends_at ? formData.ends_at.slice(0, 16) : ''}
            onChange={(e) => setFormData({ ...formData, ends_at: e.target.value ? new Date(e.target.value).toISOString() : '' })}
          />
        </div>
        <div className="col-span-2 flex items-center gap-2">
          <Switch
            id="is_active"
            checked={formData.is_active}
            onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
          />
          <Label htmlFor="is_active">Active</Label>
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : banner ? 'Update' : 'Create'}
        </Button>
      </div>
    </form>
  );
}

export default function BannersPage() {
  const queryClient = useQueryClient();
  const [editingBanner, setEditingBanner] = useState<CMSBanner | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const { data, isLoading } = useQuery({
    queryKey: ['cms-banners'],
    queryFn: () => cmsApi.banners.list(),
  });

  const createMutation = useMutation({
    mutationFn: cmsApi.banners.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-banners'] });
      setIsDialogOpen(false);
      toast.success('Banner created successfully');
    },
    onError: () => {
      toast.error('Failed to create banner');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSBannerCreate> }) =>
      cmsApi.banners.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-banners'] });
      setIsDialogOpen(false);
      setEditingBanner(null);
      toast.success('Banner updated successfully');
    },
    onError: () => {
      toast.error('Failed to update banner');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: cmsApi.banners.delete,
    // Optimistic update: immediately remove from UI before API confirms
    onMutate: async (deletedId: string) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['cms-banners'] });

      // Snapshot the previous value
      const previousBanners = queryClient.getQueryData(['cms-banners']);

      // Optimistically remove from cache
      queryClient.setQueryData(['cms-banners'], (old: any) => {
        if (!old?.data?.items) return old;
        return {
          ...old,
          data: {
            ...old.data,
            items: old.data.items.filter((b: CMSBanner) => b.id !== deletedId),
          },
        };
      });

      // Return context with previous value
      return { previousBanners };
    },
    onSuccess: () => {
      toast.success('Banner deleted successfully');
    },
    onError: (_err, _deletedId, context) => {
      // Rollback to previous value on error
      if (context?.previousBanners) {
        queryClient.setQueryData(['cms-banners'], context.previousBanners);
      }
      toast.error('Failed to delete banner');
    },
    onSettled: () => {
      // Always refetch after error or success to ensure sync
      queryClient.invalidateQueries({ queryKey: ['cms-banners'] });
    },
  });

  const reorderMutation = useMutation({
    mutationFn: cmsApi.banners.reorder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-banners'] });
    },
    onError: () => {
      toast.error('Failed to reorder banners');
    },
  });

  const banners = data?.data?.items || [];

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = banners.findIndex((b) => b.id === active.id);
      const newIndex = banners.findIndex((b) => b.id === over.id);

      const newOrder = arrayMove(banners, oldIndex, newIndex);
      const ids = newOrder.map((b) => b.id);

      reorderMutation.mutate(ids);
    }
  };

  const handleSubmit = (formData: CMSBannerCreate) => {
    if (editingBanner) {
      updateMutation.mutate({ id: editingBanner.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleToggleActive = (id: string, active: boolean) => {
    updateMutation.mutate({ id, data: { is_active: active } });
  };

  return (
    <div className="container mx-auto py-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Hero Banners</CardTitle>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => setEditingBanner(null)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Banner
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>
                  {editingBanner ? 'Edit Banner' : 'Create Banner'}
                </DialogTitle>
              </DialogHeader>
              <BannerForm
                banner={editingBanner}
                onSubmit={handleSubmit}
                onCancel={() => {
                  setIsDialogOpen(false);
                  setEditingBanner(null);
                }}
                isLoading={createMutation.isPending || updateMutation.isPending}
              />
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading banners...
            </div>
          ) : banners.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No banners yet. Create your first banner to get started.
            </div>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={banners.map((b) => b.id)}
                strategy={verticalListSortingStrategy}
              >
                <div className="space-y-3">
                  {banners.map((banner) => (
                    <SortableBannerItem
                      key={banner.id}
                      banner={banner}
                      onEdit={(b) => {
                        setEditingBanner(b);
                        setIsDialogOpen(true);
                      }}
                      onDelete={(id) => deleteMutation.mutate(id)}
                      onToggleActive={handleToggleActive}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
