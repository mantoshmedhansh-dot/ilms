'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { ClipboardCheck, Plus, CheckCircle, XCircle, AlertTriangle, Package } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface QualityInspection {
  id: string;
  inspection_number: string;
  product_name: string;
  product_sku: string;
  lot_number?: string;
  batch_number?: string;
  inspection_type: 'RECEIVING' | 'IN_PROCESS' | 'FINAL' | 'RANDOM';
  quantity_inspected: number;
  quantity_passed: number;
  quantity_failed: number;
  defect_type?: string;
  inspector_name: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'PASSED' | 'FAILED' | 'ON_HOLD';
  inspected_at?: string;
  notes?: string;
}

interface QualityStats {
  total_inspections: number;
  pass_rate: number;
  pending_inspections: number;
  failed_today: number;
}

const qualityApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/wms/quality/inspections', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<QualityStats> => {
    try {
      const { data } = await apiClient.get('/wms/quality/stats');
      return data;
    } catch {
      return { total_inspections: 0, pass_rate: 0, pending_inspections: 0, failed_today: 0 };
    }
  },
};

const typeColors: Record<string, string> = {
  RECEIVING: 'bg-blue-100 text-blue-800',
  IN_PROCESS: 'bg-purple-100 text-purple-800',
  FINAL: 'bg-green-100 text-green-800',
  RANDOM: 'bg-orange-100 text-orange-800',
};

const columns: ColumnDef<QualityInspection>[] = [
  {
    accessorKey: 'inspection_number',
    header: 'Inspection',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <ClipboardCheck className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.inspection_number}</div>
          <div className="text-xs text-muted-foreground">{row.original.inspector_name}</div>
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
    accessorKey: 'inspection_type',
    header: 'Type',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${typeColors[row.original.inspection_type]}`}>
        {row.original.inspection_type.replace('_', ' ')}
      </span>
    ),
  },
  {
    accessorKey: 'results',
    header: 'Results',
    cell: ({ row }) => {
      const passed = row.original.quantity_passed;
      const failed = row.original.quantity_failed;
      const total = row.original.quantity_inspected;
      const passRate = total > 0 ? (passed / total) * 100 : 0;
      return (
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <span>{passed}</span>
            <XCircle className="h-4 w-4 text-red-600 ml-2" />
            <span>{failed}</span>
          </div>
          <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-green-500" style={{ width: `${passRate}%` }} />
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'lot_number',
    header: 'Lot/Batch',
    cell: ({ row }) => (
      <div className="font-mono text-sm">
        {row.original.lot_number || row.original.batch_number || '-'}
      </div>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

export default function QualityPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['wms-quality', page, pageSize],
    queryFn: () => qualityApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-quality-stats'],
    queryFn: qualityApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quality Control"
        description="Manage product inspections and quality standards"
        actions={
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Inspection
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Inspections</CardTitle>
            <ClipboardCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_inspections || 0}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.pass_rate || 0}%</div>
            <p className="text-xs text-muted-foreground">Quality score</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.pending_inspections || 0}</div>
            <p className="text-xs text-muted-foreground">Awaiting inspection</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Today</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.failed_today || 0}</div>
            <p className="text-xs text-muted-foreground">Requires attention</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="inspection_number"
        searchPlaceholder="Search inspections..."
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
