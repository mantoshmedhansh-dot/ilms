'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Receipt, Plus, DollarSign, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface WarehouseBill {
  id: string;
  bill_number: string;
  client_name: string;
  billing_period_start: string;
  billing_period_end: string;
  storage_charges: number;
  handling_charges: number;
  other_charges: number;
  total_amount: number;
  tax_amount: number;
  grand_total: number;
  status: 'DRAFT' | 'PENDING' | 'SENT' | 'PAID' | 'OVERDUE' | 'CANCELLED';
  due_date: string;
  paid_date?: string;
  created_at: string;
}

interface BillingStats {
  total_billed: number;
  pending_amount: number;
  overdue_amount: number;
  collected_this_month: number;
}

const billingApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/warehouse-billing/', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<BillingStats> => {
    try {
      const { data } = await apiClient.get('/warehouse-billing/stats');
      return data;
    } catch {
      return { total_billed: 0, pending_amount: 0, overdue_amount: 0, collected_this_month: 0 };
    }
  },
};

const columns: ColumnDef<WarehouseBill>[] = [
  {
    accessorKey: 'bill_number',
    header: 'Invoice',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Receipt className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.bill_number}</div>
          <div className="text-xs text-muted-foreground">{row.original.client_name}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'billing_period',
    header: 'Period',
    cell: ({ row }) => (
      <div className="text-sm">
        {new Date(row.original.billing_period_start).toLocaleDateString()} - {new Date(row.original.billing_period_end).toLocaleDateString()}
      </div>
    ),
  },
  {
    accessorKey: 'charges',
    header: 'Charges',
    cell: ({ row }) => (
      <div className="text-sm space-y-0.5">
        <div>Storage: ${row.original.storage_charges.toFixed(2)}</div>
        <div className="text-muted-foreground">Handling: ${row.original.handling_charges.toFixed(2)}</div>
      </div>
    ),
  },
  {
    accessorKey: 'grand_total',
    header: 'Total',
    cell: ({ row }) => (
      <div>
        <div className="font-mono font-medium">${row.original.grand_total.toFixed(2)}</div>
        <div className="text-xs text-muted-foreground">Tax: ${row.original.tax_amount.toFixed(2)}</div>
      </div>
    ),
  },
  {
    accessorKey: 'due_date',
    header: 'Due Date',
    cell: ({ row }) => {
      const isOverdue = new Date(row.original.due_date) < new Date() && row.original.status !== 'PAID';
      return (
        <div className={`flex items-center gap-2 ${isOverdue ? 'text-red-600' : ''}`}>
          <Clock className="h-4 w-4" />
          <span className="text-sm">{new Date(row.original.due_date).toLocaleDateString()}</span>
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

export default function BillingPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['wms-billing', page, pageSize],
    queryFn: () => billingApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-billing-stats'],
    queryFn: billingApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Warehouse Billing"
        description="Manage 3PL billing, storage fees, and handling charges"
        actions={
          <Button onClick={() => toast.info('Feature coming soon')}>
            <Plus className="mr-2 h-4 w-4" />
            Generate Invoice
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Billed</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${(stats?.total_billed || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <Clock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">${(stats?.pending_amount || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Awaiting payment</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overdue</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">${(stats?.overdue_amount || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Past due date</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Collected</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">${(stats?.collected_this_month || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="bill_number"
        searchPlaceholder="Search invoices..."
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
