'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  ArrowDownCircle,
  ArrowUpCircle,
  ArrowLeftRight,
  Package,
  Warehouse,
  Filter,
  Calendar,
  FileText,
  Barcode,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import { inventoryApi, warehousesApi } from '@/lib/api';
import { StockMovement } from '@/types';

interface WarehouseOption {
  id: string;
  name: string;
  code: string;
}

const movementTypeConfig: Record<string, { label: string; color: string; icon: typeof ArrowDownCircle }> = {
  RECEIPT: { label: 'Receipt', color: 'bg-green-100 text-green-800', icon: ArrowDownCircle },
  ISSUE: { label: 'Issue', color: 'bg-red-100 text-red-800', icon: ArrowUpCircle },
  TRANSFER_IN: { label: 'Transfer In', color: 'bg-blue-100 text-blue-800', icon: ArrowDownCircle },
  TRANSFER_OUT: { label: 'Transfer Out', color: 'bg-blue-100 text-blue-800', icon: ArrowUpCircle },
  RETURN_IN: { label: 'Return In', color: 'bg-purple-100 text-purple-800', icon: ArrowDownCircle },
  RETURN_OUT: { label: 'Return Out', color: 'bg-purple-100 text-purple-800', icon: ArrowUpCircle },
  ADJUSTMENT_PLUS: { label: 'Adjustment (+)', color: 'bg-emerald-100 text-emerald-800', icon: ArrowDownCircle },
  ADJUSTMENT_MINUS: { label: 'Adjustment (-)', color: 'bg-orange-100 text-orange-800', icon: ArrowUpCircle },
  DAMAGE: { label: 'Damage', color: 'bg-red-100 text-red-800', icon: ArrowUpCircle },
  SCRAP: { label: 'Scrap', color: 'bg-gray-100 text-gray-800', icon: ArrowUpCircle },
  CYCLE_COUNT: { label: 'Cycle Count', color: 'bg-cyan-100 text-cyan-800', icon: RefreshCw },
};

export default function StockMovementsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [warehouseFilter, setWarehouseFilter] = useState<string>('all');
  const [movementTypeFilter, setMovementTypeFilter] = useState<string>('all');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['stock-movements', page, pageSize, warehouseFilter, movementTypeFilter, dateFrom, dateTo],
    queryFn: () =>
      inventoryApi.getMovements({
        page: page + 1,
        size: pageSize,
        warehouse_id: warehouseFilter !== 'all' ? warehouseFilter : undefined,
        movement_type: movementTypeFilter !== 'all' ? movementTypeFilter : undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
  });

  const { data: warehousesData } = useQuery({
    queryKey: ['warehouses-dropdown'],
    queryFn: () => warehousesApi.list({ size: 100 }),
  });

  const columns: ColumnDef<StockMovement>[] = [
    {
      accessorKey: 'movement_number',
      header: 'Movement #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="font-mono text-sm font-medium">{row.original.movement_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'movement_type',
      header: 'Type',
      cell: ({ row }) => {
        const type = row.original.movement_type;
        const config = movementTypeConfig[type] || { label: type, color: 'bg-gray-100 text-gray-800', icon: ArrowLeftRight };
        const Icon = config.icon;
        return (
          <div className="flex items-center gap-2">
            <Icon className={`h-4 w-4 ${type.includes('IN') || type.includes('RECEIPT') || type.includes('PLUS') ? 'text-green-600' : 'text-red-600'}`} />
            <Badge variant="outline" className={config.color}>
              {config.label}
            </Badge>
          </div>
        );
      },
    },
    {
      accessorKey: 'product_name',
      header: 'Product',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Package className="h-4 w-4 text-muted-foreground" />
          <div>
            <div className="text-sm font-medium">{row.original.product_name || 'Unknown'}</div>
            <div className="text-xs text-muted-foreground font-mono">{row.original.product_sku || '-'}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'serial_number',
      header: 'Serial #',
      cell: ({ row }) => {
        const serial = row.original.serial_number;
        return serial ? (
          <div className="flex items-center gap-2">
            <Barcode className="h-4 w-4 text-muted-foreground" />
            <span className="font-mono text-sm">{serial}</span>
          </div>
        ) : (
          <span className="text-muted-foreground">-</span>
        );
      },
    },
    {
      accessorKey: 'warehouse_name',
      header: 'Warehouse',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Warehouse className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm">{row.original.warehouse_name || 'Unknown'}</span>
        </div>
      ),
    },
    {
      accessorKey: 'quantity',
      header: 'Qty',
      cell: ({ row }) => {
        const qty = row.original.quantity;
        const isPositive = qty > 0;
        return (
          <span className={`font-mono text-sm font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {isPositive ? '+' : ''}{qty}
          </span>
        );
      },
    },
    {
      accessorKey: 'balance_after',
      header: 'Balance',
      cell: ({ row }) => (
        <div className="text-sm">
          <span className="text-muted-foreground">{row.original.balance_before ?? '-'}</span>
          <span className="mx-1">→</span>
          <span className="font-medium">{row.original.balance_after ?? '-'}</span>
        </div>
      ),
    },
    {
      accessorKey: 'reference_number',
      header: 'Reference',
      cell: ({ row }) => {
        const refType = row.original.reference_type;
        const refNum = row.original.reference_number;
        return refNum ? (
          <div>
            <div className="text-xs text-muted-foreground uppercase">{refType || 'REF'}</div>
            <div className="font-mono text-sm text-blue-600">{refNum}</div>
          </div>
        ) : (
          <span className="text-muted-foreground">-</span>
        );
      },
    },
    {
      accessorKey: 'movement_date',
      header: 'Date',
      cell: ({ row }) => {
        const date = row.original.movement_date ? new Date(row.original.movement_date) : null;
        return date ? (
          <div className="text-sm">
            <div>{date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</div>
            <div className="text-xs text-muted-foreground">
              {date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        ) : (
          <span className="text-muted-foreground">-</span>
        );
      },
    },
  ];

  const warehouses: WarehouseOption[] = warehousesData?.items ?? [];
  const movements = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Stock Movements"
        description="View stock movement history and audit trail"
        actions={
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
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

        {/* Movement Type Filter */}
        <Select value={movementTypeFilter} onValueChange={setMovementTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="RECEIPT">Receipt</SelectItem>
            <SelectItem value="ISSUE">Issue</SelectItem>
            <SelectItem value="TRANSFER_IN">Transfer In</SelectItem>
            <SelectItem value="TRANSFER_OUT">Transfer Out</SelectItem>
            <SelectItem value="RETURN_IN">Return In</SelectItem>
            <SelectItem value="RETURN_OUT">Return Out</SelectItem>
            <SelectItem value="ADJUSTMENT_PLUS">Adjustment (+)</SelectItem>
            <SelectItem value="ADJUSTMENT_MINUS">Adjustment (-)</SelectItem>
            <SelectItem value="DAMAGE">Damage</SelectItem>
            <SelectItem value="SCRAP">Scrap</SelectItem>
            <SelectItem value="CYCLE_COUNT">Cycle Count</SelectItem>
          </SelectContent>
        </Select>

        {/* Date Range */}
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="w-[150px]"
            placeholder="From"
          />
          <span className="text-muted-foreground">to</span>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="w-[150px]"
            placeholder="To"
          />
        </div>

        {/* Clear Filters */}
        {(warehouseFilter !== 'all' || movementTypeFilter !== 'all' || dateFrom || dateTo) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setWarehouseFilter('all');
              setMovementTypeFilter('all');
              setDateFrom('');
              setDateTo('');
            }}
          >
            Clear Filters
          </Button>
        )}
      </div>

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={movements}
        searchKey="movement_number"
        searchPlaceholder="Search movements..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />
    </div>
  );
}
