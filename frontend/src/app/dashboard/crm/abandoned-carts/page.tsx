'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { ShoppingCart, Mail, Phone, Clock, DollarSign, User, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface AbandonedCart {
  id: string;
  cart_id: string;
  customer_name: string;
  customer_email: string;
  customer_phone?: string;
  items_count: number;
  cart_value: number;
  abandoned_at: string;
  last_activity: string;
  recovery_status: 'NOT_CONTACTED' | 'EMAIL_SENT' | 'SMS_SENT' | 'RECOVERED' | 'LOST';
  recovery_attempts: number;
  source_channel?: string;
}

interface AbandonedCartStats {
  total_abandoned: number;
  total_value: number;
  recovery_rate: number;
  recovered_today: number;
}

const abandonedCartsApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/crm/abandoned-carts', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<AbandonedCartStats> => {
    try {
      const { data } = await apiClient.get('/crm/abandoned-carts/stats');
      return data;
    } catch {
      return { total_abandoned: 0, total_value: 0, recovery_rate: 0, recovered_today: 0 };
    }
  },
};

const statusColors: Record<string, string> = {
  NOT_CONTACTED: 'bg-gray-100 text-gray-800',
  EMAIL_SENT: 'bg-blue-100 text-blue-800',
  SMS_SENT: 'bg-purple-100 text-purple-800',
  RECOVERED: 'bg-green-100 text-green-800',
  LOST: 'bg-red-100 text-red-800',
};

const columns: ColumnDef<AbandonedCart>[] = [
  {
    accessorKey: 'cart_id',
    header: 'Cart',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <ShoppingCart className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.cart_id}</div>
          <div className="text-xs text-muted-foreground">{row.original.items_count} items</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'customer_name',
    header: 'Customer',
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.customer_name}</div>
        <div className="text-xs text-muted-foreground">{row.original.customer_email}</div>
      </div>
    ),
  },
  {
    accessorKey: 'cart_value',
    header: 'Value',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <DollarSign className="h-4 w-4 text-muted-foreground" />
        <span className="font-mono font-medium">${row.original.cart_value.toFixed(2)}</span>
      </div>
    ),
  },
  {
    accessorKey: 'abandoned_at',
    header: 'Abandoned',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">{new Date(row.original.abandoned_at).toLocaleString()}</span>
      </div>
    ),
  },
  {
    accessorKey: 'recovery_attempts',
    header: 'Attempts',
    cell: ({ row }) => (
      <span className="font-mono">{row.original.recovery_attempts}</span>
    ),
  },
  {
    accessorKey: 'recovery_status',
    header: 'Status',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[row.original.recovery_status]}`}>
        {row.original.recovery_status.replace(/_/g, ' ')}
      </span>
    ),
  },
  {
    id: 'actions',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" title="Send Email">
          <Mail className="h-4 w-4" />
        </Button>
        {row.original.customer_phone && (
          <Button variant="ghost" size="sm" title="Send SMS">
            <Phone className="h-4 w-4" />
          </Button>
        )}
      </div>
    ),
  },
];

export default function AbandonedCartsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['abandoned-carts', page, pageSize],
    queryFn: () => abandonedCartsApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['abandoned-carts-stats'],
    queryFn: abandonedCartsApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Abandoned Carts"
        description="Recover lost sales by reaching out to customers who abandoned their carts"
        actions={
          <Button>
            <Mail className="mr-2 h-4 w-4" />
            Send Recovery Campaign
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Abandoned</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_abandoned || 0}</div>
            <p className="text-xs text-muted-foreground">Last 30 days</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">${(stats?.total_value || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Potential revenue</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recovery Rate</CardTitle>
            <AlertCircle className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.recovery_rate || 0}%</div>
            <p className="text-xs text-muted-foreground">Carts recovered</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recovered Today</CardTitle>
            <User className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.recovered_today || 0}</div>
            <p className="text-xs text-muted-foreground">Sales recovered</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="customer_name"
        searchPlaceholder="Search customers..."
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
