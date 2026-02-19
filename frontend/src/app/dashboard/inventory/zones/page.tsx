'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, Grid3X3, Loader2 } from 'lucide-react';
import Link from 'next/link';
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
import { Textarea } from '@/components/ui/textarea';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { zonesApi, warehousesApi } from '@/lib/api';

interface Zone {
  id: string;
  name: string;
  code: string;
  warehouse_id: string;
  zone_type: string;
  description?: string;
  is_active: boolean;
  warehouse?: { name: string; code: string };
  bin_count?: number;
  created_at: string;
}

const zoneTypes = [
  { label: 'Receiving', value: 'RECEIVING' },
  { label: 'Storage', value: 'STORAGE' },
  { label: 'Picking', value: 'PICKING' },
  { label: 'Packing', value: 'PACKING' },
  { label: 'Shipping', value: 'SHIPPING' },
  { label: 'Returns', value: 'RETURNS' },
  { label: 'Quarantine', value: 'QUARANTINE' },
];

export default function ZonesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [zoneToDelete, setZoneToDelete] = useState<Zone | null>(null);
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    code: '',
    warehouse_id: '',
    zone_type: 'STORAGE',
    description: '',
    is_active: true,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['zones', page, pageSize],
    queryFn: () => zonesApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: warehouses } = useQuery({
    queryKey: ['warehouses-list'],
    queryFn: () => warehousesApi.list({ size: 100, is_active: true }),
  });

  const createMutation = useMutation({
    mutationFn: zonesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
      toast.success('Zone created successfully');
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create zone');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof zonesApi.update>[1] }) =>
      zonesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
      toast.success('Zone updated successfully');
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update zone');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: zonesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
      toast.success('Zone deleted successfully');
      setDeleteDialogOpen(false);
      setZoneToDelete(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete zone');
    },
  });

  const resetForm = () => {
    setFormData({
      id: '',
      name: '',
      code: '',
      warehouse_id: '',
      zone_type: 'STORAGE',
      description: '',
      is_active: true,
    });
    setIsEditMode(false);
    setIsDialogOpen(false);
  };

  const handleEdit = (zone: Zone) => {
    setFormData({
      id: zone.id,
      name: zone.name,
      code: zone.code,
      warehouse_id: zone.warehouse_id,
      zone_type: zone.zone_type,
      description: zone.description || '',
      is_active: zone.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleSubmit = () => {
    if (!formData.name.trim() || !formData.code.trim() || !formData.warehouse_id) {
      toast.error('Please fill all required fields');
      return;
    }

    if (isEditMode) {
      updateMutation.mutate({
        id: formData.id,
        data: {
          name: formData.name,
          zone_type: formData.zone_type,
          description: formData.description || undefined,
          is_active: formData.is_active,
        },
      });
    } else {
      createMutation.mutate({
        name: formData.name,
        code: formData.code.toUpperCase(),
        warehouse_id: formData.warehouse_id,
        zone_type: formData.zone_type,
        description: formData.description || undefined,
        is_active: formData.is_active,
      });
    }
  };

  const columns: ColumnDef<Zone>[] = [
    {
      accessorKey: 'name',
      header: 'Zone',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Grid3X3 className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium">{row.original.name}</div>
            <div className="text-sm text-muted-foreground">{row.original.code}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'warehouse',
      header: 'Warehouse',
      cell: ({ row }) => row.original.warehouse?.name || '-',
    },
    {
      accessorKey: 'zone_type',
      header: 'Type',
      cell: ({ row }) => (
        <span className="capitalize text-sm">
          {row.original.zone_type?.replace(/_/g, ' ').toLowerCase()}
        </span>
      ),
    },
    {
      accessorKey: 'bin_count',
      header: 'Bins',
      cell: ({ row }) => row.original.bin_count ?? 0,
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
            <DropdownMenuItem asChild>
              <Link href={`/dashboard/inventory/bins?zone_id=${row.original.id}`}>
                <Grid3X3 className="mr-2 h-4 w-4" />
                View Bins
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleEdit(row.original)}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() => {
                setZoneToDelete(row.original);
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
        title="Warehouse Zones"
        description="Manage zones within warehouses for organized storage"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Zone
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{isEditMode ? 'Edit Zone' : 'Create New Zone'}</DialogTitle>
            <DialogDescription>
              {isEditMode ? 'Update zone details' : 'Add a new zone to a warehouse'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="warehouse">Warehouse *</Label>
              <Select
                value={formData.warehouse_id}
                onValueChange={(value) => setFormData({ ...formData, warehouse_id: value })}
                disabled={isEditMode}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {warehouses?.items?.map((wh: { id: string; name: string; code: string }) => (
                    <SelectItem key={wh.id} value={wh.id}>
                      {wh.name} ({wh.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  placeholder="Zone A"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="code">Code *</Label>
                <Input
                  id="code"
                  placeholder="ZA"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">Zone Type</Label>
              <Select
                value={formData.zone_type}
                onValueChange={(value) => setFormData({ ...formData, zone_type: value })}
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
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Optional description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="is_active"
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
              />
              <Label htmlFor="is_active">Active</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={resetForm}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {(createMutation.isPending || updateMutation.isPending) && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {isEditMode ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Zone</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{zoneToDelete?.name}"? This will also delete all bins in this zone. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => zoneToDelete && deleteMutation.mutate(zoneToDelete.id)}
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
