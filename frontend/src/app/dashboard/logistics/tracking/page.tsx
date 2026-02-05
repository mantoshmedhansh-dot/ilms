'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MapPin, Package, Truck, Clock, CheckCircle, AlertTriangle, Search, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { toast } from 'sonner';
import apiClient from '@/lib/api/client';

interface Shipment {
  id: string;
  tracking_number: string;
  order_number: string;
  customer_name: string;
  carrier_name: string;
  origin_city: string;
  destination_city: string;
  current_location?: string;
  status: 'BOOKED' | 'PICKED_UP' | 'IN_TRANSIT' | 'OUT_FOR_DELIVERY' | 'DELIVERED' | 'EXCEPTION' | 'RETURNED';
  estimated_delivery?: string;
  actual_delivery?: string;
  last_update: string;
}

interface TrackingStats {
  total_shipments: number;
  in_transit: number;
  out_for_delivery: number;
  exceptions: number;
}

const trackingApi = {
  list: async (params?: { page?: number; size?: number; search?: string }) => {
    try {
      const { data } = await apiClient.get('/order-tracking/', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<TrackingStats> => {
    try {
      const { data } = await apiClient.get('/order-tracking/stats');
      return data;
    } catch {
      return { total_shipments: 0, in_transit: 0, out_for_delivery: 0, exceptions: 0 };
    }
  },
  track: async (trackingNumber: string) => {
    const { data } = await apiClient.get(`/order-tracking/track/${trackingNumber}`);
    return data;
  },
};

const statusColors: Record<string, string> = {
  BOOKED: 'bg-gray-100 text-gray-800',
  PICKED_UP: 'bg-blue-100 text-blue-800',
  IN_TRANSIT: 'bg-purple-100 text-purple-800',
  OUT_FOR_DELIVERY: 'bg-orange-100 text-orange-800',
  DELIVERED: 'bg-green-100 text-green-800',
  EXCEPTION: 'bg-red-100 text-red-800',
  RETURNED: 'bg-yellow-100 text-yellow-800',
};

const columns: ColumnDef<Shipment>[] = [
  {
    accessorKey: 'tracking_number',
    header: 'Tracking',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Package className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.tracking_number}</div>
          <div className="text-xs text-muted-foreground">Order: {row.original.order_number}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'customer_name',
    header: 'Customer',
    cell: ({ row }) => (
      <div className="font-medium">{row.original.customer_name}</div>
    ),
  },
  {
    accessorKey: 'route',
    header: 'Route',
    cell: ({ row }) => (
      <div className="text-sm">
        <div>{row.original.origin_city}</div>
        <div className="text-muted-foreground flex items-center gap-1">
          <MapPin className="h-3 w-3" />
          {row.original.destination_city}
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'carrier_name',
    header: 'Carrier',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Truck className="h-4 w-4 text-muted-foreground" />
        <span>{row.original.carrier_name}</span>
      </div>
    ),
  },
  {
    accessorKey: 'current_location',
    header: 'Current Location',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <MapPin className="h-4 w-4 text-blue-600" />
        <span className="text-sm">{row.original.current_location || 'Unknown'}</span>
      </div>
    ),
  },
  {
    accessorKey: 'estimated_delivery',
    header: 'ETA',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">
          {row.original.estimated_delivery
            ? new Date(row.original.estimated_delivery).toLocaleDateString()
            : '-'}
        </span>
      </div>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[row.original.status]}`}>
        {row.original.status.replace(/_/g, ' ')}
      </span>
    ),
  },
];

export default function OrderTrackingPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [trackingSearch, setTrackingSearch] = useState('');
  const [trackedShipment, setTrackedShipment] = useState<Shipment | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['logistics-tracking', page, pageSize],
    queryFn: () => trackingApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['logistics-tracking-stats'],
    queryFn: trackingApi.getStats,
  });

  const trackMutation = useMutation({
    mutationFn: (trackingNumber: string) => trackingApi.track(trackingNumber),
    onSuccess: (data) => {
      setTrackedShipment(data);
      toast.success('Shipment found!');
    },
    onError: () => {
      toast.error('Shipment not found. Please check the tracking number.');
    },
  });

  const handleTrack = () => {
    if (!trackingSearch.trim()) {
      toast.error('Please enter a tracking number');
      return;
    }
    trackMutation.mutate(trackingSearch.trim());
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleTrack();
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Order Tracking"
        description="Track shipments across all carriers in real-time"
      />

      {/* Quick Track */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Quick Track</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Enter tracking number or order number..."
                className="pl-10"
                value={trackingSearch}
                onChange={(e) => setTrackingSearch(e.target.value)}
                onKeyPress={handleKeyPress}
              />
            </div>
            <Button onClick={handleTrack} disabled={trackMutation.isPending}>
              {trackMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Tracking...
                </>
              ) : (
                'Track'
              )}
            </Button>
          </div>
          {trackedShipment && (
            <div className="mt-4 p-4 rounded-lg border bg-muted/50">
              <h4 className="font-medium mb-2">Tracking Result</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Tracking #:</span>
                  <p className="font-mono font-medium">{trackedShipment.tracking_number}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Status:</span>
                  <p><span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[trackedShipment.status]}`}>
                    {trackedShipment.status.replace(/_/g, ' ')}
                  </span></p>
                </div>
                <div>
                  <span className="text-muted-foreground">Location:</span>
                  <p className="font-medium">{trackedShipment.current_location || 'Unknown'}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">ETA:</span>
                  <p className="font-medium">
                    {trackedShipment.estimated_delivery
                      ? new Date(trackedShipment.estimated_delivery).toLocaleDateString()
                      : '-'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Shipments</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_shipments || 0}</div>
            <p className="text-xs text-muted-foreground">Active shipments</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Transit</CardTitle>
            <Truck className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">{stats?.in_transit || 0}</div>
            <p className="text-xs text-muted-foreground">On the way</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Out for Delivery</CardTitle>
            <MapPin className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.out_for_delivery || 0}</div>
            <p className="text-xs text-muted-foreground">Delivering today</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Exceptions</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.exceptions || 0}</div>
            <p className="text-xs text-muted-foreground">Needs attention</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="tracking_number"
        searchPlaceholder="Search shipments..."
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
