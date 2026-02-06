'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, Grid3X3, Package, Eye, Lock, Unlock } from 'lucide-react';
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
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

interface Bin {
  id: string;
  zone_id: string;
  zone?: { id: string; zone_code: string; zone_name: string };
  warehouse_id?: string;
  warehouse?: { id: string; name: string };
  bin_code: string;
  aisle?: string;
  rack?: string;
  shelf?: string;
  position?: string;
  bin_type: 'SHELF' | 'PALLET' | 'FLOOR' | 'RACK' | 'BULK';
  max_weight_kg?: number;
  max_capacity?: number;
  current_items: number;
  current_weight_kg?: number;
  is_reserved: boolean;
  is_pickable: boolean;
  is_receivable: boolean;
  is_active: boolean;
}

interface Zone {
  id: string;
  zone_code: string;
  zone_name: string;
  zone_type: string;
}

interface BinStats {
  total_bins: number;
  available_bins: number;
  occupied_bins: number;
  reserved_bins: number;
}

const binsApi = {
  list: async (params?: { page?: number; size?: number; zone_id?: string; bin_type?: string }) => {
    try {
      const { data } = await apiClient.get('/wms/bins', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<BinStats> => {
    try {
      const { data } = await apiClient.get('/wms/bins/stats');
      return data;
    } catch {
      return { total_bins: 0, available_bins: 0, occupied_bins: 0, reserved_bins: 0 };
    }
  },
  create: async (bin: Partial<Bin>) => {
    const { data } = await apiClient.post('/wms/bins', bin);
    return data;
  },
  update: async (id: string, data: Partial<Bin>) => {
    const { data: result } = await apiClient.put(`/wms/bins/${id}`, data);
    return result;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/wms/bins/${id}`);
  },
};

const zonesApi = {
  dropdown: async (): Promise<Zone[]> => {
    try {
      const { data } = await apiClient.get('/wms/zones/dropdown');
      return data;
    } catch {
      return [];
    }
  },
};

// Separate component for actions cell to properly use hooks
function BinActionsCell({ bin, onView, onEdit, onDelete }: { bin: Bin; onView: (bin: Bin) => void; onEdit: (bin: Bin) => void; onDelete: (bin: Bin) => void }) {
  const queryClient = useQueryClient();

  const reserveMutation = useMutation({
    mutationFn: () => binsApi.update(bin.id, { is_reserved: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-bins'] });
      queryClient.invalidateQueries({ queryKey: ['wms-bins-stats'] });
      toast.success('Bin reserved');
    },
    onError: () => toast.error('Failed to reserve bin'),
  });

  const unreserveMutation = useMutation({
    mutationFn: () => binsApi.update(bin.id, { is_reserved: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-bins'] });
      queryClient.invalidateQueries({ queryKey: ['wms-bins-stats'] });
      toast.success('Bin unreserved');
    },
    onError: () => toast.error('Failed to unreserve bin'),
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
        <DropdownMenuItem onClick={() => onView(bin)}>
          <Eye className="mr-2 h-4 w-4" />
          View Contents
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onEdit(bin)}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {bin.is_reserved ? (
          <DropdownMenuItem onClick={() => unreserveMutation.mutate()}>
            <Unlock className="mr-2 h-4 w-4" />
            Unreserve Bin
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem onClick={() => reserveMutation.mutate()}>
            <Lock className="mr-2 h-4 w-4" />
            Reserve Bin
          </DropdownMenuItem>
        )}
        <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={() => onDelete(bin)}>
          <Trash2 className="mr-2 h-4 w-4" />
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

const binTypeColors: Record<string, string> = {
  SHELF: 'bg-blue-100 text-blue-800',
  PALLET: 'bg-purple-100 text-purple-800',
  FLOOR: 'bg-green-100 text-green-800',
  RACK: 'bg-orange-100 text-orange-800',
  BULK: 'bg-cyan-100 text-cyan-800',
};

const binTypes = [
  { label: 'Shelf', value: 'SHELF' },
  { label: 'Pallet', value: 'PALLET' },
  { label: 'Floor', value: 'FLOOR' },
  { label: 'Rack', value: 'RACK' },
  { label: 'Bulk', value: 'BULK' },
];

const createColumns = (onView: (bin: Bin) => void, onEdit: (bin: Bin) => void, onDelete: (bin: Bin) => void): ColumnDef<Bin>[] => [
  {
    accessorKey: 'bin_code',
    header: 'Bin Location',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Grid3X3 className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.bin_code}</div>
          <div className="text-xs text-muted-foreground">
            {row.original.aisle && `Aisle ${row.original.aisle}`}
            {row.original.rack && `, Rack ${row.original.rack}`}
            {row.original.shelf && `, Shelf ${row.original.shelf}`}
          </div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'zone',
    header: 'Zone / Warehouse',
    cell: ({ row }) => (
      <div>
        <div className="text-sm font-medium">{row.original.zone?.zone_name || '-'}</div>
        <div className="text-xs text-muted-foreground">{row.original.warehouse?.name || '-'}</div>
      </div>
    ),
  },
  {
    accessorKey: 'bin_type',
    header: 'Type',
    cell: ({ row }) => {
      const binType = row.original.bin_type || 'STANDARD';
      return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${binTypeColors[binType] || 'bg-gray-100 text-gray-800'}`}>
          {binType.replace('_', ' ')}
        </span>
      );
    },
  },
  {
    accessorKey: 'current_items',
    header: 'Items',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Package className="h-4 w-4 text-muted-foreground" />
        <span className="font-mono text-sm">{row.original.current_items}</span>
      </div>
    ),
  },
  {
    accessorKey: 'capacity',
    header: 'Capacity',
    cell: ({ row }) => {
      const currentItems = row.original.current_items ?? 0;
      const maxCapacity = row.original.max_capacity ?? 0;
      const utilization = maxCapacity > 0 ? (currentItems / maxCapacity) * 100 : 0;
      return (
        <div className="space-y-1">
          <div className="text-sm">
            {currentItems} / {maxCapacity || '∞'} items
          </div>
          {maxCapacity > 0 && (
            <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full ${utilization > 90 ? 'bg-red-500' : utilization > 70 ? 'bg-yellow-500' : 'bg-green-500'}`}
                style={{ width: `${Math.min(utilization, 100)}%` }}
              />
            </div>
          )}
        </div>
      );
    },
  },
  {
    accessorKey: 'is_reserved',
    header: 'Status',
    cell: ({ row }) => (
      <div className={`inline-flex items-center gap-1.5 text-xs font-medium ${
        row.original.is_reserved ? 'text-orange-600' : 'text-green-600'
      }`}>
        {row.original.is_reserved ? (
          <>
            <Lock className="h-3 w-3" />
            Reserved
          </>
        ) : (
          <>
            <Unlock className="h-3 w-3" />
            Available
          </>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.is_active ? 'ACTIVE' : 'INACTIVE'} />,
  },
  {
    id: 'actions',
    cell: ({ row }) => <BinActionsCell bin={row.original} onView={onView} onEdit={onEdit} onDelete={onDelete} />,
  },
];

export default function BinsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingBin, setEditingBin] = useState<Bin | null>(null);
  const [viewBin, setViewBin] = useState<Bin | null>(null);
  const [deleteBin, setDeleteBin] = useState<Bin | null>(null);
  const [zoneFilter, setZoneFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [newBin, setNewBin] = useState<{
    warehouse_id: string;
    zone_id: string;
    bin_code: string;
    aisle: string;
    rack: string;
    shelf: string;
    bin_type: 'SHELF' | 'PALLET' | 'FLOOR' | 'RACK' | 'BULK';
    max_capacity: string;
    max_weight_kg: string;
    is_active: boolean;
  }>({
    warehouse_id: '',
    zone_id: '',
    bin_code: '',
    aisle: '',
    rack: '',
    shelf: '',
    bin_type: 'SHELF',
    max_capacity: '',
    max_weight_kg: '',
    is_active: true,
  });

  const queryClient = useQueryClient();

  const handleViewClick = (bin: Bin) => {
    setViewBin(bin);
  };

  const handleEditClick = (bin: Bin) => {
    setEditingBin(bin);
    setNewBin({
      warehouse_id: bin.warehouse_id || '',
      zone_id: bin.zone_id || '',
      bin_code: bin.bin_code,
      aisle: bin.aisle || '',
      rack: bin.rack || '',
      shelf: bin.shelf || '',
      bin_type: bin.bin_type,
      max_capacity: bin.max_capacity?.toString() || '',
      max_weight_kg: bin.max_weight_kg?.toString() || '',
      is_active: bin.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleDeleteClick = (bin: Bin) => {
    setDeleteBin(bin);
  };

  const columns = createColumns(handleViewClick, handleEditClick, handleDeleteClick);

  // Fetch warehouses for dropdown
  const { data: warehouses = [] } = useQuery({
    queryKey: ['warehouses-dropdown'],
    queryFn: warehousesApi.dropdown,
  });

  // Fetch zones for dropdown
  const { data: zones = [] } = useQuery({
    queryKey: ['wms-zones-dropdown'],
    queryFn: zonesApi.dropdown,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['wms-bins', page, pageSize, zoneFilter, typeFilter],
    queryFn: () => binsApi.list({
      page: page + 1,
      size: pageSize,
      zone_id: zoneFilter !== 'all' ? zoneFilter : undefined,
      bin_type: typeFilter !== 'all' ? typeFilter : undefined,
    }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-bins-stats'],
    queryFn: binsApi.getStats,
  });

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setIsEditMode(false);
    setEditingBin(null);
    setNewBin({
      warehouse_id: '',
      zone_id: '',
      bin_code: '',
      aisle: '',
      rack: '',
      shelf: '',
      bin_type: 'SHELF',
      max_capacity: '',
      max_weight_kg: '',
      is_active: true,
    });
  };

  const createMutation = useMutation({
    mutationFn: binsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-bins'] });
      queryClient.invalidateQueries({ queryKey: ['wms-bins-stats'] });
      toast.success('Bin created successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create bin');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Bin> }) => binsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-bins'] });
      queryClient.invalidateQueries({ queryKey: ['wms-bins-stats'] });
      toast.success('Bin updated successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update bin');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: binsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-bins'] });
      queryClient.invalidateQueries({ queryKey: ['wms-bins-stats'] });
      toast.success('Bin deleted successfully');
      setDeleteBin(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete bin');
    },
  });

  const handleSubmit = () => {
    if (!newBin.bin_code.trim()) {
      toast.error('Bin code is required');
      return;
    }
    if (!newBin.warehouse_id) {
      toast.error('Warehouse is required');
      return;
    }

    const binData = {
      warehouse_id: newBin.warehouse_id,
      zone_id: newBin.zone_id || undefined,
      bin_code: newBin.bin_code,
      aisle: newBin.aisle || undefined,
      rack: newBin.rack || undefined,
      shelf: newBin.shelf || undefined,
      bin_type: newBin.bin_type,
      max_capacity: parseInt(newBin.max_capacity) || undefined,
      max_weight_kg: parseFloat(newBin.max_weight_kg) || undefined,
      is_active: newBin.is_active,
    } as Partial<Bin>;

    if (isEditMode && editingBin) {
      updateMutation.mutate({ id: editingBin.id, data: binData });
    } else {
      createMutation.mutate(binData);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Warehouse Bins"
        description="Manage bin locations for precise inventory placement"
        actions={
          <Button onClick={() => { setIsEditMode(false); setIsDialogOpen(true); }}>
            <Plus className="mr-2 h-4 w-4" />
            Add Bin
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{isEditMode ? 'Edit Bin' : 'Create New Bin'}</DialogTitle>
            <DialogDescription>
              {isEditMode ? 'Update bin details.' : 'Add a new bin location within a zone.'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="warehouse">Warehouse *</Label>
              <Select
                value={newBin.warehouse_id || 'select'}
                onValueChange={(value) => setNewBin({ ...newBin, warehouse_id: value === 'select' ? '' : value })}
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
                <Label htmlFor="zone">Zone</Label>
                <Select
                  value={newBin.zone_id || 'none'}
                  onValueChange={(value) => setNewBin({ ...newBin, zone_id: value === 'none' ? '' : value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select zone" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No Zone</SelectItem>
                    {zones.map((zone) => (
                      <SelectItem key={zone.id} value={zone.id}>
                        {zone.zone_name} ({zone.zone_code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="bin_code">Bin Code *</Label>
                <Input
                  id="bin_code"
                  placeholder="A-01-01-01"
                  value={newBin.bin_code}
                  onChange={(e) => setNewBin({ ...newBin, bin_code: e.target.value.toUpperCase() })}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="aisle">Aisle</Label>
                <Input
                  id="aisle"
                  placeholder="A"
                  value={newBin.aisle}
                  onChange={(e) => setNewBin({ ...newBin, aisle: e.target.value.toUpperCase() })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="rack">Rack</Label>
                <Input
                  id="rack"
                  placeholder="01"
                  value={newBin.rack}
                  onChange={(e) => setNewBin({ ...newBin, rack: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="shelf">Shelf</Label>
                <Input
                  id="shelf"
                  placeholder="01"
                  value={newBin.shelf}
                  onChange={(e) => setNewBin({ ...newBin, shelf: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">Bin Type</Label>
              <Select
                value={newBin.bin_type}
                onValueChange={(value: 'SHELF' | 'PALLET' | 'FLOOR' | 'RACK' | 'BULK') =>
                  setNewBin({ ...newBin, bin_type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {binTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="max_capacity">Max Capacity (items)</Label>
                <Input
                  id="max_capacity"
                  type="number"
                  placeholder="100"
                  value={newBin.max_capacity}
                  onChange={(e) => setNewBin({ ...newBin, max_capacity: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="max_weight_kg">Max Weight (kg)</Label>
                <Input
                  id="max_weight_kg"
                  type="number"
                  placeholder="100"
                  step="0.1"
                  value={newBin.max_weight_kg}
                  onChange={(e) => setNewBin({ ...newBin, max_weight_kg: e.target.value })}
                />
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="is_active"
                checked={newBin.is_active}
                onCheckedChange={(checked) => setNewBin({ ...newBin, is_active: checked })}
              />
              <Label htmlFor="is_active">Active</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleDialogClose}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending || updateMutation.isPending}>
              {createMutation.isPending || updateMutation.isPending ? 'Saving...' : isEditMode ? 'Update Bin' : 'Create Bin'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Bin Sheet */}
      <Sheet open={!!viewBin} onOpenChange={() => setViewBin(null)}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle className="font-mono">{viewBin?.bin_code}</SheetTitle>
            <SheetDescription>Bin Contents and Details</SheetDescription>
          </SheetHeader>
          <div className="mt-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-muted-foreground">Zone</div>
                <div className="font-medium">{viewBin?.zone?.zone_name || 'No Zone'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Warehouse</div>
                <div className="font-medium">{viewBin?.warehouse?.name || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Type</div>
                <div className="font-medium">{viewBin?.bin_type}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Location</div>
                <div className="font-medium">
                  {viewBin?.aisle && `A${viewBin.aisle}`}
                  {viewBin?.rack && `-R${viewBin.rack}`}
                  {viewBin?.shelf && `-S${viewBin.shelf}`}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Items</div>
                <div className="font-medium">{viewBin?.current_items || 0}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Max Capacity</div>
                <div className="font-medium">{viewBin?.max_capacity || 'Unlimited'}</div>
              </div>
            </div>
            <div className="flex gap-2">
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${viewBin?.is_reserved ? 'bg-orange-100 text-orange-800' : 'bg-green-100 text-green-800'}`}>
                {viewBin?.is_reserved ? 'Reserved' : 'Available'}
              </span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${viewBin?.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                {viewBin?.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
          </div>
        </SheetContent>
      </Sheet>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteBin} onOpenChange={() => setDeleteBin(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Bin</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the bin &quot;{deleteBin?.bin_code}&quot;? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteBin && deleteMutation.mutate(deleteBin.id)}
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
            <CardTitle className="text-sm font-medium">Total Bins</CardTitle>
            <Grid3X3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_bins || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Available</CardTitle>
            <Unlock className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.available_bins || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Occupied</CardTitle>
            <Package className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.occupied_bins || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Reserved</CardTitle>
            <Lock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.reserved_bins || 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={zoneFilter} onValueChange={setZoneFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by zone" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Zones</SelectItem>
            {zones.map((zone) => (
              <SelectItem key={zone.id} value={zone.id}>
                {zone.zone_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {binTypes.map((type) => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="bin_code"
        searchPlaceholder="Search bins..."
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
