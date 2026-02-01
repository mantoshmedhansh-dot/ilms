'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, Truck, Phone, Mail, Globe, Loader2 } from 'lucide-react';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { transportersApi } from '@/lib/api';

interface Transporter {
  id: string;
  name: string;
  code: string;
  type: string;
  contact_name?: string;
  contact_phone?: string;
  contact_email?: string;
  website?: string;
  tracking_url_pattern?: string;
  api_integrated?: boolean;
  is_active: boolean;
  created_at: string;
}

const transporterTypes = [
  { label: 'Courier Partner', value: 'COURIER' },
  { label: 'Self-Delivery', value: 'SELF_SHIP' },
  { label: 'Marketplace', value: 'MARKETPLACE' },
  { label: 'Local', value: 'LOCAL' },
  { label: 'Franchise', value: 'FRANCHISE' },
];

export default function TransportersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [transporterToDelete, setTransporterToDelete] = useState<Transporter | null>(null);
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    code: '',
    type: 'COURIER',
    contact_name: '',
    contact_phone: '',
    contact_email: '',
    website: '',
    tracking_url_pattern: '',
    is_active: true,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['transporters', page, pageSize],
    queryFn: () => transportersApi.list({ page: page + 1, size: pageSize }),
  });

  const createMutation = useMutation({
    mutationFn: transportersApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transporters'] });
      toast.success('Transporter created successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create transporter'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof transportersApi.update>[1] }) =>
      transportersApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transporters'] });
      toast.success('Transporter updated successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update transporter'),
  });

  const deleteMutation = useMutation({
    mutationFn: transportersApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transporters'] });
      toast.success('Transporter deleted successfully');
      setDeleteDialogOpen(false);
      setTransporterToDelete(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete transporter'),
  });

  const resetForm = () => {
    setFormData({
      id: '',
      name: '',
      code: '',
      type: 'COURIER',
      contact_name: '',
      contact_phone: '',
      contact_email: '',
      website: '',
      tracking_url_pattern: '',
      is_active: true,
    });
    setIsEditMode(false);
    setIsDialogOpen(false);
  };

  const handleEdit = (transporter: Transporter) => {
    setFormData({
      id: transporter.id,
      name: transporter.name,
      code: transporter.code,
      type: transporter.type || 'COURIER',
      contact_name: transporter.contact_name || '',
      contact_phone: transporter.contact_phone || '',
      contact_email: transporter.contact_email || '',
      website: transporter.website || '',
      tracking_url_pattern: transporter.tracking_url_pattern || '',
      is_active: transporter.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleSubmit = () => {
    if (!formData.name.trim() || !formData.code.trim()) {
      toast.error('Name and code are required');
      return;
    }

    if (isEditMode) {
      updateMutation.mutate({
        id: formData.id,
        data: {
          name: formData.name,
          code: formData.code.toUpperCase(),
          transporter_type: formData.type,
          contact_name: formData.contact_name || undefined,
          contact_phone: formData.contact_phone || undefined,
          contact_email: formData.contact_email || undefined,
          address: formData.website || undefined,
          tracking_url_template: formData.tracking_url_pattern || undefined,
          is_active: formData.is_active,
        },
      });
    } else {
      createMutation.mutate({
        name: formData.name,
        code: formData.code.toUpperCase(),
        transporter_type: formData.type,
        contact_name: formData.contact_name || undefined,
        contact_phone: formData.contact_phone || undefined,
        contact_email: formData.contact_email || undefined,
        address: formData.website || undefined,
        tracking_url_template: formData.tracking_url_pattern || undefined,
        is_active: formData.is_active,
      });
    }
  };

  const columns: ColumnDef<Transporter>[] = [
    {
      accessorKey: 'name',
      header: 'Transporter',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Truck className="h-5 w-5 text-muted-foreground" />
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
      cell: ({ row }) => {
        const type = transporterTypes.find(t => t.value === row.original.type);
        return <span className="text-sm">{type?.label || row.original.type}</span>;
      },
    },
    {
      accessorKey: 'contact',
      header: 'Contact',
      cell: ({ row }) => (
        <div className="space-y-1">
          {row.original.contact_name && (
            <div className="text-sm">{row.original.contact_name}</div>
          )}
          {row.original.contact_phone && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Phone className="h-3 w-3" />
              {row.original.contact_phone}
            </div>
          )}
          {row.original.contact_email && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Mail className="h-3 w-3" />
              {row.original.contact_email}
            </div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'api_integrated',
      header: 'Integration',
      cell: ({ row }) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
          row.original.api_integrated
            ? 'bg-green-100 text-green-800'
            : 'bg-gray-100 text-gray-800'
        }`}>
          {row.original.api_integrated ? 'API Integrated' : 'Manual'}
        </span>
      ),
    },
    {
      accessorKey: 'website',
      header: 'Website',
      cell: ({ row }) => (
        row.original.website ? (
          <a
            href={row.original.website}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-sm text-blue-600 hover:underline"
          >
            <Globe className="h-3 w-3" />
            Visit
          </a>
        ) : (
          <span className="text-sm text-muted-foreground">-</span>
        )
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
                setTransporterToDelete(row.original);
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
        title="Transporters"
        description="Manage courier and logistics partners"
        actions={
          <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
            <DialogTrigger asChild>
              <Button onClick={() => setIsDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add Transporter
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>{isEditMode ? 'Edit Transporter' : 'Add New Transporter'}</DialogTitle>
                <DialogDescription>
                  {isEditMode ? 'Update transporter details' : 'Add a new courier or logistics partner'}
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Name *</Label>
                    <Input
                      placeholder="BlueDart"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Code *</Label>
                    <Input
                      placeholder="BD"
                      value={formData.code}
                      onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Select
                    value={formData.type}
                    onValueChange={(value) => setFormData({ ...formData, type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      {transporterTypes.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Contact Person</Label>
                  <Input
                    placeholder="Contact name"
                    value={formData.contact_name}
                    onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Phone</Label>
                    <Input
                      placeholder="Phone number"
                      value={formData.contact_phone}
                      onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input
                      type="email"
                      placeholder="Email"
                      value={formData.contact_email}
                      onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Website</Label>
                  <Input
                    placeholder="https://..."
                    value={formData.website}
                    onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Tracking URL Pattern</Label>
                  <Input
                    placeholder="https://track.example.com/{awb}"
                    value={formData.tracking_url_pattern}
                    onChange={(e) => setFormData({ ...formData, tracking_url_pattern: e.target.value })}
                  />
                  <p className="text-xs text-muted-foreground">Use {'{awb}'} as placeholder for AWB number</p>
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
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="name"
        searchPlaceholder="Search transporters..."
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
            <AlertDialogTitle>Delete Transporter</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{transporterToDelete?.name}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => transporterToDelete && deleteMutation.mutate(transporterToDelete.id)}
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
