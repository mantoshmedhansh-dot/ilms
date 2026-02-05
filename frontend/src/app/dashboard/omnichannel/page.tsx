'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Store, Package, Clock, CheckCircle, MapPin, User, ShoppingBag } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface OmnichannelOrder {
  id: string;
  order_number: string;
  customer_name: string;
  customer_phone: string;
  fulfillment_type: 'BOPIS' | 'SHIP_FROM_STORE' | 'CURBSIDE' | 'SAME_DAY';
  store_name: string;
  store_code: string;
  items_count: number;
  order_value: number;
  pickup_time?: string;
  ready_time?: string;
  collected_time?: string;
  status: 'PENDING' | 'PICKING' | 'READY' | 'NOTIFIED' | 'COLLECTED' | 'CANCELLED' | 'EXPIRED';
  created_at: string;
}

interface OmnichannelStats {
  total_orders: number;
  bopis_orders: number;
  ready_for_pickup: number;
  avg_ready_time: number;
}

const omnichannelApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/omnichannel/orders', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<OmnichannelStats> => {
    try {
      const { data } = await apiClient.get('/omnichannel/stats');
      return data;
    } catch {
      return { total_orders: 0, bopis_orders: 0, ready_for_pickup: 0, avg_ready_time: 0 };
    }
  },
};

const fulfillmentColors: Record<string, string> = {
  BOPIS: 'bg-blue-100 text-blue-800',
  SHIP_FROM_STORE: 'bg-green-100 text-green-800',
  CURBSIDE: 'bg-purple-100 text-purple-800',
  SAME_DAY: 'bg-orange-100 text-orange-800',
};

const columns: ColumnDef<OmnichannelOrder>[] = [
  {
    accessorKey: 'order_number',
    header: 'Order',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <ShoppingBag className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.order_number}</div>
          <div className="text-xs text-muted-foreground">
            {new Date(row.original.created_at).toLocaleString()}
          </div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'customer_name',
    header: 'Customer',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <User className="h-4 w-4 text-muted-foreground" />
        <div>
          <div className="font-medium">{row.original.customer_name}</div>
          <div className="text-xs text-muted-foreground">{row.original.customer_phone}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'fulfillment_type',
    header: 'Type',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${fulfillmentColors[row.original.fulfillment_type]}`}>
        {row.original.fulfillment_type.replace(/_/g, ' ')}
      </span>
    ),
  },
  {
    accessorKey: 'store_name',
    header: 'Store',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Store className="h-4 w-4 text-muted-foreground" />
        <div>
          <div className="text-sm">{row.original.store_name}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.original.store_code}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'items_count',
    header: 'Items',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Package className="h-4 w-4 text-muted-foreground" />
        <span>{row.original.items_count}</span>
      </div>
    ),
  },
  {
    accessorKey: 'pickup_time',
    header: 'Pickup Time',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">
          {row.original.pickup_time
            ? new Date(row.original.pickup_time).toLocaleString()
            : 'Flexible'}
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

export default function OmnichannelPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['omnichannel-orders', page, pageSize],
    queryFn: () => omnichannelApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['omnichannel-stats'],
    queryFn: omnichannelApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Omnichannel Fulfillment"
        description="Manage Buy Online Pick Up In Store (BOPIS), curbside, and ship-from-store orders"
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Orders</CardTitle>
            <ShoppingBag className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_orders || 0}</div>
            <p className="text-xs text-muted-foreground">Today</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">BOPIS Orders</CardTitle>
            <Store className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.bopis_orders || 0}</div>
            <p className="text-xs text-muted-foreground">Buy Online, Pick In Store</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ready for Pickup</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.ready_for_pickup || 0}</div>
            <p className="text-xs text-muted-foreground">Awaiting collection</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Ready Time</CardTitle>
            <Clock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.avg_ready_time || 0} min</div>
            <p className="text-xs text-muted-foreground">Order to ready</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fulfillment Types</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-4 gap-4 text-sm">
            <div className="flex items-start gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 shrink-0">
                <Store className="h-4 w-4 text-blue-600" />
              </div>
              <div>
                <div className="font-medium">BOPIS</div>
                <div className="text-muted-foreground">Buy Online, Pick In Store</div>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-100 shrink-0">
                <MapPin className="h-4 w-4 text-purple-600" />
              </div>
              <div>
                <div className="font-medium">Curbside</div>
                <div className="text-muted-foreground">Pick up at designated spot</div>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-100 shrink-0">
                <Package className="h-4 w-4 text-green-600" />
              </div>
              <div>
                <div className="font-medium">Ship From Store</div>
                <div className="text-muted-foreground">Store fulfills online order</div>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-orange-100 shrink-0">
                <Clock className="h-4 w-4 text-orange-600" />
              </div>
              <div>
                <div className="font-medium">Same Day</div>
                <div className="text-muted-foreground">Express delivery from store</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="order_number"
        searchPlaceholder="Search orders..."
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
