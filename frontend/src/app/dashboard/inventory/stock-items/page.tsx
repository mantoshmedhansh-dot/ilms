'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  Package,
  Warehouse,
  AlertTriangle,
  ArrowLeftRight,
  Filter,
  Barcode,
  FileText,
  Layers,
  Search,
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
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import { inventoryApi, warehousesApi } from '@/lib/api';
import { StockItem } from '@/types';

interface WarehouseOption {
  id: string;
  name: string;
  code: string;
}

const statusColors: Record<string, string> = {
  AVAILABLE: 'bg-green-100 text-green-800',
  RESERVED: 'bg-blue-100 text-blue-800',
  ALLOCATED: 'bg-indigo-100 text-indigo-800',
  PICKED: 'bg-cyan-100 text-cyan-800',
  PACKED: 'bg-teal-100 text-teal-800',
  IN_TRANSIT: 'bg-yellow-100 text-yellow-800',
  SHIPPED: 'bg-purple-100 text-purple-800',
  DAMAGED: 'bg-red-100 text-red-800',
  DEFECTIVE: 'bg-orange-100 text-orange-800',
  SOLD: 'bg-emerald-100 text-emerald-800',
  RETURNED: 'bg-pink-100 text-pink-800',
  QUARANTINE: 'bg-amber-100 text-amber-800',
  SCRAPPED: 'bg-gray-100 text-gray-800',
  OUT_OF_STOCK: 'bg-red-100 text-red-800',
};

const itemTypeColors: Record<string, string> = {
  FG: 'bg-blue-100 text-blue-800',
  SP: 'bg-purple-100 text-purple-800',
  CO: 'bg-cyan-100 text-cyan-800',
  CN: 'bg-amber-100 text-amber-800',
  AC: 'bg-emerald-100 text-emerald-800',
};

const itemTypeLabels: Record<string, string> = {
  FG: 'Finished Goods',
  SP: 'Spare Parts',
  CO: 'Components',
  CN: 'Consumables',
  AC: 'Accessories',
};

export default function StockItemsPage() {
  const [view, setView] = useState<'aggregate' | 'serialized'>('aggregate');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [warehouseFilter, setWarehouseFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [itemTypeFilter, setItemTypeFilter] = useState<string>('all');
  const [serialSearch, setSerialSearch] = useState<string>('');
  const [grnSearch, setGrnSearch] = useState<string>('');

  // Reset page when filters change
  const handleViewChange = (newView: string) => {
    setView(newView as 'aggregate' | 'serialized');
    setPage(0);
    setStatusFilter('all');
  };

  const { data, isLoading } = useQuery({
    queryKey: [
      'stock-items',
      view,
      page,
      pageSize,
      warehouseFilter,
      statusFilter,
      itemTypeFilter,
      serialSearch,
      grnSearch,
    ],
    queryFn: () =>
      inventoryApi.getStock({
        page: page + 1,
        size: pageSize,
        view,
        warehouse_id: warehouseFilter !== 'all' ? warehouseFilter : undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        item_type: itemTypeFilter !== 'all' ? itemTypeFilter : undefined,
        serial_number: serialSearch || undefined,
        grn_number: grnSearch || undefined,
      }),
  });

  const { data: warehousesData } = useQuery({
    queryKey: ['warehouses-dropdown'],
    queryFn: () => warehousesApi.list({ size: 100 }),
  });

  const { data: stats } = useQuery({
    queryKey: ['inventory-stats'],
    queryFn: inventoryApi.getStats,
  });

  // Columns for aggregate view (inventory_summary)
  const aggregateColumns: ColumnDef<StockItem>[] = [
    {
      accessorKey: 'product',
      header: 'Product',
      cell: ({ row }) => {
        const itemType = (row.original as any).item_type;
        return (
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
              <Package className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium">{row.original.product?.name || 'Unknown'}</span>
                {itemType && (
                  <Badge variant="outline" className={`text-xs ${itemTypeColors[itemType] || ''}`}>
                    {itemType}
                  </Badge>
                )}
              </div>
              <div className="text-sm text-muted-foreground font-mono">
                {row.original.product?.sku || '-'}
              </div>
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'warehouse',
      header: 'Warehouse',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Warehouse className="h-4 w-4 text-muted-foreground" />
          <div>
            <div className="text-sm font-medium">{row.original.warehouse?.name || 'Unknown'}</div>
            <div className="text-xs text-muted-foreground">{row.original.warehouse?.code}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'quantity',
      header: 'Total Qty',
      cell: ({ row }) => (
        <span className="font-mono text-sm font-medium">{row.original.quantity}</span>
      ),
    },
    {
      accessorKey: 'reserved_quantity',
      header: 'Reserved',
      cell: ({ row }) => (
        <span className="font-mono text-sm text-orange-600">{row.original.reserved_quantity}</span>
      ),
    },
    {
      accessorKey: 'available_quantity',
      header: 'Available',
      cell: ({ row }) => {
        const qty = row.original.available_quantity ?? 0;
        const color = qty > 10 ? 'text-green-600' : qty > 0 ? 'text-yellow-600' : 'text-red-600';
        return <span className={`font-mono text-sm font-medium ${color}`}>{qty}</span>;
      },
    },
    {
      accessorKey: 'reorder_level',
      header: 'Reorder Level',
      cell: ({ row }) => {
        const availableQty = row.original.available_quantity ?? 0;
        const reorderLevel = row.original.reorder_level ?? 0;
        const isLow = availableQty <= reorderLevel;
        return (
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm">{reorderLevel}</span>
            {isLow && <AlertTriangle className="h-4 w-4 text-yellow-500" />}
          </div>
        );
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <span
          className={`px-2 py-1 rounded-full text-xs font-medium ${
            statusColors[row.original.status] || 'bg-gray-100'
          }`}
        >
          {row.original.status?.replace('_', ' ') || '-'}
        </span>
      ),
    },
  ];

  // Columns for serialized view (stock_items with serial numbers)
  const serializedColumns: ColumnDef<StockItem>[] = [
    {
      accessorKey: 'serial_number',
      header: 'Serial Number',
      cell: ({ row }) => {
        const serial = (row.original as any).serial_number;
        const barcode = (row.original as any).barcode;
        return (
          <div className="flex items-center gap-2">
            <Barcode className="h-4 w-4 text-muted-foreground" />
            <div>
              <div className="font-mono text-sm font-medium">{serial || '-'}</div>
              {barcode && barcode !== serial && (
                <div className="font-mono text-xs text-muted-foreground">{barcode}</div>
              )}
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'product',
      header: 'Product',
      cell: ({ row }) => {
        const itemType = (row.original as any).item_type;
        return (
          <div className="flex items-center gap-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{row.original.product?.name || 'Unknown'}</span>
                {itemType && (
                  <Badge variant="outline" className={`text-xs ${itemTypeColors[itemType] || ''}`}>
                    {itemType}
                  </Badge>
                )}
              </div>
              <div className="text-xs text-muted-foreground font-mono">
                {row.original.product?.sku || '-'}
              </div>
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'warehouse',
      header: 'Warehouse',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Warehouse className="h-4 w-4 text-muted-foreground" />
          <div>
            <div className="text-sm">{row.original.warehouse?.name || 'Unknown'}</div>
            <div className="text-xs text-muted-foreground">{row.original.warehouse?.code}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'grn_number',
      header: 'GRN',
      cell: ({ row }) => {
        const grnNumber = (row.original as any).grn_number;
        return grnNumber ? (
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="font-mono text-sm text-blue-600">{grnNumber}</span>
          </div>
        ) : (
          <span className="text-muted-foreground">-</span>
        );
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <span
          className={`px-2 py-1 rounded-full text-xs font-medium ${
            statusColors[row.original.status] || 'bg-gray-100'
          }`}
        >
          {row.original.status?.replace('_', ' ') || '-'}
        </span>
      ),
    },
    {
      accessorKey: 'received_date',
      header: 'Received',
      cell: ({ row }) => {
        const receivedDate = (row.original as any).received_date;
        if (!receivedDate) return <span className="text-muted-foreground">-</span>;
        const date = new Date(receivedDate);
        return (
          <span className="text-sm text-muted-foreground">
            {date.toLocaleDateString('en-IN', {
              day: '2-digit',
              month: 'short',
              year: 'numeric',
            })}
          </span>
        );
      },
    },
  ];

  const warehouses: WarehouseOption[] = warehousesData?.items ?? [];
  const stockItems = data?.items ?? [];
  const columns = view === 'aggregate' ? aggregateColumns : serializedColumns;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Inventory"
        description="View and manage inventory stock levels across warehouses"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link href="/dashboard/inventory/adjustments">
                <Package className="mr-2 h-4 w-4" />
                Stock Adjustments
              </Link>
            </Button>
            <Button asChild>
              <Link href="/dashboard/inventory/transfers/new">
                <ArrowLeftRight className="mr-2 h-4 w-4" />
                Create Transfer
              </Link>
            </Button>
          </div>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total SKUs</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_skus ?? 0}</div>
            <p className="text-xs text-muted-foreground">Unique products in stock</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Stock</CardTitle>
            <Package className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.in_stock ?? 0}</div>
            <p className="text-xs text-muted-foreground">Items available</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Low Stock</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{stats?.low_stock ?? 0}</div>
            <p className="text-xs text-muted-foreground">Need reordering</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Out of Stock</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.out_of_stock ?? 0}</div>
            <p className="text-xs text-muted-foreground">Urgent attention needed</p>
          </CardContent>
        </Card>
      </div>

      {/* View Tabs */}
      <Tabs value={view} onValueChange={handleViewChange} className="w-full">
        <TabsList className="grid w-[400px] grid-cols-2">
          <TabsTrigger value="aggregate" className="flex items-center gap-2">
            <Layers className="h-4 w-4" />
            Stock Summary
          </TabsTrigger>
          <TabsTrigger value="serialized" className="flex items-center gap-2">
            <Barcode className="h-4 w-4" />
            Serialized Items
          </TabsTrigger>
        </TabsList>

        <div className="mt-4">
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-4 mb-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Filters:</span>
            </div>

            {/* Warehouse Filter */}
            <Select value={warehouseFilter} onValueChange={setWarehouseFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Warehouses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Warehouses</SelectItem>
                {warehouses.map((wh) => (
                  <SelectItem key={wh.id} value={wh.id}>
                    {wh.name} ({wh.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Item Type Filter */}
            <Select value={itemTypeFilter} onValueChange={setItemTypeFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Item Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Item Types</SelectItem>
                <SelectItem value="FG">Finished Goods (FG)</SelectItem>
                <SelectItem value="SP">Spare Parts (SP)</SelectItem>
                <SelectItem value="CO">Components (CO)</SelectItem>
                <SelectItem value="CN">Consumables (CN)</SelectItem>
                <SelectItem value="AC">Accessories (AC)</SelectItem>
              </SelectContent>
            </Select>

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                {view === 'aggregate' ? (
                  <>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="IN_STOCK">In Stock</SelectItem>
                    <SelectItem value="LOW_STOCK">Low Stock</SelectItem>
                    <SelectItem value="OUT_OF_STOCK">Out of Stock</SelectItem>
                  </>
                ) : (
                  <>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="AVAILABLE">Available</SelectItem>
                    <SelectItem value="RESERVED">Reserved</SelectItem>
                    <SelectItem value="ALLOCATED">Allocated</SelectItem>
                    <SelectItem value="PICKED">Picked</SelectItem>
                    <SelectItem value="PACKED">Packed</SelectItem>
                    <SelectItem value="IN_TRANSIT">In Transit</SelectItem>
                    <SelectItem value="SHIPPED">Shipped</SelectItem>
                    <SelectItem value="DAMAGED">Damaged</SelectItem>
                    <SelectItem value="SOLD">Sold</SelectItem>
                    <SelectItem value="RETURNED">Returned</SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>

            {/* Search inputs for serialized view */}
            {view === 'serialized' && (
              <>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search serial..."
                    value={serialSearch}
                    onChange={(e) => setSerialSearch(e.target.value)}
                    className="pl-9 w-[180px]"
                  />
                </div>
                <div className="relative">
                  <FileText className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search GRN..."
                    value={grnSearch}
                    onChange={(e) => setGrnSearch(e.target.value)}
                    className="pl-9 w-[180px]"
                  />
                </div>
              </>
            )}
          </div>

          {/* Data Table */}
          <TabsContent value="aggregate" className="mt-0">
            <DataTable
              columns={aggregateColumns}
              data={stockItems}
              searchKey="product"
              searchPlaceholder="Search products..."
              isLoading={isLoading}
              manualPagination
              pageCount={data?.pages ?? 0}
              pageIndex={page}
              pageSize={pageSize}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
            />
          </TabsContent>

          <TabsContent value="serialized" className="mt-0">
            <DataTable
              columns={serializedColumns}
              data={stockItems}
              searchKey="serial_number"
              searchPlaceholder="Search serial numbers..."
              isLoading={isLoading}
              manualPagination
              pageCount={data?.pages ?? 0}
              pageIndex={page}
              pageSize={pageSize}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
            />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
