'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, ArrowRightLeft, ArrowUp, ArrowDown, GripVertical } from 'lucide-react';
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { warehousesApi } from '@/lib/api';

interface Warehouse {
  id: string;
  name: string;
  code?: string;
}

interface Zone {
  id: string;
  zone_code: string;
  zone_name: string;
  zone_type: string;
}

const zonesDropdownApi = {
  list: async (): Promise<Zone[]> => {
    try {
      const { data } = await apiClient.get('/wms/zones/dropdown');
      return data;
    } catch {
      return [];
    }
  },
};

interface PutawayRule {
  id: string;
  name: string;
  priority: number;
  rule_type: 'CATEGORY' | 'BRAND' | 'SKU' | 'VELOCITY' | 'SIZE' | 'WEIGHT' | 'CUSTOM';
  condition_field: string;
  condition_operator: 'EQUALS' | 'CONTAINS' | 'GREATER_THAN' | 'LESS_THAN' | 'IN' | 'NOT_IN';
  condition_value: string;
  target_zone_id: string;
  target_zone_name: string;
  target_bin_type?: string;
  warehouse_id: string;
  warehouse_name: string;
  is_active: boolean;
  items_processed: number;
}

interface RuleStats {
  total_rules: number;
  active_rules: number;
  items_processed_today: number;
  unmatched_items: number;
}

const putawayRulesApi = {
  list: async (params?: { page?: number; size?: number; warehouse_id?: string; rule_type?: string }) => {
    try {
      const { data } = await apiClient.get('/wms/putaway-rules', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<RuleStats> => {
    try {
      const { data } = await apiClient.get('/wms/putaway-rules/stats');
      return data;
    } catch {
      return { total_rules: 0, active_rules: 0, items_processed_today: 0, unmatched_items: 0 };
    }
  },
  create: async (rule: Partial<PutawayRule>) => {
    const { data } = await apiClient.post('/wms/putaway-rules', rule);
    return data;
  },
  update: async (id: string, rule: Partial<PutawayRule>) => {
    const { data } = await apiClient.put(`/wms/putaway-rules/${id}`, rule);
    return data;
  },
  updatePriority: async (id: string, priority: number) => {
    const { data } = await apiClient.put(`/wms/putaway-rules/${id}/priority`, { priority });
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/wms/putaway-rules/${id}`);
  },
};

const ruleTypeColors: Record<string, string> = {
  CATEGORY: 'bg-blue-100 text-blue-800',
  BRAND: 'bg-purple-100 text-purple-800',
  SKU: 'bg-green-100 text-green-800',
  VELOCITY: 'bg-yellow-100 text-yellow-800',
  SIZE: 'bg-orange-100 text-orange-800',
  WEIGHT: 'bg-red-100 text-red-800',
  CUSTOM: 'bg-gray-100 text-gray-800',
};

const ruleTypes = [
  { label: 'By Category', value: 'CATEGORY' },
  { label: 'By Brand', value: 'BRAND' },
  { label: 'By SKU', value: 'SKU' },
  { label: 'By Velocity (ABC)', value: 'VELOCITY' },
  { label: 'By Size', value: 'SIZE' },
  { label: 'By Weight', value: 'WEIGHT' },
  { label: 'Custom', value: 'CUSTOM' },
];

const operators = [
  { label: 'Equals', value: 'EQUALS' },
  { label: 'Contains', value: 'CONTAINS' },
  { label: 'Greater Than', value: 'GREATER_THAN' },
  { label: 'Less Than', value: 'LESS_THAN' },
  { label: 'In List', value: 'IN' },
  { label: 'Not In List', value: 'NOT_IN' },
];

// Separate component for actions cell to properly use hooks
function RuleActionsCell({ rule, onEdit, onDelete }: { rule: PutawayRule; onEdit: (rule: PutawayRule) => void; onDelete: (rule: PutawayRule) => void }) {
  const queryClient = useQueryClient();

  const moveUpMutation = useMutation({
    mutationFn: () => putawayRulesApi.updatePriority(rule.id, rule.priority - 1),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['putaway-rules'] });
      toast.success('Priority updated');
    },
    onError: () => toast.error('Failed to update priority'),
  });

  const moveDownMutation = useMutation({
    mutationFn: () => putawayRulesApi.updatePriority(rule.id, rule.priority + 1),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['putaway-rules'] });
      toast.success('Priority updated');
    },
    onError: () => toast.error('Failed to update priority'),
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
        <DropdownMenuItem onClick={() => moveUpMutation.mutate()} disabled={rule.priority <= 1}>
          <ArrowUp className="mr-2 h-4 w-4" />
          Move Up
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => moveDownMutation.mutate()}>
          <ArrowDown className="mr-2 h-4 w-4" />
          Move Down
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => onEdit(rule)}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit Rule
        </DropdownMenuItem>
        <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={() => onDelete(rule)}>
          <Trash2 className="mr-2 h-4 w-4" />
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

const createColumns = (onEdit: (rule: PutawayRule) => void, onDelete: (rule: PutawayRule) => void): ColumnDef<PutawayRule>[] => [
  {
    accessorKey: 'priority',
    header: 'Priority',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <GripVertical className="h-4 w-4 text-muted-foreground cursor-move" />
        <span className="font-mono font-bold text-lg">{row.original.priority}</span>
      </div>
    ),
  },
  {
    accessorKey: 'name',
    header: 'Rule Name',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <ArrowRightLeft className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-medium">{row.original.name}</div>
          <div className="text-sm text-muted-foreground">{row.original.warehouse_name}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'rule_type',
    header: 'Type',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${ruleTypeColors[row.original.rule_type]}`}>
        {row.original.rule_type}
      </span>
    ),
  },
  {
    accessorKey: 'condition',
    header: 'Condition',
    cell: ({ row }) => (
      <div className="text-sm font-mono bg-muted px-2 py-1 rounded">
        {row.original.condition_field ?? '-'} {row.original.condition_operator?.toLowerCase()?.replace('_', ' ') ?? '-'} &quot;{row.original.condition_value ?? ''}&quot;
      </div>
    ),
  },
  {
    accessorKey: 'target_zone_name',
    header: 'Target Zone',
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.target_zone_name}</div>
        {row.original.target_bin_type && (
          <div className="text-xs text-muted-foreground">Bin Type: {row.original.target_bin_type}</div>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'items_processed',
    header: 'Items Processed',
    cell: ({ row }) => (
      <span className="font-mono text-sm">{(row.original.items_processed ?? 0).toLocaleString()}</span>
    ),
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.is_active ? 'ACTIVE' : 'INACTIVE'} />,
  },
  {
    id: 'actions',
    cell: ({ row }) => <RuleActionsCell rule={row.original} onEdit={onEdit} onDelete={onDelete} />,
  },
];

export default function PutawayRulesPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingRule, setEditingRule] = useState<PutawayRule | null>(null);
  const [deleteRule, setDeleteRule] = useState<PutawayRule | null>(null);
  const [newRule, setNewRule] = useState<{
    name: string;
    warehouse_id: string;
    rule_type: 'CATEGORY' | 'BRAND' | 'SKU' | 'VELOCITY' | 'SIZE' | 'WEIGHT' | 'CUSTOM';
    condition_field: string;
    condition_operator: 'EQUALS' | 'CONTAINS' | 'GREATER_THAN' | 'LESS_THAN' | 'IN' | 'NOT_IN';
    condition_value: string;
    target_zone_id: string;
    target_bin_type: string;
    is_active: boolean;
  }>({
    name: '',
    warehouse_id: '',
    rule_type: 'CATEGORY',
    condition_field: 'category_name',
    condition_operator: 'EQUALS',
    condition_value: '',
    target_zone_id: '',
    target_bin_type: '',
    is_active: true,
  });

  const queryClient = useQueryClient();

  const handleEditClick = (rule: PutawayRule) => {
    setEditingRule(rule);
    setNewRule({
      name: rule.name,
      warehouse_id: rule.warehouse_id,
      rule_type: rule.rule_type,
      condition_field: rule.condition_field,
      condition_operator: rule.condition_operator,
      condition_value: rule.condition_value,
      target_zone_id: rule.target_zone_id,
      target_bin_type: rule.target_bin_type || '',
      is_active: rule.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleDeleteClick = (rule: PutawayRule) => {
    setDeleteRule(rule);
  };

  const columns = createColumns(handleEditClick, handleDeleteClick);

  const { data, isLoading } = useQuery({
    queryKey: ['putaway-rules', page, pageSize],
    queryFn: () => putawayRulesApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['putaway-rules-stats'],
    queryFn: putawayRulesApi.getStats,
  });

  // Fetch warehouses and zones for dropdowns
  const { data: warehouses = [] } = useQuery({
    queryKey: ['warehouses-dropdown'],
    queryFn: warehousesApi.dropdown,
  });

  const { data: zones = [] } = useQuery({
    queryKey: ['zones-dropdown'],
    queryFn: zonesDropdownApi.list,
  });

  const createMutation = useMutation({
    mutationFn: putawayRulesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['putaway-rules'] });
      toast.success('Putaway rule created successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create rule');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<PutawayRule> }) => putawayRulesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['putaway-rules'] });
      toast.success('Putaway rule updated successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update rule');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: putawayRulesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['putaway-rules'] });
      toast.success('Putaway rule deleted successfully');
      setDeleteRule(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete rule');
    },
  });

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setIsEditMode(false);
    setEditingRule(null);
    setNewRule({
      name: '',
      warehouse_id: '',
      rule_type: 'CATEGORY',
      condition_field: 'category_name',
      condition_operator: 'EQUALS',
      condition_value: '',
      target_zone_id: '',
      target_bin_type: '',
      is_active: true,
    });
  };

  const handleSubmit = () => {
    if (!newRule.name.trim()) {
      toast.error('Rule name is required');
      return;
    }
    if (isEditMode && editingRule) {
      updateMutation.mutate({ id: editingRule.id, data: newRule });
    } else {
      createMutation.mutate(newRule);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Putaway Rules"
        description="Configure automatic putaway logic for incoming inventory"
        actions={
          <Button onClick={() => { setIsEditMode(false); setIsDialogOpen(true); }}>
            <Plus className="mr-2 h-4 w-4" />
            Add Rule
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{isEditMode ? 'Edit Putaway Rule' : 'Create Putaway Rule'}</DialogTitle>
            <DialogDescription>
              Define conditions to automatically route items to specific zones.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
            <div className="space-y-2">
              <Label htmlFor="name">Rule Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Electronics to Zone A"
                value={newRule.name}
                onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="warehouse">Warehouse *</Label>
                <Select
                  value={newRule.warehouse_id || 'select'}
                  onValueChange={(value) => setNewRule({ ...newRule, warehouse_id: value === 'select' ? '' : value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select warehouse" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="select" disabled>Select warehouse</SelectItem>
                    {warehouses.map((wh: Warehouse) => (
                      <SelectItem key={wh.id} value={wh.id}>
                        {wh.name} {wh.code && `(${wh.code})`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="type">Rule Type</Label>
                <Select
                  value={newRule.rule_type}
                  onValueChange={(value: 'CATEGORY' | 'BRAND' | 'SKU' | 'VELOCITY' | 'SIZE' | 'WEIGHT' | 'CUSTOM') =>
                    setNewRule({ ...newRule, rule_type: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {ruleTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Condition</CardTitle>
                <CardDescription>When item matches this condition...</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-3 gap-2">
                <Select
                  value={newRule.condition_field}
                  onValueChange={(value) => setNewRule({ ...newRule, condition_field: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Field" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="category_name">Category</SelectItem>
                    <SelectItem value="brand_name">Brand</SelectItem>
                    <SelectItem value="sku">SKU</SelectItem>
                    <SelectItem value="velocity_class">Velocity Class</SelectItem>
                    <SelectItem value="weight">Weight (kg)</SelectItem>
                    <SelectItem value="volume">Volume (m³)</SelectItem>
                  </SelectContent>
                </Select>
                <Select
                  value={newRule.condition_operator}
                  onValueChange={(value: 'EQUALS' | 'CONTAINS' | 'GREATER_THAN' | 'LESS_THAN' | 'IN' | 'NOT_IN') =>
                    setNewRule({ ...newRule, condition_operator: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Operator" />
                  </SelectTrigger>
                  <SelectContent>
                    {operators.map((op) => (
                      <SelectItem key={op.value} value={op.value}>
                        {op.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  placeholder="Value"
                  value={newRule.condition_value}
                  onChange={(e) => setNewRule({ ...newRule, condition_value: e.target.value })}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Target Location</CardTitle>
                <CardDescription>...route to this zone</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-4">
                <Select
                  value={newRule.target_zone_id || 'select'}
                  onValueChange={(value) => setNewRule({ ...newRule, target_zone_id: value === 'select' ? '' : value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Target Zone" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="select" disabled>Select zone</SelectItem>
                    {zones.map((zone: Zone) => (
                      <SelectItem key={zone.id} value={zone.id}>
                        {zone.zone_name} ({zone.zone_code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select
                  value={newRule.target_bin_type || 'any'}
                  onValueChange={(value) => setNewRule({ ...newRule, target_bin_type: value === 'any' ? '' : value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Bin Type (optional)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Any Bin Type</SelectItem>
                    <SelectItem value="SHELF">Shelf</SelectItem>
                    <SelectItem value="PALLET">Pallet</SelectItem>
                    <SelectItem value="FLOOR">Floor</SelectItem>
                    <SelectItem value="RACK">Rack</SelectItem>
                    <SelectItem value="BULK">Bulk</SelectItem>
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>

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
            <Button variant="outline" onClick={handleDialogClose}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending || updateMutation.isPending}>
              {createMutation.isPending || updateMutation.isPending ? 'Saving...' : isEditMode ? 'Update Rule' : 'Create Rule'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteRule} onOpenChange={() => setDeleteRule(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Putaway Rule</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the rule &quot;{deleteRule?.name}&quot;? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteRule && deleteMutation.mutate(deleteRule.id)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Rules</CardTitle>
            <ArrowRightLeft className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_rules || 0}</div>
            <p className="text-xs text-muted-foreground">{stats?.active_rules || 0} active</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Items Today</CardTitle>
            <ArrowRightLeft className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.items_processed_today || 0}</div>
            <p className="text-xs text-muted-foreground">Auto-routed</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unmatched</CardTitle>
            <ArrowRightLeft className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.unmatched_items || 0}</div>
            <p className="text-xs text-muted-foreground">Manual routing needed</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Match Rate</CardTitle>
            <ArrowRightLeft className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.items_processed_today && stats.items_processed_today > 0
                ? ((stats.items_processed_today / (stats.items_processed_today + (stats.unmatched_items || 0))) * 100).toFixed(0)
                : 0}%
            </div>
            <p className="text-xs text-muted-foreground">Automation rate</p>
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
