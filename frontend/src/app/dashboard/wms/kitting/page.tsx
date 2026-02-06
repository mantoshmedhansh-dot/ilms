'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Box, Plus, Package, CheckCircle, Clock, Layers } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface KitOrder {
  id: string;
  kit_number: string;
  kit_name: string;
  kit_sku: string;
  quantity_ordered: number;
  quantity_completed: number;
  components_count: number;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'ON_HOLD' | 'CANCELLED';
  assigned_to?: string;
  due_date?: string;
  created_at: string;
  completed_at?: string;
}

interface KittingStats {
  total_kits: number;
  in_progress: number;
  completed_today: number;
  pending_components: number;
}

const kittingApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/kitting/orders', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<KittingStats> => {
    try {
      const { data } = await apiClient.get('/kitting/stats');
      return data;
    } catch {
      return { total_kits: 0, in_progress: 0, completed_today: 0, pending_components: 0 };
    }
  },
};

const priorityColors: Record<string, string> = {
  LOW: 'bg-gray-100 text-gray-800',
  MEDIUM: 'bg-blue-100 text-blue-800',
  HIGH: 'bg-orange-100 text-orange-800',
  URGENT: 'bg-red-100 text-red-800',
};

const columns: ColumnDef<KitOrder>[] = [
  {
    accessorKey: 'kit_number',
    header: 'Kit Order',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Box className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.kit_number}</div>
          <div className="text-xs text-muted-foreground">{row.original.kit_name}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'kit_sku',
    header: 'SKU',
    cell: ({ row }) => (
      <span className="font-mono text-sm">{row.original.kit_sku}</span>
    ),
  },
  {
    accessorKey: 'priority',
    header: 'Priority',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${priorityColors[row.original.priority]}`}>
        {row.original.priority}
      </span>
    ),
  },
  {
    accessorKey: 'progress',
    header: 'Progress',
    cell: ({ row }) => {
      const progress = row.original.quantity_ordered > 0
        ? (row.original.quantity_completed / row.original.quantity_ordered) * 100
        : 0;
      return (
        <div className="space-y-1">
          <div className="text-sm">{row.original.quantity_completed} / {row.original.quantity_ordered}</div>
          <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-green-500" style={{ width: `${progress}%` }} />
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'components_count',
    header: 'Components',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Layers className="h-4 w-4 text-muted-foreground" />
        <span>{row.original.components_count}</span>
      </div>
    ),
  },
  {
    accessorKey: 'due_date',
    header: 'Due Date',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">
          {row.original.due_date ? new Date(row.original.due_date).toLocaleDateString() : '-'}
        </span>
      </div>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

export default function KittingPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['wms-kitting', page, pageSize],
    queryFn: () => kittingApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-kitting-stats'],
    queryFn: kittingApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Kitting & Assembly"
        description="Manage kit assembly orders and component bundling"
        actions={
          <Button onClick={() => toast.info('Feature coming soon')}>
            <Plus className="mr-2 h-4 w-4" />
            Create Kit Order
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Kit Orders</CardTitle>
            <Box className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_kits || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Progress</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.in_progress || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed Today</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.completed_today || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Components</CardTitle>
            <Package className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.pending_components || 0}</div>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="kit_number"
        searchPlaceholder="Search kit orders..."
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
