'use client';

import { useQuery } from '@tanstack/react-query';
import {
  Package,
  Warehouse,
  Store,
  AlertTriangle,
  TrendingUp,
  ArrowRightLeft,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

interface ChannelInventorySummary {
  channel_id: string;
  channel_code: string;
  channel_name: string;
  channel_type: string;
  total_allocated: number;
  total_buffer: number;
  total_reserved: number;
  total_available: number;
  products_count: number;
  low_stock_count: number;
  out_of_stock_count: number;
}

interface WarehouseInventorySummary {
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  total_quantity: number;
  total_reserved: number;
  total_available: number;
  products_count: number;
  low_stock_count: number;
  channels_served: number;
}

interface ChannelLocationBreakdown {
  channel_id: string;
  channel_code: string;
  channel_name: string;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  allocated_quantity: number;
  buffer_quantity: number;
  reserved_quantity: number;
  available_quantity: number;
  products_count: number;
}

interface DashboardData {
  total_channels: number;
  total_warehouses: number;
  total_products_allocated: number;
  total_allocated_quantity: number;
  total_available_quantity: number;
  by_channel: ChannelInventorySummary[];
  by_warehouse: WarehouseInventorySummary[];
  by_channel_location: ChannelLocationBreakdown[];
}

const channelTypeColors: Record<string, string> = {
  D2C: 'bg-blue-100 text-blue-800',
  D2C_WEBSITE: 'bg-blue-100 text-blue-800',
  B2B: 'bg-purple-100 text-purple-800',
  MARKETPLACE: 'bg-green-100 text-green-800',
  AMAZON: 'bg-orange-100 text-orange-800',
  FLIPKART: 'bg-yellow-100 text-yellow-800',
  DEALER: 'bg-indigo-100 text-indigo-800',
  OFFLINE: 'bg-gray-100 text-gray-800',
  OTHER: 'bg-gray-100 text-gray-800',
};

function StatCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
}: {
  title: string;
  value: number | string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  trend?: 'up' | 'down' | 'neutral';
}) {
  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600';

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${trendColor}`}>{value}</div>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-5">
        {[...Array(5)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16" />
              <Skeleton className="h-3 w-32 mt-2" />
            </CardContent>
          </Card>
        ))}
      </div>
      <Skeleton className="h-[400px] w-full" />
    </div>
  );
}

function ChannelTable({ data }: { data: ChannelInventorySummary[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Channel</TableHead>
          <TableHead>Type</TableHead>
          <TableHead className="text-right">Products</TableHead>
          <TableHead className="text-right">Allocated</TableHead>
          <TableHead className="text-right">Available</TableHead>
          <TableHead className="text-right">Reserved</TableHead>
          <TableHead className="text-right">Low Stock</TableHead>
          <TableHead>Utilization</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((channel) => {
          const utilization = channel.total_allocated > 0
            ? ((channel.total_allocated - channel.total_available) / channel.total_allocated) * 100
            : 0;

          return (
            <TableRow key={channel.channel_id}>
              <TableCell className="font-medium">
                <div>
                  <div>{channel.channel_name}</div>
                  <div className="text-xs text-muted-foreground">{channel.channel_code}</div>
                </div>
              </TableCell>
              <TableCell>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${channelTypeColors[channel.channel_type] || channelTypeColors.OTHER}`}>
                  {channel.channel_type}
                </span>
              </TableCell>
              <TableCell className="text-right font-mono">{channel.products_count}</TableCell>
              <TableCell className="text-right font-mono">{channel.total_allocated.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono text-green-600">{channel.total_available.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono text-orange-600">{channel.total_reserved.toLocaleString()}</TableCell>
              <TableCell className="text-right">
                {channel.low_stock_count > 0 ? (
                  <span className="inline-flex items-center gap-1 text-amber-600">
                    <AlertTriangle className="h-3 w-3" />
                    {channel.low_stock_count}
                  </span>
                ) : (
                  <span className="text-green-600">-</span>
                )}
              </TableCell>
              <TableCell>
                <div className="w-24">
                  <Progress value={utilization} className="h-2" />
                  <span className="text-xs text-muted-foreground">{utilization.toFixed(0)}%</span>
                </div>
              </TableCell>
            </TableRow>
          );
        })}
        {data.length === 0 && (
          <TableRow>
            <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
              No channel inventory data available
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}

function WarehouseTable({ data }: { data: WarehouseInventorySummary[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Warehouse</TableHead>
          <TableHead className="text-right">Products</TableHead>
          <TableHead className="text-right">Total Qty</TableHead>
          <TableHead className="text-right">Available</TableHead>
          <TableHead className="text-right">Reserved</TableHead>
          <TableHead className="text-right">Low Stock</TableHead>
          <TableHead className="text-right">Channels</TableHead>
          <TableHead>Utilization</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((warehouse) => {
          const utilization = warehouse.total_quantity > 0
            ? ((warehouse.total_quantity - warehouse.total_available) / warehouse.total_quantity) * 100
            : 0;

          return (
            <TableRow key={warehouse.warehouse_id}>
              <TableCell className="font-medium">
                <div>
                  <div>{warehouse.warehouse_name}</div>
                  <div className="text-xs text-muted-foreground">{warehouse.warehouse_code}</div>
                </div>
              </TableCell>
              <TableCell className="text-right font-mono">{warehouse.products_count}</TableCell>
              <TableCell className="text-right font-mono">{warehouse.total_quantity.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono text-green-600">{warehouse.total_available.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono text-orange-600">{warehouse.total_reserved.toLocaleString()}</TableCell>
              <TableCell className="text-right">
                {warehouse.low_stock_count > 0 ? (
                  <span className="inline-flex items-center gap-1 text-amber-600">
                    <AlertTriangle className="h-3 w-3" />
                    {warehouse.low_stock_count}
                  </span>
                ) : (
                  <span className="text-green-600">-</span>
                )}
              </TableCell>
              <TableCell className="text-right font-mono">{warehouse.channels_served}</TableCell>
              <TableCell>
                <div className="w-24">
                  <Progress value={utilization} className="h-2" />
                  <span className="text-xs text-muted-foreground">{utilization.toFixed(0)}%</span>
                </div>
              </TableCell>
            </TableRow>
          );
        })}
        {data.length === 0 && (
          <TableRow>
            <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
              No warehouse inventory data available
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}

function ChannelLocationTable({ data }: { data: ChannelLocationBreakdown[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Channel</TableHead>
          <TableHead>Warehouse</TableHead>
          <TableHead className="text-right">Products</TableHead>
          <TableHead className="text-right">Allocated</TableHead>
          <TableHead className="text-right">Buffer</TableHead>
          <TableHead className="text-right">Reserved</TableHead>
          <TableHead className="text-right">Available</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item, idx) => (
          <TableRow key={`${item.channel_id}-${item.warehouse_id}-${idx}`}>
            <TableCell className="font-medium">
              <div>
                <div>{item.channel_name}</div>
                <div className="text-xs text-muted-foreground">{item.channel_code}</div>
              </div>
            </TableCell>
            <TableCell>
              <div>
                <div>{item.warehouse_name}</div>
                <div className="text-xs text-muted-foreground">{item.warehouse_code}</div>
              </div>
            </TableCell>
            <TableCell className="text-right font-mono">{item.products_count}</TableCell>
            <TableCell className="text-right font-mono">{item.allocated_quantity.toLocaleString()}</TableCell>
            <TableCell className="text-right font-mono text-blue-600">{item.buffer_quantity.toLocaleString()}</TableCell>
            <TableCell className="text-right font-mono text-orange-600">{item.reserved_quantity.toLocaleString()}</TableCell>
            <TableCell className="text-right font-mono text-green-600 font-bold">{item.available_quantity.toLocaleString()}</TableCell>
          </TableRow>
        ))}
        {data.length === 0 && (
          <TableRow>
            <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
              No channel-location inventory data available
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}

export default function ChannelInventoryDashboardPage() {
  const { data, isLoading, error } = useQuery<DashboardData>({
    queryKey: ['channel-inventory-dashboard'],
    queryFn: async () => {
      const { data } = await apiClient.get('/channels/inventory/dashboard');
      return data;
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Channel Inventory Dashboard"
          description="Channel-wise and location-wise inventory visibility"
        />
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Channel Inventory Dashboard"
          description="Channel-wise and location-wise inventory visibility"
        />
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-red-600">Failed to load dashboard data</p>
            <p className="text-sm text-muted-foreground mt-2">Please try refreshing the page</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Channel Inventory Dashboard"
        description="Channel-wise and location-wise inventory visibility"
        actions={
          <Link href="/dashboard/channels/inventory">
            <Button variant="outline">
              <ArrowRightLeft className="mr-2 h-4 w-4" />
              Manage Inventory
            </Button>
          </Link>
        }
      />

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-5">
        <StatCard
          title="Total Channels"
          value={data?.total_channels || 0}
          description="Active sales channels"
          icon={Store}
        />
        <StatCard
          title="Total Warehouses"
          value={data?.total_warehouses || 0}
          description="Active warehouses"
          icon={Warehouse}
        />
        <StatCard
          title="Products Allocated"
          value={data?.total_products_allocated || 0}
          description="Unique products"
          icon={Package}
        />
        <StatCard
          title="Total Allocated"
          value={(data?.total_allocated_quantity || 0).toLocaleString()}
          description="Total units allocated"
          icon={TrendingUp}
        />
        <StatCard
          title="Total Available"
          value={(data?.total_available_quantity || 0).toLocaleString()}
          description="Available for sale"
          icon={TrendingUp}
          trend="up"
        />
      </div>

      {/* Breakdown Tabs */}
      <Tabs defaultValue="by-channel" className="space-y-4">
        <TabsList>
          <TabsTrigger value="by-channel">By Channel</TabsTrigger>
          <TabsTrigger value="by-warehouse">By Warehouse</TabsTrigger>
          <TabsTrigger value="by-channel-location">By Channel & Location</TabsTrigger>
        </TabsList>

        <TabsContent value="by-channel">
          <Card>
            <CardHeader>
              <CardTitle>Inventory by Channel</CardTitle>
              <CardDescription>
                View inventory allocation and availability for each sales channel
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ChannelTable data={data?.by_channel || []} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="by-warehouse">
          <Card>
            <CardHeader>
              <CardTitle>Inventory by Warehouse</CardTitle>
              <CardDescription>
                View inventory levels and channel allocation for each warehouse
              </CardDescription>
            </CardHeader>
            <CardContent>
              <WarehouseTable data={data?.by_warehouse || []} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="by-channel-location">
          <Card>
            <CardHeader>
              <CardTitle>Inventory by Channel & Location</CardTitle>
              <CardDescription>
                Detailed breakdown of inventory allocation per channel-warehouse combination
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ChannelLocationTable data={data?.by_channel_location || []} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
