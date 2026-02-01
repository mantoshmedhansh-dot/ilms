'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, BookOpen, Trash2, CheckCircle, XCircle, Send, FileCheck, Loader2, Copy, Pencil, RotateCcw, BookMarked } from 'lucide-react';
import { toast } from 'sonner';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { journalEntriesApi, accountsApi } from '@/lib/api';
import { formatDate, formatCurrency } from '@/lib/utils';

interface JournalLine {
  id?: string;
  account_id: string;
  account?: { code: string; name: string };
  description?: string;
  debit_amount: number;
  credit_amount: number;
}

interface JournalEntry {
  id: string;
  entry_number: string;
  entry_type: string;
  entry_date: string;
  source_type?: string;
  source_number?: string;
  narration: string;
  total_debit: number;
  total_credit: number;
  status: 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'POSTED' | 'REJECTED';
  lines?: JournalLine[];
  created_by?: { full_name: string };
  approved_by?: { full_name: string };
  rejection_reason?: string;
  created_at: string;
}

interface Account {
  id: string;
  code: string;
  name: string;
  type: string;
}

const emptyLine = (): JournalLine => ({
  account_id: '',
  description: '',
  debit_amount: 0,
  credit_amount: 0,
});

export default function JournalEntriesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [isRejectDialogOpen, setIsRejectDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isReverseDialogOpen, setIsReverseDialogOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<JournalEntry | null>(null);
  const [entryToDelete, setEntryToDelete] = useState<JournalEntry | null>(null);
  const [entryToReverse, setEntryToReverse] = useState<JournalEntry | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [reversalDate, setReversalDate] = useState(new Date().toISOString().split('T')[0]);
  const [reversalReason, setReversalReason] = useState('');
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    entry_date: new Date().toISOString().split('T')[0],
    entry_type: 'MANUAL',
    source_number: '',
    narration: '',
    lines: [emptyLine(), emptyLine()],
  });

  const { data, isLoading } = useQuery({
    queryKey: ['journal-entries', page, pageSize, statusFilter],
    queryFn: () => journalEntriesApi.list({ page: page + 1, size: pageSize, status: statusFilter === 'all' ? undefined : statusFilter }),
  });

  const { data: accountsData } = useQuery({
    queryKey: ['accounts-dropdown'],
    queryFn: () => accountsApi.getDropdown(),
  });

  const createMutation = useMutation({
    mutationFn: journalEntriesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] });
      toast.success('Journal entry created as draft');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create entry'),
  });

  const submitMutation = useMutation({
    mutationFn: (id: string) => journalEntriesApi.submit(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] });
      toast.success('Entry submitted for approval');
      setIsViewOpen(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to submit'),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => journalEntriesApi.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] });
      toast.success('Entry approved');
      setIsViewOpen(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to approve'),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => journalEntriesApi.reject(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] });
      toast.success('Entry rejected');
      setIsViewOpen(false);
      setIsRejectDialogOpen(false);
      setRejectionReason('');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to reject'),
  });

  const postMutation = useMutation({
    mutationFn: journalEntriesApi.post,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] });
      toast.success('Entry posted to ledger');
      setIsViewOpen(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to post'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof journalEntriesApi.update>[1] }) =>
      journalEntriesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] });
      toast.success('Journal entry updated');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update entry'),
  });

  const deleteMutation = useMutation({
    mutationFn: journalEntriesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] });
      toast.success('Journal entry deleted');
      setIsDeleteDialogOpen(false);
      setEntryToDelete(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete entry'),
  });

  const reverseMutation = useMutation({
    mutationFn: ({ id, date, reason }: { id: string; date: string; reason: string }) =>
      journalEntriesApi.reverse(id, date, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] });
      toast.success('Reversing entry created');
      setIsViewOpen(false);
      setIsReverseDialogOpen(false);
      setEntryToReverse(null);
      setReversalReason('');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to reverse entry'),
  });

  const handleReverse = (entry: JournalEntry) => {
    setEntryToReverse(entry);
    setReversalDate(new Date().toISOString().split('T')[0]);
    setReversalReason(`Reversal of ${entry.entry_number}`);
    setIsReverseDialogOpen(true);
  };

  const confirmReverse = () => {
    if (entryToReverse && reversalDate) {
      reverseMutation.mutate({
        id: entryToReverse.id,
        date: reversalDate,
        reason: reversalReason,
      });
    }
  };

  const resetForm = () => {
    setFormData({
      entry_date: new Date().toISOString().split('T')[0],
      entry_type: 'MANUAL',
      source_number: '',
      narration: '',
      lines: [emptyLine(), emptyLine()],
    });
    setIsDialogOpen(false);
    setIsEditMode(false);
    setEditingEntryId(null);
  };

  const handleDuplicate = async (entry: JournalEntry) => {
    try {
      const detail = await journalEntriesApi.getById(entry.id);
      setFormData({
        entry_date: new Date().toISOString().split('T')[0], // New date
        entry_type: detail.entry_type || 'MANUAL',
        source_number: '',
        narration: detail.narration || '',
        lines: detail.lines?.map((line: JournalLine) => ({
          account_id: line.account_id,
          description: line.description || '',
          debit_amount: line.debit_amount || 0,
          credit_amount: line.credit_amount || 0,
        })) || [emptyLine(), emptyLine()],
      });
      setIsEditMode(false);
      setIsDialogOpen(true);
      toast.info('Entry copied. Modify and save as new draft.');
    } catch {
      toast.error('Failed to load entry details');
    }
  };

  const handleEdit = async (entry: JournalEntry) => {
    if (entry.status !== 'DRAFT') {
      toast.error('Only draft entries can be edited');
      return;
    }
    try {
      const detail = await journalEntriesApi.getById(entry.id);
      setFormData({
        entry_date: detail.entry_date?.split('T')[0] || new Date().toISOString().split('T')[0],
        entry_type: detail.entry_type || 'MANUAL',
        source_number: detail.source_number || '',
        narration: detail.narration || '',
        lines: detail.lines?.map((line: JournalLine) => ({
          account_id: line.account_id,
          description: line.description || '',
          debit_amount: line.debit_amount || 0,
          credit_amount: line.credit_amount || 0,
        })) || [emptyLine(), emptyLine()],
      });
      setIsEditMode(true);
      setEditingEntryId(entry.id);
      setIsDialogOpen(true);
    } catch {
      toast.error('Failed to load entry details');
    }
  };

  const handleDelete = (entry: JournalEntry) => {
    if (entry.status !== 'DRAFT') {
      toast.error('Only draft entries can be deleted');
      return;
    }
    setEntryToDelete(entry);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (entryToDelete) {
      deleteMutation.mutate(entryToDelete.id);
    }
  };

  const handleViewEntry = async (entry: JournalEntry) => {
    try {
      const detail = await journalEntriesApi.getById(entry.id);
      setSelectedEntry(detail);
    } catch {
      setSelectedEntry(entry);
    }
    setIsViewOpen(true);
  };

  const addLine = () => {
    setFormData({ ...formData, lines: [...formData.lines, emptyLine()] });
  };

  const removeLine = (index: number) => {
    if (formData.lines.length > 2) {
      const newLines = formData.lines.filter((_, i) => i !== index);
      setFormData({ ...formData, lines: newLines });
    }
  };

  const updateLine = (index: number, field: keyof JournalLine, value: string | number) => {
    const newLines = [...formData.lines];
    newLines[index] = { ...newLines[index], [field]: value };
    // If debit is set, clear credit and vice versa
    if (field === 'debit_amount' && value) {
      newLines[index].credit_amount = 0;
    } else if (field === 'credit_amount' && value) {
      newLines[index].debit_amount = 0;
    }
    setFormData({ ...formData, lines: newLines });
  };

  const getTotals = () => {
    const totalDebit = formData.lines.reduce((sum, line) => sum + (line.debit_amount || 0), 0);
    const totalCredit = formData.lines.reduce((sum, line) => sum + (line.credit_amount || 0), 0);
    return { totalDebit, totalCredit, isBalanced: totalDebit === totalCredit && totalDebit > 0 };
  };

  const handleSubmit = () => {
    const { totalDebit, totalCredit } = getTotals();

    if (!formData.entry_date || !formData.narration.trim()) {
      toast.error('Date and narration are required');
      return;
    }

    if (totalDebit !== totalCredit) {
      toast.error('Debit and credit must be equal');
      return;
    }

    if (totalDebit === 0) {
      toast.error('Entry amounts cannot be zero');
      return;
    }

    const validLines = formData.lines.filter(l => l.account_id && (l.debit_amount || l.credit_amount));
    if (validLines.length < 2) {
      toast.error('At least 2 account lines are required');
      return;
    }

    const entryData = {
      entry_date: formData.entry_date,
      source_number: formData.source_number || undefined,
      narration: formData.narration,
      lines: validLines.map(l => ({
        account_id: l.account_id,
        description: l.description || undefined,
        debit_amount: l.debit_amount,
        credit_amount: l.credit_amount,
      })),
    };

    if (isEditMode && editingEntryId) {
      updateMutation.mutate({ id: editingEntryId, data: entryData });
    } else {
      createMutation.mutate({
        ...entryData,
        entry_type: formData.entry_type,
      });
    }
  };

  const columns: ColumnDef<JournalEntry>[] = [
    {
      accessorKey: 'entry_number',
      header: 'Entry #',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-muted-foreground" />
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
      accessorKey: 'narration',
      header: 'Narration',
      cell: ({ row }) => (
        <span className="text-sm line-clamp-1 max-w-xs">{row.original.narration}</span>
      ),
    },
    {
      accessorKey: 'total_debit',
      header: 'Debit',
      cell: ({ row }) => (
        <span className="font-medium text-green-600">
          {formatCurrency(row.original.total_debit)}
        </span>
      ),
    },
    {
      accessorKey: 'total_credit',
      header: 'Credit',
      cell: ({ row }) => (
        <span className="font-medium text-blue-600">
          {formatCurrency(row.original.total_credit)}
        </span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
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
            <DropdownMenuItem onClick={() => handleViewEntry(row.original)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleDuplicate(row.original)}>
              <Copy className="mr-2 h-4 w-4" />
              Duplicate
            </DropdownMenuItem>
            {row.original.status === 'DRAFT' && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => submitMutation.mutate(row.original.id)}>
                  <Send className="mr-2 h-4 w-4" />
                  Submit for Approval
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleEdit(row.original)}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => handleDelete(row.original)}
                  className="text-destructive focus:text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </>
            )}
            {row.original.status === 'PENDING_APPROVAL' && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => approveMutation.mutate(row.original.id)}>
                  <CheckCircle className="mr-2 h-4 w-4 text-green-600" />
                  Approve
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    setSelectedEntry(row.original);
                    setIsRejectDialogOpen(true);
                  }}
                  className="text-destructive focus:text-destructive"
                >
                  <XCircle className="mr-2 h-4 w-4" />
                  Reject
                </DropdownMenuItem>
              </>
            )}
            {row.original.status === 'APPROVED' && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => postMutation.mutate(row.original.id)}>
                  <FileCheck className="mr-2 h-4 w-4 text-blue-600" />
                  Post to Ledger
                </DropdownMenuItem>
              </>
            )}
            {row.original.status === 'POSTED' && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => handleReverse(row.original)}>
                  <RotateCcw className="mr-2 h-4 w-4 text-orange-600" />
                  Reverse Entry
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => window.open(`/dashboard/finance/general-ledger?entry=${row.original.id}`, '_blank')}>
                  <BookMarked className="mr-2 h-4 w-4 text-purple-600" />
                  View in Ledger
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  // API returns array directly, not { items: [...] }
  const accounts = Array.isArray(accountsData) ? accountsData : [];
  const { totalDebit, totalCredit, isBalanced } = getTotals();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Journal Entries"
        description="Record and manage accounting journal entries"
        actions={
          <div className="flex items-center gap-2">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="DRAFT">Draft</SelectItem>
                <SelectItem value="PENDING_APPROVAL">Pending</SelectItem>
                <SelectItem value="APPROVED">Approved</SelectItem>
                <SelectItem value="POSTED">Posted</SelectItem>
                <SelectItem value="REJECTED">Rejected</SelectItem>
              </SelectContent>
            </Select>
            <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
              <DialogTrigger asChild>
                <Button onClick={() => setIsDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  New Journal Entry
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>{isEditMode ? 'Edit Journal Entry' : 'Create Journal Entry'}</DialogTitle>
                  <DialogDescription>
                    {isEditMode
                      ? 'Modify the draft journal entry details and lines'
                      : 'Record a new accounting journal entry with debit and credit lines'}
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>Entry Date *</Label>
                      <Input
                        type="date"
                        value={formData.entry_date}
                        onChange={(e) => setFormData({ ...formData, entry_date: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Entry Type</Label>
                      <Select
                        value={formData.entry_type}
                        onValueChange={(value) => setFormData({ ...formData, entry_type: value })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="MANUAL">Manual</SelectItem>
                          <SelectItem value="ADJUSTMENT">Adjustment</SelectItem>
                          <SelectItem value="CLOSING">Closing</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Reference #</Label>
                      <Input
                        placeholder="Invoice #, Receipt #, etc."
                        value={formData.source_number}
                        onChange={(e) => setFormData({ ...formData, source_number: e.target.value })}
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Narration *</Label>
                    <Textarea
                      placeholder="Description of this journal entry"
                      value={formData.narration}
                      onChange={(e) => setFormData({ ...formData, narration: e.target.value })}
                    />
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label className="text-base font-medium">Entry Lines</Label>
                      <Button type="button" variant="outline" size="sm" onClick={addLine}>
                        <Plus className="mr-1 h-3 w-3" /> Add Line
                      </Button>
                    </div>

                    <div className="grid gap-2 text-xs font-medium text-muted-foreground px-1" style={{ gridTemplateColumns: '1fr 150px 100px 100px 40px' }}>
                      <div>Account</div>
                      <div>Description</div>
                      <div className="text-right">Debit</div>
                      <div className="text-right">Credit</div>
                      <div></div>
                    </div>

                    {formData.lines.map((line, idx) => (
                      <div key={idx} className="grid gap-2 items-center" style={{ gridTemplateColumns: '1fr 150px 100px 100px 40px' }}>
                        <div className="min-w-0">
                          <Select
                            value={line.account_id || 'select'}
                            onValueChange={(value) => updateLine(idx, 'account_id', value === 'select' ? '' : value)}
                          >
                            <SelectTrigger className="h-9 w-full">
                              <SelectValue placeholder="Select account" className="truncate" />
                            </SelectTrigger>
                            <SelectContent className="max-w-[400px]">
                              <SelectItem value="select" disabled>Select account</SelectItem>
                              {accounts
                                .filter((acc: Account) => acc.id && acc.id.trim() !== '')
                                .map((acc: Account) => (
                                  <SelectItem key={acc.id} value={acc.id}>
                                    <span className="truncate">{acc.code} - {acc.name}</span>
                                  </SelectItem>
                                ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Input
                            className="h-9 w-full"
                            placeholder="Line descript"
                            value={line.description || ''}
                            onChange={(e) => updateLine(idx, 'description', e.target.value)}
                          />
                        </div>
                        <div>
                          <Input
                            className="h-9 w-full text-right"
                            type="number"
                            min="0"
                            step="0.01"
                            placeholder="0.00"
                            value={line.debit_amount || ''}
                            onChange={(e) => updateLine(idx, 'debit_amount', parseFloat(e.target.value) || 0)}
                          />
                        </div>
                        <div>
                          <Input
                            className="h-9 w-full text-right"
                            type="number"
                            min="0"
                            step="0.01"
                            placeholder="0.00"
                            value={line.credit_amount || ''}
                            onChange={(e) => updateLine(idx, 'credit_amount', parseFloat(e.target.value) || 0)}
                          />
                        </div>
                        <div className="flex justify-center">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => removeLine(idx)}
                            disabled={formData.lines.length <= 2}
                          >
                            <Trash2 className="h-4 w-4 text-muted-foreground" />
                          </Button>
                        </div>
                      </div>
                    ))}

                    <Separator />

                    <div className="grid gap-2 items-center font-medium" style={{ gridTemplateColumns: '1fr 150px 100px 100px 40px' }}>
                      <div className="text-right">Totals:</div>
                      <div></div>
                      <div className={`text-right ${isBalanced ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(totalDebit)}
                      </div>
                      <div className={`text-right ${isBalanced ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(totalCredit)}
                      </div>
                      <div></div>
                    </div>

                    {!isBalanced && totalDebit !== totalCredit && (
                      <div className="text-sm text-red-600 text-center">
                        Difference: {formatCurrency(Math.abs(totalDebit - totalCredit))}
                      </div>
                    )}
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={resetForm}>Cancel</Button>
                  <Button
                    onClick={handleSubmit}
                    disabled={createMutation.isPending || updateMutation.isPending || !isBalanced}
                  >
                    {(createMutation.isPending || updateMutation.isPending) && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    {isEditMode ? 'Update Draft' : 'Save as Draft'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="entry_number"
        searchPlaceholder="Search entries..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Entry Detail Sheet */}
      <Sheet open={isViewOpen} onOpenChange={setIsViewOpen}>
        <SheetContent className="w-[600px] sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              {selectedEntry?.entry_number}
            </SheetTitle>
            <SheetDescription>Journal entry details and workflow</SheetDescription>
          </SheetHeader>
          {selectedEntry && (
            <div className="mt-6 space-y-6">
              <div className="flex items-center gap-3">
                <StatusBadge status={selectedEntry.status} />
                <span className="text-sm text-muted-foreground">
                  {formatDate(selectedEntry.entry_date)}
                </span>
              </div>

              {selectedEntry.source_number && (
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Reference</div>
                    <div className="font-mono">{selectedEntry.source_number}</div>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardContent className="pt-4">
                  <div className="text-xs text-muted-foreground">Narration</div>
                  <div className="text-sm mt-1">{selectedEntry.narration}</div>
                </CardContent>
              </Card>

              {selectedEntry.lines && selectedEntry.lines.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Entry Lines</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {selectedEntry.lines.map((line, idx) => (
                        <div key={idx} className="flex justify-between items-center text-sm py-2 border-b last:border-0">
                          <div>
                            <div className="font-medium">{line.account?.code} - {line.account?.name}</div>
                            {line.description && (
                              <div className="text-xs text-muted-foreground">{line.description}</div>
                            )}
                          </div>
                          <div className="text-right">
                            {line.debit_amount > 0 && (
                              <div className="text-green-600">{formatCurrency(line.debit_amount)} Dr</div>
                            )}
                            {line.credit_amount > 0 && (
                              <div className="text-blue-600">{formatCurrency(line.credit_amount)} Cr</div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              <div className="grid grid-cols-2 gap-4">
                <Card className="bg-green-50">
                  <CardContent className="pt-4">
                    <div className="text-xs text-green-600">Total Debit</div>
                    <div className="text-xl font-bold text-green-700">
                      {formatCurrency(selectedEntry.total_debit)}
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-blue-50">
                  <CardContent className="pt-4">
                    <div className="text-xs text-blue-600">Total Credit</div>
                    <div className="text-xl font-bold text-blue-700">
                      {formatCurrency(selectedEntry.total_credit)}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {selectedEntry.rejection_reason && (
                <Card className="bg-red-50">
                  <CardContent className="pt-4">
                    <div className="text-xs text-red-600">Rejection Reason</div>
                    <div className="text-sm text-red-700">{selectedEntry.rejection_reason}</div>
                  </CardContent>
                </Card>
              )}

              {selectedEntry.created_by && (
                <div className="text-xs text-muted-foreground">
                  Created by: {selectedEntry.created_by.full_name}
                </div>
              )}

              {/* Workflow Actions */}
              <Separator />
              <div className="flex flex-wrap gap-2">
                {selectedEntry.status === 'DRAFT' && (
                  <Button
                    onClick={() => submitMutation.mutate(selectedEntry.id)}
                    disabled={submitMutation.isPending}
                  >
                    {submitMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
                    Submit for Approval
                  </Button>
                )}

                {selectedEntry.status === 'PENDING_APPROVAL' && (
                  <>
                    <Button
                      onClick={() => approveMutation.mutate(selectedEntry.id)}
                      disabled={approveMutation.isPending}
                    >
                      {approveMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle className="mr-2 h-4 w-4" />}
                      Approve
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={() => setIsRejectDialogOpen(true)}
                    >
                      <XCircle className="mr-2 h-4 w-4" />
                      Reject
                    </Button>
                  </>
                )}

                {selectedEntry.status === 'APPROVED' && (
                  <Button
                    onClick={() => postMutation.mutate(selectedEntry.id)}
                    disabled={postMutation.isPending}
                  >
                    {postMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileCheck className="mr-2 h-4 w-4" />}
                    Post to Ledger
                  </Button>
                )}

                {selectedEntry.status === 'REJECTED' && (
                  <div className="text-sm text-muted-foreground">
                    Entry was rejected. Create a new entry to proceed.
                  </div>
                )}

                {selectedEntry.status === 'POSTED' && (
                  <div className="text-sm text-green-600 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    Entry has been posted to the general ledger
                  </div>
                )}
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Rejection Dialog */}
      <AlertDialog open={isRejectDialogOpen} onOpenChange={setIsRejectDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject Journal Entry</AlertDialogTitle>
            <AlertDialogDescription>
              Please provide a reason for rejecting this journal entry.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Enter rejection reason..."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => selectedEntry && rejectMutation.mutate({ id: selectedEntry.id, reason: rejectionReason })}
              disabled={!rejectionReason.trim() || rejectMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {rejectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Reject Entry
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Journal Entry</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete journal entry{' '}
              <span className="font-medium">{entryToDelete?.entry_number}</span>?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete Entry
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reverse Entry Dialog */}
      <AlertDialog open={isReverseDialogOpen} onOpenChange={setIsReverseDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reverse Journal Entry</AlertDialogTitle>
            <AlertDialogDescription>
              Create a reversing entry for{' '}
              <span className="font-medium">{entryToReverse?.entry_number}</span>.
              This will create a new journal entry with opposite debit/credit amounts.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-4 space-y-4">
            <div className="space-y-2">
              <Label>Reversal Date</Label>
              <Input
                type="date"
                value={reversalDate}
                onChange={(e) => setReversalDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Reason (optional)</Label>
              <Textarea
                placeholder="Reason for reversal..."
                value={reversalReason}
                onChange={(e) => setReversalReason(e.target.value)}
              />
            </div>
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmReverse}
              disabled={!reversalDate || reverseMutation.isPending}
              className="bg-orange-600 text-white hover:bg-orange-700"
            >
              {reverseMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Reversal
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
