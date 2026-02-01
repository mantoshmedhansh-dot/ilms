'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, Download, QrCode, Barcode, CheckCircle, XCircle, Settings, Package, Truck, Loader2 } from 'lucide-react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { serializationApi, ModelCodeReference, SupplierCode } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { useAuth } from '@/providers/auth-provider';

interface SerialItem {
  id: string;
  po_id: string;
  po_item_id?: string;
  product_id?: string;
  product_sku?: string;
  model_code: string;
  item_type: 'FG' | 'SP';
  brand_prefix: string;
  supplier_code: string;
  year_code: string;
  month_code: string;
  serial_number: number;
  barcode: string;
  status: string;
  grn_id?: string;
  received_at?: string;
  stock_item_id?: string;
  assigned_at?: string;
  order_id?: string;
  sold_at?: string;
  warranty_start_date?: string;
  warranty_end_date?: string;
  created_at: string;
}

interface Product {
  id: string;
  name: string;
  sku: string;
}

interface Vendor {
  id: string;
  name: string;
  code: string;
}

interface Category {
  id: string;
  name: string;
  slug: string;
  parent_id?: string;
}

interface Brand {
  id: string;
  name: string;
  slug: string;
}

interface CreateProductFormData {
  item_type: 'FG' | 'SP';
  category_code: string;
  subcategory_code: string;
  brand_code: string;
  model_code: string;
  name: string;
  description: string;
  category_id: string;
  brand_id: string;
  mrp: string;
  selling_price: string;
  cost_price: string;
  hsn_code: string;
  gst_rate: string;
  warranty_months: string;
}

const localSerializationApi = {
  list: async (params?: { page?: number; size?: number; status?: string; item_type?: string; search?: string }) => {
    try {
      const { data } = await apiClient.get('/serialization/serials', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  validate: async (barcode: string) => {
    try {
      const { data } = await apiClient.get(`/serialization/validate/${barcode}`);
      return data;
    } catch {
      return { valid: false, message: 'Barcode not found or invalid' };
    }
  },
};

const serialColumns: ColumnDef<SerialItem>[] = [
  {
    accessorKey: 'barcode',
    header: 'Barcode',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Barcode className="h-4 w-4 text-muted-foreground" />
        <div>
          <div className="font-mono font-medium">{row.original.barcode}</div>
          <div className="text-xs text-muted-foreground">
            Serial #{row.original.serial_number.toString().padStart(8, '0')}
          </div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'model_code',
    header: 'Model',
    cell: ({ row }) => (
      <div className="text-sm">
        <Badge variant="secondary" className="font-mono">
          {row.original.model_code}
        </Badge>
        <div className="text-muted-foreground font-mono text-xs mt-1">
          {row.original.product_sku || '-'}
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'item_type',
    header: 'Type',
    cell: ({ row }) => (
      <Badge variant={row.original.item_type === 'FG' ? 'default' : 'outline'}>
        {row.original.item_type === 'FG' ? 'Finished Good' : 'Spare Part'}
      </Badge>
    ),
  },
  {
    accessorKey: 'supplier_code',
    header: 'Supplier',
    cell: ({ row }) => (
      <span className="font-mono text-sm">{row.original.supplier_code}</span>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: 'created_at',
    header: 'Generated',
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(row.original.created_at)}
      </span>
    ),
  },
  {
    id: 'actions',
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Actions</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem>
            <Eye className="mr-2 h-4 w-4" />
            View Details
          </DropdownMenuItem>
          <DropdownMenuItem>
            <QrCode className="mr-2 h-4 w-4" />
            Print Barcode
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];

// Columns for Finished Goods (Water Purifiers)
const fgModelCodeColumns: ColumnDef<ModelCodeReference>[] = [
  {
    accessorKey: 'model_code',
    header: 'Model Code',
    cell: ({ row }) => (
      <Badge variant="secondary" className="font-mono text-base">
        {row.original.model_code}
      </Badge>
    ),
  },
  {
    accessorKey: 'fg_code',
    header: 'FG Code',
    cell: ({ row }) => (
      <span className="font-mono text-sm">{row.original.fg_code}</span>
    ),
  },
  {
    accessorKey: 'product_sku',
    header: 'Product SKU',
    cell: ({ row }) => (
      <span className="font-mono text-sm">{row.original.product_sku || '-'}</span>
    ),
  },
  {
    accessorKey: 'description',
    header: 'Description',
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">{row.original.description || '-'}</span>
    ),
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) => (
      <Badge variant={row.original.is_active ? 'default' : 'secondary'}>
        {row.original.is_active ? 'Active' : 'Inactive'}
      </Badge>
    ),
  },
];

// Columns for Spare Parts
const spModelCodeColumns: ColumnDef<ModelCodeReference>[] = [
  {
    accessorKey: 'model_code',
    header: 'Model Code',
    cell: ({ row }) => (
      <Badge variant="secondary" className="font-mono text-base">
        {row.original.model_code}
      </Badge>
    ),
  },
  {
    accessorKey: 'fg_code',
    header: 'Item Code',
    cell: ({ row }) => (
      <span className="font-mono text-sm">{row.original.fg_code}</span>
    ),
  },
  {
    accessorKey: 'product_sku',
    header: 'Product SKU',
    cell: ({ row }) => (
      <span className="font-mono text-sm">{row.original.product_sku || '-'}</span>
    ),
  },
  {
    accessorKey: 'description',
    header: 'Description',
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">{row.original.description || '-'}</span>
    ),
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) => (
      <Badge variant={row.original.is_active ? 'default' : 'secondary'}>
        {row.original.is_active ? 'Active' : 'Inactive'}
      </Badge>
    ),
  },
];

// supplierCodeColumns is defined inside the component to access handlers

export default function SerializationPage() {
  const queryClient = useQueryClient();
  const { permissions } = useAuth();
  const isSuperAdmin = permissions?.is_super_admin === true;
  const [activeTab, setActiveTab] = useState('serials');
  const [itemTypeFilter, setItemTypeFilter] = useState<'FG' | 'SP'>('FG'); // FG = Finished Goods, SP = Spare Parts
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [validateBarcode, setValidateBarcode] = useState('');
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    message: string;
    item?: SerialItem;
  } | null>(null);

  // Model Code Dialog State
  const [isModelCodeDialogOpen, setIsModelCodeDialogOpen] = useState(false);
  const [newModelCode, setNewModelCode] = useState({
    fg_code: '',
    model_code: '',
    item_type: 'FG',
    product_id: '',
    product_sku: '',
    description: '',
  });

  // Supplier Code Dialog State
  const [isSupplierCodeDialogOpen, setIsSupplierCodeDialogOpen] = useState(false);
  const [newSupplierCode, setNewSupplierCode] = useState({
    code: '',
    name: '',
    vendor_id: '',
    description: '',
  });

  // Link Vendor Dialog State
  const [isLinkVendorDialogOpen, setIsLinkVendorDialogOpen] = useState(false);
  const [linkVendorData, setLinkVendorData] = useState({
    code: '',
    vendor_id: '',
  });

  // Create Product Dialog State
  const [isCreateProductDialogOpen, setIsCreateProductDialogOpen] = useState(false);
  const [newProduct, setNewProduct] = useState<CreateProductFormData>({
    item_type: 'FG',
    category_code: 'WP',
    subcategory_code: 'R',
    brand_code: 'A',
    model_code: '',
    name: '',
    description: '',
    category_id: '',
    brand_id: '',
    mrp: '',
    selling_price: '',
    cost_price: '',
    hsn_code: '',
    gst_rate: '18',
    warranty_months: '12',
  });

  // Queries
  const { data: serialData, isLoading: serialsLoading } = useQuery({
    queryKey: ['serial-items', page, pageSize, itemTypeFilter],
    queryFn: () => localSerializationApi.list({ page: page + 1, size: pageSize, item_type: itemTypeFilter }),
  });

  const { data: modelCodes = [], isLoading: modelCodesLoading } = useQuery({
    queryKey: ['model-codes', itemTypeFilter],
    queryFn: () => serializationApi.getModelCodes(false, itemTypeFilter),
  });

  const { data: supplierCodes = [], isLoading: supplierCodesLoading } = useQuery({
    queryKey: ['supplier-codes'],
    queryFn: () => serializationApi.getSupplierCodes(false),
  });

  const { data: products = [] } = useQuery({
    queryKey: ['products-for-model-codes'],
    queryFn: async () => {
      try {
        const { data } = await apiClient.get('/products', { params: { limit: 500 } });
        return data.items || [];
      } catch {
        return [];
      }
    },
  });

  const { data: vendors = [] } = useQuery({
    queryKey: ['vendors-for-supplier-codes'],
    queryFn: async () => {
      try {
        const { data } = await apiClient.get('/vendors/dropdown', { params: { active_only: true } });
        return data || [];
      } catch {
        return [];
      }
    },
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['categories-for-products'],
    queryFn: async () => {
      try {
        const { data } = await apiClient.get('/categories', { params: { size: 100 } });
        return data.items || data || [];
      } catch {
        return [];
      }
    },
  });

  const { data: brands = [] } = useQuery({
    queryKey: ['brands-for-products'],
    queryFn: async () => {
      try {
        const { data } = await apiClient.get('/brands', { params: { size: 100 } });
        return data.items || data || [];
      } catch {
        return [];
      }
    },
  });

  // Mutations
  const createModelCodeMutation = useMutation({
    mutationFn: serializationApi.createModelCode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-codes'] });
      toast.success('Model code created successfully');
      setIsModelCodeDialogOpen(false);
      setNewModelCode({ fg_code: '', model_code: '', item_type: 'FG', product_id: '', product_sku: '', description: '' });
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create model code'),
  });

  const createSupplierCodeMutation = useMutation({
    mutationFn: serializationApi.createSupplierCode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supplier-codes'] });
      toast.success('Supplier code created successfully');
      setIsSupplierCodeDialogOpen(false);
      setNewSupplierCode({ code: '', name: '', vendor_id: '', description: '' });
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create supplier code'),
  });

  const linkVendorMutation = useMutation({
    mutationFn: async ({ code, vendor_id }: { code: string; vendor_id: string }) => {
      const { data } = await apiClient.put(`/serialization/suppliers/${code}/link-vendor?vendor_id=${vendor_id}`);
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['supplier-codes'] });
      toast.success(data.message || 'Vendor linked successfully');
      setIsLinkVendorDialogOpen(false);
      setLinkVendorData({ code: '', vendor_id: '' });
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to link vendor'),
  });

  const createProductMutation = useMutation({
    mutationFn: async (productData: CreateProductFormData) => {
      const { data } = await apiClient.post('/serialization/create-product', {
        item_type: productData.item_type,
        category_code: productData.category_code,
        subcategory_code: productData.subcategory_code,
        brand_code: productData.brand_code,
        model_code: productData.model_code,
        name: productData.name,
        description: productData.description || null,
        category_id: productData.category_id,
        brand_id: productData.brand_id,
        mrp: parseFloat(productData.mrp),
        selling_price: productData.selling_price ? parseFloat(productData.selling_price) : null,
        cost_price: productData.cost_price ? parseFloat(productData.cost_price) : null,
        hsn_code: productData.hsn_code || null,
        gst_rate: parseFloat(productData.gst_rate || '18'),
        warranty_months: parseInt(productData.warranty_months || '12'),
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['model-codes'] });
      queryClient.invalidateQueries({ queryKey: ['products-for-model-codes'] });
      toast.success(
        <div>
          <p className="font-medium">Product created successfully!</p>
          <p className="text-sm text-muted-foreground">FG Code: {data.fg_code}</p>
          <p className="text-sm text-muted-foreground">Barcode: {data.barcode_example}</p>
        </div>
      );
      setIsCreateProductDialogOpen(false);
      resetCreateProductForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create product'),
  });

  const handleValidate = async () => {
    if (!validateBarcode.trim()) return;
    try {
      const result = await localSerializationApi.validate(validateBarcode);
      setValidationResult(result);
    } catch {
      setValidationResult({
        valid: false,
        message: 'Barcode not found or invalid',
      });
    }
  };

  const handleCreateModelCode = () => {
    if (!newModelCode.model_code || newModelCode.model_code.length !== 3) {
      toast.error('Model code must be exactly 3 characters');
      return;
    }
    if (!newModelCode.product_sku) {
      toast.error('Please select a product');
      return;
    }
    createModelCodeMutation.mutate(newModelCode);
  };

  const handleCreateSupplierCode = () => {
    if (!newSupplierCode.code || newSupplierCode.code.length !== 2) {
      toast.error('Supplier code must be exactly 2 characters');
      return;
    }
    if (!newSupplierCode.name) {
      toast.error('Please enter supplier name');
      return;
    }
    createSupplierCodeMutation.mutate(newSupplierCode);
  };

  const handleLinkVendor = () => {
    if (!linkVendorData.vendor_id) {
      toast.error('Please select a vendor');
      return;
    }
    linkVendorMutation.mutate(linkVendorData);
  };

  const openLinkVendorDialog = (code: string) => {
    setLinkVendorData({ code, vendor_id: '' });
    setIsLinkVendorDialogOpen(true);
  };

  // Supplier Code columns (defined here to access handlers)
  const supplierCodeColumns: ColumnDef<SupplierCode>[] = [
    {
      accessorKey: 'code',
      header: 'Supplier Code',
      cell: ({ row }) => (
        <Badge variant="secondary" className="font-mono text-base">
          {row.original.code}
        </Badge>
      ),
    },
    {
      accessorKey: 'name',
      header: 'Supplier Name',
      cell: ({ row }) => (
        <span className="font-medium">{row.original.name}</span>
      ),
    },
    {
      accessorKey: 'vendor_id',
      header: 'Linked Vendor',
      cell: ({ row }) => {
        const vendor = vendors.find((v: Vendor) => v.id === row.original.vendor_id);
        return (
          <span className={row.original.vendor_id ? 'text-green-600 font-medium' : 'text-amber-600'}>
            {row.original.vendor_id ? (vendor?.name || 'Linked') : 'Not linked'}
          </span>
        );
      },
    },
    {
      accessorKey: 'is_active',
      header: 'Status',
      cell: ({ row }) => (
        <Badge variant={row.original.is_active ? 'default' : 'secondary'}>
          {row.original.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {!row.original.vendor_id && (
              <DropdownMenuItem onClick={() => openLinkVendorDialog(row.original.code)}>
                <Truck className="mr-2 h-4 w-4" />
                Link Vendor
              </DropdownMenuItem>
            )}
            {row.original.vendor_id && (
              <DropdownMenuItem className="text-green-600">
                <CheckCircle className="mr-2 h-4 w-4" />
                Vendor Linked
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const resetCreateProductForm = () => {
    setNewProduct({
      item_type: 'FG',
      category_code: 'WP',
      subcategory_code: 'R',
      brand_code: 'A',
      model_code: '',
      name: '',
      description: '',
      category_id: '',
      brand_id: '',
      mrp: '',
      selling_price: '',
      cost_price: '',
      hsn_code: '',
      gst_rate: '18',
      warranty_months: '12',
    });
  };

  const handleCreateProduct = () => {
    // Validation
    if (!newProduct.model_code || newProduct.model_code.length !== 3) {
      toast.error('Model code must be exactly 3 characters');
      return;
    }
    if (!newProduct.name.trim()) {
      toast.error('Please enter product name');
      return;
    }
    if (!newProduct.category_id) {
      toast.error('Please select a category');
      return;
    }
    if (!newProduct.brand_id) {
      toast.error('Please select a brand');
      return;
    }
    if (!newProduct.mrp || parseFloat(newProduct.mrp) <= 0) {
      toast.error('Please enter a valid MRP');
      return;
    }
    createProductMutation.mutate(newProduct);
  };

  // Generate preview FG Code
  const previewFGCode = `${newProduct.category_code}${newProduct.subcategory_code}${newProduct.brand_code}${newProduct.model_code}001`;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Serialization"
        description="Manage product serial numbers, barcodes, and code mappings"
        actions={
          <div className="flex gap-2 items-center">
            {/* Item Type Filter Buttons */}
            <div className="flex border rounded-lg overflow-hidden mr-2">
              <Button
                variant={itemTypeFilter === 'FG' ? 'default' : 'ghost'}
                size="sm"
                className={`rounded-none ${itemTypeFilter === 'FG' ? '' : 'hover:bg-muted'}`}
                onClick={() => setItemTypeFilter('FG')}
              >
                <Package className="mr-2 h-4 w-4" />
                Finished Goods
              </Button>
              <Button
                variant={itemTypeFilter === 'SP' ? 'default' : 'ghost'}
                size="sm"
                className={`rounded-none border-l ${itemTypeFilter === 'SP' ? '' : 'hover:bg-muted'}`}
                onClick={() => setItemTypeFilter('SP')}
              >
                <Settings className="mr-2 h-4 w-4" />
                Spare Parts
              </Button>
            </div>
            <Button
              size="sm"
              onClick={() => {
                setNewProduct({ ...newProduct, item_type: itemTypeFilter });
                setIsCreateProductDialogOpen(true);
              }}
            >
              <Plus className="mr-2 h-4 w-4" />
              Create New Product
            </Button>
            <Button variant="outline" size="sm">
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
        }
      />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3 lg:w-[400px]">
          <TabsTrigger value="serials" className="flex items-center gap-2">
            <Barcode className="h-4 w-4" />
            Serial Numbers
          </TabsTrigger>
          <TabsTrigger value="model-codes" className="flex items-center gap-2">
            <Package className="h-4 w-4" />
            Model Codes
          </TabsTrigger>
          <TabsTrigger value="supplier-codes" className="flex items-center gap-2">
            <Truck className="h-4 w-4" />
            Supplier Codes
          </TabsTrigger>
        </TabsList>

        {/* Serial Numbers Tab */}
        <TabsContent value="serials" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <QrCode className="h-5 w-5" />
                Barcode Validation
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4 items-end">
                <div className="flex-1">
                  <Input
                    placeholder="Scan or enter barcode"
                    value={validateBarcode}
                    onChange={(e) => setValidateBarcode(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleValidate()}
                  />
                </div>
                <Button onClick={handleValidate}>Validate</Button>
              </div>
              {validationResult && (
                <div className={`mt-4 p-4 rounded-lg ${
                  validationResult.valid ? 'bg-green-50' : 'bg-red-50'
                }`}>
                  <div className="flex items-center gap-2">
                    {validationResult.valid ? (
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-600" />
                    )}
                    <span className={validationResult.valid ? 'text-green-800' : 'text-red-800'}>
                      {validationResult.message}
                    </span>
                  </div>
                  {validationResult.item && (
                    <div className="mt-2 text-sm text-muted-foreground">
                      <div>Model: {validationResult.item.model_code} ({validationResult.item.product_sku || 'N/A'})</div>
                      <div>Status: {validationResult.item.status}</div>
                      <div>Type: {validationResult.item.item_type === 'FG' ? 'Finished Good' : 'Spare Part'}</div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <DataTable
            columns={serialColumns}
            data={serialData?.items ?? []}
            searchKey="barcode"
            searchPlaceholder="Search by barcode..."
            isLoading={serialsLoading}
            manualPagination
            pageCount={serialData?.pages ?? 0}
            pageIndex={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        </TabsContent>

        {/* Model Codes Tab */}
        <TabsContent value="model-codes" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  {itemTypeFilter === 'FG' ? (
                    <Package className="h-5 w-5" />
                  ) : (
                    <Settings className="h-5 w-5" />
                  )}
                  {itemTypeFilter === 'FG' ? 'Water Purifier Codes (Finished Goods)' : 'Spare Parts Codes'}
                </CardTitle>
                <CardDescription>
                  {itemTypeFilter === 'FG'
                    ? 'Map Water Purifier products to 3-character model codes for barcode generation'
                    : 'Map Spare Parts to 3-character model codes for barcode generation'
                  }
                </CardDescription>
              </div>
              <Button onClick={() => {
                setNewModelCode({ ...newModelCode, item_type: itemTypeFilter });
                setIsModelCodeDialogOpen(true);
              }}>
                <Plus className="mr-2 h-4 w-4" />
                Add {itemTypeFilter === 'FG' ? 'FG' : 'SP'} Code
              </Button>
            </CardHeader>
            <CardContent>
              {itemTypeFilter === 'FG' ? (
                <div className="p-4 mb-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-sm text-blue-800">
                    <strong>FG Barcode Format (16 chars):</strong> AP + YearCode(2) + MonthCode(1) + <strong>ModelCode(3)</strong> + Serial(8)
                  </p>
                  <p className="text-xs text-blue-600 mt-1">
                    Example: AP<strong>AA</strong><strong>A</strong><strong>IEL</strong>00000001 (AA=2026, A=Jan, IEL=Model, Serial)
                  </p>
                  <p className="text-xs text-blue-600 mt-1">
                    <strong>FG Code Format:</strong> WP(Category) + R(Subcategory) + A(Brand) + IEL(Model) + 001(Seq) = WPRAIEL001
                  </p>
                </div>
              ) : (
                <div className="p-4 mb-4 bg-orange-50 rounded-lg border border-orange-200">
                  <p className="text-sm text-orange-800">
                    <strong>SP Barcode Format (16 chars):</strong> AP + SupplierCode(2) + YearCode(1) + MonthCode(1) + ChannelCode(2) + Serial(8)
                  </p>
                  <p className="text-xs text-orange-600 mt-1">
                    Example: AP<strong>FS</strong><strong>A</strong><strong>A</strong><strong>EC</strong>00000001 (FS=FastTrack, A=2026, A=Jan, EC=Economical)
                  </p>
                  <p className="text-xs text-orange-600 mt-1">
                    <strong>SP Code Format:</strong> SP(Category) + SD(Subcategory) + F(Brand) + SDF(Model) + 001(Seq) = SPSDFSD001
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <DataTable
            columns={itemTypeFilter === 'FG' ? fgModelCodeColumns : spModelCodeColumns}
            data={modelCodes.filter((code: ModelCodeReference) => code.item_type === itemTypeFilter)}
            searchKey="product_sku"
            searchPlaceholder={itemTypeFilter === 'FG' ? 'Search Water Purifiers...' : 'Search Spare Parts...'}
            isLoading={modelCodesLoading}
          />
        </TabsContent>

        {/* Supplier Codes Tab */}
        <TabsContent value="supplier-codes" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Truck className="h-5 w-5" />
                  Supplier Codes
                </CardTitle>
                <CardDescription>
                  Map vendors to 2-character supplier codes for barcode generation
                </CardDescription>
              </div>
              <Button onClick={() => setIsSupplierCodeDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add Supplier Code
              </Button>
            </CardHeader>
            <CardContent>
              <div className="p-4 mb-4 bg-green-50 rounded-lg border border-green-200">
                <p className="text-sm text-green-800">
                  <strong>Barcode Format:</strong> AP + <strong>Supplier(2)</strong> + Year(1) + Month(1) + Model(3) + Serial(6)
                </p>
                <p className="text-xs text-green-600 mt-1">
                  Example: AP<strong>FS</strong>AASDF000001 (FS=Supplier Code for the vendor/manufacturer)
                </p>
              </div>
            </CardContent>
          </Card>

          <DataTable
            columns={supplierCodeColumns}
            data={supplierCodes}
            searchKey="name"
            searchPlaceholder="Search by name..."
            isLoading={supplierCodesLoading}
          />
        </TabsContent>
      </Tabs>

      {/* Add Model Code Dialog */}
      <Dialog open={isModelCodeDialogOpen} onOpenChange={setIsModelCodeDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Model Code</DialogTitle>
            <DialogDescription>
              Create a 3-character model code for a product. This will be used in barcode generation.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Product *</Label>
              <Select
                value={newModelCode.product_id || 'select'}
                onValueChange={(value) => {
                  if (value === 'select') return;
                  const product = products.find((p: Product) => p.id === value);
                  setNewModelCode({
                    ...newModelCode,
                    product_id: value,
                    product_sku: product?.sku || '',
                    fg_code: product?.sku || '',
                  });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select product" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="select" disabled>Select product</SelectItem>
                  {products.map((p: Product) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.name} ({p.sku})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Model Code (3 chars) *</Label>
                <Input
                  placeholder="e.g., SDF"
                  maxLength={3}
                  className="font-mono uppercase"
                  value={newModelCode.model_code}
                  onChange={(e) => setNewModelCode({ ...newModelCode, model_code: e.target.value.toUpperCase() })}
                />
                <p className="text-xs text-muted-foreground">Must be exactly 3 characters</p>
              </div>
              <div className="space-y-2">
                <Label>Item Type</Label>
                <Select
                  value={newModelCode.item_type}
                  onValueChange={(value) => setNewModelCode({ ...newModelCode, item_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="FG">Finished Goods (FG)</SelectItem>
                    <SelectItem value="RM">Raw Material (RM)</SelectItem>
                    <SelectItem value="SFG">Semi-Finished (SFG)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                placeholder="Optional description"
                value={newModelCode.description}
                onChange={(e) => setNewModelCode({ ...newModelCode, description: e.target.value })}
              />
            </div>
            {newModelCode.model_code.length === 3 && (
              <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
                <p className="text-sm text-purple-800">
                  <strong>Preview:</strong> AP??AA<strong>{newModelCode.model_code}</strong>000001
                </p>
                <p className="text-xs text-purple-600 mt-1">
                  ?? = Supplier code (set per vendor)
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsModelCodeDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateModelCode} disabled={createModelCodeMutation.isPending}>
              {createModelCodeMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Supplier Code Dialog */}
      <Dialog open={isSupplierCodeDialogOpen} onOpenChange={setIsSupplierCodeDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Supplier Code</DialogTitle>
            <DialogDescription>
              Create a 2-character supplier code for a vendor/manufacturer. This will be used in barcode generation.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Vendor (Optional)</Label>
              <Select
                value={newSupplierCode.vendor_id || 'none'}
                onValueChange={(value) => {
                  if (value === 'none') {
                    setNewSupplierCode({ ...newSupplierCode, vendor_id: '' });
                    return;
                  }
                  const vendor = vendors.find((v: Vendor) => v.id === value);
                  setNewSupplierCode({
                    ...newSupplierCode,
                    vendor_id: value,
                    name: vendor?.name || newSupplierCode.name,
                  });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select vendor" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No linked vendor</SelectItem>
                  {vendors.map((v: Vendor) => (
                    <SelectItem key={v.id} value={v.id}>
                      {v.name} ({v.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Supplier Code (2 chars) *</Label>
                <Input
                  placeholder="e.g., FS"
                  maxLength={2}
                  className="font-mono uppercase"
                  value={newSupplierCode.code}
                  onChange={(e) => setNewSupplierCode({ ...newSupplierCode, code: e.target.value.toUpperCase() })}
                />
                <p className="text-xs text-muted-foreground">Must be exactly 2 characters</p>
              </div>
              <div className="space-y-2">
                <Label>Supplier Name *</Label>
                <Input
                  placeholder="e.g., Fujian Supplier"
                  value={newSupplierCode.name}
                  onChange={(e) => setNewSupplierCode({ ...newSupplierCode, name: e.target.value })}
                />
              </div>
            </div>
            {newSupplierCode.code.length === 2 && (
              <div className="p-3 bg-green-50 rounded-lg border border-green-200">
                <p className="text-sm text-green-800">
                  <strong>Preview:</strong> AP<strong>{newSupplierCode.code}</strong>AA???000001
                </p>
                <p className="text-xs text-green-600 mt-1">
                  ??? = Model code (set per product)
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsSupplierCodeDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateSupplierCode} disabled={createSupplierCodeMutation.isPending}>
              {createSupplierCodeMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Link Vendor Dialog */}
      <Dialog open={isLinkVendorDialogOpen} onOpenChange={setIsLinkVendorDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Link Vendor to Supplier Code</DialogTitle>
            <DialogDescription>
              Link a vendor to supplier code <strong>{linkVendorData.code}</strong>. This is required for barcode generation during PO approval.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Supplier Code</Label>
              <Badge variant="secondary" className="font-mono text-lg">
                {linkVendorData.code}
              </Badge>
            </div>
            <div className="space-y-2">
              <Label>Select Vendor *</Label>
              <Select
                value={linkVendorData.vendor_id || 'none'}
                onValueChange={(value) => {
                  if (value === 'none') {
                    setLinkVendorData({ ...linkVendorData, vendor_id: '' });
                    return;
                  }
                  setLinkVendorData({ ...linkVendorData, vendor_id: value });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select vendor to link" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none" disabled>Select a vendor</SelectItem>
                  {vendors.map((vendor: Vendor) => (
                    <SelectItem key={vendor.id} value={vendor.id}>
                      {vendor.name} ({vendor.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">Choose the vendor/supplier to link to this code</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsLinkVendorDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleLinkVendor} disabled={linkVendorMutation.isPending}>
              {linkVendorMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Link Vendor
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Product with Code Dialog */}
      <Dialog open={isCreateProductDialogOpen} onOpenChange={setIsCreateProductDialogOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {newProduct.item_type === 'FG' ? (
                <Package className="h-5 w-5" />
              ) : (
                <Settings className="h-5 w-5" />
              )}
              Create New {newProduct.item_type === 'FG' ? 'Finished Good' : 'Spare Part'}
            </DialogTitle>
            <DialogDescription>
              Create a new product with auto-generated FG Code / Item Code. The product will be added to both the Serialization codes and Products catalog.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* Item Type Selection */}
            <div className="space-y-2">
              <Label>Product Type *</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={newProduct.item_type === 'FG' ? 'default' : 'outline'}
                  className="flex-1"
                  onClick={() => setNewProduct({
                    ...newProduct,
                    item_type: 'FG',
                    category_code: 'WP',
                    subcategory_code: 'R',
                  })}
                >
                  <Package className="mr-2 h-4 w-4" />
                  Finished Goods
                </Button>
                <Button
                  type="button"
                  variant={newProduct.item_type === 'SP' ? 'default' : 'outline'}
                  className="flex-1"
                  onClick={() => setNewProduct({
                    ...newProduct,
                    item_type: 'SP',
                    category_code: 'SP',
                    subcategory_code: 'SD',
                  })}
                >
                  <Settings className="mr-2 h-4 w-4" />
                  Spare Parts
                </Button>
              </div>
            </div>

            {/* Code Components */}
            <div className="space-y-2">
              <Label>Code Components *</Label>
              <p className="text-xs text-muted-foreground mb-2">
                These codes combine to create the FG Code / Item Code
              </p>
              <div className="grid grid-cols-4 gap-2">
                <div>
                  <Label className="text-xs">Category (2)</Label>
                  <Input
                    placeholder="WP"
                    maxLength={2}
                    className="font-mono uppercase"
                    value={newProduct.category_code}
                    onChange={(e) => setNewProduct({ ...newProduct, category_code: e.target.value.toUpperCase() })}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {newProduct.item_type === 'FG' ? 'WP=Water Purifier' : 'SP=Spare Part'}
                  </p>
                </div>
                <div>
                  <Label className="text-xs">Subcategory (1-2)</Label>
                  <Input
                    placeholder="R"
                    maxLength={2}
                    className="font-mono uppercase"
                    value={newProduct.subcategory_code}
                    onChange={(e) => setNewProduct({ ...newProduct, subcategory_code: e.target.value.toUpperCase() })}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {newProduct.item_type === 'FG' ? 'R=RO, U=UV' : 'SD=Sediment, CB=Carbon'}
                  </p>
                </div>
                <div>
                  <Label className="text-xs">Brand (1)</Label>
                  <Input
                    placeholder="A"
                    maxLength={1}
                    className="font-mono uppercase"
                    value={newProduct.brand_code}
                    onChange={(e) => setNewProduct({ ...newProduct, brand_code: e.target.value.toUpperCase() })}
                  />
                  <p className="text-xs text-muted-foreground mt-1">A=Aquapurite</p>
                </div>
                <div>
                  <Label className="text-xs">Model (3) *</Label>
                  <Input
                    placeholder="IEL"
                    maxLength={3}
                    className="font-mono uppercase"
                    value={newProduct.model_code}
                    onChange={(e) => setNewProduct({ ...newProduct, model_code: e.target.value.toUpperCase() })}
                  />
                  <p className="text-xs text-muted-foreground mt-1">For barcode</p>
                </div>
              </div>
            </div>

            {/* FG Code Preview */}
            {newProduct.model_code.length === 3 && (
              <div className={`p-4 rounded-lg border ${newProduct.item_type === 'FG' ? 'bg-blue-50 border-blue-200' : 'bg-orange-50 border-orange-200'}`}>
                <p className={`text-sm font-medium ${newProduct.item_type === 'FG' ? 'text-blue-800' : 'text-orange-800'}`}>
                  Generated Codes Preview:
                </p>
                <div className="mt-2 space-y-1">
                  <p className={`font-mono text-lg ${newProduct.item_type === 'FG' ? 'text-blue-900' : 'text-orange-900'}`}>
                    {newProduct.item_type === 'FG' ? 'FG Code' : 'Item Code'}: <strong>{previewFGCode}</strong>
                  </p>
                  <p className={`font-mono text-sm ${newProduct.item_type === 'FG' ? 'text-blue-700' : 'text-orange-700'}`}>
                    Product SKU: <strong>{previewFGCode}</strong>
                  </p>
                  <p className={`font-mono text-sm ${newProduct.item_type === 'FG' ? 'text-blue-700' : 'text-orange-700'}`}>
                    Model Code: <strong>{newProduct.model_code}</strong> (used in barcode)
                  </p>
                  <p className={`font-mono text-xs ${newProduct.item_type === 'FG' ? 'text-blue-600' : 'text-orange-600'} mt-2`}>
                    Barcode Example: APFSAA{newProduct.model_code}00000001
                  </p>
                </div>
              </div>
            )}

            {/* Product Details */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Product Name *</Label>
                <Input
                  placeholder="e.g., IELITZ RO Water Purifier"
                  value={newProduct.name}
                  onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label>Description</Label>
                <Input
                  placeholder="Optional product description"
                  value={newProduct.description}
                  onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Brand *</Label>
                  <Select
                    value={newProduct.brand_id || 'select'}
                    onValueChange={(value) => {
                      if (value !== 'select') {
                        setNewProduct({ ...newProduct, brand_id: value });
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select brand" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="select" disabled>Select brand</SelectItem>
                      {brands.map((b: Brand) => (
                        <SelectItem key={b.id} value={b.id}>
                          {b.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Category *</Label>
                  <Select
                    value={newProduct.category_id || 'select'}
                    onValueChange={(value) => {
                      if (value !== 'select') {
                        setNewProduct({ ...newProduct, category_id: value });
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="select" disabled>Select category</SelectItem>
                      {categories.map((c: Category) => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Pricing */}
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>MRP (₹) *</Label>
                  <Input
                    type="number"
                    placeholder="0.00"
                    value={newProduct.mrp}
                    onChange={(e) => setNewProduct({ ...newProduct, mrp: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Selling Price (₹)</Label>
                  <Input
                    type="number"
                    placeholder="Same as MRP"
                    value={newProduct.selling_price}
                    onChange={(e) => setNewProduct({ ...newProduct, selling_price: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Cost Price (₹)</Label>
                  <Input
                    type="number"
                    placeholder="0.00"
                    value={newProduct.cost_price}
                    onChange={(e) => setNewProduct({ ...newProduct, cost_price: e.target.value })}
                  />
                </div>
              </div>

              {/* Tax & Warranty */}
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>HSN Code</Label>
                  <Input
                    placeholder="e.g., 8421"
                    value={newProduct.hsn_code}
                    onChange={(e) => setNewProduct({ ...newProduct, hsn_code: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>GST Rate (%)</Label>
                  <Select
                    value={newProduct.gst_rate}
                    onValueChange={(value) => setNewProduct({ ...newProduct, gst_rate: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">0%</SelectItem>
                      <SelectItem value="5">5%</SelectItem>
                      <SelectItem value="12">12%</SelectItem>
                      <SelectItem value="18">18%</SelectItem>
                      <SelectItem value="28">28%</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Warranty (months)</Label>
                  <Input
                    type="number"
                    placeholder="12"
                    value={newProduct.warranty_months}
                    onChange={(e) => setNewProduct({ ...newProduct, warranty_months: e.target.value })}
                  />
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsCreateProductDialogOpen(false);
                resetCreateProductForm();
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateProduct}
              disabled={createProductMutation.isPending}
            >
              {createProductMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Product
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
