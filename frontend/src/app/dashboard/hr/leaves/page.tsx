'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  Calendar,
  Clock,
  Check,
  X,
  Filter,
  MoreHorizontal,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { hrApi, LeaveRequest } from '@/lib/api';

const leaveTypes = [
  { value: 'CASUAL', label: 'Casual Leave' },
  { value: 'SICK', label: 'Sick Leave' },
  { value: 'EARNED', label: 'Earned Leave' },
  { value: 'MATERNITY', label: 'Maternity Leave' },
  { value: 'PATERNITY', label: 'Paternity Leave' },
  { value: 'COMPENSATORY', label: 'Compensatory Off' },
  { value: 'UNPAID', label: 'Unpaid Leave' },
];

const leaveStatuses = [
  { value: 'PENDING', label: 'Pending', variant: 'secondary' as const },
  { value: 'APPROVED', label: 'Approved', variant: 'default' as const },
  { value: 'REJECTED', label: 'Rejected', variant: 'destructive' as const },
  { value: 'CANCELLED', label: 'Cancelled', variant: 'outline' as const },
];

function getStatusBadge(status: string) {
  const config = leaveStatuses.find((s) => s.value === status);
  return (
    <Badge variant={config?.variant || 'outline'}>
      {config?.label || status}
    </Badge>
  );
}

function getLeaveTypeLabel(type: string) {
  return leaveTypes.find((t) => t.value === type)?.label || type;
}

export default function LeavesPage() {
  const [statusFilter, setStatusFilter] = useState<string>('PENDING');
  const [page, setPage] = useState(1);
  const [selectedLeave, setSelectedLeave] = useState<LeaveRequest | null>(null);
  const [actionType, setActionType] = useState<'APPROVE' | 'REJECT' | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const pageSize = 20;

  const queryClient = useQueryClient();

  const { data: leavesData, isLoading } = useQuery({
    queryKey: ['leave-requests', page, statusFilter],
    queryFn: () =>
      hrApi.leave.listRequests({
        page,
        size: pageSize,
        status: statusFilter || undefined,
      }),
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, action, reason }: { id: string; action: 'APPROVE' | 'REJECT'; reason?: string }) =>
      hrApi.leave.approve(id, action, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leave-requests'] });
      queryClient.invalidateQueries({ queryKey: ['hr-dashboard'] });
      setSelectedLeave(null);
      setActionType(null);
      setRejectionReason('');
      toast.success(actionType === 'APPROVE' ? 'Leave approved' : 'Leave rejected');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Error processing leave request');
    },
  });

  const handleAction = () => {
    if (!selectedLeave || !actionType) return;
    approveMutation.mutate({
      id: selectedLeave.id,
      action: actionType,
      reason: actionType === 'REJECT' ? rejectionReason : undefined,
    });
  };

  const requests = leavesData?.items || [];
  const totalPages = leavesData?.pages || 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Leave Management</h1>
          <p className="text-muted-foreground">
            Review and manage leave requests
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <Select
              value={statusFilter || 'all'}
              onValueChange={(value) => {
                setStatusFilter(value === 'all' ? '' : value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                {leaveStatuses.map((status) => (
                  <SelectItem key={status.value} value={status.value}>
                    {status.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Leave Requests Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead>Leave Type</TableHead>
                <TableHead>From</TableHead>
                <TableHead>To</TableHead>
                <TableHead>Days</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-[80px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 8 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-24" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : requests.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <Calendar className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="font-medium">No leave requests</h3>
                    <p className="text-sm text-muted-foreground">
                      {statusFilter === 'PENDING' ? 'No pending leave requests' : 'No leave requests found'}
                    </p>
                  </TableCell>
                </TableRow>
              ) : (
                requests.map((leave: LeaveRequest) => (
                  <TableRow key={leave.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{leave.employee_name}</div>
                        <div className="text-sm text-muted-foreground">{leave.employee_code}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{getLeaveTypeLabel(leave.leave_type)}</Badge>
                    </TableCell>
                    <TableCell>{leave.from_date ? format(new Date(leave.from_date), 'dd MMM yyyy') : '-'}</TableCell>
                    <TableCell>{leave.to_date ? format(new Date(leave.to_date), 'dd MMM yyyy') : '-'}</TableCell>
                    <TableCell>
                      {leave.days} {leave.is_half_day && <span className="text-xs text-muted-foreground">(Half)</span>}
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate">
                      {leave.reason || <span className="text-muted-foreground">-</span>}
                    </TableCell>
                    <TableCell>{getStatusBadge(leave.status)}</TableCell>
                    <TableCell>
                      {leave.status === 'PENDING' ? (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => { setSelectedLeave(leave); setActionType('APPROVE'); }}>
                              <Check className="mr-2 h-4 w-4 text-green-600" />
                              Approve
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => { setSelectedLeave(leave); setActionType('REJECT'); }}>
                              <X className="mr-2 h-4 w-4 text-red-600" />
                              Reject
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Approval Dialog */}
      <Dialog open={!!actionType} onOpenChange={(open) => { if (!open) { setActionType(null); setSelectedLeave(null); setRejectionReason(''); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{actionType === 'APPROVE' ? 'Approve Leave' : 'Reject Leave'}</DialogTitle>
            <DialogDescription>
              {actionType === 'APPROVE'
                ? 'Are you sure you want to approve this leave request?'
                : 'Please provide a reason for rejection'}
            </DialogDescription>
          </DialogHeader>
          {selectedLeave && (
            <div className="py-4">
              <div className="grid gap-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Employee:</span>
                  <span className="font-medium">{selectedLeave.employee_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Leave Type:</span>
                  <span>{getLeaveTypeLabel(selectedLeave.leave_type)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Duration:</span>
                  <span>
                    {selectedLeave.from_date && selectedLeave.to_date
                      ? `${format(new Date(selectedLeave.from_date), 'dd MMM')} - ${format(new Date(selectedLeave.to_date), 'dd MMM yyyy')} (${selectedLeave.days} days)`
                      : '-'}
                  </span>
                </div>
              </div>
              {actionType === 'REJECT' && (
                <div className="mt-4 grid gap-2">
                  <Label>Rejection Reason</Label>
                  <Textarea
                    placeholder="Enter reason for rejection..."
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                  />
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => { setActionType(null); setSelectedLeave(null); }}>
              Cancel
            </Button>
            <Button
              variant={actionType === 'REJECT' ? 'destructive' : 'default'}
              onClick={handleAction}
              disabled={approveMutation.isPending || (actionType === 'REJECT' && !rejectionReason)}
            >
              {approveMutation.isPending ? 'Processing...' : actionType === 'APPROVE' ? 'Approve' : 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
