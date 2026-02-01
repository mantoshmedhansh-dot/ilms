'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  MoreHorizontal, Plus, Eye, ArrowRightLeft, Warehouse, Package,
  CheckCircle, Loader2, Send, Truck, XCircle
} from 'lucide-react';
import Link from 'next/link';
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
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { transfersApi } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface TransferItem {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  received_quantity?: number;
}

interface StockTransfer {
  id: string;
  transfer_number: string;
  source_warehouse_id: string;
  destination_warehouse_id: string;
  status: 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'IN_TRANSIT' | 'RECEIVED' | 'CANCELLED';
  total_quantity: number;
  transfer_date: string;
  notes?: string;
  created_at: string;
  source_warehouse?: { id: string; name: string; code: string };
  destination_warehouse?: { id: string; name: string; code: string };
  items?: TransferItem[];
}

// Actions cell component
function TransferActionsCell({
  transfer,
  onView,
  onReceive,
  onSubmit,
  onApprove,
  onShip,
}: {
  transfer: StockTransfer;
  onView: (transfer: StockTransfer) => void;
  onReceive: (transfer: StockTransfer) => void;
  onSubmit: (transfer: StockTransfer) => void;
  onApprove: (transfer: StockTransfer) => void;
  onShip: (transfer: StockTransfer) => void;
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
        <DropdownMenuItem onClick={() => onView(transfer)}>
          <Eye className="mr-2 h-4 w-4" />
          View Details
        </DropdownMenuItem>

        {/* Status-based actions */}
        {transfer.status === 'DRAFT' && (
          <DropdownMenuItem onClick={() => onSubmit(transfer)}>
            <Send className="mr-2 h-4 w-4" />
            Submit for Approval
          </DropdownMenuItem>
        )}
        {transfer.status === 'PENDING_APPROVAL' && (
          <DropdownMenuItem onClick={() => onApprove(transfer)}>
            <CheckCircle className="mr-2 h-4 w-4" />
            Approve
          </DropdownMenuItem>
        )}
        {transfer.status === 'APPROVED' && (
          <DropdownMenuItem onClick={() => onShip(transfer)}>
            <Truck className="mr-2 h-4 w-4" />
            Mark as Shipped
          </DropdownMenuItem>
        )}
        {transfer.status === 'IN_TRANSIT' && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => onReceive(transfer)}
              className="text-green-600 focus:text-green-600"
            >
              <Package className="mr-2 h-4 w-4" />
              Receive Stock
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function TransfersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Dialog/Sheet states
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [selectedTransfer, setSelectedTransfer] = useState<StockTransfer | null>(null);
  const [transferDetails, setTransferDetails] = useState<StockTransfer | null>(null);
  const [isReceiveDialogOpen, setIsReceiveDialogOpen] = useState(false);
  const [receiveItems, setReceiveItems] = useState<{ id: string; received_quantity: number }[]>([]);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Queries
  const { data, isLoading } = useQuery({
    queryKey: ['transfers', page, pageSize, statusFilter],
    queryFn: () => transfersApi.list({
      page: page + 1,
      size: pageSize,
      status: statusFilter !== 'all' ? statusFilter : undefined,
    }),
  });

  // Mutations
  const submitMutation = useMutation({
    mutationFn: (id: string) => transfersApi.submit(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfers'] });
      toast.success('Transfer submitted for approval');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to submit transfer'),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => transfersApi.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfers'] });
      toast.success('Transfer approved');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to approve transfer'),
  });

  const shipMutation = useMutation({
    mutationFn: (id: string) => transfersApi.ship(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfers'] });
      toast.success('Transfer marked as shipped');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to ship transfer'),
  });

  const receiveMutation = useMutation({
    mutationFn: ({ id, items }: { id: string; items?: { stock_item_id: string; received_quantity: number }[] }) =>
      transfersApi.receive(id, items),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfers'] });
      toast.success('Stock received successfully! Inventory updated.');
      setIsReceiveDialogOpen(false);
      setSelectedTransfer(null);
      setReceiveItems([]);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to receive stock'),
  });

  // Handlers
  const handleView = async (transfer: StockTransfer) => {
    setSelectedTransfer(transfer);
    setIsViewOpen(true);
    setIsLoadingDetails(true);

    try {
      const details = await transfersApi.getById(transfer.id);
      setTransferDetails(details);
    } catch {
      setTransferDetails(transfer);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  const handleReceive = async (transfer: StockTransfer) => {
    setSelectedTransfer(transfer);
    setIsLoadingDetails(true);

    try {
      const details = await transfersApi.getById(transfer.id);
      setTransferDetails(details);
      // Initialize receive items with full quantity
      if (details.items) {
        setReceiveItems(details.items.map((item: TransferItem) => ({
          id: item.id,
          received_quantity: item.quantity,
        })));
      }
    } catch {
      setTransferDetails(transfer);
      if (transfer.items) {
        setReceiveItems(transfer.items.map((item: TransferItem) => ({
          id: item.id,
          received_quantity: item.quantity,
        })));
      }
    } finally {
      setIsLoadingDetails(false);
      setIsReceiveDialogOpen(true);
    }
  };

  const handleConfirmReceive = () => {
    if (!selectedTransfer) return;

    // Map to API format
    const items = receiveItems.map(item => ({
      stock_item_id: item.id,
      received_quantity: item.received_quantity,
    }));

    receiveMutation.mutate({ id: selectedTransfer.id, items });
  };

  const updateReceiveQuantity = (itemId: string, quantity: number) => {
    setReceiveItems(prev =>
      prev.map(item =>
        item.id === itemId ? { ...item, received_quantity: quantity } : item
      )
    );
  };

  const columns: ColumnDef<StockTransfer>[] = [
    {
      accessorKey: 'transfer_number',
      header: 'Transfer #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <ArrowRightLeft className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium font-mono">{row.original.transfer_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'source',
      header: 'From',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Warehouse className="h-4 w-4 text-red-500" />
          <span className="text-sm">
            {row.original.source_warehouse?.name || 'N/A'}
          </span>
        </div>
      ),
    },
    {
      accessorKey: 'destination',
      header: 'To',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Warehouse className="h-4 w-4 text-green-500" />
          <span className="text-sm">
            {row.original.destination_warehouse?.name || 'N/A'}
          </span>
        </div>
      ),
    },
    {
      accessorKey: 'total_quantity',
      header: 'Quantity',
      cell: ({ row }) => (
        <Badge variant="secondary">{row.original.total_quantity} units</Badge>
      ),
    },
    {
      accessorKey: 'transfer_date',
      header: 'Transfer Date',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {formatDate(row.original.transfer_date)}
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
        <TransferActionsCell
          transfer={row.original}
          onView={handleView}
          onReceive={handleReceive}
          onSubmit={(t) => submitMutation.mutate(t.id)}
          onApprove={(t) => approveMutation.mutate(t.id)}
          onShip={(t) => shipMutation.mutate(t.id)}
        />
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Stock Transfers"
        description="Manage inventory transfers between warehouses"
        actions={
          <div className="flex items-center gap-2">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="DRAFT">Draft</SelectItem>
                <SelectItem value="PENDING_APPROVAL">Pending Approval</SelectItem>
                <SelectItem value="APPROVED">Approved</SelectItem>
                <SelectItem value="IN_TRANSIT">In Transit</SelectItem>
                <SelectItem value="RECEIVED">Received</SelectItem>
                <SelectItem value="CANCELLED">Cancelled</SelectItem>
              </SelectContent>
            </Select>
            <Button asChild>
              <Link href="/dashboard/inventory/transfers/new">
                <Plus className="mr-2 h-4 w-4" />
                New Transfer
              </Link>
            </Button>
          </div>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="transfer_number"
        searchPlaceholder="Search transfers..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* View Details Sheet */}
      <Sheet open={isViewOpen} onOpenChange={setIsViewOpen}>
        <SheetContent className="w-[500px] sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <ArrowRightLeft className="h-5 w-5" />
              {selectedTransfer?.transfer_number}
            </SheetTitle>
            <SheetDescription>
              Stock Transfer Details
            </SheetDescription>
          </SheetHeader>

          {isLoadingDetails ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : transferDetails && (
            <div className="mt-6 space-y-6">
              <div className="flex items-center justify-between">
                <StatusBadge status={transferDetails.status} />
                <span className="text-sm text-muted-foreground">
                  {formatDate(transferDetails.created_at)}
                </span>
              </div>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Transfer Route</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 flex-1">
                      <Warehouse className="h-4 w-4 text-red-500" />
                      <div>
                        <p className="text-xs text-muted-foreground">From</p>
                        <p className="font-medium">{transferDetails.source_warehouse?.name}</p>
                      </div>
                    </div>
                    <ArrowRightLeft className="h-4 w-4 text-muted-foreground" />
                    <div className="flex items-center gap-2 flex-1">
                      <Warehouse className="h-4 w-4 text-green-500" />
                      <div>
                        <p className="text-xs text-muted-foreground">To</p>
                        <p className="font-medium">{transferDetails.destination_warehouse?.name}</p>
                      </div>
                    </div>
                  </div>
                  <Separator />
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Transfer Date:</span>
                    <span>{formatDate(transferDetails.transfer_date)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Total Quantity:</span>
                    <span className="font-medium">{transferDetails.total_quantity} units</span>
                  </div>
                </CardContent>
              </Card>

              {/* Items */}
              {transferDetails.items && transferDetails.items.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Package className="h-4 w-4" />
                      Items ({transferDetails.items.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {transferDetails.items.map((item: TransferItem, index: number) => (
                        <div key={item.id || index} className="flex justify-between items-center py-2 border-b last:border-0">
                          <div>
                            <p className="font-medium text-sm">{item.product_name}</p>
                            <p className="text-xs text-muted-foreground font-mono">{item.sku}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium">{item.quantity} units</p>
                            {item.received_quantity !== undefined && (
                              <p className="text-xs text-green-600">
                                Received: {item.received_quantity}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {transferDetails.notes && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Notes</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{transferDetails.notes}</p>
                  </CardContent>
                </Card>
              )}

              {/* Action button for IN_TRANSIT */}
              {transferDetails.status === 'IN_TRANSIT' && (
                <Button
                  className="w-full"
                  onClick={() => {
                    setIsViewOpen(false);
                    handleReceive(transferDetails);
                  }}
                >
                  <Package className="mr-2 h-4 w-4" />
                  Receive Stock
                </Button>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Receive Stock Dialog */}
      <Dialog open={isReceiveDialogOpen} onOpenChange={setIsReceiveDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="h-5 w-5 text-green-600" />
              Receive Stock Transfer
            </DialogTitle>
            <DialogDescription>
              Confirm received quantities for transfer {selectedTransfer?.transfer_number}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Transfer Info */}
            <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
              <div>
                <p className="text-xs text-muted-foreground">From Warehouse</p>
                <p className="font-medium">{transferDetails?.source_warehouse?.name}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">To Warehouse</p>
                <p className="font-medium">{transferDetails?.destination_warehouse?.name}</p>
              </div>
            </div>

            {/* Items to Receive */}
            <div className="space-y-2">
              <Label className="text-base font-semibold">Items to Receive</Label>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      <th className="px-4 py-2 text-left">Product</th>
                      <th className="px-4 py-2 text-right">Sent Qty</th>
                      <th className="px-4 py-2 text-right">Received Qty</th>
                      <th className="px-4 py-2 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transferDetails?.items?.map((item: TransferItem, index: number) => {
                      const receiveItem = receiveItems.find(r => r.id === item.id);
                      const receivedQty = receiveItem?.received_quantity ?? item.quantity;
                      const isShort = receivedQty < item.quantity;

                      return (
                        <tr key={item.id || index} className="border-t">
                          <td className="px-4 py-3">
                            <p className="font-medium">{item.product_name}</p>
                            <p className="text-xs text-muted-foreground font-mono">{item.sku}</p>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <Badge variant="outline">{item.quantity}</Badge>
                          </td>
                          <td className="px-4 py-3">
                            <Input
                              type="number"
                              min="0"
                              max={item.quantity}
                              className="w-24 text-right ml-auto"
                              value={receivedQty}
                              onChange={(e) => updateReceiveQuantity(item.id, parseInt(e.target.value) || 0)}
                            />
                          </td>
                          <td className="px-4 py-3 text-center">
                            {isShort ? (
                              <Badge variant="destructive" className="text-xs">
                                <XCircle className="h-3 w-3 mr-1" />
                                Short
                              </Badge>
                            ) : (
                              <Badge variant="default" className="text-xs bg-green-600">
                                <CheckCircle className="h-3 w-3 mr-1" />
                                Full
                              </Badge>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Summary */}
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm font-medium text-green-800">Total to Receive</p>
                  <p className="text-xs text-green-600">
                    Inventory will be added to {transferDetails?.destination_warehouse?.name}
                  </p>
                </div>
                <p className="text-2xl font-bold text-green-700">
                  {receiveItems.reduce((sum, item) => sum + item.received_quantity, 0)} units
                </p>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsReceiveDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleConfirmReceive}
              disabled={receiveMutation.isPending}
              className="bg-green-600 hover:bg-green-700"
            >
              {receiveMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <CheckCircle className="mr-2 h-4 w-4" />
              Confirm Receipt
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
