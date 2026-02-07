'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, Download, FileX, CheckCircle, Trash2, Loader2 } from 'lucide-react';
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
import { Separator } from '@/components/ui/separator';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { creditDebitNotesApi, customersApi, invoicesApi } from '@/lib/api';
import { formatDate, formatCurrency } from '@/lib/utils';

interface CreditNoteLine {
  id?: string;
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
  tax_rate?: number;
  tax_amount?: number;
}

interface CreditNote {
  id: string;
  credit_note_number: string;
  credit_note_date: string;
  invoice_id?: string;
  invoice?: { invoice_number: string };
  customer_id: string;
  customer?: { name: string; email?: string; phone?: string };
  reason: string;
  lines?: CreditNoteLine[];
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  status: 'DRAFT' | 'APPROVED' | 'APPLIED' | 'CANCELLED';
  applied_to_invoice_id?: string;
  created_at: string;
}

interface Customer {
  id: string;
  name: string;
}

interface Invoice {
  id: string;
  invoice_number: string;
  total_amount: number;
  customer_id: string;
}

const creditReasons = [
  { label: 'Goods Returned', value: 'GOODS_RETURNED' },
  { label: 'Defective Goods', value: 'DEFECTIVE_GOODS' },
  { label: 'Pricing Error', value: 'PRICING_ERROR' },
  { label: 'Quantity Discrepancy', value: 'QUANTITY_DISCREPANCY' },
  { label: 'Service Not Rendered', value: 'SERVICE_NOT_RENDERED' },
  { label: 'Other', value: 'OTHER' },
];

const emptyLine = (): CreditNoteLine => ({
  description: '',
  quantity: 1,
  unit_price: 0,
  amount: 0,
  tax_rate: 18,
  tax_amount: 0,
});

export default function CreditNotesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [selectedNote, setSelectedNote] = useState<CreditNote | null>(null);

  const [formData, setFormData] = useState({
    customer_id: '',
    invoice_id: '',
    reason: 'GOODS_RETURNED',
    reason_detail: '',
    credit_note_date: new Date().toISOString().split('T')[0],
    lines: [emptyLine()],
  });

  const { data, isLoading } = useQuery({
    queryKey: ['credit-notes', page, pageSize],
    queryFn: () => creditDebitNotesApi.list({ page: page + 1, size: pageSize, type: 'CREDIT' }),
  });

  const { data: customersData } = useQuery({
    queryKey: ['customers-list'],
    queryFn: () => customersApi.list({ size: 100 }),
  });

  const { data: invoicesData } = useQuery({
    queryKey: ['invoices-for-cn', formData.customer_id],
    queryFn: () => invoicesApi.list({ customer_id: formData.customer_id, size: 50 }),
    enabled: !!formData.customer_id,
  });

  const createMutation = useMutation({
    mutationFn: (data: { invoice_id?: string; customer_id: string; reason: string; credit_note_date?: string; subtotal?: number; tax_amount?: number; total_amount?: number; lines?: { description: string; quantity: number; unit_price: number; amount?: number; tax_rate?: number; tax_amount?: number }[] }) =>
      creditDebitNotesApi.create({ type: 'CREDIT', ...data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credit-notes'] });
      toast.success('Credit note created');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create credit note'),
  });

  const approveMutation = useMutation({
    mutationFn: creditDebitNotesApi.approve,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credit-notes'] });
      toast.success('Credit note approved');
      setIsViewOpen(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to approve'),
  });

  const applyMutation = useMutation({
    mutationFn: ({ id, invoice_id }: { id: string; invoice_id: string }) =>
      creditDebitNotesApi.apply(id, invoice_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credit-notes'] });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('Credit note applied to invoice');
      setIsViewOpen(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to apply'),
  });

  const cancelMutation = useMutation({
    mutationFn: creditDebitNotesApi.cancel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credit-notes'] });
      toast.success('Credit note cancelled');
      setIsViewOpen(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to cancel'),
  });

  const resetForm = () => {
    setFormData({
      customer_id: '',
      invoice_id: '',
      reason: 'GOODS_RETURNED',
      reason_detail: '',
      credit_note_date: new Date().toISOString().split('T')[0],
      lines: [emptyLine()],
    });
    setIsDialogOpen(false);
  };

  const handleViewNote = async (note: CreditNote) => {
    try {
      const detail = await creditDebitNotesApi.getById(note.id);
      setSelectedNote(detail);
    } catch {
      setSelectedNote(note);
    }
    setIsViewOpen(true);
  };

  const handleDownload = async (note: CreditNote) => {
    try {
      // Fetch HTML with auth token, then open in new tab
      const htmlContent = await creditDebitNotesApi.download(note.id);
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => window.URL.revokeObjectURL(url);
      }
      toast.success('Opening credit note for download/print');
    } catch {
      toast.error('Failed to download credit note');
    }
  };

  const addLine = () => {
    setFormData({ ...formData, lines: [...formData.lines, emptyLine()] });
  };

  const removeLine = (index: number) => {
    if (formData.lines.length > 1) {
      const newLines = formData.lines.filter((_, i) => i !== index);
      setFormData({ ...formData, lines: newLines });
    }
  };

  const updateLine = (index: number, field: keyof CreditNoteLine, value: string | number) => {
    const newLines = [...formData.lines];
    newLines[index] = { ...newLines[index], [field]: value };
    // Auto-calculate amount and tax
    if (field === 'quantity' || field === 'unit_price' || field === 'tax_rate') {
      const qty = field === 'quantity' ? Number(value) : newLines[index].quantity;
      const price = field === 'unit_price' ? Number(value) : newLines[index].unit_price;
      const taxRate = field === 'tax_rate' ? Number(value) : (newLines[index].tax_rate || 0);
      const amount = qty * price;
      const taxAmount = amount * (taxRate / 100);
      newLines[index].amount = amount;
      newLines[index].tax_amount = taxAmount;
    }
    setFormData({ ...formData, lines: newLines });
  };

  const getTotals = () => {
    const subtotal = formData.lines.reduce((sum, line) => sum + (line.amount || 0), 0);
    const taxAmount = formData.lines.reduce((sum, line) => sum + (line.tax_amount || 0), 0);
    const total = subtotal + taxAmount;
    return { subtotal, taxAmount, total };
  };

  const handleSubmit = () => {
    if (!formData.customer_id || !formData.reason || !formData.credit_note_date) {
      toast.error('Customer, reason, and date are required');
      return;
    }

    const validLines = formData.lines.filter(l => l.description && l.amount > 0);
    if (validLines.length === 0) {
      toast.error('At least one line item is required');
      return;
    }

    const { subtotal, taxAmount, total } = getTotals();

    createMutation.mutate({
      customer_id: formData.customer_id,
      invoice_id: formData.invoice_id || undefined,
      reason: formData.reason === 'OTHER' ? formData.reason_detail : formData.reason,
      credit_note_date: formData.credit_note_date,
      lines: validLines.map(l => ({
        description: l.description,
        quantity: l.quantity,
        unit_price: l.unit_price,
        amount: l.amount,
        tax_rate: l.tax_rate,
        tax_amount: l.tax_amount,
      })),
      subtotal,
      tax_amount: taxAmount,
      total_amount: total,
    });
  };

  const columns: ColumnDef<CreditNote>[] = [
    {
      accessorKey: 'credit_note_number',
      header: 'Credit Note #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <FileX className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.original.credit_note_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'invoice',
      header: 'Against Invoice',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground font-mono">
          {row.original.invoice?.invoice_number || '-'}
        </span>
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
      accessorKey: 'credit_note_date',
      header: 'Date',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {formatDate(row.original.credit_note_date)}
        </span>
      ),
    },
    {
      accessorKey: 'reason',
      header: 'Reason',
      cell: ({ row }) => (
        <span className="text-sm line-clamp-1">{row.original.reason}</span>
      ),
    },
    {
      accessorKey: 'total_amount',
      header: 'Amount',
      cell: ({ row }) => (
        <span className="font-medium text-red-600">
          -{formatCurrency(row.original.total_amount)}
        </span>
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
            <DropdownMenuItem onClick={() => handleViewNote(row.original)}>
              <Eye className="mr-2 h-4 w-4" />
              View
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleDownload(row.original)}>
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const customers = customersData?.items ?? [];
  const invoices = invoicesData?.items ?? [];
  const { subtotal, taxAmount, total } = getTotals();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Credit Notes"
        description="Manage credit notes and refunds"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Credit Note
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Credit Note</DialogTitle>
            <DialogDescription>Issue a credit note for returns or adjustments</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
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
              <div className="space-y-2">
                <Label>Date *</Label>
                <Input
                  type="date"
                  value={formData.credit_note_date}
                  onChange={(e) => setFormData({ ...formData, credit_note_date: e.target.value })}
                />
              </div>
            </div>

            {formData.customer_id && invoices.length > 0 && (
              <div className="space-y-2">
                <Label>Against Invoice (Optional)</Label>
                <Select
                  value={formData.invoice_id || 'none'}
                  onValueChange={(value) => setFormData({ ...formData, invoice_id: value === 'none' ? '' : value })}
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
                          {inv.invoice_number} - {formatCurrency(inv.total_amount)}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Reason *</Label>
                <Select
                  value={formData.reason}
                  onValueChange={(value) => setFormData({ ...formData, reason: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {creditReasons.map((r) => (
                      <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {formData.reason === 'OTHER' && (
                <div className="space-y-2">
                  <Label>Specify Reason *</Label>
                  <Input
                    placeholder="Enter reason"
                    value={formData.reason_detail}
                    onChange={(e) => setFormData({ ...formData, reason_detail: e.target.value })}
                  />
                </div>
              )}
            </div>

            <Separator />

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-base font-medium">Line Items</Label>
                <Button type="button" variant="outline" size="sm" onClick={addLine}>
                  <Plus className="mr-1 h-3 w-3" /> Add Line
                </Button>
              </div>

              <div className="grid grid-cols-12 gap-2 text-xs font-medium text-muted-foreground px-1">
                <div className="col-span-4">Description</div>
                <div className="col-span-2 text-right">Qty</div>
                <div className="col-span-2 text-right">Unit Price</div>
                <div className="col-span-1 text-right">Tax %</div>
                <div className="col-span-2 text-right">Amount</div>
                <div className="col-span-1"></div>
              </div>

              {formData.lines.map((line, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2 items-center">
                  <div className="col-span-4">
                    <Input
                      className="h-9"
                      placeholder="Item description"
                      value={line.description}
                      onChange={(e) => updateLine(idx, 'description', e.target.value)}
                    />
                  </div>
                  <div className="col-span-2">
                    <Input
                      className="h-9 text-right"
                      type="number"
                      min="1"
                      value={line.quantity}
                      onChange={(e) => updateLine(idx, 'quantity', parseInt(e.target.value) || 1)}
                    />
                  </div>
                  <div className="col-span-2">
                    <Input
                      className="h-9 text-right"
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                      value={line.unit_price || ''}
                      onChange={(e) => updateLine(idx, 'unit_price', parseFloat(e.target.value) || 0)}
                    />
                  </div>
                  <div className="col-span-1">
                    <Input
                      className="h-9 text-right"
                      type="number"
                      min="0"
                      max="28"
                      value={line.tax_rate || ''}
                      onChange={(e) => updateLine(idx, 'tax_rate', parseInt(e.target.value) || 0)}
                    />
                  </div>
                  <div className="col-span-2 text-right font-medium">
                    {formatCurrency(line.amount + (line.tax_amount || 0))}
                  </div>
                  <div className="col-span-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => removeLine(idx)}
                      disabled={formData.lines.length <= 1}
                    >
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                </div>
              ))}

              <Separator />

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Subtotal:</span>
                  <span>{formatCurrency(subtotal)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tax:</span>
                  <span>{formatCurrency(taxAmount)}</span>
                </div>
                <div className="flex justify-between font-medium text-base text-red-600">
                  <span>Total Credit:</span>
                  <span>-{formatCurrency(total)}</span>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={resetForm}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Credit Note
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="credit_note_number"
        searchPlaceholder="Search credit notes..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Credit Note Detail Sheet */}
      <Sheet open={isViewOpen} onOpenChange={setIsViewOpen}>
        <SheetContent className="w-[550px] sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <FileX className="h-5 w-5" />
              Credit Note {selectedNote?.credit_note_number}
            </SheetTitle>
            <SheetDescription>Credit note details</SheetDescription>
          </SheetHeader>
          {selectedNote && (
            <div className="mt-6 space-y-4">
              <div className="flex items-center gap-3">
                <StatusBadge status={selectedNote.status} />
                <span className="text-sm text-muted-foreground">
                  {formatDate(selectedNote.credit_note_date)}
                </span>
              </div>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Customer</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="font-medium">{selectedNote.customer?.name}</div>
                  {selectedNote.customer?.email && (
                    <div className="text-sm text-muted-foreground">{selectedNote.customer.email}</div>
                  )}
                </CardContent>
              </Card>

              {selectedNote.invoice && (
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Against Invoice</div>
                    <div className="font-mono">{selectedNote.invoice.invoice_number}</div>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardContent className="pt-4">
                  <div className="text-xs text-muted-foreground">Reason</div>
                  <div className="text-sm">{selectedNote.reason}</div>
                </CardContent>
              </Card>

              {selectedNote.lines && selectedNote.lines.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Line Items</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {selectedNote.lines.map((line, idx) => (
                        <div key={idx} className="flex justify-between text-sm py-2 border-b last:border-0">
                          <div>
                            <div>{line.description}</div>
                            <div className="text-xs text-muted-foreground">
                              {line.quantity} x {formatCurrency(line.unit_price)}
                            </div>
                          </div>
                          <div className="text-right font-medium">
                            {formatCurrency(line.amount)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              <Card className="bg-red-50">
                <CardContent className="pt-4">
                  <div className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>Subtotal</span>
                      <span>{formatCurrency(selectedNote.subtotal)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Tax</span>
                      <span>{formatCurrency(selectedNote.tax_amount)}</span>
                    </div>
                    <Separator className="my-2" />
                    <div className="flex justify-between font-bold text-red-700">
                      <span>Total Credit</span>
                      <span>-{formatCurrency(selectedNote.total_amount)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <div className="flex flex-wrap gap-2 pt-4">
                <Button variant="outline" onClick={() => handleDownload(selectedNote)}>
                  <Download className="mr-2 h-4 w-4" />
                  Download PDF
                </Button>

                {selectedNote.status === 'DRAFT' && (
                  <>
                    <Button
                      onClick={() => approveMutation.mutate(selectedNote.id)}
                      disabled={approveMutation.isPending}
                    >
                      {approveMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle className="mr-2 h-4 w-4" />}
                      Approve
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={() => cancelMutation.mutate(selectedNote.id)}
                      disabled={cancelMutation.isPending}
                    >
                      {cancelMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
                      Cancel
                    </Button>
                  </>
                )}

                {selectedNote.status === 'APPROVED' && selectedNote.invoice_id && (
                  <Button
                    onClick={() => applyMutation.mutate({ id: selectedNote.id, invoice_id: selectedNote.invoice_id! })}
                    disabled={applyMutation.isPending}
                  >
                    {applyMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Apply to Invoice
                  </Button>
                )}

                {selectedNote.status === 'APPLIED' && (
                  <div className="text-sm text-green-600 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    Credit has been applied
                  </div>
                )}
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
