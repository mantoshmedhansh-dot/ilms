'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, Box, Loader2, Layers } from 'lucide-react';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { binsApi, zonesApi, warehousesApi } from '@/lib/api';

interface Bin {
  id: string;
  name: string;
  code: string;
  zone_id: string;
  aisle?: string;
  rack?: string;
  level?: string;
  position?: string;
  capacity?: number;
  current_quantity?: number;
  is_active: boolean;
  zone?: { name: string; code: string; warehouse?: { name: string } };
  created_at: string;
}

interface Zone {
  id: string;
  name: string;
  code: string;
  warehouse_id: string;
  warehouse?: { name: string };
}

export default function BinsPage() {
  const searchParams = useSearchParams();
  const initialZoneId = searchParams.get('zone_id') || '';

  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [zoneFilter, setZoneFilter] = useState(initialZoneId);
  const [warehouseFilter, setWarehouseFilter] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isBulkDialogOpen, setIsBulkDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [binToDelete, setBinToDelete] = useState<Bin | null>(null);

  const [formData, setFormData] = useState({
    id: '',
    name: '',
    code: '',
    zone_id: initialZoneId,
    aisle: '',
    rack: '',
    level: '',
    position: '',
    capacity: '',
    is_active: true,
  });

  const [bulkFormData, setBulkFormData] = useState({
    zone_id: '',
    prefix: 'BIN',
    aisles: 2,
    racks_per_aisle: 4,
    levels_per_rack: 3,
    positions_per_level: 4,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['bins', page, pageSize, zoneFilter, warehouseFilter],
    queryFn: () => binsApi.list({
      page: page + 1,
      size: pageSize,
      zone_id: zoneFilter || undefined,
      warehouse_id: warehouseFilter || undefined,
    }),
  });

  const { data: warehouses } = useQuery({
    queryKey: ['warehouses-list'],
    queryFn: () => warehousesApi.list({ size: 100, is_active: true }),
  });

  const { data: zones } = useQuery({
    queryKey: ['zones-list', warehouseFilter],
    queryFn: () => zonesApi.list({ size: 100, warehouse_id: warehouseFilter || undefined }),
  });

  const createMutation = useMutation({
    mutationFn: binsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bins'] });
      toast.success('Bin created successfully');
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create bin');
    },
  });

  const bulkCreateMutation = useMutation({
    mutationFn: binsApi.bulkCreate,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['bins'] });
      toast.success(`${data.created_count || 'Multiple'} bins created successfully`);
      setIsBulkDialogOpen(false);
      setBulkFormData({
        zone_id: '',
        prefix: 'BIN',
        aisles: 2,
        racks_per_aisle: 4,
        levels_per_rack: 3,
        positions_per_level: 4,
      });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create bins');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof binsApi.update>[1] }) =>
      binsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bins'] });
      toast.success('Bin updated successfully');
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update bin');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: binsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bins'] });
      toast.success('Bin deleted successfully');
      setDeleteDialogOpen(false);
      setBinToDelete(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete bin');
    },
  });

  const resetForm = () => {
    setFormData({
      id: '',
      name: '',
      code: '',
      zone_id: initialZoneId,
      aisle: '',
      rack: '',
      level: '',
      position: '',
      capacity: '',
      is_active: true,
    });
    setIsEditMode(false);
    setIsDialogOpen(false);
  };

  const handleEdit = (bin: Bin) => {
    setFormData({
      id: bin.id,
      name: bin.name,
      code: bin.code,
      zone_id: bin.zone_id,
      aisle: bin.aisle || '',
      rack: bin.rack || '',
      level: bin.level || '',
      position: bin.position || '',
      capacity: bin.capacity?.toString() || '',
      is_active: bin.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleSubmit = () => {
    if (!formData.name.trim() || !formData.code.trim() || !formData.zone_id) {
      toast.error('Please fill all required fields');
      return;
    }

    if (isEditMode) {
      updateMutation.mutate({
        id: formData.id,
        data: {
          name: formData.name,
          code: formData.code.toUpperCase(),
          aisle: formData.aisle || undefined,
          rack: formData.rack || undefined,
          level: formData.level || undefined,
          position: formData.position || undefined,
          capacity: formData.capacity ? parseInt(formData.capacity) : undefined,
          is_active: formData.is_active,
        },
      });
    } else {
      createMutation.mutate({
        name: formData.name,
        code: formData.code.toUpperCase(),
        zone_id: formData.zone_id,
        aisle: formData.aisle || undefined,
        rack: formData.rack || undefined,
        level: formData.level || undefined,
        position: formData.position || undefined,
        capacity: formData.capacity ? parseInt(formData.capacity) : undefined,
        is_active: formData.is_active,
      });
    }
  };

  const handleBulkCreate = () => {
    if (!bulkFormData.zone_id) {
      toast.error('Please select a zone');
      return;
    }
    bulkCreateMutation.mutate(bulkFormData);
  };

  const columns: ColumnDef<Bin>[] = [
    {
      accessorKey: 'code',
      header: 'Bin',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Box className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium">{row.original.code}</div>
            <div className="text-sm text-muted-foreground">{row.original.name}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'zone',
      header: 'Zone / Warehouse',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.zone?.name || '-'}</div>
          <div className="text-sm text-muted-foreground">{row.original.zone?.warehouse?.name || '-'}</div>
        </div>
      ),
    },
    {
      accessorKey: 'location',
      header: 'Location',
      cell: ({ row }) => {
        const parts = [
          row.original.aisle && `A${row.original.aisle}`,
          row.original.rack && `R${row.original.rack}`,
          row.original.level && `L${row.original.level}`,
          row.original.position && `P${row.original.position}`,
        ].filter(Boolean);
        return parts.length > 0 ? parts.join('-') : '-';
      },
    },
    {
      accessorKey: 'capacity',
      header: 'Capacity',
      cell: ({ row }) => (
        <div>
          <div>{row.original.current_quantity ?? 0} / {row.original.capacity ?? '∞'}</div>
        </div>
      ),
    },
    {
      accessorKey: 'is_active',
      header: 'Status',
      cell: ({ row }) => (
        <StatusBadge status={row.original.is_active ? 'ACTIVE' : 'INACTIVE'} />
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
            <DropdownMenuItem onClick={() => handleEdit(row.original)}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() => {
                setBinToDelete(row.original);
                setDeleteDialogOpen(true);
              }}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Warehouse Bins"
        description="Manage bin locations for precise inventory storage"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setIsBulkDialogOpen(true)}>
              <Layers className="mr-2 h-4 w-4" />
              Bulk Create
            </Button>
            <Button onClick={() => setIsDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Bin
            </Button>
          </div>
        }
      />

      <Dialog open={isBulkDialogOpen} onOpenChange={setIsBulkDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Bulk Create Bins</DialogTitle>
            <DialogDescription>
              Generate multiple bins based on aisle-rack-level-position structure
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Zone *</Label>
              <Select
                value={bulkFormData.zone_id}
                onValueChange={(value) => setBulkFormData({ ...bulkFormData, zone_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select zone" />
                </SelectTrigger>
                <SelectContent>
                  {zones?.items?.map((zone: Zone) => (
                    <SelectItem key={zone.id} value={zone.id}>
                      {zone.name} ({zone.warehouse?.name})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Bin Prefix</Label>
              <Input
                value={bulkFormData.prefix}
                onChange={(e) => setBulkFormData({ ...bulkFormData, prefix: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Aisles</Label>
                <Input
                  type="number"
                  min={1}
                  value={bulkFormData.aisles}
                  onChange={(e) => setBulkFormData({ ...bulkFormData, aisles: parseInt(e.target.value) || 1 })}
                />
              </div>
              <div className="space-y-2">
                <Label>Racks per Aisle</Label>
                <Input
                  type="number"
                  min={1}
                  value={bulkFormData.racks_per_aisle}
                  onChange={(e) => setBulkFormData({ ...bulkFormData, racks_per_aisle: parseInt(e.target.value) || 1 })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Levels per Rack</Label>
                <Input
                  type="number"
                  min={1}
                  value={bulkFormData.levels_per_rack}
                  onChange={(e) => setBulkFormData({ ...bulkFormData, levels_per_rack: parseInt(e.target.value) || 1 })}
                />
              </div>
              <div className="space-y-2">
                <Label>Positions per Level</Label>
                <Input
                  type="number"
                  min={1}
                  value={bulkFormData.positions_per_level}
                  onChange={(e) => setBulkFormData({ ...bulkFormData, positions_per_level: parseInt(e.target.value) || 1 })}
                />
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              This will create {bulkFormData.aisles * bulkFormData.racks_per_aisle * bulkFormData.levels_per_rack * bulkFormData.positions_per_level} bins
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsBulkDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleBulkCreate} disabled={bulkCreateMutation.isPending}>
              {bulkCreateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Bins
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{isEditMode ? 'Edit Bin' : 'Create New Bin'}</DialogTitle>
            <DialogDescription>
              {isEditMode ? 'Update bin details' : 'Add a new storage bin'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Zone *</Label>
              <Select
                value={formData.zone_id}
                onValueChange={(value) => setFormData({ ...formData, zone_id: value })}
                disabled={isEditMode}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select zone" />
                </SelectTrigger>
                <SelectContent>
                  {zones?.items?.map((zone: Zone) => (
                    <SelectItem key={zone.id} value={zone.id}>
                      {zone.name} ({zone.warehouse?.name})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Name *</Label>
                <Input
                  placeholder="Bin 1"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Code *</Label>
                <Input
                  placeholder="BIN001"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                />
              </div>
            </div>
            <div className="grid grid-cols-4 gap-2">
              <div className="space-y-2">
                <Label>Aisle</Label>
                <Input
                  placeholder="A"
                  value={formData.aisle}
                  onChange={(e) => setFormData({ ...formData, aisle: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Rack</Label>
                <Input
                  placeholder="1"
                  value={formData.rack}
                  onChange={(e) => setFormData({ ...formData, rack: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Level</Label>
                <Input
                  placeholder="2"
                  value={formData.level}
                  onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Position</Label>
                <Input
                  placeholder="3"
                  value={formData.position}
                  onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Capacity</Label>
              <Input
                type="number"
                placeholder="Leave empty for unlimited"
                value={formData.capacity}
                onChange={(e) => setFormData({ ...formData, capacity: e.target.value })}
              />
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
              />
              <Label>Active</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={resetForm}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending || updateMutation.isPending}>
              {(createMutation.isPending || updateMutation.isPending) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEditMode ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Select value={warehouseFilter || 'all'} onValueChange={(value) => { setWarehouseFilter(value === 'all' ? '' : value); setZoneFilter(''); }}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="All Warehouses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Warehouses</SelectItem>
            {warehouses?.items?.map((wh: { id: string; name: string }) => (
              <SelectItem key={wh.id} value={wh.id}>{wh.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={zoneFilter || 'all'} onValueChange={(v) => setZoneFilter(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="All Zones" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Zones</SelectItem>
            {zones?.items?.map((zone: Zone) => (
              <SelectItem key={zone.id} value={zone.id}>{zone.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="code"
        searchPlaceholder="Search bins..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Bin</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete bin "{binToDelete?.code}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => binToDelete && deleteMutation.mutate(binToDelete.id)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
