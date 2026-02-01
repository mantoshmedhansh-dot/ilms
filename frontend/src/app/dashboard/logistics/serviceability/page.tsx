'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  MoreHorizontal, Plus, Pencil, MapPin, CheckCircle, XCircle, Upload,
  Loader2, Search, AlertTriangle
} from 'lucide-react';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { serviceabilityApi, transportersApi } from '@/lib/api';

interface ServiceabilityZone {
  id: string;
  pincode: string;
  city: string;
  state: string;
  region?: string;
  zone?: string;
  is_serviceable?: boolean;
  is_active: boolean;
  delivery_days?: number;
  cod_available: boolean;
  prepaid_available: boolean;
  max_weight?: number;
  transporter_ids?: string[];
  transporters?: { id: string; name: string }[];
  franchisee_id?: string;
  franchisee?: { name: string };
  created_at: string;
}

interface Transporter {
  id: string;
  name: string;
  code: string;
}

interface CheckResult {
  serviceable: boolean;
  pincode: string;
  city?: string;
  state?: string;
  transporters?: { name: string; delivery_days: number }[];
  cod_available?: boolean;
  prepaid_available?: boolean;
  message?: string;
}

const regions = [
  { label: 'North', value: 'NORTH' },
  { label: 'South', value: 'SOUTH' },
  { label: 'East', value: 'EAST' },
  { label: 'West', value: 'WEST' },
  { label: 'Central', value: 'CENTRAL' },
  { label: 'Metro', value: 'METRO' },
];

const states = [
  'Andhra Pradesh', 'Bihar', 'Chhattisgarh', 'Delhi', 'Goa', 'Gujarat',
  'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala',
  'Madhya Pradesh', 'Maharashtra', 'Odisha', 'Punjab', 'Rajasthan',
  'Tamil Nadu', 'Telangana', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
];

// Separate component for actions
function ServiceabilityActionsCell({ zone, onEdit }: {
  zone: ServiceabilityZone;
  onEdit: (zone: ServiceabilityZone) => void;
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
        <DropdownMenuItem onClick={() => onEdit(zone)}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function ServiceabilityPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);

  // Dialog states
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);

  // Check pincode state
  const [checkPincode, setCheckPincode] = useState('');
  const [checkResult, setCheckResult] = useState<CheckResult | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    id: '',
    pincode: '',
    city: '',
    state: '',
    region: '',
    transporter_ids: [] as string[],
    prepaid_available: true,
    cod_available: true,
    is_active: true,
  });

  // Queries
  const { data, isLoading } = useQuery({
    queryKey: ['serviceability', page, pageSize],
    queryFn: () => serviceabilityApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: transportersData } = useQuery({
    queryKey: ['transporters'],
    queryFn: () => transportersApi.list({ is_active: true }),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: serviceabilityApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['serviceability'] });
      toast.success('Pincode added successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to add pincode'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof serviceabilityApi.update>[1] }) =>
      serviceabilityApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['serviceability'] });
      toast.success('Pincode updated successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update pincode'),
  });

  const resetForm = () => {
    setFormData({
      id: '',
      pincode: '',
      city: '',
      state: '',
      region: '',
      transporter_ids: [],
      prepaid_available: true,
      cod_available: true,
      is_active: true,
    });
    setIsEditMode(false);
    setIsDialogOpen(false);
  };

  const handleEdit = (zone: ServiceabilityZone) => {
    setFormData({
      id: zone.id,
      pincode: zone.pincode,
      city: zone.city,
      state: zone.state,
      region: zone.region || zone.zone || '',
      transporter_ids: zone.transporter_ids || zone.transporters?.map(t => t.id) || [],
      prepaid_available: zone.prepaid_available,
      cod_available: zone.cod_available,
      is_active: zone.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleSubmit = () => {
    if (!formData.pincode || !formData.city || !formData.state) {
      toast.error('Please fill all required fields');
      return;
    }

    if (formData.pincode.length !== 6) {
      toast.error('Pincode must be 6 digits');
      return;
    }

    const payload = {
      pincode: formData.pincode,
      city: formData.city,
      state: formData.state,
      region: formData.region || undefined,
      transporter_ids: formData.transporter_ids.length > 0 ? formData.transporter_ids : undefined,
      prepaid_available: formData.prepaid_available,
      cod_available: formData.cod_available,
      is_active: formData.is_active,
    };

    if (isEditMode) {
      updateMutation.mutate({ id: formData.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleCheckPincode = async () => {
    if (checkPincode.length !== 6) {
      toast.error('Please enter a valid 6-digit pincode');
      return;
    }

    setIsChecking(true);
    try {
      const result = await serviceabilityApi.check(checkPincode);
      setCheckResult(result);
    } catch {
      setCheckResult({
        serviceable: false,
        pincode: checkPincode,
        message: 'Unable to check serviceability',
      });
    } finally {
      setIsChecking(false);
    }
  };

  const toggleTransporter = (transporterId: string) => {
    setFormData(prev => ({
      ...prev,
      transporter_ids: prev.transporter_ids.includes(transporterId)
        ? prev.transporter_ids.filter(id => id !== transporterId)
        : [...prev.transporter_ids, transporterId],
    }));
  };

  const columns: ColumnDef<ServiceabilityZone>[] = [
    {
      accessorKey: 'pincode',
      header: 'Pincode',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4 text-muted-foreground" />
          <span className="font-mono font-medium">{row.original.pincode}</span>
        </div>
      ),
    },
    {
      accessorKey: 'location',
      header: 'Location',
      cell: ({ row }) => (
        <div className="text-sm">
          <div className="font-medium">{row.original.city}</div>
          <div className="text-muted-foreground">{row.original.state}</div>
        </div>
      ),
    },
    {
      accessorKey: 'region',
      header: 'Region',
      cell: ({ row }) => {
        const region = row.original.region || row.original.zone;
        return region ? (
          <span className="px-2 py-1 rounded bg-muted text-sm">{region}</span>
        ) : (
          <span className="text-muted-foreground">-</span>
        );
      },
    },
    {
      accessorKey: 'transporters',
      header: 'Transporters',
      cell: ({ row }) => {
        const transporters = row.original.transporters;
        if (!transporters || transporters.length === 0) {
          return <span className="text-muted-foreground text-sm">All</span>;
        }
        return (
          <div className="flex flex-wrap gap-1">
            {transporters.slice(0, 2).map((t, idx) => (
              <Badge key={idx} variant="outline" className="text-xs">
                {t.name}
              </Badge>
            ))}
            {transporters.length > 2 && (
              <Badge variant="secondary" className="text-xs">
                +{transporters.length - 2}
              </Badge>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'payment',
      header: 'Payment Options',
      cell: ({ row }) => (
        <div className="flex gap-2">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
            row.original.prepaid_available ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'
          }`}>
            Prepaid
          </span>
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
            row.original.cod_available ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-500'
          }`}>
            COD
          </span>
        </div>
      ),
    },
    {
      accessorKey: 'is_active',
      header: 'Status',
      cell: ({ row }) => {
        const isActive = row.original.is_active ?? row.original.is_serviceable;
        return (
          <div className="flex items-center gap-1">
            {isActive ? (
              <CheckCircle className="h-4 w-4 text-green-600" />
            ) : (
              <XCircle className="h-4 w-4 text-red-600" />
            )}
            <span className={isActive ? 'text-green-600' : 'text-red-600'}>
              {isActive ? 'Active' : 'Inactive'}
            </span>
          </div>
        );
      },
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <ServiceabilityActionsCell
          zone={row.original}
          onEdit={handleEdit}
        />
      ),
    },
  ];

  const transporters = transportersData?.items ?? transportersData ?? [];
  const serviceabilityList = data?.items ?? [];

  // Calculate stats
  const activeCount = serviceabilityList.filter((s: ServiceabilityZone) => s.is_active || s.is_serviceable).length;
  const codCount = serviceabilityList.filter((s: ServiceabilityZone) => s.cod_available).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Serviceability"
        description="Manage delivery zones and pincode serviceability"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" disabled>
              <Upload className="mr-2 h-4 w-4" />
              Bulk Upload
            </Button>
            <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
              <DialogTrigger asChild>
                <Button onClick={() => setIsDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Pincode
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>{isEditMode ? 'Edit Pincode' : 'Add Pincode'}</DialogTitle>
                  <DialogDescription>
                    {isEditMode ? 'Update serviceability settings for this pincode' : 'Add a new serviceable pincode'}
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="space-y-2">
                    <Label>Pincode *</Label>
                    <Input
                      placeholder="110001"
                      maxLength={6}
                      value={formData.pincode}
                      onChange={(e) => setFormData({ ...formData, pincode: e.target.value.replace(/\D/g, '') })}
                      disabled={isEditMode}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>City *</Label>
                      <Input
                        placeholder="New Delhi"
                        value={formData.city}
                        onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>State *</Label>
                      <Select
                        value={formData.state}
                        onValueChange={(value) => setFormData({ ...formData, state: value })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select state" />
                        </SelectTrigger>
                        <SelectContent>
                          {states.map((state) => (
                            <SelectItem key={state} value={state}>
                              {state}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Region</Label>
                    <Select
                      value={formData.region || 'none'}
                      onValueChange={(value) => setFormData({ ...formData, region: value === 'none' ? '' : value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select region (optional)" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">No specific region</SelectItem>
                        {regions.map((region) => (
                          <SelectItem key={region.value} value={region.value}>
                            {region.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Transporters (Optional)</Label>
                    <div className="flex flex-wrap gap-2 p-3 border rounded-md max-h-32 overflow-y-auto">
                      {transporters.filter((t: Transporter) => t.id && t.id.trim() !== '').map((t: Transporter) => (
                        <Badge
                          key={t.id}
                          variant={formData.transporter_ids.includes(t.id) ? 'default' : 'outline'}
                          className="cursor-pointer"
                          onClick={() => toggleTransporter(t.id)}
                        >
                          {t.name}
                        </Badge>
                      ))}
                      {transporters.length === 0 && (
                        <span className="text-sm text-muted-foreground">No transporters available</span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Leave empty to allow all transporters
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="prepaid"
                        checked={formData.prepaid_available}
                        onCheckedChange={(checked) => setFormData({ ...formData, prepaid_available: checked })}
                      />
                      <Label htmlFor="prepaid">Prepaid Available</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="cod"
                        checked={formData.cod_available}
                        onCheckedChange={(checked) => setFormData({ ...formData, cod_available: checked })}
                      />
                      <Label htmlFor="cod">COD Available</Label>
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
                    {isEditMode ? 'Update' : 'Add'} Pincode
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Pincodes</CardTitle>
            <MapPin className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data?.total ?? serviceabilityList.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{activeCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">COD Available</CardTitle>
            <Badge variant="outline" className="text-xs">COD</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{codCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Coverage</CardTitle>
            <CheckCircle className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {serviceabilityList.length > 0 ? Math.round((activeCount / serviceabilityList.length) * 100) : 0}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Check Pincode Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Search className="h-5 w-5" />
            Check Pincode Serviceability
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-start">
            <div className="space-y-2">
              <Input
                placeholder="Enter 6-digit pincode"
                value={checkPincode}
                onChange={(e) => {
                  setCheckPincode(e.target.value.replace(/\D/g, ''));
                  setCheckResult(null);
                }}
                maxLength={6}
                className="w-48"
              />
            </div>
            <Button
              variant="outline"
              onClick={handleCheckPincode}
              disabled={checkPincode.length !== 6 || isChecking}
            >
              {isChecking ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" />
              )}
              Check
            </Button>

            {checkResult && (
              <div className={`flex-1 p-4 rounded-lg ${
                checkResult.serviceable ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
              }`}>
                <div className="flex items-start gap-3">
                  {checkResult.serviceable ? (
                    <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <p className={`font-medium ${checkResult.serviceable ? 'text-green-800' : 'text-red-800'}`}>
                      {checkResult.serviceable ? 'Serviceable' : 'Not Serviceable'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Pincode: {checkResult.pincode}
                      {checkResult.city && ` - ${checkResult.city}, ${checkResult.state}`}
                    </p>
                    {checkResult.serviceable && (
                      <div className="mt-2 flex gap-2">
                        {checkResult.prepaid_available && (
                          <Badge variant="outline" className="bg-green-100">Prepaid</Badge>
                        )}
                        {checkResult.cod_available && (
                          <Badge variant="outline" className="bg-blue-100">COD</Badge>
                        )}
                      </div>
                    )}
                    {checkResult.message && (
                      <p className="text-sm text-muted-foreground mt-1">{checkResult.message}</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <DataTable
        columns={columns}
        data={serviceabilityList}
        searchKey="pincode"
        searchPlaceholder="Search pincodes..."
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
