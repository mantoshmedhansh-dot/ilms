'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Calendar, Package, Clock, DollarSign, Users, CheckCircle, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface Preorder {
  id: string;
  preorder_number: string;
  product_name: string;
  product_sku: string;
  customer_name: string;
  customer_email: string;
  quantity: number;
  unit_price: number;
  total_amount: number;
  deposit_amount?: number;
  deposit_paid: boolean;
  expected_release_date?: string;
  status: 'PENDING_PAYMENT' | 'CONFIRMED' | 'READY_TO_SHIP' | 'SHIPPED' | 'CANCELLED' | 'REFUNDED';
  created_at: string;
}

interface PreorderStats {
  total_preorders: number;
  total_value: number;
  confirmed_count: number;
  pending_payment: number;
}

const preordersApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/logistics/preorders', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<PreorderStats> => {
    try {
      const { data } = await apiClient.get('/logistics/preorders/stats');
      return data;
    } catch {
      return { total_preorders: 0, total_value: 0, confirmed_count: 0, pending_payment: 0 };
    }
  },
};

const columns: ColumnDef<Preorder>[] = [
  {
    accessorKey: 'preorder_number',
    header: 'Preorder',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100">
          <Calendar className="h-5 w-5 text-purple-600" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.preorder_number}</div>
          <div className="text-xs text-muted-foreground">
            {new Date(row.original.created_at).toLocaleDateString()}
          </div>
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
    accessorKey: 'quantity',
    header: 'Qty',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Package className="h-4 w-4 text-muted-foreground" />
        <span className="font-mono">{row.original.quantity}</span>
      </div>
    ),
  },
  {
    accessorKey: 'total_amount',
    header: 'Amount',
    cell: ({ row }) => (
      <div>
        <div className="flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-muted-foreground" />
          <span className="font-mono font-medium">${row.original.total_amount.toFixed(2)}</span>
        </div>
        {row.original.deposit_amount && (
          <div className="text-xs text-muted-foreground">
            Deposit: ${row.original.deposit_amount.toFixed(2)}
            {row.original.deposit_paid ? ' (Paid)' : ' (Pending)'}
          </div>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'expected_release_date',
    header: 'Release Date',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">
          {row.original.expected_release_date
            ? new Date(row.original.expected_release_date).toLocaleDateString()
            : 'TBD'}
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

export default function PreordersPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['logistics-preorders', page, pageSize],
    queryFn: () => preordersApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['logistics-preorders-stats'],
    queryFn: preordersApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Preorders"
        description="Manage advance orders for upcoming product releases"
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
            <CardTitle className="text-sm font-medium">Total Preorders</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_preorders || 0}</div>
            <p className="text-xs text-muted-foreground">Active preorders</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">${(stats?.total_value || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Committed revenue</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Confirmed</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.confirmed_count || 0}</div>
            <p className="text-xs text-muted-foreground">Payment received</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Payment</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.pending_payment || 0}</div>
            <p className="text-xs text-muted-foreground">Awaiting deposit</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="preorder_number"
        searchPlaceholder="Search preorders..."
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
