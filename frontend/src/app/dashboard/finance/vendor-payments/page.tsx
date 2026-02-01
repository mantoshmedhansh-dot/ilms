'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Eye, Download, CreditCard, IndianRupee, Calendar, Building2, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency, formatDate } from '@/lib/utils';

interface VendorPayment {
  id: string;
  vendor_id: string;
  vendor_code: string;
  vendor_name: string;
  transaction_date: string;
  reference_number: string;
  payment_mode: string | null;
  payment_reference: string | null;
  bank_name: string | null;
  cheque_number: string | null;
  cheque_date: string | null;
  amount: number;
  tds_amount: number;
  net_amount: number;
  tds_section: string | null;
  narration: string | null;
  running_balance: number;
  created_at: string;
}

interface PaymentStats {
  total_payments: number;
  total_amount: number;
  total_tds: number;
  payments_this_month: number;
  amount_this_month: number;
  payments_today: number;
  amount_today: number;
  top_vendors: Array<{
    id: string;
    vendor_code: string;
    name: string;
    total_paid: number;
  }>;
}

const vendorPaymentsApi = {
  list: async (params?: { page?: number; size?: number; payment_mode?: string; search?: string }) => {
    try {
      const { data } = await apiClient.get('/vendor-payments', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<PaymentStats> => {
    try {
      const { data } = await apiClient.get('/vendor-payments/stats');
      return data;
    } catch {
      return {
        total_payments: 0,
        total_amount: 0,
        total_tds: 0,
        payments_this_month: 0,
        amount_this_month: 0,
        payments_today: 0,
        amount_today: 0,
        top_vendors: []
      };
    }
  },
  getDetail: async (id: string) => {
    const { data } = await apiClient.get(`/vendor-payments/${id}`);
    return data;
  },
};

const paymentModeColors: Record<string, string> = {
  NEFT: 'bg-blue-100 text-blue-800',
  RTGS: 'bg-purple-100 text-purple-800',
  CHEQUE: 'bg-yellow-100 text-yellow-800',
  UPI: 'bg-green-100 text-green-800',
  CASH: 'bg-gray-100 text-gray-800',
};

export default function VendorPaymentsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [paymentModeFilter, setPaymentModeFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['vendor-payments', page, pageSize, paymentModeFilter, searchTerm],
    queryFn: () => vendorPaymentsApi.list({
      page: page + 1,
      size: pageSize,
      payment_mode: paymentModeFilter !== 'all' ? paymentModeFilter : undefined,
      search: searchTerm || undefined,
    }),
  });

  const { data: stats } = useQuery({
    queryKey: ['vendor-payments-stats'],
    queryFn: vendorPaymentsApi.getStats,
  });

  const columns: ColumnDef<VendorPayment>[] = [
    {
      accessorKey: 'reference_number',
      header: 'Reference',
      cell: ({ row }) => (
        <div className="font-medium text-blue-600">{row.original.reference_number}</div>
      ),
    },
    {
      accessorKey: 'vendor_name',
      header: 'Vendor',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.vendor_name}</div>
          <div className="text-xs text-muted-foreground">{row.original.vendor_code}</div>
        </div>
      ),
    },
    {
      accessorKey: 'transaction_date',
      header: 'Date',
      cell: ({ row }) => formatDate(row.original.transaction_date),
    },
    {
      accessorKey: 'payment_mode',
      header: 'Mode',
      cell: ({ row }) => {
        const mode = row.original.payment_mode || 'N/A';
        const colorClass = paymentModeColors[mode] || 'bg-gray-100 text-gray-600';
        return (
          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${colorClass}`}>
            {mode}
          </span>
        );
      },
    },
    {
      accessorKey: 'amount',
      header: 'Amount',
      cell: ({ row }) => (
        <div className="text-right font-medium">{formatCurrency(row.original.amount)}</div>
      ),
    },
    {
      accessorKey: 'tds_amount',
      header: 'TDS',
      cell: ({ row }) => (
        <div className="text-right text-muted-foreground">
          {row.original.tds_amount > 0 ? formatCurrency(row.original.tds_amount) : '-'}
        </div>
      ),
    },
    {
      accessorKey: 'net_amount',
      header: 'Net Amount',
      cell: ({ row }) => (
        <div className="text-right font-semibold text-green-600">
          {formatCurrency(row.original.net_amount)}
        </div>
      ),
    },
    {
      accessorKey: 'payment_reference',
      header: 'Bank Ref',
      cell: ({ row }) => (
        <div className="text-sm">
          {row.original.payment_reference || '-'}
          {row.original.cheque_number && (
            <div className="text-xs text-muted-foreground">
              Chq: {row.original.cheque_number}
            </div>
          )}
        </div>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Download className="mr-2 h-4 w-4" />
              Download Receipt
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vendor Payments"
        description="Track and manage payments made to vendors"
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Payments</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_payments || 0}</div>
            <p className="text-xs text-muted-foreground">
              Total: {formatCurrency(stats?.total_amount || 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">This Month</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.payments_this_month || 0}</div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(stats?.amount_this_month || 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Today</CardTitle>
            <IndianRupee className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.payments_today || 0}</div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(stats?.amount_today || 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">TDS Deducted</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats?.total_tds || 0)}</div>
            <p className="text-xs text-muted-foreground">
              Total TDS withheld
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Top Vendors */}
      {stats?.top_vendors && stats.top_vendors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Building2 className="h-4 w-4" />
              Top Vendors by Payment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {stats.top_vendors.map((vendor) => (
                <div
                  key={vendor.id}
                  className="flex items-center gap-2 px-3 py-2 bg-muted rounded-lg"
                >
                  <div>
                    <div className="text-sm font-medium">{vendor.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {formatCurrency(vendor.total_paid)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Input
          placeholder="Search by reference, vendor..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="max-w-sm"
        />
        <Select value={paymentModeFilter} onValueChange={setPaymentModeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Payment Mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Modes</SelectItem>
            <SelectItem value="NEFT">NEFT</SelectItem>
            <SelectItem value="RTGS">RTGS</SelectItem>
            <SelectItem value="CHEQUE">Cheque</SelectItem>
            <SelectItem value="UPI">UPI</SelectItem>
            <SelectItem value="CASH">Cash</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={data?.items || []}
        isLoading={isLoading}
        pageCount={data?.pages || 1}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />
    </div>
  );
}
