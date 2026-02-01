'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  MoreHorizontal,
  Warehouse,
  Package,
  CheckCircle,
  AlertTriangle,
  XCircle,
  RefreshCw,
  ArrowRight,
  Clock,
  MapPin
} from 'lucide-react';
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
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatDate, formatCurrency } from '@/lib/utils';

interface OrderAllocation {
  id: string;
  order_id: string;
  order_number: string;
  customer_name: string;
  customer_city: string;
  customer_state: string;
  customer_pincode: string;
  status: 'PENDING' | 'ALLOCATED' | 'PARTIALLY_ALLOCATED' | 'FAILED' | 'MANUAL_REQUIRED';
  warehouse_id?: string;
  warehouse_name?: string;
  total_items: number;
  allocated_items: number;
  total_quantity: number;
  allocated_quantity: number;
  order_value: number;
  allocation_score?: number;
  failure_reason?: string;
  created_at: string;
  allocated_at?: string;
}

interface AllocationStats {
  total_pending: number;
  allocated_today: number;
  failed_allocations: number;
  manual_required: number;
  avg_allocation_time_seconds: number;
}

interface WarehouseOption {
  id: string;
  name: string;
  code: string;
  city: string;
  available_stock: number;
}

const allocationApi = {
  list: async (params?: { page?: number; size?: number; status?: string }) => {
    try {
      const { data } = await apiClient.get('/orders/allocations', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<AllocationStats> => {
    try {
      const { data } = await apiClient.get('/orders/allocations/stats');
      return data;
    } catch {
      return {
        total_pending: 0,
        allocated_today: 0,
        failed_allocations: 0,
        manual_required: 0,
        avg_allocation_time_seconds: 0
      };
    }
  },
  getWarehouses: async (orderId: string): Promise<WarehouseOption[]> => {
    try {
      const { data } = await apiClient.get(`/orders/${orderId}/available-warehouses`);
      return data;
    } catch {
      return [];
    }
  },
  allocate: async (orderId: string, warehouseId: string) => {
    const { data } = await apiClient.post(`/orders/${orderId}/allocate`, { warehouse_id: warehouseId });
    return data;
  },
  autoAllocate: async (orderIds?: string[]) => {
    const { data } = await apiClient.post('/orders/allocations/auto-allocate', { order_ids: orderIds });
    return data;
  },
  retry: async (orderId: string) => {
    const { data } = await apiClient.post(`/orders/${orderId}/retry-allocation`);
    return data;
  },
};

const statusColors: Record<string, string> = {
  PENDING: 'bg-gray-100 text-gray-800',
  ALLOCATED: 'bg-green-100 text-green-800',
  PARTIALLY_ALLOCATED: 'bg-yellow-100 text-yellow-800',
  FAILED: 'bg-red-100 text-red-800',
  MANUAL_REQUIRED: 'bg-orange-100 text-orange-800',
};

const statusIcons: Record<string, React.ReactNode> = {
  PENDING: <Clock className="h-4 w-4" />,
  ALLOCATED: <CheckCircle className="h-4 w-4 text-green-600" />,
  PARTIALLY_ALLOCATED: <AlertTriangle className="h-4 w-4 text-yellow-600" />,
  FAILED: <XCircle className="h-4 w-4 text-red-600" />,
  MANUAL_REQUIRED: <AlertTriangle className="h-4 w-4 text-orange-600" />,
};

export default function OrderAllocationPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isAllocateDialogOpen, setIsAllocateDialogOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<OrderAllocation | null>(null);
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>('');
  const [isAutoAllocating, setIsAutoAllocating] = useState(false);

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['order-allocations', page, pageSize, statusFilter],
    queryFn: () => allocationApi.list({
      page: page + 1,
      size: pageSize,
      status: statusFilter !== 'all' ? statusFilter : undefined,
    }),
  });

  const { data: stats } = useQuery({
    queryKey: ['allocation-stats'],
    queryFn: allocationApi.getStats,
  });

  const { data: warehouses } = useQuery({
    queryKey: ['available-warehouses', selectedOrder?.order_id],
    queryFn: () => selectedOrder ? allocationApi.getWarehouses(selectedOrder.order_id) : Promise.resolve([]),
    enabled: !!selectedOrder,
  });

  const allocateMutation = useMutation({
    mutationFn: ({ orderId, warehouseId }: { orderId: string; warehouseId: string }) =>
      allocationApi.allocate(orderId, warehouseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order-allocations'] });
      queryClient.invalidateQueries({ queryKey: ['allocation-stats'] });
      setIsAllocateDialogOpen(false);
      setSelectedOrder(null);
      setSelectedWarehouse('');
      toast.success('Order allocated successfully');
    },
    onError: () => {
      toast.error('Failed to allocate order');
    },
  });

  const autoAllocateMutation = useMutation({
    mutationFn: () => allocationApi.autoAllocate(),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['order-allocations'] });
      queryClient.invalidateQueries({ queryKey: ['allocation-stats'] });
      setIsAutoAllocating(false);
      toast.success(`Auto-allocated ${result.allocated_count || 0} orders`);
    },
    onError: () => {
      setIsAutoAllocating(false);
      toast.error('Auto-allocation failed');
    },
  });

  const retryMutation = useMutation({
    mutationFn: (orderId: string) => allocationApi.retry(orderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order-allocations'] });
      toast.success('Allocation retry initiated');
    },
    onError: () => {
      toast.error('Retry failed');
    },
  });

  const handleAutoAllocate = () => {
    setIsAutoAllocating(true);
    autoAllocateMutation.mutate();
  };

  const handleManualAllocate = (order: OrderAllocation) => {
    setSelectedOrder(order);
    setIsAllocateDialogOpen(true);
  };

  const columns: ColumnDef<OrderAllocation>[] = [
    {
      accessorKey: 'order_number',
      header: 'Order',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Package className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="font-mono font-medium">{row.original.order_number}</div>
            <div className="text-sm text-muted-foreground">{row.original.customer_name}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'destination',
      header: 'Destination',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4 text-muted-foreground" />
          <div className="text-sm">
            <div>{row.original.customer_city}, {row.original.customer_state}</div>
            <div className="text-muted-foreground">{row.original.customer_pincode}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'items',
      header: 'Items',
      cell: ({ row }) => (
        <div className="text-sm">
          <div>{row.original.allocated_items} / {row.original.total_items} items</div>
          <div className="text-muted-foreground">
            {row.original.allocated_quantity} / {row.original.total_quantity} qty
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'order_value',
      header: 'Value',
      cell: ({ row }) => (
        <div className="font-medium">{formatCurrency(row.original.order_value)}</div>
      ),
    },
    {
      accessorKey: 'warehouse_name',
      header: 'Warehouse',
      cell: ({ row }) => (
        row.original.warehouse_name ? (
          <div className="flex items-center gap-2">
            <Warehouse className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{row.original.warehouse_name}</span>
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">Not assigned</span>
        )
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          {statusIcons[row.original.status]}
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[row.original.status] ?? 'bg-gray-100 text-gray-800'}`}>
            {row.original.status?.replace('_', ' ') ?? '-'}
          </span>
        </div>
      ),
    },
    {
      accessorKey: 'created_at',
      header: 'Order Date',
      cell: ({ row }) => (
        <div className="text-sm text-muted-foreground">
          {formatDate(row.original.created_at)}
        </div>
      ),
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
            {(row.original.status === 'PENDING' || row.original.status === 'MANUAL_REQUIRED') && (
              <DropdownMenuItem onClick={() => handleManualAllocate(row.original)}>
                <Warehouse className="mr-2 h-4 w-4" />
                Manual Allocate
              </DropdownMenuItem>
            )}
            {row.original.status === 'FAILED' && (
              <DropdownMenuItem onClick={() => retryMutation.mutate(row.original.order_id)}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry Allocation
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={() => toast.success(`Viewing order ${row.original.order_number}`)}>
              <ArrowRight className="mr-2 h-4 w-4" />
              View Order
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Order Allocation"
        description="Manage warehouse allocation for orders"
        actions={
          <Button onClick={handleAutoAllocate} disabled={isAutoAllocating}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isAutoAllocating ? 'animate-spin' : ''}`} />
            {isAutoAllocating ? 'Allocating...' : 'Auto Allocate All'}
          </Button>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <Clock className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_pending || 0}</div>
            <p className="text-xs text-muted-foreground">Awaiting allocation</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Allocated Today</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.allocated_today || 0}</div>
            <p className="text-xs text-muted-foreground">Successfully allocated</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.failed_allocations || 0}</div>
            <p className="text-xs text-muted-foreground">Needs attention</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Manual Required</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.manual_required || 0}</div>
            <p className="text-xs text-muted-foreground">Requires review</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.avg_allocation_time_seconds || 0}s</div>
            <p className="text-xs text-muted-foreground">Per allocation</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="ALLOCATED">Allocated</SelectItem>
            <SelectItem value="PARTIALLY_ALLOCATED">Partially Allocated</SelectItem>
            <SelectItem value="FAILED">Failed</SelectItem>
            <SelectItem value="MANUAL_REQUIRED">Manual Required</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="order_number"
        searchPlaceholder="Search orders..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Manual Allocation Dialog */}
      <Dialog open={isAllocateDialogOpen} onOpenChange={setIsAllocateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Manual Allocation</DialogTitle>
            <DialogDescription>
              Select a warehouse for order {selectedOrder?.order_number}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Destination</label>
              <p className="text-sm text-muted-foreground">
                {selectedOrder?.customer_city}, {selectedOrder?.customer_state} - {selectedOrder?.customer_pincode}
              </p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Select Warehouse</label>
              <Select value={selectedWarehouse} onValueChange={setSelectedWarehouse}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {warehouses?.map((wh) => (
                    <SelectItem key={wh.id} value={wh.id}>
                      <div className="flex items-center justify-between w-full">
                        <span>{wh.name} ({wh.code})</span>
                        <span className="text-muted-foreground ml-4">{wh.city}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {selectedOrder?.failure_reason && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-red-600">Previous Failure Reason</label>
                <p className="text-sm text-muted-foreground bg-red-50 p-2 rounded">
                  {selectedOrder.failure_reason}
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAllocateDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => selectedOrder && allocateMutation.mutate({
                orderId: selectedOrder.order_id,
                warehouseId: selectedWarehouse
              })}
              disabled={!selectedWarehouse || allocateMutation.isPending}
            >
              {allocateMutation.isPending ? 'Allocating...' : 'Allocate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
