'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, DollarSign, TrendingUp, AlertCircle, Loader2, RefreshCw, Download, Upload, FileSpreadsheet, BarChart3, Copy } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import { channelsApi, productsApi, categoriesApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

interface Category {
  id: string;
  name: string;
  slug: string;
}

interface ChannelPricing {
  id: string;
  channel_id: string;
  product_id: string;
  variant_id?: string;
  mrp: number;
  selling_price: number;
  transfer_price?: number;
  discount_percentage?: number;
  max_discount_percentage?: number;
  is_active: boolean;
  is_listed: boolean;
  effective_from?: string;
  effective_to?: string;
  created_at: string;
  updated_at: string;
  // Computed/joined fields
  margin_percentage?: number;
  // Product details from server-side join
  product_name?: string;
  product_sku?: string;
}

interface Channel {
  id: string;
  code: string;
  name: string;
  type: string;
}

interface Product {
  id: string;
  name: string;
  sku: string;
  mrp: number;
}

// Merged view: Products from Master + Channel Pricing (if exists)
interface ProductWithPricing {
  // From Product Master (always present)
  product_id: string;
  product_name: string;
  product_sku: string;
  master_mrp: number;
  // From Channel Pricing (may be null if not configured)
  pricing_id?: string;
  channel_mrp?: number;
  selling_price?: number;
  transfer_price?: number;
  discount_percentage?: number;
  max_discount_percentage?: number;
  is_active?: boolean;
  is_listed?: boolean;
  has_pricing: boolean;
}

// Separate component for action cell to avoid hooks in render function
function PricingActionsCell({
  pricing,
  channelId,
  onEdit,
  onDelete,
}: {
  pricing: ChannelPricing;
  channelId: string;
  onEdit: (pricing: ChannelPricing) => void;
  onDelete: (pricing: ChannelPricing) => void;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Actions</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => onEdit(pricing)}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit Price
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onDelete(pricing)} className="text-destructive focus:text-destructive">
          <Trash2 className="mr-2 h-4 w-4" />
          Remove
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function ChannelPricingPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  // Cascading category selection: Parent → Subcategory → Product
  const [parentCategoryId, setParentCategoryId] = useState<string>('');
  const [subcategoryId, setSubcategoryId] = useState<string>('');
  const [selectedProductId, setSelectedProductId] = useState<string>('');
  const [activeTab, setActiveTab] = useState('pricing');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);
  const [isCopyDialogOpen, setIsCopyDialogOpen] = useState(false);
  const [sourceChannelId, setSourceChannelId] = useState<string>('');
  const [copyOverwrite, setCopyOverwrite] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [selectedPricing, setSelectedPricing] = useState<ChannelPricing | null>(null);
  // Dialog form state - includes cascading category for product selection
  const [dialogParentCategoryId, setDialogParentCategoryId] = useState<string>('');
  const [dialogSubcategoryId, setDialogSubcategoryId] = useState<string>('');
  const [formData, setFormData] = useState({
    product_id: '',
    mrp: 0,
    selling_price: 0,
    transfer_price: 0,
    discount_percentage: 0,
    max_discount_percentage: 25,
    is_active: true,
    is_listed: true,
  });

  const queryClient = useQueryClient();

  // Fetch channels for dropdown
  const { data: channels = [] } = useQuery({
    queryKey: ['channels-dropdown'],
    queryFn: () => channelsApi.dropdown(),
  });

  // ==================== CASCADING CATEGORY DROPDOWNS ====================

  // Step 1: Fetch ROOT categories only (parent_id IS NULL)
  const { data: parentCategoriesData } = useQuery({
    queryKey: ['categories-roots'],
    queryFn: () => categoriesApi.getRoots(),
  });
  const parentCategories: Category[] = parentCategoriesData?.items || [];

  // Step 2: Fetch CHILDREN of selected parent category (for main page filter)
  const { data: subcategoriesData, isLoading: subcategoriesLoading } = useQuery({
    queryKey: ['categories-children', parentCategoryId],
    queryFn: () => categoriesApi.getChildren(parentCategoryId),
    enabled: !!parentCategoryId,
  });
  const subcategories: Category[] = subcategoriesData?.items || [];

  // Step 3: Fetch products filtered by subcategory (for main page)
  const { data: productsData, isLoading: productsLoading, error: productsError } = useQuery({
    queryKey: ['products-dropdown', subcategoryId],
    queryFn: () => productsApi.list({
      size: 100,
      category_id: subcategoryId,
    }),
    enabled: !!subcategoryId,
  });
  const products: Product[] = productsData?.items || [];

  // ==================== DIALOG CASCADING DROPDOWNS ====================

  // Fetch CHILDREN of selected parent category (for dialog)
  const { data: dialogSubcategoriesData, isLoading: dialogSubcategoriesLoading } = useQuery({
    queryKey: ['categories-children', dialogParentCategoryId],
    queryFn: () => categoriesApi.getChildren(dialogParentCategoryId),
    enabled: !!dialogParentCategoryId,
  });
  const dialogSubcategories: Category[] = dialogSubcategoriesData?.items || [];

  // Fetch products filtered by subcategory (for dialog)
  const { data: dialogProductsData, isLoading: dialogProductsLoading } = useQuery({
    queryKey: ['products-dropdown', dialogSubcategoryId],
    queryFn: () => productsApi.list({
      size: 100,
      category_id: dialogSubcategoryId,
    }),
    enabled: !!dialogSubcategoryId,
  });
  const dialogProducts: Product[] = dialogProductsData?.items || [];

  // Reset dependent dropdowns when parent changes (main filter)
  const handleParentCategoryChange = (value: string) => {
    setParentCategoryId(value);
    setSubcategoryId(''); // Reset subcategory when parent changes
    setSelectedProductId(''); // Reset product when parent changes
  };

  const handleSubcategoryChange = (value: string) => {
    setSubcategoryId(value);
    setSelectedProductId(''); // Reset product when subcategory changes
  };

  // Reset dependent dropdowns when parent changes (dialog)
  const handleDialogParentCategoryChange = (value: string) => {
    setDialogParentCategoryId(value);
    setDialogSubcategoryId(''); // Reset subcategory
    setFormData(prev => ({ ...prev, product_id: '', mrp: 0, selling_price: 0 })); // Reset product
  };

  const handleDialogSubcategoryChange = (value: string) => {
    setDialogSubcategoryId(value);
    setFormData(prev => ({ ...prev, product_id: '', mrp: 0, selling_price: 0 })); // Reset product
  };

  // Fetch pricing for selected channel (filtered by product if selected)
  const { data: pricingData, isLoading } = useQuery({
    queryKey: ['channel-pricing', selectedChannelId, selectedProductId, page, pageSize],
    queryFn: () => channelsApi.pricing.list(selectedChannelId, {
      skip: page * pageSize,
      limit: pageSize,
      product_id: selectedProductId || undefined,
    }),
    enabled: !!selectedChannelId,
  });

  // Get product IDs from pricing data to fetch their details
  const pricingProductIds = useMemo(() => {
    const items = pricingData?.items || [];
    return items.map((p: ChannelPricing) => p.product_id);
  }, [pricingData]);

  // Fetch all products (for displaying names of existing pricing records)
  const { data: allProductsData } = useQuery({
    queryKey: ['products-all-for-pricing', pricingProductIds],
    queryFn: () => productsApi.list({ size: 200 }), // Fetch all products
    enabled: !!selectedChannelId && pricingProductIds.length > 0 && !subcategoryId,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
  const allProducts: Product[] = allProductsData?.items || [];

  // Fetch selected channel details for commission settings
  const { data: selectedChannel } = useQuery({
    queryKey: ['channel-detail', selectedChannelId],
    queryFn: () => channelsApi.getById(selectedChannelId),
    enabled: !!selectedChannelId,
  });

  // Fetch pricing rules for selected channel
  const { data: rulesData, isLoading: rulesLoading } = useQuery({
    queryKey: ['pricing-rules', selectedChannelId],
    queryFn: () => channelsApi.pricingRules.list({
      channel_id: selectedChannelId || undefined,
      is_active: true,
    }),
    enabled: !!selectedChannelId,
  });

  // Fetch pricing history for selected channel
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['pricing-history', selectedChannelId],
    queryFn: () => channelsApi.pricingHistory.list({
      channel_id: selectedChannelId || undefined,
      size: 50,
    }),
    enabled: !!selectedChannelId,
  });

  // Commission form state
  const [commissionForm, setCommissionForm] = useState({
    commission_percentage: 0,
    fixed_fee_per_order: 0,
    payment_cycle_days: 7,
    price_markup_percentage: 0,
  });

  // Update commission form when channel data loads
  useMemo(() => {
    if (selectedChannel) {
      setCommissionForm({
        commission_percentage: selectedChannel.commission_percentage || 0,
        fixed_fee_per_order: selectedChannel.fixed_fee_per_order || 0,
        payment_cycle_days: selectedChannel.payment_cycle_days || 7,
        price_markup_percentage: selectedChannel.price_markup_percentage || 0,
      });
    }
  }, [selectedChannel]);

  // Get product map for displaying names (includes both filtered products AND all products for pricing display)
  const productMap = useMemo(() => {
    const map = new Map<string, Product>();
    // Add all products first (for existing pricing display)
    allProducts.forEach(p => map.set(p.id, p));
    // Then add/override with filtered products (when subcategory is selected)
    products.forEach(p => map.set(p.id, p));
    return map;
  }, [products, allProducts]);

  // Get channel map
  const channelMap = useMemo(() => {
    const map = new Map<string, Channel>();
    channels.forEach((c: Channel) => map.set(c.id, c));
    return map;
  }, [channels]);

  // Get pricing map by product_id for quick lookup
  const pricingMap = useMemo(() => {
    const map = new Map<string, ChannelPricing>();
    (pricingData?.items || []).forEach((p: ChannelPricing) => map.set(p.product_id, p));
    return map;
  }, [pricingData]);

  // ==================== STRUCTURAL FIX ====================
  // Two views:
  // 1. When only channel selected (no subcategory): Show ALL existing channel pricing records
  // 2. When subcategory selected: Show products from Master with pricing status

  // View 1: Existing channel pricing (direct from channel_pricing table)
  // Now uses product_name and product_sku from API response (joined with products table)
  const existingPricingWithProducts = useMemo((): ProductWithPricing[] => {
    const items = pricingData?.items || [];
    if (items.length === 0) return [];

    return items.map((pricing: ChannelPricing & { product_name?: string; product_sku?: string }) => {
      // Use product_name/sku from API response (server-side join), fallback to productMap
      const product = productMap.get(pricing.product_id);
      return {
        product_id: pricing.product_id,
        product_name: pricing.product_name || product?.name || `Unknown Product`,
        product_sku: pricing.product_sku || product?.sku || '-',
        master_mrp: product?.mrp || pricing.mrp,
        pricing_id: pricing.id,
        channel_mrp: pricing.mrp,
        selling_price: pricing.selling_price,
        transfer_price: pricing.transfer_price,
        discount_percentage: pricing.discount_percentage,
        max_discount_percentage: pricing.max_discount_percentage,
        is_active: pricing.is_active,
        is_listed: pricing.is_listed,
        has_pricing: true,
      };
    });
  }, [pricingData, productMap]);

  // View 2: Merged Products from Master + Channel Pricing (if exists)
  // This shows ALL products in selected subcategory with their pricing status
  const mergedProductsWithPricing = useMemo((): ProductWithPricing[] => {
    // Only merge when we have a subcategory selected (products loaded)
    if (!subcategoryId || products.length === 0) {
      return [];
    }

    return products.map(product => {
      const pricing = pricingMap.get(product.id);
      return {
        product_id: product.id,
        product_name: product.name,
        product_sku: product.sku,
        master_mrp: product.mrp,
        pricing_id: pricing?.id,
        channel_mrp: pricing?.mrp,
        selling_price: pricing?.selling_price,
        transfer_price: pricing?.transfer_price,
        discount_percentage: pricing?.discount_percentage,
        max_discount_percentage: pricing?.max_discount_percentage,
        is_active: pricing?.is_active,
        is_listed: pricing?.is_listed,
        has_pricing: !!pricing,
      };
    });
  }, [products, pricingMap, subcategoryId]);

  // Use merged view if subcategory selected, otherwise show existing pricing
  const displayData = subcategoryId ? mergedProductsWithPricing : existingPricingWithProducts;

  // Calculate stats from pricing data
  const stats = useMemo(() => {
    const items = pricingData?.items || [];
    const totalProducts = items.length;
    const avgMargin = totalProducts > 0
      ? items.reduce((sum: number, p: ChannelPricing) => {
          const margin = p.mrp > 0 ? ((p.mrp - p.selling_price) / p.mrp) * 100 : 0;
          return sum + margin;
        }, 0) / totalProducts
      : 0;
    const belowThreshold = items.filter((p: ChannelPricing) => {
      const margin = p.mrp > 0 ? ((p.mrp - p.selling_price) / p.mrp) * 100 : 0;
      return margin < 10;
    }).length;

    return {
      total_products_mapped: pricingData?.total || 0,
      avg_margin_percent: avgMargin,
      products_below_threshold: belowThreshold,
      total_channels: channels.length,
    };
  }, [pricingData, channels]);

  // Handlers
  const handleEdit = (pricing: ChannelPricing) => {
    setSelectedPricing(pricing);
    setFormData({
      product_id: pricing.product_id,
      mrp: pricing.mrp,
      selling_price: pricing.selling_price,
      transfer_price: pricing.transfer_price || 0,
      discount_percentage: pricing.discount_percentage || 0,
      max_discount_percentage: pricing.max_discount_percentage || 25,
      is_active: pricing.is_active,
      is_listed: pricing.is_listed,
    });
    setIsDialogOpen(true);
  };

  const handleDelete = (pricing: ChannelPricing) => {
    const product = productMap.get(pricing.product_id);
    if (confirm(`Remove pricing for ${product?.name || 'this product'}?`)) {
      deleteMutation.mutate({ channelId: selectedChannelId, pricingId: pricing.id });
    }
  };

  const handleAddNew = () => {
    if (!selectedChannelId) {
      toast.error('Please select a channel first');
      return;
    }
    setSelectedPricing(null);

    // If a product is already selected in the main filter, pre-populate the dialog
    if (selectedProductId && parentCategoryId && subcategoryId) {
      const selectedProduct = products.find(p => p.id === selectedProductId);
      setDialogParentCategoryId(parentCategoryId);
      setDialogSubcategoryId(subcategoryId);
      setFormData({
        product_id: selectedProductId,
        mrp: selectedProduct?.mrp || 0,
        selling_price: selectedProduct?.mrp || 0, // Default selling price to MRP
        transfer_price: 0,
        discount_percentage: 0,
        max_discount_percentage: 25,
        is_active: true,
        is_listed: true,
      });
    } else {
      // Reset cascading category selection for dialog
      setDialogParentCategoryId('');
      setDialogSubcategoryId('');
      setFormData({
        product_id: '',
        mrp: 0,
        selling_price: 0,
        transfer_price: 0,
        discount_percentage: 0,
        max_discount_percentage: 25,
        is_active: true,
        is_listed: true,
      });
    }
    setIsDialogOpen(true);
  };

  // Handler to add pricing for a specific product from the table
  const handleAddPricingForProduct = (item: ProductWithPricing) => {
    setSelectedPricing(null);
    setDialogParentCategoryId(parentCategoryId);
    setDialogSubcategoryId(subcategoryId);
    setFormData({
      product_id: item.product_id,
      mrp: item.master_mrp,
      selling_price: item.master_mrp, // Default to MRP
      transfer_price: 0,
      discount_percentage: 0,
      max_discount_percentage: 25,
      is_active: true,
      is_listed: true,
    });
    setIsDialogOpen(true);
  };

  // Handler to edit pricing for a product that already has pricing
  const handleEditPricing = (item: ProductWithPricing) => {
    if (!item.has_pricing || !item.pricing_id) return;

    setSelectedPricing({
      id: item.pricing_id,
      channel_id: selectedChannelId,
      product_id: item.product_id,
      mrp: item.channel_mrp || item.master_mrp,
      selling_price: item.selling_price || 0,
      transfer_price: item.transfer_price,
      discount_percentage: item.discount_percentage,
      max_discount_percentage: item.max_discount_percentage,
      is_active: item.is_active || false,
      is_listed: item.is_listed || false,
      created_at: '',
      updated_at: '',
    });
    setDialogParentCategoryId(parentCategoryId);
    setDialogSubcategoryId(subcategoryId);
    setFormData({
      product_id: item.product_id,
      mrp: item.channel_mrp || item.master_mrp,
      selling_price: item.selling_price || 0,
      transfer_price: item.transfer_price || 0,
      discount_percentage: item.discount_percentage || 0,
      max_discount_percentage: item.max_discount_percentage || 25,
      is_active: item.is_active || true,
      is_listed: item.is_listed || true,
    });
    setIsDialogOpen(true);
  };

  // Column definitions for merged ProductWithPricing data
  const columns: ColumnDef<ProductWithPricing>[] = useMemo(() => [
    {
      accessorKey: 'product_name',
      header: 'Product (from Master)',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.product_name}</div>
          <div className="text-sm text-muted-foreground">{row.original.product_sku}</div>
        </div>
      ),
    },
    {
      accessorKey: 'master_mrp',
      header: 'MRP (Master)',
      cell: ({ row }) => (
        <span className="font-mono text-sm">{formatCurrency(row.original.master_mrp)}</span>
      ),
    },
    {
      accessorKey: 'selling_price',
      header: 'Selling Price',
      cell: ({ row }) => {
        if (!row.original.has_pricing) {
          return <span className="text-muted-foreground italic">Not configured</span>;
        }
        return (
          <span className="font-mono text-sm font-medium">{formatCurrency(row.original.selling_price || 0)}</span>
        );
      },
    },
    {
      id: 'discount',
      header: 'Discount',
      cell: ({ row }) => {
        if (!row.original.has_pricing || !row.original.selling_price) {
          return <span className="text-muted-foreground">-</span>;
        }
        const mrp = row.original.channel_mrp || row.original.master_mrp;
        const discount = mrp > 0
          ? ((mrp - row.original.selling_price) / mrp) * 100
          : 0;
        return (
          <span className="text-orange-600 font-medium">
            {discount.toFixed(1)}%
          </span>
        );
      },
    },
    {
      id: 'margin',
      header: 'Margin %',
      cell: ({ row }) => {
        if (!row.original.has_pricing || !row.original.selling_price) {
          return <span className="text-muted-foreground">-</span>;
        }
        const mrp = row.original.channel_mrp || row.original.master_mrp;
        const margin = mrp > 0
          ? ((mrp - row.original.selling_price) / mrp) * 100
          : 0;
        const color = margin >= 20 ? 'text-green-600' : margin >= 10 ? 'text-yellow-600' : 'text-red-600';
        return <span className={`font-medium ${color}`}>{margin.toFixed(1)}%</span>;
      },
    },
    {
      accessorKey: 'max_discount_percentage',
      header: 'Max Discount',
      cell: ({ row }) => {
        if (!row.original.has_pricing) {
          return <span className="text-muted-foreground">-</span>;
        }
        const maxDiscount = row.original.max_discount_percentage || 0;
        return (
          <span className="text-sm text-muted-foreground">
            {maxDiscount > 0 ? `${maxDiscount}%` : '-'}
          </span>
        );
      },
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) => {
        if (!row.original.has_pricing) {
          return (
            <span className="px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
              Not Configured
            </span>
          );
        }
        return (
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
            row.original.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
          }`}>
            {row.original.is_active ? 'Active' : 'Inactive'}
          </span>
        );
      },
    },
    {
      id: 'actions',
      header: 'Action',
      cell: ({ row }) => {
        if (!row.original.has_pricing) {
          return (
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleAddPricingForProduct(row.original)}
            >
              <Plus className="mr-1 h-3 w-3" />
              Add Pricing
            </Button>
          );
        }
        return (
          <div className="flex gap-1">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => handleEditPricing(row.original)}
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="text-destructive"
              onClick={() => {
                if (confirm(`Remove pricing for ${row.original.product_name}?`)) {
                  deleteMutation.mutate({ channelId: selectedChannelId, pricingId: row.original.pricing_id! });
                }
              }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        );
      },
    },
  ], [selectedChannelId, parentCategoryId, subcategoryId]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: Parameters<typeof channelsApi.pricing.create>[1]) =>
      channelsApi.pricing.create(selectedChannelId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel-pricing'] });
      toast.success('Pricing rule created successfully');
      setIsDialogOpen(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create pricing rule');
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: { pricingId: string; pricing: Parameters<typeof channelsApi.pricing.update>[2] }) =>
      channelsApi.pricing.update(selectedChannelId, data.pricingId, data.pricing),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel-pricing'] });
      toast.success('Pricing updated successfully');
      setIsDialogOpen(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update pricing');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (data: { channelId: string; pricingId: string }) =>
      channelsApi.pricing.delete(data.channelId, data.pricingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel-pricing'] });
      toast.success('Pricing rule removed');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to remove pricing rule');
    },
  });

  const syncMutation = useMutation({
    mutationFn: () => channelsApi.pricing.sync(selectedChannelId),
    onSuccess: (result) => {
      toast.success(`Synced ${result.synced_count} pricing rules to channel`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to sync pricing');
    },
  });

  // Commission update mutation
  const commissionMutation = useMutation({
    mutationFn: (data: {
      commission_percentage?: number;
      fixed_fee_per_order?: number;
      payment_cycle_days?: number;
      price_markup_percentage?: number;
    }) => channelsApi.update(selectedChannelId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel-detail', selectedChannelId] });
      toast.success('Commission settings saved successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to save commission settings');
    },
  });

  // Pricing rule mutations
  const createRuleMutation = useMutation({
    mutationFn: (rule: Parameters<typeof channelsApi.pricingRules.create>[0]) =>
      channelsApi.pricingRules.create(rule),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pricing-rules'] });
      toast.success('Pricing rule created');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create pricing rule');
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: (ruleId: string) => channelsApi.pricingRules.delete(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pricing-rules'] });
      toast.success('Pricing rule deleted');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete pricing rule');
    },
  });

  // Import mutation
  const importMutation = useMutation({
    mutationFn: async (items: Array<{
      product_id: string;
      mrp: number;
      selling_price: number;
      transfer_price?: number;
      max_discount_percentage?: number;
      is_active?: boolean;
    }>) => channelsApi.pricing.bulk(selectedChannelId, items),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['channel-pricing'] });
      toast.success(`Successfully imported ${result.created || 0} new, updated ${result.updated || 0} existing pricing rules`);
      setIsImportDialogOpen(false);
      setImportFile(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to import pricing');
    },
  });

  // Copy pricing mutation
  const copyMutation = useMutation({
    mutationFn: async () => channelsApi.pricing.copyFrom(selectedChannelId, sourceChannelId, copyOverwrite),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['channel-pricing'] });
      const message = copyOverwrite
        ? `Copied ${result.copied || 0} new, updated ${result.updated || 0} existing pricing rules`
        : `Copied ${result.copied || 0} pricing rules (${result.skipped || 0} skipped - already exist)`;
      toast.success(message);
      setIsCopyDialogOpen(false);
      setSourceChannelId('');
      setCopyOverwrite(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to copy pricing');
    },
  });

  // Export pricing to CSV
  const handleExport = async () => {
    if (!selectedChannelId) {
      toast.error('Please select a channel first');
      return;
    }

    setIsExporting(true);
    try {
      const data = await channelsApi.pricing.export(selectedChannelId);
      const items = data.items || [];

      if (items.length === 0) {
        toast.error('No pricing data to export');
        setIsExporting(false);
        return;
      }

      // Generate CSV content
      const headers = ['Product ID', 'Product Name', 'SKU', 'MRP', 'Selling Price', 'Transfer Price', 'Max Discount %', 'Active'];
      const rows = items.map((item: ChannelPricing & { product_name?: string; product_sku?: string }) => [
        item.product_id,
        item.product_name || '',
        item.product_sku || '',
        item.mrp,
        item.selling_price,
        item.transfer_price || '',
        item.max_discount_percentage || '',
        item.is_active ? 'Yes' : 'No',
      ]);

      const csvContent = [
        headers.join(','),
        ...rows.map((row: (string | number)[]) => row.map((cell: string | number) => `"${cell}"`).join(',')),
      ].join('\n');

      // Download CSV
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      const channel = channels.find((c: Channel) => c.id === selectedChannelId);
      link.download = `channel-pricing-${channel?.code || 'export'}-${new Date().toISOString().split('T')[0]}.csv`;
      link.click();
      URL.revokeObjectURL(link.href);

      toast.success(`Exported ${items.length} pricing rules`);
    } catch (error) {
      toast.error('Failed to export pricing data');
    } finally {
      setIsExporting(false);
    }
  };

  // Process imported CSV file
  const handleImportFile = async () => {
    if (!importFile) {
      toast.error('Please select a file');
      return;
    }

    const text = await importFile.text();
    const lines = text.split('\n').filter(line => line.trim());

    if (lines.length < 2) {
      toast.error('CSV file must have a header row and at least one data row');
      return;
    }

    // Parse CSV (skip header)
    const items: Array<{
      product_id: string;
      mrp: number;
      selling_price: number;
      transfer_price?: number;
      max_discount_percentage?: number;
      is_active?: boolean;
    }> = [];

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i];
      // Simple CSV parsing (handles quoted values)
      const values = line.match(/("([^"]*)"|[^,]*)/g)?.map(v => v.replace(/^"|"$/g, '').trim()) || [];

      if (values.length >= 5) {
        const [product_id, , , mrp, selling_price, transfer_price, max_discount, is_active] = values;

        if (product_id && mrp && selling_price) {
          items.push({
            product_id,
            mrp: parseFloat(mrp) || 0,
            selling_price: parseFloat(selling_price) || 0,
            transfer_price: transfer_price ? parseFloat(transfer_price) : undefined,
            max_discount_percentage: max_discount ? parseFloat(max_discount) : undefined,
            is_active: is_active?.toLowerCase() !== 'no',
          });
        }
      }
    }

    if (items.length === 0) {
      toast.error('No valid pricing data found in CSV');
      return;
    }

    importMutation.mutate(items);
  };

  const handleSaveCommission = () => {
    commissionMutation.mutate(commissionForm);
  };

  const handleSubmit = () => {
    if (selectedPricing) {
      updateMutation.mutate({
        pricingId: selectedPricing.id,
        pricing: {
          mrp: formData.mrp,
          selling_price: formData.selling_price,
          transfer_price: formData.transfer_price || undefined,
          discount_percentage: formData.discount_percentage || undefined,
          max_discount_percentage: formData.max_discount_percentage || undefined,
          is_active: formData.is_active,
          is_listed: formData.is_listed,
        },
      });
    } else {
      createMutation.mutate({
        product_id: formData.product_id,
        mrp: formData.mrp,
        selling_price: formData.selling_price,
        transfer_price: formData.transfer_price || undefined,
        discount_percentage: formData.discount_percentage || undefined,
        max_discount_percentage: formData.max_discount_percentage || undefined,
        is_active: formData.is_active,
        is_listed: formData.is_listed,
      });
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Channel Pricing"
        description="Manage product prices across different sales channels"
        actions={
          <div className="flex gap-2">
            <Link href="/dashboard/channels/pricing/compare">
              <Button variant="outline">
                <BarChart3 className="mr-2 h-4 w-4" />
                Compare Channels
              </Button>
            </Link>
            <Link href="/dashboard/channels/pricing/profitability">
              <Button variant="outline">
                <TrendingUp className="mr-2 h-4 w-4" />
                Profitability
              </Button>
            </Link>
            <Link href="/dashboard/channels/pricing/promotions">
              <Button variant="outline">
                <DollarSign className="mr-2 h-4 w-4" />
                Promotions
              </Button>
            </Link>
            {selectedChannelId && (
              <>
                <Button
                  variant="outline"
                  onClick={() => setIsCopyDialogOpen(true)}
                >
                  <Copy className="mr-2 h-4 w-4" />
                  Copy From Channel
                </Button>
                <Button
                  variant="outline"
                  onClick={handleExport}
                  disabled={isExporting}
                >
                  {isExporting ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="mr-2 h-4 w-4" />
                  )}
                  Export CSV
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setIsImportDialogOpen(true)}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  Import CSV
                </Button>
                <Button
                  variant="outline"
                  onClick={() => syncMutation.mutate()}
                  disabled={syncMutation.isPending}
                >
                  {syncMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="mr-2 h-4 w-4" />
                  )}
                  Sync to Channel
                </Button>
              </>
            )}
            <Button onClick={handleAddNew} disabled={!selectedChannelId}>
              <Plus className="mr-2 h-4 w-4" />
              Add Pricing Rule
            </Button>
          </div>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Products Mapped</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_products_mapped}</div>
            <p className="text-xs text-muted-foreground">In selected channel</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Margin</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {stats.avg_margin_percent.toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">Average across products</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Below Threshold</CardTitle>
            <AlertCircle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats.products_below_threshold}</div>
            <p className="text-xs text-muted-foreground">Products with margin &lt; 10%</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Channels</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_channels}</div>
            <p className="text-xs text-muted-foreground">Available channels</p>
          </CardContent>
        </Card>
      </div>

      {/* Channel and Cascading Category Selectors */}
      <div className="flex gap-4 flex-wrap items-end">
        {/* Step 1: Channel Selection */}
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Channel</Label>
          <Select value={selectedChannelId} onValueChange={setSelectedChannelId}>
            <SelectTrigger className="w-[250px]">
              <SelectValue placeholder="Select channel" />
            </SelectTrigger>
            <SelectContent>
              {channels.map((channel: Channel) => (
                <SelectItem key={channel.id} value={channel.id}>
                  {channel.name} ({channel.code})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Step 2: Parent Category Selection (ROOT categories only) */}
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Parent Category</Label>
          <Select value={parentCategoryId || "all"} onValueChange={(v) => handleParentCategoryChange(v === "all" ? "" : v)}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="All Categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {parentCategories.map((category) => (
                <SelectItem key={category.id} value={category.id}>
                  {category.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Step 3: Subcategory Selection (children of selected parent) */}
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Subcategory</Label>
          <Select
            value={subcategoryId || "all"}
            onValueChange={(v) => handleSubcategoryChange(v === "all" ? "" : v)}
            disabled={!parentCategoryId}
          >
            <SelectTrigger className="w-[220px]">
              <SelectValue placeholder={parentCategoryId ? "Select subcategory" : "Select parent first"} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Subcategories</SelectItem>
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

        {/* Step 4: Product Selection (products in selected subcategory) */}
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Product</Label>
          <Select
            value={selectedProductId || "all"}
            onValueChange={(v) => setSelectedProductId(v === "all" ? "" : v)}
            disabled={!subcategoryId}
          >
            <SelectTrigger className="w-[280px]">
              <SelectValue placeholder={subcategoryId ? "All Products" : "Select subcategory first"} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Products</SelectItem>
              {productsLoading ? (
                <SelectItem value="loading" disabled>Loading...</SelectItem>
              ) : products.length === 0 ? (
                <SelectItem value="none" disabled>No products in this subcategory</SelectItem>
              ) : (
                products.map((product) => (
                  <SelectItem key={product.id} value={product.id}>
                    {product.name} ({product.sku})
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </div>

        {/* Products count indicator */}
        {subcategoryId && (
          <div className="text-sm text-muted-foreground self-end pb-2">
            {productsLoading ? 'Loading...' : `${products.length} products`}
          </div>
        )}
      </div>

      {/* Selected Product Info Card - Shows Master Data */}
      {selectedProductId && selectedChannelId && (
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Selected Product (from Master Data)</p>
                  <p className="font-semibold text-lg">
                    {products.find(p => p.id === selectedProductId)?.name || 'Loading...'}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    SKU: {products.find(p => p.id === selectedProductId)?.sku || '-'}
                  </p>
                </div>
                <div className="border-l pl-6">
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">MRP (Master)</p>
                  <p className="font-bold text-xl text-primary">
                    {formatCurrency(products.find(p => p.id === selectedProductId)?.mrp || 0)}
                  </p>
                </div>
              </div>
              <Button onClick={handleAddNew} size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Add Pricing for this Product
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {!selectedChannelId ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <DollarSign className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">Select a Channel</p>
            <p className="text-sm text-muted-foreground">Choose a sales channel above to view and manage its pricing</p>
          </CardContent>
        </Card>
      ) : (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="grid w-full grid-cols-4 lg:w-[600px]">
            <TabsTrigger value="pricing" className="flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Pricing
            </TabsTrigger>
            <TabsTrigger value="commission" className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Commission
            </TabsTrigger>
            <TabsTrigger value="rules" className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              Rules
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4" />
              History
            </TabsTrigger>
          </TabsList>

          <TabsContent value="pricing" className="space-y-4">
            {/* Show helpful message based on current filter state */}
            {!subcategoryId && existingPricingWithProducts.length > 0 && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>Showing all existing pricing for this channel.</strong> Use the category filters above to browse products by category and add new pricing.
                </p>
              </div>
            )}
            {subcategoryId && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm text-green-800">
                  <strong>Showing products from Product Master.</strong> Products with pricing are marked as "Active", others show "Not Configured" with an option to add pricing.
                </p>
              </div>
            )}

            {/* Data Table - shows displayData (existing pricing OR merged products) */}
            <DataTable
              columns={columns}
              data={displayData}
              isLoading={isLoading || productsLoading}
            />

            {/* Empty state when no data */}
            {!isLoading && !productsLoading && displayData.length === 0 && (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <DollarSign className="h-12 w-12 text-muted-foreground mb-4" />
                  {!subcategoryId ? (
                    <>
                      <p className="text-lg font-medium">No Pricing Configured Yet</p>
                      <p className="text-sm text-muted-foreground">
                        Select a Parent Category → Subcategory above to browse products and add pricing
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="text-lg font-medium">No Products in This Subcategory</p>
                      <p className="text-sm text-muted-foreground">
                        Add products to this subcategory in Product Master first
                      </p>
                    </>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="commission" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Commission Settings</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Default Commission %</Label>
                      <Input
                        type="number"
                        placeholder="0"
                        value={commissionForm.commission_percentage || ''}
                        onChange={(e) => setCommissionForm({
                          ...commissionForm,
                          commission_percentage: parseFloat(e.target.value) || 0
                        })}
                      />
                      <p className="text-xs text-muted-foreground">Applied to all products in this channel</p>
                    </div>
                    <div className="space-y-2">
                      <Label>Fixed Fee per Order (₹)</Label>
                      <Input
                        type="number"
                        placeholder="0"
                        value={commissionForm.fixed_fee_per_order || ''}
                        onChange={(e) => setCommissionForm({
                          ...commissionForm,
                          fixed_fee_per_order: parseFloat(e.target.value) || 0
                        })}
                      />
                      <p className="text-xs text-muted-foreground">Additional fee per order</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Payment Cycle (Days)</Label>
                      <Input
                        type="number"
                        placeholder="7"
                        value={commissionForm.payment_cycle_days || ''}
                        onChange={(e) => setCommissionForm({
                          ...commissionForm,
                          payment_cycle_days: parseInt(e.target.value) || 7
                        })}
                      />
                      <p className="text-xs text-muted-foreground">Settlement cycle in days</p>
                    </div>
                    <div className="space-y-2">
                      <Label>Price Markup %</Label>
                      <Input
                        type="number"
                        placeholder="0"
                        value={commissionForm.price_markup_percentage || ''}
                        onChange={(e) => setCommissionForm({
                          ...commissionForm,
                          price_markup_percentage: parseFloat(e.target.value) || 0
                        })}
                      />
                      <p className="text-xs text-muted-foreground">Default markup on base price</p>
                    </div>
                  </div>
                  <div className="pt-4 border-t">
                    <Button
                      onClick={handleSaveCommission}
                      disabled={commissionMutation.isPending}
                    >
                      {commissionMutation.isPending ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : null}
                      Save Commission Settings
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="rules" className="space-y-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Pricing Rules</CardTitle>
                <Button size="sm" disabled>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Rule
                </Button>
              </CardHeader>
              <CardContent>
                {rulesLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : (rulesData?.items?.length || 0) === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No pricing rules configured for this channel.</p>
                    <p className="text-sm mt-2">Default volume and segment discounts are applied automatically.</p>
                    <div className="mt-4 p-4 bg-muted rounded-lg text-left">
                      <p className="font-medium mb-2">Default Volume Discounts:</p>
                      <div className="grid grid-cols-4 gap-2 text-sm">
                        <div>10+ units: 3% off</div>
                        <div>25+ units: 5% off</div>
                        <div>50+ units: 7% off</div>
                        <div>100+ units: 10% off</div>
                      </div>
                      <p className="font-medium mt-4 mb-2">Default Segment Discounts:</p>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <div>VIP: 5% off</div>
                        <div>Dealer: 15% off</div>
                        <div>Distributor: 20% off</div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {rulesData?.items?.map((rule: {
                      id: string;
                      code: string;
                      name: string;
                      description?: string;
                      rule_type: string;
                      discount_type: string;
                      discount_value: number;
                      is_active: boolean;
                      conditions: Record<string, unknown>;
                    }) => (
                      <div key={rule.id} className="border rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary">{rule.rule_type}</Badge>
                            <span className="font-medium">{rule.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant={rule.is_active ? "outline" : "secondary"} className={rule.is_active ? "text-green-600" : ""}>
                              {rule.is_active ? "Active" : "Inactive"}
                            </Badge>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-destructive"
                              onClick={() => {
                                if (confirm(`Delete rule "${rule.name}"?`)) {
                                  deleteRuleMutation.mutate(rule.id);
                                }
                              }}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        {rule.description && (
                          <p className="text-sm text-muted-foreground mb-2">{rule.description}</p>
                        )}
                        <div className="flex items-center gap-4 text-sm">
                          <span className="bg-muted px-2 py-1 rounded">
                            {rule.discount_type === 'PERCENTAGE' ? `${rule.discount_value}% off` : `₹${rule.discount_value} off`}
                          </span>
                          <span className="text-muted-foreground">Code: {rule.code}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="history" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Pricing History</CardTitle>
              </CardHeader>
              <CardContent>
                {historyLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : (historyData?.items?.length || 0) === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <RefreshCw className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No pricing changes recorded yet.</p>
                    <p className="text-sm mt-2">Changes to pricing will appear here.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {historyData?.items?.map((item: {
                      id: string;
                      entity_type: string;
                      entity_id: string;
                      field_name: string;
                      old_value?: string;
                      new_value?: string;
                      changed_at: string;
                      change_reason?: string;
                    }) => (
                      <div key={item.id} className="flex items-center gap-4 text-sm border-b pb-4">
                        <div className="w-36 font-medium text-muted-foreground">
                          {new Date(item.changed_at).toLocaleString()}
                        </div>
                        <Badge variant="outline">
                          {item.field_name === 'created' ? 'CREATED' :
                           item.field_name === 'deleted' ? 'DELETED' :
                           item.entity_type === 'PRICING_RULE' ? 'RULE_UPDATE' : 'PRICE_UPDATE'}
                        </Badge>
                        <div className="flex-1">
                          <span className="font-medium">{item.field_name}</span>
                          {item.old_value && item.new_value ? (
                            <>
                              <span className="text-muted-foreground"> changed from </span>
                              <span className="line-through text-red-500">{item.old_value}</span>
                              <span className="text-muted-foreground"> to </span>
                              <span className="text-green-600">{item.new_value}</span>
                            </>
                          ) : item.new_value ? (
                            <span className="text-green-600"> = {item.new_value}</span>
                          ) : item.old_value ? (
                            <span className="line-through text-red-500"> = {item.old_value}</span>
                          ) : null}
                        </div>
                      </div>
                    ))}
                    <p className="text-sm text-muted-foreground text-center py-4">
                      Showing {historyData?.items?.length || 0} of {historyData?.total || 0} changes
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}

      {/* Import CSV Dialog */}
      <Dialog open={isImportDialogOpen} onOpenChange={setIsImportDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5" />
              Import Pricing from CSV
            </DialogTitle>
            <DialogDescription>
              Upload a CSV file to bulk update pricing for {channelMap.get(selectedChannelId)?.name || 'this channel'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* CSV Format Instructions */}
            <div className="p-4 bg-muted rounded-lg">
              <p className="font-medium text-sm mb-2">CSV Format Requirements:</p>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• First row must be headers</li>
                <li>• Required columns: <code className="bg-background px-1 rounded">Product ID, Product Name, SKU, MRP, Selling Price</code></li>
                <li>• Optional columns: <code className="bg-background px-1 rounded">Transfer Price, Max Discount %, Active</code></li>
                <li>• Active column accepts: Yes/No</li>
              </ul>
              <div className="mt-3 pt-3 border-t">
                <p className="text-sm text-muted-foreground">
                  <strong>Tip:</strong> Export existing pricing first to get the correct format, modify values, then import.
                </p>
              </div>
            </div>

            {/* File Input */}
            <div className="space-y-2">
              <Label>Select CSV File</Label>
              <Input
                type="file"
                accept=".csv"
                onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                className="cursor-pointer"
              />
              {importFile && (
                <p className="text-sm text-muted-foreground">
                  Selected: {importFile.name} ({(importFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>

            {/* Preview Info */}
            {importFile && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  Ready to import. This will create new pricing rules or update existing ones for products in the file.
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsImportDialogOpen(false);
                setImportFile(null);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleImportFile}
              disabled={!importFile || importMutation.isPending}
            >
              {importMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              Import {importFile ? 'File' : ''}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Copy Pricing Dialog */}
      <Dialog open={isCopyDialogOpen} onOpenChange={setIsCopyDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Copy className="h-5 w-5" />
              Copy Pricing From Another Channel
            </DialogTitle>
            <DialogDescription>
              Copy all pricing rules from a source channel to {channelMap.get(selectedChannelId)?.name || 'this channel'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Source Channel Selection */}
            <div className="space-y-2">
              <Label>Source Channel</Label>
              <Select value={sourceChannelId} onValueChange={setSourceChannelId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select source channel" />
                </SelectTrigger>
                <SelectContent>
                  {channels
                    .filter((c: Channel) => c.id !== selectedChannelId)
                    .map((channel: Channel) => (
                      <SelectItem key={channel.id} value={channel.id}>
                        {channel.name} ({channel.code})
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Select the channel to copy pricing from
              </p>
            </div>

            {/* Overwrite Option */}
            <div className="flex items-start space-x-3 p-4 bg-muted rounded-lg">
              <input
                type="checkbox"
                id="copyOverwrite"
                checked={copyOverwrite}
                onChange={(e) => setCopyOverwrite(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300"
              />
              <div className="space-y-1">
                <Label htmlFor="copyOverwrite" className="font-medium cursor-pointer">
                  Overwrite existing pricing
                </Label>
                <p className="text-xs text-muted-foreground">
                  If checked, existing pricing for the same products will be updated.
                  Otherwise, products with existing pricing will be skipped.
                </p>
              </div>
            </div>

            {/* Info Box */}
            {sourceChannelId && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>Ready to copy.</strong> This will copy all active pricing rules from{' '}
                  <strong>{channelMap.get(sourceChannelId)?.name}</strong> to{' '}
                  <strong>{channelMap.get(selectedChannelId)?.name}</strong>.
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsCopyDialogOpen(false);
                setSourceChannelId('');
                setCopyOverwrite(false);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => copyMutation.mutate()}
              disabled={!sourceChannelId || copyMutation.isPending}
            >
              {copyMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Copy className="mr-2 h-4 w-4" />
              )}
              Copy Pricing
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add/Edit Pricing Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {selectedPricing ? 'Edit Channel Pricing' : 'Add Channel Pricing'}
            </DialogTitle>
            <DialogDescription>
              {selectedPricing
                ? `Update pricing for ${productMap.get(selectedPricing.product_id)?.name || 'this product'}`
                : `Set product pricing for ${channelMap.get(selectedChannelId)?.name || 'this channel'}`}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {!selectedPricing && (
              <>
                {/* Step 1: Parent Category Dropdown */}
                <div className="space-y-2">
                  <Label>Parent Category</Label>
                  <Select
                    value={dialogParentCategoryId}
                    onValueChange={handleDialogParentCategoryChange}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select parent category" />
                    </SelectTrigger>
                    <SelectContent>
                      {parentCategories.map((category) => (
                        <SelectItem key={category.id} value={category.id}>
                          {category.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Step 2: Subcategory Dropdown (filtered by parent) */}
                <div className="space-y-2">
                  <Label>Subcategory</Label>
                  <Select
                    value={dialogSubcategoryId}
                    onValueChange={handleDialogSubcategoryChange}
                    disabled={!dialogParentCategoryId}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={dialogParentCategoryId ? "Select subcategory" : "Select parent first"} />
                    </SelectTrigger>
                    <SelectContent>
                      {dialogSubcategoriesLoading ? (
                        <SelectItem value="loading" disabled>Loading...</SelectItem>
                      ) : dialogSubcategories.length === 0 ? (
                        <SelectItem value="none" disabled>No subcategories found</SelectItem>
                      ) : (
                        dialogSubcategories.map((category) => (
                          <SelectItem key={category.id} value={category.id}>
                            {category.name}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                {/* Step 3: Product Dropdown (filtered by subcategory) */}
                <div className="space-y-2">
                  <Label>
                    Product
                    {dialogProductsLoading && <span className="text-muted-foreground ml-2">(Loading...)</span>}
                    {!dialogProductsLoading && dialogSubcategoryId && (
                      <span className="text-muted-foreground ml-2">({dialogProducts.length} available)</span>
                    )}
                  </Label>
                  <Select
                    value={formData.product_id}
                    onValueChange={(value) => {
                      const product = dialogProducts.find(p => p.id === value);
                      setFormData({
                        ...formData,
                        product_id: value,
                        mrp: product?.mrp || 0,
                        selling_price: product?.mrp || 0,
                      });
                    }}
                    disabled={!dialogSubcategoryId}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={dialogSubcategoryId ? "Select product" : "Select subcategory first"} />
                    </SelectTrigger>
                    <SelectContent>
                      {dialogProductsLoading ? (
                        <SelectItem value="loading" disabled>Loading products...</SelectItem>
                      ) : dialogProducts.length === 0 ? (
                        <SelectItem value="none" disabled>No products in this subcategory</SelectItem>
                      ) : (
                        dialogProducts.map((product) => (
                          <SelectItem key={product.id} value={product.id}>
                            {product.name} ({product.sku}) - ₹{product.mrp?.toLocaleString() || 0}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </>
            )}
            {/* Product Info Card - Shows when product is selected */}
            {formData.product_id && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs text-blue-600 font-medium uppercase tracking-wide mb-1">Product from Master Data</p>
                <div className="flex justify-between items-center">
                  <div>
                    <p className="font-semibold">
                      {dialogProducts.find(p => p.id === formData.product_id)?.name ||
                       products.find(p => p.id === formData.product_id)?.name || 'Selected Product'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      SKU: {dialogProducts.find(p => p.id === formData.product_id)?.sku ||
                            products.find(p => p.id === formData.product_id)?.sku || '-'}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">MRP (Master)</p>
                    <p className="font-bold text-lg">{formatCurrency(formData.mrp)}</p>
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>MRP <span className="text-xs text-muted-foreground">(from Product Master)</span></Label>
                <Input
                  type="number"
                  placeholder="0.00"
                  value={formData.mrp || ''}
                  readOnly
                  className="bg-muted cursor-not-allowed"
                />
                <p className="text-xs text-muted-foreground">Auto-filled from Product Master</p>
              </div>
              <div className="space-y-2">
                <Label>Selling Price <span className="text-xs text-red-500">*</span></Label>
                <Input
                  type="number"
                  placeholder="0.00"
                  value={formData.selling_price || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, selling_price: parseFloat(e.target.value) || 0 })
                  }
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Transfer Price (B2B)</Label>
                <Input
                  type="number"
                  placeholder="0.00"
                  value={formData.transfer_price || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, transfer_price: parseFloat(e.target.value) || 0 })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>Discount %</Label>
                <Input
                  type="number"
                  placeholder="0"
                  value={formData.discount_percentage || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, discount_percentage: parseFloat(e.target.value) || 0 })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Max Discount % (Guard Rail)</Label>
              <Input
                type="number"
                placeholder="25"
                value={formData.max_discount_percentage || ''}
                onChange={(e) =>
                  setFormData({ ...formData, max_discount_percentage: parseFloat(e.target.value) || 0 })
                }
              />
              <p className="text-xs text-muted-foreground">Maximum discount allowed on this product for this channel</p>
            </div>
            {formData.mrp > 0 && formData.selling_price > 0 && (
              <div className="p-3 bg-muted rounded-lg">
                <div className="flex justify-between text-sm">
                  <span>Calculated Margin:</span>
                  <span className={`font-medium ${
                    ((formData.mrp - formData.selling_price) / formData.mrp) * 100 >= 10
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}>
                    {(((formData.mrp - formData.selling_price) / formData.mrp) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createMutation.isPending || updateMutation.isPending || (!selectedPricing && !formData.product_id)}
            >
              {(createMutation.isPending || updateMutation.isPending) && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {selectedPricing ? 'Update Pricing' : 'Save Pricing'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
