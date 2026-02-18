'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Store,
  Plus,
  Search,
  RefreshCw,
  Loader2,
  ChevronLeft,
  ChevronRight,
  MapPin,
} from 'lucide-react';
import { toast } from 'sonner';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { dmsApi, dealersApi } from '@/lib/api';
import { RetailerOutlet, RetailerOutletListResponse, Dealer } from '@/types';

const OUTLET_TYPES = [
  'KIRANA',
  'MODERN_TRADE',
  'SUPERMARKET',
  'PHARMACY',
  'HARDWARE',
  'ELECTRONICS',
  'GENERAL_STORE',
  'OTHER',
] as const;

const BEAT_DAYS = [
  'MONDAY',
  'TUESDAY',
  'WEDNESDAY',
  'THURSDAY',
  'FRIDAY',
  'SATURDAY',
  'SUNDAY',
] as const;

function formatCurrency(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 10000000) return `\u20B9${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `\u20B9${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `\u20B9${(num / 1000).toFixed(1)}K`;
  return `\u20B9${num.toFixed(0)}`;
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    ACTIVE: 'bg-green-100 text-green-800',
    INACTIVE: 'bg-yellow-100 text-yellow-800',
    CLOSED: 'bg-red-100 text-red-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

function getOutletTypeBadge(type: string): string {
  const colors: Record<string, string> = {
    KIRANA: 'bg-orange-100 text-orange-800',
    MODERN_TRADE: 'bg-blue-100 text-blue-800',
    SUPERMARKET: 'bg-purple-100 text-purple-800',
    PHARMACY: 'bg-teal-100 text-teal-800',
    HARDWARE: 'bg-slate-100 text-slate-800',
    ELECTRONICS: 'bg-cyan-100 text-cyan-800',
    GENERAL_STORE: 'bg-indigo-100 text-indigo-800',
    OTHER: 'bg-gray-100 text-gray-800',
  };
  return colors[type] || 'bg-gray-100 text-gray-800';
}

function formatOutletType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

interface OutletFormData {
  dealer_id: string;
  name: string;
  owner_name: string;
  outlet_type: string;
  phone: string;
  email: string;
  address_line1: string;
  city: string;
  state: string;
  pincode: string;
  beat_day: string;
}

const emptyFormData: OutletFormData = {
  dealer_id: '',
  name: '',
  owner_name: '',
  outlet_type: '',
  phone: '',
  email: '',
  address_line1: '',
  city: '',
  state: '',
  pincode: '',
  beat_day: '',
};

export default function DMSRetailersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [dealerFilter, setDealerFilter] = useState<string>('all');
  const [cityFilter, setCityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [outletTypeFilter, setOutletTypeFilter] = useState<string>('all');
  const [showDialog, setShowDialog] = useState(false);
  const [editingOutlet, setEditingOutlet] = useState<RetailerOutlet | null>(null);
  const [formData, setFormData] = useState<OutletFormData>(emptyFormData);

  const pageSize = 20;

  // Fetch retailers
  const { data: retailersData, isLoading, refetch, isFetching } = useQuery<RetailerOutletListResponse>({
    queryKey: ['dms-retailers', page, dealerFilter, cityFilter, statusFilter, outletTypeFilter],
    queryFn: () =>
      dmsApi.listRetailers({
        page,
        size: pageSize,
        dealer_id: dealerFilter !== 'all' ? dealerFilter : undefined,
        city: cityFilter.trim() || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        outlet_type: outletTypeFilter !== 'all' ? outletTypeFilter : undefined,
      }),
    staleTime: 2 * 60 * 1000,
  });

  // Fetch dealers for dropdown
  const { data: dealersData } = useQuery({
    queryKey: ['dealers-dropdown'],
    queryFn: () => dealersApi.list({ size: 100 }),
    staleTime: 10 * 60 * 1000,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: OutletFormData) =>
      dmsApi.createRetailer({
        dealer_id: data.dealer_id,
        name: data.name,
        owner_name: data.owner_name,
        outlet_type: data.outlet_type,
        phone: data.phone,
        email: data.email || undefined,
        address_line1: data.address_line1,
        city: data.city,
        state: data.state,
        pincode: data.pincode,
        beat_day: data.beat_day || undefined,
      }),
    onSuccess: () => {
      toast.success('Retailer outlet created successfully');
      queryClient.invalidateQueries({ queryKey: ['dms-retailers'] });
      handleCloseDialog();
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to create outlet');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: OutletFormData }) =>
      dmsApi.updateRetailer(id, {
        dealer_id: data.dealer_id,
        name: data.name,
        owner_name: data.owner_name,
        outlet_type: data.outlet_type,
        phone: data.phone,
        email: data.email || undefined,
        address_line1: data.address_line1,
        city: data.city,
        state: data.state,
        pincode: data.pincode,
        beat_day: data.beat_day || undefined,
      }),
    onSuccess: () => {
      toast.success('Retailer outlet updated successfully');
      queryClient.invalidateQueries({ queryKey: ['dms-retailers'] });
      handleCloseDialog();
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to update outlet');
    },
  });

  const dealers = (dealersData?.items || []) as Dealer[];
  const retailers = retailersData?.items || [];
  const totalRetailers = retailersData?.total || 0;
  const totalPages = Math.ceil(totalRetailers / pageSize);

  const handleOpenCreate = () => {
    setEditingOutlet(null);
    setFormData(emptyFormData);
    setShowDialog(true);
  };

  const handleOpenEdit = (outlet: RetailerOutlet) => {
    setEditingOutlet(outlet);
    setFormData({
      dealer_id: outlet.dealer_id,
      name: outlet.name,
      owner_name: outlet.owner_name,
      outlet_type: outlet.outlet_type,
      phone: outlet.phone,
      email: outlet.email || '',
      address_line1: outlet.address_line1,
      city: outlet.city,
      state: outlet.state,
      pincode: outlet.pincode,
      beat_day: outlet.beat_day || '',
    });
    setShowDialog(true);
  };

  const handleCloseDialog = () => {
    setShowDialog(false);
    setEditingOutlet(null);
    setFormData(emptyFormData);
  };

  const handleSubmit = () => {
    if (!formData.dealer_id) {
      toast.error('Please select a dealer');
      return;
    }
    if (!formData.name.trim()) {
      toast.error('Outlet name is required');
      return;
    }
    if (!formData.owner_name.trim()) {
      toast.error('Owner name is required');
      return;
    }
    if (!formData.outlet_type) {
      toast.error('Please select an outlet type');
      return;
    }
    if (!formData.phone.trim()) {
      toast.error('Phone number is required');
      return;
    }
    if (!formData.address_line1.trim()) {
      toast.error('Address is required');
      return;
    }
    if (!formData.city.trim()) {
      toast.error('City is required');
      return;
    }
    if (!formData.state.trim()) {
      toast.error('State is required');
      return;
    }
    if (!formData.pincode.trim()) {
      toast.error('Pincode is required');
      return;
    }

    if (editingOutlet) {
      updateMutation.mutate({ id: editingOutlet.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const isMutating = createMutation.isPending || updateMutation.isPending;

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-100 rounded-lg">
            <Store className="h-6 w-6 text-orange-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Retailer Outlets</h1>
            <p className="text-muted-foreground">
              Manage retail outlets across your dealer network
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleOpenCreate}>
            <Plus className="h-4 w-4 mr-2" />
            Add Outlet
          </Button>
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="icon">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="min-w-[180px]">
              <Label className="text-xs text-muted-foreground mb-1 block">Dealer</Label>
              <Select value={dealerFilter} onValueChange={(v) => { setDealerFilter(v); setPage(1); }}>
                <SelectTrigger>
                  <SelectValue placeholder="All Dealers" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Dealers</SelectItem>
                  {dealers.map((d) => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.dealer_code || d.code} - {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[150px]">
              <Label className="text-xs text-muted-foreground mb-1 block">City</Label>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Filter by city..."
                  value={cityFilter}
                  onChange={(e) => { setCityFilter(e.target.value); setPage(1); }}
                  className="pl-8"
                />
              </div>
            </div>
            <div className="min-w-[150px]">
              <Label className="text-xs text-muted-foreground mb-1 block">Status</Label>
              <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
                <SelectTrigger>
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="ACTIVE">Active</SelectItem>
                  <SelectItem value="INACTIVE">Inactive</SelectItem>
                  <SelectItem value="CLOSED">Closed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[160px]">
              <Label className="text-xs text-muted-foreground mb-1 block">Outlet Type</Label>
              <Select value={outletTypeFilter} onValueChange={(v) => { setOutletTypeFilter(v); setPage(1); }}>
                <SelectTrigger>
                  <SelectValue placeholder="All Types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  {OUTLET_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {formatOutletType(t)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Retailers Table */}
      <Card>
        <CardContent className="pt-4">
          {retailers.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-3 font-medium text-muted-foreground">Outlet Code</th>
                      <th className="pb-3 font-medium text-muted-foreground">Name</th>
                      <th className="pb-3 font-medium text-muted-foreground">Owner</th>
                      <th className="pb-3 font-medium text-muted-foreground">Dealer</th>
                      <th className="pb-3 font-medium text-muted-foreground text-center">Type</th>
                      <th className="pb-3 font-medium text-muted-foreground">City</th>
                      <th className="pb-3 font-medium text-muted-foreground text-center">Beat Day</th>
                      <th className="pb-3 font-medium text-muted-foreground text-right">Orders</th>
                      <th className="pb-3 font-medium text-muted-foreground text-right">Revenue</th>
                      <th className="pb-3 font-medium text-muted-foreground text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {retailers.map((outlet) => (
                      <tr
                        key={outlet.id}
                        className="border-b last:border-0 hover:bg-muted/50 cursor-pointer"
                        onClick={() => handleOpenEdit(outlet)}
                      >
                        <td className="py-3 font-mono text-xs font-medium">{outlet.outlet_code}</td>
                        <td className="py-3">
                          <span className="font-medium">{outlet.name}</span>
                        </td>
                        <td className="py-3 text-muted-foreground">{outlet.owner_name}</td>
                        <td className="py-3">
                          <div>
                            <span className="font-medium">{outlet.dealer_name}</span>
                            {outlet.dealer_code && (
                              <span className="text-xs text-muted-foreground ml-1">({outlet.dealer_code})</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 text-center">
                          <Badge variant="outline" className={`text-[10px] ${getOutletTypeBadge(outlet.outlet_type)}`}>
                            {formatOutletType(outlet.outlet_type)}
                          </Badge>
                        </td>
                        <td className="py-3">
                          <div className="flex items-center gap-1 text-muted-foreground">
                            <MapPin className="h-3 w-3" />
                            <span>{outlet.city}</span>
                          </div>
                        </td>
                        <td className="py-3 text-center text-xs text-muted-foreground">
                          {outlet.beat_day ? outlet.beat_day.charAt(0) + outlet.beat_day.slice(1).toLowerCase() : '-'}
                        </td>
                        <td className="py-3 text-right tabular-nums">{outlet.total_orders}</td>
                        <td className="py-3 text-right tabular-nums font-semibold">
                          {formatCurrency(outlet.total_revenue)}
                        </td>
                        <td className="py-3 text-center">
                          <Badge variant="outline" className={`text-[10px] ${getStatusColor(outlet.status)}`}>
                            {outlet.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {totalPages} ({totalRetailers} outlets)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <Store className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-muted-foreground">No retailer outlets found</p>
              <Button variant="outline" className="mt-3" onClick={handleOpenCreate}>
                <Plus className="h-4 w-4 mr-2" /> Add First Outlet
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create / Edit Outlet Dialog */}
      <Dialog open={showDialog} onOpenChange={(open) => { if (!open) handleCloseDialog(); else setShowDialog(open); }}>
        <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Store className="h-5 w-5 text-orange-600" />
              {editingOutlet ? 'Edit Outlet' : 'Add Retailer Outlet'}
            </DialogTitle>
            <DialogDescription>
              {editingOutlet
                ? `Update details for ${editingOutlet.name} (${editingOutlet.outlet_code})`
                : 'Register a new retailer outlet under a dealer.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Dealer */}
            <div>
              <Label>Dealer *</Label>
              <Select value={formData.dealer_id} onValueChange={(v) => setFormData({ ...formData, dealer_id: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a dealer..." />
                </SelectTrigger>
                <SelectContent>
                  {dealers.filter((d) => d.status === 'ACTIVE').map((d) => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.dealer_code || d.code} - {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Name & Owner */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Outlet Name *</Label>
                <Input
                  placeholder="e.g. Sharma General Store"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div>
                <Label>Owner Name *</Label>
                <Input
                  placeholder="e.g. Ramesh Sharma"
                  value={formData.owner_name}
                  onChange={(e) => setFormData({ ...formData, owner_name: e.target.value })}
                />
              </div>
            </div>

            {/* Outlet Type & Beat Day */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Outlet Type *</Label>
                <Select value={formData.outlet_type} onValueChange={(v) => setFormData({ ...formData, outlet_type: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select type..." />
                  </SelectTrigger>
                  <SelectContent>
                    {OUTLET_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {formatOutletType(t)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Beat Day</Label>
                <Select value={formData.beat_day} onValueChange={(v) => setFormData({ ...formData, beat_day: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select day..." />
                  </SelectTrigger>
                  <SelectContent>
                    {BEAT_DAYS.map((d) => (
                      <SelectItem key={d} value={d}>
                        {d.charAt(0) + d.slice(1).toLowerCase()}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Phone & Email */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Phone *</Label>
                <Input
                  placeholder="e.g. 9876543210"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                />
              </div>
              <div>
                <Label>Email</Label>
                <Input
                  placeholder="e.g. shop@example.com"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
            </div>

            {/* Address */}
            <div>
              <Label>Address *</Label>
              <Input
                placeholder="Street address, landmark..."
                value={formData.address_line1}
                onChange={(e) => setFormData({ ...formData, address_line1: e.target.value })}
              />
            </div>

            {/* City, State, Pincode */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>City *</Label>
                <Input
                  placeholder="e.g. Delhi"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                />
              </div>
              <div>
                <Label>State *</Label>
                <Input
                  placeholder="e.g. Delhi"
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                />
              </div>
              <div>
                <Label>Pincode *</Label>
                <Input
                  placeholder="e.g. 110001"
                  value={formData.pincode}
                  onChange={(e) => setFormData({ ...formData, pincode: e.target.value })}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseDialog}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={isMutating}>
              {isMutating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {editingOutlet ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                <>
                  <Store className="h-4 w-4 mr-2" />
                  {editingOutlet ? 'Update Outlet' : 'Create Outlet'}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
