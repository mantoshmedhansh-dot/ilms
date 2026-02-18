'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  TrendingUp,
  Plus,
  RefreshCw,
  IndianRupee,
  ShoppingCart,
  Loader2,
  ChevronLeft,
  ChevronRight,
  X,
  Package,
} from 'lucide-react';

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
import { dmsApi, dealersApi, productsApi } from '@/lib/api';
import { DMSSecondarySale, DMSSecondarySaleListResponse, Dealer, RetailerOutlet, Product } from '@/types';

function formatCurrency(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 10000000) return `\u20B9${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `\u20B9${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `\u20B9${(num / 1000).toFixed(1)}K`;
  return `\u20B9${num.toFixed(0)}`;
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    RECORDED: 'bg-blue-100 text-blue-800',
    VERIFIED: 'bg-green-100 text-green-800',
    PENDING: 'bg-yellow-100 text-yellow-800',
    REJECTED: 'bg-red-100 text-red-800',
    CANCELLED: 'bg-red-100 text-red-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

interface SaleFormItem {
  product_id: string;
  product_name: string;
  quantity: number;
}

export default function DMSSecondarySalesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [showRecordDialog, setShowRecordDialog] = useState(false);

  // Record sale form state
  const [selectedDealerId, setSelectedDealerId] = useState<string>('');
  const [selectedRetailerId, setSelectedRetailerId] = useState<string>('');
  const [saleItems, setSaleItems] = useState<SaleFormItem[]>([]);
  const [saleNotes, setSaleNotes] = useState('');
  const [selectedProductId, setSelectedProductId] = useState<string>('');
  const [newItemQty, setNewItemQty] = useState(1);

  // Queries
  const { data: salesData, isLoading, refetch, isFetching } = useQuery<DMSSecondarySaleListResponse>({
    queryKey: ['dms-secondary-sales', page],
    queryFn: () => dmsApi.listSecondarySales({ page, size: 20 }),
    staleTime: 2 * 60 * 1000,
  });

  const { data: dealersData } = useQuery({
    queryKey: ['dealers-dropdown'],
    queryFn: () => dealersApi.list({ size: 100 }),
    staleTime: 10 * 60 * 1000,
  });

  const { data: retailersData } = useQuery({
    queryKey: ['dms-retailers', selectedDealerId],
    queryFn: () => dmsApi.listRetailers({ dealer_id: selectedDealerId, size: 200 }),
    enabled: !!selectedDealerId,
    staleTime: 5 * 60 * 1000,
  });

  const { data: productsData } = useQuery({
    queryKey: ['products-dropdown'],
    queryFn: () => productsApi.list({ size: 200 }),
    staleTime: 10 * 60 * 1000,
  });

  const createSaleMutation = useMutation({
    mutationFn: (data: { dealer_id: string; retailer_id: string; items: Array<{ product_id: string; quantity: number }>; notes?: string }) =>
      dmsApi.createSecondarySale(data),
    onSuccess: () => {
      toast.success('Secondary sale recorded successfully');
      queryClient.invalidateQueries({ queryKey: ['dms-secondary-sales'] });
      queryClient.invalidateQueries({ queryKey: ['dms-dashboard'] });
      resetForm();
      setShowRecordDialog(false);
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to record sale');
    },
  });

  const resetForm = () => {
    setSelectedDealerId('');
    setSelectedRetailerId('');
    setSaleItems([]);
    setSaleNotes('');
    setSelectedProductId('');
    setNewItemQty(1);
  };

  const handleDealerChange = (dealerId: string) => {
    setSelectedDealerId(dealerId);
    setSelectedRetailerId('');
  };

  const handleAddItem = () => {
    if (!selectedProductId) {
      toast.error('Select a product');
      return;
    }
    if (newItemQty < 1) {
      toast.error('Quantity must be at least 1');
      return;
    }
    const product = products.find(p => p.id === selectedProductId);
    if (saleItems.some(item => item.product_id === selectedProductId)) {
      toast.error('Product already added');
      return;
    }
    setSaleItems([...saleItems, {
      product_id: selectedProductId,
      product_name: product?.name || selectedProductId,
      quantity: newItemQty,
    }]);
    setSelectedProductId('');
    setNewItemQty(1);
  };

  const handleRemoveItem = (index: number) => {
    setSaleItems(saleItems.filter((_, i) => i !== index));
  };

  const handleRecordSale = () => {
    if (!selectedDealerId) {
      toast.error('Select a dealer');
      return;
    }
    if (!selectedRetailerId) {
      toast.error('Select a retailer');
      return;
    }
    if (saleItems.length === 0) {
      toast.error('Add at least one product');
      return;
    }
    createSaleMutation.mutate({
      dealer_id: selectedDealerId,
      retailer_id: selectedRetailerId,
      items: saleItems.map(i => ({ product_id: i.product_id, quantity: i.quantity })),
      notes: saleNotes || undefined,
    });
  };

  const sales = salesData?.items || [];
  const totalSales = salesData?.total || 0;
  const totalPages = Math.ceil(totalSales / 20);
  const summary = salesData?.summary;
  const dealers = (dealersData?.items || []) as Dealer[];
  const retailers = (retailersData?.items || []) as RetailerOutlet[];
  const products = (productsData?.items || []) as Product[];

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24" />)}
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
          <div className="p-2 bg-emerald-100 rounded-lg">
            <TrendingUp className="h-6 w-6 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Secondary Sales</h1>
            <p className="text-muted-foreground">
              Dealer-to-retailer sales tracking
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setShowRecordDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Record Sale
          </Button>
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="icon">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-l-4 border-l-emerald-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Total Secondary Sales</CardTitle>
            <IndianRupee className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">
              {formatCurrency(summary?.total_sales)}
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Volume This Month</CardTitle>
            <Package className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">
              {summary?.volume_this_month?.toLocaleString('en-IN') ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-purple-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Sales This Month</CardTitle>
            <ShoppingCart className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">
              {summary?.count_this_month ?? 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Sales Table */}
      <Card>
        <CardContent className="pt-4">
          {sales.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-3 font-medium text-muted-foreground">Date</th>
                      <th className="pb-3 font-medium text-muted-foreground">Order #</th>
                      <th className="pb-3 font-medium text-muted-foreground">Dealer</th>
                      <th className="pb-3 font-medium text-muted-foreground">Retailer</th>
                      <th className="pb-3 font-medium text-muted-foreground text-right">Amount</th>
                      <th className="pb-3 font-medium text-muted-foreground text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sales.map((sale) => (
                      <tr key={sale.id} className="border-b last:border-0 hover:bg-muted/50">
                        <td className="py-3 text-muted-foreground text-xs">
                          {sale.created_at ? new Date(sale.created_at).toLocaleDateString('en-IN') : '-'}
                        </td>
                        <td className="py-3 font-mono text-xs font-medium">{sale.order_number}</td>
                        <td className="py-3">
                          <span className="font-medium">{sale.dealer_name}</span>
                        </td>
                        <td className="py-3">
                          <span className="text-muted-foreground">{sale.retailer_name}</span>
                        </td>
                        <td className="py-3 text-right tabular-nums font-semibold">
                          {formatCurrency(sale.total_amount)}
                        </td>
                        <td className="py-3 text-center">
                          <Badge variant="outline" className={`text-[10px] ${getStatusColor(sale.status)}`}>
                            {sale.status.replace(/_/g, ' ')}
                          </Badge>
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
                    Page {page} of {totalPages} ({totalSales} sales)
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
              <p className="text-muted-foreground">No secondary sales recorded yet</p>
              <Button variant="outline" className="mt-3" onClick={() => setShowRecordDialog(true)}>
                <Plus className="h-4 w-4 mr-2" /> Record First Sale
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Record Sale Dialog */}
      <Dialog open={showRecordDialog} onOpenChange={(open) => { if (!open) { resetForm(); } setShowRecordDialog(open); }}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-emerald-600" />
              Record Sale
            </DialogTitle>
            <DialogDescription>
              Record a dealer-to-retailer secondary sale with product details.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Select Dealer */}
            <div>
              <Label>Dealer *</Label>
              <Select value={selectedDealerId} onValueChange={handleDealerChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a dealer..." />
                </SelectTrigger>
                <SelectContent>
                  {dealers.filter(d => d.status === 'ACTIVE').map(d => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.dealer_code || d.code} - {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Select Retailer (dependent on dealer) */}
            <div>
              <Label>Retailer *</Label>
              <Select
                value={selectedRetailerId}
                onValueChange={setSelectedRetailerId}
                disabled={!selectedDealerId}
              >
                <SelectTrigger>
                  <SelectValue placeholder={selectedDealerId ? 'Select a retailer...' : 'Select a dealer first'} />
                </SelectTrigger>
                <SelectContent>
                  {retailers.filter(r => r.status === 'ACTIVE').map(r => (
                    <SelectItem key={r.id} value={r.id}>
                      {r.outlet_code} - {r.name}
                    </SelectItem>
                  ))}
                  {selectedDealerId && retailers.length === 0 && (
                    <div className="px-2 py-4 text-sm text-muted-foreground text-center">
                      No retailers found for this dealer
                    </div>
                  )}
                </SelectContent>
              </Select>
            </div>

            {/* Add Products */}
            <div className="space-y-2">
              <Label>Products *</Label>
              <div className="flex gap-2">
                <div className="flex-1">
                  <Select value={selectedProductId} onValueChange={setSelectedProductId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select product..." />
                    </SelectTrigger>
                    <SelectContent>
                      {products.map(p => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.sku} - {p.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
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
              {saleItems.length > 0 && (
                <div className="border rounded-md divide-y">
                  {saleItems.map((item, index) => (
                    <div key={index} className="flex items-center justify-between px-3 py-2 text-sm">
                      <div className="flex-1">
                        <span className="font-medium">{item.product_name}</span>
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
                placeholder="Sale notes, remarks..."
                value={saleNotes}
                onChange={e => setSaleNotes(e.target.value)}
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => { resetForm(); setShowRecordDialog(false); }}>
              Cancel
            </Button>
            <Button
              onClick={handleRecordSale}
              disabled={createSaleMutation.isPending || !selectedDealerId || !selectedRetailerId || saleItems.length === 0}
            >
              {createSaleMutation.isPending ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Recording...</>
              ) : (
                <><TrendingUp className="h-4 w-4 mr-2" /> Record Sale</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
