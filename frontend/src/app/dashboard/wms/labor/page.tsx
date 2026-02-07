'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Users, Plus, Clock, TrendingUp, Package, Timer, Award, Loader2 } from 'lucide-react';
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

interface Worker {
  id: string;
  employee_id: string;
  name: string;
  role: 'PICKER' | 'PACKER' | 'RECEIVER' | 'PUTAWAY' | 'SUPERVISOR';
  shift: 'MORNING' | 'AFTERNOON' | 'NIGHT';
  status: 'ACTIVE' | 'ON_BREAK' | 'OFF_DUTY';
  tasks_completed: number;
  items_processed: number;
  avg_time_per_task: number;
  performance_score: number;
  current_zone?: string;
}

interface LaborStats {
  total_workers: number;
  active_now: number;
  avg_productivity: number;
  tasks_completed_today: number;
}

interface NewWorkerForm {
  employee_id: string;
  name: string;
  role: 'PICKER' | 'PACKER' | 'RECEIVER' | 'PUTAWAY' | 'SUPERVISOR';
  shift: 'MORNING' | 'AFTERNOON' | 'NIGHT';
  current_zone: string;
}

const laborApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/labor/', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<LaborStats> => {
    try {
      const { data } = await apiClient.get('/labor/stats');
      return data;
    } catch {
      return { total_workers: 0, active_now: 0, avg_productivity: 0, tasks_completed_today: 0 };
    }
  },
  create: async (workerData: {
    employee_id: string;
    name: string;
    role: 'PICKER' | 'PACKER' | 'RECEIVER' | 'PUTAWAY' | 'SUPERVISOR';
    shift: 'MORNING' | 'AFTERNOON' | 'NIGHT';
    current_zone?: string;
  }) => {
    const { data } = await apiClient.post('/labor/', workerData);
    return data;
  },
};

const roleOptions = [
  { label: 'Picker', value: 'PICKER' },
  { label: 'Packer', value: 'PACKER' },
  { label: 'Receiver', value: 'RECEIVER' },
  { label: 'Putaway', value: 'PUTAWAY' },
  { label: 'Supervisor', value: 'SUPERVISOR' },
];

const shiftOptions = [
  { label: 'Morning', value: 'MORNING' },
  { label: 'Afternoon', value: 'AFTERNOON' },
  { label: 'Night', value: 'NIGHT' },
];

const roleColors: Record<string, string> = {
  PICKER: 'bg-blue-100 text-blue-800',
  PACKER: 'bg-green-100 text-green-800',
  RECEIVER: 'bg-purple-100 text-purple-800',
  PUTAWAY: 'bg-orange-100 text-orange-800',
  SUPERVISOR: 'bg-red-100 text-red-800',
};

const columns: ColumnDef<Worker>[] = [
  {
    accessorKey: 'name',
    header: 'Worker',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
          <Users className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-medium">{row.original.name}</div>
          <div className="text-xs text-muted-foreground">{row.original.employee_id}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'role',
    header: 'Role',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${roleColors[row.original.role]}`}>
        {row.original.role}
      </span>
    ),
  },
  {
    accessorKey: 'shift',
    header: 'Shift',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">{row.original.shift}</span>
      </div>
    ),
  },
  {
    accessorKey: 'tasks_completed',
    header: 'Tasks',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Package className="h-4 w-4 text-muted-foreground" />
        <span className="font-mono">{row.original.tasks_completed}</span>
      </div>
    ),
  },
  {
    accessorKey: 'avg_time_per_task',
    header: 'Avg Time',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Timer className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">{row.original.avg_time_per_task}s</span>
      </div>
    ),
  },
  {
    accessorKey: 'performance_score',
    header: 'Performance',
    cell: ({ row }) => {
      const score = row.original.performance_score;
      const color = score >= 90 ? 'text-green-600' : score >= 70 ? 'text-yellow-600' : 'text-red-600';
      return (
        <div className="flex items-center gap-2">
          <Award className={`h-4 w-4 ${color}`} />
          <span className={`font-medium ${color}`}>{score}%</span>
        </div>
      );
    },
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

const initialFormState: NewWorkerForm = {
  employee_id: '',
  name: '',
  role: 'PICKER',
  shift: 'MORNING',
  current_zone: '',
};

export default function LaborPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newWorker, setNewWorker] = useState<NewWorkerForm>(initialFormState);

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['wms-labor', page, pageSize],
    queryFn: () => laborApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-labor-stats'],
    queryFn: laborApi.getStats,
  });

  const createMutation = useMutation({
    mutationFn: laborApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-labor'] });
      queryClient.invalidateQueries({ queryKey: ['wms-labor-stats'] });
      toast.success('Worker added successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add worker');
    },
  });

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setNewWorker(initialFormState);
  };

  const handleSubmit = () => {
    if (!newWorker.employee_id.trim()) {
      toast.error('Employee ID is required');
      return;
    }
    if (!newWorker.name.trim()) {
      toast.error('Worker name is required');
      return;
    }

    const workerData = {
      employee_id: newWorker.employee_id.trim(),
      name: newWorker.name.trim(),
      role: newWorker.role,
      shift: newWorker.shift,
      current_zone: newWorker.current_zone.trim() || undefined,
    };

    createMutation.mutate(workerData);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Labor Management"
        description="Track warehouse workforce productivity and assignments"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Worker
          </Button>
        }
      />

      {/* Add Worker Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add New Worker</DialogTitle>
            <DialogDescription>
              Add a new worker to the warehouse labor pool.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="employee_id">Employee ID *</Label>
                <Input
                  id="employee_id"
                  placeholder="e.g., EMP001"
                  value={newWorker.employee_id}
                  onChange={(e) =>
                    setNewWorker({ ...newWorker, employee_id: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  placeholder="Worker name"
                  value={newWorker.name}
                  onChange={(e) =>
                    setNewWorker({ ...newWorker, name: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="role">Role *</Label>
                <Select
                  value={newWorker.role}
                  onValueChange={(value: 'PICKER' | 'PACKER' | 'RECEIVER' | 'PUTAWAY' | 'SUPERVISOR') =>
                    setNewWorker({ ...newWorker, role: value })
                  }
                >
                  <SelectTrigger id="role">
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    {roleOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="shift">Shift *</Label>
                <Select
                  value={newWorker.shift}
                  onValueChange={(value: 'MORNING' | 'AFTERNOON' | 'NIGHT') =>
                    setNewWorker({ ...newWorker, shift: value })
                  }
                >
                  <SelectTrigger id="shift">
                    <SelectValue placeholder="Select shift" />
                  </SelectTrigger>
                  <SelectContent>
                    {shiftOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="current_zone">Current Zone (Optional)</Label>
              <Input
                id="current_zone"
                placeholder="e.g., Zone A, Receiving Bay"
                value={newWorker.current_zone}
                onChange={(e) =>
                  setNewWorker({ ...newWorker, current_zone: e.target.value })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleDialogClose}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {createMutation.isPending ? 'Adding...' : 'Add Worker'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Workers</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_workers || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Now</CardTitle>
            <Clock className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.active_now || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Productivity</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.avg_productivity || 0}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tasks Today</CardTitle>
            <Package className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.tasks_completed_today || 0}</div>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="name"
        searchPlaceholder="Search workers..."
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
