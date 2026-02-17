'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  Landmark,
  Upload,
  Check,
  X,
  Link2,
  Link2Off,
  Download,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { bankingApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Sparkles, Brain, TrendingUp } from 'lucide-react';

interface BankAccount {
  id: string;
  account_code: string;
  account_name: string;
  bank_name?: string;
  bank_account_number?: string;
  current_balance: number;
}

interface BankStatementLine {
  id: string;
  statement_date: string;
  value_date?: string;
  transaction_ref?: string;
  cheque_number?: string;
  transaction_type: string;
  description: string;
  debit_amount: number;
  credit_amount: number;
  balance: number;
  is_reconciled: boolean;
  matched_gl_id?: string;
}

interface GLEntry {
  id: string;
  transaction_date: string;
  entry_number: string;
  narration: string;
  debit_amount: number;
  credit_amount: number;
  running_balance: number;
  is_reconciled?: boolean;
}

interface ReconciliationSummary {
  bank_account_id: string;
  period_start: string;
  period_end: string;
  opening_book_balance: number;
  closing_book_balance: number;
  bank_statement_balance: number;
  deposits_in_transit: number;
  outstanding_cheques: number;
  unreconciled_count: number;
  reconciled_count: number;
  difference: number;
}

// Mock API - replace with actual API calls
const bankReconciliationApi = {
  getBankAccounts: async (): Promise<BankAccount[]> => {
    try {
      const { data } = await apiClient.get('/accounting/accounts/dropdown', {
        params: { account_type: 'ASSET', postable_only: true }
      });
      return data.filter((a: BankAccount) => a.account_code.startsWith('1'));
    } catch {
      return [];
    }
  },

  getStatementLines: async (accountId: string, params: { start_date: string; end_date: string }): Promise<BankStatementLine[]> => {
    try {
      const { data } = await apiClient.get(`/accounting/bank-statements/${accountId}`, { params });
      return data.items || [];
    } catch {
      return [];
    }
  },

  getGLEntries: async (accountId: string, params: { start_date: string; end_date: string }): Promise<GLEntry[]> => {
    try {
      const { data } = await apiClient.get(`/accounting/ledger/${accountId}`, { params });
      return data.items || [];
    } catch {
      return [];
    }
  },

  getSummary: async (accountId: string, params: { start_date: string; end_date: string }): Promise<ReconciliationSummary> => {
    try {
      const { data } = await apiClient.get(`/accounting/bank-reconciliation/${accountId}/summary`, { params });
      return data;
    } catch {
      return {
        bank_account_id: accountId,
        period_start: params.start_date,
        period_end: params.end_date,
        opening_book_balance: 0,
        closing_book_balance: 0,
        bank_statement_balance: 0,
        deposits_in_transit: 0,
        outstanding_cheques: 0,
        unreconciled_count: 0,
        reconciled_count: 0,
        difference: 0,
      };
    }
  },

  matchEntries: async (statementLineId: string, glEntryId: string): Promise<void> => {
    await apiClient.post('/accounting/bank-reconciliation/match', {
      statement_line_id: statementLineId,
      gl_entry_id: glEntryId,
    });
  },

  unmatchEntry: async (statementLineId: string): Promise<void> => {
    await apiClient.post(`/accounting/bank-reconciliation/unmatch/${statementLineId}`);
  },
};

export default function BankReconciliationPage() {
  const [selectedAccount, setSelectedAccount] = useState<string>('');
  const [periodStart, setPeriodStart] = useState(format(new Date(new Date().getFullYear(), new Date().getMonth(), 1), 'yyyy-MM-dd'));
  const [periodEnd, setPeriodEnd] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [selectedStatementLine, setSelectedStatementLine] = useState<BankStatementLine | null>(null);
  const [selectedGLEntry, setSelectedGLEntry] = useState<GLEntry | null>(null);
  const [isMatchDialogOpen, setIsMatchDialogOpen] = useState(false);
  const [isAutoReconciling, setIsAutoReconciling] = useState(false);
  const [autoReconcileResults, setAutoReconcileResults] = useState<{
    matched_count: number;
    total_amount: number;
    suggestions: Array<{
      bank_txn_id: string;
      journal_entry_id: string;
      confidence: number;
      bank_description: string;
      journal_narration: string;
      amount: number;
    }>;
  } | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const queryClient = useQueryClient();

  // Fetch bank accounts
  const { data: bankAccounts, isLoading: accountsLoading } = useQuery({
    queryKey: ['bank-accounts'],
    queryFn: bankReconciliationApi.getBankAccounts,
  });

  // Fetch statement lines
  const { data: statementLines, isLoading: statementsLoading } = useQuery({
    queryKey: ['bank-statements', selectedAccount, periodStart, periodEnd],
    queryFn: () => bankReconciliationApi.getStatementLines(selectedAccount, { start_date: periodStart, end_date: periodEnd }),
    enabled: !!selectedAccount,
  });

  // Fetch GL entries
  const { data: glEntries, isLoading: glLoading } = useQuery({
    queryKey: ['gl-entries', selectedAccount, periodStart, periodEnd],
    queryFn: () => bankReconciliationApi.getGLEntries(selectedAccount, { start_date: periodStart, end_date: periodEnd }),
    enabled: !!selectedAccount,
  });

  // Fetch summary
  const { data: summary } = useQuery({
    queryKey: ['reconciliation-summary', selectedAccount, periodStart, periodEnd],
    queryFn: () => bankReconciliationApi.getSummary(selectedAccount, { start_date: periodStart, end_date: periodEnd }),
    enabled: !!selectedAccount,
  });

  // Match mutation
  const matchMutation = useMutation({
    mutationFn: ({ statementId, glId }: { statementId: string; glId: string }) =>
      bankReconciliationApi.matchEntries(statementId, glId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bank-statements'] });
      queryClient.invalidateQueries({ queryKey: ['gl-entries'] });
      queryClient.invalidateQueries({ queryKey: ['reconciliation-summary'] });
      setIsMatchDialogOpen(false);
      setSelectedStatementLine(null);
      setSelectedGLEntry(null);
      toast.success('Entries matched successfully');
    },
    onError: () => {
      toast.error('Failed to match entries');
    },
  });

  const handleMatch = () => {
    if (selectedStatementLine && selectedGLEntry) {
      matchMutation.mutate({
        statementId: selectedStatementLine.id,
        glId: selectedGLEntry.id,
      });
    }
  };

  const selectedAccountDetails = bankAccounts?.find(a => a.id === selectedAccount);
  const unreconciledStatements = statementLines?.filter(s => !s.is_reconciled) || [];
  const unreconciledGL = glEntries?.filter(g => !g.is_reconciled) || [];

  const handleImportStatement = () => {
    // Create file input and trigger click
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv,.xlsx,.xls';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        toast.info(`Bank statement import from file "${file.name}" is not yet implemented. Please upload statements manually.`);
      }
    };
    input.click();
  };

  const handleExportReport = () => {
    if (!selectedAccount) {
      toast.error('Please select a bank account first');
      return;
    }
    const exportData = {
      account: selectedAccountDetails,
      period: { start: periodStart, end: periodEnd },
      summary: summary,
      statement_lines: statementLines,
      gl_entries: glEntries,
      exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Bank_Reconciliation_${selectedAccountDetails?.account_name || 'Report'}_${periodStart}_${periodEnd}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Reconciliation report exported');
  };

  // ML Auto-Reconciliation handlers
  const handleGetSuggestions = async () => {
    if (!selectedAccount) {
      toast.error('Please select a bank account first');
      return;
    }
    setIsAutoReconciling(true);
    try {
      const suggestions = await bankingApi.getReconciliationSuggestions(selectedAccount, {
        start_date: periodStart,
        end_date: periodEnd,
        min_confidence: 0.7,
        limit: 50,
      });
      setAutoReconcileResults(suggestions);
      setShowSuggestions(true);
      toast.success(`Found ${suggestions.suggestions?.length || 0} potential matches`);
    } catch (error) {
      toast.error('Failed to get reconciliation suggestions');
    } finally {
      setIsAutoReconciling(false);
    }
  };

  const handleAutoReconcile = async (dryRun = true) => {
    if (!selectedAccount) {
      toast.error('Please select a bank account first');
      return;
    }
    setIsAutoReconciling(true);
    try {
      const result = await bankingApi.autoReconcile(selectedAccount, {
        start_date: periodStart,
        end_date: periodEnd,
        confidence_threshold: 0.85,
        dry_run: dryRun,
      });

      if (dryRun) {
        setAutoReconcileResults(result);
        setShowSuggestions(true);
        toast.success(`Preview: ${result.matched_count} entries can be auto-matched`);
      } else {
        queryClient.invalidateQueries({ queryKey: ['bank-statements'] });
        queryClient.invalidateQueries({ queryKey: ['gl-entries'] });
        queryClient.invalidateQueries({ queryKey: ['reconciliation-summary'] });
        setShowSuggestions(false);
        setAutoReconcileResults(null);
        toast.success(`Successfully auto-reconciled ${result.matched_count} entries`);
      }
    } catch (error) {
      toast.error('Failed to auto-reconcile');
    } finally {
      setIsAutoReconciling(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Bank Reconciliation"
        description="Match bank statements with book entries"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleImportStatement}>
              <Upload className="mr-2 h-4 w-4" />
              Import Statement
            </Button>
            <Button variant="outline" onClick={handleExportReport}>
              <Download className="mr-2 h-4 w-4" />
              Export Report
            </Button>
            <Button
              variant="outline"
              onClick={handleGetSuggestions}
              disabled={!selectedAccount || isAutoReconciling}
              className="border-purple-200 text-purple-700 hover:bg-purple-50"
            >
              <Brain className="mr-2 h-4 w-4" />
              Get Suggestions
            </Button>
            <Button
              onClick={() => handleAutoReconcile(true)}
              disabled={!selectedAccount || isAutoReconciling}
              className="bg-indigo-600 text-white hover:bg-indigo-700"
            >
              <Sparkles className="mr-2 h-4 w-4" />
              {isAutoReconciling ? 'Processing...' : 'Auto-Reconcile'}
            </Button>
          </div>
        }
      />

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label>Bank Account</Label>
              <Select value={selectedAccount} onValueChange={setSelectedAccount}>
                <SelectTrigger>
                  <SelectValue placeholder="Select bank account" />
                </SelectTrigger>
                <SelectContent>
                  {accountsLoading ? (
                    <SelectItem value="loading" disabled>Loading...</SelectItem>
                  ) : bankAccounts?.length === 0 ? (
                    <SelectItem value="no-accounts" disabled>No bank accounts found</SelectItem>
                  ) : (
                    bankAccounts?.map((account) => (
                      <SelectItem key={account.id} value={account.id}>
                        {account.account_code} - {account.account_name}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Period Start</Label>
              <Input
                type="date"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Period End</Label>
              <Input
                type="date"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
              />
            </div>
            <div className="flex items-end">
              <Button
                className="w-full"
                onClick={() => queryClient.invalidateQueries({ queryKey: ['bank-statements'] })}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {selectedAccount && (
        <>
          {/* Summary Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Book Balance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatCurrency(summary?.closing_book_balance || 0)}
                </div>
                <p className="text-xs text-muted-foreground">As per General Ledger</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Bank Balance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatCurrency(summary?.bank_statement_balance || 0)}
                </div>
                <p className="text-xs text-muted-foreground">As per bank statement</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Unreconciled</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-orange-600">
                  {summary?.unreconciled_count || 0}
                </div>
                <p className="text-xs text-muted-foreground">Entries to match</p>
              </CardContent>
            </Card>
            <Card className={summary?.difference === 0 ? 'border-green-500' : 'border-red-500'}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  Difference
                  {summary?.difference === 0 ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-600" />
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${summary?.difference === 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(summary?.difference || 0)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {summary?.difference === 0 ? 'Balanced' : 'Needs attention'}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* ML Auto-Reconcile Suggestions */}
          {showSuggestions && autoReconcileResults && (
            <Card className="border-indigo-200 bg-indigo-50/50 dark:border-indigo-800 dark:bg-indigo-950/20">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-purple-600" />
                  AI-Powered Match Suggestions
                </CardTitle>
                <CardDescription>
                  Found {autoReconcileResults.suggestions?.length || 0} potential matches with high confidence
                </CardDescription>
              </CardHeader>
              <CardContent>
                {autoReconcileResults.suggestions?.length > 0 ? (
                  <>
                    <div className="max-h-[300px] overflow-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Bank Description</TableHead>
                            <TableHead>Book Narration</TableHead>
                            <TableHead className="text-right">Amount</TableHead>
                            <TableHead>Confidence</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {autoReconcileResults.suggestions.slice(0, 10).map((suggestion, idx) => (
                            <TableRow key={idx}>
                              <TableCell className="max-w-[200px] truncate text-sm">
                                {suggestion.bank_description}
                              </TableCell>
                              <TableCell className="max-w-[200px] truncate text-sm">
                                {suggestion.journal_narration}
                              </TableCell>
                              <TableCell className="text-right font-medium">
                                {formatCurrency(suggestion.amount)}
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  <div className="w-16 bg-gray-200 rounded-full h-2">
                                    <div
                                      className="bg-indigo-600 h-2 rounded-full"
                                      style={{ width: `${suggestion.confidence * 100}%` }}
                                    />
                                  </div>
                                  <span className="text-xs text-muted-foreground">
                                    {Math.round(suggestion.confidence * 100)}%
                                  </span>
                                </div>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    <div className="flex items-center justify-between mt-4 pt-4 border-t">
                      <div className="text-sm text-muted-foreground">
                        <TrendingUp className="inline h-4 w-4 mr-1" />
                        Total matched amount: <span className="font-semibold">{formatCurrency(autoReconcileResults.total_amount || 0)}</span>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" onClick={() => setShowSuggestions(false)}>
                          Cancel
                        </Button>
                        <Button
                          onClick={() => handleAutoReconcile(false)}
                          disabled={isAutoReconciling}
                          className="bg-emerald-600 text-white hover:bg-emerald-700"
                        >
                          <CheckCircle2 className="mr-2 h-4 w-4" />
                          Apply {autoReconcileResults.matched_count} Matches
                        </Button>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No high-confidence matches found</p>
                    <p className="text-sm">Try adjusting the date range or matching manually</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Side-by-side view */}
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Bank Statement */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Landmark className="h-4 w-4" />
                  Bank Statement
                </CardTitle>
                <CardDescription>
                  {unreconciledStatements.length} unreconciled entries
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="max-h-[500px] overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[40px]"></TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead className="text-right">Debit</TableHead>
                        <TableHead className="text-right">Credit</TableHead>
                        <TableHead className="w-[50px]">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {statementsLoading ? (
                        Array.from({ length: 5 }).map((_, i) => (
                          <TableRow key={i}>
                            {Array.from({ length: 6 }).map((_, j) => (
                              <TableCell key={j}><Skeleton className="h-4 w-16" /></TableCell>
                            ))}
                          </TableRow>
                        ))
                      ) : unreconciledStatements.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                            No unreconciled bank entries
                          </TableCell>
                        </TableRow>
                      ) : (
                        unreconciledStatements.map((line) => (
                          <TableRow
                            key={line.id}
                            className={`cursor-pointer ${selectedStatementLine?.id === line.id ? 'bg-blue-50' : ''}`}
                            onClick={() => setSelectedStatementLine(line)}
                          >
                            <TableCell>
                              <Checkbox
                                checked={selectedStatementLine?.id === line.id}
                                onCheckedChange={() => setSelectedStatementLine(line)}
                              />
                            </TableCell>
                            <TableCell className="text-sm">
                              {format(new Date(line.statement_date), 'dd/MM/yy')}
                            </TableCell>
                            <TableCell className="max-w-[200px] truncate text-sm">
                              {line.description}
                            </TableCell>
                            <TableCell className="text-right text-sm text-red-600">
                              {line.debit_amount > 0 ? formatCurrency(line.debit_amount) : '-'}
                            </TableCell>
                            <TableCell className="text-right text-sm text-green-600">
                              {line.credit_amount > 0 ? formatCurrency(line.credit_amount) : '-'}
                            </TableCell>
                            <TableCell>
                              {line.is_reconciled ? (
                                <Badge variant="default" className="bg-green-100 text-green-800">
                                  <Check className="h-3 w-3" />
                                </Badge>
                              ) : (
                                <Badge variant="outline">
                                  <X className="h-3 w-3" />
                                </Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            {/* Book Entries (GL) */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Landmark className="h-4 w-4" />
                  Book Entries (GL)
                </CardTitle>
                <CardDescription>
                  {unreconciledGL.length} unreconciled entries
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="max-h-[500px] overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[40px]"></TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead>Entry #</TableHead>
                        <TableHead className="text-right">Debit</TableHead>
                        <TableHead className="text-right">Credit</TableHead>
                        <TableHead className="w-[50px]">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {glLoading ? (
                        Array.from({ length: 5 }).map((_, i) => (
                          <TableRow key={i}>
                            {Array.from({ length: 6 }).map((_, j) => (
                              <TableCell key={j}><Skeleton className="h-4 w-16" /></TableCell>
                            ))}
                          </TableRow>
                        ))
                      ) : unreconciledGL.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                            No unreconciled book entries
                          </TableCell>
                        </TableRow>
                      ) : (
                        unreconciledGL.map((entry) => (
                          <TableRow
                            key={entry.id}
                            className={`cursor-pointer ${selectedGLEntry?.id === entry.id ? 'bg-blue-50' : ''}`}
                            onClick={() => setSelectedGLEntry(entry)}
                          >
                            <TableCell>
                              <Checkbox
                                checked={selectedGLEntry?.id === entry.id}
                                onCheckedChange={() => setSelectedGLEntry(entry)}
                              />
                            </TableCell>
                            <TableCell className="text-sm">
                              {format(new Date(entry.transaction_date), 'dd/MM/yy')}
                            </TableCell>
                            <TableCell className="text-sm font-mono">
                              {entry.entry_number}
                            </TableCell>
                            <TableCell className="text-right text-sm text-red-600">
                              {entry.debit_amount > 0 ? formatCurrency(entry.debit_amount) : '-'}
                            </TableCell>
                            <TableCell className="text-right text-sm text-green-600">
                              {entry.credit_amount > 0 ? formatCurrency(entry.credit_amount) : '-'}
                            </TableCell>
                            <TableCell>
                              {entry.is_reconciled ? (
                                <Badge variant="default" className="bg-green-100 text-green-800">
                                  <Check className="h-3 w-3" />
                                </Badge>
                              ) : (
                                <Badge variant="outline">
                                  <X className="h-3 w-3" />
                                </Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Match Action */}
          {selectedStatementLine && selectedGLEntry && (
            <Card className="border-blue-200 bg-blue-50">
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="text-sm">
                      <span className="font-medium">Bank: </span>
                      {selectedStatementLine.description.substring(0, 30)}...
                      <span className="ml-2 font-bold">
                        {formatCurrency(selectedStatementLine.debit_amount || selectedStatementLine.credit_amount)}
                      </span>
                    </div>
                    <Link2 className="h-5 w-5 text-blue-600" />
                    <div className="text-sm">
                      <span className="font-medium">Book: </span>
                      {selectedGLEntry.entry_number}
                      <span className="ml-2 font-bold">
                        {formatCurrency(selectedGLEntry.debit_amount || selectedGLEntry.credit_amount)}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setSelectedStatementLine(null);
                        setSelectedGLEntry(null);
                      }}
                    >
                      <X className="mr-2 h-4 w-4" />
                      Cancel
                    </Button>
                    <Button onClick={handleMatch} disabled={matchMutation.isPending}>
                      <Link2 className="mr-2 h-4 w-4" />
                      {matchMutation.isPending ? 'Matching...' : 'Match Entries'}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {!selectedAccount && (
        <Card className="py-12">
          <CardContent className="flex flex-col items-center justify-center text-center">
            <Landmark className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">Select a Bank Account</h3>
            <p className="text-sm text-muted-foreground mt-2">
              Choose a bank account from the dropdown above to start reconciliation
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
