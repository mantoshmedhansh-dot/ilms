'use client';

import { useEffect, useState } from 'react';
import { usePartnerStore, PartnerPayout } from '@/lib/storefront/partner-store';
import { partnerApi } from '@/lib/storefront/partner-api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { IndianRupee, Wallet, Clock, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import { formatCurrency, formatDate } from '@/lib/utils';

const statusColors: Record<string, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  PROCESSING: 'bg-blue-100 text-blue-800',
  COMPLETED: 'bg-green-100 text-green-800',
  FAILED: 'bg-red-100 text-red-800',
};

const MIN_PAYOUT_AMOUNT = 500;

export default function PartnerPayoutsPage() {
  const { dashboardStats, payouts, setPayouts, setDashboardStats, partner } = usePartnerStore();
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRequestDialog, setShowRequestDialog] = useState(false);
  const [payoutAmount, setPayoutAmount] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsResponse, payoutsResponse] = await Promise.all([
          partnerApi.getDashboardStats(),
          partnerApi.getPayouts(1, 20),
        ]);
        setDashboardStats(statsResponse);
        setPayouts(payoutsResponse.items || []);
      } catch (error) {
        console.error('Failed to fetch payouts:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [setDashboardStats, setPayouts]);

  const handleRequestPayout = async () => {
    const amount = parseFloat(payoutAmount);

    if (isNaN(amount) || amount < MIN_PAYOUT_AMOUNT) {
      setError(`Minimum payout amount is ${formatCurrency(MIN_PAYOUT_AMOUNT)}`);
      return;
    }

    if (amount > (dashboardStats?.pending_earnings || 0)) {
      setError('Amount exceeds available balance');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const response = await partnerApi.requestPayout(amount);

      if (response.success) {
        setSuccess('Payout request submitted successfully!');
        setShowRequestDialog(false);
        setPayoutAmount('');

        // Refresh data
        const [statsResponse, payoutsResponse] = await Promise.all([
          partnerApi.getDashboardStats(),
          partnerApi.getPayouts(1, 20),
        ]);
        setDashboardStats(statsResponse);
        setPayouts(payoutsResponse.items || []);
      } else {
        setError(response.message);
      }
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
            err.message
          : 'Failed to request payout';
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const stats = dashboardStats || {
    pending_earnings: 0,
    paid_earnings: 0,
  };

  const canRequestPayout =
    partner?.kyc_status === 'VERIFIED' && stats.pending_earnings >= MIN_PAYOUT_AMOUNT;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Payouts</h1>
          <p className="text-muted-foreground">Request and track your payouts</p>
        </div>

        <Dialog open={showRequestDialog} onOpenChange={setShowRequestDialog}>
          <DialogTrigger asChild>
            <Button disabled={!canRequestPayout}>
              <IndianRupee className="h-4 w-4 mr-2" />
              Request Payout
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Request Payout</DialogTitle>
              <DialogDescription>
                Enter the amount you want to withdraw. Minimum payout is {formatCurrency(MIN_PAYOUT_AMOUNT)}.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label>Available Balance</Label>
                <p className="text-2xl font-bold text-green-600">
                  {formatCurrency(stats.pending_earnings)}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="amount">Payout Amount</Label>
                <div className="relative">
                  <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="amount"
                    type="number"
                    placeholder="Enter amount"
                    value={payoutAmount}
                    onChange={(e) => setPayoutAmount(e.target.value)}
                    className="pl-9"
                    min={MIN_PAYOUT_AMOUNT}
                    max={stats.pending_earnings}
                  />
                </div>
                <p className="text-sm text-muted-foreground">
                  Minimum: {formatCurrency(MIN_PAYOUT_AMOUNT)}
                </p>
              </div>

              <Button
                variant="outline"
                className="w-full"
                onClick={() => setPayoutAmount(stats.pending_earnings.toString())}
              >
                Withdraw Full Amount
              </Button>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setShowRequestDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleRequestPayout} disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Processing...
                  </>
                ) : (
                  'Request Payout'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {success && (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      {/* KYC Warning */}
      {partner?.kyc_status !== 'VERIFIED' && (
        <Alert className="bg-yellow-50 border-yellow-200">
          <AlertCircle className="h-4 w-4 text-yellow-600" />
          <AlertDescription className="text-yellow-800">
            Complete your KYC verification to request payouts.{' '}
            <a href="/partner/kyc" className="font-medium underline">
              Complete KYC
            </a>
          </AlertDescription>
        </Alert>
      )}

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Available Balance</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {formatCurrency(stats.pending_earnings)}
            </div>
            <p className="text-xs text-muted-foreground">Ready for withdrawal</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Paid</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats.paid_earnings)}</div>
            <p className="text-xs text-muted-foreground">All-time payouts</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Minimum Payout</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(MIN_PAYOUT_AMOUNT)}</div>
            <p className="text-xs text-muted-foreground">Required minimum</p>
          </CardContent>
        </Card>
      </div>

      {/* Payout History */}
      <Card>
        <CardHeader>
          <CardTitle>Payout History</CardTitle>
          <CardDescription>Track all your payout requests</CardDescription>
        </CardHeader>
        <CardContent>
          {payouts.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No payout requests yet</p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Payout ID</TableHead>
                    <TableHead>Requested On</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead className="text-right">TDS</TableHead>
                    <TableHead className="text-right">Net Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Reference</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payouts.map((payout) => (
                    <TableRow key={payout.id}>
                      <TableCell className="font-mono text-sm">
                        {payout.payout_number}
                      </TableCell>
                      <TableCell>{formatDate(payout.requested_at)}</TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(payout.amount)}
                      </TableCell>
                      <TableCell className="text-right text-red-600">
                        -{formatCurrency(payout.tds_deducted)}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(payout.net_amount)}
                      </TableCell>
                      <TableCell>
                        <Badge className={statusColors[payout.status] || ''}>
                          {payout.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {payout.payment_reference || '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
