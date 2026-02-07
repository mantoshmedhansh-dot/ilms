'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, Network, ArrowUp, ArrowDown, GripVertical, Zap, MapPin, DollarSign, Clock, Star } from 'lucide-react';
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
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface AllocationRule {
  id: string;
  name: string;
  priority: number;
  rule_type: 'NEAREST' | 'COST_OPTIMIZED' | 'PRIORITY' | 'ROUND_ROBIN' | 'FIFO' | 'CHANNEL_SPECIFIC' | 'CUSTOM';
  channel_id?: string;
  channel_name?: string;
  criteria: {
    field: string;
    operator: string;
    value: string;
  }[];
  target_warehouse_ids?: string[];
  target_warehouse_names?: string[];
  fallback_rule_id?: string;
  max_distance_km?: number;
  consider_inventory: boolean;
  consider_cost: boolean;
  consider_sla: boolean;
  is_active: boolean;
  orders_allocated: number;
}

interface RuleStats {
  total_rules: number;
  active_rules: number;
  orders_allocated_today: number;
  avg_allocation_time_ms: number;
}

const allocationRulesApi = {
  list: async (params?: { page?: number; size?: number; rule_type?: string }) => {
    try {
      const { data } = await apiClient.get('/allocation-rules', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<RuleStats> => {
    try {
      const { data } = await apiClient.get('/allocation-rules/stats');
      return data;
    } catch {
      return { total_rules: 0, active_rules: 0, orders_allocated_today: 0, avg_allocation_time_ms: 0 };
    }
  },
  create: async (rule: Partial<AllocationRule>) => {
    const { data } = await apiClient.post('/allocation-rules', rule);
    return data;
  },
  updatePriority: async (id: string, priority: number) => {
    const { data } = await apiClient.put(`/allocation-rules/${id}/priority`, { priority });
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/allocation-rules/${id}`);
  },
};

const ruleTypeConfig: Record<string, { color: string; icon: React.ComponentType<{ className?: string }>; label: string }> = {
  NEAREST: { color: 'bg-blue-100 text-blue-800', icon: MapPin, label: 'Nearest Warehouse' },
  COST_OPTIMIZED: { color: 'bg-green-100 text-green-800', icon: DollarSign, label: 'Cost Optimized' },
  PRIORITY: { color: 'bg-purple-100 text-purple-800', icon: Star, label: 'Priority Based' },
  ROUND_ROBIN: { color: 'bg-yellow-100 text-yellow-800', icon: Network, label: 'Round Robin' },
  FIFO: { color: 'bg-orange-100 text-orange-800', icon: Clock, label: 'FIFO' },
  CHANNEL_SPECIFIC: { color: 'bg-pink-100 text-pink-800', icon: Network, label: 'Channel Specific' },
  CUSTOM: { color: 'bg-gray-100 text-gray-800', icon: Zap, label: 'Custom' },
};

const columns: ColumnDef<AllocationRule>[] = [
  {
    accessorKey: 'priority',
    header: 'Priority',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <GripVertical className="h-4 w-4 text-muted-foreground cursor-move" />
        <span className="font-mono font-bold text-lg w-8 text-center">{row.original.priority}</span>
      </div>
    ),
  },
  {
    accessorKey: 'name',
    header: 'Rule',
    cell: ({ row }) => {
      const config = ruleTypeConfig[row.original.rule_type] || ruleTypeConfig.CUSTOM;
      const Icon = config.icon;
      return (
        <div className="flex items-center gap-3">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${config.color}`}>
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <div className="font-medium">{row.original.name}</div>
            {row.original.channel_name && (
              <div className="text-sm text-muted-foreground">Channel: {row.original.channel_name}</div>
            )}
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'rule_type',
    header: 'Type',
    cell: ({ row }) => {
      const config = ruleTypeConfig[row.original.rule_type] || ruleTypeConfig.CUSTOM;
      return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
          {config.label}
        </span>
      );
    },
  },
  {
    accessorKey: 'considerations',
    header: 'Considers',
    cell: ({ row }) => (
      <div className="flex gap-2">
        {row.original.consider_inventory && (
          <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700">Inventory</span>
        )}
        {row.original.consider_cost && (
          <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">Cost</span>
        )}
        {row.original.consider_sla && (
          <span className="text-xs px-2 py-0.5 rounded bg-orange-100 text-orange-700">SLA</span>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'target_warehouse_names',
    header: 'Target Warehouses',
    cell: ({ row }) => (
      <div className="text-sm">
        {row.original.target_warehouse_names?.length
          ? row.original.target_warehouse_names.slice(0, 2).join(', ') +
            (row.original.target_warehouse_names.length > 2 ? ` +${row.original.target_warehouse_names.length - 2}` : '')
          : 'All Warehouses'}
      </div>
    ),
  },
  {
    accessorKey: 'orders_allocated',
    header: 'Orders',
    cell: ({ row }) => (
      <span className="font-mono text-sm">{(row.original.orders_allocated ?? 0).toLocaleString()}</span>
    ),
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.is_active ? 'ACTIVE' : 'INACTIVE'} />,
  },
  {
    id: 'actions',
    cell: ({ row }) => {
      const queryClient = useQueryClient();

      const moveUpMutation = useMutation({
        mutationFn: () => allocationRulesApi.updatePriority(row.original.id, row.original.priority - 1),
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ['allocation-rules'] });
          toast.success('Priority updated');
        },
      });

      const moveDownMutation = useMutation({
        mutationFn: () => allocationRulesApi.updatePriority(row.original.id, row.original.priority + 1),
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ['allocation-rules'] });
          toast.success('Priority updated');
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
            <DropdownMenuItem onClick={() => moveUpMutation.mutate()}>
              <ArrowUp className="mr-2 h-4 w-4" />
              Move Up
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => moveDownMutation.mutate()}>
              <ArrowDown className="mr-2 h-4 w-4" />
              Move Down
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Pencil className="mr-2 h-4 w-4" />
              Edit Rule
            </DropdownMenuItem>
            <DropdownMenuItem className="text-destructive focus:text-destructive">
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
  },
];

export default function AllocationRulesPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newRule, setNewRule] = useState<{
    name: string;
    rule_type: 'NEAREST' | 'COST_OPTIMIZED' | 'PRIORITY' | 'ROUND_ROBIN' | 'FIFO' | 'CHANNEL_SPECIFIC' | 'CUSTOM';
    channel_id: string;
    max_distance_km: string;
    consider_inventory: boolean;
    consider_cost: boolean;
    consider_sla: boolean;
    description: string;
    is_active: boolean;
  }>({
    name: '',
    rule_type: 'NEAREST',
    channel_id: '',
    max_distance_km: '',
    consider_inventory: true,
    consider_cost: true,
    consider_sla: true,
    description: '',
    is_active: true,
  });

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['allocation-rules', page, pageSize],
    queryFn: () => allocationRulesApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['allocation-rules-stats'],
    queryFn: allocationRulesApi.getStats,
  });

  const createMutation = useMutation({
    mutationFn: allocationRulesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['allocation-rules'] });
      toast.success('Allocation rule created successfully');
      setIsDialogOpen(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create rule');
    },
  });

  const handleCreate = () => {
    if (!newRule.name.trim()) {
      toast.error('Rule name is required');
      return;
    }
    createMutation.mutate({
      ...newRule,
      max_distance_km: parseFloat(newRule.max_distance_km) || undefined,
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Allocation Rules"
        description="Configure warehouse and courier allocation logic for orders"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Rule
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Allocation Rule</DialogTitle>
            <DialogDescription>
              Define how orders should be allocated to warehouses and couriers.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
            <div className="space-y-2">
              <Label htmlFor="name">Rule Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Amazon Orders - Mumbai Warehouse"
                value={newRule.name}
                onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="type">Rule Type</Label>
                <Select
                  value={newRule.rule_type}
                  onValueChange={(value: 'NEAREST' | 'COST_OPTIMIZED' | 'PRIORITY' | 'ROUND_ROBIN' | 'FIFO' | 'CHANNEL_SPECIFIC' | 'CUSTOM') =>
                    setNewRule({ ...newRule, rule_type: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NEAREST">Nearest Warehouse</SelectItem>
                    <SelectItem value="COST_OPTIMIZED">Cost Optimized</SelectItem>
                    <SelectItem value="PRIORITY">Priority Based</SelectItem>
                    <SelectItem value="ROUND_ROBIN">Round Robin</SelectItem>
                    <SelectItem value="FIFO">FIFO</SelectItem>
                    <SelectItem value="CHANNEL_SPECIFIC">Channel Specific</SelectItem>
                    <SelectItem value="CUSTOM">Custom</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="channel">Channel (Optional)</Label>
                <Select
                  value={newRule.channel_id}
                  onValueChange={(value) => setNewRule({ ...newRule, channel_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All Channels" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Channels</SelectItem>
                    <SelectItem value="d2c">D2C Website</SelectItem>
                    <SelectItem value="amazon">Amazon</SelectItem>
                    <SelectItem value="flipkart">Flipkart</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="max_distance">Max Distance (km)</Label>
              <Input
                id="max_distance"
                type="number"
                placeholder="e.g., 500"
                value={newRule.max_distance_km}
                onChange={(e) => setNewRule({ ...newRule, max_distance_km: e.target.value })}
              />
            </div>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Considerations</CardTitle>
                <CardDescription>What factors to consider during allocation</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="consider_inventory">Inventory Availability</Label>
                  <Switch
                    id="consider_inventory"
                    checked={newRule.consider_inventory}
                    onCheckedChange={(checked) => setNewRule({ ...newRule, consider_inventory: checked })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="consider_cost">Shipping Cost</Label>
                  <Switch
                    id="consider_cost"
                    checked={newRule.consider_cost}
                    onCheckedChange={(checked) => setNewRule({ ...newRule, consider_cost: checked })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="consider_sla">SLA Compliance</Label>
                  <Switch
                    id="consider_sla"
                    checked={newRule.consider_sla}
                    onCheckedChange={(checked) => setNewRule({ ...newRule, consider_sla: checked })}
                  />
                </div>
              </CardContent>
            </Card>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe when this rule should apply..."
                value={newRule.description}
                onChange={(e) => setNewRule({ ...newRule, description: e.target.value })}
              />
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="is_active"
                checked={newRule.is_active}
                onCheckedChange={(checked) => setNewRule({ ...newRule, is_active: checked })}
              />
              <Label htmlFor="is_active">Active</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Rule'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Rules</CardTitle>
            <Network className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_rules || 0}</div>
            <p className="text-xs text-muted-foreground">{stats?.active_rules || 0} active</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Orders Today</CardTitle>
            <Zap className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.orders_allocated_today || 0}</div>
            <p className="text-xs text-muted-foreground">Auto-allocated</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Allocation Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.avg_allocation_time_ms || 0}ms</div>
            <p className="text-xs text-muted-foreground">Per order</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <Star className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">99.2%</div>
            <p className="text-xs text-muted-foreground">Allocation success</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="name"
        searchPlaceholder="Search rules..."
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
