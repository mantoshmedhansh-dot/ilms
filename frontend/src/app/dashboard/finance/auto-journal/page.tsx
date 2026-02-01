'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  Wand2,
  FileText,
  Receipt,
  Building2,
  CheckCircle,
  Clock,
  Loader2,
  ChevronRight,
  RefreshCcw,
  Send,
  AlertCircle,
  FileCheck,
  BookOpen
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { autoJournalApi, invoicesApi, accountsApi } from '@/lib/api';
import { formatDate, formatCurrency } from '@/lib/utils';

interface PendingJournal {
  id: string;
  entry_number: string;
  entry_date: string;
  journal_type: string | null;
  narration: string;
  total_debit: number;
  total_credit: number;
  reference_type: string | null;
  reference_id: string | null;
  lines_count: number;
}

interface Invoice {
  id: string;
  invoice_number: string;
  invoice_date: string;
  customer_name: string;
  total_amount: number;
  status: string;
  has_journal: boolean;
}

interface GenerationResult {
  success: boolean;
  journal_id?: string;
  entry_number?: string;
  message: string;
  error?: string;
}

export default function AutoJournalPage() {
  const queryClient = useQueryClient();
  const [isInvoiceDialogOpen, setIsInvoiceDialogOpen] = useState(false);
  const [isReceiptDialogOpen, setIsReceiptDialogOpen] = useState(false);
  const [isBankDialogOpen, setIsBankDialogOpen] = useState(false);
  const [isBulkDialogOpen, setIsBulkDialogOpen] = useState(false);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState('');
  const [selectedReceiptId, setSelectedReceiptId] = useState('');
  const [selectedBankTxnId, setSelectedBankTxnId] = useState('');
  const [contraAccountCode, setContraAccountCode] = useState('');
  const [autoPost, setAutoPost] = useState(false);
  const [selectedInvoiceIds, setSelectedInvoiceIds] = useState<string[]>([]);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  // Fetch pending journal entries
  const { data: pendingJournals, isLoading: loadingPending, refetch: refetchPending } = useQuery({
    queryKey: ['pending-journals'],
    queryFn: () => autoJournalApi.listPendingJournals({ skip: 0, limit: 100 }),
  });

  // Fetch invoices without journals
  const { data: invoicesData } = useQuery({
    queryKey: ['invoices-for-journal'],
    queryFn: () => invoicesApi.list({ page: 1, size: 100 }),
  });

  // Fetch accounts for contra account selection
  const { data: accountsData } = useQuery({
    queryKey: ['accounts-dropdown'],
    queryFn: () => accountsApi.getDropdown(),
  });

  // Generate from invoice mutation
  const generateFromInvoiceMutation = useMutation({
    mutationFn: (data: { invoice_id: string; auto_post: boolean }) =>
      autoJournalApi.generateFromInvoice(data.invoice_id, data.auto_post),
    onSuccess: (result: GenerationResult) => {
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['pending-journals'] });
        queryClient.invalidateQueries({ queryKey: ['invoices-for-journal'] });
        toast.success(result.message);
        setIsInvoiceDialogOpen(false);
        setSelectedInvoiceId('');
        setAutoPost(false);
      } else {
        toast.error(result.error || 'Failed to generate journal');
      }
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to generate journal'),
  });

  // Generate from receipt mutation
  const generateFromReceiptMutation = useMutation({
    mutationFn: (data: { receipt_id: string; bank_account_code?: string; auto_post: boolean }) =>
      autoJournalApi.generateFromReceipt(data.receipt_id, data.bank_account_code, data.auto_post),
    onSuccess: (result: GenerationResult) => {
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['pending-journals'] });
        toast.success(result.message);
        setIsReceiptDialogOpen(false);
        setSelectedReceiptId('');
        setAutoPost(false);
      } else {
        toast.error(result.error || 'Failed to generate journal');
      }
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to generate journal'),
  });

  // Generate from bank transaction mutation
  const generateFromBankMutation = useMutation({
    mutationFn: (data: { bank_transaction_id: string; contra_account_code: string; auto_post: boolean }) =>
      autoJournalApi.generateFromBankTransaction(data.bank_transaction_id, data.contra_account_code, data.auto_post),
    onSuccess: (result: GenerationResult) => {
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['pending-journals'] });
        toast.success(result.message);
        setIsBankDialogOpen(false);
        setSelectedBankTxnId('');
        setContraAccountCode('');
        setAutoPost(false);
      } else {
        toast.error(result.error || 'Failed to generate journal');
      }
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to generate journal'),
  });

  // Bulk generate mutation
  const bulkGenerateMutation = useMutation({
    mutationFn: (data: { invoice_ids?: string[]; receipt_ids?: string[]; auto_post: boolean }) =>
      autoJournalApi.bulkGenerate(data.invoice_ids, data.receipt_ids, data.auto_post),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['pending-journals'] });
      queryClient.invalidateQueries({ queryKey: ['invoices-for-journal'] });
      toast.success(`Generated ${result.summary?.successful || 0} journals successfully`);
      if (result.summary?.failed > 0) {
        toast.warning(`${result.summary.failed} failed to generate`);
      }
      setIsBulkDialogOpen(false);
      setSelectedInvoiceIds([]);
      setAutoPost(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to bulk generate'),
  });

  // Post single journal mutation
  const postJournalMutation = useMutation({
    mutationFn: (journalId: string) => autoJournalApi.postJournal(journalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-journals'] });
      toast.success('Journal entry posted successfully');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to post journal'),
  });

  // Post all pending journals mutation
  const postAllMutation = useMutation({
    mutationFn: () => autoJournalApi.postAllPending(),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['pending-journals'] });
      toast.success(`Posted ${result.posted} journals successfully`);
      if (result.failed > 0) {
        toast.warning(`${result.failed} failed to post`);
      }
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to post journals'),
  });

  const getJournalTypeLabel = (type: string | null) => {
    const labels: Record<string, string> = {
      SALES: 'Sales',
      PURCHASE: 'Purchase',
      RECEIPT: 'Receipt',
      PAYMENT: 'Payment',
      CONTRA: 'Contra',
      JOURNAL: 'Journal',
      GENERAL: 'General',
    };
    return labels[type || 'GENERAL'] || type || 'General';
  };

  const getReferenceTypeIcon = (type: string | null) => {
    switch (type) {
      case 'INVOICE':
        return <FileText className="h-4 w-4 text-blue-500" />;
      case 'RECEIPT':
        return <Receipt className="h-4 w-4 text-green-500" />;
      case 'BANK_TRANSACTION':
        return <Building2 className="h-4 w-4 text-purple-500" />;
      default:
        return <BookOpen className="h-4 w-4 text-gray-500" />;
    }
  };

  const pendingColumns: ColumnDef<PendingJournal>[] = [
    {
      accessorKey: 'entry_number',
      header: 'Entry #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          {getReferenceTypeIcon(row.original.reference_type)}
          <span className="font-medium">{row.original.entry_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'entry_date',
      header: 'Date',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {formatDate(row.original.entry_date)}
        </span>
      ),
    },
    {
      accessorKey: 'journal_type',
      header: 'Type',
      cell: ({ row }) => (
        <Badge variant="outline">
          {getJournalTypeLabel(row.original.journal_type)}
        </Badge>
      ),
    },
    {
      accessorKey: 'narration',
      header: 'Narration',
      cell: ({ row }) => (
        <span className="text-sm line-clamp-1 max-w-xs">{row.original.narration}</span>
      ),
    },
    {
      accessorKey: 'total_debit',
      header: 'Amount',
      cell: ({ row }) => (
        <span className="font-medium">
          {formatCurrency(row.original.total_debit)}
        </span>
      ),
    },
    {
      accessorKey: 'lines_count',
      header: 'Lines',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {row.original.lines_count} lines
        </span>
      ),
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <Button
          size="sm"
          onClick={() => postJournalMutation.mutate(row.original.id)}
          disabled={postJournalMutation.isPending}
        >
          {postJournalMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              <Send className="mr-2 h-4 w-4" />
              Post
            </>
          )}
        </Button>
      ),
    },
  ];

  const invoices = invoicesData?.items || [];
  // API returns array directly, not { items: [...] }
  const accounts = Array.isArray(accountsData) ? accountsData : [];
  const pendingList = pendingJournals || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Auto Journal Entry"
        description="Automatically generate journal entries from invoices, receipts, and bank transactions"
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => refetchPending()}>
              <RefreshCcw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            {pendingList.length > 0 && (
              <Button
                variant="default"
                onClick={() => postAllMutation.mutate()}
                disabled={postAllMutation.isPending}
              >
                {postAllMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <FileCheck className="mr-2 h-4 w-4" />
                )}
                Post All ({pendingList.length})
              </Button>
            )}
          </div>
        }
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Journals</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pendingList.length}</div>
            <p className="text-xs text-muted-foreground">
              Draft entries awaiting posting
            </p>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:bg-accent/50 transition-colors" onClick={() => setIsInvoiceDialogOpen(true)}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">From Invoices</CardTitle>
            <FileText className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">{invoices.length}</div>
                <p className="text-xs text-muted-foreground">Available invoices</p>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:bg-accent/50 transition-colors" onClick={() => setIsReceiptDialogOpen(true)}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">From Receipts</CardTitle>
            <Receipt className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">-</div>
                <p className="text-xs text-muted-foreground">Payment receipts</p>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:bg-accent/50 transition-colors" onClick={() => setIsBankDialogOpen(true)}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">From Bank</CardTitle>
            <Building2 className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">-</div>
                <p className="text-xs text-muted-foreground">Bank transactions</p>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Generation Options */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wand2 className="h-5 w-5" />
            Quick Generation
          </CardTitle>
          <CardDescription>
            Generate journal entries automatically from different sources
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Dialog open={isInvoiceDialogOpen} onOpenChange={setIsInvoiceDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" className="w-full h-24 flex flex-col items-center justify-center gap-2">
                  <FileText className="h-8 w-8 text-blue-500" />
                  <span>From Sales Invoice</span>
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Generate from Sales Invoice</DialogTitle>
                  <DialogDescription>
                    Creates Accounts Receivable (Debit), Revenue (Credit), and GST entries
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="space-y-2">
                    <Label>Select Invoice</Label>
                    <Select value={selectedInvoiceId} onValueChange={setSelectedInvoiceId}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select an invoice" />
                      </SelectTrigger>
                      <SelectContent>
                        {invoices.map((inv: Invoice) => (
                          <SelectItem key={inv.id} value={inv.id}>
                            {inv.invoice_number} - {inv.customer_name} ({formatCurrency(inv.total_amount)})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="autoPostInvoice"
                      checked={autoPost}
                      onCheckedChange={(checked) => setAutoPost(checked as boolean)}
                    />
                    <Label htmlFor="autoPostInvoice" className="text-sm">
                      Auto-post journal entry (skip draft stage)
                    </Label>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsInvoiceDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={() => generateFromInvoiceMutation.mutate({
                      invoice_id: selectedInvoiceId,
                      auto_post: autoPost
                    })}
                    disabled={!selectedInvoiceId || generateFromInvoiceMutation.isPending}
                  >
                    {generateFromInvoiceMutation.isPending && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    Generate Journal
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            <Dialog open={isReceiptDialogOpen} onOpenChange={setIsReceiptDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" className="w-full h-24 flex flex-col items-center justify-center gap-2">
                  <Receipt className="h-8 w-8 text-green-500" />
                  <span>From Payment Receipt</span>
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Generate from Payment Receipt</DialogTitle>
                  <DialogDescription>
                    Creates Bank/Cash (Debit) and Accounts Receivable (Credit) entries
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="space-y-2">
                    <Label>Receipt ID</Label>
                    <Input
                      placeholder="Enter receipt ID (UUID)"
                      value={selectedReceiptId}
                      onChange={(e) => setSelectedReceiptId(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Bank Account Code (Optional)</Label>
                    <Select value={contraAccountCode} onValueChange={setContraAccountCode}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select bank account" />
                      </SelectTrigger>
                      <SelectContent>
                        {accounts
                          .filter((acc: { type: string }) => acc.type === 'ASSET')
                          .map((acc: { id: string; code: string; name: string }) => (
                            <SelectItem key={acc.id} value={acc.code}>
                              {acc.code} - {acc.name}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="autoPostReceipt"
                      checked={autoPost}
                      onCheckedChange={(checked) => setAutoPost(checked as boolean)}
                    />
                    <Label htmlFor="autoPostReceipt" className="text-sm">
                      Auto-post journal entry
                    </Label>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsReceiptDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={() => generateFromReceiptMutation.mutate({
                      receipt_id: selectedReceiptId,
                      bank_account_code: contraAccountCode || undefined,
                      auto_post: autoPost
                    })}
                    disabled={!selectedReceiptId || generateFromReceiptMutation.isPending}
                  >
                    {generateFromReceiptMutation.isPending && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    Generate Journal
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            <Dialog open={isBankDialogOpen} onOpenChange={setIsBankDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" className="w-full h-24 flex flex-col items-center justify-center gap-2">
                  <Building2 className="h-8 w-8 text-purple-500" />
                  <span>From Bank Transaction</span>
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Generate from Bank Transaction</DialogTitle>
                  <DialogDescription>
                    Creates journal entry for bank deposit or withdrawal
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="space-y-2">
                    <Label>Bank Transaction ID</Label>
                    <Input
                      placeholder="Enter bank transaction ID (UUID)"
                      value={selectedBankTxnId}
                      onChange={(e) => setSelectedBankTxnId(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Contra Account *</Label>
                    <Select value={contraAccountCode} onValueChange={setContraAccountCode}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select contra account" />
                      </SelectTrigger>
                      <SelectContent>
                        {accounts.map((acc: { id: string; code: string; name: string }) => (
                          <SelectItem key={acc.id} value={acc.code}>
                            {acc.code} - {acc.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      The other side of the bank entry (e.g., Sales, Expenses, etc.)
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="autoPostBank"
                      checked={autoPost}
                      onCheckedChange={(checked) => setAutoPost(checked as boolean)}
                    />
                    <Label htmlFor="autoPostBank" className="text-sm">
                      Auto-post journal entry
                    </Label>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsBankDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={() => generateFromBankMutation.mutate({
                      bank_transaction_id: selectedBankTxnId,
                      contra_account_code: contraAccountCode,
                      auto_post: autoPost
                    })}
                    disabled={!selectedBankTxnId || !contraAccountCode || generateFromBankMutation.isPending}
                  >
                    {generateFromBankMutation.isPending && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    Generate Journal
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>

      {/* Bulk Generation */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Bulk Generation</CardTitle>
            <CardDescription>
              Generate multiple journal entries at once
            </CardDescription>
          </div>
          <Dialog open={isBulkDialogOpen} onOpenChange={setIsBulkDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Wand2 className="mr-2 h-4 w-4" />
                Bulk Generate
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Bulk Journal Generation</DialogTitle>
                <DialogDescription>
                  Select multiple invoices to generate journal entries
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label>Select Invoices</Label>
                  <div className="border rounded-md max-h-60 overflow-y-auto">
                    {invoices.map((inv: Invoice) => (
                      <div
                        key={inv.id}
                        className="flex items-center space-x-2 p-3 border-b last:border-0 hover:bg-accent/50"
                      >
                        <Checkbox
                          id={inv.id}
                          checked={selectedInvoiceIds.includes(inv.id)}
                          onCheckedChange={(checked) => {
                            if (checked) {
                              setSelectedInvoiceIds([...selectedInvoiceIds, inv.id]);
                            } else {
                              setSelectedInvoiceIds(selectedInvoiceIds.filter(id => id !== inv.id));
                            }
                          }}
                        />
                        <Label htmlFor={inv.id} className="flex-1 cursor-pointer">
                          <div className="flex items-center justify-between">
                            <div>
                              <span className="font-medium">{inv.invoice_number}</span>
                              <span className="text-sm text-muted-foreground ml-2">
                                {inv.customer_name}
                              </span>
                            </div>
                            <span className="font-medium">
                              {formatCurrency(inv.total_amount)}
                            </span>
                          </div>
                        </Label>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {selectedInvoiceIds.length} selected
                    </span>
                    <Button
                      variant="link"
                      size="sm"
                      onClick={() => {
                        if (selectedInvoiceIds.length === invoices.length) {
                          setSelectedInvoiceIds([]);
                        } else {
                          setSelectedInvoiceIds(invoices.map((inv: Invoice) => inv.id));
                        }
                      }}
                    >
                      {selectedInvoiceIds.length === invoices.length ? 'Deselect All' : 'Select All'}
                    </Button>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="autoPostBulk"
                    checked={autoPost}
                    onCheckedChange={(checked) => setAutoPost(checked as boolean)}
                  />
                  <Label htmlFor="autoPostBulk" className="text-sm">
                    Auto-post all generated entries
                  </Label>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsBulkDialogOpen(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={() => bulkGenerateMutation.mutate({
                    invoice_ids: selectedInvoiceIds,
                    auto_post: autoPost
                  })}
                  disabled={selectedInvoiceIds.length === 0 || bulkGenerateMutation.isPending}
                >
                  {bulkGenerateMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Generate {selectedInvoiceIds.length} Journals
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardHeader>
      </Card>

      {/* Pending Journals Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-orange-500" />
            Pending Journal Entries
          </CardTitle>
          <CardDescription>
            Auto-generated journal entries awaiting review and posting
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingPending ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : pendingList.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle className="mx-auto h-12 w-12 text-green-500 mb-4" />
              <p className="text-lg font-medium">All Caught Up!</p>
              <p className="text-sm text-muted-foreground">
                No pending journal entries. Generate new ones from invoices, receipts, or bank transactions.
              </p>
            </div>
          ) : (
            <DataTable
              columns={pendingColumns}
              data={pendingList}
              searchKey="entry_number"
              searchPlaceholder="Search entries..."
              pageIndex={page}
              pageSize={pageSize}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
            />
          )}
        </CardContent>
      </Card>

      {/* Help Section */}
      <Card className="bg-blue-50 border-blue-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-blue-800">
            <AlertCircle className="h-5 w-5" />
            How Auto Journal Entry Works
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-blue-700 space-y-2">
          <p><strong>From Sales Invoice:</strong> Creates debit to Accounts Receivable (AR) and credits to Sales Revenue plus GST Payable accounts.</p>
          <p><strong>From Payment Receipt:</strong> Creates debit to Bank/Cash account and credit to Accounts Receivable (AR).</p>
          <p><strong>From Bank Transaction:</strong> Creates entry based on transaction type (deposit/withdrawal) with specified contra account.</p>
          <p className="pt-2">
            <strong>Tip:</strong> Use bulk generation to process multiple invoices at once. Review generated entries before posting to ensure accuracy.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
