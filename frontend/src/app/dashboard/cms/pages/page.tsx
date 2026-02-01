'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Pencil,
  Trash2,
  Eye,
  FileText,
  Globe,
  Clock,
  Archive,
  MoreVertical,
  ExternalLink,
  Copy,
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { cmsApi, CMSPageBrief } from '@/lib/api/cms';
import { cn } from '@/lib/utils';

const statusConfig: Record<string, { icon: typeof Eye; color: string; label: string }> = {
  PUBLISHED: {
    icon: Globe,
    color: 'bg-green-100 text-green-800',
    label: 'Published',
  },
  DRAFT: {
    icon: Clock,
    color: 'bg-amber-100 text-amber-800',
    label: 'Draft',
  },
  ARCHIVED: {
    icon: Archive,
    color: 'bg-gray-100 text-gray-800',
    label: 'Archived',
  },
};

export default function PagesListPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [deletePageId, setDeletePageId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['cms-pages'],
    queryFn: () => cmsApi.pages.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: cmsApi.pages.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-pages'] });
      setDeletePageId(null);
      toast.success('Page deleted successfully');
    },
    onError: () => {
      toast.error('Failed to delete page');
    },
  });

  const publishMutation = useMutation({
    mutationFn: cmsApi.pages.publish,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-pages'] });
      toast.success('Page published successfully');
    },
    onError: () => {
      toast.error('Failed to publish page');
    },
  });

  const pages = data?.data?.items || [];

  const handleCopySlug = (slug: string) => {
    navigator.clipboard.writeText(`/${slug}`);
    toast.success('Slug copied to clipboard');
  };

  const publishedCount = pages.filter((p) => p.status === 'PUBLISHED').length;
  const draftCount = pages.filter((p) => p.status === 'DRAFT').length;

  return (
    <div className="container mx-auto py-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Static Pages</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {pages.length} total | {publishedCount} published | {draftCount} drafts
            </p>
          </div>
          <Button onClick={() => router.push('/dashboard/cms/pages/new')}>
            <Plus className="h-4 w-4 mr-2" />
            Create Page
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading pages...
            </div>
          ) : pages.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No pages yet.</p>
              <p className="text-sm">Create static pages like About Us, Privacy Policy, etc.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Slug</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Published</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead className="w-[70px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pages.map((page) => {
                  const status = statusConfig[page.status] || statusConfig.DRAFT;
                  const StatusIcon = status.icon;
                  return (
                    <TableRow key={page.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          {page.title}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            /{page.slug}
                          </code>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => handleCopySlug(page.slug)}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={cn('gap-1', status.color)}
                        >
                          <StatusIcon className="h-3 w-3" />
                          {status.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {page.published_at
                          ? format(new Date(page.published_at), 'MMM d, yyyy')
                          : '-'}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {format(new Date(page.updated_at), 'MMM d, yyyy')}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() =>
                                router.push(`/dashboard/cms/pages/${page.id}`)
                              }
                            >
                              <Pencil className="h-4 w-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            {page.status === 'PUBLISHED' && (
                              <DropdownMenuItem
                                onClick={() =>
                                  window.open(`/${page.slug}`, '_blank')
                                }
                              >
                                <ExternalLink className="h-4 w-4 mr-2" />
                                View Page
                              </DropdownMenuItem>
                            )}
                            {page.status === 'DRAFT' && (
                              <DropdownMenuItem
                                onClick={() => publishMutation.mutate(page.id)}
                              >
                                <Globe className="h-4 w-4 mr-2" />
                                Publish
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => setDeletePageId(page.id)}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Delete confirmation dialog */}
      <AlertDialog
        open={!!deletePageId}
        onOpenChange={(open) => !open && setDeletePageId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Page</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this page? This action cannot be undone
              and all version history will be lost.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletePageId && deleteMutation.mutate(deletePageId)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
