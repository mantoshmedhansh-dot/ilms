'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  IndianRupee,
  Plus,
  Search,
  RefreshCw,
  Loader2,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  TrendingDown,
  TrendingUp,
  Hash,
} from 'lucide-react';
import { toast } from 'sonner';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { dealersApi } from '@/lib/api';
import { Dealer } from '@/types';

// DealerCreditTransaction is not exported from types, define locally
interface DealerCreditTransaction {
  id: string;
  dealer_id: string;
  transaction_type: string;
  transaction_date: string;
  reference_type: string;
  reference_number: string;
  debit_amount: number;
  credit_amount: number;
  balance: number;
  payment_mode?: string;
  remarks?: string;
  created_at: string;
}

function formatCurrency(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 10000000) return `\u20B9${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `\u20B9${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `\u20B9${(num / 1000).toFixed(1)}K`;
  return `\u20B9${num.toFixed(0)}`;
}

function getTransactionTypeBadge(type: string): string {
  const colors: Record<string, string> = {
    PAYMENT: 'bg-green-100 text-green-800',
    REFUND: 'bg-blue-100 text-blue-800',
    ADJUSTMENT: 'bg-yellow-100 text-yellow-800',
    OPENING_BALANCE: 'bg-purple-100 text-purple-800',
    INVOICE: 'bg-orange-100 text-orange-800',
    CREDIT_NOTE: 'bg-teal-100 text-teal-800',
  };
  return colors[type] || 'bg-gray-100 text-gray-800';
}

const TRANSACTION_TYPES = [
  { value: 'PAYMENT', label: 'Payment' },
  { value: 'REFUND', label: 'Refund' },
  { value: 'ADJUSTMENT', label: 'Adjustment' },
  { value: 'OPENING_BALANCE', label: 'Opening Balance' },
];

const REFERENCE_TYPES = [
  { value: 'INVOICE', label: 'Invoice' },
  { value: 'CREDIT_NOTE', label: 'Credit Note' },
  { value: 'PAYMENT', label: 'Payment' },
  { value: 'ADJUSTMENT', label: 'Adjustment' },
];

const PAYMENT_MODES = [
  { value: 'CASH', label: 'Cash' },
  { value: 'CHEQUE', label: 'Cheque' },
  { value: 'NEFT', label: 'NEFT' },
  { value: 'RTGS', label: 'RTGS' },
  { value: 'UPI', label: 'UPI' },
];

const PAGE_SIZE = 20;

export default function CreditLedgerPage() {
  const queryClient = useQueryClient();

  // Dealer selection
  const [selectedDealerId, setSelectedDealerId] = useState<string>('');

  // Filters
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [searchRef, setSearchRef] = useState('');

  // Pagination
  const [page, setPage] = useState(1);

  // Record payment dialog
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [paymentType, setPaymentType] = useState('');
  const [paymentDate, setPaymentDate] = useState('');
  const [paymentRefType, setPaymentRefType] = useState('');
  const [paymentRefNumber, setPaymentRefNumber] = useState('');
  const [paymentDebit, setPaymentDebit] = useState('');
  const [paymentCredit, setPaymentCredit] = useState('');
  const [paymentMode, setPaymentMode] = useState('');
  const [paymentRemarks, setPaymentRemarks] = useState('');

  // Fetch dealers for dropdown
  const { data: dealersData } = useQuery({
    queryKey: ['dealers-dropdown'],
    queryFn: () => dealersApi.list({ size: 100 }),
    staleTime: 10 * 60 * 1000,
  });

  const dealers = (dealersData?.items || []) as Dealer[];

  // Fetch ledger for selected dealer
  const {
    data: ledgerData,
    isLoading: isLedgerLoading,
    refetch,
    isFetching,
  } = useQuery<{
    items: DealerCreditTransaction[];
    total: number;
    total_debit: number;
    total_credit: number;
    closing_balance: number;
  }>({
    queryKey: ['credit-ledger', selectedDealerId, page, startDate, endDate],
    queryFn: () =>
      dealersApi.getLedger(selectedDealerId, {
        skip: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      }),
    enabled: !!selectedDealerId,
    staleTime: 2 * 60 * 1000,
  });

  // Record payment mutation
  const recordPaymentMutation = useMutation({
    mutationFn: (data: {
      transaction_type: string;
      transaction_date: string;
      reference_type: string;
      reference_number: string;
      debit_amount: number;
      credit_amount: number;
      payment_mode?: string;
      remarks?: string;
    }) => dealersApi.recordPayment(selectedDealerId, data),
    onSuccess: () => {
      toast.success('Payment recorded successfully');
      queryClient.invalidateQueries({ queryKey: ['credit-ledger'] });
      resetPaymentForm();
      setShowPaymentDialog(false);
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    },
  });

  const resetPaymentForm = () => {
    setPaymentType('');
    setPaymentDate('');
    setPaymentRefType('');
    setPaymentRefNumber('');
    setPaymentDebit('');
    setPaymentCredit('');
    setPaymentMode('');
    setPaymentRemarks('');
  };

  const handleRecordPayment = () => {
    if (!paymentType) {
      toast.error('Select a transaction type');
      return;
    }
    if (!paymentDate) {
      toast.error('Enter a transaction date');
      return;
    }
    if (!paymentRefType) {
      toast.error('Select a reference type');
      return;
    }
    if (!paymentRefNumber) {
      toast.error('Enter a reference number');
      return;
    }
    if (!paymentDebit && !paymentCredit) {
      toast.error('Enter a debit or credit amount');
      return;
    }

    recordPaymentMutation.mutate({
      transaction_type: paymentType,
      transaction_date: paymentDate,
      reference_type: paymentRefType,
      reference_number: paymentRefNumber,
      debit_amount: Number(paymentDebit) || 0,
      credit_amount: Number(paymentCredit) || 0,
      payment_mode: paymentMode || undefined,
      remarks: paymentRemarks || undefined,
    });
  };

  // Derived data
  const transactions = ledgerData?.items || [];
  const totalTransactions = ledgerData?.total || 0;
  const totalDebit = ledgerData?.total_debit || 0;
  const totalCredit = ledgerData?.total_credit || 0;
  const closingBalance = ledgerData?.closing_balance || 0;
  const totalPages = Math.ceil(totalTransactions / PAGE_SIZE);

  // Client-side search filter on reference number
  const filteredTransactions = searchRef
    ? transactions.filter((t) =>
        t.reference_number?.toLowerCase().includes(searchRef.toLowerCase())
      )
    : transactions;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <IndianRupee className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Credit Ledger</h1>
            <p className="text-muted-foreground">
              Track dealer credit transactions, payments, and balances
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {selectedDealerId && (
            <Button onClick={() => setShowPaymentDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Record Payment
            </Button>
          )}
          <Button
            onClick={() => refetch()}
            disabled={isFetching || !selectedDealerId}
            variant="outline"
            size="icon"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Dealer Selector */}
      <Card>
        <CardContent className="pt-4">
          <div className="min-w-[280px] max-w-md">
            <Label className="text-xs text-muted-foreground mb-1 block">
              Select Dealer
            </Label>
            <Select
              value={selectedDealerId}
              onValueChange={(v) => {
                setSelectedDealerId(v);
                setPage(1);
                setStartDate('');
                setEndDate('');
                setSearchRef('');
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Choose a dealer..." />
              </SelectTrigger>
              <SelectContent>
                {dealers.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {d.dealer_code || d.code} - {d.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Empty state when no dealer selected */}
      {!selectedDealerId && (
        <Card>
          <CardContent className="py-16">
            <div className="text-center">
              <BookOpen className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-muted-foreground text-lg font-medium">
                Select a dealer to view credit ledger
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Choose a dealer from the dropdown above to see their transaction history
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading state */}
      {selectedDealerId && isLedgerLoading && (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
          <Skeleton className="h-96" />
        </div>
      )}

      {/* Content when dealer is selected and data loaded */}
      {selectedDealerId && !isLedgerLoading && (
        <>
          {/* KPI Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="border-l-4 border-l-red-500">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Total Debit
                </CardTitle>
                <TrendingDown className="h-4 w-4 text-red-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums text-red-600">
                  {formatCurrency(totalDebit)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Sum of all debits
                </p>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-green-500">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Total Credit
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums text-green-600">
                  {formatCurrency(totalCredit)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Sum of all credits
                </p>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-blue-500">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Closing Balance
                </CardTitle>
                <IndianRupee className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">
                  {formatCurrency(closingBalance)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Current outstanding
                </p>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-gray-400">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Total Transactions
                </CardTitle>
                <Hash className="h-4 w-4 text-gray-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">
                  {totalTransactions}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Ledger entries
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Filter Bar */}
          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-wrap gap-4 items-end">
                <div className="min-w-[160px]">
                  <Label className="text-xs text-muted-foreground mb-1 block">
                    Start Date
                  </Label>
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(e) => {
                      setStartDate(e.target.value);
                      setPage(1);
                    }}
                  />
                </div>
                <div className="min-w-[160px]">
                  <Label className="text-xs text-muted-foreground mb-1 block">
                    End Date
                  </Label>
                  <Input
                    type="date"
                    value={endDate}
                    onChange={(e) => {
                      setEndDate(e.target.value);
                      setPage(1);
                    }}
                  />
                </div>
                <div className="min-w-[200px] flex-1 max-w-sm">
                  <Label className="text-xs text-muted-foreground mb-1 block">
                    Search Reference #
                  </Label>
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search by reference number..."
                      value={searchRef}
                      onChange={(e) => setSearchRef(e.target.value)}
                      className="pl-9"
                    />
                  </div>
                </div>
                {(startDate || endDate || searchRef) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setStartDate('');
                      setEndDate('');
                      setSearchRef('');
                      setPage(1);
                    }}
                  >
                    Clear Filters
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Ledger Table */}
          <Card>
            <CardContent className="pt-4">
              {filteredTransactions.length > 0 ? (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left">
                          <th className="pb-3 font-medium text-muted-foreground">
                            Date
                          </th>
                          <th className="pb-3 font-medium text-muted-foreground">
                            Transaction Type
                          </th>
                          <th className="pb-3 font-medium text-muted-foreground">
                            Reference Type
                          </th>
                          <th className="pb-3 font-medium text-muted-foreground">
                            Reference #
                          </th>
                          <th className="pb-3 font-medium text-muted-foreground text-right">
                            Debit
                          </th>
                          <th className="pb-3 font-medium text-muted-foreground text-right">
                            Credit
                          </th>
                          <th className="pb-3 font-medium text-muted-foreground text-right">
                            Balance
                          </th>
                          <th className="pb-3 font-medium text-muted-foreground">
                            Remarks
                          </th>
                          <th className="pb-3 font-medium text-muted-foreground text-center">
                            Payment Mode
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredTransactions.map((txn) => (
                          <tr
                            key={txn.id}
                            className="border-b last:border-0 hover:bg-muted/50"
                          >
                            <td className="py-3 text-xs text-muted-foreground whitespace-nowrap">
                              {txn.transaction_date
                                ? new Date(txn.transaction_date).toLocaleDateString(
                                    'en-IN'
                                  )
                                : '-'}
                            </td>
                            <td className="py-3">
                              <Badge
                                variant="outline"
                                className={`text-[10px] ${getTransactionTypeBadge(txn.transaction_type)}`}
                              >
                                {(txn.transaction_type || '').replace(/_/g, ' ')}
                              </Badge>
                            </td>
                            <td className="py-3 text-xs">
                              {txn.reference_type?.replace(/_/g, ' ') || '-'}
                            </td>
                            <td className="py-3 font-mono text-xs font-medium">
                              {txn.reference_number || '-'}
                            </td>
                            <td className="py-3 text-right tabular-nums font-semibold text-red-600">
                              {txn.debit_amount > 0
                                ? formatCurrency(txn.debit_amount)
                                : '-'}
                            </td>
                            <td className="py-3 text-right tabular-nums font-semibold text-green-600">
                              {txn.credit_amount > 0
                                ? formatCurrency(txn.credit_amount)
                                : '-'}
                            </td>
                            <td className="py-3 text-right tabular-nums font-semibold">
                              {formatCurrency(txn.balance)}
                            </td>
                            <td className="py-3 text-xs text-muted-foreground max-w-[200px] truncate">
                              {txn.remarks || '-'}
                            </td>
                            <td className="py-3 text-center">
                              {txn.payment_mode ? (
                                <Badge variant="secondary" className="text-[10px]">
                                  {txn.payment_mode}
                                </Badge>
                              ) : (
                                <span className="text-xs text-muted-foreground">-</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between mt-4 pt-4 border-t">
                      <p className="text-sm text-muted-foreground">
                        Page {page} of {totalPages} ({totalTransactions} transactions)
                      </p>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setPage((p) => Math.max(1, p - 1))}
                          disabled={page <= 1}
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                          disabled={page >= totalPages}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12">
                  <BookOpen className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
                  <p className="text-muted-foreground">No transactions found</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {searchRef
                      ? 'Try adjusting your search criteria'
                      : 'Record a payment to get started'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Record Payment Dialog */}
      <Dialog
        open={showPaymentDialog}
        onOpenChange={(open) => {
          if (!open) {
            resetPaymentForm();
          }
          setShowPaymentDialog(open);
        }}
      >
        <DialogContent className="sm:max-w-[550px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <IndianRupee className="h-5 w-5 text-blue-600" />
              Record Payment
            </DialogTitle>
            <DialogDescription>
              Create a new credit ledger entry for the selected dealer.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label>Transaction Type *</Label>
              <Select value={paymentType} onValueChange={setPaymentType}>
                <SelectTrigger>
                  <SelectValue placeholder="Select transaction type..." />
                </SelectTrigger>
                <SelectContent>
                  {TRANSACTION_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Transaction Date *</Label>
              <Input
                type="date"
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
              />
            </div>

            <div>
              <Label>Reference Type *</Label>
              <Select value={paymentRefType} onValueChange={setPaymentRefType}>
                <SelectTrigger>
                  <SelectValue placeholder="Select reference type..." />
                </SelectTrigger>
                <SelectContent>
                  {REFERENCE_TYPES.map((r) => (
                    <SelectItem key={r.value} value={r.value}>
                      {r.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Reference Number *</Label>
              <Input
                placeholder="Enter reference number"
                value={paymentRefNumber}
                onChange={(e) => setPaymentRefNumber(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Debit Amount (INR)</Label>
                <Input
                  type="number"
                  placeholder="0.00"
                  value={paymentDebit}
                  onChange={(e) => setPaymentDebit(e.target.value)}
                  min={0}
                  step="0.01"
                />
              </div>
              <div>
                <Label>Credit Amount (INR)</Label>
                <Input
                  type="number"
                  placeholder="0.00"
                  value={paymentCredit}
                  onChange={(e) => setPaymentCredit(e.target.value)}
                  min={0}
                  step="0.01"
                />
              </div>
            </div>

            <div>
              <Label>Payment Mode</Label>
              <Select value={paymentMode} onValueChange={setPaymentMode}>
                <SelectTrigger>
                  <SelectValue placeholder="Select payment mode..." />
                </SelectTrigger>
                <SelectContent>
                  {PAYMENT_MODES.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Remarks</Label>
              <Textarea
                placeholder="Add a note or description..."
                value={paymentRemarks}
                onChange={(e) => setPaymentRemarks(e.target.value)}
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                resetPaymentForm();
                setShowPaymentDialog(false);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleRecordPayment}
              disabled={
                recordPaymentMutation.isPending ||
                !paymentType ||
                !paymentDate ||
                !paymentRefType ||
                !paymentRefNumber
              }
            >
              {recordPaymentMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Saving...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" /> Record Entry
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
