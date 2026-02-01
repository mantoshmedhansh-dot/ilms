'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { toast } from 'sonner';
import {
  MoreHorizontal, Plus, Shield, Clock, CheckCircle, XCircle,
  Loader2, FileText, AlertTriangle, Calendar, Package
} from 'lucide-react';
import { format } from 'date-fns';
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatDate } from '@/lib/utils';

interface WarrantyClaim {
  id: string;
  claim_number: string;
  installation_id?: string;
  installation?: {
    serial_number: string;
    product_name: string;
    customer_name: string;
    customer_phone: string;
  };
  customer_id?: string;
  customer?: { name: string; phone: string };
  product_id?: string;
  product?: { name: string; sku: string };
  serial_number?: string;
  claim_type: 'REPAIR' | 'REPLACEMENT' | 'REFUND';
  issue_description: string;
  status: 'PENDING' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED' | 'IN_PROGRESS' | 'COMPLETED' | 'CLOSED';
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  warranty_end_date?: string;
  is_within_warranty: boolean;
  resolution?: string;
  technician_notes?: string;
  approved_by_id?: string;
  approved_at?: string;
  completed_at?: string;
  created_at: string;
}

const warrantyClaimsApi = {
  list: async (params?: { page?: number; size?: number; status?: string; claim_type?: string }) => {
    try {
      const { data } = await apiClient.get('/service/warranty-claims', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  create: async (claim: Partial<WarrantyClaim>) => {
    const { data } = await apiClient.post('/service/warranty-claims', claim);
    return data;
  },
  update: async (id: string, claim: Partial<WarrantyClaim>) => {
    const { data } = await apiClient.put(`/service/warranty-claims/${id}`, claim);
    return data;
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post(`/service/warranty-claims/${id}/approve`);
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/service/warranty-claims/${id}/reject`, { reason });
    return data;
  },
  complete: async (id: string, resolution: string) => {
    const { data } = await apiClient.post(`/service/warranty-claims/${id}/complete`, { resolution });
    return data;
  },
  getStats: async () => {
    try {
      const { data } = await apiClient.get('/service/warranty-claims/stats');
      return data;
    } catch {
      return { pending: 0, approved: 0, rejected: 0, completed: 0 };
    }
  },
};

interface ClaimFormData {
  serial_number: string;
  claim_type: 'REPAIR' | 'REPLACEMENT' | 'REFUND';
  issue_description: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

const initialFormData: ClaimFormData = {
  serial_number: '',
  claim_type: 'REPAIR',
  issue_description: '',
  priority: 'MEDIUM',
};

const statusColors: Record<string, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  UNDER_REVIEW: 'bg-blue-100 text-blue-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
  IN_PROGRESS: 'bg-purple-100 text-purple-800',
  COMPLETED: 'bg-gray-100 text-gray-800',
  CLOSED: 'bg-gray-100 text-gray-800',
};

const priorityColors: Record<string, string> = {
  LOW: 'bg-gray-100 text-gray-800',
  MEDIUM: 'bg-blue-100 text-blue-800',
  HIGH: 'bg-orange-100 text-orange-800',
  CRITICAL: 'bg-red-100 text-red-800',
};

const claimTypeIcons: Record<string, React.ReactNode> = {
  REPAIR: <Package className="h-4 w-4" />,
  REPLACEMENT: <Shield className="h-4 w-4" />,
  REFUND: <FileText className="h-4 w-4" />,
};

export default function WarrantyClaimsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isRejectDialogOpen, setIsRejectDialogOpen] = useState(false);
  const [isCompleteDialogOpen, setIsCompleteDialogOpen] = useState(false);
  const [selectedClaim, setSelectedClaim] = useState<WarrantyClaim | null>(null);
  const [formData, setFormData] = useState<ClaimFormData>(initialFormData);
  const [rejectReason, setRejectReason] = useState('');
  const [resolution, setResolution] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['warranty-claims', page, pageSize, statusFilter],
    queryFn: () => warrantyClaimsApi.list({
      page: page + 1,
      size: pageSize,
      status: statusFilter !== 'all' ? statusFilter : undefined,
    }),
  });

  const { data: stats } = useQuery({
    queryKey: ['warranty-claims-stats'],
    queryFn: warrantyClaimsApi.getStats,
  });

  const createMutation = useMutation({
    mutationFn: warrantyClaimsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warranty-claims'] });
      queryClient.invalidateQueries({ queryKey: ['warranty-claims-stats'] });
      toast.success('Warranty claim created');
      setIsDialogOpen(false);
      setFormData(initialFormData);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create claim');
    },
  });

  const approveMutation = useMutation({
    mutationFn: warrantyClaimsApi.approve,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warranty-claims'] });
      queryClient.invalidateQueries({ queryKey: ['warranty-claims-stats'] });
      toast.success('Claim approved');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to approve claim');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => warrantyClaimsApi.reject(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warranty-claims'] });
      queryClient.invalidateQueries({ queryKey: ['warranty-claims-stats'] });
      toast.success('Claim rejected');
      setIsRejectDialogOpen(false);
      setRejectReason('');
      setSelectedClaim(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to reject claim');
    },
  });

  const completeMutation = useMutation({
    mutationFn: ({ id, resolution }: { id: string; resolution: string }) => warrantyClaimsApi.complete(id, resolution),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warranty-claims'] });
      queryClient.invalidateQueries({ queryKey: ['warranty-claims-stats'] });
      toast.success('Claim completed');
      setIsCompleteDialogOpen(false);
      setResolution('');
      setSelectedClaim(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to complete claim');
    },
  });

  const handleSubmit = () => {
    if (!formData.serial_number || !formData.issue_description) {
      toast.error('Serial number and issue description are required');
      return;
    }
    createMutation.mutate(formData);
  };

  const columns: ColumnDef<WarrantyClaim>[] = [
    {
      accessorKey: 'claim_number',
      header: 'Claim #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Shield className={`h-4 w-4 ${row.original.is_within_warranty ? 'text-green-600' : 'text-red-600'}`} />
          <div>
            <div className="font-mono font-medium">{row.original.claim_number}</div>
            <div className="text-xs text-muted-foreground">
              {row.original.is_within_warranty ? 'In Warranty' : 'Out of Warranty'}
            </div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'product',
      header: 'Product / Serial',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">
            {row.original.installation?.product_name || row.original.product?.name || '-'}
          </div>
          <div className="text-xs text-muted-foreground font-mono">
            {row.original.serial_number || row.original.installation?.serial_number}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'customer',
      header: 'Customer',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">
            {row.original.installation?.customer_name || row.original.customer?.name || '-'}
          </div>
          <div className="text-xs text-muted-foreground">
            {row.original.installation?.customer_phone || row.original.customer?.phone}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'claim_type',
      header: 'Type',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          {claimTypeIcons[row.original.claim_type]}
          <span className="capitalize">{row.original.claim_type?.toLowerCase() ?? '-'}</span>
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
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[row.original.status] ?? 'bg-gray-100 text-gray-800'}`}>
          {row.original.status?.replace(/_/g, ' ') ?? '-'}
        </span>
      ),
    },
    {
      accessorKey: 'created_at',
      header: 'Created',
      cell: ({ row }) => formatDate(row.original.created_at),
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
            {row.original.status === 'PENDING' && (
              <>
                <DropdownMenuItem onClick={() => approveMutation.mutate(row.original.id)}>
                  <CheckCircle className="mr-2 h-4 w-4 text-green-600" />
                  Approve
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    setSelectedClaim(row.original);
                    setIsRejectDialogOpen(true);
                  }}
                >
                  <XCircle className="mr-2 h-4 w-4 text-red-600" />
                  Reject
                </DropdownMenuItem>
              </>
            )}
            {row.original.status === 'APPROVED' && (
              <DropdownMenuItem
                onClick={() => {
                  setSelectedClaim(row.original);
                  setIsCompleteDialogOpen(true);
                }}
              >
                <CheckCircle className="mr-2 h-4 w-4" />
                Mark Complete
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const claims = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Warranty Claims"
        description="Manage product warranty claims and resolutions"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Claim
          </Button>
        }
      />

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-yellow-100 rounded-lg">
                <Clock className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Pending</p>
                <p className="text-2xl font-bold">{stats?.pending || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-lg">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Approved</p>
                <p className="text-2xl font-bold">{stats?.approved || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-red-100 rounded-lg">
                <XCircle className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Rejected</p>
                <p className="text-2xl font-bold">{stats?.rejected || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Shield className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Completed</p>
                <p className="text-2xl font-bold">{stats?.completed || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="UNDER_REVIEW">Under Review</SelectItem>
            <SelectItem value="APPROVED">Approved</SelectItem>
            <SelectItem value="REJECTED">Rejected</SelectItem>
            <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
            <SelectItem value="COMPLETED">Completed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={claims}
        searchKey="claim_number"
        searchPlaceholder="Search claims..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Create Claim Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Warranty Claim</DialogTitle>
            <DialogDescription>
              Create a new warranty claim for a product
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Serial Number / Installation ID *</Label>
              <Input
                placeholder="Enter serial number"
                value={formData.serial_number}
                onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Claim Type</Label>
                <Select
                  value={formData.claim_type}
                  onValueChange={(v: ClaimFormData['claim_type']) => setFormData({ ...formData, claim_type: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="REPAIR">Repair</SelectItem>
                    <SelectItem value="REPLACEMENT">Replacement</SelectItem>
                    <SelectItem value="REFUND">Refund</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Priority</Label>
                <Select
                  value={formData.priority}
                  onValueChange={(v: ClaimFormData['priority']) => setFormData({ ...formData, priority: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
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
              <Label>Issue Description *</Label>
              <Textarea
                placeholder="Describe the issue in detail..."
                rows={4}
                value={formData.issue_description}
                onChange={(e) => setFormData({ ...formData, issue_description: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Claim
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={isRejectDialogOpen} onOpenChange={setIsRejectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Claim</DialogTitle>
            <DialogDescription>
              Provide a reason for rejecting this warranty claim
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label>Rejection Reason *</Label>
            <Textarea
              placeholder="Enter reason for rejection..."
              rows={4}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRejectDialogOpen(false)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => selectedClaim && rejectMutation.mutate({ id: selectedClaim.id, reason: rejectReason })}
              disabled={rejectMutation.isPending || !rejectReason.trim()}
            >
              {rejectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Reject Claim
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Complete Dialog */}
      <Dialog open={isCompleteDialogOpen} onOpenChange={setIsCompleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Complete Claim</DialogTitle>
            <DialogDescription>
              Mark this warranty claim as completed
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label>Resolution Details *</Label>
            <Textarea
              placeholder="Describe how the issue was resolved..."
              rows={4}
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCompleteDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={() => selectedClaim && completeMutation.mutate({ id: selectedClaim.id, resolution })}
              disabled={completeMutation.isPending || !resolution.trim()}
            >
              {completeMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Complete Claim
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
