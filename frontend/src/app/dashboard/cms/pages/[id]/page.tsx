'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Save,
  Globe,
  Clock,
  History,
  Eye,
  RotateCcw,
  FileText,
  Settings,
  Search,
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
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
import RichTextEditor from '@/components/cms/rich-text-editor';
import { cmsApi, CMSPageCreate } from '@/lib/api/cms';
import { cn } from '@/lib/utils';

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/--+/g, '-')
    .trim();
}

export default function PageEditorPage() {
  const router = useRouter();
  const params = useParams();
  const queryClient = useQueryClient();
  const pageId = params.id as string;

  const [formData, setFormData] = useState<CMSPageCreate>({
    title: '',
    slug: '',
    content: '',
    excerpt: '',
    meta_title: '',
    meta_description: '',
    meta_keywords: '',
    og_image_url: '',
    canonical_url: '',
    status: 'DRAFT',
    template: 'default',
    show_in_footer: false,
    show_in_header: false,
    sort_order: 0,
  });

  const [revertVersion, setRevertVersion] = useState<number | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Fetch page data
  const { data: pageData, isLoading: pageLoading } = useQuery({
    queryKey: ['cms-page', pageId],
    queryFn: () => cmsApi.pages.get(pageId),
  });

  // Fetch versions
  const { data: versionsData } = useQuery({
    queryKey: ['cms-page-versions', pageId],
    queryFn: () => cmsApi.pages.getVersions(pageId),
  });

  // Initialize form data when page loads
  useEffect(() => {
    if (pageData?.data) {
      const page = pageData.data;
      setFormData({
        title: page.title,
        slug: page.slug,
        content: page.content || '',
        excerpt: page.excerpt || '',
        meta_title: page.meta_title || '',
        meta_description: page.meta_description || '',
        meta_keywords: page.meta_keywords || '',
        og_image_url: page.og_image_url || '',
        canonical_url: page.canonical_url || '',
        status: page.status,
        template: page.template,
        show_in_footer: page.show_in_footer,
        show_in_header: page.show_in_header,
        sort_order: page.sort_order,
      });
    }
  }, [pageData]);

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSPageCreate> }) =>
      cmsApi.pages.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-page', pageId] });
      queryClient.invalidateQueries({ queryKey: ['cms-page-versions', pageId] });
      queryClient.invalidateQueries({ queryKey: ['cms-pages'] });
      setHasUnsavedChanges(false);
      toast.success('Page updated successfully');
    },
    onError: () => {
      toast.error('Failed to update page');
    },
  });

  const publishMutation = useMutation({
    mutationFn: cmsApi.pages.publish,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-page', pageId] });
      queryClient.invalidateQueries({ queryKey: ['cms-pages'] });
      toast.success('Page published successfully');
    },
    onError: () => {
      toast.error('Failed to publish page');
    },
  });

  const revertMutation = useMutation({
    mutationFn: ({ id, version }: { id: string; version: number }) =>
      cmsApi.pages.revertToVersion(id, version),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-page', pageId] });
      queryClient.invalidateQueries({ queryKey: ['cms-page-versions', pageId] });
      setRevertVersion(null);
      toast.success('Page reverted successfully');
    },
    onError: () => {
      toast.error('Failed to revert page');
    },
  });

  const page = pageData?.data;
  const versions = versionsData?.data || [];

  const handleSave = () => {
    updateMutation.mutate({ id: pageId, data: formData });
  };

  const handleFieldChange = (field: keyof CMSPageCreate, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setHasUnsavedChanges(true);
  };

  const isSaving = updateMutation.isPending;

  if (pageLoading) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center py-8 text-muted-foreground">
          Loading page...
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push('/dashboard/cms/pages')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Edit Page</h1>
            {page && (
              <div className="flex items-center gap-2 mt-1">
                <Badge
                  variant="outline"
                  className={cn(
                    page.status === 'PUBLISHED' && 'bg-green-100 text-green-800',
                    page.status === 'DRAFT' && 'bg-amber-100 text-amber-800',
                    page.status === 'ARCHIVED' && 'bg-gray-100 text-gray-800'
                  )}
                >
                  {page.status === 'PUBLISHED' && <Globe className="h-3 w-3 mr-1" />}
                  {page.status === 'DRAFT' && <Clock className="h-3 w-3 mr-1" />}
                  {page.status}
                </Badge>
                {hasUnsavedChanges && (
                  <Badge variant="secondary">Unsaved changes</Badge>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {page?.status === 'DRAFT' && (
            <Button
              variant="outline"
              onClick={() => publishMutation.mutate(pageId)}
              disabled={publishMutation.isPending}
            >
              <Globe className="h-4 w-4 mr-2" />
              Publish
            </Button>
          )}
          {page?.status === 'PUBLISHED' && (
            <Button
              variant="outline"
              onClick={() => window.open(`/${page.slug}`, '_blank')}
            >
              <Eye className="h-4 w-4 mr-2" />
              View Page
            </Button>
          )}
          <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" size="icon">
                  <History className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent>
                <SheetHeader>
                  <SheetTitle>Version History</SheetTitle>
                  <SheetDescription>
                    View and restore previous versions of this page.
                  </SheetDescription>
                </SheetHeader>
                <div className="mt-6 space-y-3">
                  {versions.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No versions yet.</p>
                  ) : (
                    versions.map((version) => (
                      <div
                        key={version.id}
                        className="p-3 border rounded-lg space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <Badge variant="outline">v{version.version_number}</Badge>
                          <span className="text-xs text-muted-foreground">
                            {format(new Date(version.created_at), 'MMM d, yyyy h:mm a')}
                          </span>
                        </div>
                        <p className="text-sm font-medium">{version.title}</p>
                        {version.change_summary && (
                          <p className="text-xs text-muted-foreground">
                            {version.change_summary}
                          </p>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="w-full"
                          onClick={() => setRevertVersion(version.version_number)}
                        >
                          <RotateCcw className="h-3 w-3 mr-2" />
                          Restore this version
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </SheetContent>
            </Sheet>
          <Button onClick={handleSave} disabled={isSaving}>
            <Save className="h-4 w-4 mr-2" />
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main editor */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Content
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="title">Title *</Label>
                <Input
                  id="title"
                  value={formData.title}
                  onChange={(e) => handleFieldChange('title', e.target.value)}
                  placeholder="About Us"
                />
              </div>
              <div>
                <Label htmlFor="slug">Slug *</Label>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-muted-foreground">/</span>
                  <Input
                    id="slug"
                    value={formData.slug}
                    onChange={(e) => handleFieldChange('slug', slugify(e.target.value))}
                    placeholder="about-us"
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="excerpt">Excerpt</Label>
                <Textarea
                  id="excerpt"
                  value={formData.excerpt || ''}
                  onChange={(e) => handleFieldChange('excerpt', e.target.value)}
                  placeholder="A brief summary of the page..."
                  rows={2}
                />
              </div>
              <div>
                <Label>Content</Label>
                <div className="mt-2 border rounded-lg">
                  <RichTextEditor
                    content={formData.content || ''}
                    onChange={(content) => handleFieldChange('content', content)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Settings */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="status">Status</Label>
                <Select
                  value={formData.status}
                  onValueChange={(v) =>
                    handleFieldChange('status', v as 'DRAFT' | 'PUBLISHED' | 'ARCHIVED')
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DRAFT">Draft</SelectItem>
                    <SelectItem value="PUBLISHED">Published</SelectItem>
                    <SelectItem value="ARCHIVED">Archived</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="template">Template</Label>
                <Select
                  value={formData.template}
                  onValueChange={(v) =>
                    handleFieldChange('template', v as 'default' | 'full-width' | 'landing')
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default">Default</SelectItem>
                    <SelectItem value="full-width">Full Width</SelectItem>
                    <SelectItem value="landing">Landing Page</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="show_in_header">Show in Header</Label>
                <Switch
                  id="show_in_header"
                  checked={formData.show_in_header}
                  onCheckedChange={(v) => handleFieldChange('show_in_header', v)}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="show_in_footer">Show in Footer</Label>
                <Switch
                  id="show_in_footer"
                  checked={formData.show_in_footer}
                  onCheckedChange={(v) => handleFieldChange('show_in_footer', v)}
                />
              </div>
            </CardContent>
          </Card>

          {/* SEO */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Search className="h-4 w-4" />
                SEO
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="meta_title">Meta Title</Label>
                <Input
                  id="meta_title"
                  value={formData.meta_title || ''}
                  onChange={(e) => handleFieldChange('meta_title', e.target.value)}
                  placeholder="Page title for search engines"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {(formData.meta_title || '').length}/60 characters
                </p>
              </div>
              <div>
                <Label htmlFor="meta_description">Meta Description</Label>
                <Textarea
                  id="meta_description"
                  value={formData.meta_description || ''}
                  onChange={(e) => handleFieldChange('meta_description', e.target.value)}
                  placeholder="Brief description for search results"
                  rows={3}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {(formData.meta_description || '').length}/160 characters
                </p>
              </div>
              <div>
                <Label htmlFor="meta_keywords">Meta Keywords</Label>
                <Input
                  id="meta_keywords"
                  value={formData.meta_keywords || ''}
                  onChange={(e) => handleFieldChange('meta_keywords', e.target.value)}
                  placeholder="keyword1, keyword2, keyword3"
                />
              </div>
              <div>
                <Label htmlFor="og_image_url">OG Image URL</Label>
                <Input
                  id="og_image_url"
                  value={formData.og_image_url || ''}
                  onChange={(e) => handleFieldChange('og_image_url', e.target.value)}
                  placeholder="https://..."
                />
              </div>
              <div>
                <Label htmlFor="canonical_url">Canonical URL</Label>
                <Input
                  id="canonical_url"
                  value={formData.canonical_url || ''}
                  onChange={(e) => handleFieldChange('canonical_url', e.target.value)}
                  placeholder="https://..."
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Revert confirmation dialog */}
      <AlertDialog
        open={revertVersion !== null}
        onOpenChange={(open) => !open && setRevertVersion(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restore Version {revertVersion}?</AlertDialogTitle>
            <AlertDialogDescription>
              This will replace the current content with version {revertVersion}.
              A new version will be created to preserve the current state.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() =>
                revertVersion && revertMutation.mutate({ id: pageId, version: revertVersion })
              }
            >
              Restore
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
