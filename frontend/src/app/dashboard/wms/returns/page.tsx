'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { RotateCcw, Plus, Package, CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import apiClient from '@/lib/api/client';

interface ReturnOrder {
  id: string;
  return_number: string;
  order_number: string;
  customer_name: string;
  return_reason: 'DAMAGED' | 'WRONG_ITEM' | 'NOT_AS_DESCRIBED' | 'CHANGED_MIND' | 'DEFECTIVE' | 'OTHER';
  items_count: number;
  total_value: number;
  disposition?: 'RESTOCK' | 'REPAIR' | 'DISPOSE' | 'RETURN_TO_VENDOR';
  status: 'PENDING' | 'RECEIVED' | 'INSPECTING' | 'PROCESSED' | 'REFUNDED' | 'REJECTED';
  received_at?: string;
  created_at: string;
  notes?: string;
}

interface ReturnsStats {
  total_returns: number;
  pending_receipt: number;
  in_inspection: number;
  processed_today: number;
}

interface CreateRMAPayload {
  order_number: string;
  customer_name: string;
  return_reason: ReturnOrder['return_reason'];
  items_count: number;
  notes?: string;
}

const returnsApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/returns/rma', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<ReturnsStats> => {
    try {
      const { data } = await apiClient.get('/returns/rma/stats');
      return data;
    } catch {
      return { total_returns: 0, pending_receipt: 0, in_inspection: 0, processed_today: 0 };
    }
  },
  create: async (payload: CreateRMAPayload) => {
    const { data } = await apiClient.post('/returns/rma', payload);
    return data;
  },
};

const returnReasons = [
  { label: 'Damaged', value: 'DAMAGED' },
  { label: 'Wrong Item', value: 'WRONG_ITEM' },
  { label: 'Not As Described', value: 'NOT_AS_DESCRIBED' },
  { label: 'Changed Mind', value: 'CHANGED_MIND' },
  { label: 'Defective', value: 'DEFECTIVE' },
  { label: 'Other', value: 'OTHER' },
];

const reasonColors: Record<string, string> = {
  DAMAGED: 'bg-red-100 text-red-800',
  WRONG_ITEM: 'bg-orange-100 text-orange-800',
  NOT_AS_DESCRIBED: 'bg-yellow-100 text-yellow-800',
  CHANGED_MIND: 'bg-blue-100 text-blue-800',
  DEFECTIVE: 'bg-purple-100 text-purple-800',
  OTHER: 'bg-gray-100 text-gray-800',
};

const columns: ColumnDef<ReturnOrder>[] = [
  {
    accessorKey: 'return_number',
    header: 'Return',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <RotateCcw className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.return_number}</div>
          <div className="text-xs text-muted-foreground">Order: {row.original.order_number}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'customer_name',
    header: 'Customer',
    cell: ({ row }) => (
      <div className="font-medium">{row.original.customer_name}</div>
    ),
  },
  {
    accessorKey: 'return_reason',
    header: 'Reason',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${reasonColors[row.original.return_reason]}`}>
        {row.original.return_reason.replace(/_/g, ' ')}
      </span>
    ),
  },
  {
    accessorKey: 'items_count',
    header: 'Items',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Package className="h-4 w-4 text-muted-foreground" />
        <span>{row.original.items_count}</span>
      </div>
    ),
  },
  {
    accessorKey: 'total_value',
    header: 'Value',
    cell: ({ row }) => (
      <span className="font-mono">${row.original.total_value.toFixed(2)}</span>
    ),
  },
  {
    accessorKey: 'disposition',
    header: 'Disposition',
    cell: ({ row }) => (
      <span className="text-sm">{row.original.disposition?.replace(/_/g, ' ') || 'Pending'}</span>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

export default function ReturnsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newRMA, setNewRMA] = useState<{
    order_number: string;
    customer_name: string;
    return_reason: ReturnOrder['return_reason'];
    items_count: string;
    notes: string;
  }>({
    order_number: '',
    customer_name: '',
    return_reason: 'DAMAGED',
    items_count: '1',
    notes: '',
  });

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['wms-returns', page, pageSize],
    queryFn: () => returnsApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-returns-stats'],
    queryFn: returnsApi.getStats,
  });

  const createMutation = useMutation({
    mutationFn: returnsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-returns'] });
      queryClient.invalidateQueries({ queryKey: ['wms-returns-stats'] });
      toast.success('RMA created successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create RMA');
    },
  });

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setNewRMA({
      order_number: '',
      customer_name: '',
      return_reason: 'DAMAGED',
      items_count: '1',
      notes: '',
    });
  };

  const handleSubmit = () => {
    if (!newRMA.order_number.trim()) {
      toast.error('Order number is required');
      return;
    }
    if (!newRMA.customer_name.trim()) {
      toast.error('Customer name is required');
      return;
    }
    if (!newRMA.items_count || parseInt(newRMA.items_count) < 1) {
      toast.error('At least 1 item is required');
      return;
    }

    createMutation.mutate({
      order_number: newRMA.order_number,
      customer_name: newRMA.customer_name,
      return_reason: newRMA.return_reason,
      items_count: parseInt(newRMA.items_count),
      notes: newRMA.notes || undefined,
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Returns Management"
        description="Process customer returns and manage reverse logistics"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create RMA
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create New RMA</DialogTitle>
            <DialogDescription>
              Create a Return Merchandise Authorization for a customer return.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="order_number">Order Number *</Label>
              <Input
                id="order_number"
                placeholder="e.g., ORD-2024-001"
                value={newRMA.order_number}
                onChange={(e) =>
                  setNewRMA({ ...newRMA, order_number: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="customer_name">Customer Name *</Label>
              <Input
                id="customer_name"
                placeholder="Enter customer name"
                value={newRMA.customer_name}
                onChange={(e) =>
                  setNewRMA({ ...newRMA, customer_name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="return_reason">Reason *</Label>
              <Select
                value={newRMA.return_reason}
                onValueChange={(value: ReturnOrder['return_reason']) =>
                  setNewRMA({ ...newRMA, return_reason: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select reason" />
                </SelectTrigger>
                <SelectContent>
                  {returnReasons.map((reason) => (
                    <SelectItem key={reason.value} value={reason.value}>
                      {reason.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="items_count">Number of Items *</Label>
              <Input
                id="items_count"
                type="number"
                min="1"
                placeholder="1"
                value={newRMA.items_count}
                onChange={(e) =>
                  setNewRMA({ ...newRMA, items_count: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                placeholder="Additional notes about the return..."
                value={newRMA.notes}
                onChange={(e) =>
                  setNewRMA({ ...newRMA, notes: e.target.value })
                }
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleDialogClose}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create RMA'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Returns</CardTitle>
            <RotateCcw className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_returns || 0}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Receipt</CardTitle>
            <Clock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.pending_receipt || 0}</div>
            <p className="text-xs text-muted-foreground">Awaiting delivery</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Inspection</CardTitle>
            <AlertTriangle className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.in_inspection || 0}</div>
            <p className="text-xs text-muted-foreground">Being reviewed</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Processed Today</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.processed_today || 0}</div>
            <p className="text-xs text-muted-foreground">Completed</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="return_number"
        searchPlaceholder="Search returns..."
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
