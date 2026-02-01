'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  MoreHorizontal, Plus, Pencil, Trash2, Truck, Package,
  Loader2, CalendarIcon, ArrowRight, Weight
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

interface B2BRateCard {
  id: string;
  transporter_id: string;
  transporter_name?: string;
  transporter_code?: string;
  code: string;
  name: string;
  description?: string;
  service_type: 'LTL' | 'PTL' | 'PARCEL';
  transport_mode: 'SURFACE' | 'AIR' | 'RAIL' | 'MULTIMODAL';
  min_chargeable_weight_kg: number;
  min_invoice_value?: number;
  effective_from: string;
  effective_to?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  rate_slabs?: B2BRateSlab[];
  additional_charges?: B2BAdditionalCharge[];
}

interface B2BRateSlab {
  id: string;
  origin_city?: string;
  origin_state?: string;
  destination_city?: string;
  destination_state?: string;
  zone?: string;
  min_weight_kg: number;
  max_weight_kg?: number;
  rate_type: 'PER_KG' | 'PER_CFT' | 'FLAT_RATE';
  rate: number;
  min_charge?: number;
  transit_days_min?: number;
  transit_days_max?: number;
  is_active: boolean;
}

interface B2BAdditionalCharge {
  id: string;
  charge_type: string;
  calculation_type: 'PERCENTAGE' | 'FIXED' | 'PER_KG' | 'PER_UNIT' | 'PER_PKG';
  value: number;
  per_unit?: string;
  is_active: boolean;
}

interface Transporter {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
}

const serviceTypes = [
  { value: 'LTL', label: 'Less Than Truckload' },
  { value: 'PTL', label: 'Part Truck Load' },
  { value: 'PARCEL', label: 'Parcel' },
];

const transportModes = [
  { value: 'SURFACE', label: 'Surface' },
  { value: 'AIR', label: 'Air' },
  { value: 'RAIL', label: 'Rail' },
  { value: 'MULTIMODAL', label: 'Multimodal' },
];

const rateTypes = [
  { value: 'PER_KG', label: 'Per Kg' },
  { value: 'PER_CFT', label: 'Per CFT' },
  { value: 'FLAT_RATE', label: 'Flat Rate' },
];

const chargeTypes = [
  { value: 'HANDLING', label: 'Handling' },
  { value: 'DOCKET', label: 'Docket' },
  { value: 'LOADING', label: 'Loading' },
  { value: 'UNLOADING', label: 'Unloading' },
  { value: 'POD_COPY', label: 'POD Copy' },
  { value: 'FUEL', label: 'Fuel Surcharge' },
  { value: 'ODA', label: 'ODA Charge' },
];

function B2BRateCardActionsCell({
  rateCard,
  onEdit,
  onDelete,
  onViewSlabs
}: {
  rateCard: B2BRateCard;
  onEdit: (rateCard: B2BRateCard) => void;
  onDelete: (rateCard: B2BRateCard) => void;
  onViewSlabs: (rateCard: B2BRateCard) => void;
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
        <DropdownMenuItem onClick={() => onViewSlabs(rateCard)}>
          <Weight className="mr-2 h-4 w-4" />
          View Rate Slabs
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

export default function B2BRateCardsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [transporterFilter, setTransporterFilter] = useState<string>('all');
  const [serviceTypeFilter, setServiceTypeFilter] = useState<string>('all');

  // Dialog states
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [isSlabDialogOpen, setIsSlabDialogOpen] = useState(false);
  const [selectedRateCard, setSelectedRateCard] = useState<B2BRateCard | null>(null);
  const [rateCardToDelete, setRateCardToDelete] = useState<B2BRateCard | null>(null);

  // Form state
  const [formData, setFormData] = useState<{
    id: string;
    transporter_id: string;
    code: string;
    name: string;
    description: string;
    service_type: 'LTL' | 'PTL' | 'PARCEL';
    transport_mode: 'SURFACE' | 'AIR' | 'RAIL' | 'MULTIMODAL';
    min_chargeable_weight_kg: number;
    min_invoice_value: number;
    effective_from: Date;
    effective_to: Date | null;
    is_active: boolean;
  }>({
    id: '',
    transporter_id: '',
    code: '',
    name: '',
    description: '',
    service_type: 'LTL',
    transport_mode: 'SURFACE',
    min_chargeable_weight_kg: 25,
    min_invoice_value: 0,
    effective_from: new Date(),
    effective_to: null,
    is_active: true,
  });

  // Rate slab form
  const [slabFormData, setSlabFormData] = useState<{
    origin_city: string;
    origin_state: string;
    destination_city: string;
    destination_state: string;
    zone: string;
    min_weight_kg: number;
    max_weight_kg: number;
    rate_type: 'PER_KG' | 'PER_CFT' | 'FLAT_RATE';
    rate: number;
    min_charge: number;
    transit_days_min: number;
    transit_days_max: number;
  }>({
    origin_city: '',
    origin_state: '',
    destination_city: '',
    destination_state: '',
    zone: '',
    min_weight_kg: 0,
    max_weight_kg: 0,
    rate_type: 'PER_KG',
    rate: 0,
    min_charge: 0,
    transit_days_min: 0,
    transit_days_max: 0,
  });

  // Queries
  const { data, isLoading } = useQuery({
    queryKey: ['b2b-rate-cards', page, pageSize, transporterFilter, serviceTypeFilter],
    queryFn: () => rateCardsApi.b2b.list({
      page: page + 1,
      size: pageSize,
      transporter_id: transporterFilter !== 'all' ? transporterFilter : undefined,
      service_type: serviceTypeFilter !== 'all' ? serviceTypeFilter : undefined,
    }),
  });

  const { data: transportersData } = useQuery({
    queryKey: ['transporters'],
    queryFn: () => transportersApi.list({ is_active: true }),
  });

  const { data: rateCardDetail } = useQuery({
    queryKey: ['b2b-rate-card', selectedRateCard?.id],
    queryFn: () => selectedRateCard ? rateCardsApi.b2b.getById(selectedRateCard.id) : null,
    enabled: !!selectedRateCard && isSlabDialogOpen,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: rateCardsApi.b2b.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['b2b-rate-cards'] });
      toast.success('B2B rate card created successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create rate card'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      rateCardsApi.b2b.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['b2b-rate-cards'] });
      toast.success('B2B rate card updated successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update rate card'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => rateCardsApi.b2b.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['b2b-rate-cards'] });
      toast.success('B2B rate card deleted successfully');
      setRateCardToDelete(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete rate card'),
  });

  const addSlabMutation = useMutation({
    mutationFn: ({ rateCardId, slab }: { rateCardId: string; slab: Record<string, unknown> }) =>
      rateCardsApi.b2b.addSlab(rateCardId, slab),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['b2b-rate-card', selectedRateCard?.id] });
      toast.success('Rate slab added successfully');
      resetSlabForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to add rate slab'),
  });

  const resetForm = () => {
    setFormData({
      id: '',
      transporter_id: '',
      code: '',
      name: '',
      description: '',
      service_type: 'LTL',
      transport_mode: 'SURFACE',
      min_chargeable_weight_kg: 25,
      min_invoice_value: 0,
      effective_from: new Date(),
      effective_to: null,
      is_active: true,
    });
    setIsEditMode(false);
    setIsDialogOpen(false);
  };

  const resetSlabForm = () => {
    setSlabFormData({
      origin_city: '',
      origin_state: '',
      destination_city: '',
      destination_state: '',
      zone: '',
      min_weight_kg: 0,
      max_weight_kg: 0,
      rate_type: 'PER_KG',
      rate: 0,
      min_charge: 0,
      transit_days_min: 0,
      transit_days_max: 0,
    });
  };

  const handleEdit = (rateCard: B2BRateCard) => {
    setFormData({
      id: rateCard.id,
      transporter_id: rateCard.transporter_id,
      code: rateCard.code,
      name: rateCard.name,
      description: rateCard.description || '',
      service_type: rateCard.service_type,
      transport_mode: rateCard.transport_mode,
      min_chargeable_weight_kg: rateCard.min_chargeable_weight_kg,
      min_invoice_value: rateCard.min_invoice_value || 0,
      effective_from: new Date(rateCard.effective_from),
      effective_to: rateCard.effective_to ? new Date(rateCard.effective_to) : null,
      is_active: rateCard.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleViewSlabs = (rateCard: B2BRateCard) => {
    setSelectedRateCard(rateCard);
    setIsSlabDialogOpen(true);
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
      service_type: formData.service_type,
      transport_mode: formData.transport_mode,
      min_chargeable_weight_kg: formData.min_chargeable_weight_kg,
      min_invoice_value: formData.min_invoice_value || undefined,
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

  const handleAddSlab = () => {
    if (!selectedRateCard || !slabFormData.rate) {
      toast.error('Please fill required fields');
      return;
    }

    addSlabMutation.mutate({
      rateCardId: selectedRateCard.id,
      slab: {
        origin_city: slabFormData.origin_city || undefined,
        origin_state: slabFormData.origin_state || undefined,
        destination_city: slabFormData.destination_city || undefined,
        destination_state: slabFormData.destination_state || undefined,
        zone: slabFormData.zone || undefined,
        min_weight_kg: slabFormData.min_weight_kg,
        max_weight_kg: slabFormData.max_weight_kg || undefined,
        rate_type: slabFormData.rate_type,
        rate: slabFormData.rate,
        min_charge: slabFormData.min_charge || undefined,
        transit_days_min: slabFormData.transit_days_min || undefined,
        transit_days_max: slabFormData.transit_days_max || undefined,
      },
    });
  };

  const columns: ColumnDef<B2BRateCard>[] = [
    {
      accessorKey: 'transporter',
      header: 'Transporter',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-950">
            <Truck className="h-5 w-5 text-blue-600" />
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
      accessorKey: 'service_type',
      header: 'Service Type',
      cell: ({ row }) => (
        <Badge variant="outline">
          {serviceTypes.find(s => s.value === row.original.service_type)?.label || row.original.service_type}
        </Badge>
      ),
    },
    {
      accessorKey: 'transport_mode',
      header: 'Mode',
      cell: ({ row }) => (
        <Badge variant="secondary">
          {row.original.transport_mode}
        </Badge>
      ),
    },
    {
      accessorKey: 'min_chargeable_weight_kg',
      header: 'Min Weight',
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.original.min_chargeable_weight_kg} kg</span>
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
        <B2BRateCardActionsCell
          rateCard={row.original}
          onEdit={handleEdit}
          onDelete={setRateCardToDelete}
          onViewSlabs={handleViewSlabs}
        />
      ),
    },
  ];

  const transporters = transportersData?.items ?? transportersData ?? [];
  const rateCards = data?.items ?? [];

  // Stats
  const stats = {
    total: data?.total ?? rateCards.length,
    active: rateCards.filter((r: B2BRateCard) => r.is_active).length,
    ltl: rateCards.filter((r: B2BRateCard) => r.service_type === 'LTL').length,
    ptl: rateCards.filter((r: B2BRateCard) => r.service_type === 'PTL').length,
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="B2B Rate Cards (LTL/PTL)"
        description="Manage rate cards for Less Than Truckload and Part Truck Load shipments"
        actions={
          <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
            <DialogTrigger asChild>
              <Button onClick={() => setIsDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add B2B Rate Card
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>{isEditMode ? 'Edit B2B Rate Card' : 'Add B2B Rate Card'}</DialogTitle>
                <DialogDescription>
                  {isEditMode ? 'Update B2B rate card details' : 'Create a new B2B rate card for LTL/PTL shipments'}
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
                      placeholder="e.g., B2B-LTL-2024"
                      value={formData.code}
                      onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Name *</Label>
                    <Input
                      placeholder="e.g., LTL Surface Standard"
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
                    <Label>Service Type *</Label>
                    <Select
                      value={formData.service_type}
                      onValueChange={(value: 'LTL' | 'PTL' | 'PARCEL') => setFormData({ ...formData, service_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {serviceTypes.map((type) => (
                          <SelectItem key={type.value} value={type.value}>
                            {type.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Transport Mode *</Label>
                    <Select
                      value={formData.transport_mode}
                      onValueChange={(value: 'SURFACE' | 'AIR' | 'RAIL' | 'MULTIMODAL') => setFormData({ ...formData, transport_mode: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {transportModes.map((mode) => (
                          <SelectItem key={mode.value} value={mode.value}>
                            {mode.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Min Chargeable Weight (kg)</Label>
                    <Input
                      type="number"
                      min="0"
                      value={formData.min_chargeable_weight_kg}
                      onChange={(e) => setFormData({ ...formData, min_chargeable_weight_kg: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Min Invoice Value</Label>
                    <Input
                      type="number"
                      min="0"
                      value={formData.min_invoice_value || ''}
                      onChange={(e) => setFormData({ ...formData, min_invoice_value: parseFloat(e.target.value) || 0 })}
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
            <CardTitle className="text-sm font-medium">Total B2B Rate Cards</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">{stats.active} active</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">LTL Cards</CardTitle>
            <Truck className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.ltl}</div>
            <p className="text-xs text-muted-foreground">Less Than Truckload</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">PTL Cards</CardTitle>
            <Package className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.ptl}</div>
            <p className="text-xs text-muted-foreground">Part Truck Load</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Transporters</CardTitle>
            <Truck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{new Set(rateCards.map((r: B2BRateCard) => r.transporter_id)).size}</div>
            <p className="text-xs text-muted-foreground">With B2B rates</p>
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
        <Select value={serviceTypeFilter} onValueChange={setServiceTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Service Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Service Types</SelectItem>
            {serviceTypes.map((type) => (
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
        searchPlaceholder="Search B2B rate cards..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Rate Slabs Dialog */}
      <Dialog open={isSlabDialogOpen} onOpenChange={(open) => { if (!open) { setIsSlabDialogOpen(false); setSelectedRateCard(null); } }}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Rate Slabs - {selectedRateCard?.name}</DialogTitle>
            <DialogDescription>
              Manage lane/zone-based rate slabs for this B2B rate card
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="slabs">
            <TabsList>
              <TabsTrigger value="slabs">Rate Slabs</TabsTrigger>
              <TabsTrigger value="add">Add New Slab</TabsTrigger>
            </TabsList>

            <TabsContent value="slabs" className="space-y-4">
              {rateCardDetail?.rate_slabs?.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-muted">
                      <tr>
                        <th className="text-left p-3">Lane/Zone</th>
                        <th className="text-left p-3">Weight Range</th>
                        <th className="text-left p-3">Rate Type</th>
                        <th className="text-right p-3">Rate</th>
                        <th className="text-right p-3">Min Charge</th>
                        <th className="text-center p-3">Transit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rateCardDetail.rate_slabs.map((slab: B2BRateSlab) => (
                        <tr key={slab.id} className="border-t">
                          <td className="p-3">
                            {slab.origin_city && slab.destination_city ? (
                              <span className="flex items-center gap-1">
                                {slab.origin_city} <ArrowRight className="h-3 w-3" /> {slab.destination_city}
                              </span>
                            ) : slab.zone ? (
                              <Badge variant="outline">Zone {slab.zone}</Badge>
                            ) : (
                              'All'
                            )}
                          </td>
                          <td className="p-3 font-mono">
                            {slab.min_weight_kg}-{slab.max_weight_kg || '∞'} kg
                          </td>
                          <td className="p-3">
                            <Badge variant="secondary">{slab.rate_type}</Badge>
                          </td>
                          <td className="p-3 text-right font-mono">
                            {formatCurrency(slab.rate)}
                          </td>
                          <td className="p-3 text-right font-mono">
                            {slab.min_charge ? formatCurrency(slab.min_charge) : '-'}
                          </td>
                          <td className="p-3 text-center">
                            {slab.transit_days_min && slab.transit_days_max
                              ? `${slab.transit_days_min}-${slab.transit_days_max}d`
                              : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No rate slabs configured. Add slabs to define pricing.
                </div>
              )}
            </TabsContent>

            <TabsContent value="add" className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Origin City</Label>
                  <Input
                    placeholder="e.g., Mumbai"
                    value={slabFormData.origin_city}
                    onChange={(e) => setSlabFormData({ ...slabFormData, origin_city: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Origin State</Label>
                  <Input
                    placeholder="e.g., Maharashtra"
                    value={slabFormData.origin_state}
                    onChange={(e) => setSlabFormData({ ...slabFormData, origin_state: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Destination City</Label>
                  <Input
                    placeholder="e.g., Delhi"
                    value={slabFormData.destination_city}
                    onChange={(e) => setSlabFormData({ ...slabFormData, destination_city: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Destination State</Label>
                  <Input
                    placeholder="e.g., Delhi"
                    value={slabFormData.destination_state}
                    onChange={(e) => setSlabFormData({ ...slabFormData, destination_state: e.target.value })}
                  />
                </div>
              </div>

              <div className="text-center text-sm text-muted-foreground">— OR use Zone —</div>

              <div className="space-y-2">
                <Label>Zone Code</Label>
                <Input
                  placeholder="e.g., A, B, C..."
                  value={slabFormData.zone}
                  onChange={(e) => setSlabFormData({ ...slabFormData, zone: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Min Weight (kg)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={slabFormData.min_weight_kg || ''}
                    onChange={(e) => setSlabFormData({ ...slabFormData, min_weight_kg: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Max Weight (kg)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={slabFormData.max_weight_kg || ''}
                    onChange={(e) => setSlabFormData({ ...slabFormData, max_weight_kg: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Rate Type</Label>
                  <Select
                    value={slabFormData.rate_type}
                    onValueChange={(value: 'PER_KG' | 'PER_CFT' | 'FLAT_RATE') => setSlabFormData({ ...slabFormData, rate_type: value })}
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
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Rate (₹) *</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.5"
                    value={slabFormData.rate || ''}
                    onChange={(e) => setSlabFormData({ ...slabFormData, rate: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Min Charge (₹)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={slabFormData.min_charge || ''}
                    onChange={(e) => setSlabFormData({ ...slabFormData, min_charge: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Transit Days (Min)</Label>
                  <Input
                    type="number"
                    min="1"
                    value={slabFormData.transit_days_min || ''}
                    onChange={(e) => setSlabFormData({ ...slabFormData, transit_days_min: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Transit Days (Max)</Label>
                  <Input
                    type="number"
                    min="1"
                    value={slabFormData.transit_days_max || ''}
                    onChange={(e) => setSlabFormData({ ...slabFormData, transit_days_max: parseInt(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <Button onClick={handleAddSlab} disabled={addSlabMutation.isPending} className="w-full">
                {addSlabMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Add Rate Slab
              </Button>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!rateCardToDelete} onOpenChange={() => setRateCardToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete B2B Rate Card?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{rateCardToDelete?.name}&quot;? This will also delete all associated rate slabs.
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
