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
import {
  Plus, GripVertical, Pencil, Trash2, Eye, EyeOff, ChevronDown, ChevronRight,
  FolderOpen, HelpCircle, Star, Search
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
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { IconPicker, IconByName } from '@/components/cms/icon-picker';
import { cmsApi, CMSFaqCategory, CMSFaqCategoryCreate, CMSFaqItem, CMSFaqItemCreate } from '@/lib/api/cms';
import { cn } from '@/lib/utils';

// ==================== Sortable Category Item ====================
function SortableCategoryItem({
  category,
  isExpanded,
  onToggleExpand,
  onEdit,
  onDelete,
  onToggleActive,
  onAddItem,
}: {
  category: CMSFaqCategory;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onEdit: (category: CMSFaqCategory) => void;
  onDelete: (id: string) => void;
  onToggleActive: (id: string, active: boolean) => void;
  onAddItem: (categoryId: string) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: category.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'border rounded-lg bg-card',
        isDragging && 'opacity-50 shadow-lg',
        !category.is_active && 'opacity-60'
      )}
    >
      <div className="flex items-center gap-4 p-4">
        <button
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground"
        >
          <GripVertical className="h-5 w-5" />
        </button>

        <button
          onClick={onToggleExpand}
          className="text-muted-foreground hover:text-foreground"
        >
          {isExpanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
        </button>

        <div className={cn('p-2 rounded-lg bg-primary/10', category.icon_color)}>
          <IconByName name={category.icon} className="h-6 w-6 text-primary" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-medium">{category.name}</h3>
            <Badge variant="secondary" className="text-xs">
              {category.items_count} items
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">/{category.slug}</p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onAddItem(category.id)}
            title="Add FAQ Item"
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Item
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onToggleActive(category.id, !category.is_active)}
            title={category.is_active ? 'Deactivate' : 'Activate'}
          >
            {category.is_active ? (
              <Eye className="h-4 w-4 text-green-600" />
            ) : (
              <EyeOff className="h-4 w-4 text-muted-foreground" />
            )}
          </Button>
          <Button variant="ghost" size="icon" onClick={() => onEdit(category)}>
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
                <AlertDialogTitle>Delete Category</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete &quot;{category.name}&quot;?
                  This will also delete all {category.items_count} FAQ items in this category.
                  This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => onDelete(category.id)}>
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
    </div>
  );
}

// ==================== Sortable FAQ Item ====================
function SortableFaqItem({
  item,
  onEdit,
  onDelete,
  onToggleActive,
  onToggleFeatured,
}: {
  item: CMSFaqItem;
  onEdit: (item: CMSFaqItem) => void;
  onDelete: (id: string) => void;
  onToggleActive: (id: string, active: boolean) => void;
  onToggleFeatured: (id: string, featured: boolean) => void;
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
        'flex items-start gap-3 p-3 bg-muted/50 border rounded-lg',
        isDragging && 'opacity-50 shadow-lg',
        !item.is_active && 'opacity-60'
      )}
    >
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground mt-1"
      >
        <GripVertical className="h-4 w-4" />
      </button>

      <HelpCircle className="h-4 w-4 text-muted-foreground mt-1 shrink-0" />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium text-sm line-clamp-1">{item.question}</p>
          {item.is_featured && (
            <Star className="h-3 w-3 text-yellow-500 fill-yellow-500 shrink-0" />
          )}
        </div>
        <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">{item.answer}</p>
        {item.keywords && item.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {item.keywords.slice(0, 3).map((kw, i) => (
              <Badge key={i} variant="outline" className="text-[10px] px-1 py-0">
                {kw}
              </Badge>
            ))}
            {item.keywords.length > 3 && (
              <Badge variant="outline" className="text-[10px] px-1 py-0">
                +{item.keywords.length - 3}
              </Badge>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => onToggleFeatured(item.id, !item.is_featured)}
          title={item.is_featured ? 'Unfeature' : 'Feature'}
        >
          <Star className={cn('h-3 w-3', item.is_featured && 'text-yellow-500 fill-yellow-500')} />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => onToggleActive(item.id, !item.is_active)}
          title={item.is_active ? 'Deactivate' : 'Activate'}
        >
          {item.is_active ? (
            <Eye className="h-3 w-3 text-green-600" />
          ) : (
            <EyeOff className="h-3 w-3 text-muted-foreground" />
          )}
        </Button>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => onEdit(item)}>
          <Pencil className="h-3 w-3" />
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="icon" className="h-7 w-7">
              <Trash2 className="h-3 w-3 text-destructive" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete FAQ Item</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete this FAQ? This action cannot be undone.
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

// ==================== Category Form ====================
interface CategoryFormProps {
  category?: CMSFaqCategory | null;
  onSubmit: (data: CMSFaqCategoryCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

function CategoryForm({ category, onSubmit, onCancel, isLoading }: CategoryFormProps) {
  const [formData, setFormData] = useState<CMSFaqCategoryCreate>({
    name: category?.name || '',
    slug: category?.slug || '',
    description: category?.description || '',
    icon: category?.icon || 'HelpCircle',
    icon_color: category?.icon_color || '',
    is_active: category?.is_active ?? true,
  });

  const handleNameChange = (name: string) => {
    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    setFormData({ ...formData, name, slug: category ? formData.slug : slug });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="name">Name *</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder="Orders & Shopping"
            required
          />
        </div>
        <div>
          <Label htmlFor="slug">Slug *</Label>
          <Input
            id="slug"
            value={formData.slug}
            onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
            placeholder="orders-shopping"
            required
            pattern="^[a-z0-9-]+$"
            title="Lowercase letters, numbers, and hyphens only"
          />
        </div>
      </div>
      <div>
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={formData.description || ''}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="Frequently asked questions about orders and shopping"
          rows={2}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
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
      </div>
      <div className="flex items-center gap-2">
        <Switch
          id="is_active"
          checked={formData.is_active}
          onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
        />
        <Label htmlFor="is_active">Active</Label>
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : category ? 'Update' : 'Create'}
        </Button>
      </div>
    </form>
  );
}

// ==================== FAQ Item Form ====================
interface FaqItemFormProps {
  item?: CMSFaqItem | null;
  categories: CMSFaqCategory[];
  defaultCategoryId?: string;
  onSubmit: (data: CMSFaqItemCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

function FaqItemForm({ item, categories, defaultCategoryId, onSubmit, onCancel, isLoading }: FaqItemFormProps) {
  const [formData, setFormData] = useState<CMSFaqItemCreate>({
    category_id: item?.category_id || defaultCategoryId || '',
    question: item?.question || '',
    answer: item?.answer || '',
    keywords: item?.keywords || [],
    is_featured: item?.is_featured ?? false,
    is_active: item?.is_active ?? true,
  });
  const [keywordsText, setKeywordsText] = useState(formData.keywords?.join(', ') || '');

  const handleKeywordsChange = (text: string) => {
    setKeywordsText(text);
    const keywords = text.split(',').map(k => k.trim()).filter(k => k.length > 0);
    setFormData({ ...formData, keywords });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="category_id">Category *</Label>
        <Select
          value={formData.category_id}
          onValueChange={(value) => setFormData({ ...formData, category_id: value })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select a category" />
          </SelectTrigger>
          <SelectContent>
            {categories.map((cat) => (
              <SelectItem key={cat.id} value={cat.id}>
                <div className="flex items-center gap-2">
                  <IconByName name={cat.icon} className="h-4 w-4" />
                  {cat.name}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label htmlFor="question">Question *</Label>
        <Input
          id="question"
          value={formData.question}
          onChange={(e) => setFormData({ ...formData, question: e.target.value })}
          placeholder="How do I place an order?"
          required
        />
      </div>
      <div>
        <Label htmlFor="answer">Answer *</Label>
        <Textarea
          id="answer"
          value={formData.answer}
          onChange={(e) => setFormData({ ...formData, answer: e.target.value })}
          placeholder="Detailed answer to the question..."
          rows={5}
          required
        />
      </div>
      <div>
        <Label htmlFor="keywords">Keywords (comma-separated)</Label>
        <Input
          id="keywords"
          value={keywordsText}
          onChange={(e) => handleKeywordsChange(e.target.value)}
          placeholder="order, buy, purchase, cart"
        />
        <p className="text-xs text-muted-foreground mt-1">
          Keywords help users find this FAQ when searching
        </p>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Switch
            id="is_featured"
            checked={formData.is_featured}
            onCheckedChange={(checked) => setFormData({ ...formData, is_featured: checked })}
          />
          <Label htmlFor="is_featured">Featured</Label>
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
          {isLoading ? 'Saving...' : item ? 'Update' : 'Create'}
        </Button>
      </div>
    </form>
  );
}

// ==================== Main Page Component ====================
export default function FaqPage() {
  const queryClient = useQueryClient();
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [editingCategory, setEditingCategory] = useState<CMSFaqCategory | null>(null);
  const [editingItem, setEditingItem] = useState<CMSFaqItem | null>(null);
  const [isCategoryDialogOpen, setIsCategoryDialogOpen] = useState(false);
  const [isItemDialogOpen, setIsItemDialogOpen] = useState(false);
  const [addingItemToCategoryId, setAddingItemToCategoryId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Fetch categories
  const { data: categoriesData, isLoading: categoriesLoading } = useQuery({
    queryKey: ['cms-faq-categories'],
    queryFn: () => cmsApi.faqCategories.list(),
  });

  // Fetch items for selected category
  const { data: itemsData, isLoading: itemsLoading } = useQuery({
    queryKey: ['cms-faq-items', selectedCategoryId],
    queryFn: () => cmsApi.faqItems.list({ category_id: selectedCategoryId || undefined }),
    enabled: !!selectedCategoryId,
  });

  // Category mutations
  const createCategoryMutation = useMutation({
    mutationFn: cmsApi.faqCategories.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-faq-categories'] });
      setIsCategoryDialogOpen(false);
      toast.success('FAQ category created successfully');
    },
    onError: () => {
      toast.error('Failed to create FAQ category');
    },
  });

  const updateCategoryMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSFaqCategoryCreate> }) =>
      cmsApi.faqCategories.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-faq-categories'] });
      setIsCategoryDialogOpen(false);
      setEditingCategory(null);
      toast.success('FAQ category updated successfully');
    },
    onError: () => {
      toast.error('Failed to update FAQ category');
    },
  });

  const deleteCategoryMutation = useMutation({
    mutationFn: cmsApi.faqCategories.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-faq-categories'] });
      toast.success('FAQ category deleted successfully');
    },
    onError: () => {
      toast.error('Failed to delete FAQ category');
    },
  });

  const reorderCategoriesMutation = useMutation({
    mutationFn: cmsApi.faqCategories.reorder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-faq-categories'] });
    },
    onError: () => {
      toast.error('Failed to reorder FAQ categories');
    },
  });

  // Item mutations
  const createItemMutation = useMutation({
    mutationFn: cmsApi.faqItems.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-faq-items'] });
      queryClient.invalidateQueries({ queryKey: ['cms-faq-categories'] });
      setIsItemDialogOpen(false);
      setAddingItemToCategoryId(null);
      toast.success('FAQ item created successfully');
    },
    onError: () => {
      toast.error('Failed to create FAQ item');
    },
  });

  const updateItemMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSFaqItemCreate> }) =>
      cmsApi.faqItems.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-faq-items'] });
      queryClient.invalidateQueries({ queryKey: ['cms-faq-categories'] });
      setIsItemDialogOpen(false);
      setEditingItem(null);
      toast.success('FAQ item updated successfully');
    },
    onError: () => {
      toast.error('Failed to update FAQ item');
    },
  });

  const deleteItemMutation = useMutation({
    mutationFn: cmsApi.faqItems.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-faq-items'] });
      queryClient.invalidateQueries({ queryKey: ['cms-faq-categories'] });
      toast.success('FAQ item deleted successfully');
    },
    onError: () => {
      toast.error('Failed to delete FAQ item');
    },
  });

  const reorderItemsMutation = useMutation({
    mutationFn: cmsApi.faqItems.reorder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-faq-items'] });
    },
    onError: () => {
      toast.error('Failed to reorder FAQ items');
    },
  });

  const categories = categoriesData?.data?.items || [];
  const items = itemsData?.data?.items || [];

  const handleCategoryDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = categories.findIndex((c) => c.id === active.id);
      const newIndex = categories.findIndex((c) => c.id === over.id);

      const newOrder = arrayMove(categories, oldIndex, newIndex);
      const ids = newOrder.map((c) => c.id);

      reorderCategoriesMutation.mutate(ids);
    }
  };

  const handleItemDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = items.findIndex((i) => i.id === active.id);
      const newIndex = items.findIndex((i) => i.id === over.id);

      const newOrder = arrayMove(items, oldIndex, newIndex);
      const ids = newOrder.map((i) => i.id);

      reorderItemsMutation.mutate(ids);
    }
  };

  const handleCategorySubmit = (formData: CMSFaqCategoryCreate) => {
    if (editingCategory) {
      updateCategoryMutation.mutate({ id: editingCategory.id, data: formData });
    } else {
      createCategoryMutation.mutate(formData);
    }
  };

  const handleItemSubmit = (formData: CMSFaqItemCreate) => {
    if (editingItem) {
      updateItemMutation.mutate({ id: editingItem.id, data: formData });
    } else {
      createItemMutation.mutate(formData);
    }
  };

  const toggleExpandCategory = (categoryId: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
        setSelectedCategoryId(categoryId);
      }
      return next;
    });
  };

  const totalItems = categories.reduce((sum, cat) => sum + cat.items_count, 0);

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">FAQ Management</h1>
          <p className="text-muted-foreground">
            Manage frequently asked questions for the storefront
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-sm">
            {categories.length} categories, {totalItems} questions
          </Badge>
        </div>
      </div>

      <Tabs defaultValue="categories" className="space-y-6">
        <TabsList>
          <TabsTrigger value="categories">
            <FolderOpen className="h-4 w-4 mr-2" />
            Categories
          </TabsTrigger>
          <TabsTrigger value="items">
            <HelpCircle className="h-4 w-4 mr-2" />
            All FAQ Items
          </TabsTrigger>
        </TabsList>

        {/* Categories Tab */}
        <TabsContent value="categories" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>FAQ Categories</CardTitle>
                <CardDescription>
                  Organize FAQs into categories. Drag to reorder.
                </CardDescription>
              </div>
              <Dialog open={isCategoryDialogOpen} onOpenChange={setIsCategoryDialogOpen}>
                <DialogTrigger asChild>
                  <Button onClick={() => setEditingCategory(null)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Category
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>
                      {editingCategory ? 'Edit Category' : 'Create Category'}
                    </DialogTitle>
                  </DialogHeader>
                  <CategoryForm
                    category={editingCategory}
                    onSubmit={handleCategorySubmit}
                    onCancel={() => {
                      setIsCategoryDialogOpen(false);
                      setEditingCategory(null);
                    }}
                    isLoading={createCategoryMutation.isPending || updateCategoryMutation.isPending}
                  />
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {categoriesLoading ? (
                <div className="text-center py-8 text-muted-foreground">
                  Loading categories...
                </div>
              ) : categories.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No FAQ categories yet. Add categories like &quot;Orders&quot;, &quot;Shipping&quot;, &quot;Payments&quot;, etc.
                </div>
              ) : (
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleCategoryDragEnd}
                >
                  <SortableContext
                    items={categories.map((c) => c.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    <div className="space-y-3">
                      {categories.map((category) => (
                        <div key={category.id}>
                          <SortableCategoryItem
                            category={category}
                            isExpanded={expandedCategories.has(category.id)}
                            onToggleExpand={() => toggleExpandCategory(category.id)}
                            onEdit={(c) => {
                              setEditingCategory(c);
                              setIsCategoryDialogOpen(true);
                            }}
                            onDelete={(id) => deleteCategoryMutation.mutate(id)}
                            onToggleActive={(id, active) =>
                              updateCategoryMutation.mutate({ id, data: { is_active: active } })
                            }
                            onAddItem={(categoryId) => {
                              setAddingItemToCategoryId(categoryId);
                              setEditingItem(null);
                              setIsItemDialogOpen(true);
                            }}
                          />

                          {/* Expanded items */}
                          {expandedCategories.has(category.id) && (
                            <div className="ml-12 mt-2 space-y-2">
                              {selectedCategoryId === category.id && itemsLoading ? (
                                <div className="text-sm text-muted-foreground py-2">
                                  Loading items...
                                </div>
                              ) : selectedCategoryId === category.id && items.length === 0 ? (
                                <div className="text-sm text-muted-foreground py-2">
                                  No FAQ items in this category yet.
                                </div>
                              ) : selectedCategoryId === category.id ? (
                                <DndContext
                                  sensors={sensors}
                                  collisionDetection={closestCenter}
                                  onDragEnd={handleItemDragEnd}
                                >
                                  <SortableContext
                                    items={items.map((i) => i.id)}
                                    strategy={verticalListSortingStrategy}
                                  >
                                    {items.map((item) => (
                                      <SortableFaqItem
                                        key={item.id}
                                        item={item}
                                        onEdit={(i) => {
                                          setEditingItem(i);
                                          setAddingItemToCategoryId(null);
                                          setIsItemDialogOpen(true);
                                        }}
                                        onDelete={(id) => deleteItemMutation.mutate(id)}
                                        onToggleActive={(id, active) =>
                                          updateItemMutation.mutate({ id, data: { is_active: active } })
                                        }
                                        onToggleFeatured={(id, featured) =>
                                          updateItemMutation.mutate({ id, data: { is_featured: featured } })
                                        }
                                      />
                                    ))}
                                  </SortableContext>
                                </DndContext>
                              ) : null}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </SortableContext>
                </DndContext>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* All Items Tab */}
        <TabsContent value="items" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>All FAQ Items</CardTitle>
                <CardDescription>
                  View and manage all FAQ items across all categories
                </CardDescription>
              </div>
              <Dialog open={isItemDialogOpen} onOpenChange={setIsItemDialogOpen}>
                <DialogTrigger asChild>
                  <Button onClick={() => {
                    setEditingItem(null);
                    setAddingItemToCategoryId(null);
                  }}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add FAQ
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>
                      {editingItem ? 'Edit FAQ' : 'Create FAQ'}
                    </DialogTitle>
                  </DialogHeader>
                  <FaqItemForm
                    item={editingItem}
                    categories={categories}
                    defaultCategoryId={addingItemToCategoryId || undefined}
                    onSubmit={handleItemSubmit}
                    onCancel={() => {
                      setIsItemDialogOpen(false);
                      setEditingItem(null);
                      setAddingItemToCategoryId(null);
                    }}
                    isLoading={createItemMutation.isPending || updateItemMutation.isPending}
                  />
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">
                Use the &quot;Categories&quot; tab to view and manage FAQ items within each category.
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Item Dialog (can also be opened from category view) */}
      <Dialog open={isItemDialogOpen && !isCategoryDialogOpen} onOpenChange={setIsItemDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingItem ? 'Edit FAQ' : 'Create FAQ'}
            </DialogTitle>
          </DialogHeader>
          <FaqItemForm
            item={editingItem}
            categories={categories}
            defaultCategoryId={addingItemToCategoryId || undefined}
            onSubmit={handleItemSubmit}
            onCancel={() => {
              setIsItemDialogOpen(false);
              setEditingItem(null);
              setAddingItemToCategoryId(null);
            }}
            isLoading={createItemMutation.isPending || updateItemMutation.isPending}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
