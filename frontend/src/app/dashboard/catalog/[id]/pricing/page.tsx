'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Save, Loader2, DollarSign, Percent, Calendar, Check } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { PageHeader } from '@/components/common';
import { productsApi, channelsApi } from '@/lib/api';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
};

interface ChannelPricing {
  channel_id: string;
  channel_name: string;
  channel_type: string;
  mrp: number;
  selling_price: number;
  is_active: boolean;
  effective_from?: string;
  effective_to?: string;
}

// Default channels for pricing
const defaultChannels: ChannelPricing[] = [
  {
    channel_id: 'D2C',
    channel_name: 'D2C Website',
    channel_type: 'D2C',
    mrp: 0,
    selling_price: 0,
    is_active: true,
  },
  {
    channel_id: 'B2B',
    channel_name: 'B2B / Dealer',
    channel_type: 'B2B',
    mrp: 0,
    selling_price: 0,
    is_active: false,
  },
  {
    channel_id: 'AMAZON',
    channel_name: 'Amazon',
    channel_type: 'MARKETPLACE',
    mrp: 0,
    selling_price: 0,
    is_active: false,
  },
  {
    channel_id: 'FLIPKART',
    channel_name: 'Flipkart',
    channel_type: 'MARKETPLACE',
    mrp: 0,
    selling_price: 0,
    is_active: false,
  },
  {
    channel_id: 'FRANCHISEE',
    channel_name: 'Franchisee',
    channel_type: 'FRANCHISEE',
    mrp: 0,
    selling_price: 0,
    is_active: false,
  },
];

export default function ProductChannelPricingPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const productId = params.id as string;

  const [channelPricing, setChannelPricing] = useState<ChannelPricing[]>(defaultChannels);
  const [isSaving, setIsSaving] = useState(false);

  const { data: product, isLoading, error } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => productsApi.getById(productId),
    enabled: !!productId,
  });

  // Fetch product cost (COGS) from costing API
  const { data: productCost } = useQuery({
    queryKey: ['product-cost', productId],
    queryFn: () => productsApi.getCost(productId),
    enabled: !!productId,
  });

  // Initialize channel pricing from product data when loaded
  useState(() => {
    if (product) {
      setChannelPricing(prev => prev.map(channel => ({
        ...channel,
        mrp: product.mrp || 0,
        selling_price: channel.channel_id === 'D2C' ? (product.selling_price || 0) : 0,
      })));
    }
  });

  const handlePriceChange = (channelId: string, field: 'mrp' | 'selling_price', value: string) => {
    setChannelPricing(prev => prev.map(channel =>
      channel.channel_id === channelId
        ? { ...channel, [field]: parseFloat(value) || 0 }
        : channel
    ));
  };

  const handleActiveChange = (channelId: string, isActive: boolean) => {
    setChannelPricing(prev => prev.map(channel =>
      channel.channel_id === channelId
        ? { ...channel, is_active: isActive }
        : channel
    ));
  };

  const calculateMargin = (mrp: number, sellingPrice: number, costPrice: number) => {
    if (mrp <= 0 || sellingPrice <= 0) return null;
    const discountFromMrp = ((mrp - sellingPrice) / mrp) * 100;
    const grossMargin = costPrice > 0 ? ((sellingPrice - costPrice) / sellingPrice) * 100 : null;
    return { discountFromMrp, grossMargin };
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // In a real implementation, this would save to the ChannelPricing API
      // For now, we'll update the product's selling_price for D2C
      const d2cPricing = channelPricing.find(c => c.channel_id === 'D2C');
      if (d2cPricing) {
        await productsApi.update(productId, {
          selling_price: d2cPricing.selling_price,
        });
      }
      toast.success('Channel pricing saved successfully');
      queryClient.invalidateQueries({ queryKey: ['product', productId] });
    } catch (error: any) {
      toast.error(error.message || 'Failed to save channel pricing');
    } finally {
      setIsSaving(false);
    }
  };

  // Use COGS from ProductCost API (auto-calculated), fallback to static cost_price
  const costPrice = productCost?.average_cost || product?.cost_price || 0;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Product Not Found"
          description="The product you're looking for doesn't exist"
          actions={
            <Button variant="outline" asChild>
              <Link href="/dashboard/catalog">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Products
              </Link>
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Channel Pricing"
        description={`Configure selling prices for ${product.name} across different sales channels`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link href={`/dashboard/catalog/${productId}`}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Product
              </Link>
            </Button>
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save Pricing
            </Button>
          </div>
        }
      />

      {/* Product Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Product Cost Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="p-4 border rounded-lg bg-muted/50">
              <p className="text-sm text-muted-foreground">Product MRP</p>
              <p className="text-xl font-bold">{formatCurrency(product.mrp || 0)}</p>
            </div>
            <div className="p-4 border rounded-lg bg-muted/50">
              <p className="text-sm text-muted-foreground">COGS (Avg Cost)</p>
              <p className="text-xl font-bold">{formatCurrency(costPrice)}</p>
              <p className="text-xs text-muted-foreground">
                {productCost?.average_cost ? 'Weighted avg from GRNs' : 'Static cost price'}
              </p>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">D2C Selling Price</p>
              <p className="text-xl font-bold text-primary">{formatCurrency(product.selling_price || 0)}</p>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">D2C Margin</p>
              <p className="text-xl font-bold text-green-600">
                {costPrice > 0 && product.selling_price
                  ? `${(((product.selling_price - costPrice) / product.selling_price) * 100).toFixed(1)}%`
                  : 'N/A'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Channel Pricing Grid */}
      <Card>
        <CardHeader>
          <CardTitle>Pricing by Channel</CardTitle>
          <CardDescription>
            Set different selling prices for each sales channel. Margins are calculated based on COGS.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-muted/50 border-b">
                  <th className="text-left p-4 font-medium">Channel</th>
                  <th className="text-left p-4 font-medium">Type</th>
                  <th className="text-right p-4 font-medium">MRP</th>
                  <th className="text-right p-4 font-medium">Selling Price</th>
                  <th className="text-right p-4 font-medium">Discount %</th>
                  <th className="text-right p-4 font-medium">Margin %</th>
                  <th className="text-center p-4 font-medium">Active</th>
                </tr>
              </thead>
              <tbody>
                {channelPricing.map((channel, index) => {
                  const margins = calculateMargin(
                    channel.mrp || product.mrp || 0,
                    channel.selling_price,
                    costPrice
                  );
                  return (
                    <tr
                      key={channel.channel_id}
                      className={`border-b last:border-0 ${!channel.is_active ? 'opacity-50' : ''}`}
                    >
                      <td className="p-4">
                        <div className="font-medium">{channel.channel_name}</div>
                      </td>
                      <td className="p-4">
                        <Badge variant="outline">{channel.channel_type}</Badge>
                      </td>
                      <td className="p-4 text-right">
                        <Input
                          type="number"
                          min="0"
                          step="0.01"
                          className="w-32 text-right ml-auto"
                          value={channel.mrp || product.mrp || 0}
                          onChange={(e) => handlePriceChange(channel.channel_id, 'mrp', e.target.value)}
                          disabled={!channel.is_active}
                        />
                      </td>
                      <td className="p-4 text-right">
                        <Input
                          type="number"
                          min="0"
                          step="0.01"
                          className="w-32 text-right ml-auto"
                          value={channel.selling_price || (channel.channel_id === 'D2C' ? product.selling_price : 0) || 0}
                          onChange={(e) => handlePriceChange(channel.channel_id, 'selling_price', e.target.value)}
                          disabled={!channel.is_active}
                        />
                      </td>
                      <td className="p-4 text-right">
                        {margins?.discountFromMrp !== undefined ? (
                          <span className="text-orange-600 font-medium">
                            {margins.discountFromMrp.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                      <td className="p-4 text-right">
                        {margins?.grossMargin !== undefined && margins.grossMargin !== null ? (
                          <span className={`font-medium ${margins.grossMargin >= 20 ? 'text-green-600' : margins.grossMargin >= 10 ? 'text-orange-600' : 'text-red-600'}`}>
                            {margins.grossMargin.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                      <td className="p-4 text-center">
                        <Switch
                          checked={channel.is_active}
                          onCheckedChange={(checked) => handleActiveChange(channel.channel_id, checked)}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-muted-foreground">Margin &ge; 20%</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-orange-500"></div>
              <span className="text-muted-foreground">Margin 10-20%</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span className="text-muted-foreground">Margin &lt; 10%</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notes */}
      <Alert>
        <AlertDescription>
          <strong>Note:</strong> Channel pricing is currently linked to the D2C selling price in the product master.
          Full multi-channel pricing with effective dates will be available in the next update.
          B2B pricing is managed through Dealer Tiers, and Marketplace pricing syncs via integrations.
        </AlertDescription>
      </Alert>
    </div>
  );
}
