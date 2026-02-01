'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  MoreHorizontal, Plus, Pencil, Trash2, Truck, Package,
  Loader2, CalendarIcon, ArrowRight, MapPin, Route
} from 'lucide-react';
import { format } from 'date-fns';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { rateCardsApi, transportersApi } from '@/lib/api';
import { formatCurrency, cn, formatDate } from '@/lib/utils';

interface FTLRateCard {
  id: string;
  transporter_id: string;
  transporter_name?: string;
  transporter_code?: string;
  code: string;
  name: string;
  description?: string;
  rate_type: 'CONTRACT' | 'SPOT' | 'TENDER';
  payment_terms?: string;
  effective_from: string;
  effective_to?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  lane_rates?: FTLLaneRate[];
  additional_charges?: FTLAdditionalCharge[];
}

interface FTLLaneRate {
  id: string;
  origin_city: string;
  origin_state: string;
  destination_city: string;
  destination_state: string;
  distance_km?: number;
  vehicle_type: string;
  vehicle_capacity_tons?: number;
  rate_per_trip: number;
  rate_per_km?: number;
  min_running_km?: number;
  extra_km_rate?: number;
  transit_hours?: number;
  loading_points_included: number;
  unloading_points_included: number;
  extra_point_charge?: number;
  is_active: boolean;
}

interface FTLAdditionalCharge {
  id: string;
  charge_type: string;
  calculation_type: 'PERCENTAGE' | 'FIXED' | 'PER_KG' | 'PER_UNIT';
  value: number;
  per_unit?: string;
  is_active: boolean;
}

interface VehicleType {
  id: string;
  code: string;
  name: string;
  length_ft?: number;
  width_ft?: number;
  height_ft?: number;
  capacity_tons?: number;
  capacity_cft?: number;
  category: string;
  is_active: boolean;
}

interface Transporter {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
}

const rateTypes = [
  { value: 'CONTRACT', label: 'Contract Rate' },
  { value: 'SPOT', label: 'Spot Rate' },
  { value: 'TENDER', label: 'Tender Rate' },
];

const vehicleCategories = [
  { value: 'MINI', label: 'Mini Truck' },
  { value: 'SMALL', label: 'Small' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LARGE', label: 'Large' },
  { value: 'HEAVY', label: 'Heavy' },
  { value: 'TRAILER', label: 'Trailer' },
];

const chargeTypes = [
  { value: 'TOLL', label: 'Toll Charges' },
  { value: 'DETENTION', label: 'Detention Charges' },
  { value: 'MULTI_POINT_PICKUP', label: 'Multi-Point Pickup' },
  { value: 'MULTI_POINT_DELIVERY', label: 'Multi-Point Delivery' },
  { value: 'OVERNIGHT_HALT', label: 'Overnight Halt' },
  { value: 'DRIVER_BATA', label: 'Driver Bata' },
  { value: 'LOADING', label: 'Loading Charges' },
  { value: 'UNLOADING', label: 'Unloading Charges' },
];

function FTLRateCardActionsCell({
  rateCard,
  onEdit,
  onDelete,
  onViewLanes
}: {
  rateCard: FTLRateCard;
  onEdit: (rateCard: FTLRateCard) => void;
  onDelete: (rateCard: FTLRateCard) => void;
  onViewLanes: (rateCard: FTLRateCard) => void;
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
        <DropdownMenuItem onClick={() => onViewLanes(rateCard)}>
          <Route className="mr-2 h-4 w-4" />
          View Lane Rates
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onEdit(rateCard)}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit
        </DropdownMenuItem>
        <DropdownMenuItem
          className="text-destructive focus:text-destructive"
          onClick={() => onDelete(rateCard)}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function FTLRateCardsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [transporterFilter, setTransporterFilter] = useState<string>('all');
  const [rateTypeFilter, setRateTypeFilter] = useState<string>('all');

  // Dialog states
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [isLaneDialogOpen, setIsLaneDialogOpen] = useState(false);
  const [selectedRateCard, setSelectedRateCard] = useState<FTLRateCard | null>(null);
  const [rateCardToDelete, setRateCardToDelete] = useState<FTLRateCard | null>(null);

  // Form state
  const [formData, setFormData] = useState<{
    id: string;
    transporter_id: string;
    code: string;
    name: string;
    description: string;
    rate_type: 'CONTRACT' | 'SPOT' | 'TENDER';
    payment_terms: string;
    effective_from: Date;
    effective_to: Date | null;
    is_active: boolean;
  }>({
    id: '',
    transporter_id: '',
    code: '',
    name: '',
    description: '',
    rate_type: 'CONTRACT',
    payment_terms: '',
    effective_from: new Date(),
    effective_to: null,
    is_active: true,
  });

  // Lane rate form
  const [laneFormData, setLaneFormData] = useState({
    origin_city: '',
    origin_state: '',
    destination_city: '',
    destination_state: '',
    distance_km: 0,
    vehicle_type: '',
    vehicle_capacity_tons: 0,
    rate_per_trip: 0,
    rate_per_km: 0,
    min_running_km: 0,
    extra_km_rate: 0,
    transit_hours: 0,
    loading_points_included: 1,
    unloading_points_included: 1,
    extra_point_charge: 0,
  });

  // Queries
  const { data, isLoading } = useQuery({
    queryKey: ['ftl-rate-cards', page, pageSize, transporterFilter, rateTypeFilter],
    queryFn: () => rateCardsApi.ftl.list({
      page: page + 1,
      size: pageSize,
      transporter_id: transporterFilter !== 'all' ? transporterFilter : undefined,
      rate_type: rateTypeFilter !== 'all' ? rateTypeFilter : undefined,
    }),
  });

  const { data: transportersData } = useQuery({
    queryKey: ['transporters'],
    queryFn: () => transportersApi.list({ is_active: true }),
  });

  const { data: vehicleTypesData } = useQuery({
    queryKey: ['vehicle-types'],
    queryFn: () => rateCardsApi.vehicleTypes.list(),
  });

  const { data: rateCardDetail } = useQuery({
    queryKey: ['ftl-rate-card', selectedRateCard?.id],
    queryFn: () => selectedRateCard ? rateCardsApi.ftl.getById(selectedRateCard.id) : null,
    enabled: !!selectedRateCard && isLaneDialogOpen,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: rateCardsApi.ftl.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ftl-rate-cards'] });
      toast.success('FTL rate card created successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create rate card'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      rateCardsApi.ftl.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ftl-rate-cards'] });
      toast.success('FTL rate card updated successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update rate card'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => rateCardsApi.ftl.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ftl-rate-cards'] });
      toast.success('FTL rate card deleted successfully');
      setRateCardToDelete(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete rate card'),
  });

  const addLaneMutation = useMutation({
    mutationFn: ({ rateCardId, lane }: { rateCardId: string; lane: Record<string, unknown> }) =>
      rateCardsApi.ftl.addLane(rateCardId, lane),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ftl-rate-card', selectedRateCard?.id] });
      toast.success('Lane rate added successfully');
      resetLaneForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to add lane rate'),
  });

  const resetForm = () => {
    setFormData({
      id: '',
      transporter_id: '',
      code: '',
      name: '',
      description: '',
      rate_type: 'CONTRACT',
      payment_terms: '',
      effective_from: new Date(),
      effective_to: null,
      is_active: true,
    });
    setIsEditMode(false);
    setIsDialogOpen(false);
  };

  const resetLaneForm = () => {
    setLaneFormData({
      origin_city: '',
      origin_state: '',
      destination_city: '',
      destination_state: '',
      distance_km: 0,
      vehicle_type: '',
      vehicle_capacity_tons: 0,
      rate_per_trip: 0,
      rate_per_km: 0,
      min_running_km: 0,
      extra_km_rate: 0,
      transit_hours: 0,
      loading_points_included: 1,
      unloading_points_included: 1,
      extra_point_charge: 0,
    });
  };

  const handleEdit = (rateCard: FTLRateCard) => {
    setFormData({
      id: rateCard.id,
      transporter_id: rateCard.transporter_id,
      code: rateCard.code,
      name: rateCard.name,
      description: rateCard.description || '',
      rate_type: rateCard.rate_type,
      payment_terms: rateCard.payment_terms || '',
      effective_from: new Date(rateCard.effective_from),
      effective_to: rateCard.effective_to ? new Date(rateCard.effective_to) : null,
      is_active: rateCard.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleViewLanes = (rateCard: FTLRateCard) => {
    setSelectedRateCard(rateCard);
    setIsLaneDialogOpen(true);
  };

  const handleSubmit = () => {
    if (!formData.transporter_id || !formData.code || !formData.name) {
      toast.error('Please fill all required fields');
      return;
    }

    const payload = {
      transporter_id: formData.transporter_id,
      code: formData.code.toUpperCase(),
      name: formData.name,
      description: formData.description || undefined,
      rate_type: formData.rate_type,
      payment_terms: formData.payment_terms || undefined,
      effective_from: format(formData.effective_from, 'yyyy-MM-dd'),
      effective_to: formData.effective_to ? format(formData.effective_to, 'yyyy-MM-dd') : undefined,
      is_active: formData.is_active,
    };

    if (isEditMode) {
      updateMutation.mutate({ id: formData.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleAddLane = () => {
    if (!selectedRateCard || !laneFormData.origin_city || !laneFormData.destination_city || !laneFormData.vehicle_type || !laneFormData.rate_per_trip) {
      toast.error('Please fill required fields (origin, destination, vehicle type, rate)');
      return;
    }

    addLaneMutation.mutate({
      rateCardId: selectedRateCard.id,
      lane: {
        origin_city: laneFormData.origin_city,
        origin_state: laneFormData.origin_state || undefined,
        destination_city: laneFormData.destination_city,
        destination_state: laneFormData.destination_state || undefined,
        distance_km: laneFormData.distance_km || undefined,
        vehicle_type: laneFormData.vehicle_type,
        vehicle_capacity_tons: laneFormData.vehicle_capacity_tons || undefined,
        rate_per_trip: laneFormData.rate_per_trip,
        rate_per_km: laneFormData.rate_per_km || undefined,
        min_running_km: laneFormData.min_running_km || undefined,
        extra_km_rate: laneFormData.extra_km_rate || undefined,
        transit_hours: laneFormData.transit_hours || undefined,
        loading_points_included: laneFormData.loading_points_included,
        unloading_points_included: laneFormData.unloading_points_included,
        extra_point_charge: laneFormData.extra_point_charge || undefined,
      },
    });
  };

  const columns: ColumnDef<FTLRateCard>[] = [
    {
      accessorKey: 'transporter',
      header: 'Transporter',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-100 dark:bg-orange-950">
            <Truck className="h-5 w-5 text-orange-600" />
          </div>
          <div>
            <div className="font-medium">{row.original.transporter_name || 'N/A'}</div>
            <div className="text-sm text-muted-foreground">{row.original.transporter_code}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'code',
      header: 'Code',
      cell: ({ row }) => (
        <code className="text-sm font-mono bg-muted px-2 py-1 rounded">{row.original.code}</code>
      ),
    },
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.name}</div>
          {row.original.description && (
            <div className="text-sm text-muted-foreground truncate max-w-[200px]">
              {row.original.description}
            </div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'rate_type',
      header: 'Rate Type',
      cell: ({ row }) => {
        const typeColors: Record<string, string> = {
          CONTRACT: 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200',
          SPOT: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200',
          TENDER: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200',
        };
        return (
          <Badge className={typeColors[row.original.rate_type] || ''}>
            {rateTypes.find(r => r.value === row.original.rate_type)?.label || row.original.rate_type}
          </Badge>
        );
      },
    },
    {
      accessorKey: 'payment_terms',
      header: 'Payment Terms',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {row.original.payment_terms || '-'}
        </span>
      ),
    },
    {
      accessorKey: 'effective_from',
      header: 'Effective',
      cell: ({ row }) => (
        <div className="text-sm text-muted-foreground">
          {formatDate(row.original.effective_from)}
          {row.original.effective_to && (
            <> - {formatDate(row.original.effective_to)}</>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'is_active',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.is_active ? 'ACTIVE' : 'INACTIVE'} />,
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <FTLRateCardActionsCell
          rateCard={row.original}
          onEdit={handleEdit}
          onDelete={setRateCardToDelete}
          onViewLanes={handleViewLanes}
        />
      ),
    },
  ];

  const transporters = transportersData?.items ?? transportersData ?? [];
  const vehicleTypes = vehicleTypesData?.items ?? vehicleTypesData ?? [];
  const rateCards = data?.items ?? [];

  // Stats
  const stats = {
    total: data?.total ?? rateCards.length,
    active: rateCards.filter((r: FTLRateCard) => r.is_active).length,
    contract: rateCards.filter((r: FTLRateCard) => r.rate_type === 'CONTRACT').length,
    spot: rateCards.filter((r: FTLRateCard) => r.rate_type === 'SPOT').length,
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="FTL Rate Cards (Full Truck Load)"
        description="Manage rate cards for Full Truck Load shipments with lane-based pricing"
        actions={
          <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
            <DialogTrigger asChild>
              <Button onClick={() => setIsDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add FTL Rate Card
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>{isEditMode ? 'Edit FTL Rate Card' : 'Add FTL Rate Card'}</DialogTitle>
                <DialogDescription>
                  {isEditMode ? 'Update FTL rate card details' : 'Create a new FTL rate card for full truck load shipments'}
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
                <div className="space-y-2">
                  <Label>Transporter *</Label>
                  <Select
                    value={formData.transporter_id}
                    onValueChange={(value) => setFormData({ ...formData, transporter_id: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select transporter" />
                    </SelectTrigger>
                    <SelectContent>
                      {transporters.filter((t: Transporter) => t.id && t.id.trim() !== '').map((t: Transporter) => (
                        <SelectItem key={t.id} value={t.id}>
                          {t.name} ({t.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Rate Card Code *</Label>
                    <Input
                      placeholder="e.g., FTL-CONTRACT-2024"
                      value={formData.code}
                      onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Name *</Label>
                    <Input
                      placeholder="e.g., North India FTL Contract"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    placeholder="Optional description..."
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Rate Type *</Label>
                    <Select
                      value={formData.rate_type}
                      onValueChange={(value: 'CONTRACT' | 'SPOT' | 'TENDER') => setFormData({ ...formData, rate_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {rateTypes.map((type) => (
                          <SelectItem key={type.value} value={type.value}>
                            {type.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Payment Terms</Label>
                    <Input
                      placeholder="e.g., 15 days credit"
                      value={formData.payment_terms}
                      onChange={(e) => setFormData({ ...formData, payment_terms: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Effective From *</Label>
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          className={cn(
                            'w-full justify-start text-left font-normal',
                            !formData.effective_from && 'text-muted-foreground'
                          )}
                        >
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {formData.effective_from ? format(formData.effective_from, 'PPP') : 'Pick a date'}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="single"
                          selected={formData.effective_from}
                          onSelect={(date) => date && setFormData({ ...formData, effective_from: date })}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  </div>
                  <div className="space-y-2">
                    <Label>Effective To</Label>
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          className={cn(
                            'w-full justify-start text-left font-normal',
                            !formData.effective_to && 'text-muted-foreground'
                          )}
                        >
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {formData.effective_to ? format(formData.effective_to, 'PPP') : 'No end date'}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="single"
                          selected={formData.effective_to || undefined}
                          onSelect={(date) => setFormData({ ...formData, effective_to: date || null })}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  </div>
                </div>

                {isEditMode && (
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="is_active"
                      checked={formData.is_active}
                      onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                    />
                    <Label htmlFor="is_active">Active</Label>
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={resetForm}>Cancel</Button>
                <Button
                  onClick={handleSubmit}
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  {(createMutation.isPending || updateMutation.isPending) && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {isEditMode ? 'Update' : 'Create'} Rate Card
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total FTL Rate Cards</CardTitle>
            <Truck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">{stats.active} active</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Contract Rates</CardTitle>
            <Package className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.contract}</div>
            <p className="text-xs text-muted-foreground">Long-term contracts</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Spot Rates</CardTitle>
            <MapPin className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.spot}</div>
            <p className="text-xs text-muted-foreground">On-demand pricing</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Transporters</CardTitle>
            <Truck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{new Set(rateCards.map((r: FTLRateCard) => r.transporter_id)).size}</div>
            <p className="text-xs text-muted-foreground">With FTL rates</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={transporterFilter} onValueChange={setTransporterFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="All Transporters" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Transporters</SelectItem>
            {transporters.filter((t: Transporter) => t.id && t.id.trim() !== '').map((t: Transporter) => (
              <SelectItem key={t.id} value={t.id}>
                {t.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={rateTypeFilter} onValueChange={setRateTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Rate Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Rate Types</SelectItem>
            {rateTypes.map((type) => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={rateCards}
        searchKey="name"
        searchPlaceholder="Search FTL rate cards..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Lane Rates Dialog */}
      <Dialog open={isLaneDialogOpen} onOpenChange={(open) => { if (!open) { setIsLaneDialogOpen(false); setSelectedRateCard(null); } }}>
        <DialogContent className="max-w-5xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Lane Rates - {selectedRateCard?.name}</DialogTitle>
            <DialogDescription>
              Manage lane-based rates for this FTL rate card
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="lanes">
            <TabsList>
              <TabsTrigger value="lanes">Lane Rates</TabsTrigger>
              <TabsTrigger value="add">Add New Lane</TabsTrigger>
            </TabsList>

            <TabsContent value="lanes" className="space-y-4">
              {rateCardDetail?.lane_rates?.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-muted">
                      <tr>
                        <th className="text-left p-3">Lane</th>
                        <th className="text-left p-3">Vehicle Type</th>
                        <th className="text-right p-3">Distance</th>
                        <th className="text-right p-3">Rate/Trip</th>
                        <th className="text-right p-3">Rate/Km</th>
                        <th className="text-center p-3">Transit</th>
                        <th className="text-center p-3">Points</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rateCardDetail.lane_rates.map((lane: FTLLaneRate) => (
                        <tr key={lane.id} className="border-t">
                          <td className="p-3">
                            <div className="flex items-center gap-1">
                              <span className="font-medium">{lane.origin_city}</span>
                              <ArrowRight className="h-3 w-3 text-muted-foreground" />
                              <span className="font-medium">{lane.destination_city}</span>
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {lane.origin_state} → {lane.destination_state}
                            </div>
                          </td>
                          <td className="p-3">
                            <Badge variant="outline">{lane.vehicle_type}</Badge>
                            {lane.vehicle_capacity_tons && (
                              <div className="text-xs text-muted-foreground mt-1">
                                {lane.vehicle_capacity_tons} tons
                              </div>
                            )}
                          </td>
                          <td className="p-3 text-right font-mono">
                            {lane.distance_km ? `${lane.distance_km} km` : '-'}
                          </td>
                          <td className="p-3 text-right font-mono font-medium">
                            {formatCurrency(lane.rate_per_trip)}
                          </td>
                          <td className="p-3 text-right font-mono text-muted-foreground">
                            {lane.rate_per_km ? `${formatCurrency(lane.rate_per_km)}/km` : '-'}
                          </td>
                          <td className="p-3 text-center">
                            {lane.transit_hours ? `${lane.transit_hours}h` : '-'}
                          </td>
                          <td className="p-3 text-center text-xs">
                            <div>L: {lane.loading_points_included}</div>
                            <div>U: {lane.unloading_points_included}</div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No lane rates configured. Add lanes to define pricing.
                </div>
              )}
            </TabsContent>

            <TabsContent value="add" className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-4">
                  <h4 className="font-medium text-sm text-muted-foreground">Origin</h4>
                  <div className="space-y-2">
                    <Label>City *</Label>
                    <Input
                      placeholder="e.g., Mumbai"
                      value={laneFormData.origin_city}
                      onChange={(e) => setLaneFormData({ ...laneFormData, origin_city: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>State</Label>
                    <Input
                      placeholder="e.g., Maharashtra"
                      value={laneFormData.origin_state}
                      onChange={(e) => setLaneFormData({ ...laneFormData, origin_state: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-4">
                  <h4 className="font-medium text-sm text-muted-foreground">Destination</h4>
                  <div className="space-y-2">
                    <Label>City *</Label>
                    <Input
                      placeholder="e.g., Delhi"
                      value={laneFormData.destination_city}
                      onChange={(e) => setLaneFormData({ ...laneFormData, destination_city: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>State</Label>
                    <Input
                      placeholder="e.g., Delhi"
                      value={laneFormData.destination_state}
                      onChange={(e) => setLaneFormData({ ...laneFormData, destination_state: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Distance (km)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={laneFormData.distance_km || ''}
                    onChange={(e) => setLaneFormData({ ...laneFormData, distance_km: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Vehicle Type *</Label>
                  <Select
                    value={laneFormData.vehicle_type}
                    onValueChange={(value) => setLaneFormData({ ...laneFormData, vehicle_type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select vehicle" />
                    </SelectTrigger>
                    <SelectContent>
                      {vehicleTypes.filter((v: VehicleType) => v.code && v.code.trim() !== '').map((v: VehicleType) => (
                        <SelectItem key={v.id} value={v.code}>
                          {v.name} ({v.capacity_tons} tons)
                        </SelectItem>
                      ))}
                      {/* Fallback common vehicle types */}
                      <SelectItem value="TATA_ACE">Tata Ace (0.75T)</SelectItem>
                      <SelectItem value="EICHER_14FT">Eicher 14ft (2.5T)</SelectItem>
                      <SelectItem value="EICHER_17FT">Eicher 17ft (4T)</SelectItem>
                      <SelectItem value="EICHER_19FT">Eicher 19ft (7T)</SelectItem>
                      <SelectItem value="CONTAINER_20FT">Container 20ft (7T)</SelectItem>
                      <SelectItem value="CONTAINER_32FT">Container 32ft (15T)</SelectItem>
                      <SelectItem value="TRAILER_40FT">Trailer 40ft (25T)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Capacity (tons)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.1"
                    value={laneFormData.vehicle_capacity_tons || ''}
                    onChange={(e) => setLaneFormData({ ...laneFormData, vehicle_capacity_tons: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4">
                <div className="space-y-2">
                  <Label>Rate per Trip (₹) *</Label>
                  <Input
                    type="number"
                    min="0"
                    value={laneFormData.rate_per_trip || ''}
                    onChange={(e) => setLaneFormData({ ...laneFormData, rate_per_trip: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Rate per Km (₹)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.5"
                    value={laneFormData.rate_per_km || ''}
                    onChange={(e) => setLaneFormData({ ...laneFormData, rate_per_km: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Min Running (km)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={laneFormData.min_running_km || ''}
                    onChange={(e) => setLaneFormData({ ...laneFormData, min_running_km: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Extra Km Rate (₹)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.5"
                    value={laneFormData.extra_km_rate || ''}
                    onChange={(e) => setLaneFormData({ ...laneFormData, extra_km_rate: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4">
                <div className="space-y-2">
                  <Label>Transit Hours</Label>
                  <Input
                    type="number"
                    min="0"
                    value={laneFormData.transit_hours || ''}
                    onChange={(e) => setLaneFormData({ ...laneFormData, transit_hours: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Loading Points</Label>
                  <Input
                    type="number"
                    min="1"
                    value={laneFormData.loading_points_included}
                    onChange={(e) => setLaneFormData({ ...laneFormData, loading_points_included: parseInt(e.target.value) || 1 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Unloading Points</Label>
                  <Input
                    type="number"
                    min="1"
                    value={laneFormData.unloading_points_included}
                    onChange={(e) => setLaneFormData({ ...laneFormData, unloading_points_included: parseInt(e.target.value) || 1 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Extra Point Charge (₹)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={laneFormData.extra_point_charge || ''}
                    onChange={(e) => setLaneFormData({ ...laneFormData, extra_point_charge: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <Button onClick={handleAddLane} disabled={addLaneMutation.isPending} className="w-full">
                {addLaneMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Add Lane Rate
              </Button>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!rateCardToDelete} onOpenChange={() => setRateCardToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete FTL Rate Card?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{rateCardToDelete?.name}&quot;? This will also delete all associated lane rates.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => rateCardToDelete && deleteMutation.mutate(rateCardToDelete.id)}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
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
