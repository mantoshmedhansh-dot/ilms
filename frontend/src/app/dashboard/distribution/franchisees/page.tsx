'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, Pencil, Building2, MapPin, Phone, FileText, GraduationCap, ClipboardCheck, LifeBuoy } from 'lucide-react';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatDate } from '@/lib/utils';

interface Franchisee {
  id: string;
  name: string;
  code: string;
  owner_name: string;
  phone: string;
  email?: string;
  territory?: string;
  city: string;
  state: string;
  status: 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'TERMINATED';
  agreement_start_date?: string;
  agreement_end_date?: string;
  royalty_percentage?: number;
  serviceable_pincodes_count?: number;
  created_at: string;
}

const franchiseesApi = {
  list: async (params?: { page?: number; size?: number; status?: string }) => {
    try {
      const { data } = await apiClient.get('/franchisees', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  create: async (franchisee: Record<string, unknown>) => {
    const { data } = await apiClient.post('/franchisees', franchisee);
    return data;
  },
  update: async (id: string, franchisee: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/franchisees/${id}`, franchisee);
    return data;
  },
};

export default function FranchiseesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDetailSheetOpen, setIsDetailSheetOpen] = useState(false);
  const [selectedFranchisee, setSelectedFranchisee] = useState<Franchisee | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    code: '',
    owner_name: '',
    phone: '',
    email: '',
    territory: '',
    city: '',
    state: '',
    royalty_percentage: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['franchisees', page, pageSize],
    queryFn: () => franchiseesApi.list({ page: page + 1, size: pageSize }),
  });

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => franchiseesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['franchisees'] });
      setIsCreateDialogOpen(false);
      resetForm();
      toast.success('Franchisee created successfully');
    },
    onError: () => {
      toast.error('Failed to create franchisee');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) => franchiseesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['franchisees'] });
      setIsEditDialogOpen(false);
      setSelectedFranchisee(null);
      resetForm();
      toast.success('Franchisee updated successfully');
    },
    onError: () => {
      toast.error('Failed to update franchisee');
    },
  });

  const resetForm = () => {
    setFormData({
      name: '',
      code: '',
      owner_name: '',
      phone: '',
      email: '',
      territory: '',
      city: '',
      state: '',
      royalty_percentage: '',
    });
  };

  const handleCreateSubmit = () => {
    if (!formData.name || !formData.owner_name || !formData.phone) {
      toast.error('Please fill in required fields');
      return;
    }
    createMutation.mutate({
      ...formData,
      royalty_percentage: formData.royalty_percentage ? parseFloat(formData.royalty_percentage) : undefined,
    });
  };

  const handleEditClick = (franchisee: Franchisee) => {
    setSelectedFranchisee(franchisee);
    setFormData({
      name: franchisee.name,
      code: franchisee.code,
      owner_name: franchisee.owner_name,
      phone: franchisee.phone,
      email: franchisee.email || '',
      territory: franchisee.territory || '',
      city: franchisee.city,
      state: franchisee.state,
      royalty_percentage: franchisee.royalty_percentage?.toString() || '',
    });
    setIsEditDialogOpen(true);
  };

  const handleEditSubmit = () => {
    if (!selectedFranchisee) return;
    updateMutation.mutate({
      id: selectedFranchisee.id,
      data: {
        ...formData,
        royalty_percentage: formData.royalty_percentage ? parseFloat(formData.royalty_percentage) : undefined,
      },
    });
  };

  const handleViewDetails = (franchisee: Franchisee) => {
    setSelectedFranchisee(franchisee);
    setIsDetailSheetOpen(true);
  };

  const columns: ColumnDef<Franchisee>[] = [
    {
      accessorKey: 'name',
      header: 'Franchisee',
      cell: ({ row }) => (
        <div
          className="flex items-center gap-3 cursor-pointer hover:opacity-80"
          onClick={() => handleViewDetails(row.original)}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Building2 className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium">{row.original.name}</div>
            <div className="text-sm text-muted-foreground">{row.original.code}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'owner_name',
      header: 'Owner',
      cell: ({ row }) => (
        <div>
          <div className="text-sm">{row.original.owner_name}</div>
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Phone className="h-3 w-3" />
            {row.original.phone}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'location',
      header: 'Location',
      cell: ({ row }) => (
        <div className="flex items-center gap-1 text-sm">
          <MapPin className="h-3 w-3 text-muted-foreground" />
          <span>{row.original.city}, {row.original.state}</span>
        </div>
      ),
    },
    {
      accessorKey: 'territory',
      header: 'Territory',
      cell: ({ row }) => (
        <div className="text-sm">
          <div>{row.original.territory || '-'}</div>
          {row.original.serviceable_pincodes_count && (
            <div className="text-xs text-muted-foreground">
              {row.original.serviceable_pincodes_count} pincodes
            </div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'agreement',
      header: 'Agreement',
      cell: ({ row }) => (
        <div className="text-sm">
          {row.original.agreement_end_date ? (
            <>
              <div>Till {formatDate(row.original.agreement_end_date)}</div>
              {row.original.royalty_percentage && (
                <div className="text-xs text-muted-foreground">
                  {row.original.royalty_percentage}% royalty
                </div>
              )}
            </>
          ) : (
            <span className="text-muted-foreground">No agreement</span>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
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
            <DropdownMenuItem onClick={() => handleViewDetails(row.original)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/dashboard/distribution/franchisees/${row.original.id}?tab=contracts`)}>
              <FileText className="mr-2 h-4 w-4" />
              Contracts
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/dashboard/distribution/franchisees/${row.original.id}?tab=training`)}>
              <GraduationCap className="mr-2 h-4 w-4" />
              Training
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/dashboard/distribution/franchisees/${row.original.id}?tab=audits`)}>
              <ClipboardCheck className="mr-2 h-4 w-4" />
              Audits
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/dashboard/distribution/franchisees/${row.original.id}?tab=support`)}>
              <LifeBuoy className="mr-2 h-4 w-4" />
              Support Tickets
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => handleEditClick(row.original)}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Franchisees"
        description="Manage franchise partners and territories"
        actions={
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Franchisee
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="name"
        searchPlaceholder="Search franchisees..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Create Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add New Franchisee</DialogTitle>
            <DialogDescription>Add a new franchise partner to your network</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Franchisee Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Enter franchisee name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="code">Code</Label>
                <Input
                  id="code"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  placeholder="Enter code"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="owner_name">Owner Name *</Label>
                <Input
                  id="owner_name"
                  value={formData.owner_name}
                  onChange={(e) => setFormData({ ...formData, owner_name: e.target.value })}
                  placeholder="Enter owner name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone">Phone *</Label>
                <Input
                  id="phone"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="Enter phone number"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="Enter email"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="territory">Territory</Label>
                <Input
                  id="territory"
                  value={formData.territory}
                  onChange={(e) => setFormData({ ...formData, territory: e.target.value })}
                  placeholder="Enter territory"
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="city">City</Label>
                <Input
                  id="city"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="Enter city"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="state">State</Label>
                <Input
                  id="state"
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                  placeholder="Enter state"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="royalty_percentage">Royalty %</Label>
                <Input
                  id="royalty_percentage"
                  type="number"
                  value={formData.royalty_percentage}
                  onChange={(e) => setFormData({ ...formData, royalty_percentage: e.target.value })}
                  placeholder="e.g. 10"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsCreateDialogOpen(false); resetForm(); }}>Cancel</Button>
            <Button onClick={handleCreateSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Add Franchisee'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Franchisee</DialogTitle>
            <DialogDescription>Update franchisee information</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-name">Franchisee Name *</Label>
                <Input
                  id="edit-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Enter franchisee name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-code">Code</Label>
                <Input
                  id="edit-code"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  placeholder="Enter code"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-owner_name">Owner Name *</Label>
                <Input
                  id="edit-owner_name"
                  value={formData.owner_name}
                  onChange={(e) => setFormData({ ...formData, owner_name: e.target.value })}
                  placeholder="Enter owner name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-phone">Phone *</Label>
                <Input
                  id="edit-phone"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="Enter phone number"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-email">Email</Label>
                <Input
                  id="edit-email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="Enter email"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-territory">Territory</Label>
                <Input
                  id="edit-territory"
                  value={formData.territory}
                  onChange={(e) => setFormData({ ...formData, territory: e.target.value })}
                  placeholder="Enter territory"
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-city">City</Label>
                <Input
                  id="edit-city"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="Enter city"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-state">State</Label>
                <Input
                  id="edit-state"
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                  placeholder="Enter state"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-royalty_percentage">Royalty %</Label>
                <Input
                  id="edit-royalty_percentage"
                  type="number"
                  value={formData.royalty_percentage}
                  onChange={(e) => setFormData({ ...formData, royalty_percentage: e.target.value })}
                  placeholder="e.g. 10"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsEditDialogOpen(false); setSelectedFranchisee(null); resetForm(); }}>Cancel</Button>
            <Button onClick={handleEditSubmit} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail Sheet */}
      <Sheet open={isDetailSheetOpen} onOpenChange={setIsDetailSheetOpen}>
        <SheetContent className="w-[500px] sm:w-[600px]">
          <SheetHeader>
            <SheetTitle>Franchisee Details</SheetTitle>
            <SheetDescription>{selectedFranchisee?.code}</SheetDescription>
          </SheetHeader>
          {selectedFranchisee && (
            <div className="mt-6 space-y-6">
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-muted">
                  <Building2 className="h-8 w-8 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">{selectedFranchisee.name}</h3>
                  <StatusBadge status={selectedFranchisee.status} />
                </div>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-muted-foreground">Owner</label>
                    <p className="font-medium">{selectedFranchisee.owner_name}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Phone</label>
                    <p className="font-medium">{selectedFranchisee.phone}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-muted-foreground">Email</label>
                    <p className="font-medium">{selectedFranchisee.email || '-'}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Territory</label>
                    <p className="font-medium">{selectedFranchisee.territory || '-'}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-muted-foreground">Location</label>
                    <p className="font-medium">{selectedFranchisee.city}, {selectedFranchisee.state}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Serviceable Pincodes</label>
                    <p className="font-medium">{selectedFranchisee.serviceable_pincodes_count || 0}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-muted-foreground">Agreement End</label>
                    <p className="font-medium">{selectedFranchisee.agreement_end_date ? formatDate(selectedFranchisee.agreement_end_date) : '-'}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Royalty</label>
                    <p className="font-medium">{selectedFranchisee.royalty_percentage ? `${selectedFranchisee.royalty_percentage}%` : '-'}</p>
                  </div>
                </div>
              </div>

              <div className="flex gap-2 pt-4">
                <Button variant="outline" className="flex-1" onClick={() => {
                  setIsDetailSheetOpen(false);
                  handleEditClick(selectedFranchisee);
                }}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit
                </Button>
                <Button className="flex-1" onClick={() => router.push(`/dashboard/distribution/franchisees/${selectedFranchisee.id}`)}>
                  <Eye className="mr-2 h-4 w-4" />
                  Full Profile
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
