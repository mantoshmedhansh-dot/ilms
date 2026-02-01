'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader, StatusBadge } from '@/components/common';
import { partnersApi, PartnerPayout } from '@/lib/api';
import { Banknote, CheckCircle, XCircle, Clock, Search } from 'lucide-react';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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

// Note: This page shows payouts across all partners.
// In a full implementation, you would have a separate endpoint to list all payouts.
// For now, we'll show a placeholder since the backend only supports per-partner payout listing.

export default function PayoutsPage() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [partnerId, setPartnerId] = useState('');
  const [processDialog, setProcessDialog] = useState<{
    open: boolean;
    payout: PartnerPayout | null;
    reference: string;
    success: boolean;
    failureReason: string;
  }>({
    open: false,
    payout: null,
    reference: '',
    success: true,
    failureReason: '',
  });

  // Get list of partners
  const { data: partnersData } = useQuery({
    queryKey: ['partners-list'],
    queryFn: () => partnersApi.list({ size: 100, status: 'ACTIVE' }),
  });

  // Get analytics for pending payouts count
  const { data: analytics } = useQuery({
    queryKey: ['partner-analytics'],
    queryFn: () => partnersApi.getAnalytics(),
  });

  const processPayoutMutation = useMutation({
    mutationFn: ({ payoutId, reference, success, failureReason }: { payoutId: string; reference?: string; success: boolean; failureReason?: string }) =>
      partnersApi.processPayout(payoutId, { reference, success, failure_reason: failureReason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['partner-analytics'] });
      toast.success('Payout processed successfully');
      setProcessDialog({ open: false, payout: null, reference: '', success: true, failureReason: '' });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to process payout');
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Partner Payouts"
        description="Process payout requests from community partners"
      />

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Payouts</CardTitle>
            <Clock className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(analytics?.pending_payouts ?? 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Awaiting bank transfer
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Paid</CardTitle>
            <Banknote className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(analytics?.total_commissions_paid ?? 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              All-time payouts processed
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Partners</CardTitle>
            <CheckCircle className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {analytics?.active_partners ?? 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Eligible for payouts
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Instructions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Payout Processing Workflow</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-3">
          <p>To process partner payouts:</p>
          <ol className="list-decimal list-inside space-y-2 ml-2">
            <li>Partners request payouts from their app when they have approved commissions</li>
            <li>Payout requests appear here with &quot;PENDING&quot; status</li>
            <li>Verify the partner&apos;s bank details in their profile</li>
            <li>Process the bank transfer manually (NEFT/IMPS/UPI)</li>
            <li>Mark the payout as &quot;Completed&quot; with the transaction reference</li>
            <li>If transfer fails, mark as &quot;Failed&quot; with reason - funds return to partner balance</li>
          </ol>
        </CardContent>
      </Card>

      {/* Partner Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">View Partner Payouts</CardTitle>
          <CardDescription>
            Select a partner to view their payout history. A full payout queue view will be added soon.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[250px]">
              <Select value={partnerId} onValueChange={setPartnerId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a partner to view payouts..." />
                </SelectTrigger>
                <SelectContent>
                  {partnersData?.items?.map((partner) => (
                    <SelectItem key={partner.id} value={partner.id}>
                      {partner.full_name} ({partner.partner_code}) - Balance: {formatCurrency(partner.wallet_balance)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {!partnerId && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Search className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium">Select a Partner</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Choose a partner from the dropdown to view and process their payouts.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Process Dialog */}
      <Dialog open={processDialog.open} onOpenChange={(open) => setProcessDialog({ ...processDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Process Payout</DialogTitle>
            <DialogDescription>
              Mark this payout as completed or failed.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {processDialog.payout && (
              <div className="p-4 bg-muted rounded-lg">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Amount</span>
                  <span className="font-bold">{formatCurrency(processDialog.payout.amount)}</span>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <Select
                value={processDialog.success ? 'success' : 'failed'}
                onValueChange={(v) => setProcessDialog({ ...processDialog, success: v === 'success' })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="success">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      Successful
                    </div>
                  </SelectItem>
                  <SelectItem value="failed">
                    <div className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-red-500" />
                      Failed
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {processDialog.success ? (
              <div className="space-y-2">
                <label className="text-sm font-medium">Bank Transfer Reference</label>
                <Input
                  placeholder="e.g., IMPS/UTR123456789"
                  value={processDialog.reference}
                  onChange={(e) => setProcessDialog({ ...processDialog, reference: e.target.value })}
                />
              </div>
            ) : (
              <div className="space-y-2">
                <label className="text-sm font-medium">Failure Reason</label>
                <Input
                  placeholder="e.g., Invalid bank account"
                  value={processDialog.failureReason}
                  onChange={(e) => setProcessDialog({ ...processDialog, failureReason: e.target.value })}
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setProcessDialog({ ...processDialog, open: false })}>
              Cancel
            </Button>
            <Button
              variant={processDialog.success ? 'default' : 'destructive'}
              onClick={() => {
                if (processDialog.payout) {
                  processPayoutMutation.mutate({
                    payoutId: processDialog.payout.id,
                    reference: processDialog.reference || undefined,
                    success: processDialog.success,
                    failureReason: processDialog.failureReason || undefined,
                  });
                }
              }}
              disabled={
                (processDialog.success && !processDialog.reference) ||
                (!processDialog.success && !processDialog.failureReason)
              }
            >
              {processDialog.success ? 'Mark as Completed' : 'Mark as Failed'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
