'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader, StatusBadge } from '@/components/common';
import { partnersApi, PartnerOrder } from '@/lib/api';
import { ShoppingCart, IndianRupee, TrendingUp, Search } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { format } from 'date-fns';
import Link from 'next/link';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(value);
};

export default function PartnerOrdersPage() {
  const [partnerId, setPartnerId] = useState('');
  const [page, setPage] = useState(1);

  // Get list of partners
  const { data: partnersData } = useQuery({
    queryKey: ['partners-list'],
    queryFn: () => partnersApi.list({ size: 100, status: 'ACTIVE' }),
  });

  // Get orders for selected partner
  const { data: ordersData, isLoading } = useQuery({
    queryKey: ['partner-orders', partnerId, page],
    queryFn: () => partnersApi.getPartnerOrders(partnerId, { page, size: 20 }),
    enabled: !!partnerId,
  });

  // Get analytics
  const { data: analytics } = useQuery({
    queryKey: ['partner-analytics'],
    queryFn: () => partnersApi.getAnalytics(),
  });

  // Calculate stats for selected partner
  const selectedPartner = partnersData?.items?.find((p) => p.id === partnerId);
  const totalOrders = ordersData?.items?.length ?? 0;
  const totalSales = ordersData?.items?.reduce((sum: number, o: PartnerOrder) => sum + o.order_amount, 0) ?? 0;
  const totalCommission = ordersData?.items?.reduce((sum: number, o: PartnerOrder) => sum + o.commission_amount, 0) ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Partner Orders"
        description="View orders attributed to community partners"
      />

      {/* Overall Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Partner Orders</CardTitle>
            <ShoppingCart className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics?.total_orders ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              All-time orders via partners
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Partner Sales</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(analytics?.total_sales ?? 0)}</div>
            <p className="text-xs text-muted-foreground">
              Revenue from partner channel
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Commissions Earned</CardTitle>
            <IndianRupee className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(analytics?.total_commissions_paid ?? 0)}</div>
            <p className="text-xs text-muted-foreground">
              Total paid to partners
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Partner Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Select Partner</CardTitle>
          <CardDescription>View orders for a specific community partner</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[300px]">
              <Select value={partnerId} onValueChange={(v) => { setPartnerId(v); setPage(1); }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a partner to view their orders..." />
                </SelectTrigger>
                <SelectContent>
                  {partnersData?.items?.map((partner) => (
                    <SelectItem key={partner.id} value={partner.id}>
                      {partner.full_name} ({partner.partner_code}) - {partner.total_sales_count} orders
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Partner Stats (when selected) */}
      {partnerId && selectedPartner && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground">Partner</div>
              <div className="text-lg font-bold">{selectedPartner.full_name}</div>
              <div className="text-xs text-muted-foreground">{selectedPartner.partner_code}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground">Total Orders</div>
              <div className="text-lg font-bold">{selectedPartner.total_sales_count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground">Total Sales</div>
              <div className="text-lg font-bold">{formatCurrency(selectedPartner.total_sales_value)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground">Commission Earned</div>
              <div className="text-lg font-bold">{formatCurrency(selectedPartner.total_commission_earned)}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Orders Table */}
      {partnerId ? (
        <Card>
          <CardHeader>
            <CardTitle>Order History</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : ordersData?.items && ordersData.items.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Order Number</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Commission</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ordersData.items.map((order: PartnerOrder) => (
                    <TableRow key={order.id}>
                      <TableCell>
                        <Link
                          href={`/dashboard/orders/${order.order_id}`}
                          className="font-medium text-primary hover:underline"
                        >
                          {order.order_number}
                        </Link>
                      </TableCell>
                      <TableCell>{order.customer_name || '-'}</TableCell>
                      <TableCell>{formatCurrency(order.order_amount)}</TableCell>
                      <TableCell className="text-green-600 font-medium">
                        {formatCurrency(order.commission_amount)}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={order.order_status} />
                      </TableCell>
                      <TableCell>
                        {format(new Date(order.created_at), 'MMM d, yyyy')}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-12">
                <ShoppingCart className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <h3 className="mt-4 text-lg font-medium">No Orders Found</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  This partner has not generated any orders yet.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Search className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium">Select a Partner</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Choose a partner from the dropdown to view their order history.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
