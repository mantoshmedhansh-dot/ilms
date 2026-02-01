'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader, StatusBadge } from '@/components/common';
import { partnersApi, PartnerCommission } from '@/lib/api';
import { Wallet, CheckCircle, Clock, IndianRupee, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { format } from 'date-fns';
import { toast } from 'sonner';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(value);
};

const statusOptions = [
  { value: 'all', label: 'All Statuses' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'PAID', label: 'Paid' },
];

export default function CommissionsPage() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [partnerId, setPartnerId] = useState('');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || 'all');

  // First, get list of partners
  const { data: partnersData } = useQuery({
    queryKey: ['partners-list'],
    queryFn: () => partnersApi.list({ size: 100, status: 'ACTIVE' }),
  });

  // Get commissions for selected partner
  const { data: commissionsData, isLoading } = useQuery({
    queryKey: ['partner-commissions', partnerId, statusFilter],
    queryFn: () =>
      partnersApi.getCommissions(partnerId, {
        size: 50,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      }),
    enabled: !!partnerId,
  });

  const approveCommissionMutation = useMutation({
    mutationFn: (commissionId: string) => partnersApi.approveCommission(commissionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['partner-commissions'] });
      toast.success('Commission approved successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to approve commission');
    },
  });

  const pendingCount = commissionsData?.items?.filter((c: PartnerCommission) => c.status === 'PENDING').length ?? 0;
  const totalPending = commissionsData?.items
    ?.filter((c: PartnerCommission) => c.status === 'PENDING')
    .reduce((sum: number, c: PartnerCommission) => sum + c.commission_amount, 0) ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Partner Commissions"
        description="View and approve partner commissions"
      />

      {/* Stats */}
      {partnerId && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending Approval</CardTitle>
              <Clock className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{pendingCount}</div>
              <p className="text-xs text-muted-foreground">
                {formatCurrency(totalPending)} total
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Commissions</CardTitle>
              <Wallet className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{commissionsData?.items?.length ?? 0}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Search Commissions</CardTitle>
          <CardDescription>Select a partner to view their commission history</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[250px]">
              <Select value={partnerId} onValueChange={setPartnerId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a partner..." />
                </SelectTrigger>
                <SelectContent>
                  {partnersData?.items?.map((partner) => (
                    <SelectItem key={partner.id} value={partner.id}>
                      {partner.full_name} ({partner.partner_code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
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
          </div>
        </CardContent>
      </Card>

      {/* Commissions Table */}
      {partnerId ? (
        <Card>
          <CardHeader>
            <CardTitle>Commission History</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : commissionsData?.items && commissionsData.items.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Order</TableHead>
                    <TableHead>Order Amount</TableHead>
                    <TableHead>Rate</TableHead>
                    <TableHead>Commission</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {commissionsData.items.map((commission: PartnerCommission) => (
                    <TableRow key={commission.id}>
                      <TableCell className="font-mono text-sm">
                        {commission.order_id.substring(0, 8)}...
                      </TableCell>
                      <TableCell>{formatCurrency(commission.order_amount)}</TableCell>
                      <TableCell>{commission.commission_rate}%</TableCell>
                      <TableCell className="font-medium">
                        {formatCurrency(commission.commission_amount)}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={commission.status} />
                      </TableCell>
                      <TableCell>
                        {format(new Date(commission.created_at), 'MMM d, yyyy')}
                      </TableCell>
                      <TableCell>
                        {commission.status === 'PENDING' && (
                          <Button
                            size="sm"
                            onClick={() => approveCommissionMutation.mutate(commission.id)}
                            disabled={approveCommissionMutation.isPending}
                          >
                            <CheckCircle className="mr-1 h-3 w-3" />
                            Approve
                          </Button>
                        )}
                        {commission.status === 'APPROVED' && (
                          <span className="text-xs text-muted-foreground">
                            Approved {commission.approved_at && format(new Date(commission.approved_at), 'MMM d')}
                          </span>
                        )}
                        {commission.status === 'PAID' && (
                          <span className="text-xs text-green-600">
                            Paid {commission.paid_at && format(new Date(commission.paid_at), 'MMM d')}
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-12">
                <Wallet className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <h3 className="mt-4 text-lg font-medium">No Commissions Found</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {statusFilter !== 'all'
                    ? `No ${statusFilter.toLowerCase()} commissions for this partner.`
                    : 'This partner has no commission records yet.'}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Search className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium">Select a Partner</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Choose a partner from the dropdown to view their commissions.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
