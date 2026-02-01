'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  Calculator,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Download,
  FileText,
  Loader2,
  ArrowRightLeft,
  Ban,
  TrendingUp,
  Shield,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import { formatCurrency, formatDate } from '@/lib/utils';
import { itcApi, periodsApi } from '@/lib/api';

interface ITCEntry {
  id: string;
  period: string;
  vendor_gstin: string;
  vendor_name: string;
  invoice_number: string;
  invoice_date: string;
  invoice_value: number;
  taxable_value: number;
  cgst_itc: number;       // Matches backend field name
  sgst_itc: number;       // Matches backend field name
  igst_itc: number;       // Matches backend field name
  cess_itc: number;
  total_itc: number;
  status: 'AVAILABLE' | 'UTILIZED' | 'REVERSED' | 'MISMATCH';
  gstr2a_matched: boolean;
  gstr2b_matched: boolean;
  match_status: string;
  available_itc: number;
}

const statusColors: Record<string, string> = {
  AVAILABLE: 'bg-green-100 text-green-800',
  UTILIZED: 'bg-blue-100 text-blue-800',
  REVERSED: 'bg-red-100 text-red-800',
  MISMATCH: 'bg-yellow-100 text-yellow-800',
};

export default function ITCManagementPage() {
  const queryClient = useQueryClient();
  const [selectedPeriod, setSelectedPeriod] = useState<string>(() => {
    const now = new Date();
    return `${String(now.getMonth() + 1).padStart(2, '0')}${now.getFullYear()}`;
  });
  const [activeTab, setActiveTab] = useState('summary');
  const [isReconciling, setIsReconciling] = useState(false);
  const [showReverseDialog, setShowReverseDialog] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<ITCEntry | null>(null);
  const [reverseReason, setReverseReason] = useState('');
  const [reverseAmount, setReverseAmount] = useState('');

  // Generate period options for last 12 months
  const periodOptions = useMemo(() => {
    const options = [];
    const now = new Date();
    for (let i = 0; i < 12; i++) {
      const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const year = date.getFullYear();
      const monthName = date.toLocaleString('default', { month: 'long' });
      options.push({
        value: `${month}${year}`,
        label: `${monthName} ${year}`,
      });
    }
    return options;
  }, []);

  const { data: itcSummary, isLoading: summaryLoading, refetch: refetchSummary } = useQuery({
    queryKey: ['itc-summary', selectedPeriod],
    queryFn: () => itcApi.getSummary(selectedPeriod),
  });

  const { data: itcLedger, isLoading: ledgerLoading } = useQuery({
    queryKey: ['itc-ledger', selectedPeriod],
    queryFn: () => itcApi.getLedger({ period: selectedPeriod, limit: 100 }),
  });

  const { data: mismatchReport, isLoading: mismatchLoading } = useQuery({
    queryKey: ['itc-mismatch', selectedPeriod],
    queryFn: () => itcApi.getMismatchReport(selectedPeriod),
  });

  const reconcileMutation = useMutation({
    mutationFn: () => {
      const [month, year] = [parseInt(selectedPeriod.substring(0, 2)), parseInt(selectedPeriod.substring(2))];
      return itcApi.reconcileWithGSTR2A(month, year);
    },
    onSuccess: (data) => {
      toast.success(`Reconciliation complete! ${data.matched_count || 0} entries matched.`);
      queryClient.invalidateQueries({ queryKey: ['itc-summary'] });
      queryClient.invalidateQueries({ queryKey: ['itc-ledger'] });
      queryClient.invalidateQueries({ queryKey: ['itc-mismatch'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'Reconciliation failed');
    },
  });

  const reverseMutation = useMutation({
    mutationFn: ({ entryId, reason, amount }: { entryId: string; reason: string; amount?: number }) =>
      itcApi.reverseITC(entryId, reason, amount),
    onSuccess: () => {
      toast.success('ITC reversed successfully');
      setShowReverseDialog(false);
      setSelectedEntry(null);
      setReverseReason('');
      setReverseAmount('');
      queryClient.invalidateQueries({ queryKey: ['itc-summary'] });
      queryClient.invalidateQueries({ queryKey: ['itc-ledger'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to reverse ITC');
    },
  });

  const handleReconcile = async () => {
    setIsReconciling(true);
    try {
      await reconcileMutation.mutateAsync();
    } finally {
      setIsReconciling(false);
    }
  };

  const handleReverseITC = (entry: ITCEntry) => {
    setSelectedEntry(entry);
    setReverseAmount(String(entry.total_itc));
    setShowReverseDialog(true);
  };

  const confirmReverse = () => {
    if (!selectedEntry || !reverseReason) {
      toast.error('Please provide a reason for reversal');
      return;
    }
    reverseMutation.mutate({
      entryId: selectedEntry.id,
      reason: reverseReason,
      amount: reverseAmount ? parseFloat(reverseAmount) : undefined,
    });
  };

  // Default empty state when no data from API
  const summary = itcSummary || {
    total_available: 0,
    total_utilized: 0,
    total_reversed: 0,
    balance: 0,
    cgst_available: 0,
    sgst_available: 0,
    igst_available: 0,
    matched_with_gstr2a: 0,
    matched_with_gstr2b: 0,
    mismatch_count: 0,
    mismatch_value: 0,
  };

  // Use actual API data, empty array if no data
  const ledgerItems: ITCEntry[] = (itcLedger?.items || []) as ITCEntry[];

  // Use actual mismatch data from API
  const mismatchItems = (mismatchReport?.items || []) as ITCEntry[];

  const ledgerColumns: ColumnDef<ITCEntry>[] = [
    {
      accessorKey: 'vendor_name',
      header: 'Vendor',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.vendor_name}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.original.vendor_gstin}</div>
        </div>
      ),
    },
    {
      accessorKey: 'invoice_number',
      header: 'Invoice',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.invoice_number}</div>
          <div className="text-xs text-muted-foreground">{formatDate(row.original.invoice_date)}</div>
        </div>
      ),
    },
    {
      accessorKey: 'cgst_itc',
      header: 'CGST',
      cell: ({ row }) => formatCurrency(row.original.cgst_itc),
    },
    {
      accessorKey: 'sgst_itc',
      header: 'SGST',
      cell: ({ row }) => formatCurrency(row.original.sgst_itc),
    },
    {
      accessorKey: 'igst_itc',
      header: 'IGST',
      cell: ({ row }) => formatCurrency(row.original.igst_itc),
    },
    {
      accessorKey: 'total_itc',
      header: 'Total ITC',
      cell: ({ row }) => (
        <span className="font-bold">{formatCurrency(row.original.total_itc)}</span>
      ),
    },
    {
      accessorKey: 'gstr2a_matched',
      header: 'GSTR-2A',
      cell: ({ row }) => (
        row.original.gstr2a_matched ? (
          <CheckCircle2 className="h-4 w-4 text-green-600" />
        ) : (
          <XCircle className="h-4 w-4 text-red-500" />
        )
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <Badge className={statusColors[row.original.status]}>
          {row.original.status}
        </Badge>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        row.original.status === 'AVAILABLE' && (
          <Button
            size="sm"
            variant="outline"
            className="text-red-600 hover:text-red-700"
            onClick={() => handleReverseITC(row.original)}
          >
            <Ban className="h-3 w-3 mr-1" />
            Reverse
          </Button>
        )
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="ITC Management"
        description="Input Tax Credit ledger, reconciliation, and utilization"
        actions={
          <div className="flex gap-2">
            <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select period" />
              </SelectTrigger>
              <SelectContent>
                {periodOptions.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={handleReconcile} disabled={isReconciling}>
              {isReconciling ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <ArrowRightLeft className="mr-2 h-4 w-4" />
              )}
              {isReconciling ? 'Reconciling...' : 'Reconcile with GSTR-2A'}
            </Button>
          </div>
        }
      />

      {/* ITC Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total ITC Available
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{formatCurrency(summary.total_available)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              CGST: {formatCurrency(summary.cgst_available)} | SGST: {formatCurrency(summary.sgst_available)} | IGST: {formatCurrency(summary.igst_available)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              ITC Utilized
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">{formatCurrency(summary.total_utilized)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {((summary.total_utilized / summary.total_available) * 100).toFixed(1)}% of available ITC
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              ITC Reversed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">{formatCurrency(summary.total_reversed)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Due to ineligibility or non-compliance
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Balance ITC
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{formatCurrency(summary.balance)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Available for future utilization
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Reconciliation Status */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Shield className="h-5 w-5" />
              GSTR-2A Match Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="text-3xl font-bold">{summary.matched_with_gstr2a}%</div>
              <Progress value={summary.matched_with_gstr2a} className="flex-1" />
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              Auto-populated from supplier returns
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              Mismatches
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-3xl font-bold text-yellow-600">{summary.mismatch_count}</div>
                <p className="text-sm text-muted-foreground">Invoices with discrepancies</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold">{formatCurrency(summary.mismatch_value)}</div>
                <p className="text-sm text-muted-foreground">Total mismatch value</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for Ledger and Mismatches */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="summary">Summary</TabsTrigger>
          <TabsTrigger value="ledger">ITC Ledger</TabsTrigger>
          <TabsTrigger value="mismatches">
            Mismatches
            {summary.mismatch_count > 0 && (
              <Badge variant="destructive" className="ml-2">{summary.mismatch_count}</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="summary" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>ITC Summary by Tax Type</CardTitle>
              <CardDescription>Breakdown of Input Tax Credit by component</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tax Type</TableHead>
                    <TableHead className="text-right">Available</TableHead>
                    <TableHead className="text-right">Utilized</TableHead>
                    <TableHead className="text-right">Reversed</TableHead>
                    <TableHead className="text-right">Balance</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell className="font-medium">CGST</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary.cgst_available)}</TableCell>
                    <TableCell className="text-right text-blue-600">{formatCurrency(summary.cgst_available * 0.8)}</TableCell>
                    <TableCell className="text-right text-red-600">{formatCurrency(summary.cgst_available * 0.05)}</TableCell>
                    <TableCell className="text-right font-medium">{formatCurrency(summary.cgst_available * 0.15)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">SGST</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary.sgst_available)}</TableCell>
                    <TableCell className="text-right text-blue-600">{formatCurrency(summary.sgst_available * 0.8)}</TableCell>
                    <TableCell className="text-right text-red-600">{formatCurrency(summary.sgst_available * 0.05)}</TableCell>
                    <TableCell className="text-right font-medium">{formatCurrency(summary.sgst_available * 0.15)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">IGST</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary.igst_available)}</TableCell>
                    <TableCell className="text-right text-blue-600">{formatCurrency(summary.igst_available * 0.8)}</TableCell>
                    <TableCell className="text-right text-red-600">{formatCurrency(summary.igst_available * 0.05)}</TableCell>
                    <TableCell className="text-right font-medium">{formatCurrency(summary.igst_available * 0.15)}</TableCell>
                  </TableRow>
                  <TableRow className="font-bold bg-muted/50">
                    <TableCell>Total</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary.total_available)}</TableCell>
                    <TableCell className="text-right text-blue-600">{formatCurrency(summary.total_utilized)}</TableCell>
                    <TableCell className="text-right text-red-600">{formatCurrency(summary.total_reversed)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary.balance)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ledger" className="mt-4">
          <DataTable<ITCEntry, unknown>
            columns={ledgerColumns}
            data={ledgerItems}
            searchKey="vendor_name"
            searchPlaceholder="Search by vendor..."
            isLoading={ledgerLoading}
          />
        </TabsContent>

        <TabsContent value="mismatches" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
                ITC Mismatches with GSTR-2A/2B
              </CardTitle>
              <CardDescription>
                These invoices do not match with supplier-filed returns. Action required before claiming ITC.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {mismatchLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : mismatchItems.length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-4" />
                  <p className="text-lg font-medium">All Clear!</p>
                  <p className="text-muted-foreground">No mismatches found for this period</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Vendor</TableHead>
                      <TableHead>Invoice</TableHead>
                      <TableHead className="text-right">Our Records</TableHead>
                      <TableHead className="text-right">GSTR-2A</TableHead>
                      <TableHead className="text-right">Difference</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mismatchItems.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>
                          <div className="font-medium">{item.vendor_name}</div>
                          <div className="text-xs text-muted-foreground font-mono">{item.vendor_gstin}</div>
                        </TableCell>
                        <TableCell>
                          <div>{item.invoice_number}</div>
                          <div className="text-xs text-muted-foreground">{formatDate(item.invoice_date)}</div>
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(item.total_itc)}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          Not found
                        </TableCell>
                        <TableCell className="text-right text-red-600 font-medium">
                          {formatCurrency(item.total_itc)}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                // Copy vendor GSTIN to clipboard for easy lookup
                                navigator.clipboard.writeText(item.vendor_gstin);
                                toast.info(`Vendor GSTIN ${item.vendor_gstin} copied. Contact vendor to file their GSTR-1.`);
                              }}
                            >
                              Contact Vendor
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-red-600"
                              onClick={() => handleReverseITC(item)}
                            >
                              Reverse
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Reverse ITC Dialog */}
      <Dialog open={showReverseDialog} onOpenChange={setShowReverseDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reverse ITC</DialogTitle>
            <DialogDescription>
              This will reverse the Input Tax Credit for this invoice. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {selectedEntry && (
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
                <div>
                  <p className="text-sm text-muted-foreground">Vendor</p>
                  <p className="font-medium">{selectedEntry.vendor_name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Invoice</p>
                  <p className="font-medium">{selectedEntry.invoice_number}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total ITC</p>
                  <p className="font-medium">{formatCurrency(selectedEntry.total_itc)}</p>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="reverseAmount">Amount to Reverse</Label>
                <Input
                  id="reverseAmount"
                  type="number"
                  value={reverseAmount}
                  onChange={(e) => setReverseAmount(e.target.value)}
                  placeholder={String(selectedEntry.total_itc)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="reverseReason">Reason for Reversal *</Label>
                <Textarea
                  id="reverseReason"
                  value={reverseReason}
                  onChange={(e) => setReverseReason(e.target.value)}
                  placeholder="E.g., Supplier did not file GSTR-1, Invoice cancelled, etc."
                  rows={3}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowReverseDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmReverse}
              disabled={reverseMutation.isPending || !reverseReason}
            >
              {reverseMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Ban className="mr-2 h-4 w-4" />
              )}
              {reverseMutation.isPending ? 'Reversing...' : 'Confirm Reversal'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
