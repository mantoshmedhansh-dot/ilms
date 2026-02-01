'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { toast } from 'sonner';
import {
  MoreHorizontal,
  Plus,
  Eye,
  Download,
  FileStack,
  Truck,
  Package,
  CheckCircle,
  Loader2,
  Send,
  ClipboardCheck,
  Search,
  XCircle,
  Printer,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
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
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { formatDate } from '@/lib/utils';
import { manifestsApi, transportersApi, warehousesApi, shipmentsApi } from '@/lib/api';

interface Manifest {
  id: string;
  manifest_number: string;
  transporter_id: string;
  transporter?: { id: string; name: string; code: string };
  warehouse_id: string;
  warehouse?: { id: string; name: string; code: string };
  status: 'DRAFT' | 'CONFIRMED' | 'FINALIZED' | 'HANDED_OVER' | 'IN_TRANSIT' | 'COMPLETED' | 'CANCELLED';
  shipments_count: number;
  total_weight?: number;
  vehicle_number?: string;
  driver_name?: string;
  driver_phone?: string;
  handover_date?: string;
  handover_time?: string;
  handover_remarks?: string;
  created_at: string;
  shipments?: ManifestShipment[];
}

interface ManifestShipment {
  id: string;
  shipment_number?: string;
  awb_number?: string;
  order_number?: string;
  order?: { order_number: string };
  ship_to_name?: string;
  ship_to_city?: string;
  ship_to_pincode?: string;
  weight_kg?: number;
  no_of_boxes?: number;
  payment_mode?: 'PREPAID' | 'COD';
  cod_amount?: number;
  status?: string;
}

interface Transporter {
  id: string;
  name: string;
  code: string;
}

interface Warehouse {
  id: string;
  name: string;
  code: string;
}

interface PendingShipment {
  id: string;
  shipment_number?: string;
  awb_number?: string;
  order_number?: string;
  ship_to_name?: string;
  ship_to_city?: string;
  ship_to_pincode?: string;
  weight_kg?: number;
  no_of_boxes?: number;
  payment_mode?: 'PREPAID' | 'COD';
  cod_amount?: number;
}

const statusColors: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-800',
  CONFIRMED: 'bg-blue-100 text-blue-800',
  FINALIZED: 'bg-blue-100 text-blue-800',
  HANDED_OVER: 'bg-green-100 text-green-800',
  IN_TRANSIT: 'bg-purple-100 text-purple-800',
  COMPLETED: 'bg-green-100 text-green-800',
  CANCELLED: 'bg-red-100 text-red-800',
};

export default function ManifestsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Dialog states
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isAddShipmentsDialogOpen, setIsAddShipmentsDialogOpen] = useState(false);
  const [isHandoverDialogOpen, setIsHandoverDialogOpen] = useState(false);
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);
  const [selectedManifest, setSelectedManifest] = useState<Manifest | null>(null);
  const [selectedShipmentIds, setSelectedShipmentIds] = useState<string[]>([]);

  // Form states
  const [createForm, setCreateForm] = useState({ transporter_id: '', warehouse_id: '' });
  const [handoverForm, setHandoverForm] = useState({ vehicle_number: '', driver_name: '', driver_phone: '' });

  // Queries
  const { data, isLoading } = useQuery({
    queryKey: ['manifests', page, pageSize, statusFilter],
    queryFn: () => manifestsApi.list({ page: page + 1, size: pageSize, status: statusFilter || undefined }),
  });

  const { data: transportersData } = useQuery({
    queryKey: ['transporters-list'],
    queryFn: () => transportersApi.list({ size: 100, is_active: true }),
  });

  const { data: warehousesData } = useQuery({
    queryKey: ['warehouses-list'],
    queryFn: () => warehousesApi.list({ size: 100, is_active: true }),
  });

  // Pending shipments for adding to manifest - shipments that are READY_FOR_PICKUP status
  const { data: pendingShipmentsData, isLoading: loadingPending } = useQuery({
    queryKey: ['pending-shipments', selectedManifest?.warehouse_id, selectedManifest?.transporter_id],
    queryFn: () => shipmentsApi.list({
      warehouse_id: selectedManifest!.warehouse_id,
      transporter_id: selectedManifest!.transporter_id,
      status: 'READY_FOR_PICKUP',
      size: 100,
    }),
    enabled: isAddShipmentsDialogOpen && !!selectedManifest,
  });

  const { data: manifestDetail } = useQuery({
    queryKey: ['manifest-detail', selectedManifest?.id],
    queryFn: () => manifestsApi.getById(selectedManifest!.id),
    enabled: isDetailDialogOpen && !!selectedManifest,
  });

  // Transform data for easier use
  const transporters = transportersData?.items || [];
  const warehouses = warehousesData?.items || [];
  const pendingShipments = pendingShipmentsData?.items || [];

  // Mutations
  const createMutation = useMutation({
    mutationFn: () => manifestsApi.create({
      warehouse_id: createForm.warehouse_id,
      transporter_id: createForm.transporter_id,
    }),
    onSuccess: (newManifest) => {
      queryClient.invalidateQueries({ queryKey: ['manifests'] });
      toast.success(`Manifest ${newManifest.manifest_number} created`);
      setIsCreateDialogOpen(false);
      setCreateForm({ transporter_id: '', warehouse_id: '' });
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create manifest'),
  });

  const addShipmentsMutation = useMutation({
    mutationFn: () => manifestsApi.addShipments(selectedManifest!.id, selectedShipmentIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manifests'] });
      queryClient.invalidateQueries({ queryKey: ['pending-shipments'] });
      queryClient.invalidateQueries({ queryKey: ['manifest-detail'] });
      toast.success(`${selectedShipmentIds.length} shipments added to manifest`);
      setIsAddShipmentsDialogOpen(false);
      setSelectedShipmentIds([]);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to add shipments'),
  });

  const removeShipmentMutation = useMutation({
    mutationFn: (shipmentId: string) => manifestsApi.removeShipments(selectedManifest!.id, [shipmentId]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manifests'] });
      queryClient.invalidateQueries({ queryKey: ['manifest-detail'] });
      toast.success('Shipment removed from manifest');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to remove shipment'),
  });

  const confirmMutation = useMutation({
    mutationFn: (manifestId: string) => manifestsApi.confirm(manifestId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manifests'] });
      toast.success('Manifest confirmed');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to confirm manifest'),
  });

  const handoverMutation = useMutation({
    mutationFn: () => manifestsApi.handover(selectedManifest!.id, `Vehicle: ${handoverForm.vehicle_number}, Driver: ${handoverForm.driver_name}, Phone: ${handoverForm.driver_phone}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manifests'] });
      toast.success('Manifest handed over successfully');
      setIsHandoverDialogOpen(false);
      setHandoverForm({ vehicle_number: '', driver_name: '', driver_phone: '' });
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to handover manifest'),
  });

  const cancelMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => manifestsApi.cancel(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manifests'] });
      toast.success('Manifest cancelled');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to cancel manifest'),
  });

  const handleDownload = async (manifest: Manifest) => {
    try {
      const printData = await manifestsApi.getPrintData(manifest.id);
      // Create a printable HTML view
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.write(`
          <html>
            <head>
              <title>${manifest.manifest_number}</title>
              <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                h1 { color: #333; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
              </style>
            </head>
            <body>
              <h1>Manifest: ${printData.manifest_number}</h1>
              <p><strong>Transporter:</strong> ${printData.transporter?.name || 'N/A'}</p>
              <p><strong>Warehouse:</strong> ${printData.warehouse?.name || 'N/A'}</p>
              <p><strong>Status:</strong> ${printData.status}</p>
              <p><strong>Shipments:</strong> ${printData.shipments_count || 0}</p>
              <p><strong>Total Weight:</strong> ${printData.total_weight || 0} kg</p>
              <button onclick="window.print()">Print</button>
            </body>
          </html>
        `);
        printWindow.document.close();
      }
      toast.success('Manifest opened for print');
    } catch {
      toast.error('Failed to get manifest print data');
    }
  };

  const toggleShipmentSelection = (shipmentId: string) => {
    setSelectedShipmentIds((prev) =>
      prev.includes(shipmentId)
        ? prev.filter((id) => id !== shipmentId)
        : [...prev, shipmentId]
    );
  };

  const selectAllShipments = () => {
    if (pendingShipments) {
      if (selectedShipmentIds.length === pendingShipments.length) {
        setSelectedShipmentIds([]);
      } else {
        setSelectedShipmentIds(pendingShipments.map((s: PendingShipment) => s.id));
      }
    }
  };

  const columns: ColumnDef<Manifest>[] = [
    {
      accessorKey: 'manifest_number',
      header: 'Manifest #',
      cell: ({ row }) => (
        <div
          className="flex items-center gap-2 cursor-pointer hover:text-primary"
          onClick={() => {
            setSelectedManifest(row.original);
            setIsDetailDialogOpen(true);
          }}
        >
          <FileStack className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.original.manifest_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'transporter',
      header: 'Transporter',
      cell: ({ row }) => (
        <div className="flex items-center gap-1 text-sm">
          <Truck className="h-3 w-3 text-muted-foreground" />
          {row.original.transporter?.name || 'N/A'}
        </div>
      ),
    },
    {
      accessorKey: 'warehouse',
      header: 'Warehouse',
      cell: ({ row }) => (
        <span className="text-sm">{row.original.warehouse?.name || 'N/A'}</span>
      ),
    },
    {
      accessorKey: 'shipments_count',
      header: 'Shipments',
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Package className="h-3 w-3 text-muted-foreground" />
          <span className="font-medium">{row.original.shipments_count}</span>
        </div>
      ),
    },
    {
      accessorKey: 'total_weight',
      header: 'Weight',
      cell: ({ row }) => (
        <span className="text-sm">{row.original.total_weight?.toFixed(1) || '-'} kg</span>
      ),
    },
    {
      accessorKey: 'vehicle',
      header: 'Vehicle',
      cell: ({ row }) => (
        <div className="text-sm">
          <div className="font-mono">{row.original.vehicle_number || '-'}</div>
          {row.original.driver_name && (
            <div className="text-muted-foreground text-xs">{row.original.driver_name}</div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <Badge className={statusColors[row.original.status] ?? 'bg-gray-100 text-gray-800'}>
          {row.original.status?.replace(/_/g, ' ') ?? '-'}
        </Badge>
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
            <DropdownMenuItem
              onClick={() => {
                setSelectedManifest(row.original);
                setIsDetailDialogOpen(true);
              }}
            >
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            {row.original.status === 'DRAFT' && (
              <>
                <DropdownMenuItem
                  onClick={() => {
                    setSelectedManifest(row.original);
                    setIsAddShipmentsDialogOpen(true);
                  }}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Shipments
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => confirmMutation.mutate(row.original.id)}
                  disabled={row.original.shipments_count === 0 || confirmMutation.isPending}
                >
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Confirm Manifest
                </DropdownMenuItem>
              </>
            )}
            {row.original.status === 'CONFIRMED' && (
              <DropdownMenuItem
                onClick={() => {
                  setSelectedManifest(row.original);
                  setHandoverForm({
                    vehicle_number: row.original.vehicle_number || '',
                    driver_name: row.original.driver_name || '',
                    driver_phone: row.original.driver_phone || '',
                  });
                  setIsHandoverDialogOpen(true);
                }}
              >
                <Send className="mr-2 h-4 w-4" />
                Handover
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => handleDownload(row.original)}>
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => window.print()}>
              <Printer className="mr-2 h-4 w-4" />
              Print
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Manifests"
        description="Manage shipping manifests and handover documents"
        actions={
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Manifest
          </Button>
        }
      />

      {/* Status Filter */}
      <div className="flex gap-2">
        <Select value={statusFilter || 'all'} onValueChange={(v) => setStatusFilter(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="DRAFT">Draft</SelectItem>
            <SelectItem value="CONFIRMED">Confirmed</SelectItem>
            <SelectItem value="HANDED_OVER">Handed Over</SelectItem>
            <SelectItem value="IN_TRANSIT">In Transit</SelectItem>
            <SelectItem value="COMPLETED">Completed</SelectItem>
            <SelectItem value="CANCELLED">Cancelled</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="manifest_number"
        searchPlaceholder="Search manifests..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Create Manifest Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Manifest</DialogTitle>
            <DialogDescription>
              Select transporter and warehouse to create a new manifest
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Transporter</Label>
              <Select
                value={createForm.transporter_id}
                onValueChange={(v) => setCreateForm({ ...createForm, transporter_id: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select transporter" />
                </SelectTrigger>
                <SelectContent>
                  {transporters?.map((t: Transporter) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.name} ({t.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Origin Warehouse</Label>
              <Select
                value={createForm.warehouse_id}
                onValueChange={(v) => setCreateForm({ ...createForm, warehouse_id: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {warehouses?.map((w: Warehouse) => (
                    <SelectItem key={w.id} value={w.id}>
                      {w.name} ({w.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={!createForm.transporter_id || !createForm.warehouse_id || createMutation.isPending}
            >
              {createMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Plus className="mr-2 h-4 w-4" />
              )}
              Create Manifest
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Shipments Dialog */}
      <Dialog open={isAddShipmentsDialogOpen} onOpenChange={setIsAddShipmentsDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Add Shipments to Manifest</DialogTitle>
            <DialogDescription>
              {selectedManifest?.manifest_number} - Select shipments to add
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            {loadingPending ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : pendingShipments?.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No pending shipments available</p>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={selectedShipmentIds.length === pendingShipments?.length}
                      onCheckedChange={selectAllShipments}
                    />
                    <span className="text-sm">Select All ({pendingShipments?.length})</span>
                  </div>
                  <Badge variant="secondary">
                    {selectedShipmentIds.length} selected
                  </Badge>
                </div>
                <ScrollArea className="h-[300px] border rounded-md">
                  <div className="p-4 space-y-2">
                    {pendingShipments?.map((shipment: PendingShipment) => (
                      <div
                        key={shipment.id}
                        className={`flex items-center gap-4 p-3 border rounded-lg cursor-pointer hover:bg-muted/50 ${
                          selectedShipmentIds.includes(shipment.id) ? 'bg-muted border-primary' : ''
                        }`}
                        onClick={() => toggleShipmentSelection(shipment.id)}
                      >
                        <Checkbox checked={selectedShipmentIds.includes(shipment.id)} />
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-medium">{shipment.awb_number || shipment.shipment_number}</span>
                            <Badge variant={shipment.payment_mode === 'COD' ? 'default' : 'secondary'}>
                              {shipment.payment_mode || 'PREPAID'}
                            </Badge>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {shipment.ship_to_name || 'N/A'} | {shipment.ship_to_city || 'N/A'} - {shipment.ship_to_pincode || 'N/A'}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {shipment.weight_kg || 0} kg | {shipment.no_of_boxes || 1} pkg
                            {shipment.cod_amount && ` | COD: ₹${shipment.cod_amount.toLocaleString()}`}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddShipmentsDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => addShipmentsMutation.mutate()}
              disabled={selectedShipmentIds.length === 0 || addShipmentsMutation.isPending}
            >
              {addShipmentsMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Plus className="mr-2 h-4 w-4" />
              )}
              Add {selectedShipmentIds.length} Shipments
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Handover Dialog */}
      <Dialog open={isHandoverDialogOpen} onOpenChange={setIsHandoverDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Handover Manifest</DialogTitle>
            <DialogDescription>
              Enter vehicle and driver details for {selectedManifest?.manifest_number}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Vehicle Number *</Label>
              <Input
                placeholder="e.g., MH02AB1234"
                value={handoverForm.vehicle_number}
                onChange={(e) => setHandoverForm({ ...handoverForm, vehicle_number: e.target.value.toUpperCase() })}
              />
            </div>
            <div className="space-y-2">
              <Label>Driver Name *</Label>
              <Input
                placeholder="Enter driver name"
                value={handoverForm.driver_name}
                onChange={(e) => setHandoverForm({ ...handoverForm, driver_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Driver Phone *</Label>
              <Input
                placeholder="Enter driver phone"
                value={handoverForm.driver_phone}
                onChange={(e) => setHandoverForm({ ...handoverForm, driver_phone: e.target.value })}
              />
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Shipments:</span>
                  <span className="ml-2 font-medium">{selectedManifest?.shipments_count}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Total Weight:</span>
                  <span className="ml-2 font-medium">{selectedManifest?.total_weight?.toFixed(1)} kg</span>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsHandoverDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              className="bg-green-600 hover:bg-green-700"
              onClick={() => handoverMutation.mutate()}
              disabled={
                !handoverForm.vehicle_number ||
                !handoverForm.driver_name ||
                !handoverForm.driver_phone ||
                handoverMutation.isPending
              }
            >
              {handoverMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <ClipboardCheck className="mr-2 h-4 w-4" />
              )}
              Confirm Handover
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Manifest Detail Dialog */}
      <Dialog open={isDetailDialogOpen} onOpenChange={setIsDetailDialogOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3">
              <FileStack className="h-5 w-5" />
              {manifestDetail?.manifest_number}
              <Badge className={statusColors[manifestDetail?.status || 'DRAFT']}>
                {manifestDetail?.status?.replace(/_/g, ' ')}
              </Badge>
            </DialogTitle>
          </DialogHeader>
          <Tabs defaultValue="details" className="mt-4">
            <TabsList>
              <TabsTrigger value="details">Details</TabsTrigger>
              <TabsTrigger value="shipments">Shipments ({manifestDetail?.shipments?.length || 0})</TabsTrigger>
            </TabsList>
            <TabsContent value="details" className="mt-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Transporter</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-2">
                      <Truck className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{manifestDetail?.transporter?.name}</span>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Warehouse</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <span className="font-medium">{manifestDetail?.warehouse?.name}</span>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Total Weight</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <span className="font-medium">{manifestDetail?.total_weight?.toFixed(1) || 0} kg</span>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Created</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <span className="font-medium">{formatDate(manifestDetail?.created_at || '')}</span>
                  </CardContent>
                </Card>
                {manifestDetail?.vehicle_number && (
                  <>
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Vehicle</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <span className="font-mono font-medium">{manifestDetail.vehicle_number}</span>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Driver</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="font-medium">{manifestDetail.driver_name}</div>
                        <div className="text-sm text-muted-foreground">{manifestDetail.driver_phone}</div>
                      </CardContent>
                    </Card>
                  </>
                )}
              </div>
            </TabsContent>
            <TabsContent value="shipments" className="mt-4">
              <ScrollArea className="h-[400px]">
                <div className="space-y-2">
                  {manifestDetail?.shipments?.map((shipment: ManifestShipment) => (
                    <div key={shipment.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-medium">{shipment.awb_number || shipment.shipment_number}</span>
                          <Badge variant={shipment.payment_mode === 'COD' ? 'default' : 'secondary'}>
                            {shipment.payment_mode || 'PREPAID'}
                          </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground mt-1">
                          {shipment.order?.order_number || shipment.order_number || 'N/A'} | {shipment.ship_to_name || 'N/A'}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {shipment.ship_to_city || 'N/A'} - {shipment.ship_to_pincode || 'N/A'}
                        </div>
                      </div>
                      <div className="text-right text-sm">
                        <div>{shipment.weight_kg || 0} kg</div>
                        <div className="text-muted-foreground">{shipment.no_of_boxes || 1} pkg</div>
                        {shipment.cod_amount && (
                          <div className="font-medium text-orange-600">
                            ₹{shipment.cod_amount.toLocaleString()}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setIsDetailDialogOpen(false)}>
              Close
            </Button>
            {manifestDetail?.status === 'DRAFT' && (
              <Button
                onClick={() => {
                  setIsDetailDialogOpen(false);
                  setIsAddShipmentsDialogOpen(true);
                }}
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Shipments
              </Button>
            )}
            <Button variant="outline" onClick={() => handleDownload(manifestDetail!)}>
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
