'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { RotateCcw, Plus, Package, CheckCircle, Clock, AlertTriangle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
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

const returnsApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/returns/', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<ReturnsStats> => {
    try {
      const { data } = await apiClient.get('/returns/stats');
      return data;
    } catch {
      return { total_returns: 0, pending_receipt: 0, in_inspection: 0, processed_today: 0 };
    }
  },
};

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

  const { data, isLoading } = useQuery({
    queryKey: ['wms-returns', page, pageSize],
    queryFn: () => returnsApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-returns-stats'],
    queryFn: returnsApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Returns Management"
        description="Process customer returns and manage reverse logistics"
        actions={
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create RMA
          </Button>
        }
      />

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
