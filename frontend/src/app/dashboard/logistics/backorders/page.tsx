'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Clock, Package, AlertTriangle, CheckCircle, Calendar, DollarSign, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface Backorder {
  id: string;
  order_number: string;
  customer_name: string;
  product_name: string;
  product_sku: string;
  quantity_ordered: number;
  quantity_available: number;
  quantity_backordered: number;
  expected_date?: string;
  days_pending: number;
  order_value: number;
  status: 'PENDING' | 'PARTIAL_AVAILABLE' | 'READY' | 'CANCELLED';
  created_at: string;
}

interface BackorderStats {
  total_backorders: number;
  total_value: number;
  avg_wait_days: number;
  ready_to_ship: number;
}

const backordersApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/dom/backorders', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<BackorderStats> => {
    try {
      const { data } = await apiClient.get('/dom/stats');
      return {
        total_backorders: data.pending_backorders || 0,
        total_value: data.backorder_value || 0,
        avg_wait_days: data.avg_backorder_wait || 0,
        ready_to_ship: data.backorders_ready || 0
      };
    } catch {
      return { total_backorders: 0, total_value: 0, avg_wait_days: 0, ready_to_ship: 0 };
    }
  },
};

const columns: ColumnDef<Backorder>[] = [
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
          <div className="text-xs text-muted-foreground">{row.original.customer_name}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'product_name',
    header: 'Product',
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.product_name}</div>
        <div className="text-xs text-muted-foreground font-mono">{row.original.product_sku}</div>
      </div>
    ),
  },
  {
    accessorKey: 'quantity',
    header: 'Quantity',
    cell: ({ row }) => (
      <div className="text-sm">
        <div>Ordered: {row.original.quantity_ordered}</div>
        <div className="text-orange-600">Backordered: {row.original.quantity_backordered}</div>
      </div>
    ),
  },
  {
    accessorKey: 'expected_date',
    header: 'Expected',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Calendar className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">
          {row.original.expected_date
            ? new Date(row.original.expected_date).toLocaleDateString()
            : 'TBD'}
        </span>
      </div>
    ),
  },
  {
    accessorKey: 'days_pending',
    header: 'Days Waiting',
    cell: ({ row }) => {
      const days = row.original.days_pending;
      const color = days > 14 ? 'text-red-600' : days > 7 ? 'text-orange-600' : 'text-green-600';
      return (
        <div className="flex items-center gap-2">
          <Clock className={`h-4 w-4 ${color}`} />
          <span className={`font-medium ${color}`}>{days} days</span>
        </div>
      );
    },
  },
  {
    accessorKey: 'order_value',
    header: 'Value',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <DollarSign className="h-4 w-4 text-muted-foreground" />
        <span className="font-mono">${row.original.order_value.toFixed(2)}</span>
      </div>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

export default function BackordersPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['logistics-backorders', page, pageSize],
    queryFn: () => backordersApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['logistics-backorders-stats'],
    queryFn: backordersApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Backorders"
        description="Manage orders waiting for inventory availability"
        actions={
          <Button variant="outline">
            <Package className="mr-2 h-4 w-4" />
            Export Report
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Backorders</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_backorders || 0}</div>
            <p className="text-xs text-muted-foreground">Orders waiting</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">${(stats?.total_value || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Pending revenue</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Wait Time</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{stats?.avg_wait_days || 0} days</div>
            <p className="text-xs text-muted-foreground">Average</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ready to Ship</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.ready_to_ship || 0}</div>
            <p className="text-xs text-muted-foreground">Stock available</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="order_number"
        searchPlaceholder="Search backorders..."
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
