'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, Receipt, Loader2, CreditCard, Banknote, Building } from 'lucide-react';
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { receiptsApi, customersApi, invoicesApi } from '@/lib/api';
import { formatDate, formatCurrency } from '@/lib/utils';

interface PaymentReceipt {
  id: string;
  receipt_number: string;
  receipt_date: string;
  customer_id: string;
  customer?: { name: string; email?: string; phone?: string };
  invoice_id?: string;
  invoice?: { invoice_number: string };
  amount: number;
  payment_mode: string;
  reference_number?: string;
  bank_name?: string;
  notes?: string;
  created_at: string;
}

interface Customer {
  id: string;
  name: string;
}

interface Invoice {
  id: string;
  invoice_number: string;
  customer_id: string;
  total_amount: number;
  paid_amount: number;
}

const paymentModes = [
  { label: 'Cash', value: 'CASH', icon: Banknote },
  { label: 'UPI', value: 'UPI', icon: CreditCard },
  { label: 'Card', value: 'CARD', icon: CreditCard },
  { label: 'Bank Transfer', value: 'BANK_TRANSFER', icon: Building },
  { label: 'Cheque', value: 'CHEQUE', icon: Receipt },
];

export default function PaymentReceiptsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [selectedReceipt, setSelectedReceipt] = useState<PaymentReceipt | null>(null);
  const [formData, setFormData] = useState({
    customer_id: '',
    invoice_id: '',
    amount: 0,
    payment_mode: 'CASH',
    reference_number: '',
    payment_date: new Date().toISOString().split('T')[0],
    notes: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['receipts', page, pageSize],
    queryFn: () => receiptsApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: customersData } = useQuery({
    queryKey: ['customers-list'],
    queryFn: () => customersApi.list({ size: 100 }),
  });

  const { data: invoicesData } = useQuery({
    queryKey: ['invoices-for-receipt', formData.customer_id],
    queryFn: () => invoicesApi.list({ customer_id: formData.customer_id, size: 50 }),
    enabled: !!formData.customer_id,
  });

  const createMutation = useMutation({
    mutationFn: receiptsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['receipts'] });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('Payment receipt created successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create receipt'),
  });

  const resetForm = () => {
    setFormData({
      customer_id: '',
      invoice_id: '',
      amount: 0,
      payment_mode: 'CASH',
      reference_number: '',
      payment_date: new Date().toISOString().split('T')[0],
      notes: '',
    });
    setIsDialogOpen(false);
  };

  const handleViewReceipt = async (receipt: PaymentReceipt) => {
    try {
      const detail = await receiptsApi.getById(receipt.id);
      setSelectedReceipt(detail);
      setIsViewOpen(true);
    } catch {
      setSelectedReceipt(receipt);
      setIsViewOpen(true);
    }
  };

  const handleSubmit = () => {
    if (!formData.customer_id || !formData.amount || !formData.payment_date) {
      toast.error('Customer, amount, and date are required');
      return;
    }

    createMutation.mutate({
      customer_id: formData.customer_id,
      invoice_id: formData.invoice_id || undefined,
      amount: formData.amount,
      payment_mode: formData.payment_mode,
      reference_number: formData.reference_number || undefined,
      payment_date: formData.payment_date,
      notes: formData.notes || undefined,
    });
  };

  const getPaymentModeIcon = (mode: string) => {
    const found = paymentModes.find(m => m.value === mode);
    const Icon = found?.icon || Receipt;
    return <Icon className="h-4 w-4" />;
  };

  const columns: ColumnDef<PaymentReceipt>[] = [
    {
      accessorKey: 'receipt_number',
      header: 'Receipt #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Receipt className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.original.receipt_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'customer',
      header: 'Customer',
      cell: ({ row }) => (
        <span className="text-sm">{row.original.customer?.name || 'N/A'}</span>
      ),
    },
    {
      accessorKey: 'invoice',
      header: 'Invoice',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground font-mono">
          {row.original.invoice?.invoice_number || '-'}
        </span>
      ),
    },
    {
      accessorKey: 'receipt_date',
      header: 'Date',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {formatDate(row.original.receipt_date)}
        </span>
      ),
    },
    {
      accessorKey: 'payment_mode',
      header: 'Mode',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          {getPaymentModeIcon(row.original.payment_mode)}
          <span className="text-sm capitalize">{row.original.payment_mode?.replace(/_/g, ' ')?.toLowerCase() ?? '-'}</span>
        </div>
      ),
    },
    {
      accessorKey: 'amount',
      header: 'Amount',
      cell: ({ row }) => (
        <span className="font-medium text-green-600">
          {formatCurrency(row.original.amount)}
        </span>
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
            <DropdownMenuItem onClick={() => handleViewReceipt(row.original)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const customers = customersData?.items ?? [];
  const invoices = invoicesData?.items?.filter((inv: Invoice) => inv.total_amount > inv.paid_amount) ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Payment Receipts"
        description="Record and manage payment receipts from customers"
        actions={
          <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
            <DialogTrigger asChild>
              <Button onClick={() => setIsDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Record Payment
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Record Payment</DialogTitle>
                <DialogDescription>Record a new payment receipt</DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label>Customer *</Label>
                  <Select
                    value={formData.customer_id || 'select'}
                    onValueChange={(value) => setFormData({ ...formData, customer_id: value === 'select' ? '' : value, invoice_id: '' })}
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

                {formData.customer_id && invoices.length > 0 && (
                  <div className="space-y-2">
                    <Label>Against Invoice (Optional)</Label>
                    <Select
                      value={formData.invoice_id || 'none'}
                      onValueChange={(value) => {
                        const inv = invoices.find((i: Invoice) => i.id === value);
                        setFormData({
                          ...formData,
                          invoice_id: value === 'none' ? '' : value,
                          amount: inv ? inv.total_amount - inv.paid_amount : formData.amount,
                        });
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select invoice" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">No specific invoice</SelectItem>
                        {invoices
                          .filter((inv: Invoice) => inv.id && inv.id.trim() !== '')
                          .map((inv: Invoice) => (
                            <SelectItem key={inv.id} value={inv.id}>
                              {inv.invoice_number} - Due: {formatCurrency(inv.total_amount - inv.paid_amount)}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Amount *</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                      value={formData.amount || ''}
                      onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Date *</Label>
                    <Input
                      type="date"
                      value={formData.payment_date}
                      onChange={(e) => setFormData({ ...formData, payment_date: e.target.value })}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Payment Mode</Label>
                  <Select
                    value={formData.payment_mode}
                    onValueChange={(value) => setFormData({ ...formData, payment_mode: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {paymentModes.map((mode) => (
                        <SelectItem key={mode.value} value={mode.value}>
                          <div className="flex items-center gap-2">
                            <mode.icon className="h-4 w-4" />
                            {mode.label}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {formData.payment_mode !== 'CASH' && (
                  <div className="space-y-2">
                    <Label>Reference / Transaction ID</Label>
                    <Input
                      placeholder="Transaction reference number"
                      value={formData.reference_number}
                      onChange={(e) => setFormData({ ...formData, reference_number: e.target.value })}
                    />
                  </div>
                )}

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
                  Record Payment
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="receipt_number"
        searchPlaceholder="Search receipts..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Receipt Detail Sheet */}
      <Sheet open={isViewOpen} onOpenChange={setIsViewOpen}>
        <SheetContent className="w-[500px] sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Receipt {selectedReceipt?.receipt_number}</SheetTitle>
            <SheetDescription>Payment receipt details</SheetDescription>
          </SheetHeader>
          {selectedReceipt && (
            <div className="mt-6 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Customer</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-medium">{selectedReceipt.customer?.name}</div>
                  {selectedReceipt.customer?.phone && (
                    <div className="text-sm text-muted-foreground">{selectedReceipt.customer.phone}</div>
                  )}
                </CardContent>
              </Card>

              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Date</div>
                    <div className="font-medium">{formatDate(selectedReceipt.receipt_date)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Mode</div>
                    <div className="flex items-center gap-1 font-medium">
                      {getPaymentModeIcon(selectedReceipt.payment_mode)}
                      <span className="capitalize">{selectedReceipt.payment_mode.replace(/_/g, ' ').toLowerCase()}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {selectedReceipt.invoice && (
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Against Invoice</div>
                    <div className="font-mono font-medium">{selectedReceipt.invoice.invoice_number}</div>
                  </CardContent>
                </Card>
              )}

              {selectedReceipt.reference_number && (
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Reference Number</div>
                    <div className="font-mono">{selectedReceipt.reference_number}</div>
                  </CardContent>
                </Card>
              )}

              <Card className="bg-green-50">
                <CardContent className="pt-4">
                  <div className="text-xs text-green-600">Amount Received</div>
                  <div className="text-2xl font-bold text-green-700">
                    {formatCurrency(selectedReceipt.amount)}
                  </div>
                </CardContent>
              </Card>

              {selectedReceipt.notes && (
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Notes</div>
                    <div className="text-sm">{selectedReceipt.notes}</div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
