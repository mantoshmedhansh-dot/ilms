'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { ClipboardList, Plus, CheckCircle, XCircle, Clock, BarChart3, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface CycleCount {
  id: string;
  count_number: string;
  count_type: 'FULL' | 'ABC' | 'RANDOM' | 'ZONE' | 'SKU';
  zone_name?: string;
  locations_total: number;
  locations_counted: number;
  items_counted: number;
  variances_found: number;
  variance_value: number;
  assigned_to?: string;
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'REVIEW';
  scheduled_date: string;
  started_at?: string;
  completed_at?: string;
  accuracy_rate?: number;
}

interface CycleCountStats {
  total_counts: number;
  in_progress: number;
  avg_accuracy: number;
  variances_pending: number;
}

const cycleCountApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/cycle-count/', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<CycleCountStats> => {
    try {
      const { data } = await apiClient.get('/cycle-count/stats');
      return data;
    } catch {
      return { total_counts: 0, in_progress: 0, avg_accuracy: 0, variances_pending: 0 };
    }
  },
};

const countTypeColors: Record<string, string> = {
  FULL: 'bg-purple-100 text-purple-800',
  ABC: 'bg-blue-100 text-blue-800',
  RANDOM: 'bg-green-100 text-green-800',
  ZONE: 'bg-orange-100 text-orange-800',
  SKU: 'bg-cyan-100 text-cyan-800',
};

const columns: ColumnDef<CycleCount>[] = [
  {
    accessorKey: 'count_number',
    header: 'Count',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <ClipboardList className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.count_number}</div>
          <div className="text-xs text-muted-foreground">
            {new Date(row.original.scheduled_date).toLocaleDateString()}
          </div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'count_type',
    header: 'Type',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${countTypeColors[row.original.count_type]}`}>
        {row.original.count_type}
      </span>
    ),
  },
  {
    accessorKey: 'progress',
    header: 'Progress',
    cell: ({ row }) => {
      const progress = row.original.locations_total > 0
        ? (row.original.locations_counted / row.original.locations_total) * 100
        : 0;
      return (
        <div className="space-y-1">
          <div className="text-sm">{row.original.locations_counted} / {row.original.locations_total} locations</div>
          <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-blue-500" style={{ width: `${progress}%` }} />
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'variances',
    header: 'Variances',
    cell: ({ row }) => {
      const hasVariances = row.original.variances_found > 0;
      return (
        <div className={`flex items-center gap-2 ${hasVariances ? 'text-red-600' : 'text-green-600'}`}>
          {hasVariances ? (
            <XCircle className="h-4 w-4" />
          ) : (
            <CheckCircle className="h-4 w-4" />
          )}
          <span>{row.original.variances_found}</span>
          {hasVariances && (
            <span className="text-xs">(${row.original.variance_value.toFixed(2)})</span>
          )}
        </div>
      );
    },
  },
  {
    accessorKey: 'accuracy_rate',
    header: 'Accuracy',
    cell: ({ row }) => {
      const accuracy = row.original.accuracy_rate;
      if (!accuracy) return <span className="text-muted-foreground">-</span>;
      const color = accuracy >= 99 ? 'text-green-600' : accuracy >= 95 ? 'text-yellow-600' : 'text-red-600';
      return (
        <span className={`font-medium ${color}`}>{accuracy.toFixed(1)}%</span>
      );
    },
  },
  {
    accessorKey: 'assigned_to',
    header: 'Assigned To',
    cell: ({ row }) => (
      <span className="text-sm">{row.original.assigned_to || 'Unassigned'}</span>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

export default function CycleCountPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['wms-cycle-count', page, pageSize],
    queryFn: () => cycleCountApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-cycle-count-stats'],
    queryFn: cycleCountApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cycle Counting"
        description="Schedule and manage inventory cycle counts for accuracy"
        actions={
          <Button onClick={() => toast.info('Feature coming soon')}>
            <Plus className="mr-2 h-4 w-4" />
            Schedule Count
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Counts</CardTitle>
            <ClipboardList className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_counts || 0}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Progress</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.in_progress || 0}</div>
            <p className="text-xs text-muted-foreground">Active counts</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Accuracy</CardTitle>
            <BarChart3 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.avg_accuracy || 0}%</div>
            <p className="text-xs text-muted-foreground">Inventory accuracy</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Variances Pending</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.variances_pending || 0}</div>
            <p className="text-xs text-muted-foreground">Needs review</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="count_number"
        searchPlaceholder="Search counts..."
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
