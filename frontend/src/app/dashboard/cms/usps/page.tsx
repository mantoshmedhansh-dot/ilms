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
import { Plus, GripVertical, Pencil, Trash2, Eye, EyeOff } from 'lucide-react';
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
import { IconPicker, IconByName } from '@/components/cms/icon-picker';
import { cmsApi, CMSUsp, CMSUspCreate } from '@/lib/api/cms';
import { cn } from '@/lib/utils';

function SortableUspItem({
  usp,
  onEdit,
  onDelete,
  onToggleActive,
}: {
  usp: CMSUsp;
  onEdit: (usp: CMSUsp) => void;
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
  } = useSortable({ id: usp.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-4 p-4 bg-card border rounded-lg',
        isDragging && 'opacity-50 shadow-lg',
        !usp.is_active && 'opacity-60'
      )}
    >
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground"
      >
        <GripVertical className="h-5 w-5" />
      </button>

      <div className={cn('p-2 rounded-lg bg-primary/10', usp.icon_color)}>
        <IconByName name={usp.icon} className="h-6 w-6 text-primary" />
      </div>

      <div className="flex-1 min-w-0">
        <h3 className="font-medium">{usp.title}</h3>
        {usp.description && (
          <p className="text-sm text-muted-foreground truncate">
            {usp.description}
          </p>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onToggleActive(usp.id, !usp.is_active)}
          title={usp.is_active ? 'Deactivate' : 'Activate'}
        >
          {usp.is_active ? (
            <Eye className="h-4 w-4 text-green-600" />
          ) : (
            <EyeOff className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
        <Button variant="ghost" size="icon" onClick={() => onEdit(usp)}>
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
              <AlertDialogTitle>Delete USP</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete &quot;{usp.title}&quot;? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => onDelete(usp.id)}>
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}

interface UspFormProps {
  usp?: CMSUsp | null;
  onSubmit: (data: CMSUspCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

function UspForm({ usp, onSubmit, onCancel, isLoading }: UspFormProps) {
  const [formData, setFormData] = useState<CMSUspCreate>({
    title: usp?.title || '',
    description: usp?.description || '',
    icon: usp?.icon || 'star',
    icon_color: usp?.icon_color || '',
    link_url: usp?.link_url || '',
    link_text: usp?.link_text || '',
    is_active: usp?.is_active ?? true,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-4">
        <div>
          <Label htmlFor="title">Title *</Label>
          <Input
            id="title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            placeholder="Free Installation"
            required
          />
        </div>
        <div>
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            value={formData.description || ''}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Expert technicians at your doorstep"
            rows={2}
          />
        </div>
        <div>
          <Label>Icon *</Label>
          <IconPicker
            value={formData.icon}
            onChange={(icon) => setFormData({ ...formData, icon })}
          />
        </div>
        <div>
          <Label htmlFor="icon_color">Icon Color Class</Label>
          <Input
            id="icon_color"
            value={formData.icon_color || ''}
            onChange={(e) => setFormData({ ...formData, icon_color: e.target.value })}
            placeholder="text-blue-500"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="link_url">Link URL</Label>
            <Input
              id="link_url"
              value={formData.link_url || ''}
              onChange={(e) => setFormData({ ...formData, link_url: e.target.value })}
              placeholder="/about-us"
            />
          </div>
          <div>
            <Label htmlFor="link_text">Link Text</Label>
            <Input
              id="link_text"
              value={formData.link_text || ''}
              onChange={(e) => setFormData({ ...formData, link_text: e.target.value })}
              placeholder="Learn More"
            />
          </div>
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

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : usp ? 'Update' : 'Create'}
        </Button>
      </div>
    </form>
  );
}

export default function UspsPage() {
  const queryClient = useQueryClient();
  const [editingUsp, setEditingUsp] = useState<CMSUsp | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const { data, isLoading } = useQuery({
    queryKey: ['cms-usps'],
    queryFn: () => cmsApi.usps.list(),
  });

  const createMutation = useMutation({
    mutationFn: cmsApi.usps.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-usps'] });
      setIsDialogOpen(false);
      toast.success('USP created successfully');
    },
    onError: () => {
      toast.error('Failed to create USP');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSUspCreate> }) =>
      cmsApi.usps.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-usps'] });
      setIsDialogOpen(false);
      setEditingUsp(null);
      toast.success('USP updated successfully');
    },
    onError: () => {
      toast.error('Failed to update USP');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: cmsApi.usps.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-usps'] });
      toast.success('USP deleted successfully');
    },
    onError: () => {
      toast.error('Failed to delete USP');
    },
  });

  const reorderMutation = useMutation({
    mutationFn: cmsApi.usps.reorder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-usps'] });
    },
    onError: () => {
      toast.error('Failed to reorder USPs');
    },
  });

  const usps = data?.data?.items || [];

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = usps.findIndex((u) => u.id === active.id);
      const newIndex = usps.findIndex((u) => u.id === over.id);

      const newOrder = arrayMove(usps, oldIndex, newIndex);
      const ids = newOrder.map((u) => u.id);

      reorderMutation.mutate(ids);
    }
  };

  const handleSubmit = (formData: CMSUspCreate) => {
    if (editingUsp) {
      updateMutation.mutate({ id: editingUsp.id, data: formData });
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
          <CardTitle>USPs / Features</CardTitle>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => setEditingUsp(null)}>
                <Plus className="h-4 w-4 mr-2" />
                Add USP
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  {editingUsp ? 'Edit USP' : 'Create USP'}
                </DialogTitle>
              </DialogHeader>
              <UspForm
                usp={editingUsp}
                onSubmit={handleSubmit}
                onCancel={() => {
                  setIsDialogOpen(false);
                  setEditingUsp(null);
                }}
                isLoading={createMutation.isPending || updateMutation.isPending}
              />
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading USPs...
            </div>
          ) : usps.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No USPs yet. Add features like &quot;Free Installation&quot;, &quot;2 Year Warranty&quot;, etc.
            </div>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={usps.map((u) => u.id)}
                strategy={verticalListSortingStrategy}
              >
                <div className="space-y-3">
                  {usps.map((usp) => (
                    <SortableUspItem
                      key={usp.id}
                      usp={usp}
                      onEdit={(u) => {
                        setEditingUsp(u);
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
