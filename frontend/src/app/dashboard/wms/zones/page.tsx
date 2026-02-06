'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, Layers, Warehouse, Package } from 'lucide-react';
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { warehousesApi } from '@/lib/api';

interface Zone {
  id: string;
  warehouse_id: string;
  warehouse_name: string;
  code: string;
  name: string;
  zone_type: 'STORAGE' | 'PICKING' | 'PACKING' | 'RECEIVING' | 'SHIPPING' | 'QUARANTINE' | 'RETURNS';
  temperature_controlled: boolean;
  max_capacity: number;
  current_occupancy: number;
  bins_count: number;
  is_active: boolean;
}

interface ZoneStats {
  total_zones: number;
  active_zones: number;
  total_capacity: number;
  current_occupancy: number;
  utilization_percent: number;
}

interface ZoneCreateInput {
  zone_name: string;
  zone_code?: string;
  warehouse_id: string;
  zone_type: string;
  max_capacity?: number;
  temperature_controlled?: boolean;
  is_active?: boolean;
}

const zonesApi = {
  list: async (params?: { page?: number; size?: number; warehouse_id?: string; zone_type?: string }) => {
    try {
      const { data } = await apiClient.get('/wms/zones', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<ZoneStats> => {
    try {
      const { data } = await apiClient.get('/wms/zones/stats');
      return data;
    } catch {
      return { total_zones: 0, active_zones: 0, total_capacity: 0, current_occupancy: 0, utilization_percent: 0 };
    }
  },
  create: async (zone: ZoneCreateInput) => {
    const { data } = await apiClient.post('/wms/zones', zone);
    return data;
  },
  update: async (id: string, zone: Partial<Zone>) => {
    const { data } = await apiClient.put(`/wms/zones/${id}`, zone);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/wms/zones/${id}`);
  },
};

const zoneTypeColors: Record<string, string> = {
  STORAGE: 'bg-blue-100 text-blue-800',
  PICKING: 'bg-green-100 text-green-800',
  PACKING: 'bg-yellow-100 text-yellow-800',
  RECEIVING: 'bg-purple-100 text-purple-800',
  SHIPPING: 'bg-orange-100 text-orange-800',
  QUARANTINE: 'bg-red-100 text-red-800',
  RETURNS: 'bg-gray-100 text-gray-800',
};

const zoneTypes = [
  { label: 'Storage', value: 'STORAGE' },
  { label: 'Picking', value: 'PICKING' },
  { label: 'Packing', value: 'PACKING' },
  { label: 'Receiving', value: 'RECEIVING' },
  { label: 'Shipping', value: 'SHIPPING' },
  { label: 'Quarantine', value: 'QUARANTINE' },
  { label: 'Returns', value: 'RETURNS' },
];

// Separate component for actions cell
function ZoneActionsCell({ zone, onEdit, onDelete }: { zone: Zone; onEdit: (zone: Zone) => void; onDelete: (zone: Zone) => void }) {
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
        <DropdownMenuItem onClick={() => onEdit(zone)}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit
        </DropdownMenuItem>
        <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={() => onDelete(zone)}>
          <Trash2 className="mr-2 h-4 w-4" />
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

const createColumns = (onEdit: (zone: Zone) => void, onDelete: (zone: Zone) => void): ColumnDef<Zone>[] => [
  {
    accessorKey: 'name',
    header: 'Zone',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Layers className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-medium">{row.original.name}</div>
          <div className="text-sm text-muted-foreground">{row.original.code}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'warehouse_name',
    header: 'Warehouse',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Warehouse className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">{row.original.warehouse_name}</span>
      </div>
    ),
  },
  {
    accessorKey: 'zone_type',
    header: 'Type',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${zoneTypeColors[row.original.zone_type]}`}>
        {row.original.zone_type}
      </span>
    ),
  },
  {
    accessorKey: 'bins_count',
    header: 'Bins',
    cell: ({ row }) => (
      <span className="font-mono text-sm">{row.original.bins_count}</span>
    ),
  },
  {
    accessorKey: 'utilization',
    header: 'Utilization',
    cell: ({ row }) => {
      const utilization = row.original.max_capacity > 0
        ? (row.original.current_occupancy / row.original.max_capacity) * 100
        : 0;
      const color = utilization > 90 ? 'text-red-600' : utilization > 70 ? 'text-yellow-600' : 'text-green-600';
      return (
        <div className="space-y-1">
          <div className={`text-sm font-medium ${color}`}>{utilization.toFixed(0)}%</div>
          <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full ${utilization > 90 ? 'bg-red-500' : utilization > 70 ? 'bg-yellow-500' : 'bg-green-500'}`}
              style={{ width: `${Math.min(utilization, 100)}%` }}
            />
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'temperature_controlled',
    header: 'Temp Control',
    cell: ({ row }) => (
      <span className={`text-xs px-2 py-1 rounded ${
        row.original.temperature_controlled ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-500'
      }`}>
        {row.original.temperature_controlled ? 'Yes' : 'No'}
      </span>
    ),
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.is_active ? 'ACTIVE' : 'INACTIVE'} />,
  },
  {
    id: 'actions',
    cell: ({ row }) => <ZoneActionsCell zone={row.original} onEdit={onEdit} onDelete={onDelete} />,
  },
];

export default function ZonesPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingZone, setEditingZone] = useState<Zone | null>(null);
  const [deleteZone, setDeleteZone] = useState<Zone | null>(null);
  const [newZone, setNewZone] = useState<{
    name: string;
    code: string;
    warehouse_id: string;
    zone_type: 'STORAGE' | 'PICKING' | 'PACKING' | 'RECEIVING' | 'SHIPPING' | 'QUARANTINE' | 'RETURNS';
    max_capacity: string;
    temperature_controlled: boolean;
    is_active: boolean;
  }>({
    name: '',
    code: '',
    warehouse_id: '',
    zone_type: 'STORAGE',
    max_capacity: '',
    temperature_controlled: false,
    is_active: true,
  });

  const queryClient = useQueryClient();

  const handleEditClick = (zone: Zone) => {
    setEditingZone(zone);
    setNewZone({
      name: zone.name,
      code: zone.code,
      warehouse_id: zone.warehouse_id,
      zone_type: zone.zone_type,
      max_capacity: zone.max_capacity?.toString() || '',
      temperature_controlled: zone.temperature_controlled,
      is_active: zone.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleDeleteClick = (zone: Zone) => {
    setDeleteZone(zone);
  };

  const columns = createColumns(handleEditClick, handleDeleteClick);

  const { data, isLoading } = useQuery({
    queryKey: ['wms-zones', page, pageSize],
    queryFn: () => zonesApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-zones-stats'],
    queryFn: zonesApi.getStats,
  });

  // Fetch warehouses for dropdown
  const { data: warehouses = [] } = useQuery({
    queryKey: ['warehouses-dropdown'],
    queryFn: warehousesApi.dropdown,
  });

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setIsEditMode(false);
    setEditingZone(null);
    setNewZone({
      name: '',
      code: '',
      warehouse_id: '',
      zone_type: 'STORAGE',
      max_capacity: '',
      temperature_controlled: false,
      is_active: true,
    });
  };

  const createMutation = useMutation({
    mutationFn: zonesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-zones'] });
      queryClient.invalidateQueries({ queryKey: ['wms-zones-stats'] });
      toast.success('Zone created successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create zone');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Zone> }) => zonesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-zones'] });
      queryClient.invalidateQueries({ queryKey: ['wms-zones-stats'] });
      toast.success('Zone updated successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update zone');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: zonesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-zones'] });
      queryClient.invalidateQueries({ queryKey: ['wms-zones-stats'] });
      toast.success('Zone deleted successfully');
      setDeleteZone(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete zone');
    },
  });

  const handleSubmit = () => {
    if (!newZone.name.trim()) {
      toast.error('Zone name is required');
      return;
    }
    if (!newZone.warehouse_id) {
      toast.error('Warehouse is required');
      return;
    }

    const zoneData = {
      zone_name: newZone.name,
      zone_code: newZone.code || undefined,
      warehouse_id: newZone.warehouse_id,
      zone_type: newZone.zone_type,
      max_capacity: parseInt(newZone.max_capacity) || 0,
      temperature_controlled: newZone.temperature_controlled,
      is_active: newZone.is_active,
    };

    if (isEditMode && editingZone) {
      updateMutation.mutate({ id: editingZone.id, data: zoneData });
    } else {
      createMutation.mutate(zoneData);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Warehouse Zones"
        description="Manage warehouse zones for organized inventory storage"
        actions={
          <Button onClick={() => { setIsEditMode(false); setIsDialogOpen(true); }}>
            <Plus className="mr-2 h-4 w-4" />
            Add Zone
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{isEditMode ? 'Edit Zone' : 'Create New Zone'}</DialogTitle>
            <DialogDescription>
              {isEditMode ? 'Update zone details.' : 'Add a new zone to organize inventory within a warehouse.'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Zone Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., Zone A"
                  value={newZone.name}
                  onChange={(e) => setNewZone({ ...newZone, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="code">Code *</Label>
                <Input
                  id="code"
                  placeholder="ZONE-A"
                  value={newZone.code}
                  onChange={(e) => setNewZone({ ...newZone, code: e.target.value.toUpperCase() })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="warehouse">Warehouse *</Label>
              <Select
                value={newZone.warehouse_id || 'select'}
                onValueChange={(value) => setNewZone({ ...newZone, warehouse_id: value === 'select' ? '' : value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select warehouse" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="select" disabled>Select warehouse</SelectItem>
                  {warehouses.map((wh: { id: string; name: string; code?: string }) => (
                    <SelectItem key={wh.id} value={wh.id}>
                      {wh.name} {wh.code && `(${wh.code})`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="type">Zone Type</Label>
                <Select
                  value={newZone.zone_type}
                  onValueChange={(value: 'STORAGE' | 'PICKING' | 'PACKING' | 'RECEIVING' | 'SHIPPING' | 'QUARANTINE' | 'RETURNS') =>
                    setNewZone({ ...newZone, zone_type: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {zoneTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="capacity">Max Capacity</Label>
                <Input
                  id="capacity"
                  type="number"
                  placeholder="Units"
                  value={newZone.max_capacity}
                  onChange={(e) => setNewZone({ ...newZone, max_capacity: e.target.value })}
                />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Switch
                  id="temp_controlled"
                  checked={newZone.temperature_controlled}
                  onCheckedChange={(checked) => setNewZone({ ...newZone, temperature_controlled: checked })}
                />
                <Label htmlFor="temp_controlled">Temperature Controlled</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="is_active"
                  checked={newZone.is_active}
                  onCheckedChange={(checked) => setNewZone({ ...newZone, is_active: checked })}
                />
                <Label htmlFor="is_active">Active</Label>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleDialogClose}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending || updateMutation.isPending}>
              {createMutation.isPending || updateMutation.isPending ? 'Saving...' : isEditMode ? 'Update Zone' : 'Create Zone'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteZone} onOpenChange={() => setDeleteZone(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Zone</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the zone &quot;{deleteZone?.name}&quot;? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteZone && deleteMutation.mutate(deleteZone.id)}
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
            <CardTitle className="text-sm font-medium">Total Zones</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_zones || 0}</div>
            <p className="text-xs text-muted-foreground">{stats?.active_zones || 0} active</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Capacity</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(stats?.total_capacity || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Units</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current Occupancy</CardTitle>
            <Package className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{(stats?.current_occupancy || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Units stored</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Utilization</CardTitle>
            <Layers className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{(stats?.utilization_percent || 0).toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">Average across zones</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="name"
        searchPlaceholder="Search zones..."
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
