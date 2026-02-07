'use client';

import { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, Building, Phone, Mail, Lock, Loader2, Barcode } from 'lucide-react';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { vendorsApi } from '@/lib/api';
import { Vendor } from '@/types';

const tierColors: Record<string, string> = {
  'A+': 'bg-purple-100 text-purple-800',
  'A': 'bg-green-100 text-green-800',
  'B': 'bg-blue-100 text-blue-800',
  'C': 'bg-yellow-100 text-yellow-800',
  'D': 'bg-red-100 text-red-800',
  PLATINUM: 'bg-purple-100 text-purple-800',
  GOLD: 'bg-yellow-100 text-yellow-800',
  SILVER: 'bg-gray-100 text-gray-800',
  BRONZE: 'bg-orange-100 text-orange-800',
};

// Action cell component to handle edit/delete
function VendorActionsCell({
  vendor,
  onEdit,
  onDelete,
}: {
  vendor: Vendor;
  onEdit: (vendor: Vendor) => void;
  onDelete: (vendor: Vendor) => void;
}) {
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
        <DropdownMenuItem onClick={() => onEdit(vendor)}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit
        </DropdownMenuItem>
        <DropdownMenuItem
          className="text-destructive focus:text-destructive"
          onClick={() => onDelete(vendor)}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Column definitions factory
function getColumns(
  onEdit: (vendor: Vendor) => void,
  onDelete: (vendor: Vendor) => void
): ColumnDef<Vendor>[] {
  return [
    {
      accessorKey: 'name',
      header: 'Vendor',
      cell: ({ row }) => {
        const vendorType = row.original.vendor_type || '';
        const needsSupplierCode = ['SPARE_PARTS', 'MANUFACTURER', 'RAW_MATERIAL'].includes(vendorType);
        const hasSupplierCode = !!row.original.supplier_code;
        return (
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
              <Building className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <div className="font-medium">{row.original.name}</div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground font-mono">{row.original.code}</span>
                {hasSupplierCode && (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 text-xs font-medium">
                    <Barcode className="h-3 w-3" />
                    {row.original.supplier_code}
                  </span>
                )}
                {needsSupplierCode && !hasSupplierCode && row.original.status === 'ACTIVE' && (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 text-xs">
                    No barcode
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'contact',
      header: 'Contact',
      cell: ({ row }) => (
        <div className="space-y-1">
          {row.original.email ? (
            <div className="flex items-center gap-1 text-sm">
              <Mail className="h-3 w-3 text-muted-foreground" />
              {row.original.email}
            </div>
          ) : null}
          {row.original.phone ? (
            <div className="flex items-center gap-1 text-sm">
              <Phone className="h-3 w-3 text-muted-foreground" />
              {row.original.phone}
            </div>
          ) : null}
          {!row.original.email && !row.original.phone && (
            <span className="text-sm text-muted-foreground">-</span>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'gst_number',
      header: 'GST Number',
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.original.gst_number || '-'}</span>
      ),
    },
    {
      accessorKey: 'tier',
      header: 'Tier',
      cell: ({ row }) => {
        const tier = row.original.tier || row.original.grade || 'N/A';
        return (
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${tierColors[tier] || 'bg-gray-100'}`}>
            {tier}
          </span>
        );
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <VendorActionsCell
          vendor={row.original}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ),
    },
  ];
}

type VendorFormData = {
  name: string;
  code: string;
  email: string;
  phone: string;
  gst_number: string;
  pan_number: string;
  tier: 'PLATINUM' | 'GOLD' | 'SILVER' | 'BRONZE';
  vendor_type: 'MANUFACTURER' | 'DISTRIBUTOR' | 'SPARE_PARTS' | 'SERVICE_PROVIDER' | 'RAW_MATERIAL' | 'TRANSPORTER';
  contact_person: string;
  address_line1: string;
  city: string;
  state: string;
  pincode: string;
  // Bank Details
  bank_name: string;
  bank_branch: string;
  bank_account_number: string;
  bank_ifsc: string;
  bank_account_type: 'SAVINGS' | 'CURRENT' | 'OD' | '';
  beneficiary_name: string;
};

const emptyFormData: VendorFormData = {
  name: '',
  code: '',
  email: '',
  phone: '',
  gst_number: '',
  pan_number: '',
  tier: 'SILVER',
  vendor_type: 'MANUFACTURER',
  contact_person: '',
  address_line1: '',
  city: '',
  state: '',
  pincode: '',
  // Bank Details
  bank_name: '',
  bank_branch: '',
  bank_account_number: '',
  bank_ifsc: '',
  bank_account_type: '',
  beneficiary_name: '',
};

export default function VendorsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  // Create dialog state
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isLoadingCode, setIsLoadingCode] = useState(false);
  const [newVendor, setNewVendor] = useState<VendorFormData>(emptyFormData);

  // Edit dialog state
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);
  const [editFormData, setEditFormData] = useState<VendorFormData>(emptyFormData);

  // Delete confirmation state
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [deletingVendor, setDeletingVendor] = useState<Vendor | null>(null);

  const queryClient = useQueryClient();

  // Fetch next vendor code when create dialog opens or vendor type changes
  const fetchNextCode = async (vendorType: string) => {
    setIsLoadingCode(true);
    try {
      const result = await vendorsApi.getNextCode(vendorType);
      setNewVendor(prev => ({ ...prev, code: result.next_code }));
    } catch (error) {
      console.error('Failed to fetch next vendor code:', error);
    } finally {
      setIsLoadingCode(false);
    }
  };

  // Fetch code when create dialog opens
  useEffect(() => {
    if (isCreateDialogOpen) {
      fetchNextCode(newVendor.vendor_type);
    }
  }, [isCreateDialogOpen]);

  // Update code when vendor type changes
  const handleVendorTypeChange = (value: typeof newVendor.vendor_type) => {
    setNewVendor(prev => ({ ...prev, vendor_type: value }));
    fetchNextCode(value);
  };

  // Fetch vendors
  const { data, isLoading } = useQuery({
    queryKey: ['vendors', page, pageSize],
    queryFn: () => vendorsApi.list({ page: page + 1, size: pageSize }),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: vendorsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      toast.success('Vendor created successfully');
      setIsCreateDialogOpen(false);
      setNewVendor(emptyFormData);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create vendor');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) => vendorsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      toast.success('Vendor updated successfully');
      setIsEditDialogOpen(false);
      setEditingVendor(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update vendor');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: vendorsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      toast.success('Vendor deleted successfully');
      setIsDeleteDialogOpen(false);
      setDeletingVendor(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete vendor');
    },
  });

  // Handlers
  const handleCreate = () => {
    if (!newVendor.name.trim()) {
      toast.error('Vendor name is required');
      return;
    }
    if (!newVendor.pan_number.trim() || newVendor.pan_number.length !== 10) {
      toast.error('Valid PAN number (10 characters) is required');
      return;
    }
    if (!newVendor.address_line1.trim()) {
      toast.error('Address is required');
      return;
    }
    if (!newVendor.city.trim() || !newVendor.state.trim() || !newVendor.pincode.trim()) {
      toast.error('City, State and Pincode are required');
      return;
    }
    createMutation.mutate(newVendor);
  };

  const handleEdit = (vendor: Vendor) => {
    setEditingVendor(vendor);
    setEditFormData({
      name: vendor.name,
      code: vendor.code || vendor.vendor_code || '',
      email: vendor.email || '',
      phone: vendor.phone || '',
      gst_number: vendor.gst_number || '',
      pan_number: vendor.pan_number || '',
      tier: (vendor.tier as VendorFormData['tier']) || 'SILVER',
      vendor_type: 'MANUFACTURER', // Default, would need to fetch from backend
      contact_person: vendor.contact_person || '',
      address_line1: '',
      city: vendor.city || '',
      state: vendor.state || '',
      pincode: '',
      // Bank Details
      bank_name: vendor.bank_name || '',
      bank_branch: vendor.bank_branch || '',
      bank_account_number: vendor.bank_account_number || '',
      bank_ifsc: vendor.bank_ifsc || '',
      bank_account_type: (vendor.bank_account_type as VendorFormData['bank_account_type']) || '',
      beneficiary_name: vendor.beneficiary_name || '',
    });
    setIsEditDialogOpen(true);
  };

  const handleDelete = (vendor: Vendor) => {
    setDeletingVendor(vendor);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (deletingVendor) {
      deleteMutation.mutate(deletingVendor.id);
    }
  };

  const handleUpdate = () => {
    if (!editingVendor) return;
    if (!editFormData.name.trim()) {
      toast.error('Vendor name is required');
      return;
    }

    // Transform frontend fields to backend fields
    const updateData: Record<string, unknown> = {
      name: editFormData.name,
      legal_name: editFormData.name,
      email: editFormData.email || undefined,
      phone: editFormData.phone || undefined,
      gstin: editFormData.gst_number || undefined,
      pan: editFormData.pan_number || undefined,
      contact_person: editFormData.contact_person || undefined,
      city: editFormData.city || undefined,
      state: editFormData.state || undefined,
      // Bank Details
      bank_name: editFormData.bank_name || undefined,
      bank_branch: editFormData.bank_branch || undefined,
      bank_account_number: editFormData.bank_account_number || undefined,
      bank_ifsc: editFormData.bank_ifsc || undefined,
      bank_account_type: editFormData.bank_account_type || undefined,
      beneficiary_name: editFormData.beneficiary_name || undefined,
    };

    updateMutation.mutate({ id: editingVendor.id, data: updateData });
  };

  // Generate columns with handlers
  const columns = useMemo(
    () => getColumns(handleEdit, handleDelete),
    []
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vendors"
        description="Manage suppliers and vendor relationships"
        actions={
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Vendor
          </Button>
        }
      />

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create New Vendor</DialogTitle>
            <DialogDescription>
              Add a new vendor to your supplier network.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {/* Basic Information */}
            <div className="text-sm font-medium text-muted-foreground">Basic Information</div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  placeholder="Vendor name"
                  value={newVendor.name}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, name: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="code">Code (Auto-generated)</Label>
                <div className="relative">
                  <Input
                    id="code"
                    placeholder={isLoadingCode ? "Loading..." : "VND-MFR-00001"}
                    value={newVendor.code}
                    readOnly
                    disabled
                    className="bg-muted pr-8 font-mono"
                  />
                  <Lock className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="vendor_type">Vendor Type *</Label>
                <Select
                  value={newVendor.vendor_type}
                  onValueChange={handleVendorTypeChange}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MANUFACTURER">Manufacturer (MFR)</SelectItem>
                    <SelectItem value="SPARE_PARTS">Spare Parts (SPR)</SelectItem>
                    <SelectItem value="DISTRIBUTOR">Distributor (DST)</SelectItem>
                    <SelectItem value="RAW_MATERIAL">Raw Material (RAW)</SelectItem>
                    <SelectItem value="SERVICE_PROVIDER">Service Provider (SVC)</SelectItem>
                    <SelectItem value="TRANSPORTER">Transporter (TRN)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="tier">Tier</Label>
                <Select
                  value={newVendor.tier}
                  onValueChange={(value: 'PLATINUM' | 'GOLD' | 'SILVER' | 'BRONZE') =>
                    setNewVendor({ ...newVendor, tier: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select tier" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PLATINUM">Platinum</SelectItem>
                    <SelectItem value="GOLD">Gold</SelectItem>
                    <SelectItem value="SILVER">Silver</SelectItem>
                    <SelectItem value="BRONZE">Bronze</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Contact Information */}
            <div className="text-sm font-medium text-muted-foreground mt-2">Contact Information</div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="contact_person">Contact Person</Label>
                <Input
                  id="contact_person"
                  placeholder="Contact person name"
                  value={newVendor.contact_person}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, contact_person: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="vendor@example.com"
                  value={newVendor.email}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, email: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Phone</Label>
              <Input
                id="phone"
                placeholder="+91 9876543210"
                value={newVendor.phone}
                onChange={(e) =>
                  setNewVendor({ ...newVendor, phone: e.target.value })
                }
              />
            </div>

            {/* Tax Information */}
            <div className="text-sm font-medium text-muted-foreground mt-2">Tax Information</div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="gst_number">GSTIN (15 characters)</Label>
                <Input
                  id="gst_number"
                  placeholder="22AAAAA0000A1Z5"
                  maxLength={15}
                  value={newVendor.gst_number}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, gst_number: e.target.value.toUpperCase() })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pan_number">PAN (10 characters) *</Label>
                <Input
                  id="pan_number"
                  placeholder="AAAAA0000A"
                  maxLength={10}
                  value={newVendor.pan_number}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, pan_number: e.target.value.toUpperCase() })
                  }
                  required
                />
              </div>
            </div>

            {/* Address Information */}
            <div className="text-sm font-medium text-muted-foreground mt-2">Address Information</div>
            <div className="space-y-2">
              <Label htmlFor="address_line1">Address *</Label>
              <Input
                id="address_line1"
                placeholder="Street address"
                value={newVendor.address_line1}
                onChange={(e) =>
                  setNewVendor({ ...newVendor, address_line1: e.target.value })
                }
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="city">City *</Label>
                <Input
                  id="city"
                  placeholder="City"
                  value={newVendor.city}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, city: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="state">State *</Label>
                <Input
                  id="state"
                  placeholder="State"
                  value={newVendor.state}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, state: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pincode">Pincode *</Label>
                <Input
                  id="pincode"
                  placeholder="110001"
                  maxLength={6}
                  value={newVendor.pincode}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, pincode: e.target.value })
                  }
                />
              </div>
            </div>

            {/* Bank Details */}
            <div className="text-sm font-medium text-muted-foreground mt-2">Bank Details (for Payment)</div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="bank_name">Bank Name</Label>
                <Input
                  id="bank_name"
                  placeholder="e.g., HDFC Bank"
                  value={newVendor.bank_name}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, bank_name: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bank_branch">Branch</Label>
                <Input
                  id="bank_branch"
                  placeholder="e.g., Connaught Place"
                  value={newVendor.bank_branch}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, bank_branch: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="bank_account_number">Account Number</Label>
                <Input
                  id="bank_account_number"
                  placeholder="e.g., 50100123456789"
                  value={newVendor.bank_account_number}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, bank_account_number: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bank_ifsc">IFSC Code</Label>
                <Input
                  id="bank_ifsc"
                  placeholder="e.g., HDFC0001234"
                  maxLength={11}
                  value={newVendor.bank_ifsc}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, bank_ifsc: e.target.value.toUpperCase() })
                  }
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="bank_account_type">Account Type</Label>
                <Select
                  value={newVendor.bank_account_type}
                  onValueChange={(value: 'SAVINGS' | 'CURRENT' | 'OD') =>
                    setNewVendor({ ...newVendor, bank_account_type: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select account type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CURRENT">Current Account</SelectItem>
                    <SelectItem value="SAVINGS">Savings Account</SelectItem>
                    <SelectItem value="OD">Overdraft (OD)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="beneficiary_name">Beneficiary Name</Label>
                <Input
                  id="beneficiary_name"
                  placeholder="Name as per bank records"
                  value={newVendor.beneficiary_name}
                  onChange={(e) =>
                    setNewVendor({ ...newVendor, beneficiary_name: e.target.value })
                  }
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Vendor'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="name"
        searchPlaceholder="Search vendors..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Vendor</DialogTitle>
            <DialogDescription>
              Update vendor information for {editingVendor?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="text-sm font-medium text-muted-foreground">Basic Information</div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Vendor Code</Label>
                <Input value={editFormData.code} disabled className="bg-muted font-mono" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-name">Name *</Label>
                <Input
                  id="edit-name"
                  value={editFormData.name}
                  onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-email">Email</Label>
                <Input
                  id="edit-email"
                  type="email"
                  value={editFormData.email}
                  onChange={(e) => setEditFormData({ ...editFormData, email: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-phone">Phone</Label>
                <Input
                  id="edit-phone"
                  value={editFormData.phone}
                  onChange={(e) => setEditFormData({ ...editFormData, phone: e.target.value })}
                />
              </div>
            </div>

            <div className="text-sm font-medium text-muted-foreground mt-2">Tax Information</div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-gst">GSTIN</Label>
                <Input
                  id="edit-gst"
                  value={editFormData.gst_number}
                  maxLength={15}
                  onChange={(e) => setEditFormData({ ...editFormData, gst_number: e.target.value.toUpperCase() })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-pan">PAN *</Label>
                <Input
                  id="edit-pan"
                  value={editFormData.pan_number}
                  maxLength={10}
                  onChange={(e) => setEditFormData({ ...editFormData, pan_number: e.target.value.toUpperCase() })}
                />
              </div>
            </div>

            <div className="text-sm font-medium text-muted-foreground mt-2">Bank Details</div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-bank-name">Bank Name</Label>
                <Input
                  id="edit-bank-name"
                  value={editFormData.bank_name}
                  onChange={(e) => setEditFormData({ ...editFormData, bank_name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-bank-branch">Branch</Label>
                <Input
                  id="edit-bank-branch"
                  value={editFormData.bank_branch}
                  onChange={(e) => setEditFormData({ ...editFormData, bank_branch: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-account-number">Account Number</Label>
                <Input
                  id="edit-account-number"
                  value={editFormData.bank_account_number}
                  onChange={(e) => setEditFormData({ ...editFormData, bank_account_number: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-ifsc">IFSC Code</Label>
                <Input
                  id="edit-ifsc"
                  value={editFormData.bank_ifsc}
                  maxLength={11}
                  onChange={(e) => setEditFormData({ ...editFormData, bank_ifsc: e.target.value.toUpperCase() })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-account-type">Account Type</Label>
                <Select
                  value={editFormData.bank_account_type}
                  onValueChange={(value: 'SAVINGS' | 'CURRENT' | 'OD') =>
                    setEditFormData({ ...editFormData, bank_account_type: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select account type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CURRENT">Current Account</SelectItem>
                    <SelectItem value="SAVINGS">Savings Account</SelectItem>
                    <SelectItem value="OD">Overdraft (OD)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-beneficiary">Beneficiary Name</Label>
                <Input
                  id="edit-beneficiary"
                  value={editFormData.beneficiary_name}
                  onChange={(e) => setEditFormData({ ...editFormData, beneficiary_name: e.target.value })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdate} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Vendor</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{deletingVendor?.name}</strong> ({deletingVendor?.code})?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeletingVendor(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
