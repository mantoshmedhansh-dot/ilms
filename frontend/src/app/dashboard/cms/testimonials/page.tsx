'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Pencil,
  Trash2,
  Eye,
  EyeOff,
  Star,
  Quote,
  User,
  MapPin,
} from 'lucide-react';
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
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cmsApi, CMSTestimonial, CMSTestimonialCreate } from '@/lib/api/cms';
import { cn } from '@/lib/utils';

function StarRating({ rating, onChange }: { rating: number; onChange?: (rating: number) => void }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange?.(star)}
          disabled={!onChange}
          className={cn(
            'transition-colors',
            onChange && 'cursor-pointer hover:scale-110'
          )}
        >
          <Star
            className={cn(
              'h-5 w-5',
              star <= rating
                ? 'fill-yellow-400 text-yellow-400'
                : 'text-muted-foreground'
            )}
          />
        </button>
      ))}
    </div>
  );
}

function TestimonialCard({
  testimonial,
  onEdit,
  onDelete,
  onToggleActive,
  onToggleFeatured,
}: {
  testimonial: CMSTestimonial;
  onEdit: (testimonial: CMSTestimonial) => void;
  onDelete: (id: string) => void;
  onToggleActive: (id: string, active: boolean) => void;
  onToggleFeatured: (id: string, featured: boolean) => void;
}) {
  return (
    <div
      className={cn(
        'relative p-4 bg-card border rounded-lg transition-all',
        !testimonial.is_active && 'opacity-60'
      )}
    >
      {/* Featured badge */}
      {testimonial.is_featured && (
        <Badge className="absolute -top-2 -right-2 bg-yellow-500 hover:bg-yellow-600">
          Featured
        </Badge>
      )}

      {/* Quote icon */}
      <Quote className="absolute top-4 right-4 h-8 w-8 text-muted-foreground/20" />

      {/* Content */}
      <div className="space-y-3">
        {/* Rating */}
        <StarRating rating={testimonial.rating} />

        {/* Title */}
        {testimonial.title && (
          <h4 className="font-semibold text-sm">{testimonial.title}</h4>
        )}

        {/* Content */}
        <p className="text-sm text-muted-foreground line-clamp-3">
          &ldquo;{testimonial.content}&rdquo;
        </p>

        {/* Customer info */}
        <div className="flex items-center gap-3 pt-2 border-t">
          <Avatar className="h-10 w-10">
            <AvatarImage src={testimonial.customer_avatar_url || undefined} />
            <AvatarFallback>
              {testimonial.customer_name
                .split(' ')
                .map((n) => n[0])
                .join('')
                .toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm truncate">
              {testimonial.customer_name}
            </p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {testimonial.customer_designation && (
                <span>{testimonial.customer_designation}</span>
              )}
              {testimonial.customer_location && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {testimonial.customer_location}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Product info */}
        {testimonial.product_name && (
          <div className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
            Product: {testimonial.product_name}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-1 mt-4 pt-3 border-t">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onToggleFeatured(testimonial.id, !testimonial.is_featured)}
          title={testimonial.is_featured ? 'Remove from featured' : 'Mark as featured'}
        >
          <Star
            className={cn(
              'h-4 w-4',
              testimonial.is_featured
                ? 'fill-yellow-400 text-yellow-400'
                : 'text-muted-foreground'
            )}
          />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onToggleActive(testimonial.id, !testimonial.is_active)}
          title={testimonial.is_active ? 'Deactivate' : 'Activate'}
        >
          {testimonial.is_active ? (
            <Eye className="h-4 w-4 text-green-600" />
          ) : (
            <EyeOff className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onEdit(testimonial)}
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
              <AlertDialogTitle>Delete Testimonial</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete the testimonial from &quot;{testimonial.customer_name}&quot;? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => onDelete(testimonial.id)}>
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}

interface TestimonialFormProps {
  testimonial?: CMSTestimonial | null;
  onSubmit: (data: CMSTestimonialCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

function TestimonialForm({ testimonial, onSubmit, onCancel, isLoading }: TestimonialFormProps) {
  const [formData, setFormData] = useState<CMSTestimonialCreate>({
    customer_name: testimonial?.customer_name || '',
    customer_location: testimonial?.customer_location || '',
    customer_avatar_url: testimonial?.customer_avatar_url || '',
    customer_designation: testimonial?.customer_designation || '',
    rating: testimonial?.rating || 5,
    content: testimonial?.content || '',
    title: testimonial?.title || '',
    product_name: testimonial?.product_name || '',
    product_id: testimonial?.product_id || '',
    is_featured: testimonial?.is_featured ?? false,
    is_active: testimonial?.is_active ?? true,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <Label htmlFor="customer_name">Customer Name *</Label>
          <Input
            id="customer_name"
            value={formData.customer_name}
            onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
            placeholder="John Doe"
            required
          />
        </div>
        <div>
          <Label htmlFor="customer_location">Location</Label>
          <Input
            id="customer_location"
            value={formData.customer_location || ''}
            onChange={(e) => setFormData({ ...formData, customer_location: e.target.value })}
            placeholder="Mumbai, India"
          />
        </div>
        <div>
          <Label htmlFor="customer_designation">Designation/Title</Label>
          <Input
            id="customer_designation"
            value={formData.customer_designation || ''}
            onChange={(e) => setFormData({ ...formData, customer_designation: e.target.value })}
            placeholder="Homeowner"
          />
        </div>
        <div className="col-span-2">
          <Label htmlFor="customer_avatar_url">Avatar URL</Label>
          <Input
            id="customer_avatar_url"
            value={formData.customer_avatar_url || ''}
            onChange={(e) => setFormData({ ...formData, customer_avatar_url: e.target.value })}
            placeholder="https://..."
          />
        </div>
        <div className="col-span-2">
          <Label>Rating *</Label>
          <div className="mt-2">
            <StarRating
              rating={formData.rating}
              onChange={(rating) => setFormData({ ...formData, rating })}
            />
          </div>
        </div>
        <div className="col-span-2">
          <Label htmlFor="title">Review Title</Label>
          <Input
            id="title"
            value={formData.title || ''}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            placeholder="Best water purifier I've ever used!"
          />
        </div>
        <div className="col-span-2">
          <Label htmlFor="content">Review Content *</Label>
          <Textarea
            id="content"
            value={formData.content}
            onChange={(e) => setFormData({ ...formData, content: e.target.value })}
            placeholder="Share the customer's experience..."
            rows={4}
            required
          />
        </div>
        <div>
          <Label htmlFor="product_name">Product Name</Label>
          <Input
            id="product_name"
            value={formData.product_name || ''}
            onChange={(e) => setFormData({ ...formData, product_name: e.target.value })}
            placeholder="Aquapurite Pro 1000"
          />
        </div>
        <div>
          <Label htmlFor="product_id">Product ID</Label>
          <Input
            id="product_id"
            value={formData.product_id || ''}
            onChange={(e) => setFormData({ ...formData, product_id: e.target.value })}
            placeholder="Optional product UUID"
          />
        </div>
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
          {isLoading ? 'Saving...' : testimonial ? 'Update' : 'Create'}
        </Button>
      </div>
    </form>
  );
}

export default function TestimonialsPage() {
  const queryClient = useQueryClient();
  const [editingTestimonial, setEditingTestimonial] = useState<CMSTestimonial | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['cms-testimonials'],
    queryFn: () => cmsApi.testimonials.list(),
  });

  const createMutation = useMutation({
    mutationFn: cmsApi.testimonials.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-testimonials'] });
      setIsDialogOpen(false);
      toast.success('Testimonial created successfully');
    },
    onError: () => {
      toast.error('Failed to create testimonial');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CMSTestimonialCreate> }) =>
      cmsApi.testimonials.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-testimonials'] });
      setIsDialogOpen(false);
      setEditingTestimonial(null);
      toast.success('Testimonial updated successfully');
    },
    onError: () => {
      toast.error('Failed to update testimonial');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: cmsApi.testimonials.delete,
    // Optimistic update: immediately remove from UI
    onMutate: async (deletedId: string) => {
      await queryClient.cancelQueries({ queryKey: ['cms-testimonials'] });
      const previousTestimonials = queryClient.getQueryData(['cms-testimonials']);

      queryClient.setQueryData(['cms-testimonials'], (old: any) => {
        if (!old?.data?.items) return old;
        return {
          ...old,
          data: {
            ...old.data,
            items: old.data.items.filter((t: CMSTestimonial) => t.id !== deletedId),
          },
        };
      });

      return { previousTestimonials };
    },
    onSuccess: () => {
      toast.success('Testimonial deleted successfully');
    },
    onError: (_err, _deletedId, context) => {
      if (context?.previousTestimonials) {
        queryClient.setQueryData(['cms-testimonials'], context.previousTestimonials);
      }
      toast.error('Failed to delete testimonial');
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-testimonials'] });
    },
  });

  const testimonials = data?.data?.items || [];

  const handleSubmit = (formData: CMSTestimonialCreate) => {
    if (editingTestimonial) {
      updateMutation.mutate({ id: editingTestimonial.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleToggleActive = (id: string, active: boolean) => {
    updateMutation.mutate({ id, data: { is_active: active } });
  };

  const handleToggleFeatured = (id: string, featured: boolean) => {
    updateMutation.mutate({ id, data: { is_featured: featured } });
  };

  const featuredCount = testimonials.filter((t) => t.is_featured).length;
  const activeCount = testimonials.filter((t) => t.is_active).length;

  return (
    <div className="container mx-auto py-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Customer Testimonials</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {testimonials.length} total | {activeCount} active | {featuredCount} featured
            </p>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => setEditingTestimonial(null)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Testimonial
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>
                  {editingTestimonial ? 'Edit Testimonial' : 'Add Testimonial'}
                </DialogTitle>
              </DialogHeader>
              <TestimonialForm
                testimonial={editingTestimonial}
                onSubmit={handleSubmit}
                onCancel={() => {
                  setIsDialogOpen(false);
                  setEditingTestimonial(null);
                }}
                isLoading={createMutation.isPending || updateMutation.isPending}
              />
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading testimonials...
            </div>
          ) : testimonials.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <User className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No testimonials yet.</p>
              <p className="text-sm">Add customer reviews to showcase on your storefront.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {testimonials.map((testimonial) => (
                <TestimonialCard
                  key={testimonial.id}
                  testimonial={testimonial}
                  onEdit={(t) => {
                    setEditingTestimonial(t);
                    setIsDialogOpen(true);
                  }}
                  onDelete={(id) => deleteMutation.mutate(id)}
                  onToggleActive={handleToggleActive}
                  onToggleFeatured={handleToggleFeatured}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
