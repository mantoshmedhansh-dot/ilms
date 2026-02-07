'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Pencil,
  Trash2,
  Search,
  Globe,
  FileText,
  ExternalLink,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/common';
import { cmsApi, CMSSeo, CMSSeoCreate } from '@/lib/api/cms';

const defaultSeoData: CMSSeoCreate = {
  url_path: '',
  meta_title: '',
  meta_description: '',
  meta_keywords: '',
  og_title: '',
  og_description: '',
  og_image_url: '',
  og_type: 'website',
  canonical_url: '',
  robots_index: true,
  robots_follow: true,
};

export default function SeoSettingsPage() {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<CMSSeo | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<CMSSeoCreate>(defaultSeoData);

  const { data, isLoading } = useQuery({
    queryKey: ['cms-seo'],
    queryFn: () => cmsApi.seo.list(),
  });

  const createMutation = useMutation({
    mutationFn: cmsApi.seo.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-seo'] });
      toast.success('SEO settings created');
      handleCloseDialog();
    },
    onError: () => toast.error('Failed to create SEO settings'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSSeoCreate> }) =>
      cmsApi.seo.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-seo'] });
      toast.success('SEO settings updated');
      handleCloseDialog();
    },
    onError: () => toast.error('Failed to update SEO settings'),
  });

  const deleteMutation = useMutation({
    mutationFn: cmsApi.seo.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-seo'] });
      toast.success('SEO settings deleted');
      setIsDeleteOpen(false);
      setDeletingId(null);
    },
    onError: () => toast.error('Failed to delete SEO settings'),
  });

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setEditingItem(null);
    setFormData(defaultSeoData);
  };

  const handleEdit = (item: CMSSeo) => {
    setEditingItem(item);
    setFormData({
      url_path: item.url_path,
      meta_title: item.meta_title || '',
      meta_description: item.meta_description || '',
      meta_keywords: item.meta_keywords || '',
      og_title: item.og_title || '',
      og_description: item.og_description || '',
      og_image_url: item.og_image_url || '',
      og_type: item.og_type || 'website',
      canonical_url: item.canonical_url || '',
      robots_index: item.robots_index ?? true,
      robots_follow: item.robots_follow ?? true,
    });
    setIsDialogOpen(true);
  };

  const handleSave = () => {
    if (!formData.url_path) {
      toast.error('URL path is required');
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

  const seoItems = data?.data?.items || [];

  const commonPages = [
    { path: '/', label: 'Homepage' },
    { path: '/products', label: 'Products Page' },
    { path: '/cart', label: 'Cart Page' },
    { path: '/checkout', label: 'Checkout Page' },
    { path: '/about', label: 'About Us' },
    { path: '/contact', label: 'Contact Us' },
  ];

  const existingPaths = seoItems.map((item: CMSSeo) => item.url_path);
  const suggestedPages = commonPages.filter(p => !existingPaths.includes(p.path));

  return (
    <div className="space-y-6">
      <PageHeader
        title="SEO Settings"
        description="Manage meta tags, Open Graph, and search engine settings for your pages"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add SEO Settings
          </Button>
        }
      />

      {/* Create/Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={(open) => {
        if (!open) handleCloseDialog();
        else setIsDialogOpen(true);
      }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingItem ? 'Edit SEO Settings' : 'Add SEO Settings'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            {/* URL Path */}
            <div className="space-y-2">
              <Label htmlFor="url_path">URL Path *</Label>
              <Input
                id="url_path"
                value={formData.url_path}
                onChange={(e) => setFormData({ ...formData, url_path: e.target.value })}
                placeholder="/ or /products or /about"
              />
              <p className="text-xs text-muted-foreground">
                The URL path this SEO setting applies to (e.g., /, /products, /about)
              </p>
            </div>

            {/* Meta Tags */}
            <div className="space-y-4">
              <h4 className="font-medium flex items-center gap-2">
                <Search className="h-4 w-4" />
                Meta Tags
              </h4>
              <div className="space-y-2">
                <Label htmlFor="meta_title">Meta Title</Label>
                <Input
                  id="meta_title"
                  value={formData.meta_title}
                  onChange={(e) => setFormData({ ...formData, meta_title: e.target.value })}
                  placeholder="Page title for search engines"
                />
                <p className="text-xs text-muted-foreground">
                  {(formData.meta_title || '').length}/60 characters recommended
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="meta_description">Meta Description</Label>
                <Textarea
                  id="meta_description"
                  value={formData.meta_description}
                  onChange={(e) => setFormData({ ...formData, meta_description: e.target.value })}
                  placeholder="Brief description for search results"
                  rows={3}
                />
                <p className="text-xs text-muted-foreground">
                  {(formData.meta_description || '').length}/160 characters recommended
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="meta_keywords">Meta Keywords</Label>
                <Input
                  id="meta_keywords"
                  value={formData.meta_keywords}
                  onChange={(e) => setFormData({ ...formData, meta_keywords: e.target.value })}
                  placeholder="keyword1, keyword2, keyword3"
                />
              </div>
            </div>

            {/* Open Graph */}
            <div className="space-y-4">
              <h4 className="font-medium flex items-center gap-2">
                <Globe className="h-4 w-4" />
                Open Graph (Social Sharing)
              </h4>
              <div className="space-y-2">
                <Label htmlFor="og_title">OG Title</Label>
                <Input
                  id="og_title"
                  value={formData.og_title}
                  onChange={(e) => setFormData({ ...formData, og_title: e.target.value })}
                  placeholder="Title for social media shares"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="og_description">OG Description</Label>
                <Textarea
                  id="og_description"
                  value={formData.og_description}
                  onChange={(e) => setFormData({ ...formData, og_description: e.target.value })}
                  placeholder="Description for social media shares"
                  rows={2}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="og_image_url">OG Image URL</Label>
                <Input
                  id="og_image_url"
                  value={formData.og_image_url}
                  onChange={(e) => setFormData({ ...formData, og_image_url: e.target.value })}
                  placeholder="https://example.com/image.jpg"
                />
              </div>
            </div>

            {/* Advanced */}
            <div className="space-y-4">
              <h4 className="font-medium flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Advanced
              </h4>
              <div className="space-y-2">
                <Label htmlFor="canonical_url">Canonical URL</Label>
                <Input
                  id="canonical_url"
                  value={formData.canonical_url}
                  onChange={(e) => setFormData({ ...formData, canonical_url: e.target.value })}
                  placeholder="https://example.com/canonical-page"
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="robots_index">Allow Indexing</Label>
                  <p className="text-xs text-muted-foreground">Let search engines index this page</p>
                </div>
                <Switch
                  id="robots_index"
                  checked={formData.robots_index}
                  onCheckedChange={(v) => setFormData({ ...formData, robots_index: v })}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="robots_follow">Allow Following Links</Label>
                  <p className="text-xs text-muted-foreground">Let search engines follow links on this page</p>
                </div>
                <Switch
                  id="robots_follow"
                  checked={formData.robots_follow}
                  onCheckedChange={(v) => setFormData({ ...formData, robots_follow: v })}
                />
              </div>
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
              {(createMutation.isPending || updateMutation.isPending) ? 'Saving...' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Quick Add Suggestions */}
      {suggestedPages.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Quick Add Common Pages</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {suggestedPages.map((page) => (
                <Button
                  key={page.path}
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setFormData({ ...defaultSeoData, url_path: page.path });
                    setIsDialogOpen(true);
                  }}
                >
                  <Plus className="h-3 w-3 mr-1" />
                  {page.label}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* SEO Settings List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Search className="h-5 w-5" />
            Page SEO Settings
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : seoItems.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No SEO settings configured yet</p>
              <p className="text-sm">Add SEO settings for your pages to improve search visibility</p>
            </div>
          ) : (
            <div className="space-y-4">
              {seoItems.map((item: CMSSeo) => (
                <div
                  key={item.id}
                  className="flex items-start justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="space-y-1 flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <code className="text-sm font-mono bg-muted px-2 py-0.5 rounded">
                        {item.url_path}
                      </code>
                      <div className="flex gap-1">
                        {item.robots_index ? (
                          <Badge variant="secondary" className="text-xs">Index</Badge>
                        ) : (
                          <Badge variant="outline" className="text-xs">No Index</Badge>
                        )}
                        {item.robots_follow ? (
                          <Badge variant="secondary" className="text-xs">Follow</Badge>
                        ) : (
                          <Badge variant="outline" className="text-xs">No Follow</Badge>
                        )}
                      </div>
                    </div>
                    {item.meta_title && (
                      <p className="font-medium text-sm truncate">{item.meta_title}</p>
                    )}
                    {item.meta_description && (
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {item.meta_description}
                      </p>
                    )}
                    {item.canonical_url && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <ExternalLink className="h-3 w-3" />
                        {item.canonical_url}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 ml-4">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleEdit(item)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(item.id)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation */}
      <AlertDialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete SEO Settings</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete these SEO settings? This action cannot be undone.
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
