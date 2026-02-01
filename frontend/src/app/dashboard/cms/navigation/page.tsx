'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Pencil,
  Trash2,
  GripVertical,
  ExternalLink,
  Menu,
  Link as LinkIcon,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/common';
import { cmsApi, CMSMenuItem, CMSMenuItemCreate } from '@/lib/api/cms';

type MenuLocation = 'header' | 'footer_quick' | 'footer_service';

const defaultMenuItemData: CMSMenuItemCreate = {
  menu_location: 'header',
  title: '',
  url: '',
  icon: '',
  target: '_self',
  is_active: true,
  show_on_mobile: true,
};

const locationLabels: Record<MenuLocation, string> = {
  header: 'Header Navigation',
  footer_quick: 'Footer - Quick Links',
  footer_service: 'Footer - Customer Service',
};

const locationDescriptions: Record<MenuLocation, string> = {
  header: 'Main navigation links shown in the header (All Categories, Bestsellers, etc.)',
  footer_quick: 'Quick access links in the footer left column',
  footer_service: 'Customer service links in the footer right column',
};

export default function NavigationManagerPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<MenuLocation>('header');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<CMSMenuItem | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<CMSMenuItemCreate>(defaultMenuItemData);

  const { data, isLoading } = useQuery({
    queryKey: ['cms-menu-items'],
    queryFn: () => cmsApi.menuItems.list(),
  });

  const createMutation = useMutation({
    mutationFn: cmsApi.menuItems.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-menu-items'] });
      toast.success('Menu item created');
      handleCloseDialog();
    },
    onError: () => toast.error('Failed to create menu item'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSMenuItemCreate> }) =>
      cmsApi.menuItems.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-menu-items'] });
      toast.success('Menu item updated');
      handleCloseDialog();
    },
    onError: () => toast.error('Failed to update menu item'),
  });

  const deleteMutation = useMutation({
    mutationFn: cmsApi.menuItems.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-menu-items'] });
      toast.success('Menu item deleted');
      setIsDeleteOpen(false);
      setDeletingId(null);
    },
    onError: () => toast.error('Failed to delete menu item'),
  });

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setEditingItem(null);
    setFormData(defaultMenuItemData);
  };

  const handleAdd = (location: MenuLocation) => {
    setFormData({ ...defaultMenuItemData, menu_location: location });
    setIsDialogOpen(true);
  };

  const handleEdit = (item: CMSMenuItem) => {
    setEditingItem(item);
    setFormData({
      menu_location: item.menu_location,
      title: item.title,
      url: item.url,
      icon: item.icon || '',
      target: item.target,
      is_active: item.is_active,
      show_on_mobile: item.show_on_mobile,
      css_class: item.css_class || '',
    });
    setIsDialogOpen(true);
  };

  const handleSave = () => {
    if (!formData.title || !formData.url) {
      toast.error('Title and URL are required');
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

  const handleToggleActive = (item: CMSMenuItem) => {
    updateMutation.mutate({
      id: item.id,
      data: { is_active: !item.is_active },
    });
  };

  const menuItems = data?.data?.items || [];

  const groupedMenuItems = menuItems.reduce(
    (acc: Record<MenuLocation, CMSMenuItem[]>, item) => {
      const location = item.menu_location as MenuLocation;
      if (!acc[location]) acc[location] = [];
      acc[location].push(item);
      return acc;
    },
    { header: [], footer_quick: [], footer_service: [] }
  );

  // Sort by sort_order
  Object.keys(groupedMenuItems).forEach((loc) => {
    groupedMenuItems[loc as MenuLocation].sort((a, b) => a.sort_order - b.sort_order);
  });

  const renderMenuItemsList = (location: MenuLocation) => {
    const items = groupedMenuItems[location];

    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Menu className="h-5 w-5" />
                {locationLabels[location]}
              </CardTitle>
              <CardDescription>{locationDescriptions[location]}</CardDescription>
            </div>
            <Button size="sm" onClick={() => handleAdd(location)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Link
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <LinkIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No menu items configured</p>
              <p className="text-sm">Add links to display in this section</p>
            </div>
          ) : (
            <div className="space-y-2">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{item.title}</span>
                        {item.target === '_blank' && (
                          <ExternalLink className="h-3 w-3 text-muted-foreground" />
                        )}
                        {!item.is_active && (
                          <Badge variant="outline" className="text-xs">
                            Inactive
                          </Badge>
                        )}
                        {!item.show_on_mobile && (
                          <Badge variant="outline" className="text-xs">
                            Desktop only
                          </Badge>
                        )}
                      </div>
                      <span className="text-sm text-muted-foreground">{item.url}</span>
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
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Navigation Manager"
        description="Manage header and footer navigation links for the D2C storefront"
      />

      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Loading menu items...</div>
      ) : (
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as MenuLocation)}>
          <TabsList>
            <TabsTrigger value="header">Header</TabsTrigger>
            <TabsTrigger value="footer_quick">Quick Links</TabsTrigger>
            <TabsTrigger value="footer_service">Customer Service</TabsTrigger>
          </TabsList>

          <TabsContent value="header" className="mt-4">
            {renderMenuItemsList('header')}
          </TabsContent>

          <TabsContent value="footer_quick" className="mt-4">
            {renderMenuItemsList('footer_quick')}
          </TabsContent>

          <TabsContent value="footer_service" className="mt-4">
            {renderMenuItemsList('footer_service')}
          </TabsContent>
        </Tabs>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleCloseDialog()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingItem ? 'Edit Menu Item' : 'Add Menu Item'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="title">Title *</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Link title"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="url">URL *</Label>
              <Input
                id="url"
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                placeholder="/products or https://..."
              />
              <p className="text-xs text-muted-foreground">
                Use relative paths like /products or full URLs for external links
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="icon">Icon (optional)</Label>
              <Input
                id="icon"
                value={formData.icon || ''}
                onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                placeholder="lucide icon name (e.g., ShoppingCart)"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="target">Open In</Label>
              <Select
                value={formData.target}
                onValueChange={(v: '_self' | '_blank') => setFormData({ ...formData, target: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="_self">Same Window</SelectItem>
                  <SelectItem value="_blank">New Window</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="is_active">Active</Label>
                <p className="text-xs text-muted-foreground">Show this link on the storefront</p>
              </div>
              <Switch
                id="is_active"
                checked={formData.is_active}
                onCheckedChange={(v) => setFormData({ ...formData, is_active: v })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="show_on_mobile">Show on Mobile</Label>
                <p className="text-xs text-muted-foreground">Display this link on mobile devices</p>
              </div>
              <Switch
                id="show_on_mobile"
                checked={formData.show_on_mobile}
                onCheckedChange={(v) => setFormData({ ...formData, show_on_mobile: v })}
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
            <AlertDialogTitle>Delete Menu Item</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this menu item? This action cannot be undone.
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
