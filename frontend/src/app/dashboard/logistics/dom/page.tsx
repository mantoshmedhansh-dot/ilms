'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Network, Plus, Warehouse, Truck, Clock, CheckCircle, Settings, BarChart3 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface RoutingRule {
  id: string;
  rule_name: string;
  rule_code: string;
  priority: number;
  source_type: 'WAREHOUSE' | 'STORE' | 'VENDOR' | 'DROPSHIP';
  source_name: string;
  destination_zones?: string[];
  conditions: string;
  fulfillment_sla_hours: number;
  is_active: boolean;
  orders_routed: number;
  success_rate: number;
  created_at: string;
}

interface DOMStats {
  total_rules: number;
  active_rules: number;
  orders_today: number;
  avg_routing_time: number;
}

const domApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/dom/rules', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<DOMStats> => {
    try {
      const { data } = await apiClient.get('/dom/stats');
      return data;
    } catch {
      return { total_rules: 0, active_rules: 0, orders_today: 0, avg_routing_time: 0 };
    }
  },
};

const sourceTypeColors: Record<string, string> = {
  WAREHOUSE: 'bg-blue-100 text-blue-800',
  STORE: 'bg-green-100 text-green-800',
  VENDOR: 'bg-purple-100 text-purple-800',
  DROPSHIP: 'bg-orange-100 text-orange-800',
};

const columns: ColumnDef<RoutingRule>[] = [
  {
    accessorKey: 'rule_name',
    header: 'Rule',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Network className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-medium">{row.original.rule_name}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.original.rule_code}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'priority',
    header: 'Priority',
    cell: ({ row }) => (
      <span className="font-mono bg-muted px-2 py-1 rounded">{row.original.priority}</span>
    ),
  },
  {
    accessorKey: 'source_type',
    header: 'Source',
    cell: ({ row }) => (
      <div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${sourceTypeColors[row.original.source_type]}`}>
          {row.original.source_type}
        </span>
        <div className="text-xs text-muted-foreground mt-1">{row.original.source_name}</div>
      </div>
    ),
  },
  {
    accessorKey: 'conditions',
    header: 'Conditions',
    cell: ({ row }) => (
      <div className="max-w-[200px] truncate text-sm text-muted-foreground">
        {row.original.conditions}
      </div>
    ),
  },
  {
    accessorKey: 'fulfillment_sla_hours',
    header: 'SLA',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span>{row.original.fulfillment_sla_hours}h</span>
      </div>
    ),
  },
  {
    accessorKey: 'success_rate',
    header: 'Success Rate',
    cell: ({ row }) => {
      const rate = row.original.success_rate;
      const color = rate >= 95 ? 'text-green-600' : rate >= 80 ? 'text-yellow-600' : 'text-red-600';
      return (
        <span className={`font-medium ${color}`}>{rate.toFixed(1)}%</span>
      );
    },
  },
  {
    accessorKey: 'orders_routed',
    header: 'Orders',
    cell: ({ row }) => (
      <span className="font-mono">{row.original.orders_routed.toLocaleString()}</span>
    ),
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.is_active ? 'ACTIVE' : 'INACTIVE'} />,
  },
];

export default function DOMPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['logistics-dom', page, pageSize],
    queryFn: () => domApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['logistics-dom-stats'],
    queryFn: domApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Distributed Order Management (DOM)"
        description="Configure intelligent order routing rules across fulfillment nodes"
        actions={
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create Rule
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Rules</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_rules || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Rules</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.active_rules || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Orders Routed Today</CardTitle>
            <BarChart3 className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.orders_today || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Routing Time</CardTitle>
            <Clock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.avg_routing_time || 0}ms</div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">How DOM Works</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <div className="grid md:grid-cols-4 gap-4">
            <div className="flex items-start gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-blue-600 shrink-0">1</div>
              <div>
                <div className="font-medium text-foreground">Order Received</div>
                <div>New order enters the system</div>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-blue-600 shrink-0">2</div>
              <div>
                <div className="font-medium text-foreground">Rule Evaluation</div>
                <div>Rules evaluated by priority</div>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-blue-600 shrink-0">3</div>
              <div>
                <div className="font-medium text-foreground">Node Selection</div>
                <div>Best fulfillment node selected</div>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-100 text-green-600 shrink-0">4</div>
              <div>
                <div className="font-medium text-foreground">Order Routed</div>
                <div>Order assigned to fulfill</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="rule_name"
        searchPlaceholder="Search rules..."
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
