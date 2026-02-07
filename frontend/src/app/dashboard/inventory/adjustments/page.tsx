'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  Plus,
  Package,
  Warehouse,
  TrendingUp,
  TrendingDown,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  Filter,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { warehousesApi, productsApi, inventoryApi } from '@/lib/api';
import apiClient from '@/lib/api/client';
import { formatDate } from '@/lib/utils';

interface StockAdjustment {
  id: string;
  adjustment_number: string;
  product_id: string;
  product?: { name: string; sku: string };
  warehouse_id: string;
  warehouse?: { name: string; code: string };
  adjustment_type: 'INCREASE' | 'DECREASE';
  quantity: number;
  reason: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  notes?: string;
  created_at: string;
  created_by?: { name: string };
}

interface WarehouseOption {
  id: string;
  name: string;
  code: string;
}

interface ProductOption {
  id: string;
  name: string;
  sku: string;
}

const adjustmentReasons = [
  { label: 'Damaged', value: 'DAMAGED' },
  { label: 'Expired', value: 'EXPIRED' },
  { label: 'Lost/Missing', value: 'LOST' },
  { label: 'Theft', value: 'THEFT' },
  { label: 'Audit Correction', value: 'AUDIT' },
  { label: 'Return to Stock', value: 'RETURN' },
  { label: 'Found/Recovered', value: 'FOUND' },
  { label: 'Production/Manufacturing', value: 'PRODUCTION' },
  { label: 'Quality Check Failure', value: 'QC_FAIL' },
  { label: 'Other', value: 'OTHER' },
];

const adjustmentsApi = {
  list: async (params?: { page?: number; size?: number; status?: string; warehouse_id?: string; adjustment_type?: string }) => {
    try {
      const { data } = await apiClient.get('/inventory/adjustments', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  create: async (adjustment: { product_id: string; warehouse_id: string; adjustment_type: string; quantity: number; reason: string; notes?: string }) => {
    const { data } = await apiClient.post('/inventory/adjustments', adjustment);
    return data;
  },
};

export default function StockAdjustmentsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    product_id: '',
    warehouse_id: '',
    adjustment_type: 'DECREASE',
    quantity: 1,
    reason: '',
    notes: '',
  });

  // Fetch adjustments
  const { data, isLoading } = useQuery({
    queryKey: ['stock-adjustments', page, pageSize, statusFilter, typeFilter],
    queryFn: () =>
      adjustmentsApi.list({
        page: page + 1,
        size: pageSize,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        adjustment_type: typeFilter !== 'all' ? typeFilter : undefined,
      }),
  });

  // Fetch warehouses and products for dropdown
  const { data: warehousesData } = useQuery({
    queryKey: ['warehouses-dropdown'],
    queryFn: () => warehousesApi.list({ size: 100 }),
  });

  const { data: productsData } = useQuery({
    queryKey: ['products-dropdown'],
    queryFn: () => productsApi.list({ size: 100 }),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: adjustmentsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stock-adjustments'] });
      queryClient.invalidateQueries({ queryKey: ['stock-items'] });
      queryClient.invalidateQueries({ queryKey: ['inventory-stats'] });
      toast.success('Stock adjustment created successfully');
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create adjustment');
    },
  });

  const resetForm = () => {
    setFormData({
      product_id: '',
      warehouse_id: '',
      adjustment_type: 'DECREASE',
      quantity: 1,
      reason: '',
      notes: '',
    });
    setIsDialogOpen(false);
  };

  const handleSubmit = () => {
    if (!formData.product_id || !formData.warehouse_id || !formData.reason) {
      toast.error('Please fill in all required fields');
      return;
    }
    if (formData.quantity < 1) {
      toast.error('Quantity must be at least 1');
      return;
    }

    createMutation.mutate({
      product_id: formData.product_id,
      warehouse_id: formData.warehouse_id,
      adjustment_type: formData.adjustment_type,
      quantity: formData.quantity,
      reason: formData.reason,
      notes: formData.notes || undefined,
    });
  };

  const columns: ColumnDef<StockAdjustment>[] = [
    {
      accessorKey: 'adjustment_number',
      header: 'Adjustment #',
      cell: ({ row }) => (
        <span className="font-medium font-mono">{row.original.adjustment_number || row.original.id?.slice(0, 8)?.toUpperCase() || '-'}</span>
      ),
    },
    {
      accessorKey: 'product',
      header: 'Product',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Package className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium">{row.original.product?.name || 'Unknown'}</div>
            <div className="text-sm text-muted-foreground font-mono">
              {row.original.product?.sku || '-'}
            </div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'warehouse',
      header: 'Warehouse',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Warehouse className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm">{row.original.warehouse?.name || 'Unknown'}</span>
        </div>
      ),
    },
    {
      accessorKey: 'adjustment_type',
      header: 'Type',
      cell: ({ row }) => {
        const isIncrease = row.original.adjustment_type === 'INCREASE';
        return (
          <div className={`flex items-center gap-1 ${isIncrease ? 'text-green-600' : 'text-red-600'}`}>
            {isIncrease ? (
              <TrendingUp className="h-4 w-4" />
            ) : (
              <TrendingDown className="h-4 w-4" />
            )}
            <span className="text-sm font-medium">{isIncrease ? 'Increase' : 'Decrease'}</span>
          </div>
        );
      },
    },
    {
      accessorKey: 'quantity',
      header: 'Quantity',
      cell: ({ row }) => {
        const isIncrease = row.original.adjustment_type === 'INCREASE';
        return (
          <span className={`font-mono font-medium ${isIncrease ? 'text-green-600' : 'text-red-600'}`}>
            {isIncrease ? '+' : '-'}{row.original.quantity}
          </span>
        );
      },
    },
    {
      accessorKey: 'reason',
      header: 'Reason',
      cell: ({ row }) => (
        <span className="text-sm">{row.original.reason?.replace('_', ' ') ?? '-'}</span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'created_at',
      header: 'Created',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {formatDate(row.original.created_at)}
        </span>
      ),
    },
  ];

  const warehouses: WarehouseOption[] = warehousesData?.items ?? [];
  const products: ProductOption[] = productsData?.items ?? [];
  const adjustments = data?.items ?? [];

  // Calculate stats
  const pendingCount = adjustments.filter((a: StockAdjustment) => a.status === 'PENDING').length;
  const increaseCount = adjustments.filter((a: StockAdjustment) => a.adjustment_type === 'INCREASE').length;
  const decreaseCount = adjustments.filter((a: StockAdjustment) => a.adjustment_type === 'DECREASE').length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Stock Adjustments"
        description="Adjust inventory levels for damaged, lost, or found items"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Adjustment
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Stock Adjustment</DialogTitle>
            <DialogDescription>
              Adjust inventory levels for a specific product in a warehouse
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Warehouse *</Label>
              <Select
                value={formData.warehouse_id}
                onValueChange={(value) => setFormData({ ...formData, warehouse_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {warehouses.map((wh) => (
                    <SelectItem key={wh.id} value={wh.id}>
                      {wh.name} ({wh.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Product *</Label>
              <Select
                value={formData.product_id}
                onValueChange={(value) => setFormData({ ...formData, product_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select product" />
                </SelectTrigger>
                <SelectContent>
                  {products.map((prod) => (
                    <SelectItem key={prod.id} value={prod.id}>
                      {prod.name} ({prod.sku})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Adjustment Type *</Label>
                <Select
                  value={formData.adjustment_type}
                  onValueChange={(value) => setFormData({ ...formData, adjustment_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DECREASE">
                      <div className="flex items-center gap-2 text-red-600">
                        <TrendingDown className="h-4 w-4" />
                        Decrease
                      </div>
                    </SelectItem>
                    <SelectItem value="INCREASE">
                      <div className="flex items-center gap-2 text-green-600">
                        <TrendingUp className="h-4 w-4" />
                        Increase
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Quantity *</Label>
                <Input
                  type="number"
                  min="1"
                  value={formData.quantity}
                  onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) || 1 })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Reason *</Label>
              <Select
                value={formData.reason}
                onValueChange={(value) => setFormData({ ...formData, reason: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select reason" />
                </SelectTrigger>
                <SelectContent>
                  {adjustmentReasons.map((reason) => (
                    <SelectItem key={reason.value} value={reason.value}>
                      {reason.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                placeholder="Additional notes (optional)"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={resetForm}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Adjustment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Adjustments</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data?.total ?? adjustments.length}</div>
            <p className="text-xs text-muted-foreground">All time adjustments</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Approval</CardTitle>
            <Clock className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{pendingCount}</div>
            <p className="text-xs text-muted-foreground">Awaiting approval</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Increases</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{increaseCount}</div>
            <p className="text-xs text-muted-foreground">Stock additions</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Decreases</CardTitle>
            <TrendingDown className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{decreaseCount}</div>
            <p className="text-xs text-muted-foreground">Stock reductions</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Filters:</span>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="APPROVED">Approved</SelectItem>
            <SelectItem value="REJECTED">Rejected</SelectItem>
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="INCREASE">Increase</SelectItem>
            <SelectItem value="DECREASE">Decrease</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={adjustments}
        searchKey="product"
        searchPlaceholder="Search adjustments..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />
    </div>
  );
}
