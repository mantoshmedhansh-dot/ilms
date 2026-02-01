'use client';

import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, RefreshCw, Package, AlertTriangle, CheckCircle, XCircle, Loader2 } from 'lucide-react';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatDate } from '@/lib/utils';

interface ChannelInventory {
  id: string;
  channel_id: string;
  channel_name: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  warehouse_quantity: number;
  channel_quantity: number;
  reserved_quantity: number;
  available_quantity: number;
  sync_status: 'SYNCED' | 'PENDING' | 'FAILED' | 'OUT_OF_SYNC';
  last_synced_at: string;
  buffer_stock: number;
}

interface InventoryStats {
  total_products: number;
  synced_count: number;
  out_of_sync_count: number;
  failed_count: number;
}

const channelInventoryApi = {
  list: async (params?: { page?: number; size?: number; channel_id?: string; sync_status?: string }) => {
    try {
      const { data } = await apiClient.get('/channels/inventory', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (channelId?: string): Promise<InventoryStats> => {
    try {
      const params = channelId ? { channel_id: channelId } : {};
      const { data } = await apiClient.get('/channels/inventory/stats', { params });
      return data;
    } catch {
      return { total_products: 0, synced_count: 0, out_of_sync_count: 0, failed_count: 0 };
    }
  },
  syncProduct: async (id: string) => {
    const { data } = await apiClient.post(`/channels/inventory/${id}/sync`);
    return data;
  },
  syncAll: async (channelId?: string) => {
    const params = channelId ? { channel_id: channelId } : {};
    const { data } = await apiClient.post('/channels/inventory/sync-all', null, { params });
    return data;
  },
  updateBuffer: async (id: string, bufferStock: number) => {
    const { data } = await apiClient.put(`/channels/inventory/${id}/buffer`, null, {
      params: { buffer_stock: bufferStock }
    });
    return data;
  },
};

const syncStatusColors: Record<string, { bg: string; text: string; icon: React.ComponentType<{ className?: string }> }> = {
  SYNCED: { bg: 'bg-green-100', text: 'text-green-800', icon: CheckCircle },
  PENDING: { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: RefreshCw },
  FAILED: { bg: 'bg-red-100', text: 'text-red-800', icon: XCircle },
  OUT_OF_SYNC: { bg: 'bg-orange-100', text: 'text-orange-800', icon: AlertTriangle },
};

// Separate component for action cell to avoid hooks in render function
function InventoryActionsCell({
  inventory,
  onEditBuffer,
}: {
  inventory: ChannelInventory;
  onEditBuffer: (inventory: ChannelInventory) => void;
}) {
  const queryClient = useQueryClient();

  const syncMutation = useMutation({
    mutationFn: () => channelInventoryApi.syncProduct(inventory.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel-inventory'] });
      toast.success('Inventory synced successfully');
    },
    onError: () => {
      toast.error('Failed to sync inventory');
    },
  });

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
        <DropdownMenuItem onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}>
          <RefreshCw className={`mr-2 h-4 w-4 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
          Sync Now
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onEditBuffer(inventory)}>
          <Package className="mr-2 h-4 w-4" />
          Edit Buffer Stock
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Column definitions factory function
function getColumns(onEditBuffer: (inventory: ChannelInventory) => void): ColumnDef<ChannelInventory>[] {
  return [
    {
      accessorKey: 'product_name',
      header: 'Product',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Package className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium">{row.original.product_name}</div>
            <div className="text-sm text-muted-foreground">{row.original.product_sku}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'channel_name',
      header: 'Channel',
      cell: ({ row }) => (
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          {row.original.channel_name}
        </span>
      ),
    },
    {
      accessorKey: 'warehouse_quantity',
      header: 'Warehouse Qty',
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.original.warehouse_quantity}</span>
      ),
    },
    {
      accessorKey: 'channel_quantity',
      header: 'Channel Qty',
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.original.channel_quantity}</span>
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
        const qty = row.original.available_quantity;
        const color = qty > 10 ? 'text-green-600' : qty > 0 ? 'text-yellow-600' : 'text-red-600';
        return <span className={`font-mono text-sm font-medium ${color}`}>{qty}</span>;
      },
    },
    {
      accessorKey: 'sync_status',
      header: 'Sync Status',
      cell: ({ row }) => {
        const status = row.original.sync_status;
        const config = syncStatusColors[status] || syncStatusColors.PENDING;
        const Icon = config.icon;
        return (
          <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
            <Icon className="h-3 w-3" />
            {status.replace('_', ' ')}
          </div>
        );
      },
    },
    {
      accessorKey: 'last_synced_at',
      header: 'Last Synced',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {row.original.last_synced_at ? formatDate(row.original.last_synced_at) : 'Never'}
        </span>
      ),
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <InventoryActionsCell inventory={row.original} onEditBuffer={onEditBuffer} />
      ),
    },
  ];
}

export default function ChannelInventoryPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [channelFilter, setChannelFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isBufferDialogOpen, setIsBufferDialogOpen] = useState(false);
  const [selectedInventory, setSelectedInventory] = useState<ChannelInventory | null>(null);
  const [bufferStock, setBufferStock] = useState<number>(0);

  const queryClient = useQueryClient();

  // Handler for editing buffer stock
  const handleEditBuffer = (inventory: ChannelInventory) => {
    setSelectedInventory(inventory);
    setBufferStock(inventory.buffer_stock || 0);
    setIsBufferDialogOpen(true);
  };

  // Generate columns with handler
  const columns = useMemo(() => getColumns(handleEditBuffer), []);

  // Update buffer mutation
  const updateBufferMutation = useMutation({
    mutationFn: () => {
      if (!selectedInventory) throw new Error('No inventory selected');
      return channelInventoryApi.updateBuffer(selectedInventory.id, bufferStock);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel-inventory'] });
      toast.success('Buffer stock updated successfully');
      setIsBufferDialogOpen(false);
      setSelectedInventory(null);
    },
    onError: () => {
      toast.error('Failed to update buffer stock');
    },
  });

  const { data, isLoading } = useQuery({
    queryKey: ['channel-inventory', page, pageSize, channelFilter, statusFilter],
    queryFn: () => channelInventoryApi.list({
      page: page + 1,
      size: pageSize,
      channel_id: channelFilter !== 'all' ? channelFilter : undefined,
      sync_status: statusFilter !== 'all' ? statusFilter : undefined,
    }),
  });

  const { data: stats } = useQuery({
    queryKey: ['channel-inventory-stats', channelFilter],
    queryFn: () => channelInventoryApi.getStats(channelFilter !== 'all' ? channelFilter : undefined),
  });

  // Fetch channels for dropdown
  const { data: channelsData } = useQuery({
    queryKey: ['channels-dropdown'],
    queryFn: async () => {
      try {
        const { data } = await apiClient.get('/channels/dropdown');
        return data.items || data || [];
      } catch {
        return [];
      }
    },
  });

  const syncAllMutation = useMutation({
    mutationFn: () => channelInventoryApi.syncAll(channelFilter !== 'all' ? channelFilter : undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel-inventory'] });
      toast.success('Sync initiated for all products');
    },
    onError: () => {
      toast.error('Failed to initiate sync');
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Channel Inventory"
        description="Manage and sync inventory levels across sales channels"
        actions={
          <Button onClick={() => syncAllMutation.mutate()} disabled={syncAllMutation.isPending}>
            <RefreshCw className={`mr-2 h-4 w-4 ${syncAllMutation.isPending ? 'animate-spin' : ''}`} />
            Sync All
          </Button>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Products</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_products || 0}</div>
            <p className="text-xs text-muted-foreground">Mapped to channels</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Synced</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.synced_count || 0}</div>
            <p className="text-xs text-muted-foreground">In sync with channels</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Out of Sync</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.out_of_sync_count || 0}</div>
            <p className="text-xs text-muted-foreground">Need attention</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.failed_count || 0}</div>
            <p className="text-xs text-muted-foreground">Sync failed</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={channelFilter} onValueChange={setChannelFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by channel" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Channels</SelectItem>
            {(channelsData || []).map((channel: { id: string; name: string; channel_code?: string }) => (
              <SelectItem key={channel.id} value={channel.id}>
                {channel.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="SYNCED">Synced</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="OUT_OF_SYNC">Out of Sync</SelectItem>
            <SelectItem value="FAILED">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="product_name"
        searchPlaceholder="Search products..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Edit Buffer Stock Dialog */}
      <Dialog open={isBufferDialogOpen} onOpenChange={setIsBufferDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Edit Buffer Stock</DialogTitle>
            <DialogDescription>
              Set the buffer stock level for this product on the channel.
            </DialogDescription>
          </DialogHeader>
          {selectedInventory && (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <div className="text-sm font-medium">{selectedInventory.product_name}</div>
                <div className="text-xs text-muted-foreground">{selectedInventory.product_sku}</div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="buffer_stock">Buffer Stock</Label>
                <Input
                  id="buffer_stock"
                  type="number"
                  min="0"
                  value={bufferStock}
                  onChange={(e) => setBufferStock(parseInt(e.target.value) || 0)}
                  placeholder="Enter buffer stock"
                />
                <p className="text-xs text-muted-foreground">
                  Buffer stock is reserved and not shown as available on the channel.
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsBufferDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => updateBufferMutation.mutate()} disabled={updateBufferMutation.isPending}>
              {updateBufferMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
