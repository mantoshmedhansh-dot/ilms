'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { UserPlus, Users, DollarSign, CheckCircle, Clock, Gift, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface Referral {
  id: string;
  referrer_name: string;
  referrer_code: string;
  referred_name: string;
  referred_phone: string;
  referral_code: string;
  referral_bonus: number;
  is_qualified: boolean;
  qualified_at?: string;
  qualification_order_id?: string;
  status: 'PENDING' | 'QUALIFIED' | 'PAID' | 'EXPIRED';
  created_at: string;
}

interface ReferralStats {
  total_referrals: number;
  qualified_referrals: number;
  total_bonus_paid: number;
  conversion_rate: number;
}

const referralsApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/partners/referrals', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<ReferralStats> => {
    try {
      const { data } = await apiClient.get('/partners/referrals/stats');
      return data;
    } catch {
      return { total_referrals: 0, qualified_referrals: 0, total_bonus_paid: 0, conversion_rate: 0 };
    }
  },
};

const columns: ColumnDef<Referral>[] = [
  {
    accessorKey: 'referrer_name',
    header: 'Referrer',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
          <Users className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-medium">{row.original.referrer_name}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.original.referrer_code}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'referred_name',
    header: 'Referred Partner',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
          <UserPlus className="h-5 w-5 text-green-600" />
        </div>
        <div>
          <div className="font-medium">{row.original.referred_name}</div>
          <div className="text-xs text-muted-foreground">{row.original.referred_phone}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'referral_code',
    header: 'Code',
    cell: ({ row }) => (
      <span className="font-mono text-sm bg-muted px-2 py-1 rounded">{row.original.referral_code}</span>
    ),
  },
  {
    accessorKey: 'referral_bonus',
    header: 'Bonus',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Gift className="h-4 w-4 text-green-600" />
        <span className="font-mono font-medium">${row.original.referral_bonus.toFixed(2)}</span>
      </div>
    ),
  },
  {
    accessorKey: 'is_qualified',
    header: 'Qualified',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        {row.original.is_qualified ? (
          <>
            <CheckCircle className="h-4 w-4 text-green-600" />
            <span className="text-green-600 text-sm">Yes</span>
          </>
        ) : (
          <>
            <Clock className="h-4 w-4 text-orange-600" />
            <span className="text-orange-600 text-sm">Pending</span>
          </>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'created_at',
    header: 'Date',
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {new Date(row.original.created_at).toLocaleDateString()}
      </span>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

export default function PartnerReferralsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['partner-referrals', page, pageSize],
    queryFn: () => referralsApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['partner-referrals-stats'],
    queryFn: referralsApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Partner Referrals"
        description="Track partner referrals and bonus payouts"
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Referrals</CardTitle>
            <UserPlus className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_referrals || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Qualified</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.qualified_referrals || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Bonus Paid</CardTitle>
            <DollarSign className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">${(stats?.total_bonus_paid || 0).toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conversion Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.conversion_rate || 0}%</div>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="referrer_name"
        searchPlaceholder="Search referrals..."
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
