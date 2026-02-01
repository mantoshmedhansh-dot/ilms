'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Gift, Percent, Tag, Calendar, Eye } from 'lucide-react';
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
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { promotionsApi } from '@/lib/api';
import { formatDate, formatCurrency } from '@/lib/utils';
import { toast } from 'sonner';

interface Promotion {
  id: string;
  name: string;
  code: string;
  type: 'PERCENTAGE' | 'FIXED_AMOUNT' | 'BUY_X_GET_Y' | 'FREE_SHIPPING' | 'BUNDLE';
  discount_value: number;
  min_order_value?: number;
  max_discount?: number;
  usage_limit?: number;
  usage_count: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
  applicable_to: 'ALL' | 'PRODUCTS' | 'CATEGORIES' | 'CUSTOMERS';
  created_at: string;
}

const typeIcons: Record<string, React.ReactNode> = {
  PERCENTAGE: <Percent className="h-4 w-4" />,
  FIXED_AMOUNT: <Tag className="h-4 w-4" />,
  BUY_X_GET_Y: <Gift className="h-4 w-4" />,
  FREE_SHIPPING: <Gift className="h-4 w-4" />,
  BUNDLE: <Gift className="h-4 w-4" />,
};

const promotionTypes = [
  { value: 'PERCENTAGE', label: 'Percentage Discount' },
  { value: 'FIXED_AMOUNT', label: 'Fixed Amount' },
  { value: 'BUY_X_GET_Y', label: 'Buy X Get Y' },
  { value: 'FREE_SHIPPING', label: 'Free Shipping' },
  { value: 'BUNDLE', label: 'Bundle Deal' },
];

const applicableOptions = [
  { value: 'ALL', label: 'All Products' },
  { value: 'PRODUCTS', label: 'Specific Products' },
  { value: 'CATEGORIES', label: 'Specific Categories' },
  { value: 'CUSTOMERS', label: 'Specific Customers' },
];

export default function PromotionsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDetailsSheetOpen, setIsDetailsSheetOpen] = useState(false);
  const [selectedPromotion, setSelectedPromotion] = useState<Promotion | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    code: '',
    type: 'PERCENTAGE',
    discount_value: 0,
    min_order_value: 0,
    max_discount: 0,
    usage_limit: 0,
    start_date: '',
    end_date: '',
    is_active: true,
    applicable_to: 'ALL',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['promotions', page, pageSize],
    queryFn: () => promotionsApi.list({ page: page + 1, size: pageSize }),
  });

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => promotionsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['promotions'] });
      setIsCreateDialogOpen(false);
      resetForm();
      toast.success('Promotion created successfully');
    },
    onError: () => {
      toast.error('Failed to create promotion');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: typeof formData }) => promotionsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['promotions'] });
      setIsEditDialogOpen(false);
      setSelectedPromotion(null);
      resetForm();
      toast.success('Promotion updated successfully');
    },
    onError: () => {
      toast.error('Failed to update promotion');
    },
  });

  const resetForm = () => {
    setFormData({
      name: '',
      code: '',
      type: 'PERCENTAGE',
      discount_value: 0,
      min_order_value: 0,
      max_discount: 0,
      usage_limit: 0,
      start_date: '',
      end_date: '',
      is_active: true,
      applicable_to: 'ALL',
    });
  };

  const handleViewDetails = (promotion: Promotion) => {
    setSelectedPromotion(promotion);
    setIsDetailsSheetOpen(true);
  };

  const handleEdit = (promotion: Promotion) => {
    setSelectedPromotion(promotion);
    setFormData({
      name: promotion.name,
      code: promotion.code,
      type: promotion.type,
      discount_value: promotion.discount_value,
      min_order_value: promotion.min_order_value || 0,
      max_discount: promotion.max_discount || 0,
      usage_limit: promotion.usage_limit || 0,
      start_date: promotion.start_date ? promotion.start_date.split('T')[0] : '',
      end_date: promotion.end_date ? promotion.end_date.split('T')[0] : '',
      is_active: promotion.is_active,
      applicable_to: promotion.applicable_to,
    });
    setIsEditDialogOpen(true);
  };

  const handleCreateSubmit = () => {
    if (!formData.name || !formData.code) {
      toast.error('Please enter name and code');
      return;
    }
    createMutation.mutate(formData);
  };

  const handleEditSubmit = () => {
    if (!selectedPromotion || !formData.name || !formData.code) {
      toast.error('Please enter name and code');
      return;
    }
    updateMutation.mutate({ id: selectedPromotion.id, data: formData });
  };

  const generateCode = () => {
    const code = `PROMO${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
    setFormData({ ...formData, code });
  };

  const columns: ColumnDef<Promotion>[] = [
    {
      accessorKey: 'name',
      header: 'Promotion',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            {typeIcons[row.original.type] || <Gift className="h-5 w-5 text-muted-foreground" />}
          </div>
          <div>
            <div className="font-medium">{row.original.name}</div>
            <div className="font-mono text-sm text-muted-foreground">{row.original.code}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'discount',
      header: 'Discount',
      cell: ({ row }) => (
        <div className="text-sm">
          <div className="font-medium text-green-600">
            {row.original.type === 'PERCENTAGE'
              ? `${row.original.discount_value}%`
              : formatCurrency(row.original.discount_value)}
          </div>
          {row.original.max_discount && (
            <div className="text-muted-foreground text-xs">
              Max: {formatCurrency(row.original.max_discount)}
            </div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'min_order_value',
      header: 'Min Order',
      cell: ({ row }) => (
        <span className="text-sm">
          {row.original.min_order_value
            ? formatCurrency(row.original.min_order_value)
            : 'No minimum'}
        </span>
      ),
    },
    {
      accessorKey: 'usage',
      header: 'Usage',
      cell: ({ row }) => (
        <div className="text-sm">
          <div className="font-medium">{row.original.usage_count}</div>
          <div className="text-muted-foreground text-xs">
            {row.original.usage_limit ? `of ${row.original.usage_limit}` : 'Unlimited'}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'validity',
      header: 'Valid Period',
      cell: ({ row }) => (
        <div className="flex items-center gap-1 text-sm">
          <Calendar className="h-3 w-3 text-muted-foreground" />
          <div>
            <div>{formatDate(row.original.start_date)}</div>
            <div className="text-muted-foreground">to {formatDate(row.original.end_date)}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'is_active',
      header: 'Status',
      cell: ({ row }) => {
        const now = new Date();
        const endDate = new Date(row.original.end_date);
        const isExpired = endDate < now;
        return (
          <StatusBadge
            status={isExpired ? 'EXPIRED' : row.original.is_active ? 'ACTIVE' : 'INACTIVE'}
          />
        );
      },
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => handleViewDetails(row.original)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleEdit(row.original)}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const PromotionForm = () => (
    <div className="grid gap-4 py-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">Name *</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Enter promotion name"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="code">Code *</Label>
          <div className="flex gap-2">
            <Input
              id="code"
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              placeholder="PROMO20"
              className="font-mono"
            />
            <Button type="button" variant="outline" onClick={generateCode}>
              Generate
            </Button>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="type">Type</Label>
          <Select
            value={formData.type}
            onValueChange={(value) => setFormData({ ...formData, type: value })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select type" />
            </SelectTrigger>
            <SelectContent>
              {promotionTypes.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="discount_value">
            {formData.type === 'PERCENTAGE' ? 'Discount (%)' : 'Discount Amount'}
          </Label>
          <Input
            id="discount_value"
            type="number"
            min={0}
            value={formData.discount_value}
            onChange={(e) => setFormData({ ...formData, discount_value: parseFloat(e.target.value) || 0 })}
            placeholder={formData.type === 'PERCENTAGE' ? '10' : '500'}
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="min_order_value">Minimum Order Value</Label>
          <Input
            id="min_order_value"
            type="number"
            min={0}
            value={formData.min_order_value}
            onChange={(e) => setFormData({ ...formData, min_order_value: parseFloat(e.target.value) || 0 })}
            placeholder="0"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="max_discount">Maximum Discount</Label>
          <Input
            id="max_discount"
            type="number"
            min={0}
            value={formData.max_discount}
            onChange={(e) => setFormData({ ...formData, max_discount: parseFloat(e.target.value) || 0 })}
            placeholder="0"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="start_date">Start Date</Label>
          <Input
            id="start_date"
            type="date"
            value={formData.start_date}
            onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="end_date">End Date</Label>
          <Input
            id="end_date"
            type="date"
            value={formData.end_date}
            onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="usage_limit">Usage Limit (0 = unlimited)</Label>
          <Input
            id="usage_limit"
            type="number"
            min={0}
            value={formData.usage_limit}
            onChange={(e) => setFormData({ ...formData, usage_limit: parseInt(e.target.value) || 0 })}
            placeholder="0"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="applicable_to">Applicable To</Label>
          <Select
            value={formData.applicable_to}
            onValueChange={(value) => setFormData({ ...formData, applicable_to: value })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select scope" />
            </SelectTrigger>
            <SelectContent>
              {applicableOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="flex items-center gap-2 pt-2">
        <Switch
          id="is_active"
          checked={formData.is_active}
          onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
        />
        <Label htmlFor="is_active">Active</Label>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Promotions"
        description="Manage discount codes and promotional offers"
        actions={
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Promotion
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="code"
        searchPlaceholder="Search promotions..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Create Promotion Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create Promotion</DialogTitle>
            <DialogDescription>
              Create a new promotional offer or discount code
            </DialogDescription>
          </DialogHeader>
          <PromotionForm />
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsCreateDialogOpen(false); resetForm(); }}>
              Cancel
            </Button>
            <Button onClick={handleCreateSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Promotion'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Promotion Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Promotion</DialogTitle>
            <DialogDescription>
              Update promotion details
            </DialogDescription>
          </DialogHeader>
          <PromotionForm />
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsEditDialogOpen(false); resetForm(); setSelectedPromotion(null); }}>
              Cancel
            </Button>
            <Button onClick={handleEditSubmit} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Details Sheet */}
      <Sheet open={isDetailsSheetOpen} onOpenChange={setIsDetailsSheetOpen}>
        <SheetContent className="w-[500px] sm:w-[600px]">
          <SheetHeader>
            <SheetTitle>Promotion Details</SheetTitle>
            <SheetDescription>
              {selectedPromotion?.code}
            </SheetDescription>
          </SheetHeader>
          {selectedPromotion && (
            <div className="mt-6 space-y-6">
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-muted">
                  {typeIcons[selectedPromotion.type] || <Gift className="h-8 w-8 text-muted-foreground" />}
                </div>
                <div>
                  <h3 className="text-lg font-semibold">{selectedPromotion.name}</h3>
                  <p className="font-mono text-muted-foreground">{selectedPromotion.code}</p>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                {(() => {
                  const now = new Date();
                  const endDate = new Date(selectedPromotion.end_date);
                  const isExpired = endDate < now;
                  return (
                    <StatusBadge
                      status={isExpired ? 'EXPIRED' : selectedPromotion.is_active ? 'ACTIVE' : 'INACTIVE'}
                    />
                  );
                })()}
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium">Discount Details</h4>
                <div className="rounded-lg border p-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Type</span>
                    <span className="text-sm font-medium capitalize">{selectedPromotion.type.replace(/_/g, ' ').toLowerCase()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Discount</span>
                    <span className="text-sm font-medium text-green-600">
                      {selectedPromotion.type === 'PERCENTAGE'
                        ? `${selectedPromotion.discount_value}%`
                        : formatCurrency(selectedPromotion.discount_value)}
                    </span>
                  </div>
                  {selectedPromotion.min_order_value && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Min Order</span>
                      <span className="text-sm">{formatCurrency(selectedPromotion.min_order_value)}</span>
                    </div>
                  )}
                  {selectedPromotion.max_discount && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Max Discount</span>
                      <span className="text-sm">{formatCurrency(selectedPromotion.max_discount)}</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium">Usage & Validity</h4>
                <div className="rounded-lg border p-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Usage</span>
                    <span className="text-sm">
                      {selectedPromotion.usage_count} {selectedPromotion.usage_limit ? `/ ${selectedPromotion.usage_limit}` : '(unlimited)'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Valid From</span>
                    <span className="text-sm">{formatDate(selectedPromotion.start_date)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Valid Until</span>
                    <span className="text-sm">{formatDate(selectedPromotion.end_date)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Applicable To</span>
                    <span className="text-sm capitalize">{selectedPromotion.applicable_to.toLowerCase()}</span>
                  </div>
                </div>
              </div>

              <Button
                className="w-full"
                variant="outline"
                onClick={() => {
                  setIsDetailsSheetOpen(false);
                  handleEdit(selectedPromotion);
                }}
              >
                <Pencil className="mr-2 h-4 w-4" />
                Edit Promotion
              </Button>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
