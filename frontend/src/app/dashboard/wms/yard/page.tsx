'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Truck, Plus, MapPin, Clock, AlertTriangle } from 'lucide-react';
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

interface YardAppointment {
  id: string;
  appointment_number: string;
  carrier_name: string;
  vehicle_number: string;
  driver_name?: string;
  appointment_type: 'INBOUND' | 'OUTBOUND';
  dock_door?: string;
  scheduled_time: string;
  arrival_time?: string;
  departure_time?: string;
  status: 'SCHEDULED' | 'ARRIVED' | 'DOCKED' | 'LOADING' | 'UNLOADING' | 'COMPLETED' | 'CANCELLED' | 'DELAYED';
  po_numbers?: string[];
  notes?: string;
}

interface YardStats {
  total_appointments: number;
  in_yard: number;
  awaiting_arrival: number;
  delayed: number;
}

interface NewAppointmentData {
  carrier_name: string;
  vehicle_number: string;
  driver_name: string;
  appointment_type: 'INBOUND' | 'OUTBOUND';
  dock_door: string;
  scheduled_time: string;
  status: 'SCHEDULED' | 'ARRIVED' | 'DOCKED' | 'LOADING' | 'UNLOADING' | 'COMPLETED' | 'CANCELLED' | 'DELAYED';
  notes: string;
}

const initialFormData: NewAppointmentData = {
  carrier_name: '',
  vehicle_number: '',
  driver_name: '',
  appointment_type: 'INBOUND',
  dock_door: '',
  scheduled_time: '',
  status: 'SCHEDULED',
  notes: '',
};

const appointmentTypes = [
  { label: 'Inbound', value: 'INBOUND' },
  { label: 'Outbound', value: 'OUTBOUND' },
];

const appointmentStatuses = [
  { label: 'Scheduled', value: 'SCHEDULED' },
  { label: 'Arrived', value: 'ARRIVED' },
  { label: 'Docked', value: 'DOCKED' },
  { label: 'Loading', value: 'LOADING' },
  { label: 'Unloading', value: 'UNLOADING' },
  { label: 'Completed', value: 'COMPLETED' },
  { label: 'Cancelled', value: 'CANCELLED' },
  { label: 'Delayed', value: 'DELAYED' },
];

const yardApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/yard/appointments', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<YardStats> => {
    try {
      const { data } = await apiClient.get('/yard/stats');
      return data;
    } catch {
      return { total_appointments: 0, in_yard: 0, awaiting_arrival: 0, delayed: 0 };
    }
  },
  create: async (appointmentData: NewAppointmentData) => {
    const { data } = await apiClient.post('/yard/appointments', appointmentData);
    return data;
  },
};

const typeColors: Record<string, string> = {
  INBOUND: 'bg-green-100 text-green-800',
  OUTBOUND: 'bg-blue-100 text-blue-800',
};

const columns: ColumnDef<YardAppointment>[] = [
  {
    accessorKey: 'appointment_number',
    header: 'Appointment',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Truck className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.appointment_number}</div>
          <div className="text-xs text-muted-foreground">{row.original.carrier_name}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'appointment_type',
    header: 'Type',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${typeColors[row.original.appointment_type]}`}>
        {row.original.appointment_type}
      </span>
    ),
  },
  {
    accessorKey: 'vehicle_number',
    header: 'Vehicle',
    cell: ({ row }) => (
      <div>
        <div className="font-mono text-sm">{row.original.vehicle_number}</div>
        {row.original.driver_name && (
          <div className="text-xs text-muted-foreground">{row.original.driver_name}</div>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'dock_door',
    header: 'Dock',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <MapPin className="h-4 w-4 text-muted-foreground" />
        <span>{row.original.dock_door || 'Not assigned'}</span>
      </div>
    ),
  },
  {
    accessorKey: 'scheduled_time',
    header: 'Scheduled',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">{new Date(row.original.scheduled_time).toLocaleString()}</span>
      </div>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

export default function YardPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState<NewAppointmentData>(initialFormData);

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['wms-yard', page, pageSize],
    queryFn: () => yardApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-yard-stats'],
    queryFn: yardApi.getStats,
  });

  const createMutation = useMutation({
    mutationFn: yardApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-yard'] });
      queryClient.invalidateQueries({ queryKey: ['wms-yard-stats'] });
      toast.success('Appointment created successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create appointment');
    },
  });

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setFormData(initialFormData);
  };

  const handleSubmit = () => {
    if (!formData.carrier_name.trim()) {
      toast.error('Carrier name is required');
      return;
    }
    if (!formData.vehicle_number.trim()) {
      toast.error('Vehicle number is required');
      return;
    }
    if (!formData.scheduled_time) {
      toast.error('Scheduled time is required');
      return;
    }

    createMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Yard Management"
        description="Manage dock appointments and yard operations"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Appointment
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Appointments</CardTitle>
            <Truck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_appointments || 0}</div>
            <p className="text-xs text-muted-foreground">Today</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Yard</CardTitle>
            <MapPin className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.in_yard || 0}</div>
            <p className="text-xs text-muted-foreground">Vehicles</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Awaiting Arrival</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.awaiting_arrival || 0}</div>
            <p className="text-xs text-muted-foreground">Scheduled</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Delayed</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.delayed || 0}</div>
            <p className="text-xs text-muted-foreground">Appointments</p>
          </CardContent>
        </Card>
      </div>

      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create New Appointment</DialogTitle>
            <DialogDescription>
              Schedule a new yard appointment for dock operations.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
            <div className="space-y-2">
              <Label htmlFor="carrier_name">Carrier Name *</Label>
              <Input
                id="carrier_name"
                placeholder="Enter carrier name"
                value={formData.carrier_name}
                onChange={(e) =>
                  setFormData({ ...formData, carrier_name: e.target.value })
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="vehicle_number">Vehicle Number *</Label>
                <Input
                  id="vehicle_number"
                  placeholder="e.g., ABC-1234"
                  value={formData.vehicle_number}
                  onChange={(e) =>
                    setFormData({ ...formData, vehicle_number: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="driver_name">Driver Name</Label>
                <Input
                  id="driver_name"
                  placeholder="Driver name"
                  value={formData.driver_name}
                  onChange={(e) =>
                    setFormData({ ...formData, driver_name: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="appointment_type">Appointment Type *</Label>
              <Select
                value={formData.appointment_type}
                onValueChange={(value: 'INBOUND' | 'OUTBOUND') =>
                  setFormData({ ...formData, appointment_type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {appointmentTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="dock_door">Dock Number</Label>
                <Input
                  id="dock_door"
                  placeholder="e.g., D-01"
                  value={formData.dock_door}
                  onChange={(e) =>
                    setFormData({ ...formData, dock_door: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="scheduled_time">Scheduled Time *</Label>
                <Input
                  id="scheduled_time"
                  type="datetime-local"
                  value={formData.scheduled_time}
                  onChange={(e) =>
                    setFormData({ ...formData, scheduled_time: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select
                value={formData.status}
                onValueChange={(value: NewAppointmentData['status']) =>
                  setFormData({ ...formData, status: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {appointmentStatuses.map((status) => (
                    <SelectItem key={status.value} value={status.value}>
                      {status.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Input
                id="notes"
                placeholder="Additional notes"
                value={formData.notes}
                onChange={(e) =>
                  setFormData({ ...formData, notes: e.target.value })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleDialogClose}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Appointment'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="appointment_number"
        searchPlaceholder="Search appointments..."
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
