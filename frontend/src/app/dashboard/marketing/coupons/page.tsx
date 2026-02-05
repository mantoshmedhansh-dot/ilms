'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { BadgePercent, Plus, Calendar, Users, DollarSign, CheckCircle, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface Coupon {
  id: string;
  code: string;
  name: string;
  description?: string;
  discount_type: 'PERCENTAGE' | 'FIXED_AMOUNT' | 'FREE_SHIPPING' | 'BUY_X_GET_Y';
  discount_value: number;
  min_order_value?: number;
  max_discount?: number;
  usage_limit?: number;
  usage_count: number;
  per_user_limit?: number;
  valid_from: string;
  valid_until: string;
  is_active: boolean;
  applicable_to: 'ALL' | 'CATEGORY' | 'PRODUCT' | 'CUSTOMER_SEGMENT';
  created_at: string;
}

interface CouponStats {
  total_coupons: number;
  active_coupons: number;
  total_redemptions: number;
  total_discount_given: number;
}

const couponsApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/coupons/', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<CouponStats> => {
    try {
      const { data } = await apiClient.get('/coupons/stats');
      return data;
    } catch {
      return { total_coupons: 0, active_coupons: 0, total_redemptions: 0, total_discount_given: 0 };
    }
  },
};

const discountTypeColors: Record<string, string> = {
  PERCENTAGE: 'bg-green-100 text-green-800',
  FIXED_AMOUNT: 'bg-blue-100 text-blue-800',
  FREE_SHIPPING: 'bg-purple-100 text-purple-800',
  BUY_X_GET_Y: 'bg-orange-100 text-orange-800',
};

const columns: ColumnDef<Coupon>[] = [
  {
    accessorKey: 'code',
    header: 'Coupon',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <BadgePercent className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-bold">{row.original.code}</div>
          <div className="text-xs text-muted-foreground">{row.original.name}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'discount_type',
    header: 'Discount',
    cell: ({ row }) => (
      <div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${discountTypeColors[row.original.discount_type]}`}>
          {row.original.discount_type.replace(/_/g, ' ')}
        </span>
        <div className="text-sm mt-1">
          {row.original.discount_type === 'PERCENTAGE' && `${row.original.discount_value}% off`}
          {row.original.discount_type === 'FIXED_AMOUNT' && `$${row.original.discount_value} off`}
          {row.original.discount_type === 'FREE_SHIPPING' && 'Free Shipping'}
          {row.original.discount_type === 'BUY_X_GET_Y' && 'BOGO Deal'}
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'usage',
    header: 'Usage',
    cell: ({ row }) => (
      <div className="text-sm">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-muted-foreground" />
          <span>{row.original.usage_count}</span>
          {row.original.usage_limit && (
            <span className="text-muted-foreground">/ {row.original.usage_limit}</span>
          )}
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'min_order_value',
    header: 'Min Order',
    cell: ({ row }) => (
      <span className="text-sm">
        {row.original.min_order_value ? `$${row.original.min_order_value}` : 'No min'}
      </span>
    ),
  },
  {
    accessorKey: 'validity',
    header: 'Validity',
    cell: ({ row }) => {
      const now = new Date();
      const validFrom = new Date(row.original.valid_from);
      const validUntil = new Date(row.original.valid_until);
      const isExpired = validUntil < now;
      const isUpcoming = validFrom > now;

      return (
        <div className="text-sm">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span>{validFrom.toLocaleDateString()}</span>
          </div>
          <div className={`text-xs ${isExpired ? 'text-red-600' : isUpcoming ? 'text-blue-600' : 'text-green-600'}`}>
            {isExpired ? 'Expired' : isUpcoming ? 'Upcoming' : `Until ${validUntil.toLocaleDateString()}`}
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.is_active ? 'ACTIVE' : 'INACTIVE'} />,
  },
];

export default function CouponsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['marketing-coupons', page, pageSize],
    queryFn: () => couponsApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['marketing-coupons-stats'],
    queryFn: couponsApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Coupons"
        description="Create and manage discount coupons and promotional codes"
        actions={
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create Coupon
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Coupons</CardTitle>
            <BadgePercent className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_coupons || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.active_coupons || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Redemptions</CardTitle>
            <Users className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.total_redemptions || 0}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Discount Given</CardTitle>
            <DollarSign className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">${(stats?.total_discount_given || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="code"
        searchPlaceholder="Search coupons..."
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
