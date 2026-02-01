'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { toast } from 'sonner';
import { MoreHorizontal, Plus, Eye, AlertTriangle, Clock, UserCog, Loader2 } from 'lucide-react';
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
import { Textarea } from '@/components/ui/textarea';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { escalationsApi } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface Escalation {
  id: string;
  escalation_number: string;
  type: 'SERVICE' | 'BILLING' | 'DELIVERY' | 'QUALITY' | 'OTHER';
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  level: number;
  source_type: string;
  source_id?: string;
  customer_id?: string;
  customer?: { name: string; phone: string };
  subject: string;
  description?: string;
  status: 'OPEN' | 'ASSIGNED' | 'IN_PROGRESS' | 'PENDING' | 'RESOLVED' | 'CLOSED';
  assigned_to_id?: string;
  assigned_to?: { full_name: string };
  sla_breach_at?: string;
  resolved_at?: string;
  created_at: string;
}

interface EscalationFormData {
  type: 'SERVICE' | 'BILLING' | 'DELIVERY' | 'QUALITY' | 'OTHER';
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  subject: string;
  description: string;
  customer_phone: string;
}

const initialFormData: EscalationFormData = {
  type: 'SERVICE',
  priority: 'MEDIUM',
  subject: '',
  description: '',
  customer_phone: '',
};

const priorityColors: Record<string, string> = {
  LOW: 'bg-gray-100 text-gray-800',
  MEDIUM: 'bg-blue-100 text-blue-800',
  HIGH: 'bg-orange-100 text-orange-800',
  CRITICAL: 'bg-red-100 text-red-800',
};

const typeLabels: Record<string, string> = {
  SERVICE: 'Service Issue',
  BILLING: 'Billing Issue',
  DELIVERY: 'Delivery Issue',
  QUALITY: 'Quality Issue',
  OTHER: 'Other',
};

const columns: ColumnDef<Escalation>[] = [
  {
    accessorKey: 'escalation_number',
    header: 'Escalation #',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <AlertTriangle className={`h-4 w-4 ${
          row.original.priority === 'CRITICAL' ? 'text-red-600' :
          row.original.priority === 'HIGH' ? 'text-orange-600' :
          'text-muted-foreground'
        }`} />
        <div>
          <div className="font-medium">{row.original.escalation_number}</div>
          <div className="text-xs text-muted-foreground">L{row.original.level}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'subject',
    header: 'Subject',
    cell: ({ row }) => (
      <div>
        <div className="text-sm line-clamp-1">{row.original.subject}</div>
        <div className="text-xs text-muted-foreground">
          {typeLabels[row.original.type]}
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'customer',
    header: 'Customer',
    cell: ({ row }) => (
      <div className="text-sm">
        <div>{row.original.customer?.name || 'N/A'}</div>
        <div className="text-muted-foreground">{row.original.customer?.phone}</div>
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
    accessorKey: 'assigned_to',
    header: 'Assigned To',
    cell: ({ row }) => (
      <div className="flex items-center gap-1 text-sm">
        <UserCog className="h-3 w-3 text-muted-foreground" />
        {row.original.assigned_to?.full_name || 'Unassigned'}
      </div>
    ),
  },
  {
    accessorKey: 'sla',
    header: 'SLA',
    cell: ({ row }) => {
      const slaBreachAt = row.original.sla_breach_at ? new Date(row.original.sla_breach_at) : null;
      const isBreached = slaBreachAt && slaBreachAt < new Date();
      return (
        <div className={`flex items-center gap-1 text-sm ${isBreached ? 'text-red-600' : ''}`}>
          <Clock className="h-3 w-3" />
          {slaBreachAt ? (
            isBreached ? 'Breached' : formatDate(row.original.sla_breach_at!)
          ) : '-'}
        </div>
      );
    },
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
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
          <DropdownMenuItem onClick={() => toast.success(`Viewing escalation ${row.original.escalation_number}`)}>
            <Eye className="mr-2 h-4 w-4" />
            View Details
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];

export default function EscalationsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState<EscalationFormData>(initialFormData);

  const { data, isLoading } = useQuery({
    queryKey: ['escalations', page, pageSize],
    queryFn: () => escalationsApi.list({ page: page + 1, size: pageSize }),
  });

  const createMutation = useMutation({
    mutationFn: escalationsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['escalations'] });
      toast.success('Escalation created successfully');
      setIsDialogOpen(false);
      setFormData(initialFormData);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create escalation');
    },
  });

  const handleSubmit = () => {
    if (!formData.subject.trim()) {
      toast.error('Subject is required');
      return;
    }

    createMutation.mutate({
      type: formData.type,
      priority: formData.priority,
      subject: formData.subject,
      description: formData.description || undefined,
      source_type: 'MANUAL',
    } as Partial<Escalation>);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Escalations"
        description="Manage escalated issues and SLA tracking"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Escalation
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="escalation_number"
        searchPlaceholder="Search escalations..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Create Escalation Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Escalation</DialogTitle>
            <DialogDescription>
              Create a new escalation for an issue that needs attention
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="type">Type</Label>
                <Select
                  value={formData.type}
                  onValueChange={(value: EscalationFormData['type']) =>
                    setFormData({ ...formData, type: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(typeLabels).map(([key, label]) => (
                      <SelectItem key={key} value={key}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="priority">Priority</Label>
                <Select
                  value={formData.priority}
                  onValueChange={(value: EscalationFormData['priority']) =>
                    setFormData({ ...formData, priority: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select priority" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="LOW">Low</SelectItem>
                    <SelectItem value="MEDIUM">Medium</SelectItem>
                    <SelectItem value="HIGH">High</SelectItem>
                    <SelectItem value="CRITICAL">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="customer_phone">Customer Phone (Optional)</Label>
              <Input
                id="customer_phone"
                placeholder="+91 98765 43210"
                value={formData.customer_phone}
                onChange={(e) => setFormData({ ...formData, customer_phone: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="subject">Subject *</Label>
              <Input
                id="subject"
                placeholder="Brief description of the issue"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Detailed description of the escalation..."
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Escalation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
