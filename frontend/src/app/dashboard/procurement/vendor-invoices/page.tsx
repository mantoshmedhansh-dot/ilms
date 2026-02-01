'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, FileText, CheckCircle, XCircle, Upload, Download, AlertTriangle, Clock, DollarSign, FileCheck, Loader2 } from 'lucide-react';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency, formatDate } from '@/lib/utils';

interface VendorInvoice {
  id: string;
  invoice_number: string;
  vendor_id: string;
  vendor_name: string;
  vendor_code: string;
  po_number?: string;
  grn_number?: string;
  invoice_date: string;
  due_date: string;
  subtotal: number;
  gst_amount: number;
  tds_amount: number;
  total_amount: number;
  status: 'PENDING' | 'UNDER_REVIEW' | 'MATCHED' | 'PARTIAL_MATCH' | 'MISMATCH' | 'APPROVED' | 'REJECTED' | 'PAID';
  match_status: 'NOT_MATCHED' | 'MATCHED' | 'PARTIAL' | 'MISMATCH';
  payment_status: 'UNPAID' | 'PARTIAL' | 'PAID';
  days_until_due: number;
  created_at: string;
}

interface InvoiceStats {
  total_invoices: number;
  pending_review: number;
  matched: number;
  mismatch: number;
  overdue: number;
  total_pending_amount: number;
  total_overdue_amount: number;
}

// Vendor from master data
interface VendorBrief {
  id: string;
  vendor_code: string;
  name: string;
  gstin?: string;
  vendor_type?: string;
}

// Purchase Order from master data (matches POBrief response schema)
interface PurchaseOrderBrief {
  id: string;
  po_number: string;
  vendor_name?: string;
  grand_total: number;
  status: string;
  po_date?: string;
  vendor?: {
    id: string;
    name: string;
    code?: string;
  };
}

// Vendors API - fetches from master Vendors table
const vendorsApi = {
  getDropdown: async (): Promise<VendorBrief[]> => {
    try {
      const { data } = await apiClient.get('/vendors/dropdown', { params: { active_only: true } });
      return data || [];
    } catch {
      return [];
    }
  },
};

// Purchase Orders API - fetches from master PO table
const purchaseOrdersApi = {
  list: async (params?: { vendor_id?: string; status?: string }): Promise<{ items: PurchaseOrderBrief[] }> => {
    try {
      const { data } = await apiClient.get('/purchase/orders', {
        params: {
          ...params,
          limit: 100, // Get enough POs for dropdown
        }
      });
      return data || { items: [] };
    } catch (error) {
      console.error('Failed to fetch POs:', error);
      return { items: [] };
    }
  },
};

const vendorInvoicesApi = {
  list: async (params?: { page?: number; size?: number; status?: string; payment_status?: string }) => {
    try {
      const { data } = await apiClient.get('/vendor-invoices', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<InvoiceStats> => {
    try {
      const { data } = await apiClient.get('/vendor-invoices/stats');
      return data;
    } catch {
      return { total_invoices: 0, pending_review: 0, matched: 0, mismatch: 0, overdue: 0, total_pending_amount: 0, total_overdue_amount: 0 };
    }
  },
  create: async (invoiceData: {
    vendor_id: string;
    invoice_number: string;
    invoice_date: string;
    purchase_order_id?: string;
    subtotal: number;
    taxable_amount: number;
    cgst_amount: number;
    sgst_amount: number;
    grand_total: number;
    due_date: string;
  }) => {
    const { data } = await apiClient.post('/vendor-invoices', invoiceData);
    return data;
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post(`/vendor-invoices/${id}/approve`);
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/vendor-invoices/${id}/reject`, { reason });
    return data;
  },
  initiateMatch: async (id: string) => {
    const { data } = await apiClient.post(`/vendor-invoices/${id}/three-way-match`);
    return data;
  },
};

const statusColors: Record<string, string> = {
  PENDING: 'bg-gray-100 text-gray-800',
  UNDER_REVIEW: 'bg-blue-100 text-blue-800',
  MATCHED: 'bg-green-100 text-green-800',
  PARTIAL_MATCH: 'bg-yellow-100 text-yellow-800',
  MISMATCH: 'bg-red-100 text-red-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
  PAID: 'bg-purple-100 text-purple-800',
};

const matchStatusColors: Record<string, string> = {
  NOT_MATCHED: 'bg-gray-100 text-gray-600',
  MATCHED: 'bg-green-100 text-green-700',
  PARTIAL: 'bg-yellow-100 text-yellow-700',
  MISMATCH: 'bg-red-100 text-red-700',
};

const paymentStatusColors: Record<string, string> = {
  UNPAID: 'bg-red-100 text-red-700',
  PARTIAL: 'bg-yellow-100 text-yellow-700',
  PAID: 'bg-green-100 text-green-700',
};

export default function VendorInvoicesPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [paymentFilter, setPaymentFilter] = useState<string>('all');
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);

  // Upload form state
  const [selectedVendorId, setSelectedVendorId] = useState<string>('');
  const [selectedPOId, setSelectedPOId] = useState<string>('');
  const [invoiceNumber, setInvoiceNumber] = useState<string>('');
  const [invoiceDate, setInvoiceDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);

  const queryClient = useQueryClient();

  // Fetch vendors from master Vendors table
  const { data: vendorsData, isLoading: vendorsLoading } = useQuery({
    queryKey: ['vendors-dropdown'],
    queryFn: vendorsApi.getDropdown,
  });
  const vendors = Array.isArray(vendorsData) ? vendorsData : [];

  // Fetch POs - filtered by selected vendor
  const { data: posData, isLoading: posLoading } = useQuery({
    queryKey: ['purchase-orders-dropdown', selectedVendorId],
    queryFn: () => purchaseOrdersApi.list({
      vendor_id: selectedVendorId || undefined,
      status: 'APPROVED', // Only show approved POs for linking
    }),
    enabled: true, // Always fetch, but filter by vendor if selected
  });

  // Filter POs by selected vendor (if any)
  const posItems = Array.isArray(posData?.items) ? posData.items : [];
  const availablePOs = selectedVendorId
    ? posItems.filter(po => po.vendor?.id === selectedVendorId)
    : posItems;

  // Reset form when dialog closes
  useEffect(() => {
    if (!isUploadDialogOpen) {
      setSelectedVendorId('');
      setSelectedPOId('');
      setInvoiceNumber('');
      setInvoiceDate(new Date().toISOString().split('T')[0]);
      setInvoiceFile(null);
    }
  }, [isUploadDialogOpen]);

  // Reset PO selection when vendor changes
  useEffect(() => {
    setSelectedPOId('');
  }, [selectedVendorId]);

  const { data, isLoading } = useQuery({
    queryKey: ['vendor-invoices', page, pageSize, statusFilter, paymentFilter],
    queryFn: () => vendorInvoicesApi.list({
      page: page + 1,
      size: pageSize,
      status: statusFilter !== 'all' ? statusFilter : undefined,
      payment_status: paymentFilter !== 'all' ? paymentFilter : undefined,
    }),
  });

  const { data: stats } = useQuery({
    queryKey: ['vendor-invoices-stats'],
    queryFn: vendorInvoicesApi.getStats,
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => vendorInvoicesApi.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendor-invoices'] });
      toast.success('Invoice approved');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to approve invoice');
    },
  });

  const matchMutation = useMutation({
    mutationFn: (id: string) => vendorInvoicesApi.initiateMatch(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendor-invoices'] });
      toast.success('3-Way match initiated');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to initiate 3-way match');
    },
  });

  const createInvoiceMutation = useMutation({
    mutationFn: vendorInvoicesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendor-invoices'] });
      queryClient.invalidateQueries({ queryKey: ['vendor-invoices-stats'] });
      setIsUploadDialogOpen(false);
      toast.success('Vendor invoice created successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create vendor invoice');
    },
  });

  const handleUploadSubmit = () => {
    if (!selectedVendorId) {
      toast.error('Please select a vendor');
      return;
    }
    if (!invoiceNumber.trim()) {
      toast.error('Please enter invoice number');
      return;
    }
    if (!invoiceDate) {
      toast.error('Please enter invoice date');
      return;
    }

    // Calculate due date (30 days from invoice date)
    const dueDate = new Date(invoiceDate);
    dueDate.setDate(dueDate.getDate() + 30);

    createInvoiceMutation.mutate({
      vendor_id: selectedVendorId,
      invoice_number: invoiceNumber,
      invoice_date: invoiceDate,
      purchase_order_id: selectedPOId || undefined,
      subtotal: 0, // These would be entered in a full form or extracted from file
      taxable_amount: 0,
      cgst_amount: 0,
      sgst_amount: 0,
      grand_total: 0,
      due_date: dueDate.toISOString().split('T')[0],
    });
  };

  const columns: ColumnDef<VendorInvoice>[] = [
    {
      accessorKey: 'invoice_number',
      header: 'Invoice',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <FileText className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="font-mono font-medium">{row.original.invoice_number}</div>
            <div className="text-sm text-muted-foreground">
              {formatDate(row.original.invoice_date)}
            </div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'vendor_name',
      header: 'Vendor',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.vendor_name}</div>
          <div className="text-sm text-muted-foreground">{row.original.vendor_code}</div>
        </div>
      ),
    },
    {
      accessorKey: 'references',
      header: 'PO / GRN',
      cell: ({ row }) => (
        <div className="text-sm">
          <div>{row.original.po_number || '-'}</div>
          <div className="text-muted-foreground">{row.original.grn_number || '-'}</div>
        </div>
      ),
    },
    {
      accessorKey: 'total_amount',
      header: 'Amount',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{formatCurrency(row.original.total_amount)}</div>
          <div className="text-xs text-muted-foreground">
            GST: {formatCurrency(row.original.gst_amount)}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'due_date',
      header: 'Due Date',
      cell: ({ row }) => {
        const isOverdue = row.original.days_until_due < 0;
        return (
          <div className={`flex items-center gap-2 ${isOverdue ? 'text-red-600' : ''}`}>
            {isOverdue && <AlertTriangle className="h-4 w-4" />}
            <div>
              <div className="text-sm">{formatDate(row.original.due_date)}</div>
              <div className="text-xs text-muted-foreground">
                {isOverdue
                  ? `Overdue by ${Math.abs(row.original.days_until_due)} days`
                  : `${row.original.days_until_due} days left`}
              </div>
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'match_status',
      header: 'Match Status',
      cell: ({ row }) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${matchStatusColors[row.original.match_status] ?? 'bg-gray-100 text-gray-800'}`}>
          {row.original.match_status?.replace('_', ' ') ?? '-'}
        </span>
      ),
    },
    {
      accessorKey: 'payment_status',
      header: 'Payment',
      cell: ({ row }) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${paymentStatusColors[row.original.payment_status]}`}>
          {row.original.payment_status}
        </span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[row.original.status] ?? 'bg-gray-100 text-gray-800'}`}>
          {row.original.status?.replace('_', ' ') ?? '-'}
        </span>
      ),
    },
    {
      id: 'actions',
      cell: ({ row }) => {
        const invoice = row.original;
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
              <DropdownMenuItem onClick={() => toast.success(`Viewing invoice ${invoice.invoice_number}`)}>
                <Eye className="mr-2 h-4 w-4" />
                View Details
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => toast.success(`Downloading invoice ${invoice.invoice_number}`)}>
                <Download className="mr-2 h-4 w-4" />
                Download Invoice
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {invoice.match_status === 'NOT_MATCHED' && (
                <DropdownMenuItem onClick={() => matchMutation.mutate(invoice.id)}>
                  <FileCheck className="mr-2 h-4 w-4" />
                  Initiate 3-Way Match
                </DropdownMenuItem>
              )}
              {invoice.match_status === 'MATCHED' && invoice.status !== 'APPROVED' && (
                <DropdownMenuItem onClick={() => approveMutation.mutate(invoice.id)}>
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Approve for Payment
                </DropdownMenuItem>
              )}
              {invoice.match_status === 'MISMATCH' && (
                <DropdownMenuItem className="text-orange-600" onClick={() => toast.success('Opening discrepancy resolution')}>
                  <AlertTriangle className="mr-2 h-4 w-4" />
                  Resolve Discrepancy
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vendor Invoices"
        description="Manage vendor invoices and payment processing"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <a href="/dashboard/procurement/three-way-match">
                <FileCheck className="mr-2 h-4 w-4" />
                3-Way Match
              </a>
            </Button>
            <Dialog open={isUploadDialogOpen} onOpenChange={setIsUploadDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Invoice
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Upload Vendor Invoice</DialogTitle>
                  <DialogDescription>
                    Upload an invoice PDF or image for processing
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Vendor *</label>
                    <Select value={selectedVendorId} onValueChange={setSelectedVendorId}>
                      <SelectTrigger>
                        <SelectValue placeholder={vendorsLoading ? "Loading vendors..." : "Select vendor"} />
                      </SelectTrigger>
                      <SelectContent>
                        {vendorsLoading ? (
                          <div className="flex items-center justify-center py-4">
                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            Loading...
                          </div>
                        ) : vendors.length === 0 ? (
                          <div className="py-4 text-center text-sm text-muted-foreground">
                            No active vendors found
                          </div>
                        ) : (
                          vendors.map((vendor) => (
                            <SelectItem key={vendor.id} value={vendor.id}>
                              <div className="flex flex-col">
                                <span>{vendor.name}</span>
                                <span className="text-xs text-muted-foreground">{vendor.vendor_code}</span>
                              </div>
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Invoice File</label>
                    <div className="border-2 border-dashed rounded-lg p-6 text-center">
                      <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                      <p className="text-sm text-muted-foreground">
                        Drag & drop or click to upload
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        PDF, JPG, PNG (max 10MB)
                      </p>
                      <Input
                        type="file"
                        className="mt-2"
                        accept=".pdf,.jpg,.jpeg,.png"
                        onChange={(e) => setInvoiceFile(e.target.files?.[0] || null)}
                      />
                      {invoiceFile && (
                        <p className="text-xs text-green-600 mt-1">
                          Selected: {invoiceFile.name}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Invoice Number *</label>
                      <Input
                        placeholder="INV-001"
                        value={invoiceNumber}
                        onChange={(e) => setInvoiceNumber(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Invoice Date *</label>
                      <Input
                        type="date"
                        value={invoiceDate}
                        onChange={(e) => setInvoiceDate(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Link to PO (Optional)</label>
                    <Select
                      value={selectedPOId}
                      onValueChange={setSelectedPOId}
                      disabled={!selectedVendorId}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={
                          !selectedVendorId
                            ? "Select vendor first"
                            : posLoading
                              ? "Loading POs..."
                              : "Select PO"
                        } />
                      </SelectTrigger>
                      <SelectContent>
                        {posLoading ? (
                          <div className="flex items-center justify-center py-4">
                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            Loading...
                          </div>
                        ) : availablePOs.length === 0 ? (
                          <div className="py-4 text-center text-sm text-muted-foreground">
                            {selectedVendorId
                              ? "No approved POs for this vendor"
                              : "Select a vendor to see POs"}
                          </div>
                        ) : (
                          availablePOs.map((po) => (
                            <SelectItem key={po.id} value={po.id}>
                              <div className="flex flex-col">
                                <span>{po.po_number}</span>
                                <span className="text-xs text-muted-foreground">
                                  {formatCurrency(po.grand_total)} • {po.status}
                                </span>
                              </div>
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                    {selectedVendorId && availablePOs.length > 0 && (
                      <p className="text-xs text-muted-foreground">
                        {availablePOs.length} approved PO(s) available for this vendor
                      </p>
                    )}
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsUploadDialogOpen(false)}>Cancel</Button>
                  <Button onClick={handleUploadSubmit} disabled={createInvoiceMutation.isPending}>
                    {createInvoiceMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      'Upload & Process'
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-7">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Invoices</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_invoices || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Review</CardTitle>
            <Clock className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.pending_review || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Matched</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.matched || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mismatch</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.mismatch || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overdue</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.overdue || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Amount</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">{formatCurrency(stats?.total_pending_amount || 0)}</div>
          </CardContent>
        </Card>
        <Card className="border-red-200 bg-red-50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-red-800">Overdue Amount</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-red-600">{formatCurrency(stats?.total_overdue_amount || 0)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="UNDER_REVIEW">Under Review</SelectItem>
            <SelectItem value="MATCHED">Matched</SelectItem>
            <SelectItem value="MISMATCH">Mismatch</SelectItem>
            <SelectItem value="APPROVED">Approved</SelectItem>
            <SelectItem value="PAID">Paid</SelectItem>
          </SelectContent>
        </Select>
        <Select value={paymentFilter} onValueChange={setPaymentFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Payment status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Payments</SelectItem>
            <SelectItem value="UNPAID">Unpaid</SelectItem>
            <SelectItem value="PARTIAL">Partial</SelectItem>
            <SelectItem value="PAID">Paid</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={Array.isArray(data?.items) ? data.items : []}
        searchKey="invoice_number"
        searchPlaceholder="Search invoice number..."
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
