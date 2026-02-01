'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, Truck, MapPin, Package, Loader2, CheckCircle, RotateCcw, Download, Printer, Trash2 } from 'lucide-react';
import Link from 'next/link';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { shipmentsApi, transportersApi, warehousesApi } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface Shipment {
  id: string;
  shipment_number: string;
  order_id?: string;
  order?: { order_number: string };
  order_number?: string;
  awb_number?: string;
  tracking_number?: string;
  transporter_id?: string;
  transporter?: { id: string; name: string; code: string };
  warehouse_id?: string;
  warehouse?: { name: string };
  status: string;
  ship_to_name?: string;
  ship_to_phone?: string;
  ship_to_address?: string;
  ship_to_city: string;
  ship_to_state: string;
  ship_to_pincode: string;
  weight_kg?: number;
  no_of_boxes?: number;
  shipped_at?: string;
  expected_delivery_date?: string;
  delivered_at?: string;
  created_at: string;
}

const shipmentStatuses = [
  { value: 'PENDING', label: 'Pending' },
  { value: 'PACKED', label: 'Packed' },
  { value: 'READY_FOR_PICKUP', label: 'Ready for Pickup' },
  { value: 'PICKED_UP', label: 'Picked Up' },
  { value: 'IN_TRANSIT', label: 'In Transit' },
  { value: 'OUT_FOR_DELIVERY', label: 'Out for Delivery' },
  { value: 'DELIVERED', label: 'Delivered' },
  { value: 'FAILED', label: 'Failed' },
  { value: 'RTO_INITIATED', label: 'RTO Initiated' },
  { value: 'RTO_DELIVERED', label: 'RTO Delivered' },
];

export default function ShipmentsPage() {
  const { permissions } = useAuth();
  const isSuperAdmin = permissions?.is_super_admin ?? false;
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [isStatusDialogOpen, setIsStatusDialogOpen] = useState(false);
  const [isDeliveryDialogOpen, setIsDeliveryDialogOpen] = useState(false);
  const [isRtoDialogOpen, setIsRtoDialogOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [shipmentToDelete, setShipmentToDelete] = useState<Shipment | null>(null);
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(null);
  const [newStatus, setNewStatus] = useState('');
  const [statusRemarks, setStatusRemarks] = useState('');
  const [deliveryData, setDeliveryData] = useState({ receiver_name: '', receiver_phone: '', delivery_notes: '' });
  const [rtoReason, setRtoReason] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['shipments', page, pageSize, statusFilter],
    queryFn: () => shipmentsApi.list({ page: page + 1, size: pageSize, status: statusFilter || undefined }),
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status, remarks }: { id: string; status: string; remarks?: string }) =>
      shipmentsApi.updateStatus(id, status, remarks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shipments'] });
      toast.success('Shipment status updated');
      setIsStatusDialogOpen(false);
      setNewStatus('');
      setStatusRemarks('');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update status'),
  });

  const deliverMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: typeof deliveryData }) =>
      shipmentsApi.markDelivered(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shipments'] });
      toast.success('Shipment marked as delivered');
      setIsDeliveryDialogOpen(false);
      setDeliveryData({ receiver_name: '', receiver_phone: '', delivery_notes: '' });
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to mark as delivered'),
  });

  const rtoMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      shipmentsApi.initiateRTO(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shipments'] });
      toast.success('RTO initiated');
      setIsRtoDialogOpen(false);
      setRtoReason('');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to initiate RTO'),
  });

  const deleteMutation = useMutation({
    mutationFn: shipmentsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shipments'] });
      toast.success('Shipment deleted successfully');
      setIsDeleteOpen(false);
      setShipmentToDelete(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete shipment'),
  });

  const handleDownloadLabel = async (shipment: Shipment) => {
    try {
      // Fetch HTML with auth token, then open in new tab
      const htmlContent = await shipmentsApi.downloadLabel(shipment.id);
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => window.URL.revokeObjectURL(url);
      }
      toast.success('Opening shipping label for download/print');
    } catch {
      toast.error('Failed to download shipping label');
    }
  };

  const handlePrint = async (shipment: Shipment) => {
    try {
      // Fetch HTML with auth token, then open in new tab for printing
      const htmlContent = await shipmentsApi.downloadLabel(shipment.id);
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
      toast.error('Failed to print shipment');
    }
  };

  const columns: ColumnDef<Shipment>[] = [
    {
      accessorKey: 'shipment_number',
      header: 'Shipment #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Package className="h-4 w-4 text-muted-foreground" />
          <div>
            <Link href={`/dashboard/logistics/shipments/${row.original.id}`} className="font-medium hover:underline">
              {row.original.shipment_number}
            </Link>
            {(row.original.awb_number || row.original.tracking_number) && (
              <div className="text-xs text-muted-foreground font-mono">
                {row.original.awb_number || row.original.tracking_number}
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'order_number',
      header: 'Order',
      cell: ({ row }) => (
        <span className="text-sm">
          {row.original.order?.order_number || row.original.order_number || '-'}
        </span>
      ),
    },
    {
      accessorKey: 'transporter',
      header: 'Transporter',
      cell: ({ row }) => (
        <div className="flex items-center gap-1 text-sm">
          <Truck className="h-3 w-3 text-muted-foreground" />
          {row.original.transporter?.name || 'Not assigned'}
        </div>
      ),
    },
    {
      accessorKey: 'destination',
      header: 'Destination',
      cell: ({ row }) => (
        <div className="flex items-center gap-1 text-sm">
          <MapPin className="h-3 w-3 text-muted-foreground" />
          <div>
            <div>{row.original.ship_to_city}, {row.original.ship_to_pincode}</div>
            {row.original.ship_to_name && (
              <div className="text-xs text-muted-foreground">{row.original.ship_to_name}</div>
            )}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'dates',
      header: 'Timeline',
      cell: ({ row }) => (
        <div className="text-sm">
          {row.original.shipped_at && (
            <div className="text-muted-foreground">
              Shipped: {formatDate(row.original.shipped_at)}
            </div>
          )}
          {row.original.expected_delivery_date && (
            <div>
              ETA: {formatDate(row.original.expected_delivery_date)}
            </div>
          )}
          {row.original.delivered_at && (
            <div className="text-green-600">
              Delivered: {formatDate(row.original.delivered_at)}
            </div>
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
            <DropdownMenuItem asChild>
              <Link href={`/dashboard/logistics/shipments/${row.original.id}`}>
                <Eye className="mr-2 h-4 w-4" />
                View Details
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleDownloadLabel(row.original)}>
              <Download className="mr-2 h-4 w-4" />
              Download Label
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handlePrint(row.original)}>
              <Printer className="mr-2 h-4 w-4" />
              Print
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => {
              setSelectedShipment(row.original);
              setIsStatusDialogOpen(true);
            }}>
              <Truck className="mr-2 h-4 w-4" />
              Update Status
            </DropdownMenuItem>
            {!['DELIVERED', 'RTO_DELIVERED', 'RTO_INITIATED'].includes(row.original.status) && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => {
                  setSelectedShipment(row.original);
                  setIsDeliveryDialogOpen(true);
                }}>
                  <CheckCircle className="mr-2 h-4 w-4 text-green-600" />
                  Mark Delivered
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => {
                  setSelectedShipment(row.original);
                  setIsRtoDialogOpen(true);
                }} className="text-orange-600">
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Initiate RTO
                </DropdownMenuItem>
              </>
            )}
            {isSuperAdmin && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => { setShipmentToDelete(row.original); setIsDeleteOpen(true); }}
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

  return (
    <div className="space-y-6">
      <PageHeader
        title="Shipments"
        description="Track and manage order shipments"
      />

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Select value={statusFilter || 'all'} onValueChange={(v) => setStatusFilter(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            {shipmentStatuses.map((status) => (
              <SelectItem key={status.value} value={status.value}>
                {status.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="shipment_number"
        searchPlaceholder="Search shipments..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Update Status Dialog */}
      <Dialog open={isStatusDialogOpen} onOpenChange={setIsStatusDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Shipment Status</DialogTitle>
            <DialogDescription>
              Update status for {selectedShipment?.shipment_number}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>New Status</Label>
              <Select value={newStatus} onValueChange={setNewStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {shipmentStatuses.map((status) => (
                    <SelectItem key={status.value} value={status.value}>
                      {status.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Remarks (Optional)</Label>
              <Input
                placeholder="Add remarks..."
                value={statusRemarks}
                onChange={(e) => setStatusRemarks(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsStatusDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={() => selectedShipment && updateStatusMutation.mutate({
                id: selectedShipment.id,
                status: newStatus,
                remarks: statusRemarks || undefined,
              })}
              disabled={!newStatus || updateStatusMutation.isPending}
            >
              {updateStatusMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Update Status
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Mark Delivered Dialog */}
      <Dialog open={isDeliveryDialogOpen} onOpenChange={setIsDeliveryDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mark as Delivered</DialogTitle>
            <DialogDescription>
              Record delivery details for {selectedShipment?.shipment_number}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Receiver Name</Label>
              <Input
                placeholder="Name of person who received"
                value={deliveryData.receiver_name}
                onChange={(e) => setDeliveryData({ ...deliveryData, receiver_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Receiver Phone</Label>
              <Input
                placeholder="Phone number"
                value={deliveryData.receiver_phone}
                onChange={(e) => setDeliveryData({ ...deliveryData, receiver_phone: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Delivery Notes (Optional)</Label>
              <Input
                placeholder="Any notes..."
                value={deliveryData.delivery_notes}
                onChange={(e) => setDeliveryData({ ...deliveryData, delivery_notes: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeliveryDialogOpen(false)}>Cancel</Button>
            <Button
              className="bg-green-600 hover:bg-green-700"
              onClick={() => selectedShipment && deliverMutation.mutate({
                id: selectedShipment.id,
                data: deliveryData,
              })}
              disabled={deliverMutation.isPending}
            >
              {deliverMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <CheckCircle className="mr-2 h-4 w-4" />
              Mark Delivered
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* RTO Dialog */}
      <Dialog open={isRtoDialogOpen} onOpenChange={setIsRtoDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Initiate RTO</DialogTitle>
            <DialogDescription>
              Return to Origin for {selectedShipment?.shipment_number}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>RTO Reason *</Label>
              <Input
                placeholder="Reason for returning"
                value={rtoReason}
                onChange={(e) => setRtoReason(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRtoDialogOpen(false)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => selectedShipment && rtoMutation.mutate({
                id: selectedShipment.id,
                reason: rtoReason,
              })}
              disabled={!rtoReason || rtoMutation.isPending}
            >
              {rtoMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <RotateCcw className="mr-2 h-4 w-4" />
              Initiate RTO
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Shipment Confirmation */}
      <AlertDialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Shipment</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete shipment <strong>{shipmentToDelete?.shipment_number}</strong>?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => shipmentToDelete && deleteMutation.mutate(shipmentToDelete.id)}
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
