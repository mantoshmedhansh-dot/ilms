'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { useRouter } from 'next/navigation';
import { MoreHorizontal, Plus, Eye, CheckCircle, Wrench, Calendar, User, Package } from 'lucide-react';
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
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { installationsApi, customersApi, productsApi, techniciansApi } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { toast } from 'sonner';

interface Installation {
  id: string;
  installation_number: string;
  order_id?: string;
  customer_id: string;
  customer?: { name: string; phone: string };
  product_id: string;
  product?: { name: string; sku: string };
  serial_number?: string;
  status: 'PENDING' | 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  scheduled_date?: string;
  completed_date?: string;
  technician_id?: string;
  technician?: { name: string };
  address?: string;
  notes?: string;
  created_at: string;
}

export default function InstallationsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isDetailsSheetOpen, setIsDetailsSheetOpen] = useState(false);
  const [selectedInstallation, setSelectedInstallation] = useState<Installation | null>(null);
  const [formData, setFormData] = useState({
    customer_id: '',
    product_id: '',
    serial_number: '',
    technician_id: '',
    scheduled_date: '',
    address: '',
    notes: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['installations', page, pageSize],
    queryFn: () => installationsApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: customers } = useQuery({
    queryKey: ['customers-list'],
    queryFn: () => customersApi.list({ size: 100 }),
  });

  const { data: products } = useQuery({
    queryKey: ['products-list'],
    queryFn: () => productsApi.list({ size: 100 }),
  });

  const { data: technicians } = useQuery({
    queryKey: ['technicians-list'],
    queryFn: () => techniciansApi.list({ size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => installationsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['installations'] });
      setIsCreateDialogOpen(false);
      setFormData({
        customer_id: '',
        product_id: '',
        serial_number: '',
        technician_id: '',
        scheduled_date: '',
        address: '',
        notes: '',
      });
      toast.success('Installation created successfully');
    },
    onError: () => {
      toast.error('Failed to create installation');
    },
  });

  const markCompleteMutation = useMutation({
    mutationFn: (id: string) => installationsApi.update(id, { status: 'COMPLETED', completed_date: new Date().toISOString() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['installations'] });
      toast.success('Installation marked as complete');
    },
    onError: () => {
      toast.error('Failed to update installation');
    },
  });

  const handleViewDetails = (installation: Installation) => {
    setSelectedInstallation(installation);
    setIsDetailsSheetOpen(true);
  };

  const handleMarkComplete = (id: string) => {
    markCompleteMutation.mutate(id);
  };

  const handleCreateSubmit = () => {
    if (!formData.customer_id || !formData.product_id) {
      toast.error('Please select customer and product');
      return;
    }
    createMutation.mutate(formData);
  };

  const columns: ColumnDef<Installation>[] = [
    {
      accessorKey: 'installation_number',
      header: 'Installation #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Wrench className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.original.installation_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'customer',
      header: 'Customer',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.customer?.name || 'N/A'}</div>
          <div className="text-sm text-muted-foreground">{row.original.customer?.phone}</div>
        </div>
      ),
    },
    {
      accessorKey: 'product',
      header: 'Product',
      cell: ({ row }) => (
        <div>
          <div className="text-sm">{row.original.product?.name || 'N/A'}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.original.serial_number}</div>
        </div>
      ),
    },
    {
      accessorKey: 'technician',
      header: 'Technician',
      cell: ({ row }) => (
        <span className="text-sm">
          {row.original.technician?.name || 'Not assigned'}
        </span>
      ),
    },
    {
      accessorKey: 'scheduled_date',
      header: 'Schedule',
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Calendar className="h-3 w-3 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">
            {row.original.scheduled_date ? formatDate(row.original.scheduled_date) : 'Not scheduled'}
          </span>
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
            {row.original.status === 'IN_PROGRESS' && (
              <DropdownMenuItem onClick={() => handleMarkComplete(row.original.id)}>
                <CheckCircle className="mr-2 h-4 w-4" />
                Mark Complete
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Installations"
        description="Track and manage product installations"
        actions={
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Installation
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="installation_number"
        searchPlaceholder="Search installations..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Create Installation Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create New Installation</DialogTitle>
            <DialogDescription>
              Schedule a new product installation for a customer
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="customer">Customer *</Label>
                <Select
                  value={formData.customer_id}
                  onValueChange={(value) => setFormData({ ...formData, customer_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select customer" />
                  </SelectTrigger>
                  <SelectContent>
                    {customers?.items?.map((customer: any) => (
                      <SelectItem key={customer.id} value={customer.id}>
                        {customer.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="product">Product *</Label>
                <Select
                  value={formData.product_id}
                  onValueChange={(value) => setFormData({ ...formData, product_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select product" />
                  </SelectTrigger>
                  <SelectContent>
                    {products?.items?.map((product: any) => (
                      <SelectItem key={product.id} value={product.id}>
                        {product.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="serial_number">Serial Number</Label>
                <Input
                  id="serial_number"
                  value={formData.serial_number}
                  onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
                  placeholder="Enter serial number"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="technician">Assigned Technician</Label>
                <Select
                  value={formData.technician_id}
                  onValueChange={(value) => setFormData({ ...formData, technician_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select technician" />
                  </SelectTrigger>
                  <SelectContent>
                    {technicians?.items?.map((tech: any) => (
                      <SelectItem key={tech.id} value={tech.id}>
                        {tech.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="scheduled_date">Scheduled Date</Label>
                <Input
                  id="scheduled_date"
                  type="datetime-local"
                  value={formData.scheduled_date}
                  onChange={(e) => setFormData({ ...formData, scheduled_date: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="address">Installation Address</Label>
              <Textarea
                id="address"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="Enter installation address"
                rows={2}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Additional notes..."
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Installation'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Details Sheet */}
      <Sheet open={isDetailsSheetOpen} onOpenChange={setIsDetailsSheetOpen}>
        <SheetContent className="w-[500px] sm:w-[600px]">
          <SheetHeader>
            <SheetTitle>Installation Details</SheetTitle>
            <SheetDescription>
              {selectedInstallation?.installation_number}
            </SheetDescription>
          </SheetHeader>
          {selectedInstallation && (
            <div className="mt-6 space-y-6">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                <StatusBadge status={selectedInstallation.status} />
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Customer Information
                </h4>
                <div className="rounded-lg border p-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Name</span>
                    <span className="text-sm font-medium">{selectedInstallation.customer?.name || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Phone</span>
                    <span className="text-sm">{selectedInstallation.customer?.phone || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Address</span>
                    <span className="text-sm text-right max-w-[200px]">{selectedInstallation.address || 'N/A'}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium flex items-center gap-2">
                  <Package className="h-4 w-4" />
                  Product Information
                </h4>
                <div className="rounded-lg border p-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Product</span>
                    <span className="text-sm font-medium">{selectedInstallation.product?.name || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">SKU</span>
                    <span className="text-sm font-mono">{selectedInstallation.product?.sku || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Serial Number</span>
                    <span className="text-sm font-mono">{selectedInstallation.serial_number || 'N/A'}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Schedule
                </h4>
                <div className="rounded-lg border p-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Technician</span>
                    <span className="text-sm">{selectedInstallation.technician?.name || 'Not assigned'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Scheduled Date</span>
                    <span className="text-sm">
                      {selectedInstallation.scheduled_date ? formatDate(selectedInstallation.scheduled_date) : 'Not scheduled'}
                    </span>
                  </div>
                  {selectedInstallation.completed_date && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Completed Date</span>
                      <span className="text-sm">{formatDate(selectedInstallation.completed_date)}</span>
                    </div>
                  )}
                </div>
              </div>

              {selectedInstallation.notes && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Notes</h4>
                  <p className="text-sm text-muted-foreground">{selectedInstallation.notes}</p>
                </div>
              )}

              {selectedInstallation.status === 'IN_PROGRESS' && (
                <Button
                  className="w-full"
                  onClick={() => {
                    handleMarkComplete(selectedInstallation.id);
                    setIsDetailsSheetOpen(false);
                  }}
                >
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Mark as Complete
                </Button>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
