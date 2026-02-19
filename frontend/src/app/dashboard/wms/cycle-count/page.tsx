'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { ClipboardList, Plus, CheckCircle, XCircle, Clock, BarChart3, AlertTriangle } from 'lucide-react';
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

interface CycleCount {
  id: string;
  count_number: string;
  count_type: 'FULL' | 'ABC' | 'RANDOM' | 'ZONE' | 'SKU';
  zone_name?: string;
  locations_total: number;
  locations_counted: number;
  items_counted: number;
  variances_found: number;
  variance_value: number;
  assigned_to?: string;
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'REVIEW';
  scheduled_date: string;
  started_at?: string;
  completed_at?: string;
  accuracy_rate?: number;
}

interface CycleCountStats {
  total_counts: number;
  in_progress: number;
  avg_accuracy: number;
  variances_pending: number;
}

interface ScheduleCycleCountData {
  zone_name: string;
  count_type: 'FULL' | 'ABC' | 'RANDOM';
  scheduled_date: string;
  assigned_to: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH';
}

const cycleCountApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/cycle-count/plans', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<CycleCountStats> => {
    try {
      const { data } = await apiClient.get('/cycle-count/plans/stats');
      return data;
    } catch {
      return { total_counts: 0, in_progress: 0, avg_accuracy: 0, variances_pending: 0 };
    }
  },
  schedule: async (data: ScheduleCycleCountData) => {
    const response = await apiClient.post('/cycle-count/plans', data);
    return response.data;
  },
};

const countTypeColors: Record<string, string> = {
  FULL: 'bg-purple-100 text-purple-800',
  ABC: 'bg-blue-100 text-blue-800',
  RANDOM: 'bg-green-100 text-green-800',
  ZONE: 'bg-orange-100 text-orange-800',
  SKU: 'bg-cyan-100 text-cyan-800',
};

const columns: ColumnDef<CycleCount>[] = [
  {
    accessorKey: 'count_number',
    header: 'Count',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <ClipboardList className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.count_number}</div>
          <div className="text-xs text-muted-foreground">
            {new Date(row.original.scheduled_date).toLocaleDateString()}
          </div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'count_type',
    header: 'Type',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${countTypeColors[row.original.count_type]}`}>
        {row.original.count_type}
      </span>
    ),
  },
  {
    accessorKey: 'progress',
    header: 'Progress',
    cell: ({ row }) => {
      const progress = row.original.locations_total > 0
        ? (row.original.locations_counted / row.original.locations_total) * 100
        : 0;
      return (
        <div className="space-y-1">
          <div className="text-sm">{row.original.locations_counted} / {row.original.locations_total} locations</div>
          <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-blue-500" style={{ width: `${progress}%` }} />
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'variances',
    header: 'Variances',
    cell: ({ row }) => {
      const hasVariances = row.original.variances_found > 0;
      return (
        <div className={`flex items-center gap-2 ${hasVariances ? 'text-red-600' : 'text-green-600'}`}>
          {hasVariances ? (
            <XCircle className="h-4 w-4" />
          ) : (
            <CheckCircle className="h-4 w-4" />
          )}
          <span>{row.original.variances_found}</span>
          {hasVariances && (
            <span className="text-xs">(${row.original.variance_value.toFixed(2)})</span>
          )}
        </div>
      );
    },
  },
  {
    accessorKey: 'accuracy_rate',
    header: 'Accuracy',
    cell: ({ row }) => {
      const accuracy = row.original.accuracy_rate;
      if (!accuracy) return <span className="text-muted-foreground">-</span>;
      const color = accuracy >= 99 ? 'text-green-600' : accuracy >= 95 ? 'text-yellow-600' : 'text-red-600';
      return (
        <span className={`font-medium ${color}`}>{accuracy.toFixed(1)}%</span>
      );
    },
  },
  {
    accessorKey: 'assigned_to',
    header: 'Assigned To',
    cell: ({ row }) => (
      <span className="text-sm">{row.original.assigned_to || 'Unassigned'}</span>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

const countTypes = [
  { label: 'Full Count', value: 'FULL' },
  { label: 'ABC Analysis', value: 'ABC' },
  { label: 'Random Sample', value: 'RANDOM' },
];

const priorityOptions = [
  { label: 'Low', value: 'LOW' },
  { label: 'Medium', value: 'MEDIUM' },
  { label: 'High', value: 'HIGH' },
];

export default function CycleCountPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState<{
    zone_name: string;
    count_type: 'FULL' | 'ABC' | 'RANDOM';
    scheduled_date: string;
    assigned_to: string;
    priority: 'LOW' | 'MEDIUM' | 'HIGH';
  }>({
    zone_name: '',
    count_type: 'FULL',
    scheduled_date: '',
    assigned_to: '',
    priority: 'MEDIUM',
  });

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['wms-cycle-count', page, pageSize],
    queryFn: () => cycleCountApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-cycle-count-stats'],
    queryFn: cycleCountApi.getStats,
  });

  const scheduleMutation = useMutation({
    mutationFn: cycleCountApi.schedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-cycle-count'] });
      queryClient.invalidateQueries({ queryKey: ['wms-cycle-count-stats'] });
      toast.success('Cycle count scheduled successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to schedule cycle count');
    },
  });

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setFormData({
      zone_name: '',
      count_type: 'FULL',
      scheduled_date: '',
      assigned_to: '',
      priority: 'MEDIUM',
    });
  };

  const handleSubmit = () => {
    if (!formData.zone_name.trim()) {
      toast.error('Zone/Area is required');
      return;
    }
    if (!formData.scheduled_date) {
      toast.error('Scheduled date is required');
      return;
    }

    scheduleMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cycle Counting"
        description="Schedule and manage inventory cycle counts for accuracy"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Schedule Count
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Schedule Cycle Count</DialogTitle>
            <DialogDescription>
              Schedule a new cycle count for inventory accuracy verification.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="zone_name">Zone/Area *</Label>
              <Input
                id="zone_name"
                placeholder="e.g., Zone A, Receiving Area"
                value={formData.zone_name}
                onChange={(e) =>
                  setFormData({ ...formData, zone_name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="count_type">Count Type</Label>
              <Select
                value={formData.count_type}
                onValueChange={(value: 'FULL' | 'ABC' | 'RANDOM') =>
                  setFormData({ ...formData, count_type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select count type" />
                </SelectTrigger>
                <SelectContent>
                  {countTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="scheduled_date">Scheduled Date *</Label>
              <Input
                id="scheduled_date"
                type="date"
                value={formData.scheduled_date}
                onChange={(e) =>
                  setFormData({ ...formData, scheduled_date: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="assigned_to">Assigned Counter</Label>
              <Input
                id="assigned_to"
                placeholder="Counter name"
                value={formData.assigned_to}
                onChange={(e) =>
                  setFormData({ ...formData, assigned_to: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="priority">Priority</Label>
              <Select
                value={formData.priority}
                onValueChange={(value: 'LOW' | 'MEDIUM' | 'HIGH') =>
                  setFormData({ ...formData, priority: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  {priorityOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
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
            <Button onClick={handleSubmit} disabled={scheduleMutation.isPending}>
              {scheduleMutation.isPending ? 'Scheduling...' : 'Schedule Count'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Counts</CardTitle>
            <ClipboardList className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_counts || 0}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Progress</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.in_progress || 0}</div>
            <p className="text-xs text-muted-foreground">Active counts</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Accuracy</CardTitle>
            <BarChart3 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.avg_accuracy || 0}%</div>
            <p className="text-xs text-muted-foreground">Inventory accuracy</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Variances Pending</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.variances_pending || 0}</div>
            <p className="text-xs text-muted-foreground">Needs review</p>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="count_number"
        searchPlaceholder="Search counts..."
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
