'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Pencil,
  Trash2,
  Eye,
  EyeOff,
  Bell,
  Calendar,
  X,
  Info,
  AlertTriangle,
  Tag,
  CheckCircle,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { cmsApi, CMSAnnouncement, CMSAnnouncementCreate } from '@/lib/api/cms';
import { cn } from '@/lib/utils';

type AnnouncementType = 'INFO' | 'WARNING' | 'PROMO' | 'SUCCESS';

const typeConfig: Record<AnnouncementType, { icon: typeof Info; color: string; label: string }> = {
  INFO: {
    icon: Info,
    color: 'bg-blue-100 text-blue-800 border-blue-200',
    label: 'Information',
  },
  WARNING: {
    icon: AlertTriangle,
    color: 'bg-amber-100 text-amber-800 border-amber-200',
    label: 'Warning',
  },
  PROMO: {
    icon: Tag,
    color: 'bg-purple-100 text-purple-800 border-purple-200',
    label: 'Promotion',
  },
  SUCCESS: {
    icon: CheckCircle,
    color: 'bg-green-100 text-green-800 border-green-200',
    label: 'Success',
  },
};

function AnnouncementCard({
  announcement,
  onEdit,
  onDelete,
  onToggleActive,
}: {
  announcement: CMSAnnouncement;
  onEdit: (announcement: CMSAnnouncement) => void;
  onDelete: (id: string) => void;
  onToggleActive: (id: string, active: boolean) => void;
}) {
  const config = typeConfig[announcement.announcement_type];
  const Icon = config.icon;
  const isScheduled = announcement.starts_at || announcement.ends_at;

  return (
    <div
      className={cn(
        'p-4 bg-card border rounded-lg',
        !announcement.is_active && 'opacity-60'
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className={cn('p-2 rounded-lg', config.color)}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <Badge variant="outline" className={config.color}>
              {config.label}
            </Badge>
            {isScheduled && (
              <Badge variant="outline" className="text-xs">
                <Calendar className="h-3 w-3 mr-1" />
                Scheduled
              </Badge>
            )}
            {announcement.is_dismissible && (
              <Badge variant="outline" className="text-xs">
                <X className="h-3 w-3 mr-1" />
                Dismissible
              </Badge>
            )}
          </div>
          <p className="text-sm font-medium">{announcement.text}</p>
          {announcement.link_text && (
            <p className="text-xs text-muted-foreground mt-1">
              Link: {announcement.link_text} &rarr; {announcement.link_url}
            </p>
          )}
        </div>
      </div>

      {/* Schedule info */}
      {isScheduled && (
        <div className="mt-3 text-xs text-muted-foreground bg-muted px-3 py-2 rounded">
          {announcement.starts_at && (
            <span>
              Starts: {format(new Date(announcement.starts_at), 'MMM d, yyyy h:mm a')}
            </span>
          )}
          {announcement.starts_at && announcement.ends_at && <span className="mx-2">|</span>}
          {announcement.ends_at && (
            <span>
              Ends: {format(new Date(announcement.ends_at), 'MMM d, yyyy h:mm a')}
            </span>
          )}
        </div>
      )}

      {/* Custom colors preview */}
      {(announcement.background_color || announcement.text_color) && (
        <div
          className="mt-3 p-2 rounded text-sm text-center"
          style={{
            backgroundColor: announcement.background_color || undefined,
            color: announcement.text_color || undefined,
          }}
        >
          Preview with custom colors
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-1 mt-4 pt-3 border-t">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onToggleActive(announcement.id, !announcement.is_active)}
          title={announcement.is_active ? 'Deactivate' : 'Activate'}
        >
          {announcement.is_active ? (
            <Eye className="h-4 w-4 text-green-600" />
          ) : (
            <EyeOff className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onEdit(announcement)}
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
              <AlertDialogTitle>Delete Announcement</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete this announcement? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => onDelete(announcement.id)}>
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}

interface AnnouncementFormProps {
  announcement?: CMSAnnouncement | null;
  onSubmit: (data: CMSAnnouncementCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

function AnnouncementForm({ announcement, onSubmit, onCancel, isLoading }: AnnouncementFormProps) {
  const [formData, setFormData] = useState<CMSAnnouncementCreate>({
    text: announcement?.text || '',
    link_url: announcement?.link_url || '',
    link_text: announcement?.link_text || '',
    announcement_type: announcement?.announcement_type || 'INFO',
    background_color: announcement?.background_color || '',
    text_color: announcement?.text_color || '',
    starts_at: announcement?.starts_at || '',
    ends_at: announcement?.ends_at || '',
    is_dismissible: announcement?.is_dismissible ?? true,
    is_active: announcement?.is_active ?? true,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <Label htmlFor="text">Announcement Text *</Label>
          <Textarea
            id="text"
            value={formData.text}
            onChange={(e) => setFormData({ ...formData, text: e.target.value })}
            placeholder="Free shipping on all orders above Rs. 5000!"
            rows={2}
            required
          />
        </div>
        <div className="col-span-2">
          <Label htmlFor="announcement_type">Type</Label>
          <Select
            value={formData.announcement_type}
            onValueChange={(v) => setFormData({ ...formData, announcement_type: v as AnnouncementType })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(typeConfig).map(([key, config]) => {
                const Icon = config.icon;
                return (
                  <SelectItem key={key} value={key}>
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      {config.label}
                    </div>
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="link_url">Link URL</Label>
          <Input
            id="link_url"
            value={formData.link_url || ''}
            onChange={(e) => setFormData({ ...formData, link_url: e.target.value })}
            placeholder="/products"
          />
        </div>
        <div>
          <Label htmlFor="link_text">Link Text</Label>
          <Input
            id="link_text"
            value={formData.link_text || ''}
            onChange={(e) => setFormData({ ...formData, link_text: e.target.value })}
            placeholder="Shop Now"
          />
        </div>
        <div>
          <Label htmlFor="background_color">Background Color</Label>
          <div className="flex gap-2">
            <Input
              id="background_color"
              value={formData.background_color || ''}
              onChange={(e) => setFormData({ ...formData, background_color: e.target.value })}
              placeholder="#000000"
            />
            <Input
              type="color"
              value={formData.background_color || '#000000'}
              onChange={(e) => setFormData({ ...formData, background_color: e.target.value })}
              className="w-12 p-1 h-10"
            />
          </div>
        </div>
        <div>
          <Label htmlFor="text_color">Text Color</Label>
          <div className="flex gap-2">
            <Input
              id="text_color"
              value={formData.text_color || ''}
              onChange={(e) => setFormData({ ...formData, text_color: e.target.value })}
              placeholder="#ffffff"
            />
            <Input
              type="color"
              value={formData.text_color || '#ffffff'}
              onChange={(e) => setFormData({ ...formData, text_color: e.target.value })}
              className="w-12 p-1 h-10"
            />
          </div>
        </div>
        <div>
          <Label htmlFor="starts_at">Start Date</Label>
          <Input
            id="starts_at"
            type="datetime-local"
            value={formData.starts_at ? formData.starts_at.slice(0, 16) : ''}
            onChange={(e) =>
              setFormData({
                ...formData,
                starts_at: e.target.value ? new Date(e.target.value).toISOString() : '',
              })
            }
          />
        </div>
        <div>
          <Label htmlFor="ends_at">End Date</Label>
          <Input
            id="ends_at"
            type="datetime-local"
            value={formData.ends_at ? formData.ends_at.slice(0, 16) : ''}
            onChange={(e) =>
              setFormData({
                ...formData,
                ends_at: e.target.value ? new Date(e.target.value).toISOString() : '',
              })
            }
          />
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="is_dismissible"
            checked={formData.is_dismissible}
            onCheckedChange={(checked) => setFormData({ ...formData, is_dismissible: checked })}
          />
          <Label htmlFor="is_dismissible">Dismissible</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="is_active"
            checked={formData.is_active}
            onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
          />
          <Label htmlFor="is_active">Active</Label>
        </div>
      </div>

      {/* Preview */}
      {formData.text && (
        <div className="pt-4 border-t">
          <Label className="text-xs text-muted-foreground">Preview</Label>
          <div
            className="mt-2 p-3 rounded text-sm text-center"
            style={{
              backgroundColor: formData.background_color || '#1f2937',
              color: formData.text_color || '#ffffff',
            }}
          >
            {formData.text}
            {formData.link_text && (
              <span className="ml-2 underline">{formData.link_text}</span>
            )}
          </div>
        </div>
      )}

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : announcement ? 'Update' : 'Create'}
        </Button>
      </div>
    </form>
  );
}

export default function AnnouncementsPage() {
  const queryClient = useQueryClient();
  const [editingAnnouncement, setEditingAnnouncement] = useState<CMSAnnouncement | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['cms-announcements'],
    queryFn: () => cmsApi.announcements.list(),
  });

  const createMutation = useMutation({
    mutationFn: cmsApi.announcements.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-announcements'] });
      setIsDialogOpen(false);
      toast.success('Announcement created successfully');
    },
    onError: () => {
      toast.error('Failed to create announcement');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSAnnouncementCreate> }) =>
      cmsApi.announcements.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-announcements'] });
      setIsDialogOpen(false);
      setEditingAnnouncement(null);
      toast.success('Announcement updated successfully');
    },
    onError: () => {
      toast.error('Failed to update announcement');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: cmsApi.announcements.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-announcements'] });
      toast.success('Announcement deleted successfully');
    },
    onError: () => {
      toast.error('Failed to delete announcement');
    },
  });

  const announcements = data?.data?.items || [];

  const handleSubmit = (formData: CMSAnnouncementCreate) => {
    if (editingAnnouncement) {
      updateMutation.mutate({ id: editingAnnouncement.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleToggleActive = (id: string, active: boolean) => {
    updateMutation.mutate({ id, data: { is_active: active } });
  };

  const activeCount = announcements.filter((a) => a.is_active).length;

  return (
    <div className="container mx-auto py-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Announcement Bar</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {announcements.length} total | {activeCount} active
            </p>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => setEditingAnnouncement(null)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Announcement
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>
                  {editingAnnouncement ? 'Edit Announcement' : 'Create Announcement'}
                </DialogTitle>
              </DialogHeader>
              <AnnouncementForm
                announcement={editingAnnouncement}
                onSubmit={handleSubmit}
                onCancel={() => {
                  setIsDialogOpen(false);
                  setEditingAnnouncement(null);
                }}
                isLoading={createMutation.isPending || updateMutation.isPending}
              />
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading announcements...
            </div>
          ) : announcements.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No announcements yet.</p>
              <p className="text-sm">Create announcements for promotions, notices, or updates.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {announcements.map((announcement) => (
                <AnnouncementCard
                  key={announcement.id}
                  announcement={announcement}
                  onEdit={(a) => {
                    setEditingAnnouncement(a);
                    setIsDialogOpen(true);
                  }}
                  onDelete={(id) => deleteMutation.mutate(id)}
                  onToggleActive={handleToggleActive}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
