'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Users, Plus, Clock, TrendingUp, Package, Timer, Award } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface Worker {
  id: string;
  employee_id: string;
  name: string;
  role: 'PICKER' | 'PACKER' | 'RECEIVER' | 'PUTAWAY' | 'SUPERVISOR';
  shift: 'MORNING' | 'AFTERNOON' | 'NIGHT';
  status: 'ACTIVE' | 'ON_BREAK' | 'OFF_DUTY';
  tasks_completed: number;
  items_processed: number;
  avg_time_per_task: number;
  performance_score: number;
  current_zone?: string;
}

interface LaborStats {
  total_workers: number;
  active_now: number;
  avg_productivity: number;
  tasks_completed_today: number;
}

const laborApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/wms/labor', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<LaborStats> => {
    try {
      const { data } = await apiClient.get('/wms/labor/stats');
      return data;
    } catch {
      return { total_workers: 0, active_now: 0, avg_productivity: 0, tasks_completed_today: 0 };
    }
  },
};

const roleColors: Record<string, string> = {
  PICKER: 'bg-blue-100 text-blue-800',
  PACKER: 'bg-green-100 text-green-800',
  RECEIVER: 'bg-purple-100 text-purple-800',
  PUTAWAY: 'bg-orange-100 text-orange-800',
  SUPERVISOR: 'bg-red-100 text-red-800',
};

const columns: ColumnDef<Worker>[] = [
  {
    accessorKey: 'name',
    header: 'Worker',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
          <Users className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-medium">{row.original.name}</div>
          <div className="text-xs text-muted-foreground">{row.original.employee_id}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'role',
    header: 'Role',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${roleColors[row.original.role]}`}>
        {row.original.role}
      </span>
    ),
  },
  {
    accessorKey: 'shift',
    header: 'Shift',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">{row.original.shift}</span>
      </div>
    ),
  },
  {
    accessorKey: 'tasks_completed',
    header: 'Tasks',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Package className="h-4 w-4 text-muted-foreground" />
        <span className="font-mono">{row.original.tasks_completed}</span>
      </div>
    ),
  },
  {
    accessorKey: 'avg_time_per_task',
    header: 'Avg Time',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Timer className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">{row.original.avg_time_per_task}s</span>
      </div>
    ),
  },
  {
    accessorKey: 'performance_score',
    header: 'Performance',
    cell: ({ row }) => {
      const score = row.original.performance_score;
      const color = score >= 90 ? 'text-green-600' : score >= 70 ? 'text-yellow-600' : 'text-red-600';
      return (
        <div className="flex items-center gap-2">
          <Award className={`h-4 w-4 ${color}`} />
          <span className={`font-medium ${color}`}>{score}%</span>
        </div>
      );
    },
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

export default function LaborPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['wms-labor', page, pageSize],
    queryFn: () => laborApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-labor-stats'],
    queryFn: laborApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Labor Management"
        description="Track warehouse workforce productivity and assignments"
        actions={
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Add Worker
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Workers</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_workers || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Now</CardTitle>
            <Clock className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.active_now || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Productivity</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.avg_productivity || 0}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tasks Today</CardTitle>
            <Package className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.tasks_completed_today || 0}</div>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="name"
        searchPlaceholder="Search workers..."
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
