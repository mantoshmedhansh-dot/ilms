'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Trash2,
  Edit,
  Eye,
  EyeOff,
  Star,
  StarOff,
  GripVertical,
  Search,
  Video,
  Youtube,
  Clock,
  ExternalLink,
  Play,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
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
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { cmsApi, CMSVideoGuide, CMSVideoGuideCreate } from '@/lib/api/cms';
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

const VIDEO_CATEGORIES = [
  { value: 'INSTALLATION', label: 'Installation' },
  { value: 'MAINTENANCE', label: 'Maintenance' },
  { value: 'TROUBLESHOOTING', label: 'Troubleshooting' },
  { value: 'PRODUCT_TOUR', label: 'Product Tour' },
  { value: 'HOW_TO', label: 'How To' },
  { value: 'TIPS', label: 'Tips & Tricks' },
];

const VIDEO_TYPES = [
  { value: 'YOUTUBE', label: 'YouTube' },
  { value: 'VIMEO', label: 'Vimeo' },
  { value: 'DIRECT', label: 'Direct URL' },
];

// Extract YouTube ID from URL
function extractYouTubeId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
    /^([a-zA-Z0-9_-]{11})$/,
  ];
  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }
  return null;
}

// Generate YouTube thumbnail URL
function getYouTubeThumbnail(videoId: string): string {
  return `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;
}

// Format duration
function formatDuration(seconds?: number): string {
  if (!seconds) return '--:--';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Generate slug from title
function generateSlug(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim();
}

// Sortable Row Component
function SortableGuideRow({
  guide,
  onEdit,
  onDelete,
  onToggleActive,
  onToggleFeatured,
}: {
  guide: CMSVideoGuide;
  onEdit: (guide: CMSVideoGuide) => void;
  onDelete: (guide: CMSVideoGuide) => void;
  onToggleActive: (guide: CMSVideoGuide) => void;
  onToggleFeatured: (guide: CMSVideoGuide) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: guide.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const categoryLabel = VIDEO_CATEGORIES.find(c => c.value === guide.category)?.label || guide.category;

  return (
    <TableRow ref={setNodeRef} style={style} className={isDragging ? 'bg-muted' : ''}>
      <TableCell>
        <button
          className="cursor-grab active:cursor-grabbing p-1 hover:bg-muted rounded"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-4 w-4 text-muted-foreground" />
        </button>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-3">
          <div className="relative w-24 h-14 rounded overflow-hidden bg-muted flex-shrink-0">
            {guide.thumbnail_url ? (
              <img
                src={guide.thumbnail_url}
                alt={guide.title}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Video className="h-6 w-6 text-muted-foreground" />
              </div>
            )}
            {guide.video_type === 'YOUTUBE' && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                <Play className="h-6 w-6 text-white" />
              </div>
            )}
          </div>
          <div className="min-w-0">
            <p className="font-medium truncate max-w-[300px]">{guide.title}</p>
            <p className="text-sm text-muted-foreground truncate max-w-[300px]">
              {guide.slug}
            </p>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant="outline">{categoryLabel}</Badge>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Clock className="h-4 w-4" />
          {formatDuration(guide.duration_seconds)}
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <Eye className="h-4 w-4" />
          {guide.view_count.toLocaleString()}
        </div>
      </TableCell>
      <TableCell>
        <Switch
          checked={guide.is_featured}
          onCheckedChange={() => onToggleFeatured(guide)}
        />
      </TableCell>
      <TableCell>
        <Switch
          checked={guide.is_active}
          onCheckedChange={() => onToggleActive(guide)}
        />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onEdit(guide)}
          >
            <Edit className="h-4 w-4" />
          </Button>
          {guide.video_url && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => window.open(guide.video_url, '_blank')}
            >
              <ExternalLink className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onDelete(guide)}
          >
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

export default function VideoGuidesPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingGuide, setEditingGuide] = useState<CMSVideoGuide | null>(null);
  const [deleteGuide, setDeleteGuide] = useState<CMSVideoGuide | null>(null);

  // Form state
  const [formData, setFormData] = useState<CMSVideoGuideCreate>({
    title: '',
    slug: '',
    description: '',
    thumbnail_url: '',
    video_url: '',
    video_type: 'YOUTUBE',
    video_id: '',
    duration_seconds: undefined,
    category: 'HOW_TO',
    tags: [],
    sort_order: 0,
    is_featured: false,
    is_active: true,
  });

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Fetch guides
  const { data: guidesData, isLoading } = useQuery({
    queryKey: ['video-guides', categoryFilter, searchQuery],
    queryFn: async () => {
      const params: Record<string, string | number | boolean | undefined> = { limit: 100 };
      if (categoryFilter) params.category = categoryFilter;
      if (searchQuery) params.search = searchQuery;
      const response = await cmsApi.videoGuides.list(params);
      return response.data;
    },
  });

  const guides = guidesData?.items || [];

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: CMSVideoGuideCreate) => cmsApi.videoGuides.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video-guides'] });
      toast.success('Video guide created successfully');
      closeForm();
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to create video guide');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSVideoGuideCreate> }) =>
      cmsApi.videoGuides.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video-guides'] });
      toast.success('Video guide updated successfully');
      closeForm();
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to update video guide');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => cmsApi.videoGuides.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video-guides'] });
      toast.success('Video guide deleted successfully');
      setDeleteGuide(null);
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to delete video guide');
    },
  });

  // Reorder mutation
  const reorderMutation = useMutation({
    mutationFn: (ids: string[]) => cmsApi.videoGuides.reorder(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video-guides'] });
      toast.success('Order updated');
    },
    onError: () => {
      toast.error('Failed to reorder');
    },
  });

  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = guides.findIndex((g) => g.id === active.id);
      const newIndex = guides.findIndex((g) => g.id === over.id);

      const newOrder = arrayMove(guides, oldIndex, newIndex);
      const ids = newOrder.map((g) => g.id);
      reorderMutation.mutate(ids);
    }
  };

  // Auto-fill fields when video URL changes
  useEffect(() => {
    if (formData.video_type === 'YOUTUBE' && formData.video_url) {
      const videoId = extractYouTubeId(formData.video_url);
      if (videoId) {
        setFormData(prev => ({
          ...prev,
          video_id: videoId,
          thumbnail_url: prev.thumbnail_url || getYouTubeThumbnail(videoId),
        }));
      }
    }
  }, [formData.video_url, formData.video_type]);

  // Auto-generate slug from title
  useEffect(() => {
    if (formData.title && !editingGuide) {
      setFormData(prev => ({
        ...prev,
        slug: generateSlug(prev.title),
      }));
    }
  }, [formData.title, editingGuide]);

  const openCreateForm = () => {
    setEditingGuide(null);
    setFormData({
      title: '',
      slug: '',
      description: '',
      thumbnail_url: '',
      video_url: '',
      video_type: 'YOUTUBE',
      video_id: '',
      duration_seconds: undefined,
      category: 'HOW_TO',
      tags: [],
      sort_order: guides.length,
      is_featured: false,
      is_active: true,
    });
    setIsFormOpen(true);
  };

  const openEditForm = (guide: CMSVideoGuide) => {
    setEditingGuide(guide);
    setFormData({
      title: guide.title,
      slug: guide.slug,
      description: guide.description || '',
      thumbnail_url: guide.thumbnail_url,
      video_url: guide.video_url,
      video_type: guide.video_type || 'YOUTUBE',
      video_id: guide.video_id || '',
      duration_seconds: guide.duration_seconds,
      category: guide.category,
      tags: guide.tags || [],
      sort_order: guide.sort_order,
      is_featured: guide.is_featured,
      is_active: guide.is_active,
    });
    setIsFormOpen(true);
  };

  const closeForm = () => {
    setIsFormOpen(false);
    setEditingGuide(null);
  };

  const handleSubmit = () => {
    if (!formData.title || !formData.slug || !formData.video_url || !formData.thumbnail_url) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (editingGuide) {
      updateMutation.mutate({ id: editingGuide.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleToggleActive = (guide: CMSVideoGuide) => {
    updateMutation.mutate({
      id: guide.id,
      data: { is_active: !guide.is_active },
    });
  };

  const handleToggleFeatured = (guide: CMSVideoGuide) => {
    updateMutation.mutate({
      id: guide.id,
      data: { is_featured: !guide.is_featured },
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Video Guides</h1>
          <p className="text-muted-foreground">
            Manage video content for the storefront guides page
          </p>
        </div>
        <Button onClick={openCreateForm}>
          <Plus className="h-4 w-4 mr-2" />
          Add Video
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search videos..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Categories</SelectItem>
                {VIDEO_CATEGORIES.map((cat) => (
                  <SelectItem key={cat.value} value={cat.value}>
                    {cat.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Videos Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Video className="h-5 w-5" />
            Videos ({guides.length})
          </CardTitle>
          <CardDescription>
            Drag and drop to reorder videos. Featured videos appear first on the storefront.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading videos...
            </div>
          ) : guides.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No videos found. Add your first video guide.
            </div>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]"></TableHead>
                    <TableHead>Video</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Views</TableHead>
                    <TableHead>Featured</TableHead>
                    <TableHead>Active</TableHead>
                    <TableHead className="w-[120px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <SortableContext
                    items={guides.map((g) => g.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    {guides.map((guide) => (
                      <SortableGuideRow
                        key={guide.id}
                        guide={guide}
                        onEdit={openEditForm}
                        onDelete={setDeleteGuide}
                        onToggleActive={handleToggleActive}
                        onToggleFeatured={handleToggleFeatured}
                      />
                    ))}
                  </SortableContext>
                </TableBody>
              </Table>
            </DndContext>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingGuide ? 'Edit Video Guide' : 'Add Video Guide'}
            </DialogTitle>
            <DialogDescription>
              {editingGuide
                ? 'Update the video guide details'
                : 'Add a new video guide to the storefront'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="title">Title *</Label>
                <Input
                  id="title"
                  value={formData.title}
                  onChange={(e) =>
                    setFormData({ ...formData, title: e.target.value })
                  }
                  placeholder="RO Water Purifier Installation Guide"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="slug">Slug *</Label>
                <Input
                  id="slug"
                  value={formData.slug}
                  onChange={(e) =>
                    setFormData({ ...formData, slug: e.target.value })
                  }
                  placeholder="ro-water-purifier-installation"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="Detailed description of the video content..."
                rows={3}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="video_type">Video Type</Label>
                <Select
                  value={formData.video_type}
                  onValueChange={(value) =>
                    setFormData({ ...formData, video_type: value as 'YOUTUBE' | 'VIMEO' | 'DIRECT' })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {VIDEO_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="category">Category</Label>
                <Select
                  value={formData.category}
                  onValueChange={(value) =>
                    setFormData({ ...formData, category: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {VIDEO_CATEGORIES.map((cat) => (
                      <SelectItem key={cat.value} value={cat.value}>
                        {cat.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="video_url">Video URL *</Label>
              <Input
                id="video_url"
                value={formData.video_url}
                onChange={(e) =>
                  setFormData({ ...formData, video_url: e.target.value })
                }
                placeholder="https://www.youtube.com/watch?v=..."
              />
              {formData.video_type === 'YOUTUBE' && formData.video_id && (
                <p className="text-sm text-muted-foreground">
                  YouTube ID: {formData.video_id}
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="thumbnail_url">Thumbnail URL *</Label>
                <Input
                  id="thumbnail_url"
                  value={formData.thumbnail_url}
                  onChange={(e) =>
                    setFormData({ ...formData, thumbnail_url: e.target.value })
                  }
                  placeholder="https://..."
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="duration">Duration (seconds)</Label>
                <Input
                  id="duration"
                  type="number"
                  value={formData.duration_seconds || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      duration_seconds: e.target.value ? parseInt(e.target.value) : undefined,
                    })
                  }
                  placeholder="e.g., 720 for 12 minutes"
                />
              </div>
            </div>

            {/* Thumbnail Preview */}
            {formData.thumbnail_url && (
              <div className="space-y-2">
                <Label>Thumbnail Preview</Label>
                <div className="relative w-full max-w-xs aspect-video rounded overflow-hidden bg-muted">
                  <img
                    src={formData.thumbnail_url}
                    alt="Thumbnail preview"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                </div>
              </div>
            )}

            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Switch
                  id="is_featured"
                  checked={formData.is_featured}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_featured: checked })
                  }
                />
                <Label htmlFor="is_featured">Featured</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  id="is_active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_active: checked })
                  }
                />
                <Label htmlFor="is_active">Active</Label>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeForm}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending
                ? 'Saving...'
                : editingGuide
                ? 'Update'
                : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteGuide} onOpenChange={() => setDeleteGuide(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Video Guide</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deleteGuide?.title}"? This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteGuide && deleteMutation.mutate(deleteGuide.id)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
