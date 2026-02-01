'use client';

import { useState, useEffect, Suspense } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, Pencil, Truck, Package, MapPin, Calendar, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { format } from 'date-fns';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { ordersApi, shipmentsApi } from '@/lib/api';
import { Order, OrderStatus } from '@/types';
import { toast } from 'sonner';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
};

const orderStatuses: OrderStatus[] = [
  'NEW',
  'PENDING_PAYMENT',
  'CONFIRMED',
  'ALLOCATED',
  'PICKING',
  'PACKED',
  'SHIPPED',
  'IN_TRANSIT',
  'DELIVERED',
  'CANCELLED',
];

function OrdersPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Read initial values from URL params
  const initialStatus = searchParams.get('status') || 'all';
  const initialPage = parseInt(searchParams.get('page') || '0', 10);
  const initialPageSize = parseInt(searchParams.get('size') || '10', 10);

  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [statusFilter, setStatusFilter] = useState<string>(initialStatus);
  const [isTrackingSheetOpen, setIsTrackingSheetOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [trackingInfo, setTrackingInfo] = useState<any>(null);
  const [isLoadingTracking, setIsLoadingTracking] = useState(false);

  // Sync URL params when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (statusFilter !== 'all') {
      params.set('status', statusFilter);
    }
    if (page > 0) {
      params.set('page', page.toString());
    }
    if (pageSize !== 10) {
      params.set('size', pageSize.toString());
    }

    const queryString = params.toString();
    const newUrl = queryString ? `/dashboard/orders?${queryString}` : '/dashboard/orders';

    // Update URL without triggering navigation
    window.history.replaceState(null, '', newUrl);
  }, [statusFilter, page, pageSize]);

  const { data, isLoading } = useQuery({
    queryKey: ['orders', page, pageSize, statusFilter],
    queryFn: () =>
      ordersApi.list({
        page: page + 1,
        size: pageSize,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      }),
  });

  const handleTrackShipment = async (order: Order) => {
    setSelectedOrder(order);
    setIsTrackingSheetOpen(true);
    setIsLoadingTracking(true);

    try {
      // Try to fetch shipment info for the order
      const shipments = await shipmentsApi.list({ order_id: order.id, size: 1 });
      if (shipments?.items?.[0]) {
        setTrackingInfo(shipments.items[0]);
      } else {
        setTrackingInfo(null);
      }
    } catch {
      setTrackingInfo(null);
    } finally {
      setIsLoadingTracking(false);
    }
  };

  const columns: ColumnDef<Order>[] = [
    {
      accessorKey: 'order_number',
      header: 'Order #',
      cell: ({ row }) => (
        <Link
          href={`/dashboard/orders/${row.original.id}`}
          className="font-medium text-primary hover:underline"
        >
          {row.original.order_number}
        </Link>
      ),
    },
    {
      accessorKey: 'customer',
      header: 'Customer',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.customer?.full_name || row.original.customer?.name || '-'}</div>
          <div className="text-sm text-muted-foreground">
            {row.original.customer?.phone || '-'}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'source',
      header: 'Channel',
      cell: ({ row }) => (
        <span className="inline-flex items-center rounded-full bg-muted px-2 py-1 text-xs font-medium">
          {row.original.source || row.original.channel || '-'}
        </span>
      ),
    },
    {
      accessorKey: 'total_amount',
      header: 'Amount',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{formatCurrency(row.original.total_amount ?? row.original.grand_total ?? 0)}</div>
          <div className="text-xs text-muted-foreground">
            {row.original.item_count ?? row.original.items?.length ?? 0} items
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'payment_status',
      header: 'Payment',
      cell: ({ row }) => <StatusBadge status={row.original.payment_status} />,
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'created_at',
      header: 'Date',
      cell: ({ row }) => format(new Date(row.original.created_at), 'MMM d, yyyy'),
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
            <DropdownMenuItem onClick={() => router.push(`/dashboard/orders/${row.original.id}`)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/dashboard/orders/${row.original.id}/edit`)}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleTrackShipment(row.original)}>
              <Truck className="mr-2 h-4 w-4" />
              Track Shipment
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Orders"
        description="Manage and track customer orders"
        actions={
          <Button asChild>
            <Link href="/dashboard/orders/new">
              <Plus className="mr-2 h-4 w-4" />
              Create Order
            </Link>
          </Button>
        }
      />

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            {orderStatuses.map((status) => (
              <SelectItem key={status} value={status}>
                {status.replace(/_/g, ' ')}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

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

      {/* Tracking Sheet */}
      <Sheet open={isTrackingSheetOpen} onOpenChange={setIsTrackingSheetOpen}>
        <SheetContent className="w-[500px] sm:w-[600px]">
          <SheetHeader>
            <SheetTitle>Shipment Tracking</SheetTitle>
            <SheetDescription>
              Order: {selectedOrder?.order_number}
            </SheetDescription>
          </SheetHeader>
          {isLoadingTracking ? (
            <div className="mt-6 flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : trackingInfo ? (
            <div className="mt-6 space-y-6">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                <StatusBadge status={trackingInfo.status} />
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium flex items-center gap-2">
                  <Package className="h-4 w-4" />
                  Shipment Details
                </h4>
                <div className="rounded-lg border p-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">AWB Number</span>
                    <span className="text-sm font-mono">{trackingInfo.awb_number || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Carrier</span>
                    <span className="text-sm">{trackingInfo.transporter?.name || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Weight</span>
                    <span className="text-sm">{trackingInfo.weight || 'N/A'} kg</span>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  Delivery Address
                </h4>
                <div className="rounded-lg border p-4">
                  <p className="text-sm">
                    {trackingInfo.shipping_address || 'N/A'}
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Timeline
                </h4>
                <div className="rounded-lg border p-4 space-y-3">
                  {trackingInfo.created_at && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Created</span>
                      <span className="text-sm">{format(new Date(trackingInfo.created_at), 'MMM d, yyyy h:mm a')}</span>
                    </div>
                  )}
                  {trackingInfo.shipped_at && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Shipped</span>
                      <span className="text-sm">{format(new Date(trackingInfo.shipped_at), 'MMM d, yyyy h:mm a')}</span>
                    </div>
                  )}
                  {trackingInfo.delivered_at && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Delivered</span>
                      <span className="text-sm">{format(new Date(trackingInfo.delivered_at), 'MMM d, yyyy h:mm a')}</span>
                    </div>
                  )}
                  {trackingInfo.expected_delivery && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Expected Delivery</span>
                      <span className="text-sm">{format(new Date(trackingInfo.expected_delivery), 'MMM d, yyyy')}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-6 text-center py-12">
              <Truck className="mx-auto h-12 w-12 text-muted-foreground/50" />
              <h3 className="mt-4 text-lg font-medium">No shipment found</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                This order has not been shipped yet or tracking information is unavailable.
              </p>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

// Loading fallback component
function OrdersPageLoading() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Orders"
        description="Manage and track customer orders"
      />
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    </div>
  );
}

// Wrap in Suspense for useSearchParams
export default function OrdersPage() {
  return (
    <Suspense fallback={<OrdersPageLoading />}>
      <OrdersPageContent />
    </Suspense>
  );
}
