'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, Download, Truck, RefreshCw, XCircle, Loader2 } from 'lucide-react';
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
import { Card, CardContent } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { ewayBillsApi, invoicesApi } from '@/lib/api';
import { formatDate, formatCurrency } from '@/lib/utils';

interface EWayBill {
  id: string;
  ewb_number?: string;
  eway_bill_number?: string;
  ewb_date?: string;
  generated_at?: string;
  valid_upto?: string;
  valid_until?: string;
  valid_from?: string;
  invoice_id?: string;
  invoice?: { invoice_number: string };
  from_gstin?: string;
  to_gstin?: string;
  from_place?: string;
  from_name?: string;
  to_place?: string;
  to_name?: string;
  document_value?: number;
  total_value?: number;
  vehicle_number?: string;
  vehicle_type?: string;
  transporter_id?: string;
  transporter_name?: string;
  distance_km?: number;
  status: string;
  cancel_reason?: string;
  cancellation_reason?: string;
  is_valid?: boolean;
  created_at?: string;
}

interface Invoice {
  id: string;
  invoice_number: string;
  total_amount: number;
}

const transportModes = [
  { label: 'Road', value: 'ROAD' },
  { label: 'Rail', value: 'RAIL' },
  { label: 'Air', value: 'AIR' },
  { label: 'Ship', value: 'SHIP' },
];

const vehicleTypes = [
  { label: 'Regular', value: 'REGULAR' },
  { label: 'Over Dimensional Cargo', value: 'ODC' },
];

export default function EWayBillsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [isExtendOpen, setIsExtendOpen] = useState(false);
  const [selectedBill, setSelectedBill] = useState<EWayBill | null>(null);
  const [extendData, setExtendData] = useState({ reason: '', vehicle_number: '', valid_upto: '' });

  const [formData, setFormData] = useState({
    invoice_id: '',
    from_gstin: '',
    to_gstin: '',
    from_place: '',
    to_place: '',
    transport_mode: 'ROAD',
    vehicle_type: 'REGULAR',
    vehicle_number: '',
    transporter_name: '',
    distance_km: 0,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['eway-bills', page, pageSize],
    queryFn: () => ewayBillsApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: invoicesData } = useQuery({
    queryKey: ['invoices-for-ewb'],
    queryFn: () => invoicesApi.list({ size: 50, status: 'POSTED' }),
  });

  const generateMutation = useMutation({
    mutationFn: ewayBillsApi.generate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eway-bills'] });
      toast.success('E-Way Bill generated successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to generate E-Way Bill'),
  });

  const cancelMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => ewayBillsApi.cancel(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eway-bills'] });
      toast.success('E-Way Bill cancelled');
      setIsViewOpen(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to cancel'),
  });

  const extendMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: typeof extendData }) =>
      ewayBillsApi.extendValidity(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eway-bills'] });
      toast.success('Validity extended');
      setIsExtendOpen(false);
      setExtendData({ reason: '', vehicle_number: '', valid_upto: '' });
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to extend validity'),
  });

  const resetForm = () => {
    setFormData({
      invoice_id: '',
      from_gstin: '',
      to_gstin: '',
      from_place: '',
      to_place: '',
      transport_mode: 'ROAD',
      vehicle_type: 'REGULAR',
      vehicle_number: '',
      transporter_name: '',
      distance_km: 0,
    });
    setIsDialogOpen(false);
  };

  const handleViewBill = async (bill: EWayBill) => {
    try {
      const detail = await ewayBillsApi.getById(bill.id);
      setSelectedBill(detail);
    } catch {
      setSelectedBill(bill);
    }
    setIsViewOpen(true);
  };

  const handleDownload = async (bill: EWayBill) => {
    try {
      // Fetch HTML with auth token, then open in new tab
      const htmlContent = await ewayBillsApi.download(bill.id);
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => window.URL.revokeObjectURL(url);
      }
      toast.success('Opening E-Way Bill for download/print');
    } catch {
      toast.error('Failed to download E-Way Bill');
    }
  };

  const handleSubmit = () => {
    if (!formData.invoice_id || !formData.from_place || !formData.to_place) {
      toast.error('Invoice, origin, and destination are required');
      return;
    }

    generateMutation.mutate({
      invoice_id: formData.invoice_id,
      from_gstin: formData.from_gstin,
      to_gstin: formData.to_gstin,
      from_place: formData.from_place,
      to_place: formData.to_place,
      transport_mode: formData.transport_mode,
      vehicle_type: formData.vehicle_type,
      vehicle_number: formData.vehicle_number || undefined,
      transporter_name: formData.transporter_name || undefined,
      distance_km: formData.distance_km || undefined,
    });
  };

  const columns: ColumnDef<EWayBill>[] = [
    {
      accessorKey: 'eway_bill_number',
      header: 'E-Way Bill #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Truck className="h-4 w-4 text-muted-foreground" />
          <span className="font-mono font-medium">{row.original.eway_bill_number || row.original.ewb_number || '-'}</span>
        </div>
      ),
    },
    {
      accessorKey: 'invoice',
      header: 'Invoice',
      cell: ({ row }) => (
        <span className="text-sm">{row.original.invoice?.invoice_number || '-'}</span>
      ),
    },
    {
      accessorKey: 'route',
      header: 'Route',
      cell: ({ row }) => (
        <div className="text-sm">
          <div>{row.original.from_place}</div>
          <div className="text-muted-foreground">→ {row.original.to_place}</div>
        </div>
      ),
    },
    {
      accessorKey: 'vehicle_number',
      header: 'Vehicle',
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.original.vehicle_number || '-'}</span>
      ),
    },
    {
      accessorKey: 'total_value',
      header: 'Value',
      cell: ({ row }) => (
        <span className="font-medium">{formatCurrency(row.original.total_value ?? row.original.document_value ?? 0)}</span>
      ),
    },
    {
      accessorKey: 'valid_until',
      header: 'Valid Till',
      cell: ({ row }) => {
        const validDate = row.original.valid_until || row.original.valid_upto;
        if (!validDate) return <span className="text-sm text-muted-foreground">-</span>;
        const isExpired = new Date(validDate) < new Date();
        return (
          <span className={`text-sm ${isExpired ? 'text-red-600' : 'text-muted-foreground'}`}>
            {formatDate(validDate)}
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
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => handleViewBill(row.original)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleDownload(row.original)}>
              <Download className="mr-2 h-4 w-4" />
              Download
            </DropdownMenuItem>
            {row.original.status === 'ACTIVE' && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => {
                  setSelectedBill(row.original);
                  setIsExtendOpen(true);
                }}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Extend Validity
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const invoices = invoicesData?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="E-Way Bills"
        description="Manage GST E-Way bills for goods transportation"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Generate E-Way Bill
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Generate E-Way Bill</DialogTitle>
            <DialogDescription>Create a new E-Way Bill for goods transportation</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Invoice *</Label>
              <Select
                value={formData.invoice_id || 'select'}
                onValueChange={(value) => setFormData({ ...formData, invoice_id: value === 'select' ? '' : value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select invoice" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="select" disabled>Select invoice</SelectItem>
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

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>From GSTIN</Label>
                <Input
                  placeholder="22AAAAA0000A1Z5"
                  value={formData.from_gstin}
                  onChange={(e) => setFormData({ ...formData, from_gstin: e.target.value.toUpperCase() })}
                />
              </div>
              <div className="space-y-2">
                <Label>To GSTIN</Label>
                <Input
                  placeholder="22BBBBB0000B1Z5"
                  value={formData.to_gstin}
                  onChange={(e) => setFormData({ ...formData, to_gstin: e.target.value.toUpperCase() })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>From Place *</Label>
                <Input
                  placeholder="Mumbai"
                  value={formData.from_place}
                  onChange={(e) => setFormData({ ...formData, from_place: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>To Place *</Label>
                <Input
                  placeholder="Delhi"
                  value={formData.to_place}
                  onChange={(e) => setFormData({ ...formData, to_place: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Transport Mode</Label>
                <Select
                  value={formData.transport_mode}
                  onValueChange={(value) => setFormData({ ...formData, transport_mode: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {transportModes.map((mode) => (
                      <SelectItem key={mode.value} value={mode.value}>{mode.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Vehicle Type</Label>
                <Select
                  value={formData.vehicle_type}
                  onValueChange={(value) => setFormData({ ...formData, vehicle_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {vehicleTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Vehicle Number</Label>
                <Input
                  placeholder="MH01AB1234"
                  value={formData.vehicle_number}
                  onChange={(e) => setFormData({ ...formData, vehicle_number: e.target.value.toUpperCase() })}
                />
              </div>
              <div className="space-y-2">
                <Label>Distance (km)</Label>
                <Input
                  type="number"
                  min="0"
                  placeholder="500"
                  value={formData.distance_km || ''}
                  onChange={(e) => setFormData({ ...formData, distance_km: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Transporter Name</Label>
              <Input
                placeholder="ABC Logistics"
                value={formData.transporter_name}
                onChange={(e) => setFormData({ ...formData, transporter_name: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={resetForm}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={generateMutation.isPending}>
              {generateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Generate E-Way Bill
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="eway_bill_number"
        searchPlaceholder="Search E-Way bills..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* E-Way Bill Detail Sheet */}
      <Sheet open={isViewOpen} onOpenChange={setIsViewOpen}>
        <SheetContent className="w-[500px] sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Truck className="h-5 w-5" />
              E-Way Bill {selectedBill?.eway_bill_number || selectedBill?.ewb_number}
            </SheetTitle>
            <SheetDescription>Transportation document details</SheetDescription>
          </SheetHeader>
          {selectedBill && (
            <div className="mt-6 space-y-4">
              <div className="flex items-center gap-3">
                <StatusBadge status={selectedBill.status} />
                <span className="text-sm text-muted-foreground">
                  Generated: {formatDate(selectedBill.generated_at || selectedBill.ewb_date || selectedBill.created_at || '')}
                </span>
              </div>

              <Card>
                <CardContent className="pt-4 grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-muted-foreground">Valid Until</div>
                    <div className="font-medium">{formatDate(selectedBill.valid_until || selectedBill.valid_upto || '')}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Document Value</div>
                    <div className="font-medium">{formatCurrency(selectedBill.total_value ?? selectedBill.document_value ?? 0)}</div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-4">
                  <div className="text-xs text-muted-foreground mb-2">Route</div>
                  <div className="flex items-center gap-2">
                    <div className="font-medium">{selectedBill.from_place}</div>
                    <span className="text-muted-foreground">→</span>
                    <div className="font-medium">{selectedBill.to_place}</div>
                  </div>
                  {selectedBill.distance_km && (
                    <div className="text-sm text-muted-foreground mt-1">{selectedBill.distance_km} km</div>
                  )}
                </CardContent>
              </Card>

              {selectedBill.vehicle_number && (
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Vehicle</div>
                    <div className="font-mono font-medium">{selectedBill.vehicle_number}</div>
                    {selectedBill.transporter_name && (
                      <div className="text-sm text-muted-foreground">{selectedBill.transporter_name}</div>
                    )}
                  </CardContent>
                </Card>
              )}

              {(selectedBill.cancellation_reason || selectedBill.cancel_reason) && (
                <Card className="bg-red-50">
                  <CardContent className="pt-4">
                    <div className="text-xs text-red-600">Cancellation Reason</div>
                    <div className="text-sm text-red-700">{selectedBill.cancellation_reason || selectedBill.cancel_reason}</div>
                  </CardContent>
                </Card>
              )}

              <div className="flex gap-2 pt-4">
                <Button variant="outline" onClick={() => handleDownload(selectedBill)}>
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>
                {selectedBill.status === 'ACTIVE' && (
                  <Button
                    variant="destructive"
                    onClick={() => cancelMutation.mutate({ id: selectedBill.id, reason: 'Cancelled by user' })}
                    disabled={cancelMutation.isPending}
                  >
                    {cancelMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <XCircle className="mr-2 h-4 w-4" />}
                    Cancel E-Way Bill
                  </Button>
                )}
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Extend Validity Dialog */}
      <Dialog open={isExtendOpen} onOpenChange={setIsExtendOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Extend E-Way Bill Validity</DialogTitle>
            <DialogDescription>
              Extend validity for E-Way Bill {selectedBill?.eway_bill_number || selectedBill?.ewb_number}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Reason for Extension *</Label>
              <Input
                placeholder="Vehicle breakdown, natural calamity, etc."
                value={extendData.reason}
                onChange={(e) => setExtendData({ ...extendData, reason: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>New Vehicle Number (if changed)</Label>
              <Input
                placeholder="MH01AB1234"
                value={extendData.vehicle_number}
                onChange={(e) => setExtendData({ ...extendData, vehicle_number: e.target.value.toUpperCase() })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsExtendOpen(false)}>Cancel</Button>
            <Button
              onClick={() => selectedBill && extendMutation.mutate({ id: selectedBill.id, data: extendData })}
              disabled={!extendData.reason.trim() || extendMutation.isPending}
            >
              {extendMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Extend Validity
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
