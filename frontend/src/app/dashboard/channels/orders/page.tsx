'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Eye, Download, ShoppingCart, Package, Truck, CheckCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency, formatDate } from '@/lib/utils';

interface MarketplaceOrder {
  id: string;
  channel_id: string;
  channel_name: string;
  channel_order_id: string;
  internal_order_id?: string;
  customer_name: string;
  customer_phone: string;
  shipping_address: string;
  shipping_city: string;
  shipping_pincode: string;
  items_count: number;
  total_amount: number;
  channel_status: string;
  internal_status: string;
  payment_mode: 'PREPAID' | 'COD';
  is_imported: boolean;
  ordered_at: string;
  imported_at?: string;
}

interface OrderStats {
  total_orders_today: number;
  pending_import: number;
  processing: number;
  shipped: number;
  cod_amount: number;
  prepaid_amount: number;
}

const marketplaceOrdersApi = {
  list: async (params?: { page?: number; size?: number; channel_id?: string; status?: string; payment_mode?: string }) => {
    try {
      const { data } = await apiClient.get('/channels/orders', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<OrderStats> => {
    try {
      const { data } = await apiClient.get('/channels/orders/stats');
      return data;
    } catch {
      return {
        total_orders_today: 0,
        pending_import: 0,
        processing: 0,
        shipped: 0,
        cod_amount: 0,
        prepaid_amount: 0
      };
    }
  },
  importOrder: async (orderId: string) => {
    const { data } = await apiClient.post(`/channels/orders/${orderId}/import`);
    return data;
  },
  fetchFromChannel: async (channelId: string) => {
    const { data } = await apiClient.post(`/channels/${channelId}/fetch-orders`);
    return data;
  },
};

const createColumns = (
  onView: (order: MarketplaceOrder) => void,
  onImport: (order: MarketplaceOrder) => void
): ColumnDef<MarketplaceOrder>[] => [
  {
    accessorKey: 'channel_order_id',
    header: 'Order ID',
    cell: ({ row }) => (
      <div>
        <div className="font-mono text-sm font-medium">{row.original.channel_order_id}</div>
        {row.original.internal_order_id && (
          <div className="text-xs text-muted-foreground">Int: {row.original.internal_order_id}</div>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'channel_name',
    header: 'Channel',
    cell: ({ row }) => {
      const colors: Record<string, string> = {
        Amazon: 'bg-orange-100 text-orange-800',
        Flipkart: 'bg-blue-100 text-blue-800',
        Myntra: 'bg-pink-100 text-pink-800',
        D2C: 'bg-green-100 text-green-800',
      };
      return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[row.original.channel_name] || 'bg-gray-100'}`}>
          {row.original.channel_name}
        </span>
      );
    },
  },
  {
    accessorKey: 'customer_name',
    header: 'Customer',
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.customer_name}</div>
        <div className="text-sm text-muted-foreground">{row.original.shipping_city} - {row.original.shipping_pincode}</div>
      </div>
    ),
  },
  {
    accessorKey: 'items_count',
    header: 'Items',
    cell: ({ row }) => (
      <span className="text-sm">{row.original.items_count} items</span>
    ),
  },
  {
    accessorKey: 'total_amount',
    header: 'Amount',
    cell: ({ row }) => (
      <div>
        <div className="font-mono font-medium">{formatCurrency(row.original.total_amount)}</div>
        <span className={`text-xs px-1.5 py-0.5 rounded ${
          row.original.payment_mode === 'COD' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'
        }`}>
          {row.original.payment_mode}
        </span>
      </div>
    ),
  },
  {
    accessorKey: 'channel_status',
    header: 'Channel Status',
    cell: ({ row }) => <StatusBadge status={row.original.channel_status} />,
  },
  {
    accessorKey: 'is_imported',
    header: 'Import Status',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        {row.original.is_imported ? (
          <span className="flex items-center gap-1 text-xs text-green-600">
            <CheckCircle className="h-3 w-3" />
            Imported
          </span>
        ) : (
          <span className="text-xs text-orange-600">Pending</span>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'ordered_at',
    header: 'Ordered At',
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">{formatDate(row.original.ordered_at)}</span>
    ),
  },
  {
    id: 'actions',
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Actions</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => onView(row.original)}>
            <Eye className="mr-2 h-4 w-4" />
            View Details
          </DropdownMenuItem>
          {!row.original.is_imported && (
            <DropdownMenuItem onClick={() => onImport(row.original)}>
              <Download className="mr-2 h-4 w-4" />
              Import Order
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];

export default function MarketplaceOrdersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [channelFilter, setChannelFilter] = useState<string>('all');
  const [paymentFilter, setPaymentFilter] = useState<string>('all');
  const [importFilter, setImportFilter] = useState<string>('all');
  const [viewOrder, setViewOrder] = useState<MarketplaceOrder | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [isFetching, setIsFetching] = useState(false);

  const handleView = (order: MarketplaceOrder) => {
    setViewOrder(order);
    setIsSheetOpen(true);
  };

  const importMutation = useMutation({
    mutationFn: (orderId: string) => marketplaceOrdersApi.importOrder(orderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplace-orders'] });
      queryClient.invalidateQueries({ queryKey: ['marketplace-orders-stats'] });
      toast.success('Order imported successfully');
    },
    onError: () => toast.error('Failed to import order'),
  });

  const handleImport = (order: MarketplaceOrder) => {
    importMutation.mutate(order.id);
  };

  const handleFetchOrders = async () => {
    setIsFetching(true);
    try {
      await marketplaceOrdersApi.fetchFromChannel('all');
      queryClient.invalidateQueries({ queryKey: ['marketplace-orders'] });
      queryClient.invalidateQueries({ queryKey: ['marketplace-orders-stats'] });
      toast.success('Orders fetched from channels');
    } catch {
      toast.error('Failed to fetch orders from channels');
    } finally {
      setIsFetching(false);
    }
  };

  const columns = createColumns(handleView, handleImport);

  const { data, isLoading } = useQuery({
    queryKey: ['marketplace-orders', page, pageSize, channelFilter, paymentFilter, importFilter],
    queryFn: () => marketplaceOrdersApi.list({
      page: page + 1,
      size: pageSize,
      channel_id: channelFilter !== 'all' ? channelFilter : undefined,
      payment_mode: paymentFilter !== 'all' ? paymentFilter : undefined,
    }),
  });

  const { data: stats } = useQuery({
    queryKey: ['marketplace-orders-stats'],
    queryFn: marketplaceOrdersApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Marketplace Orders"
        description="View and manage orders from all connected sales channels"
        actions={
          <Button variant="outline" onClick={handleFetchOrders} disabled={isFetching}>
            {isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
            {isFetching ? 'Fetching...' : 'Fetch Orders'}
          </Button>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Today&apos;s Orders</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_orders_today || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Import</CardTitle>
            <Download className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.pending_import || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Processing</CardTitle>
            <Package className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.processing || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Shipped</CardTitle>
            <Truck className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.shipped || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">COD Amount</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">{formatCurrency(stats?.cod_amount || 0)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Prepaid Amount</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">{formatCurrency(stats?.prepaid_amount || 0)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={channelFilter} onValueChange={setChannelFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Channels" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Channels</SelectItem>
            <SelectItem value="amazon">Amazon</SelectItem>
            <SelectItem value="flipkart">Flipkart</SelectItem>
            <SelectItem value="myntra">Myntra</SelectItem>
            <SelectItem value="d2c">D2C</SelectItem>
          </SelectContent>
        </Select>
        <Select value={paymentFilter} onValueChange={setPaymentFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Payment Mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Payments</SelectItem>
            <SelectItem value="PREPAID">Prepaid</SelectItem>
            <SelectItem value="COD">COD</SelectItem>
          </SelectContent>
        </Select>
        <Select value={importFilter} onValueChange={setImportFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Import Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="imported">Imported</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="channel_order_id"
        searchPlaceholder="Search orders..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Order Details Sheet */}
      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent className="sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>Order Details</SheetTitle>
            <SheetDescription>
              {viewOrder?.channel_order_id}
            </SheetDescription>
          </SheetHeader>
          {viewOrder && (
            <div className="mt-6 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-muted-foreground">Channel</label>
                  <p className="font-medium">{viewOrder.channel_name}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Status</label>
                  <p><StatusBadge status={viewOrder.channel_status} /></p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Customer</label>
                  <p className="font-medium">{viewOrder.customer_name}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Phone</label>
                  <p className="font-medium">{viewOrder.customer_phone}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Items</label>
                  <p className="font-medium">{viewOrder.items_count} items</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Amount</label>
                  <p className="font-medium">{formatCurrency(viewOrder.total_amount)}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Payment Mode</label>
                  <p className="font-medium">{viewOrder.payment_mode}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Import Status</label>
                  <p className="font-medium">{viewOrder.is_imported ? 'Imported' : 'Pending'}</p>
                </div>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Shipping Address</label>
                <p className="font-medium">{viewOrder.shipping_address}</p>
                <p className="text-muted-foreground">{viewOrder.shipping_city} - {viewOrder.shipping_pincode}</p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Order Date</label>
                <p className="font-medium">{formatDate(viewOrder.ordered_at)}</p>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
