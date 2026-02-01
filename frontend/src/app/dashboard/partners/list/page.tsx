'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Eye, CheckCircle, XCircle, Ban, UserCheck, Pencil, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { format } from 'date-fns';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { partnersApi, CommunityPartner } from '@/lib/api';
import { toast } from 'sonner';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
};

const statusOptions = [
  { value: 'all', label: 'All Statuses' },
  { value: 'PENDING_KYC', label: 'Pending KYC' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'SUSPENDED', label: 'Suspended' },
];

const kycStatusOptions = [
  { value: 'all', label: 'All KYC Statuses' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'SUBMITTED', label: 'Submitted' },
  { value: 'VERIFIED', label: 'Verified' },
  { value: 'REJECTED', label: 'Rejected' },
];

export default function PartnersListPage() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || 'all');
  const [kycStatusFilter, setKycStatusFilter] = useState(searchParams.get('kyc_status') || 'all');
  const [search, setSearch] = useState('');

  // KYC Verification Dialog
  const [kycDialog, setKycDialog] = useState<{
    open: boolean;
    partner: CommunityPartner | null;
    action: 'approve' | 'reject';
    notes: string;
  }>({
    open: false,
    partner: null,
    action: 'approve',
    notes: '',
  });

  // Suspend Dialog
  const [suspendDialog, setSuspendDialog] = useState<{
    open: boolean;
    partner: CommunityPartner | null;
    reason: string;
  }>({
    open: false,
    partner: null,
    reason: '',
  });

  // Delete Dialog
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean;
    partner: CommunityPartner | null;
  }>({
    open: false,
    partner: null,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['partners', page, pageSize, statusFilter, kycStatusFilter, search],
    queryFn: () =>
      partnersApi.list({
        page: page + 1,
        size: pageSize,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        kyc_status: kycStatusFilter !== 'all' ? kycStatusFilter : undefined,
        search: search || undefined,
      }),
  });

  const verifyKycMutation = useMutation({
    mutationFn: ({ partnerId, status, notes }: { partnerId: string; status: 'VERIFIED' | 'REJECTED'; notes?: string }) =>
      partnersApi.verifyKyc(partnerId, { status, notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['partners'] });
      toast.success('KYC verification updated');
      setKycDialog({ open: false, partner: null, action: 'approve', notes: '' });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update KYC status');
    },
  });

  const suspendMutation = useMutation({
    mutationFn: ({ partnerId, reason }: { partnerId: string; reason: string }) =>
      partnersApi.suspend(partnerId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['partners'] });
      toast.success('Partner suspended');
      setSuspendDialog({ open: false, partner: null, reason: '' });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to suspend partner');
    },
  });

  const activateMutation = useMutation({
    mutationFn: (partnerId: string) => partnersApi.activate(partnerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['partners'] });
      toast.success('Partner activated');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to activate partner');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (partnerId: string) => partnersApi.delete(partnerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['partners'] });
      toast.success('Partner deleted successfully');
      setDeleteDialog({ open: false, partner: null });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete partner');
    },
  });

  const columns: ColumnDef<CommunityPartner>[] = [
    {
      accessorKey: 'partner_code',
      header: 'Partner Code',
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.original.partner_code}</span>
      ),
    },
    {
      accessorKey: 'full_name',
      header: 'Name',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.full_name}</div>
          <div className="text-sm text-muted-foreground">{row.original.phone}</div>
        </div>
      ),
    },
    {
      accessorKey: 'city',
      header: 'Location',
      cell: ({ row }) => (
        <div className="text-sm">
          {row.original.city && row.original.state
            ? `${row.original.city}, ${row.original.state}`
            : row.original.state || '-'}
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'kyc_status',
      header: 'KYC Status',
      cell: ({ row }) => <StatusBadge status={row.original.kyc_status} />,
    },
    {
      accessorKey: 'tier',
      header: 'Tier',
      cell: ({ row }) => (
        <span className="text-sm">{row.original.tier?.name || '-'}</span>
      ),
    },
    {
      accessorKey: 'total_sales_count',
      header: 'Orders',
      cell: ({ row }) => row.original.total_sales_count || 0,
    },
    {
      accessorKey: 'total_sales_value',
      header: 'Sales',
      cell: ({ row }) => formatCurrency(row.original.total_sales_value || 0),
    },
    {
      accessorKey: 'created_at',
      header: 'Joined',
      cell: ({ row }) => format(new Date(row.original.created_at), 'MMM d, yyyy'),
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
            <DropdownMenuItem asChild>
              <Link href={`/dashboard/partners/${row.original.id}`}>
                <Eye className="mr-2 h-4 w-4" />
                View Details
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href={`/dashboard/partners/${row.original.id}/edit`}>
                <Pencil className="mr-2 h-4 w-4" />
                Edit Partner
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => setDeleteDialog({
                open: true,
                partner: row.original,
              })}
              className="text-red-600"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Partner
            </DropdownMenuItem>

            {row.original.kyc_status === 'SUBMITTED' && (
              <>
                <DropdownMenuItem
                  onClick={() => setKycDialog({
                    open: true,
                    partner: row.original,
                    action: 'approve',
                    notes: '',
                  })}
                >
                  <CheckCircle className="mr-2 h-4 w-4 text-green-600" />
                  Approve KYC
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => setKycDialog({
                    open: true,
                    partner: row.original,
                    action: 'reject',
                    notes: '',
                  })}
                >
                  <XCircle className="mr-2 h-4 w-4 text-red-600" />
                  Reject KYC
                </DropdownMenuItem>
              </>
            )}

            {row.original.status === 'ACTIVE' && (
              <DropdownMenuItem
                onClick={() => setSuspendDialog({
                  open: true,
                  partner: row.original,
                  reason: '',
                })}
              >
                <Ban className="mr-2 h-4 w-4 text-red-600" />
                Suspend Partner
              </DropdownMenuItem>
            )}

            {row.original.status === 'SUSPENDED' && row.original.kyc_status === 'VERIFIED' && (
              <DropdownMenuItem
                onClick={() => activateMutation.mutate(row.original.id)}
              >
                <UserCheck className="mr-2 h-4 w-4 text-green-600" />
                Reactivate Partner
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="All Partners"
        description="Manage community partners and their KYC status"
      />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <Input
          placeholder="Search by name, phone, code..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-[250px]"
        />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {statusOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={kycStatusFilter} onValueChange={setKycStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="KYC Status" />
          </SelectTrigger>
          <SelectContent>
            {kycStatusOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="full_name"
        searchPlaceholder="Search partners..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.total_pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* KYC Verification Dialog */}
      <Dialog open={kycDialog.open} onOpenChange={(open) => setKycDialog({ ...kycDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {kycDialog.action === 'approve' ? 'Approve KYC' : 'Reject KYC'}
            </DialogTitle>
            <DialogDescription>
              {kycDialog.action === 'approve'
                ? `Approve KYC for ${kycDialog.partner?.full_name}? This will activate the partner.`
                : `Reject KYC for ${kycDialog.partner?.full_name}? Please provide a reason.`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Textarea
              placeholder={kycDialog.action === 'approve' ? 'Optional notes...' : 'Reason for rejection (required)'}
              value={kycDialog.notes}
              onChange={(e) => setKycDialog({ ...kycDialog, notes: e.target.value })}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setKycDialog({ ...kycDialog, open: false })}>
              Cancel
            </Button>
            <Button
              variant={kycDialog.action === 'approve' ? 'default' : 'destructive'}
              onClick={() => {
                if (kycDialog.partner) {
                  verifyKycMutation.mutate({
                    partnerId: kycDialog.partner.id,
                    status: kycDialog.action === 'approve' ? 'VERIFIED' : 'REJECTED',
                    notes: kycDialog.notes || undefined,
                  });
                }
              }}
              disabled={kycDialog.action === 'reject' && !kycDialog.notes}
            >
              {kycDialog.action === 'approve' ? 'Approve' : 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Suspend Dialog */}
      <Dialog open={suspendDialog.open} onOpenChange={(open) => setSuspendDialog({ ...suspendDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Suspend Partner</DialogTitle>
            <DialogDescription>
              Suspend {suspendDialog.partner?.full_name}? They will not be able to earn commissions until reactivated.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Textarea
              placeholder="Reason for suspension (required)"
              value={suspendDialog.reason}
              onChange={(e) => setSuspendDialog({ ...suspendDialog, reason: e.target.value })}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSuspendDialog({ ...suspendDialog, open: false })}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (suspendDialog.partner && suspendDialog.reason) {
                  suspendMutation.mutate({
                    partnerId: suspendDialog.partner.id,
                    reason: suspendDialog.reason,
                  });
                }
              }}
              disabled={!suspendDialog.reason}
            >
              Suspend Partner
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog.open} onOpenChange={(open) => setDeleteDialog({ ...deleteDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Partner</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {deleteDialog.partner?.full_name} ({deleteDialog.partner?.partner_code})?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialog({ ...deleteDialog, open: false })}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deleteDialog.partner) {
                  deleteMutation.mutate(deleteDialog.partner.id);
                }
              }}
            >
              Delete Partner
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
