'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  MoreHorizontal,
  Plus,
  Eye,
  CheckCircle,
  XCircle,
  FileText,
  ArrowRight,
  Building,
  Calendar,
  Loader2,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { vendorProformasApi, vendorsApi, productsApi } from '@/lib/api';
import { formatCurrency, cn } from '@/lib/utils';

interface ProformaItem {
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  gst_rate: number;
  amount: number;
}

interface VendorProforma {
  id: string;
  proforma_number: string;
  vendor_id: string;
  vendor?: { name: string; code?: string; vendor_code?: string };
  proforma_date: string;
  due_date: string;
  items: ProformaItem[];
  subtotal: number;
  gst_amount: number;
  total_amount: number;
  status: string;
  notes?: string;
  po_id?: string;
  created_at: string;
}

interface Vendor {
  id: string;
  name: string;
  code?: string;
  vendor_code?: string;
}

interface Product {
  id: string;
  name: string;
  sku: string;
  mrp: number;
}

const statusColors: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-800',
  PENDING: 'bg-yellow-100 text-yellow-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
  CONVERTED: 'bg-blue-100 text-blue-800',
};

// Separate component for actions to avoid hooks in render function
function ProformaActionsCell({
  proforma,
  onView,
  onApprove,
  onReject,
  onConvert,
}: {
  proforma: VendorProforma;
  onView: (proforma: VendorProforma) => void;
  onApprove: (proforma: VendorProforma) => void;
  onReject: (proforma: VendorProforma) => void;
  onConvert: (proforma: VendorProforma) => void;
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
        <DropdownMenuItem onClick={() => onView(proforma)}>
          <Eye className="mr-2 h-4 w-4" />
          View Details
        </DropdownMenuItem>
        {proforma.status === 'PENDING' && (
          <>
            <DropdownMenuItem onClick={() => onApprove(proforma)}>
              <CheckCircle className="mr-2 h-4 w-4" />
              Approve
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onReject(proforma)} className="text-destructive">
              <XCircle className="mr-2 h-4 w-4" />
              Reject
            </DropdownMenuItem>
          </>
        )}
        {proforma.status === 'APPROVED' && !proforma.po_id && (
          <DropdownMenuItem onClick={() => onConvert(proforma)}>
            <ArrowRight className="mr-2 h-4 w-4" />
            Convert to PO
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function VendorProformasPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isViewSheetOpen, setIsViewSheetOpen] = useState(false);
  const [isRejectDialogOpen, setIsRejectDialogOpen] = useState(false);
  const [isConvertDialogOpen, setIsConvertDialogOpen] = useState(false);
  const [selectedProforma, setSelectedProforma] = useState<VendorProforma | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  // Form state for creating proforma
  const [formData, setFormData] = useState({
    vendor_id: '',
    proforma_number: '',
    proforma_date: new Date(),
    due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days from now
    notes: '',
    items: [] as {
      product_id: string;
      product_name: string;
      sku: string;
      quantity: number;
      unit_price: number;
      gst_rate: number;
    }[],
  });

  // Fetch proformas
  const { data, isLoading } = useQuery({
    queryKey: ['vendor-proformas', page, pageSize, statusFilter],
    queryFn: () =>
      vendorProformasApi.list({
        page: page + 1,
        size: pageSize,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      }),
  });

  // Fetch vendors for dropdown (only ACTIVE vendors)
  const { data: vendorsData } = useQuery({
    queryKey: ['vendors-dropdown-active'],
    queryFn: () => vendorsApi.getDropdown(),
  });

  // Fetch products for dropdown
  const { data: productsData } = useQuery({
    queryKey: ['products-dropdown'],
    queryFn: () => productsApi.list({ size: 100 }),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: vendorProformasApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendor-proformas'] });
      toast.success('Proforma created successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create proforma'),
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: (id: string) => vendorProformasApi.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendor-proformas'] });
      toast.success('Proforma approved successfully');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to approve proforma'),
  });

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      vendorProformasApi.reject(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendor-proformas'] });
      toast.success('Proforma rejected');
      setIsRejectDialogOpen(false);
      setRejectReason('');
      setSelectedProforma(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to reject proforma'),
  });

  // Convert to PO mutation
  const convertMutation = useMutation({
    mutationFn: (id: string) => vendorProformasApi.convertToPO(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendor-proformas'] });
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      toast.success('Proforma converted to Purchase Order');
      setIsConvertDialogOpen(false);
      setSelectedProforma(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to convert to PO'),
  });

  const resetForm = () => {
    setFormData({
      vendor_id: '',
      proforma_number: '',
      proforma_date: new Date(),
      due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
      notes: '',
      items: [],
    });
    setIsCreateDialogOpen(false);
  };

  const handleAddItem = () => {
    setFormData({
      ...formData,
      items: [
        ...formData.items,
        {
          product_id: '',
          product_name: '',
          sku: '',
          quantity: 1,
          unit_price: 0,
          gst_rate: 18,
        },
      ],
    });
  };

  const handleRemoveItem = (index: number) => {
    setFormData({
      ...formData,
      items: formData.items.filter((_, i) => i !== index),
    });
  };

  const handleItemChange = (index: number, field: string, value: string | number) => {
    const updatedItems = [...formData.items];
    updatedItems[index] = { ...updatedItems[index], [field]: value };

    // If product changed, update product details
    if (field === 'product_id') {
      const product = products.find((p) => p.id === value);
      if (product) {
        updatedItems[index].product_name = product.name;
        updatedItems[index].sku = product.sku;
        updatedItems[index].unit_price = product.mrp || 0;
      }
    }

    setFormData({ ...formData, items: updatedItems });
  };

  const handleCreate = () => {
    if (!formData.vendor_id) {
      toast.error('Please select a vendor');
      return;
    }
    if (!formData.proforma_number.trim()) {
      toast.error('Proforma number is required');
      return;
    }
    if (formData.items.length === 0) {
      toast.error('Please add at least one item');
      return;
    }

    createMutation.mutate({
      vendor_id: formData.vendor_id,
      proforma_number: formData.proforma_number,
      proforma_date: format(formData.proforma_date, 'yyyy-MM-dd'),
      due_date: format(formData.due_date, 'yyyy-MM-dd'),
      notes: formData.notes || undefined,
      items: formData.items.map((item) => ({
        product_id: item.product_id,
        quantity: item.quantity,
        unit_price: item.unit_price,
        gst_rate: item.gst_rate,
      })),
    });
  };

  const handleView = (proforma: VendorProforma) => {
    setSelectedProforma(proforma);
    setIsViewSheetOpen(true);
  };

  const handleApprove = (proforma: VendorProforma) => {
    approveMutation.mutate(proforma.id);
  };

  const handleReject = (proforma: VendorProforma) => {
    setSelectedProforma(proforma);
    setIsRejectDialogOpen(true);
  };

  const handleConvert = (proforma: VendorProforma) => {
    setSelectedProforma(proforma);
    setIsConvertDialogOpen(true);
  };

  const confirmReject = () => {
    if (!selectedProforma) return;
    if (!rejectReason.trim()) {
      toast.error('Please provide a reason for rejection');
      return;
    }
    rejectMutation.mutate({ id: selectedProforma.id, reason: rejectReason });
  };

  const confirmConvert = () => {
    if (!selectedProforma) return;
    convertMutation.mutate(selectedProforma.id);
  };

  // Calculate totals for form
  const calculateTotals = () => {
    let subtotal = 0;
    let gstAmount = 0;

    formData.items.forEach((item) => {
      const amount = item.quantity * item.unit_price;
      subtotal += amount;
      gstAmount += amount * (item.gst_rate / 100);
    });

    return { subtotal, gstAmount, total: subtotal + gstAmount };
  };

  const vendors: Vendor[] = Array.isArray(vendorsData) ? vendorsData : [];
  const products: Product[] = productsData?.items ?? (Array.isArray(productsData) ? productsData : []);
  const proformas: VendorProforma[] = data?.items ?? (Array.isArray(data) ? data : []);
  const totals = calculateTotals();

  const columns: ColumnDef<VendorProforma>[] = [
    {
      accessorKey: 'proforma_number',
      header: 'Proforma #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="font-mono font-medium">{row.original.proforma_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'vendor',
      header: 'Vendor',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Building className="h-4 w-4 text-muted-foreground" />
          <div>
            <div className="font-medium">{row.original.vendor?.name || '-'}</div>
            <div className="text-xs text-muted-foreground">{row.original.vendor?.code}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'proforma_date',
      header: 'Proforma Date',
      cell: ({ row }) => (
        <span className="text-sm">
          {row.original.proforma_date
            ? format(new Date(row.original.proforma_date), 'dd MMM yyyy')
            : '-'}
        </span>
      ),
    },
    {
      accessorKey: 'due_date',
      header: 'Due Date',
      cell: ({ row }) => (
        <span className="text-sm">
          {row.original.due_date ? format(new Date(row.original.due_date), 'dd MMM yyyy') : '-'}
        </span>
      ),
    },
    {
      accessorKey: 'total_amount',
      header: 'Amount',
      cell: ({ row }) => (
        <span className="font-medium">{formatCurrency(row.original.total_amount)}</span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <span
          className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[row.original.status] || 'bg-gray-100'}`}
        >
          {row.original.status}
        </span>
      ),
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <ProformaActionsCell
          proforma={row.original}
          onView={handleView}
          onApprove={handleApprove}
          onReject={handleReject}
          onConvert={handleConvert}
        />
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vendor Proformas"
        description="Manage vendor proforma invoices and convert to purchase orders"
        actions={
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Proforma
          </Button>
        }
      />

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Vendor Proforma</DialogTitle>
            <DialogDescription>
              Create a new proforma invoice from a vendor
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {/* Vendor and Proforma Number */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Vendor *</Label>
                <Select
                  value={formData.vendor_id}
                  onValueChange={(value) => setFormData({ ...formData, vendor_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select vendor" />
                  </SelectTrigger>
                  <SelectContent>
                    {vendors.map((vendor: Vendor) => (
                      <SelectItem key={vendor.id} value={vendor.id}>
                        {vendor.name} ({vendor.code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Proforma Number *</Label>
                <Input
                  placeholder="PI-2024-001"
                  value={formData.proforma_number}
                  onChange={(e) =>
                    setFormData({ ...formData, proforma_number: e.target.value.toUpperCase() })
                  }
                />
              </div>
            </div>

            {/* Dates */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Proforma Date *</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        'w-full justify-start text-left font-normal',
                        !formData.proforma_date && 'text-muted-foreground'
                      )}
                    >
                      <Calendar className="mr-2 h-4 w-4" />
                      {formData.proforma_date
                        ? format(formData.proforma_date, 'PPP')
                        : 'Select date'}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0">
                    <CalendarComponent
                      mode="single"
                      selected={formData.proforma_date}
                      onSelect={(date) =>
                        date && setFormData({ ...formData, proforma_date: date })
                      }
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>
              <div className="space-y-2">
                <Label>Due Date *</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        'w-full justify-start text-left font-normal',
                        !formData.due_date && 'text-muted-foreground'
                      )}
                    >
                      <Calendar className="mr-2 h-4 w-4" />
                      {formData.due_date ? format(formData.due_date, 'PPP') : 'Select date'}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0">
                    <CalendarComponent
                      mode="single"
                      selected={formData.due_date}
                      onSelect={(date) => date && setFormData({ ...formData, due_date: date })}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>
            </div>

            {/* Items */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Line Items</Label>
                <Button type="button" variant="outline" size="sm" onClick={handleAddItem}>
                  <Plus className="mr-2 h-3 w-3" />
                  Add Item
                </Button>
              </div>

              {formData.items.length === 0 ? (
                <div className="rounded-lg border border-dashed p-8 text-center">
                  <p className="text-sm text-muted-foreground">
                    No items added yet. Click "Add Item" to add products.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {formData.items.map((item, index) => (
                    <div key={index} className="grid grid-cols-12 gap-2 items-end border rounded-lg p-3">
                      <div className="col-span-4">
                        <Label className="text-xs">Product</Label>
                        <Select
                          value={item.product_id}
                          onValueChange={(value) => handleItemChange(index, 'product_id', value)}
                        >
                          <SelectTrigger className="h-9">
                            <SelectValue placeholder="Select product" />
                          </SelectTrigger>
                          <SelectContent>
                            {products.map((product: Product) => (
                              <SelectItem key={product.id} value={product.id}>
                                {product.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="col-span-2">
                        <Label className="text-xs">Quantity</Label>
                        <Input
                          type="number"
                          min="1"
                          className="h-9"
                          value={item.quantity}
                          onChange={(e) =>
                            handleItemChange(index, 'quantity', parseInt(e.target.value) || 1)
                          }
                        />
                      </div>
                      <div className="col-span-2">
                        <Label className="text-xs">Unit Price</Label>
                        <Input
                          type="number"
                          min="0"
                          step="0.01"
                          className="h-9"
                          value={item.unit_price}
                          onChange={(e) =>
                            handleItemChange(index, 'unit_price', parseFloat(e.target.value) || 0)
                          }
                        />
                      </div>
                      <div className="col-span-1">
                        <Label className="text-xs">GST %</Label>
                        <Input
                          type="number"
                          min="0"
                          max="100"
                          className="h-9"
                          value={item.gst_rate}
                          onChange={(e) =>
                            handleItemChange(index, 'gst_rate', parseFloat(e.target.value) || 0)
                          }
                        />
                      </div>
                      <div className="col-span-2">
                        <Label className="text-xs">Amount</Label>
                        <div className="h-9 flex items-center px-3 bg-muted rounded-md text-sm">
                          {formatCurrency(item.quantity * item.unit_price)}
                        </div>
                      </div>
                      <div className="col-span-1">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-9 w-9 text-destructive"
                          onClick={() => handleRemoveItem(index)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}

                  {/* Totals */}
                  <div className="border-t pt-3 mt-3 space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>Subtotal:</span>
                      <span>{formatCurrency(totals.subtotal)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>GST:</span>
                      <span>{formatCurrency(totals.gstAmount)}</span>
                    </div>
                    <div className="flex justify-between font-medium">
                      <span>Total:</span>
                      <span>{formatCurrency(totals.total)}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label>Notes (Optional)</Label>
              <Textarea
                placeholder="Any additional notes..."
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={resetForm}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Proforma
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="DRAFT">Draft</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="APPROVED">Approved</SelectItem>
            <SelectItem value="REJECTED">Rejected</SelectItem>
            <SelectItem value="CONVERTED">Converted</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={proformas}
        searchKey="proforma_number"
        searchPlaceholder="Search proformas..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* View Details Sheet */}
      <Sheet open={isViewSheetOpen} onOpenChange={setIsViewSheetOpen}>
        <SheetContent className="sm:max-w-xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Proforma Details</SheetTitle>
            <SheetDescription>
              {selectedProforma?.proforma_number}
            </SheetDescription>
          </SheetHeader>
          {selectedProforma && (
            <div className="mt-6 space-y-6">
              {/* Header Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Vendor</p>
                  <p className="font-medium">{selectedProforma.vendor?.name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <span
                    className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${statusColors[selectedProforma.status]}`}
                  >
                    {selectedProforma.status}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Proforma Date</p>
                  <p className="font-medium">
                    {format(new Date(selectedProforma.proforma_date), 'dd MMM yyyy')}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Due Date</p>
                  <p className="font-medium">
                    {format(new Date(selectedProforma.due_date), 'dd MMM yyyy')}
                  </p>
                </div>
              </div>

              {/* Items */}
              <div>
                <p className="text-sm font-medium mb-2">Line Items</p>
                <div className="space-y-2">
                  {selectedProforma.items?.map((item, index) => (
                    <div key={index} className="flex justify-between items-center p-3 bg-muted rounded-lg">
                      <div>
                        <p className="font-medium">{item.product_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {item.quantity} x {formatCurrency(item.unit_price)}
                        </p>
                      </div>
                      <p className="font-medium">{formatCurrency(item.amount)}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Totals */}
              <div className="border-t pt-4 space-y-2">
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span>{formatCurrency(selectedProforma.subtotal)}</span>
                </div>
                <div className="flex justify-between">
                  <span>GST</span>
                  <span>{formatCurrency(selectedProforma.gst_amount)}</span>
                </div>
                <div className="flex justify-between font-bold text-lg">
                  <span>Total</span>
                  <span>{formatCurrency(selectedProforma.total_amount)}</span>
                </div>
              </div>

              {/* Notes */}
              {selectedProforma.notes && (
                <div>
                  <p className="text-sm font-medium mb-1">Notes</p>
                  <p className="text-sm text-muted-foreground">{selectedProforma.notes}</p>
                </div>
              )}

              {/* Actions */}
              {selectedProforma.status === 'PENDING' && (
                <div className="flex gap-2 pt-4">
                  <Button
                    className="flex-1"
                    onClick={() => {
                      handleApprove(selectedProforma);
                      setIsViewSheetOpen(false);
                    }}
                    disabled={approveMutation.isPending}
                  >
                    <CheckCircle className="mr-2 h-4 w-4" />
                    Approve
                  </Button>
                  <Button
                    variant="destructive"
                    className="flex-1"
                    onClick={() => {
                      setIsViewSheetOpen(false);
                      handleReject(selectedProforma);
                    }}
                  >
                    <XCircle className="mr-2 h-4 w-4" />
                    Reject
                  </Button>
                </div>
              )}

              {selectedProforma.status === 'APPROVED' && !selectedProforma.po_id && (
                <Button
                  className="w-full"
                  onClick={() => {
                    setIsViewSheetOpen(false);
                    handleConvert(selectedProforma);
                  }}
                >
                  <ArrowRight className="mr-2 h-4 w-4" />
                  Convert to Purchase Order
                </Button>
              )}

              {selectedProforma.po_id && (
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-700">
                    This proforma has been converted to PO
                  </p>
                </div>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Reject Dialog */}
      <AlertDialog open={isRejectDialogOpen} onOpenChange={setIsRejectDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject Proforma</AlertDialogTitle>
            <AlertDialogDescription>
              Please provide a reason for rejecting this proforma.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Reason for rejection..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setRejectReason('')}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmReject}
              disabled={rejectMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {rejectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Reject
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Convert to PO Dialog */}
      <AlertDialog open={isConvertDialogOpen} onOpenChange={setIsConvertDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Convert to Purchase Order</AlertDialogTitle>
            <AlertDialogDescription>
              This will create a new Purchase Order from this proforma. The proforma status will be
              marked as "Converted".
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmConvert} disabled={convertMutation.isPending}>
              {convertMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Convert to PO
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
