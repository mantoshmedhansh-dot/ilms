'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  MoreHorizontal, Plus, Pencil, Trash2, Calculator, Truck, Clock,
  DollarSign, Star, Package, Loader2, CalendarIcon
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { rateCardsApi, transportersApi } from '@/lib/api';
import { formatCurrency, cn, formatDate } from '@/lib/utils';

interface RateCard {
  id: string;
  name: string;
  transporter_id: string;
  transporter?: { name: string; code: string };
  transporter_name?: string;
  source_zone?: string;
  destination_zone?: string;
  zone_from?: string;
  zone_to?: string;
  weight_slab: string;
  weight_slab_kg?: string;
  rate_per_kg: number;
  per_kg_rate?: number;
  min_charge: number;
  base_rate?: number;
  fuel_surcharge_percent?: number;
  cod_charges?: number;
  cod_charge?: number;
  cod_percent?: number;
  rto_charges?: number;
  effective_from: string;
  effective_to?: string;
  min_weight_kg?: number;
  max_weight_kg?: number;
  estimated_days?: number;
  reliability_score?: number;
  is_active: boolean;
  created_at: string;
}

interface Transporter {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
}

interface RateCardStats {
  total_rate_cards: number;
  active_cards: number;
  transporters_count: number;
  avg_base_rate: number;
}

const zones = [
  { label: 'North', value: 'NORTH' },
  { label: 'South', value: 'SOUTH' },
  { label: 'East', value: 'EAST' },
  { label: 'West', value: 'WEST' },
  { label: 'Central', value: 'CENTRAL' },
  { label: 'Metro', value: 'METRO' },
  { label: 'Local', value: 'LOCAL' },
];

const weightSlabs = [
  { label: '0-0.5 kg', value: '0-0.5' },
  { label: '0.5-1 kg', value: '0.5-1' },
  { label: '1-2 kg', value: '1-2' },
  { label: '2-5 kg', value: '2-5' },
  { label: '5-10 kg', value: '5-10' },
  { label: '10-20 kg', value: '10-20' },
  { label: '20-50 kg', value: '20-50' },
  { label: '50+ kg', value: '50+' },
];

// Separate component for actions
function RateCardActionsCell({ rateCard, onEdit, onDelete }: {
  rateCard: RateCard;
  onEdit: (rateCard: RateCard) => void;
  onDelete: (rateCard: RateCard) => void;
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
        <DropdownMenuItem onClick={() => onEdit(rateCard)}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit Rate
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

export default function RateCardsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [transporterFilter, setTransporterFilter] = useState<string>('all');

  // Dialog states
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [isCompareDialogOpen, setIsCompareDialogOpen] = useState(false);
  const [rateCardToDelete, setRateCardToDelete] = useState<RateCard | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    transporter_id: '',
    source_zone: '',
    destination_zone: '',
    weight_slab: '',
    rate_per_kg: 0,
    min_charge: 0,
    fuel_surcharge_percent: 0,
    cod_charges: 0,
    rto_charges: 0,
    effective_from: new Date(),
    effective_to: null as Date | null,
    is_active: true,
  });

  // Compare rates state
  const [compareParams, setCompareParams] = useState({
    zone_from: '',
    zone_to: '',
    weight_kg: '',
    is_cod: false,
  });

  // Queries
  const { data, isLoading } = useQuery({
    queryKey: ['rate-cards', page, pageSize, transporterFilter],
    queryFn: () => rateCardsApi.list({
      page: page + 1,
      size: pageSize,
      transporter_id: transporterFilter !== 'all' ? transporterFilter : undefined,
    }),
  });

  const { data: transportersData } = useQuery({
    queryKey: ['transporters'],
    queryFn: () => transportersApi.list({ is_active: true }),
  });

  const { data: comparedRates, refetch: fetchComparedRates } = useQuery({
    queryKey: ['compared-rates', compareParams],
    queryFn: () => rateCardsApi.calculate({
      origin_pincode: compareParams.zone_from,
      destination_pincode: compareParams.zone_to,
      weight_kg: parseFloat(compareParams.weight_kg) || 0,
      payment_mode: compareParams.is_cod ? 'COD' : 'PREPAID',
    }),
    enabled: false,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: rateCardsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rate-cards'] });
      toast.success('Rate card created successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create rate card'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof rateCardsApi.update>[1] }) =>
      rateCardsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rate-cards'] });
      toast.success('Rate card updated successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update rate card'),
  });

  const deleteMutation = useMutation({
    mutationFn: rateCardsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rate-cards'] });
      toast.success('Rate card deleted successfully');
      setRateCardToDelete(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete rate card'),
  });

  const resetForm = () => {
    setFormData({
      id: '',
      name: '',
      transporter_id: '',
      source_zone: '',
      destination_zone: '',
      weight_slab: '',
      rate_per_kg: 0,
      min_charge: 0,
      fuel_surcharge_percent: 0,
      cod_charges: 0,
      rto_charges: 0,
      effective_from: new Date(),
      effective_to: null,
      is_active: true,
    });
    setIsEditMode(false);
    setIsDialogOpen(false);
  };

  const handleEdit = (rateCard: RateCard) => {
    setFormData({
      id: rateCard.id,
      name: rateCard.name || '',
      transporter_id: rateCard.transporter_id,
      source_zone: rateCard.source_zone || rateCard.zone_from || '',
      destination_zone: rateCard.destination_zone || rateCard.zone_to || '',
      weight_slab: rateCard.weight_slab || rateCard.weight_slab_kg || '',
      rate_per_kg: rateCard.rate_per_kg || rateCard.per_kg_rate || 0,
      min_charge: rateCard.min_charge || rateCard.base_rate || 0,
      fuel_surcharge_percent: rateCard.fuel_surcharge_percent || 0,
      cod_charges: rateCard.cod_charges || rateCard.cod_charge || 0,
      rto_charges: rateCard.rto_charges || 0,
      effective_from: new Date(rateCard.effective_from),
      effective_to: rateCard.effective_to ? new Date(rateCard.effective_to) : null,
      is_active: rateCard.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleSubmit = () => {
    if (!formData.transporter_id || !formData.weight_slab || !formData.rate_per_kg) {
      toast.error('Please fill all required fields');
      return;
    }

    const payload = {
      name: formData.name || `${formData.source_zone} to ${formData.destination_zone} - ${formData.weight_slab}`,
      transporter_id: formData.transporter_id,
      source_zone: formData.source_zone || undefined,
      destination_zone: formData.destination_zone || undefined,
      weight_slab: formData.weight_slab,
      rate_per_kg: formData.rate_per_kg,
      min_charge: formData.min_charge,
      fuel_surcharge_percent: formData.fuel_surcharge_percent || undefined,
      cod_charges: formData.cod_charges || undefined,
      rto_charges: formData.rto_charges || undefined,
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

  const handleCompare = () => {
    if (!compareParams.zone_from || !compareParams.zone_to || !compareParams.weight_kg) {
      toast.error('Please fill all required fields');
      return;
    }
    fetchComparedRates();
  };

  const columns: ColumnDef<RateCard>[] = [
    {
      accessorKey: 'transporter',
      header: 'Transporter',
      cell: ({ row }) => {
        const transporterName = row.original.transporter?.name || row.original.transporter_name || 'N/A';
        const reliabilityScore = row.original.reliability_score ?? 0;
        return (
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
              <Truck className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <div className="font-medium">{transporterName}</div>
              {reliabilityScore > 0 && (
                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Star className="h-3 w-3 text-yellow-500" />
                  {reliabilityScore.toFixed(1)}
                </div>
              )}
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => (
        <span className="text-sm font-medium">{row.original.name || '-'}</span>
      ),
    },
    {
      accessorKey: 'zones',
      header: 'Zones',
      cell: ({ row }) => {
        const from = row.original.source_zone || row.original.zone_from || 'Any';
        const to = row.original.destination_zone || row.original.zone_to || 'Any';
        return (
          <div className="text-sm">
            <div>{from} → {to}</div>
          </div>
        );
      },
    },
    {
      accessorKey: 'weight_slab',
      header: 'Weight Slab',
      cell: ({ row }) => {
        const slab = row.original.weight_slab || row.original.weight_slab_kg;
        const minWeight = row.original.min_weight_kg;
        const maxWeight = row.original.max_weight_kg;
        return (
          <div className="text-sm font-mono">
            {slab || (minWeight !== undefined && maxWeight !== undefined ? `${minWeight}-${maxWeight} kg` : '-')}
          </div>
        );
      },
    },
    {
      accessorKey: 'min_charge',
      header: 'Base Rate',
      cell: ({ row }) => {
        const baseRate = row.original.min_charge || row.original.base_rate || 0;
        return <span className="font-mono font-medium">{formatCurrency(baseRate)}</span>;
      },
    },
    {
      accessorKey: 'rate_per_kg',
      header: 'Per Kg',
      cell: ({ row }) => {
        const perKg = row.original.rate_per_kg || row.original.per_kg_rate || 0;
        return <span className="font-mono text-sm">{formatCurrency(perKg)}/kg</span>;
      },
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
        <RateCardActionsCell
          rateCard={row.original}
          onEdit={handleEdit}
          onDelete={setRateCardToDelete}
        />
      ),
    },
  ];

  const transporters = transportersData?.items ?? transportersData ?? [];
  const rateCards = data?.items ?? [];

  // Calculate stats from data
  const stats: RateCardStats = {
    total_rate_cards: data?.total ?? rateCards.length,
    active_cards: rateCards.filter((r: RateCard) => r.is_active).length,
    transporters_count: new Set(rateCards.map((r: RateCard) => r.transporter_id)).size,
    avg_base_rate: rateCards.length > 0
      ? rateCards.reduce((sum: number, r: RateCard) => sum + (r.min_charge || r.base_rate || 0), 0) / rateCards.length
      : 0,
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Transporter Rate Cards"
        description="Manage and compare shipping rates across transporters"
        actions={
          <div className="flex gap-2">
            <Dialog open={isCompareDialogOpen} onOpenChange={setIsCompareDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline">
                  <Calculator className="mr-2 h-4 w-4" />
                  Compare Rates
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Compare Shipping Rates</DialogTitle>
                  <DialogDescription>
                    Compare rates across all transporters for a specific route and weight.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>From Zone</Label>
                      <Select
                        value={compareParams.zone_from}
                        onValueChange={(value) => setCompareParams({ ...compareParams, zone_from: value })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select zone" />
                        </SelectTrigger>
                        <SelectContent>
                          {zones.map((zone) => (
                            <SelectItem key={zone.value} value={zone.value}>
                              {zone.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>To Zone</Label>
                      <Select
                        value={compareParams.zone_to}
                        onValueChange={(value) => setCompareParams({ ...compareParams, zone_to: value })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select zone" />
                        </SelectTrigger>
                        <SelectContent>
                          {zones.map((zone) => (
                            <SelectItem key={zone.value} value={zone.value}>
                              {zone.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Weight (kg)</Label>
                      <Input
                        type="number"
                        placeholder="e.g., 2.5"
                        value={compareParams.weight_kg}
                        onChange={(e) => setCompareParams({ ...compareParams, weight_kg: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2 flex items-end">
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="is_cod"
                          checked={compareParams.is_cod}
                          onCheckedChange={(checked) => setCompareParams({ ...compareParams, is_cod: checked })}
                        />
                        <Label htmlFor="is_cod">COD Order</Label>
                      </div>
                    </div>
                  </div>
                  <Button onClick={handleCompare}>Compare Rates</Button>

                  {/* Comparison Results */}
                  {comparedRates && (
                    <Card>
                      <CardHeader className="py-3">
                        <CardTitle className="text-sm">Rate Calculation Result</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>Base Rate:</div>
                          <div className="font-mono">{formatCurrency(comparedRates.base_rate || 0)}</div>
                          <div>Weight Charge:</div>
                          <div className="font-mono">{formatCurrency(comparedRates.weight_charge || 0)}</div>
                          <div>Fuel Surcharge:</div>
                          <div className="font-mono">{formatCurrency(comparedRates.fuel_surcharge || 0)}</div>
                          {compareParams.is_cod && (
                            <>
                              <div>COD Charges:</div>
                              <div className="font-mono">{formatCurrency(comparedRates.cod_charge || 0)}</div>
                            </>
                          )}
                          <div className="font-bold border-t pt-2">Total:</div>
                          <div className="font-mono font-bold border-t pt-2">{formatCurrency(comparedRates.total || 0)}</div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </DialogContent>
            </Dialog>

            <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
              <DialogTrigger asChild>
                <Button onClick={() => setIsDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Rate Card
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle>{isEditMode ? 'Edit Rate Card' : 'Add Rate Card'}</DialogTitle>
                  <DialogDescription>
                    {isEditMode ? 'Update shipping rate card details' : 'Create a new shipping rate card for a transporter'}
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

                  <div className="space-y-2">
                    <Label>Rate Card Name</Label>
                    <Input
                      placeholder="e.g., North to South - Standard"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>From Zone</Label>
                      <Select
                        value={formData.source_zone || 'any'}
                        onValueChange={(value) => setFormData({ ...formData, source_zone: value === 'any' ? '' : value })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Any zone" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="any">Any Zone</SelectItem>
                          {zones.map((zone) => (
                            <SelectItem key={zone.value} value={zone.value}>
                              {zone.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>To Zone</Label>
                      <Select
                        value={formData.destination_zone || 'any'}
                        onValueChange={(value) => setFormData({ ...formData, destination_zone: value === 'any' ? '' : value })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Any zone" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="any">Any Zone</SelectItem>
                          {zones.map((zone) => (
                            <SelectItem key={zone.value} value={zone.value}>
                              {zone.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Weight Slab *</Label>
                    <Select
                      value={formData.weight_slab}
                      onValueChange={(value) => setFormData({ ...formData, weight_slab: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select weight slab" />
                      </SelectTrigger>
                      <SelectContent>
                        {weightSlabs.map((slab) => (
                          <SelectItem key={slab.value} value={slab.value}>
                            {slab.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Min Charge (₹) *</Label>
                      <Input
                        type="number"
                        min="0"
                        step="1"
                        placeholder="50"
                        value={formData.min_charge || ''}
                        onChange={(e) => setFormData({ ...formData, min_charge: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Rate Per Kg (₹) *</Label>
                      <Input
                        type="number"
                        min="0"
                        step="0.5"
                        placeholder="20"
                        value={formData.rate_per_kg || ''}
                        onChange={(e) => setFormData({ ...formData, rate_per_kg: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>Fuel Surcharge %</Label>
                      <Input
                        type="number"
                        min="0"
                        step="0.5"
                        placeholder="10"
                        value={formData.fuel_surcharge_percent || ''}
                        onChange={(e) => setFormData({ ...formData, fuel_surcharge_percent: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>COD Charges (₹)</Label>
                      <Input
                        type="number"
                        min="0"
                        step="1"
                        placeholder="30"
                        value={formData.cod_charges || ''}
                        onChange={(e) => setFormData({ ...formData, cod_charges: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>RTO Charges (₹)</Label>
                      <Input
                        type="number"
                        min="0"
                        step="1"
                        placeholder="50"
                        value={formData.rto_charges || ''}
                        onChange={(e) => setFormData({ ...formData, rto_charges: parseFloat(e.target.value) || 0 })}
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
                      <Label>Effective To (Optional)</Label>
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
          </div>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Rate Cards</CardTitle>
            <Calculator className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_rate_cards}</div>
            <p className="text-xs text-muted-foreground">{stats.active_cards} active</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Transporters</CardTitle>
            <Truck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.transporters_count}</div>
            <p className="text-xs text-muted-foreground">With rate cards</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Base Rate</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats.avg_base_rate)}</div>
            <p className="text-xs text-muted-foreground">Across all cards</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Coverage</CardTitle>
            <Package className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">99.5%</div>
            <p className="text-xs text-muted-foreground">Pincode coverage</p>
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
      </div>

      <DataTable
        columns={columns}
        data={rateCards}
        searchKey="name"
        searchPlaceholder="Search rate cards..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Delete Confirmation */}
      <AlertDialog open={!!rateCardToDelete} onOpenChange={() => setRateCardToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Rate Card?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this rate card? This action cannot be undone.
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
