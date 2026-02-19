'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, Play, Pause, CheckCircle, ClipboardList, Package, User, Clock, Printer } from 'lucide-react';
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
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatDate } from '@/lib/utils';

interface Picklist {
  id: string;
  picklist_number: string;
  warehouse_id: string;
  warehouse_name: string;
  picker_id?: string;
  picker_name?: string;
  status: 'PENDING' | 'ASSIGNED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
  total_orders: number;
  total_items: number;
  picked_items: number;
  total_quantity: number;
  picked_quantity: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  estimated_time_minutes?: number;
}

interface PicklistStats {
  total_picklists: number;
  pending: number;
  in_progress: number;
  completed_today: number;
  avg_pick_time_minutes: number;
}

const picklistsApi = {
  list: async (params?: { page?: number; size?: number; status?: string; warehouse_id?: string }) => {
    try {
      const { data } = await apiClient.get('/picklists', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<PicklistStats> => {
    try {
      const { data } = await apiClient.get('/picklists/stats');
      return data;
    } catch {
      return { total_picklists: 0, pending: 0, in_progress: 0, completed_today: 0, avg_pick_time_minutes: 0 };
    }
  },
  create: async (params: { warehouse_id: string; order_ids: string[]; priority?: string }) => {
    const { data } = await apiClient.post('/picklists', params);
    return data;
  },
  assign: async (id: string, pickerId: string) => {
    const { data } = await apiClient.post(`/picklists/${id}/assign`, { picker_id: pickerId });
    return data;
  },
  start: async (id: string) => {
    const { data } = await apiClient.post(`/picklists/${id}/start`);
    return data;
  },
  complete: async (id: string) => {
    const { data } = await apiClient.post(`/picklists/${id}/complete`);
    return data;
  },
};

const statusColors: Record<string, string> = {
  PENDING: 'bg-gray-100 text-gray-800',
  ASSIGNED: 'bg-blue-100 text-blue-800',
  IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
  COMPLETED: 'bg-green-100 text-green-800',
  CANCELLED: 'bg-red-100 text-red-800',
};

const priorityColors: Record<string, string> = {
  LOW: 'bg-gray-100 text-gray-600',
  NORMAL: 'bg-blue-100 text-blue-700',
  HIGH: 'bg-orange-100 text-orange-700',
  URGENT: 'bg-red-100 text-red-700',
};

// Separate component for actions cell to properly use hooks
function PicklistActionsCell({
  picklist,
  onView,
  onPrint
}: {
  picklist: Picklist;
  onView: (p: Picklist) => void;
  onPrint: (p: Picklist) => void;
}) {
  const queryClient = useQueryClient();

  const startMutation = useMutation({
    mutationFn: () => picklistsApi.start(picklist.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['picklists'] });
      queryClient.invalidateQueries({ queryKey: ['picklists-stats'] });
      toast.success('Picklist started');
    },
    onError: () => toast.error('Failed to start picklist'),
  });

  const completeMutation = useMutation({
    mutationFn: () => picklistsApi.complete(picklist.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['picklists'] });
      queryClient.invalidateQueries({ queryKey: ['picklists-stats'] });
      toast.success('Picklist completed');
    },
    onError: () => toast.error('Failed to complete picklist'),
  });

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
        <DropdownMenuItem onClick={() => onView(picklist)}>
          <Eye className="mr-2 h-4 w-4" />
          View Details
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onPrint(picklist)}>
          <Printer className="mr-2 h-4 w-4" />
          Print Picklist
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {picklist.status === 'ASSIGNED' && (
          <DropdownMenuItem onClick={() => startMutation.mutate()}>
            <Play className="mr-2 h-4 w-4" />
            Start Picking
          </DropdownMenuItem>
        )}
        {picklist.status === 'IN_PROGRESS' && (
          <DropdownMenuItem onClick={() => completeMutation.mutate()}>
            <CheckCircle className="mr-2 h-4 w-4" />
            Mark Complete
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

const createColumns = (
  onView: (p: Picklist) => void,
  onPrint: (p: Picklist) => void
): ColumnDef<Picklist>[] => [
  {
    accessorKey: 'picklist_number',
    header: 'Picklist #',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <ClipboardList className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.picklist_number}</div>
          <div className="text-sm text-muted-foreground">{row.original.warehouse_name}</div>
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
    accessorKey: 'picker_name',
    header: 'Picker',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <User className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">{row.original.picker_name || 'Unassigned'}</span>
      </div>
    ),
  },
  {
    accessorKey: 'orders_items',
    header: 'Orders / Items',
    cell: ({ row }) => (
      <div className="text-sm">
        <div>{row.original.total_orders} orders</div>
        <div className="text-muted-foreground">{row.original.total_items} items</div>
      </div>
    ),
  },
  {
    accessorKey: 'progress',
    header: 'Progress',
    cell: ({ row }) => {
      const progress = row.original.total_quantity > 0
        ? (row.original.picked_quantity / row.original.total_quantity) * 100
        : 0;
      return (
        <div className="space-y-1">
          <div className="text-sm font-medium">{progress.toFixed(0)}%</div>
          <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full ${progress === 100 ? 'bg-green-500' : 'bg-blue-500'}`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="text-xs text-muted-foreground">
            {row.original.picked_quantity} / {row.original.total_quantity} qty
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[row.original.status] ?? 'bg-gray-100 text-gray-800'}`}>
        {row.original.status?.replace(/_/g, ' ') ?? '-'}
      </span>
    ),
  },
  {
    accessorKey: 'time',
    header: 'Time',
    cell: ({ row }) => (
      <div className="text-sm">
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3 text-muted-foreground" />
          {row.original.estimated_time_minutes ? `${row.original.estimated_time_minutes} min` : '-'}
        </div>
        {row.original.started_at && (
          <div className="text-xs text-muted-foreground">
            Started: {formatDate(row.original.started_at)}
          </div>
        )}
      </div>
    ),
  },
  {
    id: 'actions',
    cell: ({ row }) => (
      <PicklistActionsCell
        picklist={row.original}
        onView={onView}
        onPrint={onPrint}
      />
    ),
  },
];

interface Warehouse {
  id: string;
  code: string;
  name: string;
}

interface CreatePicklistForm {
  warehouse_id: string;
  priority: string;
  picker_id?: string;
}

export default function PicklistsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [viewPicklist, setViewPicklist] = useState<Picklist | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [formData, setFormData] = useState<CreatePicklistForm>({
    warehouse_id: '',
    priority: 'NORMAL',
    picker_id: undefined,
  });

  const queryClient = useQueryClient();

  const handleView = (picklist: Picklist) => {
    setViewPicklist(picklist);
    setIsSheetOpen(true);
  };

  const handlePrint = (picklist: Picklist) => {
    toast.success(`Printing picklist ${picklist.picklist_number}`);
    window.print();
  };

  const columns = createColumns(handleView, handlePrint);

  const { data, isLoading } = useQuery({
    queryKey: ['picklists', page, pageSize, statusFilter],
    queryFn: () => picklistsApi.list({
      page: page + 1,
      size: pageSize,
      status: statusFilter !== 'all' ? statusFilter : undefined,
    }),
  });

  const { data: stats } = useQuery({
    queryKey: ['picklists-stats'],
    queryFn: picklistsApi.getStats,
  });

  const { data: warehouses } = useQuery({
    queryKey: ['warehouses-dropdown'],
    queryFn: async (): Promise<Warehouse[]> => {
      try {
        const { data } = await apiClient.get('/warehouses/dropdown');
        return data;
      } catch {
        return [];
      }
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: CreatePicklistForm) => picklistsApi.create({
      warehouse_id: data.warehouse_id,
      order_ids: [], // Auto-select pending orders
      priority: data.priority,
    }),
    onSuccess: async (data) => {
      toast.success('Picklist created successfully');
      if (formData.picker_id) {
        // Assign picker if selected
        await picklistsApi.assign(data.id, formData.picker_id);
      }
      setIsDialogOpen(false);
      setFormData({ warehouse_id: '', priority: 'NORMAL', picker_id: undefined });
      queryClient.invalidateQueries({ queryKey: ['picklists'] });
      queryClient.invalidateQueries({ queryKey: ['picklists-stats'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create picklist');
    },
  });

  const handleCreatePicklist = () => {
    if (!formData.warehouse_id) {
      toast.error('Please select a warehouse');
      return;
    }
    createMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Picklists"
        description="Manage order picking and warehouse fulfillment"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Picklist
          </Button>
        }
      />

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Picklist</DialogTitle>
            <DialogDescription>
              Create a new picklist for warehouse picking. Pending orders will be automatically assigned.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Warehouse *</label>
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
            <div className="space-y-2">
              <label className="text-sm font-medium">Priority</label>
              <Select
                value={formData.priority}
                onValueChange={(value) => setFormData({ ...formData, priority: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="LOW">Low</SelectItem>
                  <SelectItem value="NORMAL">Normal</SelectItem>
                  <SelectItem value="HIGH">High</SelectItem>
                  <SelectItem value="URGENT">Urgent</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreatePicklist} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Picklist'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Picklists</CardTitle>
            <ClipboardList className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_picklists || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <Pause className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">{stats?.pending || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Progress</CardTitle>
            <Play className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{stats?.in_progress || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed Today</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.completed_today || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Pick Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.avg_pick_time_minutes || 0}m</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="ASSIGNED">Assigned</SelectItem>
            <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
            <SelectItem value="COMPLETED">Completed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="picklist_number"
        searchPlaceholder="Search picklists..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Picklist Details Sheet */}
      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent className="sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>Picklist Details</SheetTitle>
            <SheetDescription>
              {viewPicklist?.picklist_number}
            </SheetDescription>
          </SheetHeader>
          {viewPicklist && (
            <div className="mt-6 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-muted-foreground">Warehouse</label>
                  <p className="font-medium">{viewPicklist.warehouse_name}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Picker</label>
                  <p className="font-medium">{viewPicklist.picker_name || 'Unassigned'}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Status</label>
                  <p><StatusBadge status={viewPicklist.status} /></p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Priority</label>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${priorityColors[viewPicklist.priority]}`}>
                    {viewPicklist.priority}
                  </span>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Total Orders</label>
                  <p className="font-medium">{viewPicklist.total_orders}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Total Items</label>
                  <p className="font-medium">{viewPicklist.total_items}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Progress</label>
                  <p className="font-medium">{viewPicklist.picked_quantity} / {viewPicklist.total_quantity} qty</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Est. Time</label>
                  <p className="font-medium">{viewPicklist.estimated_time_minutes ? `${viewPicklist.estimated_time_minutes} min` : '-'}</p>
                </div>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Created At</label>
                <p className="font-medium">{formatDate(viewPicklist.created_at)}</p>
              </div>
              {viewPicklist.started_at && (
                <div>
                  <label className="text-sm text-muted-foreground">Started At</label>
                  <p className="font-medium">{formatDate(viewPicklist.started_at)}</p>
                </div>
              )}
              {viewPicklist.completed_at && (
                <div>
                  <label className="text-sm text-muted-foreground">Completed At</label>
                  <p className="font-medium">{formatDate(viewPicklist.completed_at)}</p>
                </div>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
