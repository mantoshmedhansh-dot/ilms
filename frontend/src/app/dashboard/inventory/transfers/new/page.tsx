'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, ArrowRight, Warehouse, Package, Loader2, Search, X } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { PageHeader } from '@/components/common';
import { warehousesApi, productsApi, transfersApi } from '@/lib/api';

interface TransferItem {
  product_id: string;
  product_name: string;
  product_sku: string;
  quantity: number;
  available_quantity?: number;
}

interface WarehouseOption {
  id: string;
  name: string;
  code: string;
}

interface ProductOption {
  id: string;
  name: string;
  sku: string;
  stock_quantity?: number;
}

export default function NewTransferPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [sourceWarehouseId, setSourceWarehouseId] = useState<string>('');
  const [destinationWarehouseId, setDestinationWarehouseId] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [items, setItems] = useState<TransferItem[]>([]);
  const [productSearchOpen, setProductSearchOpen] = useState(false);
  const [productSearch, setProductSearch] = useState('');

  // Fetch warehouses
  const { data: warehousesData } = useQuery({
    queryKey: ['warehouses-dropdown'],
    queryFn: () => warehousesApi.list({ size: 100 }),
  });

  // Fetch products
  const { data: productsData } = useQuery({
    queryKey: ['products-dropdown', productSearch],
    queryFn: () => productsApi.list({ size: 50, search: productSearch || undefined }),
  });

  // Create transfer mutation
  const createMutation = useMutation({
    mutationFn: transfersApi.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['transfers'] });
      toast.success('Stock transfer created successfully');
      router.push('/inventory/transfers');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create transfer');
    },
  });

  const warehouses: WarehouseOption[] = warehousesData?.items ?? [];
  const products: ProductOption[] = productsData?.items ?? [];

  // Filter out destination warehouses to not include source
  const destinationWarehouses = warehouses.filter((w) => w.id !== sourceWarehouseId);

  // Filter out already added products
  const availableProducts = products.filter(
    (p) => !items.some((item) => item.product_id === p.id)
  );

  const handleAddProduct = (product: ProductOption) => {
    setItems([
      ...items,
      {
        product_id: product.id,
        product_name: product.name,
        product_sku: product.sku,
        quantity: 1,
        available_quantity: product.stock_quantity,
      },
    ]);
    setProductSearchOpen(false);
    setProductSearch('');
  };

  const handleRemoveProduct = (productId: string) => {
    setItems(items.filter((item) => item.product_id !== productId));
  };

  const handleQuantityChange = (productId: string, quantity: number) => {
    setItems(
      items.map((item) =>
        item.product_id === productId
          ? { ...item, quantity: Math.max(1, quantity) }
          : item
      )
    );
  };

  const handleSubmit = () => {
    // Validation
    if (!sourceWarehouseId) {
      toast.error('Please select a source warehouse');
      return;
    }
    if (!destinationWarehouseId) {
      toast.error('Please select a destination warehouse');
      return;
    }
    if (sourceWarehouseId === destinationWarehouseId) {
      toast.error('Source and destination warehouses must be different');
      return;
    }
    if (items.length === 0) {
      toast.error('Please add at least one product to transfer');
      return;
    }

    createMutation.mutate({
      from_warehouse_id: sourceWarehouseId,
      to_warehouse_id: destinationWarehouseId,
      items: items.map((item) => ({
        product_id: item.product_id,
        quantity: item.quantity,
      })),
      notes: notes || undefined,
    });
  };

  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);
  const sourceWarehouse = warehouses.find((w) => w.id === sourceWarehouseId);
  const destWarehouse = warehouses.find((w) => w.id === destinationWarehouseId);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Create Stock Transfer"
        description="Transfer inventory between warehouses"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => router.back()}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Transfer
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column - Warehouse Selection */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Source Warehouse</CardTitle>
              <CardDescription>Select where products will be transferred from</CardDescription>
            </CardHeader>
            <CardContent>
              <Select value={sourceWarehouseId} onValueChange={setSourceWarehouseId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select source warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {warehouses.map((wh) => (
                    <SelectItem key={wh.id} value={wh.id}>
                      <div className="flex items-center gap-2">
                        <Warehouse className="h-4 w-4" />
                        <span>{wh.name}</span>
                        <span className="text-muted-foreground">({wh.code})</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          <div className="flex justify-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              <ArrowRight className="h-5 w-5 text-primary" />
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Destination Warehouse</CardTitle>
              <CardDescription>Select where products will be transferred to</CardDescription>
            </CardHeader>
            <CardContent>
              <Select
                value={destinationWarehouseId}
                onValueChange={setDestinationWarehouseId}
                disabled={!sourceWarehouseId}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select destination warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {destinationWarehouses.map((wh) => (
                    <SelectItem key={wh.id} value={wh.id}>
                      <div className="flex items-center gap-2">
                        <Warehouse className="h-4 w-4" />
                        <span>{wh.name}</span>
                        <span className="text-muted-foreground">({wh.code})</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Notes</CardTitle>
              <CardDescription>Add any additional notes for this transfer</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="Enter notes (optional)"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
              />
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Products */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Transfer Items</CardTitle>
                  <CardDescription>
                    Add products to transfer between warehouses
                  </CardDescription>
                </div>
                <Popover open={productSearchOpen} onOpenChange={setProductSearchOpen}>
                  <PopoverTrigger asChild>
                    <Button disabled={!sourceWarehouseId}>
                      <Plus className="mr-2 h-4 w-4" />
                      Add Product
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[400px] p-0" align="end">
                    <Command>
                      <CommandInput
                        placeholder="Search products..."
                        value={productSearch}
                        onValueChange={setProductSearch}
                      />
                      <CommandList>
                        <CommandEmpty>No products found.</CommandEmpty>
                        <CommandGroup>
                          {availableProducts.map((product) => (
                            <CommandItem
                              key={product.id}
                              onSelect={() => handleAddProduct(product)}
                              className="cursor-pointer"
                            >
                              <div className="flex items-center gap-3">
                                <div className="flex h-8 w-8 items-center justify-center rounded bg-muted">
                                  <Package className="h-4 w-4" />
                                </div>
                                <div>
                                  <div className="font-medium">{product.name}</div>
                                  <div className="text-sm text-muted-foreground font-mono">
                                    {product.sku}
                                  </div>
                                </div>
                              </div>
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>
            </CardHeader>
            <CardContent>
              {items.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Package className="h-12 w-12 text-muted-foreground/50" />
                  <h3 className="mt-4 text-lg font-medium">No products added</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {sourceWarehouseId
                      ? 'Click "Add Product" to start adding items to transfer'
                      : 'Select a source warehouse first to add products'}
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Header */}
                  <div className="grid grid-cols-12 gap-4 text-sm font-medium text-muted-foreground border-b pb-2">
                    <div className="col-span-6">Product</div>
                    <div className="col-span-3">Quantity</div>
                    <div className="col-span-2">Available</div>
                    <div className="col-span-1"></div>
                  </div>

                  {/* Items */}
                  {items.map((item) => (
                    <div
                      key={item.product_id}
                      className="grid grid-cols-12 gap-4 items-center py-2 border-b last:border-0"
                    >
                      <div className="col-span-6">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                            <Package className="h-5 w-5 text-muted-foreground" />
                          </div>
                          <div>
                            <div className="font-medium">{item.product_name}</div>
                            <div className="text-sm text-muted-foreground font-mono">
                              {item.product_sku}
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="col-span-3">
                        <Input
                          type="number"
                          min="1"
                          value={item.quantity}
                          onChange={(e) =>
                            handleQuantityChange(item.product_id, parseInt(e.target.value) || 1)
                          }
                          className="w-24"
                        />
                      </div>
                      <div className="col-span-2">
                        <span className="text-sm text-muted-foreground">
                          {item.available_quantity ?? '-'}
                        </span>
                      </div>
                      <div className="col-span-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive hover:text-destructive"
                          onClick={() => handleRemoveProduct(item.product_id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}

                  {/* Summary */}
                  <div className="flex justify-between items-center pt-4 border-t">
                    <div className="text-sm text-muted-foreground">
                      {items.length} product(s), {totalItems} total units
                    </div>
                    {sourceWarehouse && destWarehouse && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium">{sourceWarehouse.name}</span>
                        <ArrowRight className="h-4 w-4" />
                        <span className="font-medium">{destWarehouse.name}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
