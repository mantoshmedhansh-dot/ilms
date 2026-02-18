'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShoppingCart,
  RefreshCw,
  Plus,
  Search,
  Package,
  Clock,
  Truck,
  IndianRupee,
  X,
  AlertCircle,
  Loader2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { toast } from 'sonner';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { dmsApi, dealersApi } from '@/lib/api';
import { DMSOrder, DMSOrderListResponse, Dealer } from '@/types';

function formatCurrency(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 10000000) return `\u20B9${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `\u20B9${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `\u20B9${(num / 1000).toFixed(1)}K`;
  return `\u20B9${num.toFixed(0)}`;
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    NEW: 'bg-blue-100 text-blue-800',
    CONFIRMED: 'bg-indigo-100 text-indigo-800',
    ALLOCATED: 'bg-cyan-100 text-cyan-800',
    SHIPPED: 'bg-purple-100 text-purple-800',
    IN_TRANSIT: 'bg-violet-100 text-violet-800',
    DELIVERED: 'bg-green-100 text-green-800',
    CANCELLED: 'bg-red-100 text-red-800',
    PENDING_PAYMENT: 'bg-yellow-100 text-yellow-800',
    READY_TO_SHIP: 'bg-teal-100 text-teal-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

function getPaymentStatusColor(status: string): string {
  const colors: Record<string, string> = {
    PAID: 'bg-green-100 text-green-800',
    PENDING: 'bg-yellow-100 text-yellow-800',
    PARTIAL: 'bg-orange-100 text-orange-800',
    OVERDUE: 'bg-red-100 text-red-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

interface OrderFormItem {
  product_id: string;
  product_name: string;
  quantity: number;
}

export default function DMSOrdersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dealerFilter, setDealerFilter] = useState<string>('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  // Create order form state
  const [selectedDealerId, setSelectedDealerId] = useState<string>('');
  const [orderItems, setOrderItems] = useState<OrderFormItem[]>([]);
  const [orderNotes, setOrderNotes] = useState('');
  const [newItemProductId, setNewItemProductId] = useState('');
  const [newItemProductName, setNewItemProductName] = useState('');
  const [newItemQty, setNewItemQty] = useState(1);

  const { data: ordersData, isLoading, refetch, isFetching } = useQuery<DMSOrderListResponse>({
    queryKey: ['dms-orders', page, statusFilter, dealerFilter],
    queryFn: () => dmsApi.listOrders({
      page,
      size: 20,
      status: statusFilter !== 'all' ? statusFilter : undefined,
      dealer_id: dealerFilter !== 'all' ? dealerFilter : undefined,
    }),
    staleTime: 2 * 60 * 1000,
  });

  const { data: dealersData } = useQuery({
    queryKey: ['dealers-dropdown'],
    queryFn: () => dealersApi.list({ size: 100 }),
    staleTime: 10 * 60 * 1000,
  });

  const createOrderMutation = useMutation({
    mutationFn: (data: { dealerId: string; items: Array<{ product_id: string; quantity: number }>; notes?: string }) =>
      dmsApi.createOrder(data.dealerId, { items: data.items, notes: data.notes }),
    onSuccess: () => {
      toast.success('B2B Order created successfully');
      queryClient.invalidateQueries({ queryKey: ['dms-orders'] });
      queryClient.invalidateQueries({ queryKey: ['dms-dashboard'] });
      resetCreateForm();
      setShowCreateDialog(false);
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to create order');
    },
  });

  const resetCreateForm = () => {
    setSelectedDealerId('');
    setOrderItems([]);
    setOrderNotes('');
    setNewItemProductId('');
    setNewItemProductName('');
    setNewItemQty(1);
  };

  const handleAddItem = () => {
    if (!newItemProductId.trim()) {
      toast.error('Enter a product ID');
      return;
    }
    if (newItemQty < 1) {
      toast.error('Quantity must be at least 1');
      return;
    }
    setOrderItems([...orderItems, {
      product_id: newItemProductId.trim(),
      product_name: newItemProductName.trim() || newItemProductId.trim(),
      quantity: newItemQty,
    }]);
    setNewItemProductId('');
    setNewItemProductName('');
    setNewItemQty(1);
  };

  const handleRemoveItem = (index: number) => {
    setOrderItems(orderItems.filter((_, i) => i !== index));
  };

  const handleCreateOrder = () => {
    if (!selectedDealerId) {
      toast.error('Select a dealer');
      return;
    }
    if (orderItems.length === 0) {
      toast.error('Add at least one item');
      return;
    }
    createOrderMutation.mutate({
      dealerId: selectedDealerId,
      items: orderItems.map(i => ({ product_id: i.product_id, quantity: i.quantity })),
      notes: orderNotes || undefined,
    });
  };

  const orders = ordersData?.items || [];
  const totalOrders = ordersData?.total || 0;
  const totalPages = Math.ceil(totalOrders / 20);
  const dealers = (dealersData?.items || []) as Dealer[];

  // Compute mini-KPIs from current page
  const pendingCount = orders.filter(o => ['NEW', 'CONFIRMED', 'PENDING_PAYMENT'].includes(o.status)).length;
  const shippedCount = orders.filter(o => ['SHIPPED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY'].includes(o.status)).length;

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 rounded-lg">
            <ShoppingCart className="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">DMS Orders</h1>
            <p className="text-muted-foreground">
              B2B distributor order management
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create B2B Order
          </Button>
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="icon">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* KPI Mini Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-l-4 border-l-indigo-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Total B2B Orders</CardTitle>
            <ShoppingCart className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{totalOrders}</div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-yellow-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Pending</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{pendingCount}</div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-purple-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Shipped</CardTitle>
            <Truck className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{shippedCount}</div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-emerald-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Revenue (Page)</CardTitle>
            <IndianRupee className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">
              {formatCurrency(orders.reduce((sum, o) => sum + Number(o.total_amount || 0), 0))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Bar */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="min-w-[180px]">
              <Label className="text-xs text-muted-foreground mb-1 block">Dealer</Label>
              <Select value={dealerFilter} onValueChange={(v) => { setDealerFilter(v); setPage(1); }}>
                <SelectTrigger>
                  <SelectValue placeholder="All Dealers" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Dealers</SelectItem>
                  {dealers.map(d => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.dealer_code || d.code} - {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[160px]">
              <Label className="text-xs text-muted-foreground mb-1 block">Status</Label>
              <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
                <SelectTrigger>
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="NEW">New</SelectItem>
                  <SelectItem value="CONFIRMED">Confirmed</SelectItem>
                  <SelectItem value="ALLOCATED">Allocated</SelectItem>
                  <SelectItem value="SHIPPED">Shipped</SelectItem>
                  <SelectItem value="IN_TRANSIT">In Transit</SelectItem>
                  <SelectItem value="DELIVERED">Delivered</SelectItem>
                  <SelectItem value="CANCELLED">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Orders Table */}
      <Card>
        <CardContent className="pt-4">
          {orders.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-3 font-medium text-muted-foreground">Order #</th>
                      <th className="pb-3 font-medium text-muted-foreground">Dealer</th>
                      <th className="pb-3 font-medium text-muted-foreground text-right">Total</th>
                      <th className="pb-3 font-medium text-muted-foreground text-center">Status</th>
                      <th className="pb-3 font-medium text-muted-foreground text-center">Payment</th>
                      <th className="pb-3 font-medium text-muted-foreground text-right">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((order) => (
                      <tr key={order.id} className="border-b last:border-0 hover:bg-muted/50">
                        <td className="py-3 font-mono text-xs font-medium">{order.order_number}</td>
                        <td className="py-3">
                          <div>
                            <span className="font-medium">{order.dealer_name}</span>
                            <span className="text-xs text-muted-foreground ml-2">{order.dealer_code}</span>
                          </div>
                        </td>
                        <td className="py-3 text-right tabular-nums font-semibold">
                          {formatCurrency(order.total_amount)}
                        </td>
                        <td className="py-3 text-center">
                          <Badge variant="outline" className={`text-[10px] ${getStatusColor(order.status)}`}>
                            {order.status.replace(/_/g, ' ')}
                          </Badge>
                        </td>
                        <td className="py-3 text-center">
                          <Badge variant="outline" className={`text-[10px] ${getPaymentStatusColor(order.payment_status)}`}>
                            {order.payment_status || 'N/A'}
                          </Badge>
                        </td>
                        <td className="py-3 text-right text-muted-foreground text-xs">
                          {order.created_at ? new Date(order.created_at).toLocaleDateString('en-IN') : ''}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {totalPages} ({totalOrders} orders)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <Package className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-muted-foreground">No B2B orders found</p>
              <Button variant="outline" className="mt-3" onClick={() => setShowCreateDialog(true)}>
                <Plus className="h-4 w-4 mr-2" /> Create First Order
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create B2B Order Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={(open) => { if (!open) { resetCreateForm(); } setShowCreateDialog(open); }}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShoppingCart className="h-5 w-5 text-indigo-600" />
              Create B2B Order
            </DialogTitle>
            <DialogDescription>
              Select a dealer and add products. Dealer-specific pricing will be auto-applied.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Step 1: Select Dealer */}
            <div>
              <Label>Dealer *</Label>
              <Select value={selectedDealerId} onValueChange={setSelectedDealerId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a dealer..." />
                </SelectTrigger>
                <SelectContent>
                  {dealers.filter(d => d.status === 'ACTIVE').map(d => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.dealer_code || d.code} - {d.name}
                      {d.available_credit !== undefined && (
                        <span className="text-muted-foreground ml-2">
                          (Credit: {formatCurrency(d.available_credit)})
                        </span>
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Step 2: Add Products */}
            <div className="space-y-2">
              <Label>Products *</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="Product ID (UUID)"
                  value={newItemProductId}
                  onChange={e => setNewItemProductId(e.target.value)}
                  className="flex-1"
                />
                <Input
                  placeholder="Name (optional)"
                  value={newItemProductName}
                  onChange={e => setNewItemProductName(e.target.value)}
                  className="w-36"
                />
                <Input
                  type="number"
                  placeholder="Qty"
                  value={newItemQty}
                  onChange={e => setNewItemQty(parseInt(e.target.value) || 1)}
                  min={1}
                  className="w-20"
                />
                <Button type="button" variant="outline" size="icon" onClick={handleAddItem}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>

              {/* Added Items */}
              {orderItems.length > 0 && (
                <div className="border rounded-md divide-y">
                  {orderItems.map((item, index) => (
                    <div key={index} className="flex items-center justify-between px-3 py-2 text-sm">
                      <div className="flex-1">
                        <span className="font-medium">{item.product_name}</span>
                        <span className="text-xs text-muted-foreground ml-2 font-mono">
                          {item.product_id.substring(0, 8)}...
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">x{item.quantity}</Badge>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => handleRemoveItem(index)}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Notes */}
            <div>
              <Label>Notes (optional)</Label>
              <Textarea
                placeholder="Order notes, special instructions..."
                value={orderNotes}
                onChange={e => setOrderNotes(e.target.value)}
                rows={2}
              />
            </div>

            {/* Credit check info */}
            {selectedDealerId && (
              <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-md">
                <AlertCircle className="h-4 w-4 text-blue-600 mt-0.5" />
                <p className="text-xs text-blue-700">
                  Dealer-specific and tier pricing will be auto-applied. Credit limit will be checked before order confirmation.
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => { resetCreateForm(); setShowCreateDialog(false); }}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateOrder}
              disabled={createOrderMutation.isPending || !selectedDealerId || orderItems.length === 0}
            >
              {createOrderMutation.isPending ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Creating...</>
              ) : (
                <><ShoppingCart className="h-4 w-4 mr-2" /> Create Order</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
