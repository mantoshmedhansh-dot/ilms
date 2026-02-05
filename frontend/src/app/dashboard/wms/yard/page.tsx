'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Truck, Plus, MapPin, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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

const yardApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/wms/yard/appointments', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<YardStats> => {
    try {
      const { data } = await apiClient.get('/wms/yard/stats');
      return data;
    } catch {
      return { total_appointments: 0, in_yard: 0, awaiting_arrival: 0, delayed: 0 };
    }
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

  const { data, isLoading } = useQuery({
    queryKey: ['wms-yard', page, pageSize],
    queryFn: () => yardApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-yard-stats'],
    queryFn: yardApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Yard Management"
        description="Manage dock appointments and yard operations"
        actions={
          <Button>
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
