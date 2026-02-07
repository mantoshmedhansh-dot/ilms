'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, Download, FileText, Send, Loader2, Shield, XCircle, Printer, Trash2 } from 'lucide-react';
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
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { invoicesApi, customersApi } from '@/lib/api';
import { formatDate, formatCurrency } from '@/lib/utils';

interface Invoice {
  id: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  customer_id: string;
  customer?: { name: string; gstin?: string; address?: string };
  items: InvoiceItem[];
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  irn?: string;
  irn_generated_at?: string;
  status: 'DRAFT' | 'SENT' | 'PAID' | 'PARTIALLY_PAID' | 'OVERDUE' | 'CANCELLED';
  notes?: string;
  created_at: string;
}

interface InvoiceItem {
  id: string;
  product_id: string;
  product_name: string;
  description?: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  tax_amount: number;
  total: number;
}

interface Customer {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  gstin?: string;
}

export default function InvoicesPage() {
  const { permissions } = useAuth();
  const isSuperAdmin = permissions?.is_super_admin ?? false;
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [invoiceToDelete, setInvoiceToDelete] = useState<Invoice | null>(null);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [formData, setFormData] = useState({
    customer_id: '',
    invoice_date: new Date().toISOString().split('T')[0],
    due_date: '',
    notes: '',
    items: [{ product_id: '', product_name: '', quantity: 1, unit_price: 0, tax_rate: 18 }],
  });

  const { data, isLoading } = useQuery({
    queryKey: ['invoices', page, pageSize],
    queryFn: () => invoicesApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: customersData } = useQuery({
    queryKey: ['customers-list'],
    queryFn: () => customersApi.list({ size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: invoicesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('Invoice created successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create invoice'),
  });

  const generateIRNMutation = useMutation({
    mutationFn: invoicesApi.generateIRN,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('IRN generated successfully');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to generate IRN'),
  });

  const cancelIRNMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => invoicesApi.cancelIRN(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('IRN cancelled');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to cancel IRN'),
  });

  const deleteMutation = useMutation({
    mutationFn: invoicesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('Invoice deleted successfully');
      setIsDeleteOpen(false);
      setInvoiceToDelete(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete invoice'),
  });

  const resetForm = () => {
    setFormData({
      customer_id: '',
      invoice_date: new Date().toISOString().split('T')[0],
      due_date: '',
      notes: '',
      items: [{ product_id: '', product_name: '', quantity: 1, unit_price: 0, tax_rate: 18 }],
    });
    setIsDialogOpen(false);
  };

  const handleViewInvoice = async (invoice: Invoice) => {
    try {
      const detail = await invoicesApi.getById(invoice.id);
      setSelectedInvoice(detail);
      setIsViewOpen(true);
    } catch {
      toast.error('Failed to load invoice details');
    }
  };

  const handleDownload = async (invoice: Invoice) => {
    try {
      // Fetch HTML with auth token, then open in new tab
      const htmlContent = await invoicesApi.download(invoice.id);
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => window.URL.revokeObjectURL(url);
      }
      toast.success('Opening invoice for download/print');
    } catch {
      toast.error('Failed to download invoice');
    }
  };

  const handlePrint = async (invoice: Invoice) => {
    try {
      // Fetch HTML with auth token, then open in new tab for printing
      const htmlContent = await invoicesApi.download(invoice.id);
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => {
          window.URL.revokeObjectURL(url);
          printWindow.print();
        };
      }
    } catch {
      toast.error('Failed to print invoice');
    }
  };

  const handleSubmit = () => {
    if (!formData.customer_id || !formData.invoice_date || !formData.due_date) {
      toast.error('Customer, invoice date, and due date are required');
      return;
    }

    createMutation.mutate({
      customer_id: formData.customer_id,
      invoice_date: formData.invoice_date,
      due_date: formData.due_date,
      items: formData.items.map(item => ({
        product_id: item.product_id || 'manual',
        quantity: item.quantity,
        unit_price: item.unit_price,
        tax_rate: item.tax_rate,
      })),
      notes: formData.notes || undefined,
    });
  };

  const addItem = () => {
    setFormData({
      ...formData,
      items: [...formData.items, { product_id: '', product_name: '', quantity: 1, unit_price: 0, tax_rate: 18 }],
    });
  };

  const updateItem = (index: number, field: string, value: string | number) => {
    const newItems = [...formData.items];
    newItems[index] = { ...newItems[index], [field]: value };
    setFormData({ ...formData, items: newItems });
  };

  const removeItem = (index: number) => {
    if (formData.items.length > 1) {
      setFormData({
        ...formData,
        items: formData.items.filter((_, i) => i !== index),
      });
    }
  };

  const columns: ColumnDef<Invoice>[] = [
    {
      accessorKey: 'invoice_number',
      header: 'Invoice #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.original.invoice_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'customer',
      header: 'Customer',
      cell: ({ row }) => (
        <div>
          <div className="text-sm font-medium">{row.original.customer?.name || 'N/A'}</div>
          {row.original.customer?.gstin && (
            <div className="text-xs text-muted-foreground font-mono">{row.original.customer.gstin}</div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'invoice_date',
      header: 'Invoice Date',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {formatDate(row.original.invoice_date)}
        </span>
      ),
    },
    {
      accessorKey: 'due_date',
      header: 'Due Date',
      cell: ({ row }) => {
        const isOverdue = new Date(row.original.due_date) < new Date() && row.original.status !== 'PAID';
        return (
          <span className={`text-sm ${isOverdue ? 'text-red-600 font-medium' : 'text-muted-foreground'}`}>
            {formatDate(row.original.due_date)}
          </span>
        );
      },
    },
    {
      accessorKey: 'total_amount',
      header: 'Amount',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{formatCurrency(row.original.total_amount)}</div>
          {row.original.paid_amount > 0 && row.original.paid_amount < row.original.total_amount && (
            <div className="text-xs text-muted-foreground">
              Paid: {formatCurrency(row.original.paid_amount)}
            </div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'irn',
      header: 'IRN',
      cell: ({ row }) => (
        row.original.irn ? (
          <div className="flex items-center gap-1">
            <Shield className="h-3 w-3 text-green-600" />
            <span className="text-xs text-green-600">E-Invoice</span>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">-</span>
        )
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
            <DropdownMenuItem onClick={() => handleViewInvoice(row.original)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleDownload(row.original)}>
              <Download className="mr-2 h-4 w-4" />
              Download
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handlePrint(row.original)}>
              <Printer className="mr-2 h-4 w-4" />
              Print
            </DropdownMenuItem>
            {row.original.status === 'DRAFT' && (
              <DropdownMenuItem>
                <Send className="mr-2 h-4 w-4" />
                Send to Customer
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            {!row.original.irn && row.original.status !== 'CANCELLED' && (
              <DropdownMenuItem
                onClick={() => generateIRNMutation.mutate(row.original.id)}
                disabled={generateIRNMutation.isPending}
              >
                <Shield className="mr-2 h-4 w-4" />
                Generate IRN
              </DropdownMenuItem>
            )}
            {row.original.irn && (
              <DropdownMenuItem
                onClick={() => cancelIRNMutation.mutate({ id: row.original.id, reason: 'Cancelled' })}
                className="text-destructive"
              >
                <XCircle className="mr-2 h-4 w-4" />
                Cancel IRN
              </DropdownMenuItem>
            )}
            {isSuperAdmin && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => { setInvoiceToDelete(row.original); setIsDeleteOpen(true); }}
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

  const customers = customersData?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Invoices"
        description="Manage sales invoices and billing"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Invoice
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Invoice</DialogTitle>
            <DialogDescription>Create a new sales invoice</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Customer *</Label>
              <Select
                value={formData.customer_id || 'select'}
                onValueChange={(value) => setFormData({ ...formData, customer_id: value === 'select' ? '' : value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select customer" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="select" disabled>Select customer</SelectItem>
                  {customers
                    .filter((c: Customer) => c.id && c.id.trim() !== '')
                    .map((c: Customer) => (
                      <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Invoice Date *</Label>
                <Input
                  type="date"
                  value={formData.invoice_date}
                  onChange={(e) => setFormData({ ...formData, invoice_date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Due Date *</Label>
                <Input
                  type="date"
                  value={formData.due_date}
                  onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <Label>Items</Label>
                <Button type="button" variant="outline" size="sm" onClick={addItem}>
                  <Plus className="h-3 w-3 mr-1" /> Add Item
                </Button>
              </div>
              {formData.items.map((item, index) => (
                <div key={index} className="grid grid-cols-12 gap-2 items-end p-2 border rounded-md">
                  <div className="col-span-4 space-y-1">
                    <Label className="text-xs">Description</Label>
                    <Input
                      placeholder="Product/Service"
                      value={item.product_name}
                      onChange={(e) => updateItem(index, 'product_name', e.target.value)}
                    />
                  </div>
                  <div className="col-span-2 space-y-1">
                    <Label className="text-xs">Qty</Label>
                    <Input
                      type="number"
                      min="1"
                      value={item.quantity}
                      onChange={(e) => updateItem(index, 'quantity', parseInt(e.target.value) || 1)}
                    />
                  </div>
                  <div className="col-span-2 space-y-1">
                    <Label className="text-xs">Price</Label>
                    <Input
                      type="number"
                      min="0"
                      value={item.unit_price}
                      onChange={(e) => updateItem(index, 'unit_price', parseFloat(e.target.value) || 0)}
                    />
                  </div>
                  <div className="col-span-2 space-y-1">
                    <Label className="text-xs">Tax %</Label>
                    <Input
                      type="number"
                      min="0"
                      value={item.tax_rate}
                      onChange={(e) => updateItem(index, 'tax_rate', parseFloat(e.target.value) || 0)}
                    />
                  </div>
                  <div className="col-span-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeItem(index)}
                      disabled={formData.items.length === 1}
                    >
                      <XCircle className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                placeholder="Additional notes (optional)"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={resetForm}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Invoice
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="invoice_number"
        searchPlaceholder="Search invoices..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Invoice Detail Sheet */}
      <Sheet open={isViewOpen} onOpenChange={setIsViewOpen}>
        <SheetContent className="w-[600px] sm:max-w-xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Invoice {selectedInvoice?.invoice_number}</SheetTitle>
            <SheetDescription>Invoice details and line items</SheetDescription>
          </SheetHeader>
          {selectedInvoice && (
            <div className="mt-6 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Customer</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-medium">{selectedInvoice.customer?.name}</div>
                  {selectedInvoice.customer?.gstin && (
                    <div className="text-sm text-muted-foreground">GSTIN: {selectedInvoice.customer.gstin}</div>
                  )}
                </CardContent>
              </Card>

              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Invoice Date</div>
                    <div className="font-medium">{formatDate(selectedInvoice.invoice_date)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Due Date</div>
                    <div className="font-medium">{formatDate(selectedInvoice.due_date)}</div>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Items</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {selectedInvoice.items?.map((item, idx) => (
                      <div key={idx} className="flex justify-between py-2 border-b last:border-0">
                        <div>
                          <div className="font-medium">{item.product_name}</div>
                          <div className="text-sm text-muted-foreground">
                            {item.quantity} x {formatCurrency(item.unit_price)} @ {item.tax_rate}%
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">{formatCurrency(item.total)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Subtotal</span>
                    <span>{formatCurrency(selectedInvoice.subtotal)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Tax</span>
                    <span>{formatCurrency(selectedInvoice.tax_amount)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-lg border-t pt-2">
                    <span>Total</span>
                    <span>{formatCurrency(selectedInvoice.total_amount)}</span>
                  </div>
                  {selectedInvoice.paid_amount > 0 && (
                    <>
                      <div className="flex justify-between text-green-600">
                        <span>Paid</span>
                        <span>{formatCurrency(selectedInvoice.paid_amount)}</span>
                      </div>
                      <div className="flex justify-between font-medium">
                        <span>Balance</span>
                        <span>{formatCurrency(selectedInvoice.total_amount - selectedInvoice.paid_amount)}</span>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>

              {selectedInvoice.irn && (
                <Card className="bg-green-50">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2">
                      <Shield className="h-5 w-5 text-green-600" />
                      <div>
                        <div className="font-medium text-green-800">E-Invoice Generated</div>
                        <div className="text-xs text-green-600 font-mono">{selectedInvoice.irn}</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              <div className="flex gap-2">
                <Button className="flex-1" onClick={() => handleDownload(selectedInvoice)}>
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>
                {!selectedInvoice.irn && (
                  <Button
                    variant="outline"
                    onClick={() => generateIRNMutation.mutate(selectedInvoice.id)}
                    disabled={generateIRNMutation.isPending}
                  >
                    <Shield className="mr-2 h-4 w-4" />
                    Generate IRN
                  </Button>
                )}
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Delete Invoice Confirmation */}
      <AlertDialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Invoice</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete invoice <strong>{invoiceToDelete?.invoice_number}</strong>?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => invoiceToDelete && deleteMutation.mutate(invoiceToDelete.id)}
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
