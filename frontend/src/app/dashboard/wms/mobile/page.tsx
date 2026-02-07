'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Smartphone, Plus, Wifi, WifiOff, Battery, BatteryLow, MapPin, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface MobileDevice {
  id: string;
  device_id: string;
  device_name: string;
  device_type: 'SCANNER' | 'TABLET' | 'HANDHELD' | 'FORKLIFT_TERMINAL';
  assigned_to?: string;
  assigned_zone?: string;
  status: 'ONLINE' | 'OFFLINE' | 'CHARGING' | 'MAINTENANCE';
  battery_level: number;
  last_seen: string;
  firmware_version: string;
  ip_address?: string;
}

interface MobileStats {
  total_devices: number;
  online_devices: number;
  low_battery: number;
  in_maintenance: number;
}

interface DeviceFormData {
  device_id: string;
  device_name: string;
  device_type: 'SCANNER' | 'TABLET' | 'HANDHELD' | 'FORKLIFT_TERMINAL';
  assigned_to: string;
  assigned_zone: string;
  status: 'ONLINE' | 'OFFLINE' | 'CHARGING' | 'MAINTENANCE';
}

const deviceTypes = [
  { label: 'Scanner', value: 'SCANNER' },
  { label: 'Tablet', value: 'TABLET' },
  { label: 'Handheld', value: 'HANDHELD' },
  { label: 'Forklift Terminal', value: 'FORKLIFT_TERMINAL' },
];

const deviceStatuses = [
  { label: 'Online', value: 'ONLINE' },
  { label: 'Offline', value: 'OFFLINE' },
  { label: 'Charging', value: 'CHARGING' },
  { label: 'Maintenance', value: 'MAINTENANCE' },
];

const initialFormData: DeviceFormData = {
  device_id: '',
  device_name: '',
  device_type: 'SCANNER',
  assigned_to: '',
  assigned_zone: '',
  status: 'OFFLINE',
};

const mobileApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/mobile-wms/devices', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<MobileStats> => {
    try {
      const { data } = await apiClient.get('/mobile-wms/stats');
      return data;
    } catch {
      return { total_devices: 0, online_devices: 0, low_battery: 0, in_maintenance: 0 };
    }
  },
  create: async (deviceData: DeviceFormData) => {
    const { data } = await apiClient.post('/mobile-wms/devices', deviceData);
    return data;
  },
};

const deviceTypeColors: Record<string, string> = {
  SCANNER: 'bg-blue-100 text-blue-800',
  TABLET: 'bg-green-100 text-green-800',
  HANDHELD: 'bg-purple-100 text-purple-800',
  FORKLIFT_TERMINAL: 'bg-orange-100 text-orange-800',
};

const columns: ColumnDef<MobileDevice>[] = [
  {
    accessorKey: 'device_name',
    header: 'Device',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Smartphone className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-medium">{row.original.device_name}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.original.device_id}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'device_type',
    header: 'Type',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${deviceTypeColors[row.original.device_type]}`}>
        {row.original.device_type.replace('_', ' ')}
      </span>
    ),
  },
  {
    accessorKey: 'assigned_to',
    header: 'Assigned To',
    cell: ({ row }) => (
      <div>
        <div className="text-sm">{row.original.assigned_to || 'Unassigned'}</div>
        {row.original.assigned_zone && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <MapPin className="h-3 w-3" />
            {row.original.assigned_zone}
          </div>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'battery_level',
    header: 'Battery',
    cell: ({ row }) => {
      const battery = row.original.battery_level;
      const isLow = battery < 20;
      return (
        <div className="flex items-center gap-2">
          {isLow ? (
            <BatteryLow className="h-4 w-4 text-red-600" />
          ) : (
            <Battery className="h-4 w-4 text-green-600" />
          )}
          <span className={`font-medium ${isLow ? 'text-red-600' : 'text-green-600'}`}>
            {battery}%
          </span>
        </div>
      );
    },
  },
  {
    accessorKey: 'last_seen',
    header: 'Last Seen',
    cell: ({ row }) => (
      <div className="text-sm text-muted-foreground">
        {new Date(row.original.last_seen).toLocaleString()}
      </div>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => {
      const status = row.original.status;
      const isOnline = status === 'ONLINE';
      return (
        <div className="flex items-center gap-2">
          {isOnline ? (
            <Wifi className="h-4 w-4 text-green-600" />
          ) : (
            <WifiOff className="h-4 w-4 text-gray-400" />
          )}
          <StatusBadge status={status} />
        </div>
      );
    },
  },
];

export default function MobilePage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState<DeviceFormData>(initialFormData);

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['wms-mobile', page, pageSize],
    queryFn: () => mobileApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-mobile-stats'],
    queryFn: mobileApi.getStats,
  });

  const createMutation = useMutation({
    mutationFn: mobileApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-mobile'] });
      queryClient.invalidateQueries({ queryKey: ['wms-mobile-stats'] });
      toast.success('Device registered successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to register device');
    },
  });

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setFormData(initialFormData);
  };

  const handleSubmit = () => {
    if (!formData.device_id.trim()) {
      toast.error('Device ID is required');
      return;
    }
    if (!formData.device_name.trim()) {
      toast.error('Device Name is required');
      return;
    }

    createMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mobile Devices"
        description="Manage warehouse mobile devices and scanners"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Register Device
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Register New Device</DialogTitle>
            <DialogDescription>
              Add a new mobile device to the warehouse management system.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="device_id">Device ID *</Label>
                <Input
                  id="device_id"
                  placeholder="e.g., DEV-001"
                  value={formData.device_id}
                  onChange={(e) =>
                    setFormData({ ...formData, device_id: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="device_name">Device Name *</Label>
                <Input
                  id="device_name"
                  placeholder="e.g., Scanner A1"
                  value={formData.device_name}
                  onChange={(e) =>
                    setFormData({ ...formData, device_name: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="device_type">Device Type</Label>
              <Select
                value={formData.device_type}
                onValueChange={(value: DeviceFormData['device_type']) =>
                  setFormData({ ...formData, device_type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select device type" />
                </SelectTrigger>
                <SelectContent>
                  {deviceTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="assigned_to">Assigned Worker</Label>
                <Input
                  id="assigned_to"
                  placeholder="Worker name"
                  value={formData.assigned_to}
                  onChange={(e) =>
                    setFormData({ ...formData, assigned_to: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="assigned_zone">Assigned Zone</Label>
                <Input
                  id="assigned_zone"
                  placeholder="e.g., Zone A"
                  value={formData.assigned_zone}
                  onChange={(e) =>
                    setFormData({ ...formData, assigned_zone: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Initial Status</Label>
              <Select
                value={formData.status}
                onValueChange={(value: DeviceFormData['status']) =>
                  setFormData({ ...formData, status: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {deviceStatuses.map((status) => (
                    <SelectItem key={status.value} value={status.value}>
                      {status.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleDialogClose}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {createMutation.isPending ? 'Registering...' : 'Register Device'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Devices</CardTitle>
            <Smartphone className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_devices || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Online</CardTitle>
            <Wifi className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.online_devices || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Low Battery</CardTitle>
            <BatteryLow className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.low_battery || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Maintenance</CardTitle>
            <WifiOff className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.in_maintenance || 0}</div>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="device_name"
        searchPlaceholder="Search devices..."
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
