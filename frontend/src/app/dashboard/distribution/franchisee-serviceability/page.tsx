'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { toast } from 'sonner';
import {
  MoreHorizontal, Plus, MapPin, Check, X, Loader2, Search, Upload, Download
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface Franchisee {
  id: string;
  name: string;
  code: string;
  status: string;
}

interface ServiceabilityZone {
  id: string;
  franchisee_id: string;
  franchisee?: Franchisee;
  pincode: string;
  city?: string;
  state?: string;
  is_active: boolean;
  priority: number;
  delivery_days?: number;
  cod_available: boolean;
  created_at: string;
}

const serviceabilityApi = {
  list: async (params?: { page?: number; size?: number; franchisee_id?: string; pincode?: string }) => {
    try {
      const { data } = await apiClient.get('/serviceability/zones', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getFranchisees: async () => {
    try {
      const { data } = await apiClient.get('/franchisees', { params: { status: 'ACTIVE', size: 100 } });
      return data?.items || [];
    } catch {
      return [];
    }
  },
  create: async (zone: Partial<ServiceabilityZone>) => {
    const { data } = await apiClient.post('/serviceability/zones', zone);
    return data;
  },
  bulkCreate: async (franchisee_id: string, pincodes: string[]) => {
    const { data } = await apiClient.post('/serviceability/zones/bulk', { franchisee_id, pincodes });
    return data;
  },
  update: async (id: string, zone: Partial<ServiceabilityZone>) => {
    const { data } = await apiClient.put(`/serviceability/zones/${id}`, zone);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/serviceability/zones/${id}`);
  },
  checkPincode: async (pincode: string) => {
    const { data } = await apiClient.get(`/serviceability/check/${pincode}`);
    return data;
  },
};

interface ZoneFormData {
  franchisee_id: string;
  pincode: string;
  city: string;
  state: string;
  priority: number;
  delivery_days: number;
  cod_available: boolean;
}

const initialFormData: ZoneFormData = {
  franchisee_id: '',
  pincode: '',
  city: '',
  state: '',
  priority: 1,
  delivery_days: 3,
  cod_available: true,
};

export default function FranchiseeServiceabilityPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [franchiseeFilter, setFranchiseeFilter] = useState<string>('all');
  const [pincodeSearch, setPincodeSearch] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isBulkDialogOpen, setIsBulkDialogOpen] = useState(false);
  const [formData, setFormData] = useState<ZoneFormData>(initialFormData);
  const [bulkPincodes, setBulkPincodes] = useState('');
  const [bulkFranchiseeId, setBulkFranchiseeId] = useState('');
  const [checkPincode, setCheckPincode] = useState('');
  const [checkResult, setCheckResult] = useState<any>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['serviceability-zones', page, pageSize, franchiseeFilter, pincodeSearch],
    queryFn: () => serviceabilityApi.list({
      page: page + 1,
      size: pageSize,
      franchisee_id: franchiseeFilter !== 'all' ? franchiseeFilter : undefined,
      pincode: pincodeSearch || undefined,
    }),
  });

  const { data: franchisees = [] } = useQuery({
    queryKey: ['franchisees-dropdown'],
    queryFn: serviceabilityApi.getFranchisees,
  });

  const createMutation = useMutation({
    mutationFn: serviceabilityApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['serviceability-zones'] });
      toast.success('Serviceability zone added');
      setIsDialogOpen(false);
      setFormData(initialFormData);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add zone');
    },
  });

  const bulkCreateMutation = useMutation({
    mutationFn: ({ franchisee_id, pincodes }: { franchisee_id: string; pincodes: string[] }) =>
      serviceabilityApi.bulkCreate(franchisee_id, pincodes),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['serviceability-zones'] });
      toast.success(`Added ${data.created || 0} pincodes`);
      setIsBulkDialogOpen(false);
      setBulkPincodes('');
      setBulkFranchiseeId('');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add pincodes');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: serviceabilityApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['serviceability-zones'] });
      toast.success('Zone removed');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to remove zone');
    },
  });

  const handleCheckPincode = async () => {
    if (!checkPincode || checkPincode.length !== 6) {
      toast.error('Please enter a valid 6-digit pincode');
      return;
    }
    try {
      const result = await serviceabilityApi.checkPincode(checkPincode);
      setCheckResult(result);
    } catch {
      setCheckResult({ serviceable: false, message: 'Pincode not found' });
    }
  };

  const handleSubmit = () => {
    if (!formData.franchisee_id || !formData.pincode) {
      toast.error('Franchisee and pincode are required');
      return;
    }
    createMutation.mutate(formData);
  };

  const handleBulkSubmit = () => {
    if (!bulkFranchiseeId) {
      toast.error('Please select a franchisee');
      return;
    }
    const pincodes = bulkPincodes.split(/[\n,]/).map(p => p.trim()).filter(p => p.length === 6);
    if (pincodes.length === 0) {
      toast.error('Please enter valid pincodes');
      return;
    }
    bulkCreateMutation.mutate({ franchisee_id: bulkFranchiseeId, pincodes });
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
      accessorKey: 'city',
      header: 'City / State',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.city || '-'}</div>
          <div className="text-xs text-muted-foreground">{row.original.state}</div>
        </div>
      ),
    },
    {
      accessorKey: 'franchisee',
      header: 'Franchisee',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.franchisee?.name || '-'}</div>
          <div className="text-xs text-muted-foreground">{row.original.franchisee?.code}</div>
        </div>
      ),
    },
    {
      accessorKey: 'priority',
      header: 'Priority',
      cell: ({ row }) => (
        <Badge variant={row.original.priority === 1 ? 'default' : 'secondary'}>
          P{row.original.priority}
        </Badge>
      ),
    },
    {
      accessorKey: 'delivery_days',
      header: 'Delivery Days',
      cell: ({ row }) => <span>{row.original.delivery_days || '-'} days</span>,
    },
    {
      accessorKey: 'cod_available',
      header: 'COD',
      cell: ({ row }) => (
        row.original.cod_available ? (
          <Check className="h-4 w-4 text-green-600" />
        ) : (
          <X className="h-4 w-4 text-red-600" />
        )
      ),
    },
    {
      accessorKey: 'is_active',
      header: 'Status',
      cell: ({ row }) => (
        <StatusBadge status={row.original.is_active ? 'ACTIVE' : 'INACTIVE'} />
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
              className="text-destructive"
              onClick={() => deleteMutation.mutate(row.original.id)}
            >
              Remove Zone
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const zones = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Franchisee Serviceability"
        description="Manage serviceable pincodes for franchisees"
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setIsBulkDialogOpen(true)}>
              <Upload className="mr-2 h-4 w-4" />
              Bulk Import
            </Button>
            <Button onClick={() => setIsDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Pincode
            </Button>
          </div>
        }
      />

      {/* Pincode Checker */}
      <Card>
        <CardHeader className="py-4">
          <CardTitle className="text-base">Check Serviceability</CardTitle>
        </CardHeader>
        <CardContent className="flex items-end gap-4">
          <div className="flex-1 max-w-xs space-y-2">
            <Label>Enter Pincode</Label>
            <Input
              placeholder="e.g., 110001"
              value={checkPincode}
              onChange={(e) => {
                setCheckPincode(e.target.value.replace(/\D/g, '').slice(0, 6));
                setCheckResult(null);
              }}
            />
          </div>
          <Button onClick={handleCheckPincode}>
            <Search className="mr-2 h-4 w-4" />
            Check
          </Button>
          {checkResult && (
            <div className={`flex items-center gap-2 px-4 py-2 rounded-md ${
              checkResult.serviceable ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              {checkResult.serviceable ? (
                <>
                  <Check className="h-4 w-4" />
                  <span>Serviceable by {checkResult.franchisee?.name || 'Partner'}</span>
                </>
              ) : (
                <>
                  <X className="h-4 w-4" />
                  <span>Not Serviceable</span>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="w-64">
          <Select value={franchiseeFilter} onValueChange={setFranchiseeFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Filter by franchisee" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Franchisees</SelectItem>
              {franchisees.map((f: Franchisee) => (
                <SelectItem key={f.id} value={f.id}>{f.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Input
          placeholder="Search by pincode..."
          className="w-48"
          value={pincodeSearch}
          onChange={(e) => setPincodeSearch(e.target.value.replace(/\D/g, ''))}
        />
      </div>

      <DataTable
        columns={columns}
        data={zones}
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

      {/* Add Single Pincode Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Serviceable Pincode</DialogTitle>
            <DialogDescription>
              Add a pincode to a franchisee's serviceable area
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Franchisee *</Label>
              <Select
                value={formData.franchisee_id}
                onValueChange={(v) => setFormData({ ...formData, franchisee_id: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select franchisee" />
                </SelectTrigger>
                <SelectContent>
                  {franchisees.map((f: Franchisee) => (
                    <SelectItem key={f.id} value={f.id}>{f.name} ({f.code})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Pincode *</Label>
                <Input
                  placeholder="e.g., 110001"
                  value={formData.pincode}
                  onChange={(e) => setFormData({ ...formData, pincode: e.target.value.replace(/\D/g, '').slice(0, 6) })}
                />
              </div>
              <div className="space-y-2">
                <Label>Priority</Label>
                <Select
                  value={String(formData.priority)}
                  onValueChange={(v) => setFormData({ ...formData, priority: Number(v) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">P1 - Primary</SelectItem>
                    <SelectItem value="2">P2 - Secondary</SelectItem>
                    <SelectItem value="3">P3 - Backup</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>City</Label>
                <Input
                  placeholder="City name"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>State</Label>
                <Input
                  placeholder="State name"
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Delivery Days</Label>
                <Input
                  type="number"
                  min={1}
                  value={formData.delivery_days}
                  onChange={(e) => setFormData({ ...formData, delivery_days: Number(e.target.value) })}
                />
              </div>
              <div className="flex items-center gap-2 pt-6">
                <input
                  type="checkbox"
                  id="cod"
                  checked={formData.cod_available}
                  onChange={(e) => setFormData({ ...formData, cod_available: e.target.checked })}
                  className="h-4 w-4"
                />
                <Label htmlFor="cod">COD Available</Label>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Add Pincode
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Import Dialog */}
      <Dialog open={isBulkDialogOpen} onOpenChange={setIsBulkDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bulk Import Pincodes</DialogTitle>
            <DialogDescription>
              Import multiple pincodes for a franchisee at once
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Franchisee *</Label>
              <Select value={bulkFranchiseeId} onValueChange={setBulkFranchiseeId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select franchisee" />
                </SelectTrigger>
                <SelectContent>
                  {franchisees.map((f: Franchisee) => (
                    <SelectItem key={f.id} value={f.id}>{f.name} ({f.code})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Pincodes (comma or newline separated)</Label>
              <textarea
                className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                placeholder="110001, 110002, 110003&#10;or&#10;110001&#10;110002&#10;110003"
                value={bulkPincodes}
                onChange={(e) => setBulkPincodes(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                {bulkPincodes.split(/[\n,]/).filter(p => p.trim().length === 6).length} valid pincodes found
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsBulkDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleBulkSubmit} disabled={bulkCreateMutation.isPending}>
              {bulkCreateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Import Pincodes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
