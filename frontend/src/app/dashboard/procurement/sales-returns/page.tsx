'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  MoreHorizontal, Plus, Eye, Package, CheckCircle, XCircle,
  Loader2, CalendarIcon, AlertTriangle, Download, Printer,
  Trash2, Truck, ClipboardCheck, CreditCard, RefreshCw,
  MapPin, Phone, User
} from 'lucide-react';
import { format } from 'date-fns';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Checkbox } from '@/components/ui/checkbox';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { srnApi, ordersApi, warehousesApi, customersApi } from '@/lib/api';
import { formatDate, formatCurrency, cn } from '@/lib/utils';

interface SRN {
  id: string;
  srn_number: string;
  srn_date: string;
  order_id?: string;
  invoice_id?: string;
  customer_id: string;
  warehouse_id: string;
  status: string;
  return_reason: string;
  return_reason_detail?: string;
  resolution_type?: string;
  pickup_required: boolean;
  pickup_status?: string;
  pickup_scheduled_date?: string;
  courier_name?: string;
  courier_tracking_number?: string;
  qc_required: boolean;
  qc_status?: string;
  total_items: number;
  total_quantity_returned: number;
  total_quantity_accepted: number;
  total_quantity_rejected: number;
  total_value: number;
  put_away_complete: boolean;
  customer_name?: string;
  order_number?: string;
  warehouse_name?: string;
  items?: SRNItem[];
  created_at: string;
}

interface SRNItem {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  serial_numbers?: string[];
  quantity_sold: number;
  quantity_returned: number;
  quantity_accepted: number;
  quantity_rejected: number;
  unit_price: number;
  return_value: number;
  item_condition?: string;
  restock_decision?: string;
  qc_result?: string;
  rejection_reason?: string;
  bin_location?: string;
}

interface Order {
  id: string;
  order_number: string;
  customer_id: string;
  customer?: { first_name?: string; last_name?: string; phone?: string };
  status: string;
  items?: OrderItem[];
  grand_total: number;
}

interface OrderItem {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  serial_numbers?: string[];
}

interface Customer {
  id: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  email?: string;
  address_line1?: string;
  city?: string;
  state?: string;
  pincode?: string;
}

interface Warehouse {
  id: string;
  name: string;
  code: string;
}

const statusOptions = [
  { label: 'All Statuses', value: 'all' },
  { label: 'Draft', value: 'DRAFT' },
  { label: 'Pending Receipt', value: 'PENDING_RECEIPT' },
  { label: 'Received', value: 'RECEIVED' },
  { label: 'Pending QC', value: 'PENDING_QC' },
  { label: 'Put Away Pending', value: 'PUT_AWAY_PENDING' },
  { label: 'Put Away Complete', value: 'PUT_AWAY_COMPLETE' },
  { label: 'Credited', value: 'CREDITED' },
  { label: 'Replaced', value: 'REPLACED' },
  { label: 'Refunded', value: 'REFUNDED' },
  { label: 'Cancelled', value: 'CANCELLED' },
];

const returnReasons = [
  { label: 'Defective', value: 'DEFECTIVE' },
  { label: 'Damaged in Transit', value: 'DAMAGED_IN_TRANSIT' },
  { label: 'Wrong Item', value: 'WRONG_ITEM' },
  { label: 'Not as Described', value: 'NOT_AS_DESCRIBED' },
  { label: 'Change of Mind', value: 'CHANGE_OF_MIND' },
  { label: 'Warranty Claim', value: 'WARRANTY_CLAIM' },
  { label: 'Size Issue', value: 'SIZE_ISSUE' },
  { label: 'Quality Issue', value: 'QUALITY_ISSUE' },
  { label: 'Other', value: 'OTHER' },
];

const itemConditions = [
  { label: 'Like New', value: 'LIKE_NEW' },
  { label: 'Good', value: 'GOOD' },
  { label: 'Damaged', value: 'DAMAGED' },
  { label: 'Defective', value: 'DEFECTIVE' },
  { label: 'Unsalvageable', value: 'UNSALVAGEABLE' },
];

const restockDecisions = [
  { label: 'Restock as New', value: 'RESTOCK_AS_NEW' },
  { label: 'Restock as Refurb', value: 'RESTOCK_AS_REFURB' },
  { label: 'Send for Repair', value: 'SEND_FOR_REPAIR' },
  { label: 'Return to Vendor', value: 'RETURN_TO_VENDOR' },
  { label: 'Scrap', value: 'SCRAP' },
];

const resolutionTypes = [
  { label: 'Credit Note', value: 'CREDIT_NOTE' },
  { label: 'Replacement', value: 'REPLACEMENT' },
  { label: 'Refund', value: 'REFUND' },
];

const pickupStatuses = [
  { label: 'Scheduled', value: 'SCHEDULED' },
  { label: 'Picked Up', value: 'PICKED_UP' },
  { label: 'In Transit', value: 'IN_TRANSIT' },
  { label: 'Delivered', value: 'DELIVERED' },
];

// Actions cell component
function SRNActionsCell({
  srn,
  onView,
  onSchedulePickup,
  onReceive,
  onProcessQC,
  onPutAway,
  onResolve,
  onDownload,
  onPrint,
  onDelete,
  isSuperAdmin
}: {
  srn: SRN;
  onView: (srn: SRN) => void;
  onSchedulePickup: (srn: SRN) => void;
  onReceive: (srn: SRN) => void;
  onProcessQC: (srn: SRN) => void;
  onPutAway: (srn: SRN) => void;
  onResolve: (srn: SRN) => void;
  onDownload: (srn: SRN) => void;
  onPrint: (srn: SRN) => void;
  onDelete: (srn: SRN) => void;
  isSuperAdmin: boolean;
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
        <DropdownMenuItem onClick={() => onView(srn)}>
          <Eye className="mr-2 h-4 w-4" />
          View Details
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onDownload(srn)}>
          <Download className="mr-2 h-4 w-4" />
          Download PDF
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onPrint(srn)}>
          <Printer className="mr-2 h-4 w-4" />
          Print
        </DropdownMenuItem>

        {/* Workflow Actions */}
        {(srn.status === 'DRAFT' || srn.status === 'PENDING_RECEIPT') && srn.pickup_required && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onSchedulePickup(srn)}>
              <Truck className="mr-2 h-4 w-4" />
              Update Pickup
            </DropdownMenuItem>
          </>
        )}
        {(srn.status === 'DRAFT' || srn.status === 'PENDING_RECEIPT') && (
          <DropdownMenuItem onClick={() => onReceive(srn)}>
            <Package className="mr-2 h-4 w-4" />
            Receive Goods
          </DropdownMenuItem>
        )}
        {srn.status === 'PENDING_QC' && (
          <DropdownMenuItem onClick={() => onProcessQC(srn)}>
            <ClipboardCheck className="mr-2 h-4 w-4" />
            Process QC
          </DropdownMenuItem>
        )}
        {srn.status === 'PUT_AWAY_PENDING' && (
          <DropdownMenuItem onClick={() => onPutAway(srn)}>
            <MapPin className="mr-2 h-4 w-4" />
            Process Put-Away
          </DropdownMenuItem>
        )}
        {srn.status === 'PUT_AWAY_COMPLETE' && (
          <DropdownMenuItem onClick={() => onResolve(srn)}>
            <CreditCard className="mr-2 h-4 w-4" />
            Resolve Return
          </DropdownMenuItem>
        )}

        {isSuperAdmin && srn.status === 'DRAFT' && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() => onDelete(srn)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete SRN
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function SalesReturnsPage() {
  const queryClient = useQueryClient();
  const { permissions } = useAuth();
  const isSuperAdmin = permissions?.is_super_admin ?? false;
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Dialog states
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [selectedSRN, setSelectedSRN] = useState<SRN | null>(null);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [isPickupDialogOpen, setIsPickupDialogOpen] = useState(false);
  const [isReceiveDialogOpen, setIsReceiveDialogOpen] = useState(false);
  const [isQCDialogOpen, setIsQCDialogOpen] = useState(false);
  const [isPutAwayDialogOpen, setIsPutAwayDialogOpen] = useState(false);
  const [isResolveDialogOpen, setIsResolveDialogOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [srnToDelete, setSrnToDelete] = useState<SRN | null>(null);

  // Form state for Create SRN
  const [formData, setFormData] = useState({
    order_id: '',
    customer_id: '',
    warehouse_id: '',
    srn_date: new Date(),
    return_reason: '',
    return_reason_detail: '',
    pickup_required: false,
    pickup_scheduled_date: undefined as Date | undefined,
    pickup_contact_name: '',
    pickup_contact_phone: '',
    qc_required: true,
    receiving_remarks: '',
  });

  // Item quantities for return
  const [returnQuantities, setReturnQuantities] = useState<Record<string, number>>({});

  // Pickup update form
  const [pickupForm, setPickupForm] = useState({
    pickup_status: '',
    courier_name: '',
    courier_tracking_number: '',
  });

  // QC results state
  const [qcResults, setQcResults] = useState<Record<string, {
    qc_result: string;
    item_condition: string;
    restock_decision: string;
    quantity_accepted: number;
    quantity_rejected: number;
    rejection_reason: string;
  }>>({});

  // Put-away locations
  const [putAwayLocations, setPutAwayLocations] = useState<Record<string, string>>({});

  // Resolution form
  const [resolveForm, setResolveForm] = useState({
    resolution_type: '',
    notes: '',
  });

  // Queries
  const { data, isLoading } = useQuery({
    queryKey: ['srn', page, pageSize, statusFilter, searchQuery],
    queryFn: () => srnApi.list({
      page: page + 1,
      size: pageSize,
      status: statusFilter !== 'all' ? statusFilter : undefined,
      search: searchQuery || undefined,
    }),
  });

  const { data: ordersData } = useQuery({
    queryKey: ['orders-for-srn'],
    queryFn: () => ordersApi.list({ status: 'DELIVERED', size: 100 }),
  });

  const { data: warehousesData } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => warehousesApi.list({ is_active: true }),
  });

  const { data: customersData } = useQuery({
    queryKey: ['customers'],
    queryFn: () => customersApi.list({ size: 100 }),
  });

  // Get selected order details
  const selectedOrder = (ordersData?.items ?? []).find((o: Order) => o.id === formData.order_id);

  // Mutations
  const createMutation = useMutation({
    mutationFn: srnApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['srn'] });
      toast.success('Sales Return Note created successfully');
      resetCreateForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create SRN'),
  });

  const updatePickupMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof srnApi.updatePickup>[1] }) =>
      srnApi.updatePickup(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['srn'] });
      toast.success('Pickup status updated');
      setIsPickupDialogOpen(false);
      setSelectedSRN(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update pickup'),
  });

  const receiveMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof srnApi.receive>[1] }) =>
      srnApi.receive(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['srn'] });
      toast.success('Goods received successfully');
      setIsReceiveDialogOpen(false);
      setSelectedSRN(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to receive goods'),
  });

  const processQCMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof srnApi.processQC>[1] }) =>
      srnApi.processQC(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['srn'] });
      toast.success('Quality check completed');
      setIsQCDialogOpen(false);
      setSelectedSRN(null);
      setQcResults({});
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to process QC'),
  });

  const putAwayMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof srnApi.processPutaway>[1] }) =>
      srnApi.processPutaway(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['srn'] });
      toast.success('Put-away completed');
      setIsPutAwayDialogOpen(false);
      setSelectedSRN(null);
      setPutAwayLocations({});
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to process put-away'),
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof srnApi.resolve>[1] }) =>
      srnApi.resolve(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['srn'] });
      toast.success('Return resolved successfully');
      setIsResolveDialogOpen(false);
      setSelectedSRN(null);
      setResolveForm({ resolution_type: '', notes: '' });
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to resolve return'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => srnApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['srn'] });
      toast.success('SRN deleted successfully');
      setIsDeleteOpen(false);
      setSrnToDelete(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete SRN'),
  });

  const handleDownload = async (srn: SRN) => {
    try {
      const htmlContent = await srnApi.download(srn.id);
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => window.URL.revokeObjectURL(url);
      }
      toast.success('Opening SRN for download/print');
    } catch {
      toast.error('Failed to download SRN');
    }
  };

  const handlePrint = async (srn: SRN) => {
    try {
      const htmlContent = await srnApi.download(srn.id);
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
      toast.error('Failed to print SRN');
    }
  };

  const resetCreateForm = () => {
    setFormData({
      order_id: '',
      customer_id: '',
      warehouse_id: '',
      srn_date: new Date(),
      return_reason: '',
      return_reason_detail: '',
      pickup_required: false,
      pickup_scheduled_date: undefined,
      pickup_contact_name: '',
      pickup_contact_phone: '',
      qc_required: true,
      receiving_remarks: '',
    });
    setReturnQuantities({});
    setIsCreateDialogOpen(false);
  };

  const handleOrderChange = (orderId: string) => {
    const order = (ordersData?.items ?? []).find((o: Order) => o.id === orderId);
    setFormData({
      ...formData,
      order_id: orderId,
      customer_id: order?.customer_id || '',
    });
    // Initialize return quantities
    if (order?.items) {
      const initialQuantities: Record<string, number> = {};
      order.items.forEach((item: OrderItem) => {
        if (item.id) {
          initialQuantities[item.id] = 0;
        }
      });
      setReturnQuantities(initialQuantities);
    }
  };

  const handleCreate = () => {
    if (!formData.order_id || !formData.warehouse_id || !formData.return_reason) {
      toast.error('Please fill in all required fields');
      return;
    }

    const order = (ordersData?.items ?? []).find((o: Order) => o.id === formData.order_id);
    if (!order?.items) {
      toast.error('No items found in selected order');
      return;
    }

    const items = order.items
      .filter((item: OrderItem) => returnQuantities[item.id] > 0)
      .map((item: OrderItem) => ({
        order_item_id: item.id,
        product_id: item.product_id,
        product_name: item.product_name,
        sku: item.sku,
        serial_numbers: item.serial_numbers,
        quantity_sold: item.quantity,
        quantity_returned: returnQuantities[item.id],
        unit_price: item.unit_price,
      }));

    if (items.length === 0) {
      toast.error('Please select at least one item to return');
      return;
    }

    createMutation.mutate({
      srn_date: format(formData.srn_date, 'yyyy-MM-dd'),
      order_id: formData.order_id,
      customer_id: formData.customer_id,
      warehouse_id: formData.warehouse_id,
      return_reason: formData.return_reason,
      return_reason_detail: formData.return_reason_detail || undefined,
      pickup_required: formData.pickup_required,
      pickup_scheduled_date: formData.pickup_scheduled_date
        ? format(formData.pickup_scheduled_date, 'yyyy-MM-dd')
        : undefined,
      pickup_contact_name: formData.pickup_contact_name || undefined,
      pickup_contact_phone: formData.pickup_contact_phone || undefined,
      qc_required: formData.qc_required,
      receiving_remarks: formData.receiving_remarks || undefined,
      items,
    });
  };

  const handleUpdatePickup = () => {
    if (!selectedSRN) return;
    updatePickupMutation.mutate({
      id: selectedSRN.id,
      data: {
        pickup_status: pickupForm.pickup_status || undefined,
        courier_name: pickupForm.courier_name || undefined,
        courier_tracking_number: pickupForm.courier_tracking_number || undefined,
      },
    });
  };

  const handleReceive = () => {
    if (!selectedSRN) return;
    receiveMutation.mutate({
      id: selectedSRN.id,
      data: {
        receiving_remarks: formData.receiving_remarks || undefined,
      },
    });
  };

  const handleProcessQC = () => {
    if (!selectedSRN?.items) return;
    const itemResults = selectedSRN.items.map((item) => ({
      item_id: item.id,
      qc_result: qcResults[item.id]?.qc_result || 'ACCEPTED',
      item_condition: qcResults[item.id]?.item_condition || 'LIKE_NEW',
      restock_decision: qcResults[item.id]?.restock_decision || 'RESTOCK_AS_NEW',
      quantity_accepted: qcResults[item.id]?.quantity_accepted ?? item.quantity_returned,
      quantity_rejected: qcResults[item.id]?.quantity_rejected ?? 0,
      rejection_reason: qcResults[item.id]?.rejection_reason || undefined,
    }));

    processQCMutation.mutate({
      id: selectedSRN.id,
      data: { item_results: itemResults },
    });
  };

  const handlePutAway = () => {
    if (!selectedSRN?.items) return;
    const itemLocations = selectedSRN.items
      .filter((item) => item.quantity_accepted > 0)
      .map((item) => ({
        item_id: item.id,
        bin_location: putAwayLocations[item.id] || 'RETURNS-DEFAULT',
      }));

    putAwayMutation.mutate({
      id: selectedSRN.id,
      data: { item_locations: itemLocations },
    });
  };

  const handleResolve = () => {
    if (!selectedSRN || !resolveForm.resolution_type) {
      toast.error('Please select a resolution type');
      return;
    }
    resolveMutation.mutate({
      id: selectedSRN.id,
      data: {
        resolution_type: resolveForm.resolution_type,
        notes: resolveForm.notes || undefined,
      },
    });
  };

  // Open handlers
  const handleView = (srn: SRN) => {
    setSelectedSRN(srn);
    setIsDetailsOpen(true);
  };

  const handleSchedulePickup = (srn: SRN) => {
    setSelectedSRN(srn);
    setPickupForm({
      pickup_status: srn.pickup_status || '',
      courier_name: srn.courier_name || '',
      courier_tracking_number: srn.courier_tracking_number || '',
    });
    setIsPickupDialogOpen(true);
  };

  const handleReceiveOpen = (srn: SRN) => {
    setSelectedSRN(srn);
    setIsReceiveDialogOpen(true);
  };

  const handleQCOpen = (srn: SRN) => {
    setSelectedSRN(srn);
    // Initialize QC results
    if (srn.items) {
      const initialResults: typeof qcResults = {};
      srn.items.forEach((item) => {
        initialResults[item.id] = {
          qc_result: 'ACCEPTED',
          item_condition: 'LIKE_NEW',
          restock_decision: 'RESTOCK_AS_NEW',
          quantity_accepted: item.quantity_returned,
          quantity_rejected: 0,
          rejection_reason: '',
        };
      });
      setQcResults(initialResults);
    }
    setIsQCDialogOpen(true);
  };

  const handlePutAwayOpen = (srn: SRN) => {
    setSelectedSRN(srn);
    setIsPutAwayDialogOpen(true);
  };

  const handleResolveOpen = (srn: SRN) => {
    setSelectedSRN(srn);
    setIsResolveDialogOpen(true);
  };

  const columns: ColumnDef<SRN>[] = [
    {
      accessorKey: 'srn_number',
      header: 'SRN Number',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <RefreshCw className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.original.srn_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'customer_name',
      header: 'Customer',
      cell: ({ row }) => (
        <span className="text-sm">{row.original.customer_name || 'N/A'}</span>
      ),
    },
    {
      accessorKey: 'order_number',
      header: 'Order #',
      cell: ({ row }) => (
        <span className="text-sm font-mono text-muted-foreground">
          {row.original.order_number || 'N/A'}
        </span>
      ),
    },
    {
      accessorKey: 'return_reason',
      header: 'Reason',
      cell: ({ row }) => (
        <Badge variant="outline" className="text-xs">
          {row.original.return_reason?.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    {
      accessorKey: 'total_value',
      header: 'Value',
      cell: ({ row }) => (
        <span className="font-medium">{formatCurrency(row.original.total_value)}</span>
      ),
    },
    {
      accessorKey: 'pickup_status',
      header: 'Pickup',
      cell: ({ row }) => {
        if (!row.original.pickup_required) return <span className="text-muted-foreground text-xs">N/A</span>;
        return (
          <Badge variant={row.original.pickup_status === 'DELIVERED' ? 'default' : 'secondary'} className="text-xs">
            {row.original.pickup_status || 'Pending'}
          </Badge>
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
        <SRNActionsCell
          srn={row.original}
          onView={handleView}
          onSchedulePickup={handleSchedulePickup}
          onReceive={handleReceiveOpen}
          onProcessQC={handleQCOpen}
          onPutAway={handlePutAwayOpen}
          onResolve={handleResolveOpen}
          onDownload={handleDownload}
          onPrint={handlePrint}
          onDelete={(srn) => { setSrnToDelete(srn); setIsDeleteOpen(true); }}
          isSuperAdmin={isSuperAdmin}
        />
      ),
    },
  ];

  const warehouses: Warehouse[] = warehousesData?.items ?? (Array.isArray(warehousesData) ? warehousesData : []);
  const orders = ordersData?.items ?? [];
  const srnList = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sales Returns"
        description="Manage customer returns, RMA, and reverse logistics"
        actions={
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Return
          </Button>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Returns</CardTitle>
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data?.total || 0}</div>
            <p className="text-xs text-muted-foreground">
              Value: {formatCurrency(data?.total_value || 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Pickup</CardTitle>
            <Truck className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {srnList.filter((s: SRN) => s.pickup_required && s.pickup_status !== 'DELIVERED').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Awaiting QC</CardTitle>
            <ClipboardCheck className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {srnList.filter((s: SRN) => s.status === 'PENDING_QC').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ready to Resolve</CardTitle>
            <CreditCard className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {srnList.filter((s: SRN) => s.status === 'PUT_AWAY_COMPLETE').length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <Input
          placeholder="Search SRN or customer..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-64"
        />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            {statusOptions.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={srnList}
        isLoading={isLoading}
        manualPagination
        pageCount={Math.ceil((data?.total ?? 0) / pageSize)}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Create SRN Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Sales Return Note</DialogTitle>
            <DialogDescription>
              Create a return against a delivered order
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Order Selection */}
            <div className="grid gap-2">
              <Label>Select Order *</Label>
              <Select value={formData.order_id} onValueChange={handleOrderChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select delivered order" />
                </SelectTrigger>
                <SelectContent>
                  {orders.map((order: Order) => (
                    <SelectItem key={order.id} value={order.id}>
                      {order.order_number} - {order.customer?.first_name} {order.customer?.last_name} ({formatCurrency(order.grand_total)})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Warehouse */}
            <div className="grid gap-2">
              <Label>Return To Warehouse *</Label>
              <Select value={formData.warehouse_id} onValueChange={(v) => setFormData({...formData, warehouse_id: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Select warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {warehouses.map((wh) => (
                    <SelectItem key={wh.id} value={wh.id}>
                      {wh.name} ({wh.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Return Date */}
              <div className="grid gap-2">
                <Label>Return Date *</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className={cn("justify-start text-left font-normal")}>
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {formData.srn_date ? format(formData.srn_date, 'PP') : 'Pick date'}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0">
                    <Calendar
                      mode="single"
                      selected={formData.srn_date}
                      onSelect={(d) => d && setFormData({...formData, srn_date: d})}
                    />
                  </PopoverContent>
                </Popover>
              </div>

              {/* Return Reason */}
              <div className="grid gap-2">
                <Label>Return Reason *</Label>
                <Select value={formData.return_reason} onValueChange={(v) => setFormData({...formData, return_reason: v})}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select reason" />
                  </SelectTrigger>
                  <SelectContent>
                    {returnReasons.map((r) => (
                      <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Reason Detail */}
            <div className="grid gap-2">
              <Label>Reason Details</Label>
              <Textarea
                value={formData.return_reason_detail}
                onChange={(e) => setFormData({...formData, return_reason_detail: e.target.value})}
                placeholder="Additional details about the return reason..."
              />
            </div>

            {/* Options */}
            <div className="flex gap-6">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="pickup_required"
                  checked={formData.pickup_required}
                  onCheckedChange={(c) => setFormData({...formData, pickup_required: !!c})}
                />
                <Label htmlFor="pickup_required">Pickup Required</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="qc_required"
                  checked={formData.qc_required}
                  onCheckedChange={(c) => setFormData({...formData, qc_required: !!c})}
                />
                <Label htmlFor="qc_required">QC Required</Label>
              </div>
            </div>

            {/* Pickup Details */}
            {formData.pickup_required && (
              <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
                <div className="grid gap-2">
                  <Label>Pickup Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className={cn("justify-start text-left font-normal")}>
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {formData.pickup_scheduled_date ? format(formData.pickup_scheduled_date, 'PP') : 'Schedule pickup'}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <Calendar
                        mode="single"
                        selected={formData.pickup_scheduled_date}
                        onSelect={(d) => setFormData({...formData, pickup_scheduled_date: d})}
                      />
                    </PopoverContent>
                  </Popover>
                </div>
                <div className="grid gap-2">
                  <Label>Contact Name</Label>
                  <Input
                    value={formData.pickup_contact_name}
                    onChange={(e) => setFormData({...formData, pickup_contact_name: e.target.value})}
                    placeholder="Contact name"
                  />
                </div>
                <div className="grid gap-2 col-span-2">
                  <Label>Contact Phone</Label>
                  <Input
                    value={formData.pickup_contact_phone}
                    onChange={(e) => setFormData({...formData, pickup_contact_phone: e.target.value})}
                    placeholder="Contact phone"
                  />
                </div>
              </div>
            )}

            {/* Order Items */}
            {selectedOrder?.items && selectedOrder.items.length > 0 && (
              <div className="space-y-2">
                <Label>Items to Return</Label>
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-muted">
                      <tr>
                        <th className="p-2 text-left">Product</th>
                        <th className="p-2 text-center">Ordered</th>
                        <th className="p-2 text-center">Price</th>
                        <th className="p-2 text-center">Return Qty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedOrder.items.map((item: OrderItem) => (
                        <tr key={item.id} className="border-t">
                          <td className="p-2">
                            <div className="font-medium">{item.product_name}</div>
                            <div className="text-xs text-muted-foreground">SKU: {item.sku}</div>
                          </td>
                          <td className="p-2 text-center">{item.quantity}</td>
                          <td className="p-2 text-center">{formatCurrency(item.unit_price)}</td>
                          <td className="p-2 text-center">
                            <Input
                              type="number"
                              min={0}
                              max={item.quantity}
                              value={returnQuantities[item.id] || 0}
                              onChange={(e) => setReturnQuantities({
                                ...returnQuantities,
                                [item.id]: Math.min(item.quantity, Math.max(0, parseInt(e.target.value) || 0))
                              })}
                              className="w-20 text-center"
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={resetCreateForm}>Cancel</Button>
            <Button onClick={handleCreate} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Return
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Details Sheet */}
      <Sheet open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
        <SheetContent className="w-[600px] sm:max-w-[600px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle>SRN Details - {selectedSRN?.srn_number}</SheetTitle>
            <SheetDescription>View return details and history</SheetDescription>
          </SheetHeader>
          {selectedSRN && (
            <div className="space-y-6 py-6">
              <div className="flex justify-between items-center">
                <StatusBadge status={selectedSRN.status} />
                <span className="text-2xl font-bold">{formatCurrency(selectedSRN.total_value)}</span>
              </div>

              <Separator />

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Customer:</span>
                  <p className="font-medium">{selectedSRN.customer_name}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Order:</span>
                  <p className="font-medium">{selectedSRN.order_number}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Return Reason:</span>
                  <p className="font-medium">{selectedSRN.return_reason?.replace(/_/g, ' ')}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Date:</span>
                  <p className="font-medium">{formatDate(selectedSRN.srn_date)}</p>
                </div>
              </div>

              {selectedSRN.pickup_required && (
                <>
                  <Separator />
                  <div>
                    <h4 className="font-semibold mb-2">Pickup Details</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Status:</span>
                        <p className="font-medium">{selectedSRN.pickup_status || 'Pending'}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Scheduled:</span>
                        <p className="font-medium">{selectedSRN.pickup_scheduled_date ? formatDate(selectedSRN.pickup_scheduled_date) : 'Not set'}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Courier:</span>
                        <p className="font-medium">{selectedSRN.courier_name || 'Not assigned'}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">AWB:</span>
                        <p className="font-medium">{selectedSRN.courier_tracking_number || 'N/A'}</p>
                      </div>
                    </div>
                  </div>
                </>
              )}

              <Separator />

              <div>
                <h4 className="font-semibold mb-2">Items</h4>
                <div className="space-y-2">
                  {selectedSRN.items?.map((item) => (
                    <div key={item.id} className="p-3 bg-muted rounded-lg">
                      <div className="flex justify-between">
                        <div>
                          <p className="font-medium">{item.product_name}</p>
                          <p className="text-xs text-muted-foreground">SKU: {item.sku}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium">{formatCurrency(item.return_value)}</p>
                          <p className="text-xs">Qty: {item.quantity_returned}</p>
                        </div>
                      </div>
                      {item.item_condition && (
                        <div className="mt-2 flex gap-2">
                          <Badge variant="outline" className="text-xs">{item.item_condition}</Badge>
                          <Badge variant="outline" className="text-xs">{item.restock_decision}</Badge>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="p-3 bg-muted rounded-lg">
                  <p className="text-2xl font-bold">{selectedSRN.total_quantity_returned}</p>
                  <p className="text-xs text-muted-foreground">Returned</p>
                </div>
                <div className="p-3 bg-green-50 rounded-lg">
                  <p className="text-2xl font-bold text-green-600">{selectedSRN.total_quantity_accepted}</p>
                  <p className="text-xs text-muted-foreground">Accepted</p>
                </div>
                <div className="p-3 bg-red-50 rounded-lg">
                  <p className="text-2xl font-bold text-red-600">{selectedSRN.total_quantity_rejected}</p>
                  <p className="text-xs text-muted-foreground">Rejected</p>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Pickup Update Dialog */}
      <Dialog open={isPickupDialogOpen} onOpenChange={setIsPickupDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Pickup Status</DialogTitle>
            <DialogDescription>Update pickup tracking information</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Pickup Status</Label>
              <Select value={pickupForm.pickup_status} onValueChange={(v) => setPickupForm({...pickupForm, pickup_status: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {pickupStatuses.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label>Courier Name</Label>
              <Input
                value={pickupForm.courier_name}
                onChange={(e) => setPickupForm({...pickupForm, courier_name: e.target.value})}
                placeholder="Enter courier name"
              />
            </div>
            <div className="grid gap-2">
              <Label>AWB / Tracking Number</Label>
              <Input
                value={pickupForm.courier_tracking_number}
                onChange={(e) => setPickupForm({...pickupForm, courier_tracking_number: e.target.value})}
                placeholder="Enter AWB number"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsPickupDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleUpdatePickup} disabled={updatePickupMutation.isPending}>
              {updatePickupMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Update
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Receive Dialog */}
      <Dialog open={isReceiveDialogOpen} onOpenChange={setIsReceiveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Receive Goods</DialogTitle>
            <DialogDescription>Mark returned goods as received</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Receiving Remarks</Label>
              <Textarea
                value={formData.receiving_remarks}
                onChange={(e) => setFormData({...formData, receiving_remarks: e.target.value})}
                placeholder="Any notes about the received goods..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsReceiveDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleReceive} disabled={receiveMutation.isPending}>
              {receiveMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Receive Goods
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* QC Dialog */}
      <Dialog open={isQCDialogOpen} onOpenChange={setIsQCDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Quality Check - {selectedSRN?.srn_number}</DialogTitle>
            <DialogDescription>Inspect returned items and decide restock action</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            {selectedSRN?.items?.map((item) => (
              <div key={item.id} className="p-4 border rounded-lg mb-4">
                <div className="flex justify-between mb-4">
                  <div>
                    <p className="font-semibold">{item.product_name}</p>
                    <p className="text-sm text-muted-foreground">SKU: {item.sku} | Qty: {item.quantity_returned}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label>Condition</Label>
                    <Select
                      value={qcResults[item.id]?.item_condition || 'LIKE_NEW'}
                      onValueChange={(v) => setQcResults({
                        ...qcResults,
                        [item.id]: { ...qcResults[item.id], item_condition: v }
                      })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {itemConditions.map((c) => (
                          <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label>Restock Decision</Label>
                    <Select
                      value={qcResults[item.id]?.restock_decision || 'RESTOCK_AS_NEW'}
                      onValueChange={(v) => setQcResults({
                        ...qcResults,
                        [item.id]: { ...qcResults[item.id], restock_decision: v }
                      })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {restockDecisions.map((d) => (
                          <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label>Accept Qty</Label>
                    <Input
                      type="number"
                      min={0}
                      max={item.quantity_returned}
                      value={qcResults[item.id]?.quantity_accepted ?? item.quantity_returned}
                      onChange={(e) => {
                        const accepted = parseInt(e.target.value) || 0;
                        setQcResults({
                          ...qcResults,
                          [item.id]: {
                            ...qcResults[item.id],
                            quantity_accepted: accepted,
                            quantity_rejected: item.quantity_returned - accepted,
                            qc_result: accepted === item.quantity_returned ? 'ACCEPTED' : accepted === 0 ? 'REJECTED' : 'PARTIAL'
                          }
                        });
                      }}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label>Reject Qty</Label>
                    <Input
                      type="number"
                      value={qcResults[item.id]?.quantity_rejected ?? 0}
                      disabled
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsQCDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleProcessQC} disabled={processQCMutation.isPending}>
              {processQCMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Complete QC
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Put-Away Dialog */}
      <Dialog open={isPutAwayDialogOpen} onOpenChange={setIsPutAwayDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Put-Away - {selectedSRN?.srn_number}</DialogTitle>
            <DialogDescription>Assign bin locations for accepted items</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            {selectedSRN?.items?.filter(i => i.quantity_accepted > 0).map((item) => (
              <div key={item.id} className="flex justify-between items-center p-3 border rounded-lg mb-2">
                <div>
                  <p className="font-medium">{item.product_name}</p>
                  <p className="text-sm text-muted-foreground">Accepted: {item.quantity_accepted}</p>
                </div>
                <Input
                  placeholder="Bin location"
                  value={putAwayLocations[item.id] || ''}
                  onChange={(e) => setPutAwayLocations({...putAwayLocations, [item.id]: e.target.value})}
                  className="w-48"
                />
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsPutAwayDialogOpen(false)}>Cancel</Button>
            <Button onClick={handlePutAway} disabled={putAwayMutation.isPending}>
              {putAwayMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Complete Put-Away
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Resolve Dialog */}
      <Dialog open={isResolveDialogOpen} onOpenChange={setIsResolveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resolve Return - {selectedSRN?.srn_number}</DialogTitle>
            <DialogDescription>Choose how to resolve this return</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Resolution Type *</Label>
              <Select value={resolveForm.resolution_type} onValueChange={(v) => setResolveForm({...resolveForm, resolution_type: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Select resolution" />
                </SelectTrigger>
                <SelectContent>
                  {resolutionTypes.map((r) => (
                    <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label>Notes</Label>
              <Textarea
                value={resolveForm.notes}
                onChange={(e) => setResolveForm({...resolveForm, notes: e.target.value})}
                placeholder="Additional notes..."
              />
            </div>
            {selectedSRN && (
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Return Value:</p>
                <p className="text-2xl font-bold">{formatCurrency(selectedSRN.total_value)}</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsResolveDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleResolve} disabled={resolveMutation.isPending}>
              {resolveMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Resolve
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete SRN?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete {srnToDelete?.srn_number}? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => srnToDelete && deleteMutation.mutate(srnToDelete.id)}
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
