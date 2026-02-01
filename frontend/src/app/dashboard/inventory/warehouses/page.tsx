'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, Warehouse, MapPin, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/providers/auth-provider';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
import { Switch } from '@/components/ui/switch';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { warehousesApi } from '@/lib/api';
import { Warehouse as WarehouseType } from '@/types';

const warehouseTypes = [
  { label: 'Main Warehouse', value: 'MAIN' },
  { label: 'Regional Warehouse', value: 'REGIONAL' },
  { label: 'Service Center', value: 'SERVICE_CENTER' },
  { label: 'Dealer', value: 'DEALER' },
  { label: 'Virtual', value: 'VIRTUAL' },
];

export default function WarehousesPage() {
  const { permissions } = useAuth();
  const isSuperAdmin = permissions?.is_super_admin ?? false;
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingWarehouse, setEditingWarehouse] = useState<WarehouseType | null>(null);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [warehouseToDelete, setWarehouseToDelete] = useState<WarehouseType | null>(null);
  const [newWarehouse, setNewWarehouse] = useState<{
    name: string;
    code: string;
    type: 'MAIN' | 'REGIONAL' | 'SERVICE_CENTER' | 'DEALER' | 'VIRTUAL';
    address: string;
    city: string;
    state: string;
    pincode: string;
    capacity: string;
    is_active: boolean;
  }>({
    name: '',
    code: '',
    type: 'MAIN',
    address: '',
    city: '',
    state: '',
    pincode: '',
    capacity: '',
    is_active: true,
  });

  const queryClient = useQueryClient();

  const handleEdit = (warehouse: WarehouseType) => {
    setEditingWarehouse(warehouse);
    setNewWarehouse({
      name: warehouse.name,
      code: warehouse.code,
      type: warehouse.type as 'MAIN' | 'REGIONAL' | 'SERVICE_CENTER' | 'DEALER' | 'VIRTUAL',
      address: warehouse.address || '',
      city: warehouse.city || '',
      state: warehouse.state || '',
      pincode: warehouse.pincode || '',
      capacity: warehouse.capacity?.toString() || '',
      is_active: warehouse.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setIsEditMode(false);
    setEditingWarehouse(null);
    setNewWarehouse({
      name: '',
      code: '',
      type: 'MAIN',
      address: '',
      city: '',
      state: '',
      pincode: '',
      capacity: '',
      is_active: true,
    });
  };

  const { data, isLoading } = useQuery({
    queryKey: ['warehouses', page, pageSize],
    queryFn: () => warehousesApi.list({ page: page + 1, size: pageSize }),
  });

  const createMutation = useMutation({
    mutationFn: warehousesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      toast.success('Warehouse created successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create warehouse');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<WarehouseType> }) => warehousesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      toast.success('Warehouse updated successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update warehouse');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: warehousesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      toast.success('Warehouse deleted successfully');
      setIsDeleteOpen(false);
      setWarehouseToDelete(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete warehouse');
    },
  });

  const columns: ColumnDef<WarehouseType>[] = [
    {
      accessorKey: 'name',
      header: 'Warehouse',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Warehouse className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium">{row.original.name}</div>
            <div className="text-sm text-muted-foreground">{row.original.code}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'type',
      header: 'Type',
      cell: ({ row }) => (
        <span className="capitalize text-sm">
          {row.original.type?.replace(/_/g, ' ').toLowerCase() ?? '-'}
        </span>
      ),
    },
    {
      accessorKey: 'address',
      header: 'Location',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4 text-muted-foreground" />
          <div className="text-sm">
            <div>{[row.original.city, row.original.state].filter(Boolean).join(', ') || '-'}</div>
            <div className="text-muted-foreground">{row.original.pincode || '-'}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'capacity',
      header: 'Capacity',
      cell: ({ row }) => (
        <span className="text-sm">
          {row.original.capacity ? `${row.original.capacity.toLocaleString()} units` : '-'}
        </span>
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
            {isSuperAdmin && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => { setWarehouseToDelete(row.original); setIsDeleteOpen(true); }}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const handleSubmit = () => {
    if (!newWarehouse.name.trim()) {
      toast.error('Warehouse name is required');
      return;
    }
    if (!newWarehouse.code.trim()) {
      toast.error('Warehouse code is required');
      return;
    }

    const warehouseData = {
      name: newWarehouse.name,
      code: newWarehouse.code.toUpperCase(),
      type: newWarehouse.type,
      address: newWarehouse.address,
      city: newWarehouse.city,
      state: newWarehouse.state,
      pincode: newWarehouse.pincode,
      capacity: newWarehouse.capacity ? parseInt(newWarehouse.capacity) : undefined,
      is_active: newWarehouse.is_active,
    };

    if (isEditMode && editingWarehouse) {
      updateMutation.mutate({ id: editingWarehouse.id, data: warehouseData });
    } else {
      createMutation.mutate(warehouseData);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Warehouses"
        description="Manage warehouse locations and inventory storage"
        actions={
          <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
            <DialogTrigger asChild>
              <Button onClick={() => { setIsEditMode(false); setIsDialogOpen(true); }}>
                <Plus className="mr-2 h-4 w-4" />
                Add Warehouse
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>{isEditMode ? 'Edit Warehouse' : 'Create New Warehouse'}</DialogTitle>
                <DialogDescription>
                  {isEditMode ? 'Update warehouse details.' : 'Add a new warehouse location for inventory storage.'}
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Name *</Label>
                    <Input
                      id="name"
                      placeholder="Warehouse name"
                      value={newWarehouse.name}
                      onChange={(e) =>
                        setNewWarehouse({ ...newWarehouse, name: e.target.value })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="code">Code *</Label>
                    <Input
                      id="code"
                      placeholder="WH001"
                      value={newWarehouse.code}
                      onChange={(e) =>
                        setNewWarehouse({ ...newWarehouse, code: e.target.value.toUpperCase() })
                      }
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="type">Type</Label>
                  <Select
                    value={newWarehouse.type}
                    onValueChange={(value: 'MAIN' | 'REGIONAL' | 'SERVICE_CENTER' | 'DEALER' | 'VIRTUAL') =>
                      setNewWarehouse({ ...newWarehouse, type: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      {warehouseTypes.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="address">Address</Label>
                  <Input
                    id="address"
                    placeholder="Street address"
                    value={newWarehouse.address}
                    onChange={(e) =>
                      setNewWarehouse({ ...newWarehouse, address: e.target.value })
                    }
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="city">City</Label>
                    <Input
                      id="city"
                      placeholder="City"
                      value={newWarehouse.city}
                      onChange={(e) =>
                        setNewWarehouse({ ...newWarehouse, city: e.target.value })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="state">State</Label>
                    <Input
                      id="state"
                      placeholder="State"
                      value={newWarehouse.state}
                      onChange={(e) =>
                        setNewWarehouse({ ...newWarehouse, state: e.target.value })
                      }
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="pincode">Pincode</Label>
                    <Input
                      id="pincode"
                      placeholder="110001"
                      value={newWarehouse.pincode}
                      onChange={(e) =>
                        setNewWarehouse({ ...newWarehouse, pincode: e.target.value })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="capacity">Capacity</Label>
                    <Input
                      id="capacity"
                      type="number"
                      placeholder="Units"
                      value={newWarehouse.capacity}
                      onChange={(e) =>
                        setNewWarehouse({ ...newWarehouse, capacity: e.target.value })
                      }
                    />
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Switch
                    id="is_active"
                    checked={newWarehouse.is_active}
                    onCheckedChange={(checked) =>
                      setNewWarehouse({ ...newWarehouse, is_active: checked })
                    }
                  />
                  <Label htmlFor="is_active">Active</Label>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={handleDialogClose}>
                  Cancel
                </Button>
                <Button onClick={handleSubmit} disabled={createMutation.isPending || updateMutation.isPending}>
                  {createMutation.isPending || updateMutation.isPending ? 'Saving...' : isEditMode ? 'Update Warehouse' : 'Create Warehouse'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="name"
        searchPlaceholder="Search warehouses..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Delete Warehouse Confirmation */}
      <AlertDialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Warehouse</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete warehouse <strong>{warehouseToDelete?.name}</strong>?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => warehouseToDelete && deleteMutation.mutate(warehouseToDelete.id)}
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
