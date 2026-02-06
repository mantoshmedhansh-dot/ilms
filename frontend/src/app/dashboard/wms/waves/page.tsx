'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Waves, Plus, Play, CheckCircle, Clock, Package, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
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
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import apiClient from '@/lib/api/client';

interface Wave {
  id: string;
  wave_number: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  total_orders: number;
  total_items: number;
  picked_items: number;
  assigned_pickers: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

interface WaveStats {
  total_waves: number;
  active_waves: number;
  completed_today: number;
  pending_orders: number;
}

interface Warehouse {
  id: string;
  code: string;
  name: string;
}

interface WaveCreatePayload {
  warehouse_id: string;
  wave_type: string;
  name?: string;
  auto_select_orders: boolean;
  auto_release: boolean;
  optimize_route: boolean;
  group_by_zone: boolean;
}

const WAVE_TYPES = [
  { value: 'CARRIER_CUTOFF', label: 'Carrier Cutoff', description: 'Group orders by carrier pickup time' },
  { value: 'PRIORITY', label: 'Priority', description: 'Group by order priority/SLA' },
  { value: 'ZONE', label: 'Zone', description: 'Group by warehouse zone' },
  { value: 'PRODUCT', label: 'Product', description: 'Group by product category' },
  { value: 'CHANNEL', label: 'Channel', description: 'Group by sales channel' },
  { value: 'CUSTOMER', label: 'Customer', description: 'Group by customer type' },
  { value: 'CUSTOM', label: 'Custom', description: 'Custom rule-based grouping' },
];

const wavesApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/wms-advanced/waves', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<WaveStats> => {
    try {
      const { data } = await apiClient.get('/wms-advanced/waves/stats');
      return data;
    } catch {
      return { total_waves: 0, active_waves: 0, completed_today: 0, pending_orders: 0 };
    }
  },
  create: async (payload: WaveCreatePayload) => {
    const { data } = await apiClient.post('/wms-advanced/waves', payload);
    return data;
  },
  getWarehouses: async (): Promise<Warehouse[]> => {
    try {
      const { data } = await apiClient.get('/warehouses/dropdown');
      return data;
    } catch {
      return [];
    }
  },
};

const priorityColors: Record<string, string> = {
  LOW: 'bg-gray-100 text-gray-800',
  MEDIUM: 'bg-blue-100 text-blue-800',
  HIGH: 'bg-orange-100 text-orange-800',
  URGENT: 'bg-red-100 text-red-800',
};

const columns: ColumnDef<Wave>[] = [
  {
    accessorKey: 'wave_number',
    header: 'Wave',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Waves className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.wave_number}</div>
          <div className="text-xs text-muted-foreground">
            {new Date(row.original.created_at).toLocaleDateString()}
          </div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'priority',
    header: 'Priority',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${priorityColors[row.original.priority]}`}>
        {row.original.priority}
      </span>
    ),
  },
  {
    accessorKey: 'total_orders',
    header: 'Orders',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Package className="h-4 w-4 text-muted-foreground" />
        <span className="font-mono">{row.original.total_orders}</span>
      </div>
    ),
  },
  {
    accessorKey: 'progress',
    header: 'Progress',
    cell: ({ row }) => {
      const progress = row.original.total_items > 0
        ? (row.original.picked_items / row.original.total_items) * 100
        : 0;
      return (
        <div className="space-y-1">
          <div className="text-sm">{row.original.picked_items} / {row.original.total_items} items</div>
          <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'assigned_pickers',
    header: 'Pickers',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Users className="h-4 w-4 text-muted-foreground" />
        <span>{row.original.assigned_pickers}</span>
      </div>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

export default function WavesPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState<WaveCreatePayload>({
    warehouse_id: '',
    wave_type: 'CARRIER_CUTOFF',
    name: '',
    auto_select_orders: true,
    auto_release: false,
    optimize_route: true,
    group_by_zone: true,
  });

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['wms-waves', page, pageSize],
    queryFn: () => wavesApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-waves-stats'],
    queryFn: wavesApi.getStats,
  });

  const { data: warehouses } = useQuery({
    queryKey: ['warehouses-dropdown'],
    queryFn: wavesApi.getWarehouses,
  });

  const createMutation = useMutation({
    mutationFn: wavesApi.create,
    onSuccess: () => {
      toast.success('Wave created successfully');
      setIsDialogOpen(false);
      setFormData({
        warehouse_id: '',
        wave_type: 'CARRIER_CUTOFF',
        name: '',
        auto_select_orders: true,
        auto_release: false,
        optimize_route: true,
        group_by_zone: true,
      });
      queryClient.invalidateQueries({ queryKey: ['wms-waves'] });
      queryClient.invalidateQueries({ queryKey: ['wms-waves-stats'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create wave');
    },
  });

  const handleSubmit = () => {
    if (!formData.warehouse_id) {
      toast.error('Please select a warehouse');
      return;
    }
    createMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Wave Management</h1>
          <p className="text-muted-foreground mt-1">
            Create and manage picking waves for efficient order fulfillment
          </p>
        </div>
        <Button onClick={() => setIsDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Wave
        </Button>
      </div>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Create New Wave</DialogTitle>
            <DialogDescription>
              Configure and create a new picking wave for order fulfillment
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="warehouse">Warehouse *</Label>
              <Select
                value={formData.warehouse_id}
                onValueChange={(value) => setFormData({ ...formData, warehouse_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {warehouses?.map((wh) => (
                    <SelectItem key={wh.id} value={wh.id}>
                      {wh.code} - {wh.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="wave_type">Wave Type</Label>
              <Select
                value={formData.wave_type}
                onValueChange={(value) => setFormData({ ...formData, wave_type: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select wave type" />
                </SelectTrigger>
                <SelectContent>
                  {WAVE_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      <div>
                        <div className="font-medium">{type.label}</div>
                        <div className="text-xs text-muted-foreground">{type.description}</div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="name">Wave Name (Optional)</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Morning Batch"
              />
            </div>

            <div className="space-y-4 pt-2">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto-select Orders</Label>
                  <p className="text-xs text-muted-foreground">
                    Automatically select eligible orders
                  </p>
                </div>
                <Switch
                  checked={formData.auto_select_orders}
                  onCheckedChange={(checked) => setFormData({ ...formData, auto_select_orders: checked })}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto-release Wave</Label>
                  <p className="text-xs text-muted-foreground">
                    Immediately release after creation
                  </p>
                </div>
                <Switch
                  checked={formData.auto_release}
                  onCheckedChange={(checked) => setFormData({ ...formData, auto_release: checked })}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Optimize Route</Label>
                  <p className="text-xs text-muted-foreground">
                    Optimize picking path for efficiency
                  </p>
                </div>
                <Switch
                  checked={formData.optimize_route}
                  onCheckedChange={(checked) => setFormData({ ...formData, optimize_route: checked })}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Group by Zone</Label>
                  <p className="text-xs text-muted-foreground">
                    Group picks by warehouse zone
                  </p>
                </div>
                <Switch
                  checked={formData.group_by_zone}
                  onCheckedChange={(checked) => setFormData({ ...formData, group_by_zone: checked })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Wave'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Waves</CardTitle>
            <Waves className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_waves || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Waves</CardTitle>
            <Play className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.active_waves || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed Today</CardTitle>
            <CheckCircle className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.completed_today || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Orders</CardTitle>
            <Clock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.pending_orders || 0}</div>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="wave_number"
        searchPlaceholder="Search waves..."
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
