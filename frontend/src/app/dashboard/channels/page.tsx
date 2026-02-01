'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Eye, Power, PowerOff, Network, ShoppingBag, TrendingUp } from 'lucide-react';
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
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency, formatDate } from '@/lib/utils';

interface SalesChannel {
  id: string;
  name: string;
  code: string;
  channel_type: 'D2C' | 'MARKETPLACE' | 'B2B' | 'DEALER' | 'OFFLINE';
  marketplace_name?: string;
  api_key?: string;
  api_secret?: string;
  seller_id?: string;
  warehouse_id?: string;
  is_active: boolean;
  auto_sync_orders: boolean;
  auto_sync_inventory: boolean;
  commission_rate?: number;
  description?: string;
  created_at: string;
}

interface ChannelStats {
  total_channels: number;
  active_channels: number;
  total_orders_today: number;
  total_revenue_today: number;
}

const channelsApi = {
  list: async (params?: { page?: number; size?: number; channel_type?: string }) => {
    try {
      const { data } = await apiClient.get('/channels', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<ChannelStats> => {
    try {
      const { data } = await apiClient.get('/channels/stats');
      return data;
    } catch {
      return { total_channels: 0, active_channels: 0, total_orders_today: 0, total_revenue_today: 0 };
    }
  },
  create: async (channel: Partial<SalesChannel>) => {
    const { data } = await apiClient.post('/channels', channel);
    return data;
  },
  activate: async (id: string) => {
    const { data } = await apiClient.post(`/channels/${id}/activate`);
    return data;
  },
  deactivate: async (id: string) => {
    const { data } = await apiClient.post(`/channels/${id}/deactivate`);
    return data;
  },
};

const channelTypeColors: Record<string, string> = {
  D2C: 'bg-blue-100 text-blue-800',
  MARKETPLACE: 'bg-purple-100 text-purple-800',
  B2B: 'bg-green-100 text-green-800',
  DEALER: 'bg-orange-100 text-orange-800',
  OFFLINE: 'bg-gray-100 text-gray-800',
};

const marketplaces = [
  'Amazon', 'Flipkart', 'Myntra', 'Meesho', 'JioMart', 'TataCliq', 'Ajio', 'Nykaa'
];

// Separate component for action cell to avoid hooks in render function
function ChannelActionsCell({ channel, onEdit, onView }: {
  channel: SalesChannel;
  onEdit: (channel: SalesChannel) => void;
  onView: (channel: SalesChannel) => void;
}) {
  const queryClient = useQueryClient();

  const activateMutation = useMutation({
    mutationFn: () => channelsApi.activate(channel.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      toast.success('Channel activated');
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: () => channelsApi.deactivate(channel.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      toast.success('Channel deactivated');
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
        <DropdownMenuItem onClick={() => onView(channel)}>
          <Eye className="mr-2 h-4 w-4" />
          View Details
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onEdit(channel)}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {channel.is_active ? (
          <DropdownMenuItem
            onClick={() => deactivateMutation.mutate()}
            className="text-destructive focus:text-destructive"
          >
            <PowerOff className="mr-2 h-4 w-4" />
            Deactivate
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem onClick={() => activateMutation.mutate()}>
            <Power className="mr-2 h-4 w-4" />
            Activate
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Column definitions factory function - takes handlers as parameters
function getColumns(
  onEdit: (channel: SalesChannel) => void,
  onView: (channel: SalesChannel) => void
): ColumnDef<SalesChannel>[] {
  return [
    {
      accessorKey: 'name',
      header: 'Channel',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Network className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium">{row.original.name}</div>
            <div className="text-sm text-muted-foreground">{row.original.code}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'channel_type',
      header: 'Type',
      cell: ({ row }) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${channelTypeColors[row.original.channel_type]}`}>
          {row.original.channel_type}
        </span>
      ),
    },
    {
      accessorKey: 'marketplace_name',
      header: 'Marketplace',
      cell: ({ row }) => (
        <span className="text-sm">{row.original.marketplace_name || '-'}</span>
      ),
    },
    {
      accessorKey: 'commission_rate',
      header: 'Commission',
      cell: ({ row }) => (
        <span className="text-sm">
          {row.original.commission_rate ? `${row.original.commission_rate}%` : '-'}
        </span>
      ),
    },
    {
      accessorKey: 'sync',
      header: 'Auto Sync',
      cell: ({ row }) => (
        <div className="flex gap-2">
          <span className={`px-2 py-0.5 rounded text-xs ${
            row.original.auto_sync_orders ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'
          }`}>
            Orders
          </span>
          <span className={`px-2 py-0.5 rounded text-xs ${
            row.original.auto_sync_inventory ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'
          }`}>
            Inventory
          </span>
        </div>
      ),
    },
    {
      accessorKey: 'is_active',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.is_active ? 'ACTIVE' : 'INACTIVE'} />,
    },
    {
      accessorKey: 'created_at',
      header: 'Created',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">{formatDate(row.original.created_at)}</span>
      ),
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <ChannelActionsCell channel={row.original} onEdit={onEdit} onView={onView} />
      ),
    },
  ];
}

export default function ChannelsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [selectedChannel, setSelectedChannel] = useState<SalesChannel | null>(null);
  const [formData, setFormData] = useState<{
    id?: string;
    name: string;
    code: string;
    channel_type: 'D2C' | 'MARKETPLACE' | 'B2B' | 'DEALER' | 'OFFLINE';
    marketplace_name: string;
    commission_rate: string;
    auto_sync_orders: boolean;
    auto_sync_inventory: boolean;
    description: string;
  }>({
    name: '',
    code: '',
    channel_type: 'D2C',
    marketplace_name: '',
    commission_rate: '',
    auto_sync_orders: true,
    auto_sync_inventory: true,
    description: '',
  });

  const queryClient = useQueryClient();

  // Handler for viewing channel details
  const handleView = (channel: SalesChannel) => {
    setSelectedChannel(channel);
    setIsViewDialogOpen(true);
  };

  // Handler for editing channel
  const handleEdit = (channel: SalesChannel) => {
    setFormData({
      id: channel.id,
      name: channel.name,
      code: channel.code,
      channel_type: channel.channel_type,
      marketplace_name: channel.marketplace_name || '',
      commission_rate: channel.commission_rate?.toString() || '',
      auto_sync_orders: channel.auto_sync_orders,
      auto_sync_inventory: channel.auto_sync_inventory,
      description: channel.description || '',
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      name: '',
      code: '',
      channel_type: 'D2C',
      marketplace_name: '',
      commission_rate: '',
      auto_sync_orders: true,
      auto_sync_inventory: true,
      description: '',
    });
    setIsEditMode(false);
    setIsDialogOpen(false);
  };

  // Generate columns with handlers
  const columns = getColumns(handleEdit, handleView);

  const { data, isLoading } = useQuery({
    queryKey: ['channels', page, pageSize],
    queryFn: () => channelsApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['channel-stats'],
    queryFn: channelsApi.getStats,
  });

  const createMutation = useMutation({
    mutationFn: channelsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      toast.success('Channel created successfully');
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create channel');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<SalesChannel> }) =>
      apiClient.put(`/channels/${id}`, data).then((res) => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      toast.success('Channel updated successfully');
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update channel');
    },
  });

  const handleSubmit = () => {
    if (!formData.name.trim()) {
      toast.error('Channel name is required');
      return;
    }

    const channelData = {
      name: formData.name,
      code: formData.code || undefined,
      channel_type: formData.channel_type,
      seller_id: formData.marketplace_name || undefined,
      commission_percentage: parseFloat(formData.commission_rate) || undefined,
      auto_confirm_orders: formData.auto_sync_orders,
      auto_allocate_inventory: formData.auto_sync_inventory,
    };

    if (isEditMode && formData.id) {
      updateMutation.mutate({ id: formData.id, data: channelData });
    } else {
      createMutation.mutate(channelData);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sales Channels"
        description="Manage D2C, marketplace, and B2B sales channels"
        actions={
          <>
            <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
              <DialogTrigger asChild>
                <Button onClick={() => { resetForm(); setIsDialogOpen(true); }}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Channel
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle>{isEditMode ? 'Edit Sales Channel' : 'Create Sales Channel'}</DialogTitle>
                  <DialogDescription>
                    {isEditMode ? 'Update channel settings.' : 'Add a new sales channel for order and inventory management.'}
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="name">Channel Name *</Label>
                      <Input
                        id="name"
                        placeholder="e.g., Amazon India"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="code">Code</Label>
                      <Input
                        id="code"
                        placeholder="AMAZON_IN"
                        value={formData.code}
                        onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                        disabled={isEditMode}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="type">Channel Type</Label>
                      <Select
                        value={formData.channel_type}
                        onValueChange={(value: 'D2C' | 'MARKETPLACE' | 'B2B' | 'DEALER' | 'OFFLINE') =>
                          setFormData({ ...formData, channel_type: value })
                        }
                        disabled={isEditMode}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="D2C">D2C (Direct to Consumer)</SelectItem>
                          <SelectItem value="MARKETPLACE">Marketplace</SelectItem>
                          <SelectItem value="B2B">B2B / GTMT</SelectItem>
                          <SelectItem value="DEALER">Dealer Portal</SelectItem>
                          <SelectItem value="OFFLINE">Offline / Retail</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    {formData.channel_type === 'MARKETPLACE' && (
                      <div className="space-y-2">
                        <Label htmlFor="marketplace">Marketplace</Label>
                        <Select
                          value={formData.marketplace_name}
                          onValueChange={(value) => setFormData({ ...formData, marketplace_name: value })}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select marketplace" />
                          </SelectTrigger>
                          <SelectContent>
                            {marketplaces.map((mp) => (
                              <SelectItem key={mp} value={mp}>{mp}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="commission">Commission Rate (%)</Label>
                    <Input
                      id="commission"
                      type="number"
                      step="0.1"
                      placeholder="e.g., 15"
                      value={formData.commission_rate}
                      onChange={(e) => setFormData({ ...formData, commission_rate: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      placeholder="Channel description..."
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="sync_orders"
                        checked={formData.auto_sync_orders}
                        onCheckedChange={(checked) => setFormData({ ...formData, auto_sync_orders: checked })}
                      />
                      <Label htmlFor="sync_orders">Auto-sync Orders</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="sync_inventory"
                        checked={formData.auto_sync_inventory}
                        onCheckedChange={(checked) => setFormData({ ...formData, auto_sync_inventory: checked })}
                      />
                      <Label htmlFor="sync_inventory">Auto-sync Inventory</Label>
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={resetForm}>Cancel</Button>
                  <Button onClick={handleSubmit} disabled={createMutation.isPending || updateMutation.isPending}>
                    {(createMutation.isPending || updateMutation.isPending) ? 'Saving...' : isEditMode ? 'Update Channel' : 'Create Channel'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {/* View Details Dialog */}
            <Dialog open={isViewDialogOpen} onOpenChange={setIsViewDialogOpen}>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Channel Details</DialogTitle>
                </DialogHeader>
                {selectedChannel && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
                        <Network className="h-6 w-6 text-muted-foreground" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-lg">{selectedChannel.name}</h3>
                        <p className="text-sm text-muted-foreground">{selectedChannel.code}</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Type:</span>
                        <span className={`ml-2 px-2 py-0.5 rounded text-xs ${channelTypeColors[selectedChannel.channel_type]}`}>
                          {selectedChannel.channel_type}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Status:</span>
                        <StatusBadge status={selectedChannel.is_active ? 'ACTIVE' : 'INACTIVE'} />
                      </div>
                      {selectedChannel.marketplace_name && (
                        <div>
                          <span className="text-muted-foreground">Marketplace:</span>
                          <span className="ml-2 font-medium">{selectedChannel.marketplace_name}</span>
                        </div>
                      )}
                      {selectedChannel.commission_rate && (
                        <div>
                          <span className="text-muted-foreground">Commission:</span>
                          <span className="ml-2 font-medium">{selectedChannel.commission_rate}%</span>
                        </div>
                      )}
                      <div>
                        <span className="text-muted-foreground">Auto-sync Orders:</span>
                        <span className="ml-2 font-medium">{selectedChannel.auto_sync_orders ? 'Yes' : 'No'}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Auto-sync Inventory:</span>
                        <span className="ml-2 font-medium">{selectedChannel.auto_sync_inventory ? 'Yes' : 'No'}</span>
                      </div>
                    </div>
                    {selectedChannel.description && (
                      <div>
                        <span className="text-sm text-muted-foreground">Description:</span>
                        <p className="mt-1 text-sm">{selectedChannel.description}</p>
                      </div>
                    )}
                    <div className="text-xs text-muted-foreground">
                      Created: {formatDate(selectedChannel.created_at)}
                    </div>
                  </div>
                )}
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsViewDialogOpen(false)}>Close</Button>
                  <Button onClick={() => { setIsViewDialogOpen(false); if (selectedChannel) handleEdit(selectedChannel); }}>
                    <Pencil className="mr-2 h-4 w-4" />
                    Edit
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Channels</CardTitle>
            <Network className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_channels || 0}</div>
            <p className="text-xs text-muted-foreground">{stats?.active_channels || 0} active</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Channels</CardTitle>
            <Power className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.active_channels || 0}</div>
            <p className="text-xs text-muted-foreground">Currently active</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Orders Today</CardTitle>
            <ShoppingBag className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_orders_today || 0}</div>
            <p className="text-xs text-muted-foreground">Across all channels</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Revenue Today</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats?.total_revenue_today || 0)}</div>
            <p className="text-xs text-muted-foreground">All channels combined</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="name"
        searchPlaceholder="Search channels..."
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
