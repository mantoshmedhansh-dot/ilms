'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MoreHorizontal, Plus, Pencil, Trash2, FolderTree, ChevronRight, ChevronDown, Loader2, Folder, FolderOpen } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Card, CardContent } from '@/components/ui/card';
import { PageHeader, StatusBadge } from '@/components/common';
import { Skeleton } from '@/components/ui/skeleton';
import { categoriesApi } from '@/lib/api';
import { Category } from '@/types';
import { cn } from '@/lib/utils';

interface CategoryFormData {
  name: string;
  slug: string;
  description: string;
  parent_id: string;
  sort_order: number;
  is_active: boolean;
}

const defaultFormData: CategoryFormData = {
  name: '',
  slug: '',
  description: '',
  parent_id: '',
  sort_order: 0,
  is_active: true,
};

interface CategoryTree {
  root: Category;
  children: Category[];
}

export default function CategoriesPage() {
  const queryClient = useQueryClient();
  const [expandedRoots, setExpandedRoots] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');

  // Create dialog state
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [createFormData, setCreateFormData] = useState<CategoryFormData>(defaultFormData);

  // Edit dialog state
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [editFormData, setEditFormData] = useState<CategoryFormData>(defaultFormData);

  // Delete dialog state
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [categoryToDelete, setCategoryToDelete] = useState<Category | null>(null);

  // Fetch all categories (increase size to get all)
  const { data, isLoading } = useQuery({
    queryKey: ['categories-all'],
    queryFn: () => categoriesApi.list({ page: 1, size: 100 }),
  });

  // Build category tree structure
  const categoryTree = useMemo(() => {
    if (!data?.items) return [];

    const categories = data.items as Category[];
    const rootCategories = categories.filter(c => !c.parent_id);
    const childCategories = categories.filter(c => c.parent_id);

    // Sort roots by sort_order, then by name
    const sortedRoots = [...rootCategories].sort((a, b) => {
      if ((a.sort_order ?? 0) !== (b.sort_order ?? 0)) {
        return (a.sort_order ?? 0) - (b.sort_order ?? 0);
      }
      return a.name.localeCompare(b.name);
    });

    return sortedRoots.map(root => ({
      root,
      children: childCategories
        .filter(c => c.parent_id === root.id)
        .sort((a, b) => {
          if ((a.sort_order ?? 0) !== (b.sort_order ?? 0)) {
            return (a.sort_order ?? 0) - (b.sort_order ?? 0);
          }
          return a.name.localeCompare(b.name);
        }),
    })) as CategoryTree[];
  }, [data]);

  // Filter categories based on search
  const filteredTree = useMemo(() => {
    if (!searchQuery.trim()) return categoryTree;

    const query = searchQuery.toLowerCase();
    return categoryTree
      .map(tree => ({
        root: tree.root,
        children: tree.children.filter(c =>
          c.name.toLowerCase().includes(query) ||
          c.slug.toLowerCase().includes(query)
        ),
      }))
      .filter(tree =>
        tree.root.name.toLowerCase().includes(query) ||
        tree.root.slug.toLowerCase().includes(query) ||
        tree.children.length > 0
      );
  }, [categoryTree, searchQuery]);

  // Get root categories for parent selection
  const rootCategories = useMemo(() => {
    return data?.items?.filter((c: Category) => !c.parent_id) ?? [];
  }, [data]);

  const toggleRoot = (rootId: string) => {
    setExpandedRoots(prev => {
      const newSet = new Set(prev);
      if (newSet.has(rootId)) {
        newSet.delete(rootId);
      } else {
        newSet.add(rootId);
      }
      return newSet;
    });
  };

  const expandAll = () => {
    setExpandedRoots(new Set(categoryTree.map(t => t.root.id)));
  };

  const collapseAll = () => {
    setExpandedRoots(new Set());
  };

  const createMutation = useMutation({
    mutationFn: categoriesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      toast.success('Category created successfully');
      setIsCreateDialogOpen(false);
      setCreateFormData(defaultFormData);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create category');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Category> }) =>
      categoriesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      toast.success('Category updated successfully');
      setIsEditDialogOpen(false);
      setEditingCategory(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update category');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => categoriesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      toast.success('Category deleted successfully');
      setIsDeleteDialogOpen(false);
      setCategoryToDelete(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete category');
    },
  });

  const handleCreate = () => {
    if (!createFormData.name.trim()) {
      toast.error('Category name is required');
      return;
    }
    createMutation.mutate({
      name: createFormData.name,
      slug: createFormData.slug || createFormData.name.toLowerCase().replace(/\s+/g, '-'),
      description: createFormData.description || undefined,
      parent_id: createFormData.parent_id || undefined,
      sort_order: createFormData.sort_order || 0,
      is_active: createFormData.is_active,
    });
  };

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    setEditFormData({
      name: category.name,
      slug: category.slug,
      description: category.description || '',
      parent_id: category.parent_id || '',
      sort_order: category.sort_order || 0,
      is_active: category.is_active,
    });
    setIsEditDialogOpen(true);
  };

  const handleUpdate = () => {
    if (!editingCategory || !editFormData.name.trim()) {
      toast.error('Category name is required');
      return;
    }
    updateMutation.mutate({
      id: editingCategory.id,
      data: {
        name: editFormData.name,
        slug: editFormData.slug || editFormData.name.toLowerCase().replace(/\s+/g, '-'),
        description: editFormData.description || undefined,
        parent_id: editFormData.parent_id || undefined,
        sort_order: editFormData.sort_order,
        is_active: editFormData.is_active,
      },
    });
  };

  const handleDelete = (category: Category) => {
    setCategoryToDelete(category);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (categoryToDelete) {
      deleteMutation.mutate(categoryToDelete.id);
    }
  };

  const CategoryRow = ({ category, isChild = false }: { category: Category; isChild?: boolean }) => (
    <TableRow className={cn(isChild && "bg-muted/30")}>
      <TableCell>
        <div className={cn("flex items-center gap-3", isChild && "pl-8")}>
          <div className={cn(
            "flex h-9 w-9 items-center justify-center rounded-lg flex-shrink-0",
            isChild ? "bg-muted" : "bg-primary/10"
          )}>
            {isChild ? (
              <FolderTree className="h-4 w-4 text-muted-foreground" />
            ) : (
              <Folder className="h-4 w-4 text-primary" />
            )}
          </div>
          <div className="min-w-0">
            <div className={cn("font-medium truncate", !isChild && "text-primary")}>
              {category.name}
            </div>
            <div className="text-xs text-muted-foreground truncate">{category.slug}</div>
          </div>
        </div>
      </TableCell>
      <TableCell className="max-w-[200px]">
        <span className="text-sm text-muted-foreground line-clamp-1" title={category.description || ''}>
          {category.description || '-'}
        </span>
      </TableCell>
      <TableCell className="text-center">
        <span className="text-sm">{category.sort_order ?? 0}</span>
      </TableCell>
      <TableCell>
        <StatusBadge status={category.is_active ? 'ACTIVE' : 'INACTIVE'} />
      </TableCell>
      <TableCell>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => handleEdit(category)}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() => handleDelete(category)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader
        title="Categories"
        description="Manage product categories and subcategories"
        actions={
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add Category
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Category</DialogTitle>
                <DialogDescription>
                  Add a new product category to organize your catalog.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="create-name">Name *</Label>
                  <Input
                    id="create-name"
                    placeholder="Category name"
                    value={createFormData.name}
                    onChange={(e) =>
                      setCreateFormData({ ...createFormData, name: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-slug">Slug</Label>
                  <Input
                    id="create-slug"
                    placeholder="category-slug (auto-generated if empty)"
                    value={createFormData.slug}
                    onChange={(e) =>
                      setCreateFormData({ ...createFormData, slug: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-parent">Parent Category</Label>
                  <Select
                    value={createFormData.parent_id || 'none'}
                    onValueChange={(value) =>
                      setCreateFormData({ ...createFormData, parent_id: value === 'none' ? '' : value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select parent (optional)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None (Root Category)</SelectItem>
                      {rootCategories.map((cat: Category) => (
                        <SelectItem key={cat.id} value={cat.id}>
                          {cat.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-description">Description</Label>
                  <Textarea
                    id="create-description"
                    placeholder="Category description"
                    value={createFormData.description}
                    onChange={(e) =>
                      setCreateFormData({ ...createFormData, description: e.target.value })
                    }
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="create-order">Sort Order</Label>
                    <Input
                      id="create-order"
                      type="number"
                      placeholder="0"
                      value={createFormData.sort_order}
                      onChange={(e) =>
                        setCreateFormData({ ...createFormData, sort_order: parseInt(e.target.value) || 0 })
                      }
                    />
                  </div>
                  <div className="flex items-center justify-between pt-6">
                    <Label htmlFor="create-active">Active</Label>
                    <Switch
                      id="create-active"
                      checked={createFormData.is_active}
                      onCheckedChange={(checked) =>
                        setCreateFormData({ ...createFormData, is_active: checked })
                      }
                    />
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleCreate} disabled={createMutation.isPending}>
                  {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Create Category
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      {/* Search and Actions */}
      <div className="flex items-center justify-between gap-4">
        <Input
          placeholder="Search categories..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-sm"
        />
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={expandAll}>
            Expand All
          </Button>
          <Button variant="outline" size="sm" onClick={collapseAll}>
            Collapse All
          </Button>
        </div>
      </div>

      {/* Category Tree */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <div className="pl-8 space-y-2">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                </div>
              ))}
            </div>
          ) : filteredTree.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <FolderTree className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No categories found</p>
              {searchQuery && (
                <p className="text-sm mt-1">Try a different search term</p>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[300px]">Category</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="w-[80px] text-center">Order</TableHead>
                  <TableHead className="w-[100px]">Status</TableHead>
                  <TableHead className="w-[60px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTree.map(({ root, children }) => (
                  <Collapsible
                    key={root.id}
                    open={expandedRoots.has(root.id)}
                    onOpenChange={() => toggleRoot(root.id)}
                    asChild
                  >
                    <>
                      {/* Root Category Row */}
                      <TableRow className="bg-muted/50 hover:bg-muted/70">
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <CollapsibleTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8">
                                {children.length > 0 ? (
                                  expandedRoots.has(root.id) ? (
                                    <ChevronDown className="h-4 w-4" />
                                  ) : (
                                    <ChevronRight className="h-4 w-4" />
                                  )
                                ) : (
                                  <span className="w-4" />
                                )}
                              </Button>
                            </CollapsibleTrigger>
                            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 flex-shrink-0">
                              {expandedRoots.has(root.id) ? (
                                <FolderOpen className="h-4 w-4 text-primary" />
                              ) : (
                                <Folder className="h-4 w-4 text-primary" />
                              )}
                            </div>
                            <div className="min-w-0">
                              <div className="font-semibold text-primary truncate">{root.name}</div>
                              <div className="text-xs text-muted-foreground truncate">{root.slug}</div>
                            </div>
                            {children.length > 0 && (
                              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                                {children.length} sub
                              </span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-[200px]">
                          <span className="text-sm text-muted-foreground line-clamp-1" title={root.description || ''}>
                            {root.description || '-'}
                          </span>
                        </TableCell>
                        <TableCell className="text-center">
                          <span className="text-sm">{root.sort_order ?? 0}</span>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={root.is_active ? 'ACTIVE' : 'INACTIVE'} />
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuLabel>Actions</DropdownMenuLabel>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem onClick={() => handleEdit(root)}>
                                <Pencil className="mr-2 h-4 w-4" />
                                Edit
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className="text-destructive focus:text-destructive"
                                onClick={() => handleDelete(root)}
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>

                      {/* Child Categories */}
                      <CollapsibleContent asChild>
                        <>
                          {children.map(child => (
                            <CategoryRow key={child.id} category={child} isChild />
                          ))}
                        </>
                      </CollapsibleContent>
                    </>
                  </Collapsible>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Summary */}
      <div className="text-sm text-muted-foreground">
        {categoryTree.length} root categories, {data?.items?.filter((c: Category) => c.parent_id).length ?? 0} subcategories
      </div>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Category</DialogTitle>
            <DialogDescription>
              Update the category details.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Name *</Label>
              <Input
                id="edit-name"
                placeholder="Category name"
                value={editFormData.name}
                onChange={(e) =>
                  setEditFormData({ ...editFormData, name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-slug">Slug</Label>
              <Input
                id="edit-slug"
                placeholder="category-slug"
                value={editFormData.slug}
                onChange={(e) =>
                  setEditFormData({ ...editFormData, slug: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-parent">Parent Category</Label>
              <Select
                value={editFormData.parent_id || 'none'}
                onValueChange={(value) =>
                  setEditFormData({ ...editFormData, parent_id: value === 'none' ? '' : value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select parent (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None (Root Category)</SelectItem>
                  {rootCategories
                    .filter((cat: Category) => cat.id !== editingCategory?.id)
                    .map((cat: Category) => (
                      <SelectItem key={cat.id} value={cat.id}>
                        {cat.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                placeholder="Category description"
                value={editFormData.description}
                onChange={(e) =>
                  setEditFormData({ ...editFormData, description: e.target.value })
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-order">Sort Order</Label>
                <Input
                  id="edit-order"
                  type="number"
                  placeholder="0"
                  value={editFormData.sort_order}
                  onChange={(e) =>
                    setEditFormData({ ...editFormData, sort_order: parseInt(e.target.value) || 0 })
                  }
                />
              </div>
              <div className="flex items-center justify-between pt-6">
                <Label htmlFor="edit-active">Active</Label>
                <Switch
                  id="edit-active"
                  checked={editFormData.is_active}
                  onCheckedChange={(checked) =>
                    setEditFormData({ ...editFormData, is_active: checked })
                  }
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdate} disabled={updateMutation.isPending}>
              {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Category</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{categoryToDelete?.name}"? This action cannot be undone.
              {!categoryToDelete?.parent_id && (
                <span className="block mt-2 text-amber-600">
                  Warning: This is a root category. Deleting it may affect subcategories.
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
