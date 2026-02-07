'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Receipt, Plus, DollarSign, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
import { Textarea } from '@/components/ui/textarea';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface WarehouseBill {
  id: string;
  bill_number: string;
  client_name: string;
  billing_period_start: string;
  billing_period_end: string;
  storage_charges: number;
  handling_charges: number;
  other_charges: number;
  total_amount: number;
  tax_amount: number;
  grand_total: number;
  status: 'DRAFT' | 'PENDING' | 'SENT' | 'PAID' | 'OVERDUE' | 'CANCELLED';
  due_date: string;
  paid_date?: string;
  created_at: string;
}

interface BillingStats {
  total_billed: number;
  pending_amount: number;
  overdue_amount: number;
  collected_this_month: number;
}

interface InvoiceFormData {
  client_name: string;
  billing_period_start: string;
  billing_period_end: string;
  invoice_type: 'STORAGE' | 'HANDLING' | 'COMBINED' | 'CUSTOM';
  notes: string;
}

const invoiceTypes = [
  { label: 'Storage Only', value: 'STORAGE' },
  { label: 'Handling Only', value: 'HANDLING' },
  { label: 'Combined (Storage + Handling)', value: 'COMBINED' },
  { label: 'Custom', value: 'CUSTOM' },
];

const billingApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/warehouse-billing/', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<BillingStats> => {
    try {
      const { data } = await apiClient.get('/warehouse-billing/stats');
      return data;
    } catch {
      return { total_billed: 0, pending_amount: 0, overdue_amount: 0, collected_this_month: 0 };
    }
  },
  generateInvoice: async (invoiceData: InvoiceFormData) => {
    const { data } = await apiClient.post('/warehouse-billing/generate', invoiceData);
    return data;
  },
};

const columns: ColumnDef<WarehouseBill>[] = [
  {
    accessorKey: 'bill_number',
    header: 'Invoice',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Receipt className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.bill_number}</div>
          <div className="text-xs text-muted-foreground">{row.original.client_name}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'billing_period',
    header: 'Period',
    cell: ({ row }) => (
      <div className="text-sm">
        {new Date(row.original.billing_period_start).toLocaleDateString()} - {new Date(row.original.billing_period_end).toLocaleDateString()}
      </div>
    ),
  },
  {
    accessorKey: 'charges',
    header: 'Charges',
    cell: ({ row }) => (
      <div className="text-sm space-y-0.5">
        <div>Storage: ${row.original.storage_charges.toFixed(2)}</div>
        <div className="text-muted-foreground">Handling: ${row.original.handling_charges.toFixed(2)}</div>
      </div>
    ),
  },
  {
    accessorKey: 'grand_total',
    header: 'Total',
    cell: ({ row }) => (
      <div>
        <div className="font-mono font-medium">${row.original.grand_total.toFixed(2)}</div>
        <div className="text-xs text-muted-foreground">Tax: ${row.original.tax_amount.toFixed(2)}</div>
      </div>
    ),
  },
  {
    accessorKey: 'due_date',
    header: 'Due Date',
    cell: ({ row }) => {
      const isOverdue = new Date(row.original.due_date) < new Date() && row.original.status !== 'PAID';
      return (
        <div className={`flex items-center gap-2 ${isOverdue ? 'text-red-600' : ''}`}>
          <Clock className="h-4 w-4" />
          <span className="text-sm">{new Date(row.original.due_date).toLocaleDateString()}</span>
        </div>
      );
    },
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

const initialFormData: InvoiceFormData = {
  client_name: '',
  billing_period_start: '',
  billing_period_end: '',
  invoice_type: 'COMBINED',
  notes: '',
};

export default function BillingPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState<InvoiceFormData>(initialFormData);

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['wms-billing', page, pageSize],
    queryFn: () => billingApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-billing-stats'],
    queryFn: billingApi.getStats,
  });

  const generateInvoiceMutation = useMutation({
    mutationFn: billingApi.generateInvoice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-billing'] });
      queryClient.invalidateQueries({ queryKey: ['wms-billing-stats'] });
      toast.success('Invoice generated successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to generate invoice');
    },
  });

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setFormData(initialFormData);
  };

  const handleSubmit = () => {
    if (!formData.client_name.trim()) {
      toast.error('Client name is required');
      return;
    }
    if (!formData.billing_period_start) {
      toast.error('Billing period start date is required');
      return;
    }
    if (!formData.billing_period_end) {
      toast.error('Billing period end date is required');
      return;
    }
    if (new Date(formData.billing_period_end) < new Date(formData.billing_period_start)) {
      toast.error('End date must be after start date');
      return;
    }

    generateInvoiceMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Warehouse Billing"
        description="Manage 3PL billing, storage fees, and handling charges"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Generate Invoice
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Generate Invoice</DialogTitle>
            <DialogDescription>
              Create a new invoice for warehouse billing services.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="client_name">Client *</Label>
              <Input
                id="client_name"
                placeholder="Enter client name"
                value={formData.client_name}
                onChange={(e) =>
                  setFormData({ ...formData, client_name: e.target.value })
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="billing_period_start">Billing Period From *</Label>
                <Input
                  id="billing_period_start"
                  type="date"
                  value={formData.billing_period_start}
                  onChange={(e) =>
                    setFormData({ ...formData, billing_period_start: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="billing_period_end">Billing Period To *</Label>
                <Input
                  id="billing_period_end"
                  type="date"
                  value={formData.billing_period_end}
                  onChange={(e) =>
                    setFormData({ ...formData, billing_period_end: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="invoice_type">Invoice Type</Label>
              <Select
                value={formData.invoice_type}
                onValueChange={(value: 'STORAGE' | 'HANDLING' | 'COMBINED' | 'CUSTOM') =>
                  setFormData({ ...formData, invoice_type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select invoice type" />
                </SelectTrigger>
                <SelectContent>
                  {invoiceTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                placeholder="Additional notes for this invoice..."
                value={formData.notes}
                onChange={(e) =>
                  setFormData({ ...formData, notes: e.target.value })
                }
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleDialogClose}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={generateInvoiceMutation.isPending}>
              {generateInvoiceMutation.isPending ? 'Generating...' : 'Generate Invoice'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Billed</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${(stats?.total_billed || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <Clock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">${(stats?.pending_amount || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Awaiting payment</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overdue</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">${(stats?.overdue_amount || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Past due date</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Collected</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">${(stats?.collected_this_month || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="bill_number"
        searchPlaceholder="Search invoices..."
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
