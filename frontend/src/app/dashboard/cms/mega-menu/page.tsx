'use client';

import { useState, useEffect } from 'react';
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
  Folder,
  Link as LinkIcon,
  Sparkles,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
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
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { cmsApi, CMSMegaMenuItem, CMSMegaMenuItemCreate } from '@/lib/api/cms';
import { categoriesApi } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Category {
  id: string;
  name: string;
  slug: string;
  parent_id?: string;
  children?: Category[];
}

function SortableMegaMenuItem({
  item,
  onEdit,
  onDelete,
  onToggleActive,
}: {
  item: CMSMegaMenuItem;
  onEdit: (item: CMSMegaMenuItem) => void;
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
  } = useSortable({ id: item.id });

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
        !item.is_active && 'opacity-60'
      )}
    >
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground"
      >
        <GripVertical className="h-5 w-5" />
      </button>

      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div className="p-2 bg-muted rounded">
          {item.menu_type === 'CATEGORY' ? (
            <Folder className="h-5 w-5 text-blue-600" />
          ) : (
            <LinkIcon className="h-5 w-5 text-green-600" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-medium truncate">{item.title}</h3>
            {item.is_highlighted && (
              <Badge variant="default" className="text-xs bg-amber-500">
                <Sparkles className="h-3 w-3 mr-1" />
                {item.highlight_text || 'Highlighted'}
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground truncate">
            {item.menu_type === 'CATEGORY' ? (
              <>Category: {item.category_name || 'Not linked'}</>
            ) : (
              <>Link: {item.url || 'No URL'}</>
            )}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onToggleActive(item.id, !item.is_active)}
          title={item.is_active ? 'Deactivate' : 'Activate'}
        >
          {item.is_active ? (
            <Eye className="h-4 w-4 text-green-600" />
          ) : (
            <EyeOff className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onEdit(item)}
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
              <AlertDialogTitle>Delete Menu Item</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete &quot;{item.title}&quot;? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => onDelete(item.id)}>
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}

interface CategorySelectorProps {
  categories: Category[];
  selectedId?: string;
  onSelect: (id: string) => void;
}

function CategorySelector({ categories, selectedId, onSelect }: CategorySelectorProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggleExpand = (id: string) => {
    const next = new Set(expandedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setExpandedIds(next);
  };

  const renderCategory = (category: Category, level: number = 0) => {
    const hasChildren = category.children && category.children.length > 0;
    const isExpanded = expandedIds.has(category.id);
    const isSelected = selectedId === category.id;

    return (
      <div key={category.id}>
        <div
          className={cn(
            'flex items-center gap-2 py-2 px-2 rounded cursor-pointer hover:bg-muted',
            isSelected && 'bg-primary/10 border border-primary'
          )}
          style={{ paddingLeft: `${level * 16 + 8}px` }}
          onClick={() => onSelect(category.id)}
        >
          {hasChildren ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(category.id);
              }}
              className="p-0.5"
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </button>
          ) : (
            <span className="w-5" />
          )}
          <span className={cn('flex-1', isSelected && 'font-medium')}>{category.name}</span>
        </div>
        {hasChildren && isExpanded && (
          <div>
            {category.children!.map((child) => renderCategory(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="border rounded-lg max-h-64 overflow-y-auto">
      {categories.map((category) => renderCategory(category))}
    </div>
  );
}

interface MegaMenuFormProps {
  item?: CMSMegaMenuItem | null;
  categories: Category[];
  onSubmit: (data: CMSMegaMenuItemCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

function MegaMenuForm({ item, categories, onSubmit, onCancel, isLoading }: MegaMenuFormProps) {
  const [formData, setFormData] = useState<CMSMegaMenuItemCreate>({
    title: item?.title || '',
    icon: item?.icon || '',
    image_url: item?.image_url || '',
    menu_type: item?.menu_type || 'CATEGORY',
    category_id: item?.category_id || '',
    url: item?.url || '',
    target: item?.target || '_self',
    show_subcategories: item?.show_subcategories ?? true,
    subcategory_ids: item?.subcategory_ids || [],
    is_active: item?.is_active ?? true,
    is_highlighted: item?.is_highlighted ?? false,
    highlight_text: item?.highlight_text || '',
  });

  // Find selected category's children for subcategory selection
  const findCategory = (cats: Category[], id: string): Category | null => {
    for (const cat of cats) {
      if (cat.id === id) return cat;
      if (cat.children) {
        const found = findCategory(cat.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  const selectedCategory = formData.category_id ? findCategory(categories, formData.category_id) : null;
  const subcategories = selectedCategory?.children || [];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Clean up the form data - remove empty strings for UUID fields
    const cleanedData = {
      ...formData,
      // Don't send empty strings for UUID fields - send null instead
      category_id: formData.category_id || undefined,
      subcategory_ids: formData.subcategory_ids?.length ? formData.subcategory_ids : undefined,
      // Don't send empty strings for optional string fields
      icon: formData.icon || undefined,
      image_url: formData.image_url || undefined,
      url: formData.url || undefined,
      highlight_text: formData.highlight_text || undefined,
    };
    onSubmit(cleanedData as CMSMegaMenuItemCreate);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <Label htmlFor="title">Menu Title *</Label>
          <Input
            id="title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            placeholder="e.g., Water Purifiers"
            required
          />
        </div>

        <div>
          <Label htmlFor="icon">Icon (Lucide icon name)</Label>
          <Input
            id="icon"
            value={formData.icon || ''}
            onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
            placeholder="e.g., Droplets"
          />
        </div>

        <div>
          <Label htmlFor="image_url">Image URL</Label>
          <Input
            id="image_url"
            value={formData.image_url || ''}
            onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
            placeholder="https://..."
          />
        </div>

        <div className="col-span-2">
          <Label>Menu Type *</Label>
          <Select
            value={formData.menu_type}
            onValueChange={(v) => setFormData({ ...formData, menu_type: v as 'CATEGORY' | 'CUSTOM_LINK' })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="CATEGORY">
                <div className="flex items-center gap-2">
                  <Folder className="h-4 w-4 text-blue-600" />
                  Category Link
                </div>
              </SelectItem>
              <SelectItem value="CUSTOM_LINK">
                <div className="flex items-center gap-2">
                  <LinkIcon className="h-4 w-4 text-green-600" />
                  Custom URL
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        {formData.menu_type === 'CATEGORY' && (
          <>
            <div className="col-span-2">
              <Label>Select Category *</Label>
              <CategorySelector
                categories={categories}
                selectedId={formData.category_id}
                onSelect={(id) => setFormData({ ...formData, category_id: id, subcategory_ids: [] })}
              />
            </div>

            <div className="col-span-2 flex items-center gap-2">
              <Switch
                id="show_subcategories"
                checked={formData.show_subcategories}
                onCheckedChange={(checked) => setFormData({ ...formData, show_subcategories: checked })}
              />
              <Label htmlFor="show_subcategories">Show Subcategories in Dropdown</Label>
            </div>

            {formData.show_subcategories && subcategories.length > 0 && (
              <div className="col-span-2">
                <Label>Select Specific Subcategories (leave empty to show all)</Label>
                <div className="border rounded-lg p-3 max-h-48 overflow-y-auto space-y-2">
                  {subcategories.map((sub) => (
                    <div key={sub.id} className="flex items-center gap-2">
                      <Checkbox
                        id={`sub-${sub.id}`}
                        checked={(formData.subcategory_ids || []).includes(sub.id)}
                        onCheckedChange={(checked) => {
                          const current = formData.subcategory_ids || [];
                          if (checked) {
                            setFormData({ ...formData, subcategory_ids: [...current, sub.id] });
                          } else {
                            setFormData({ ...formData, subcategory_ids: current.filter((id) => id !== sub.id) });
                          }
                        }}
                      />
                      <Label htmlFor={`sub-${sub.id}`} className="font-normal cursor-pointer">
                        {sub.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {formData.menu_type === 'CUSTOM_LINK' && (
          <>
            <div className="col-span-2">
              <Label htmlFor="url">URL *</Label>
              <Input
                id="url"
                value={formData.url || ''}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                placeholder="/products or https://..."
                required={formData.menu_type === 'CUSTOM_LINK'}
              />
            </div>
            <div>
              <Label htmlFor="target">Link Target</Label>
              <Select
                value={formData.target}
                onValueChange={(v) => setFormData({ ...formData, target: v as '_self' | '_blank' })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="_self">Same Tab</SelectItem>
                  <SelectItem value="_blank">New Tab</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        )}

        <div className="col-span-2 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Switch
              id="is_active"
              checked={formData.is_active}
              onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
            />
            <Label htmlFor="is_active">Active</Label>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              id="is_highlighted"
              checked={formData.is_highlighted}
              onCheckedChange={(checked) => setFormData({ ...formData, is_highlighted: checked })}
            />
            <Label htmlFor="is_highlighted">Highlight Badge</Label>
          </div>
        </div>

        {formData.is_highlighted && (
          <div className="col-span-2">
            <Label htmlFor="highlight_text">Highlight Text</Label>
            <Input
              id="highlight_text"
              value={formData.highlight_text || ''}
              onChange={(e) => setFormData({ ...formData, highlight_text: e.target.value })}
              placeholder="e.g., New, Sale, Hot"
              maxLength={20}
            />
          </div>
        )}
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : item ? 'Update' : 'Create'}
        </Button>
      </div>
    </form>
  );
}

export default function MegaMenuPage() {
  const queryClient = useQueryClient();
  const [editingItem, setEditingItem] = useState<CMSMegaMenuItem | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Fetch mega menu items
  const { data, isLoading } = useQuery({
    queryKey: ['cms-mega-menu-items'],
    queryFn: () => cmsApi.megaMenuItems.list(),
  });

  // Fetch categories for the form
  const { data: categoriesData } = useQuery({
    queryKey: ['categories-tree'],
    queryFn: () => categoriesApi.getTree(),
  });

  const categories = (categoriesData as Category[]) || [];

  const createMutation = useMutation({
    mutationFn: cmsApi.megaMenuItems.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-mega-menu-items'] });
      setIsDialogOpen(false);
      toast.success('Menu item created successfully');
    },
    onError: () => {
      toast.error('Failed to create menu item');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSMegaMenuItemCreate> }) =>
      cmsApi.megaMenuItems.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-mega-menu-items'] });
      setIsDialogOpen(false);
      setEditingItem(null);
      toast.success('Menu item updated successfully');
    },
    onError: () => {
      toast.error('Failed to update menu item');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: cmsApi.megaMenuItems.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-mega-menu-items'] });
      toast.success('Menu item deleted successfully');
    },
    onError: () => {
      toast.error('Failed to delete menu item');
    },
  });

  const reorderMutation = useMutation({
    mutationFn: cmsApi.megaMenuItems.reorder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-mega-menu-items'] });
    },
    onError: () => {
      toast.error('Failed to reorder menu items');
    },
  });

  const items = data?.data?.items || [];

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = items.findIndex((i) => i.id === active.id);
      const newIndex = items.findIndex((i) => i.id === over.id);

      const newOrder = arrayMove(items, oldIndex, newIndex);
      const ids = newOrder.map((i) => i.id);

      reorderMutation.mutate(ids);
    }
  };

  const handleSubmit = (formData: CMSMegaMenuItemCreate) => {
    if (editingItem) {
      updateMutation.mutate({ id: editingItem.id, data: formData });
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
          <div>
            <CardTitle>Mega Menu Management</CardTitle>
            <CardDescription className="mt-1">
              Control which categories and links appear in the D2C storefront navigation.
              Drag items to reorder them.
            </CardDescription>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => setEditingItem(null)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Menu Item
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>
                  {editingItem ? 'Edit Menu Item' : 'Create Menu Item'}
                </DialogTitle>
              </DialogHeader>
              <MegaMenuForm
                item={editingItem}
                categories={categories}
                onSubmit={handleSubmit}
                onCancel={() => {
                  setIsDialogOpen(false);
                  setEditingItem(null);
                }}
                isLoading={createMutation.isPending || updateMutation.isPending}
              />
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading menu items...
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p className="mb-4">No menu items yet. Create your first menu item to build your D2C navigation.</p>
              <p className="text-sm">
                Add categories from your product catalog or create custom links to any page.
              </p>
            </div>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={items.map((i) => i.id)}
                strategy={verticalListSortingStrategy}
              >
                <div className="space-y-3">
                  {items.map((item) => (
                    <SortableMegaMenuItem
                      key={item.id}
                      item={item}
                      onEdit={(i) => {
                        setEditingItem(i);
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
