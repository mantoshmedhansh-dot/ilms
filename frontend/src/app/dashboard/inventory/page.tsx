'use client';

import { useQuery } from '@tanstack/react-query';
import { Package, Warehouse, ArrowLeftRight, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/common';
import { inventoryApi } from '@/lib/api';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  href: string;
  isLoading?: boolean;
}

function StatCard({ title, value, icon, href, isLoading }: StatCardProps) {
  return (
    <Link href={href}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          <div className="text-muted-foreground">{icon}</div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-8 w-20" />
          ) : (
            <div className="text-2xl font-bold">{value}</div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

export default function InventoryPage() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ['inventory-summary'],
    queryFn: inventoryApi.getStockSummary,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Inventory"
        description="Monitor and manage your stock levels"
        actions={
          <Button asChild>
            <Link href="/dashboard/inventory/transfers/new">
              <ArrowLeftRight className="mr-2 h-4 w-4" />
              Create Transfer
            </Link>
          </Button>
        }
      />

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Stock Items"
          value={summary?.total_items?.toLocaleString() ?? 0}
          icon={<Package className="h-4 w-4" />}
          href="/dashboard/inventory/stock-items"
          isLoading={isLoading}
        />
        <StatCard
          title="Warehouses"
          value={summary?.total_warehouses ?? 0}
          icon={<Warehouse className="h-4 w-4" />}
          href="/dashboard/inventory/warehouses"
          isLoading={isLoading}
        />
        <StatCard
          title="Pending Transfers"
          value={summary?.pending_transfers ?? 0}
          icon={<ArrowLeftRight className="h-4 w-4" />}
          href="/dashboard/inventory/transfers"
          isLoading={isLoading}
        />
        <StatCard
          title="Low Stock Alerts"
          value={summary?.low_stock_items ?? 0}
          icon={<AlertTriangle className="h-4 w-4 text-orange-500" />}
          href="/dashboard/inventory?filter=low_stock"
          isLoading={isLoading}
        />
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <Link
              href="/dashboard/inventory/warehouses"
              className="flex items-center gap-3 rounded-lg border p-4 hover:bg-accent transition-colors"
            >
              <Warehouse className="h-8 w-8 text-muted-foreground" />
              <div>
                <p className="font-medium">Manage Warehouses</p>
                <p className="text-sm text-muted-foreground">View and edit warehouse details</p>
              </div>
            </Link>
            <Link
              href="/dashboard/inventory/transfers"
              className="flex items-center gap-3 rounded-lg border p-4 hover:bg-accent transition-colors"
            >
              <ArrowLeftRight className="h-8 w-8 text-muted-foreground" />
              <div>
                <p className="font-medium">Stock Transfers</p>
                <p className="text-sm text-muted-foreground">Move stock between warehouses</p>
              </div>
            </Link>
            <Link
              href="/dashboard/inventory/adjustments"
              className="flex items-center gap-3 rounded-lg border p-4 hover:bg-accent transition-colors"
            >
              <Package className="h-8 w-8 text-muted-foreground" />
              <div>
                <p className="font-medium">Stock Adjustments</p>
                <p className="text-sm text-muted-foreground">Reconcile inventory counts</p>
              </div>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
