'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  BarChart3,
  DollarSign,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Package,
  Loader2,
  RefreshCw,
  ArrowLeft,
} from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import { channelsApi, productsApi, categoriesApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Label } from '@/components/ui/label';

interface Category {
  id: string;
  name: string;
  slug: string;
}

interface Product {
  id: string;
  name: string;
  sku: string;
  mrp: number;
}

interface Channel {
  id: string;
  code: string;
  name: string;
  type: string;
}

interface ChannelPricing {
  channel_id: string;
  channel_name: string;
  channel_code: string;
  mrp: number;
  selling_price: number;
  transfer_price?: number;
  discount_percentage?: number;
  max_discount_percentage?: number;
  is_active: boolean;
}

interface ProductComparisonRow {
  product_id: string;
  product_name: string;
  product_sku: string;
  master_mrp: number;
  channels: Record<string, ChannelPricing | null>;
  min_price?: number;
  max_price?: number;
  price_variance?: number;
}

export default function PriceComparisonPage() {
  // Cascading category selection
  const [parentCategoryId, setParentCategoryId] = useState<string>('');
  const [subcategoryId, setSubcategoryId] = useState<string>('');

  // Fetch channels
  const { data: channels = [] } = useQuery({
    queryKey: ['channels-dropdown'],
    queryFn: () => channelsApi.dropdown(),
  });

  // Fetch ROOT categories
  const { data: parentCategoriesData } = useQuery({
    queryKey: ['categories-roots'],
    queryFn: () => categoriesApi.getRoots(),
  });
  const parentCategories: Category[] = parentCategoriesData?.items || [];

  // Fetch subcategories
  const { data: subcategoriesData, isLoading: subcategoriesLoading } = useQuery({
    queryKey: ['categories-children', parentCategoryId],
    queryFn: () => categoriesApi.getChildren(parentCategoryId),
    enabled: !!parentCategoryId,
  });
  const subcategories: Category[] = subcategoriesData?.items || [];

  // Fetch products in subcategory
  const { data: productsData, isLoading: productsLoading } = useQuery({
    queryKey: ['products-compare', subcategoryId],
    queryFn: () => productsApi.list({ size: 50, category_id: subcategoryId }),
    enabled: !!subcategoryId,
  });
  const products: Product[] = productsData?.items || [];

  // Fetch pricing for all channels for products in subcategory
  const productIds = useMemo(() => products.map(p => p.id), [products]);

  const { data: pricingData, isLoading: pricingLoading, refetch } = useQuery({
    queryKey: ['pricing-comparison', productIds],
    queryFn: async () => {
      if (productIds.length === 0) return [];
      // Fetch pricing from each channel
      const allPricing: Array<{
        channel_id: string;
        channel_name: string;
        channel_code: string;
        product_id: string;
        mrp: number;
        selling_price: number;
        transfer_price?: number;
        max_discount_percentage?: number;
        is_active: boolean;
      }> = [];

      for (const channel of channels as Channel[]) {
        try {
          const channelPricing = await channelsApi.pricing.list(channel.id, { limit: 200 });
          const items = channelPricing.items || [];
          for (const item of items) {
            if (productIds.includes(item.product_id)) {
              allPricing.push({
                channel_id: channel.id,
                channel_name: channel.name,
                channel_code: channel.code,
                product_id: item.product_id,
                mrp: item.mrp,
                selling_price: item.selling_price,
                transfer_price: item.transfer_price,
                max_discount_percentage: item.max_discount_percentage,
                is_active: item.is_active,
              });
            }
          }
        } catch (e) {
          console.error(`Failed to fetch pricing for channel ${channel.name}:`, e);
        }
      }
      return allPricing;
    },
    enabled: productIds.length > 0 && channels.length > 0,
    staleTime: 60000, // 1 minute
  });

  // Build comparison data
  const comparisonData: ProductComparisonRow[] = useMemo(() => {
    if (!products.length || !pricingData) return [];

    return products.map(product => {
      const channelPrices: Record<string, ChannelPricing | null> = {};
      const prices: number[] = [];

      for (const channel of channels as Channel[]) {
        const pricing = pricingData.find(
          (p: { channel_id: string; product_id: string }) => p.channel_id === channel.id && p.product_id === product.id
        );
        if (pricing) {
          channelPrices[channel.code] = {
            channel_id: channel.id,
            channel_name: channel.name,
            channel_code: channel.code,
            mrp: pricing.mrp,
            selling_price: pricing.selling_price,
            transfer_price: pricing.transfer_price,
            max_discount_percentage: pricing.max_discount_percentage,
            is_active: pricing.is_active,
          };
          prices.push(pricing.selling_price);
        } else {
          channelPrices[channel.code] = null;
        }
      }

      const min_price = prices.length > 0 ? Math.min(...prices) : undefined;
      const max_price = prices.length > 0 ? Math.max(...prices) : undefined;
      const price_variance = min_price && max_price ? ((max_price - min_price) / min_price) * 100 : undefined;

      return {
        product_id: product.id,
        product_name: product.name,
        product_sku: product.sku,
        master_mrp: product.mrp,
        channels: channelPrices,
        min_price,
        max_price,
        price_variance,
      };
    });
  }, [products, pricingData, channels]);

  // Calculate stats
  const stats = useMemo(() => {
    const productsWithPricing = comparisonData.filter(row =>
      Object.values(row.channels).some(c => c !== null)
    ).length;

    const variances = comparisonData
      .filter(row => row.price_variance !== undefined)
      .map(row => row.price_variance as number);

    const avgVariance = variances.length > 0
      ? variances.reduce((a, b) => a + b, 0) / variances.length
      : 0;

    const highVarianceCount = variances.filter(v => v > 15).length;

    const missingPricing = comparisonData.reduce((count, row) => {
      const missing = Object.values(row.channels).filter(c => c === null).length;
      return count + (missing > 0 ? 1 : 0);
    }, 0);

    return {
      totalProducts: products.length,
      productsWithPricing,
      avgVariance,
      highVarianceCount,
      missingPricing,
    };
  }, [comparisonData, products]);

  // Dynamic columns based on channels
  const columns: ColumnDef<ProductComparisonRow>[] = useMemo(() => {
    const baseColumns: ColumnDef<ProductComparisonRow>[] = [
      {
        accessorKey: 'product_name',
        header: 'Product',
        cell: ({ row }) => (
          <div>
            <div className="font-medium">{row.original.product_name}</div>
            <div className="text-sm text-muted-foreground font-mono">{row.original.product_sku}</div>
          </div>
        ),
      },
      {
        accessorKey: 'master_mrp',
        header: 'MRP',
        cell: ({ row }) => (
          <span className="font-mono text-sm">{formatCurrency(row.original.master_mrp)}</span>
        ),
      },
    ];

    // Add a column for each channel
    const channelColumns: ColumnDef<ProductComparisonRow>[] = (channels as Channel[]).map(channel => ({
      id: `channel_${channel.code}`,
      header: () => (
        <div className="text-center">
          <div className="font-medium">{channel.name}</div>
          <div className="text-xs text-muted-foreground">{channel.code}</div>
        </div>
      ),
      cell: ({ row }) => {
        const pricing = row.original.channels[channel.code];
        if (!pricing) {
          return (
            <div className="text-center">
              <span className="text-muted-foreground text-xs">Not Set</span>
            </div>
          );
        }
        const discount = pricing.mrp > 0
          ? ((pricing.mrp - pricing.selling_price) / pricing.mrp) * 100
          : 0;
        const isLowest = pricing.selling_price === row.original.min_price && row.original.min_price !== row.original.max_price;
        const isHighest = pricing.selling_price === row.original.max_price && row.original.min_price !== row.original.max_price;

        return (
          <div className="text-center">
            <div className={`font-mono text-sm font-medium ${isLowest ? 'text-green-600' : isHighest ? 'text-red-600' : ''}`}>
              {formatCurrency(pricing.selling_price)}
              {isLowest && <TrendingDown className="inline h-3 w-3 ml-1" />}
              {isHighest && <TrendingUp className="inline h-3 w-3 ml-1" />}
            </div>
            <div className="text-xs text-muted-foreground">
              {discount > 0 ? `${discount.toFixed(1)}% off` : '-'}
            </div>
            {!pricing.is_active && (
              <Badge variant="secondary" className="text-xs">Inactive</Badge>
            )}
          </div>
        );
      },
    }));

    // Variance column
    const varianceColumn: ColumnDef<ProductComparisonRow> = {
      id: 'variance',
      header: 'Variance',
      cell: ({ row }) => {
        const variance = row.original.price_variance;
        if (variance === undefined) {
          return <span className="text-muted-foreground">-</span>;
        }
        const isHigh = variance > 15;
        return (
          <div className="text-center">
            <span className={`font-medium ${isHigh ? 'text-orange-600' : 'text-green-600'}`}>
              {variance.toFixed(1)}%
            </span>
            {isHigh && <AlertTriangle className="inline h-3 w-3 ml-1 text-orange-600" />}
          </div>
        );
      },
    };

    return [...baseColumns, ...channelColumns, varianceColumn];
  }, [channels]);

  // Handlers
  const handleParentCategoryChange = (value: string) => {
    setParentCategoryId(value);
    setSubcategoryId('');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cross-Channel Price Comparison"
        description="Compare product pricing across all sales channels"
        actions={
          <div className="flex gap-2">
            <Link href="/dashboard/channels/pricing">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Pricing
              </Button>
            </Link>
            {subcategoryId && (
              <Button
                variant="outline"
                onClick={() => refetch()}
                disabled={pricingLoading}
              >
                {pricingLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Refresh
              </Button>
            )}
          </div>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Products</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalProducts}</div>
            <p className="text-xs text-muted-foreground">In selected subcategory</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">With Pricing</CardTitle>
            <DollarSign className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.productsWithPricing}</div>
            <p className="text-xs text-muted-foreground">Have at least 1 channel</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Variance</CardTitle>
            <BarChart3 className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats.avgVariance.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">Price difference across channels</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">High Variance</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats.highVarianceCount}</div>
            <p className="text-xs text-muted-foreground">Products with &gt;15% variance</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Missing Pricing</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.missingPricing}</div>
            <p className="text-xs text-muted-foreground">Products missing channels</p>
          </CardContent>
        </Card>
      </div>

      {/* Category Selection */}
      <div className="flex gap-4 flex-wrap items-end">
        {/* Parent Category */}
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Parent Category</Label>
          <Select value={parentCategoryId || "all"} onValueChange={(v) => handleParentCategoryChange(v === "all" ? "" : v)}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select Parent" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Select Parent</SelectItem>
              {parentCategories.map((category) => (
                <SelectItem key={category.id} value={category.id}>
                  {category.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Subcategory */}
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Subcategory</Label>
          <Select
            value={subcategoryId || "all"}
            onValueChange={(v) => setSubcategoryId(v === "all" ? "" : v)}
            disabled={!parentCategoryId}
          >
            <SelectTrigger className="w-[220px]">
              <SelectValue placeholder={parentCategoryId ? "Select Subcategory" : "Select parent first"} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Select Subcategory</SelectItem>
              {subcategoriesLoading ? (
                <SelectItem value="loading" disabled>Loading...</SelectItem>
              ) : subcategories.length === 0 ? (
                <SelectItem value="none" disabled>No subcategories</SelectItem>
              ) : (
                subcategories.map((category) => (
                  <SelectItem key={category.id} value={category.id}>
                    {category.name}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </div>

        {/* Products count */}
        {subcategoryId && (
          <div className="text-sm text-muted-foreground self-end pb-2">
            {productsLoading ? 'Loading...' : `${products.length} products`}
          </div>
        )}
      </div>

      {/* Comparison Table */}
      {!subcategoryId ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">Select a Category</p>
            <p className="text-sm text-muted-foreground">Choose a parent category and subcategory to compare pricing across channels</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {/* Legend */}
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1">
              <TrendingDown className="h-4 w-4 text-green-600" />
              <span className="text-muted-foreground">Lowest Price</span>
            </div>
            <div className="flex items-center gap-1">
              <TrendingUp className="h-4 w-4 text-red-600" />
              <span className="text-muted-foreground">Highest Price</span>
            </div>
            <div className="flex items-center gap-1">
              <AlertTriangle className="h-4 w-4 text-orange-600" />
              <span className="text-muted-foreground">High Variance (&gt;15%)</span>
            </div>
          </div>

          <DataTable
            columns={columns}
            data={comparisonData}
            isLoading={productsLoading || pricingLoading}
            searchKey="product_name"
            searchPlaceholder="Search products..."
          />
        </div>
      )}
    </div>
  );
}
