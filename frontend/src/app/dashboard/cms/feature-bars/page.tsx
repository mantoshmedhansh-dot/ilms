'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Pencil,
  Trash2,
  GripVertical,
  Star,
  Truck,
  ShieldCheck,
  Headphones,
  RotateCcw,
  Award,
  Zap,
  Heart,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
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
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/common';
import { cmsApi, CMSFeatureBar, CMSFeatureBarCreate } from '@/lib/api/cms';

const defaultFeatureBarData: CMSFeatureBarCreate = {
  icon: 'Truck',
  title: '',
  subtitle: '',
  is_active: true,
};

// Available icons for selection
const availableIcons = [
  { name: 'Truck', icon: Truck, label: 'Free Shipping' },
  { name: 'ShieldCheck', icon: ShieldCheck, label: 'Secure Payment' },
  { name: 'Headphones', icon: Headphones, label: '24/7 Support' },
  { name: 'RotateCcw', icon: RotateCcw, label: 'Easy Returns' },
  { name: 'Award', icon: Award, label: 'Quality' },
  { name: 'Zap', icon: Zap, label: 'Fast' },
  { name: 'Heart', icon: Heart, label: 'Love' },
  { name: 'Star', icon: Star, label: 'Rating' },
];

const getIconComponent = (iconName: string) => {
  const iconObj = availableIcons.find((i) => i.name === iconName);
  if (iconObj) {
    const IconComponent = iconObj.icon;
    return <IconComponent className="h-5 w-5" />;
  }
  return <Star className="h-5 w-5" />;
};

export default function FeatureBarsPage() {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<CMSFeatureBar | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<CMSFeatureBarCreate>(defaultFeatureBarData);

  const { data, isLoading } = useQuery({
    queryKey: ['cms-feature-bars'],
    queryFn: () => cmsApi.featureBars.list(),
  });

  const createMutation = useMutation({
    mutationFn: cmsApi.featureBars.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-feature-bars'] });
      toast.success('Feature bar item created');
      handleCloseDialog();
    },
    onError: () => toast.error('Failed to create feature bar item'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSFeatureBarCreate> }) =>
      cmsApi.featureBars.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-feature-bars'] });
      toast.success('Feature bar item updated');
      handleCloseDialog();
    },
    onError: () => toast.error('Failed to update feature bar item'),
  });

  const deleteMutation = useMutation({
    mutationFn: cmsApi.featureBars.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-feature-bars'] });
      toast.success('Feature bar item deleted');
      setIsDeleteOpen(false);
      setDeletingId(null);
    },
    onError: () => toast.error('Failed to delete feature bar item'),
  });

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setEditingItem(null);
    setFormData(defaultFeatureBarData);
  };

  const handleEdit = (item: CMSFeatureBar) => {
    setEditingItem(item);
    setFormData({
      icon: item.icon,
      title: item.title,
      subtitle: item.subtitle || '',
      is_active: item.is_active,
    });
    setIsDialogOpen(true);
  };

  const handleSave = () => {
    if (!formData.title) {
      toast.error('Title is required');
      return;
    }

    if (editingItem) {
      updateMutation.mutate({ id: editingItem.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleDelete = (id: string) => {
    setDeletingId(id);
    setIsDeleteOpen(true);
  };

  const handleToggleActive = (item: CMSFeatureBar) => {
    updateMutation.mutate({
      id: item.id,
      data: { is_active: !item.is_active },
    });
  };

  const featureBars = data?.data?.items || [];
  const sortedFeatureBars = [...featureBars].sort((a, b) => a.sort_order - b.sort_order);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Feature Bars"
        description="Manage the feature bar displayed at the bottom of the footer (Free Shipping, Secure Payment, etc.)"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Feature
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Star className="h-5 w-5" />
            Feature Bar Items
          </CardTitle>
          <CardDescription>
            These items appear in the feature bar at the bottom of the footer
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : sortedFeatureBars.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Star className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No feature bar items configured</p>
              <p className="text-sm">Add items to highlight key features of your store</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sortedFeatureBars.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                    <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary/10 text-primary">
                      {getIconComponent(item.icon)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{item.title}</span>
                        {!item.is_active && (
                          <Badge variant="outline" className="text-xs">
                            Inactive
                          </Badge>
                        )}
                      </div>
                      {item.subtitle && (
                        <span className="text-sm text-muted-foreground">{item.subtitle}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={item.is_active}
                      onCheckedChange={() => handleToggleActive(item)}
                    />
                    <Button variant="ghost" size="icon" onClick={() => handleEdit(item)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(item.id)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Preview Card */}
      {sortedFeatureBars.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Preview</CardTitle>
            <CardDescription>How it will look on the storefront</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-muted rounded-lg p-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {sortedFeatureBars
                  .filter((item) => item.is_active)
                  .map((item) => (
                    <div key={item.id} className="flex items-center gap-3">
                      <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary/10 text-primary">
                        {getIconComponent(item.icon)}
                      </div>
                      <div>
                        <p className="font-medium text-sm">{item.title}</p>
                        {item.subtitle && (
                          <p className="text-xs text-muted-foreground">{item.subtitle}</p>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleCloseDialog()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingItem ? 'Edit Feature Bar Item' : 'Add Feature Bar Item'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Icon</Label>
              <div className="grid grid-cols-4 gap-2">
                {availableIcons.map((iconOption) => {
                  const IconComponent = iconOption.icon;
                  return (
                    <button
                      key={iconOption.name}
                      type="button"
                      onClick={() => setFormData({ ...formData, icon: iconOption.name })}
                      className={`p-3 border rounded-lg flex flex-col items-center gap-1 hover:bg-muted/50 transition-colors ${
                        formData.icon === iconOption.name
                          ? 'border-primary bg-primary/5'
                          : 'border-border'
                      }`}
                    >
                      <IconComponent className="h-5 w-5" />
                      <span className="text-xs">{iconOption.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="title">Title *</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="e.g., Free Shipping"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="subtitle">Subtitle (optional)</Label>
              <Input
                id="subtitle"
                value={formData.subtitle || ''}
                onChange={(e) => setFormData({ ...formData, subtitle: e.target.value })}
                placeholder="e.g., On orders over Rs.500"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="is_active">Active</Label>
                <p className="text-xs text-muted-foreground">Show this item in the feature bar</p>
              </div>
              <Switch
                id="is_active"
                checked={formData.is_active}
                onCheckedChange={(v) => setFormData({ ...formData, is_active: v })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleCloseDialog}>
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending ? 'Saving...' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Feature Bar Item</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this item? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingId && deleteMutation.mutate(deletingId)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
