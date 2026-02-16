'use client';

import { useQuery } from '@tanstack/react-query';
import {
  Boxes,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  TrendingDown,
  Calculator,
  Package,
  ArrowRight,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { snopApi } from '@/lib/api';

function formatNumber(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 100000) return `${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toFixed(0);
}

export default function InventoryOptimizationPage() {
  const { data: optimizations, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['snop-inventory-optimizations'],
    queryFn: async () => {
      try {
        return await snopApi.getOptimizations();
      } catch {
        return { items: [], total: 0 };
      }
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-64" />
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
          <div className="p-2 bg-amber-100 rounded-lg">
            <Boxes className="h-6 w-6 text-amber-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Inventory Optimization</h1>
            <p className="text-muted-foreground">
              AI-recommended safety stock, reorder points, and EOQ
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button>
            <Calculator className="h-4 w-4 mr-2" />
            Run Optimization
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <span className="text-sm text-muted-foreground">Below Safety Stock</span>
            </div>
            <p className="text-2xl font-bold mt-2 text-red-600">
              {optimizations?.items?.filter((o: any) => o.current_stock < o.recommended_safety_stock).length || 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-amber-600" />
              <span className="text-sm text-muted-foreground">Near Reorder Point</span>
            </div>
            <p className="text-2xl font-bold mt-2 text-amber-600">
              {optimizations?.items?.filter((o: any) =>
                o.current_stock <= o.recommended_reorder_point &&
                o.current_stock >= o.recommended_safety_stock
              ).length || 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span className="text-sm text-muted-foreground">Optimal Stock</span>
            </div>
            <p className="text-2xl font-bold mt-2 text-green-600">
              {optimizations?.items?.filter((o: any) => o.current_stock > o.recommended_reorder_point).length || 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Calculator className="h-4 w-4 text-blue-600" />
              <span className="text-sm text-muted-foreground">Potential Savings</span>
            </div>
            <p className="text-2xl font-bold mt-2">
              {formatNumber(optimizations?.potential_savings || 0)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Optimization Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Optimization Recommendations</CardTitle>
          <CardDescription>AI-calculated inventory parameters per product-warehouse</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead>Warehouse</TableHead>
                <TableHead className="text-right">Current Stock</TableHead>
                <TableHead className="text-right">Safety Stock</TableHead>
                <TableHead className="text-right">Reorder Point</TableHead>
                <TableHead className="text-right">EOQ</TableHead>
                <TableHead>Status</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {optimizations?.items?.length > 0 ? (
                optimizations.items.map((opt: any) => {
                  const isBelowSafety = opt.current_stock < opt.recommended_safety_stock;
                  const isNearReorder = opt.current_stock <= opt.recommended_reorder_point && !isBelowSafety;

                  return (
                    <TableRow key={opt.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{opt.product_name}</p>
                          <p className="text-xs text-muted-foreground">{opt.sku}</p>
                        </div>
                      </TableCell>
                      <TableCell>{opt.warehouse_name}</TableCell>
                      <TableCell className="text-right font-medium">
                        {opt.current_stock?.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right">
                        {opt.recommended_safety_stock?.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right">
                        {opt.recommended_reorder_point?.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right">
                        {opt.recommended_eoq?.toLocaleString()}
                      </TableCell>
                      <TableCell>
                        {isBelowSafety ? (
                          <Badge variant="destructive">Critical</Badge>
                        ) : isNearReorder ? (
                          <Badge variant="secondary">Reorder</Badge>
                        ) : (
                          <Badge variant="outline">Optimal</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {(isBelowSafety || isNearReorder) && (
                          <Button variant="ghost" size="sm">
                            <ArrowRight className="h-4 w-4" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                    <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No optimization data available</p>
                    <p className="text-sm">Run optimization to calculate recommended inventory levels</p>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>About Inventory Optimization</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-4 bg-muted/50 rounded-lg">
              <h4 className="font-semibold flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                Safety Stock
              </h4>
              <p className="text-sm text-muted-foreground mt-1">
                Buffer stock to protect against demand variability and supply delays.
                Calculated based on service level targets and demand volatility.
              </p>
            </div>
            <div className="p-4 bg-muted/50 rounded-lg">
              <h4 className="font-semibold flex items-center gap-2">
                <TrendingDown className="h-4 w-4 text-blue-600" />
                Reorder Point
              </h4>
              <p className="text-sm text-muted-foreground mt-1">
                Stock level at which a new order should be placed.
                Accounts for lead time demand plus safety stock.
              </p>
            </div>
            <div className="p-4 bg-muted/50 rounded-lg">
              <h4 className="font-semibold flex items-center gap-2">
                <Calculator className="h-4 w-4 text-green-600" />
                Economic Order Quantity (EOQ)
              </h4>
              <p className="text-sm text-muted-foreground mt-1">
                Optimal order quantity that minimizes total inventory costs
                including ordering and holding costs.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
