'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { Calendar, Plus, Lock, Unlock, CheckCircle, AlertTriangle, MoreHorizontal, FileText, Download, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import { periodsApi } from '@/lib/api';
import { formatDate, formatCurrency } from '@/lib/utils';

interface FiscalPeriod {
  id: string;
  name: string;
  code: string;
  financial_year: string;
  period_type: 'MONTHLY' | 'QUARTERLY' | 'YEARLY';
  start_date: string;
  end_date: string;
  status: 'OPEN' | 'CLOSING' | 'CLOSED' | 'LOCKED';
  total_entries: number;
  pending_entries: number;
  total_debit: number;
  total_credit: number;
  closed_by?: string;
  closed_at?: string;
  is_current: boolean;
}

interface FiscalYear {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: 'ACTIVE' | 'CLOSED';
  periods_count: number;
  open_periods: number;
}

const statusColors: Record<string, string> = {
  OPEN: 'bg-green-100 text-green-800',
  CLOSING: 'bg-yellow-100 text-yellow-800',
  CLOSED: 'bg-gray-100 text-gray-800',
  LOCKED: 'bg-red-100 text-red-800',
  ACTIVE: 'bg-green-100 text-green-800',
};

const periodTypeColors: Record<string, string> = {
  MONTHLY: 'bg-blue-100 text-blue-800',
  QUARTERLY: 'bg-purple-100 text-purple-800',
  YEARLY: 'bg-orange-100 text-orange-800',
};

export default function FiscalPeriodsPage() {
  const queryClient = useQueryClient();
  const [selectedYear, setSelectedYear] = useState<string>('');
  const [periodFilter, setPeriodFilter] = useState<string>('all');
  const [isCreateYearOpen, setIsCreateYearOpen] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ type: string; periodId: string; periodName: string } | null>(null);
  const [yearForm, setYearForm] = useState({
    name: '',
    start_date: '',
    end_date: '',
  });

  const { data: yearsData, isLoading: yearsLoading } = useQuery({
    queryKey: ['fiscal-years'],
    queryFn: () => periodsApi.listYears(),
  });

  const { data: periodsData, isLoading: periodsLoading } = useQuery({
    queryKey: ['fiscal-periods', selectedYear],
    queryFn: () => periodsApi.listPeriods(selectedYear || undefined),
    enabled: true,
  });

  const createYearMutation = useMutation({
    mutationFn: periodsApi.createYear,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fiscal-years'] });
      toast.success('Fiscal year created with monthly periods');
      setIsCreateYearOpen(false);
      setYearForm({ name: '', start_date: '', end_date: '' });
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create year'),
  });

  const closePeriodMutation = useMutation({
    mutationFn: periodsApi.closePeriod,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fiscal-periods'] });
      queryClient.invalidateQueries({ queryKey: ['fiscal-years'] });
      toast.success('Period closed successfully');
      setIsConfirmOpen(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to close period'),
  });

  const reopenPeriodMutation = useMutation({
    mutationFn: periodsApi.reopenPeriod,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fiscal-periods'] });
      queryClient.invalidateQueries({ queryKey: ['fiscal-years'] });
      toast.success('Period reopened');
      setIsConfirmOpen(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to reopen period'),
  });

  const lockPeriodMutation = useMutation({
    mutationFn: periodsApi.lockPeriod,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fiscal-periods'] });
      queryClient.invalidateQueries({ queryKey: ['fiscal-years'] });
      toast.success('Period locked permanently');
      setIsConfirmOpen(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to lock period'),
  });

  const handleConfirmAction = () => {
    if (!confirmAction) return;

    switch (confirmAction.type) {
      case 'close':
        closePeriodMutation.mutate(confirmAction.periodId);
        break;
      case 'reopen':
        reopenPeriodMutation.mutate(confirmAction.periodId);
        break;
      case 'lock':
        lockPeriodMutation.mutate(confirmAction.periodId);
        break;
    }
  };

  const openConfirmDialog = (type: string, periodId: string, periodName: string) => {
    setConfirmAction({ type, periodId, periodName });
    setIsConfirmOpen(true);
  };

  const filteredPeriods = periodsData?.items?.filter((p: FiscalPeriod) => {
    if (periodFilter === 'all') return true;
    if (periodFilter === 'monthly') return p.period_type === 'MONTHLY';
    if (periodFilter === 'quarterly') return p.period_type === 'QUARTERLY';
    if (periodFilter === 'open') return p.status === 'OPEN';
    return true;
  }) ?? [];

  const columns: ColumnDef<FiscalPeriod>[] = [
    {
      accessorKey: 'name',
      header: 'Period',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Calendar className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">{row.original.name}</span>
              {row.original.is_current && (
                <Badge className="bg-blue-100 text-blue-800 text-xs">Current</Badge>
              )}
            </div>
            <div className="text-xs text-muted-foreground">{row.original.code}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'period_type',
      header: 'Type',
      cell: ({ row }) => (
        <Badge className={periodTypeColors[row.original.period_type]}>
          {row.original.period_type}
        </Badge>
      ),
    },
    {
      accessorKey: 'dates',
      header: 'Date Range',
      cell: ({ row }) => (
        <div className="text-sm">
          <div>{formatDate(row.original.start_date)}</div>
          <div className="text-muted-foreground">to {formatDate(row.original.end_date)}</div>
        </div>
      ),
    },
    {
      accessorKey: 'entries',
      header: 'Entries',
      cell: ({ row }) => (
        <div className="text-sm">
          <div className="font-medium">{row.original.total_entries} entries</div>
          {row.original.pending_entries > 0 && (
            <div className="text-xs text-orange-600">
              {row.original.pending_entries} pending
            </div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'balance',
      header: 'Balance',
      cell: ({ row }) => {
        const isBalanced = row.original.total_debit === row.original.total_credit;
        return (
          <div className="text-sm">
            <div className="flex items-center gap-1">
              {isBalanced ? (
                <CheckCircle className="h-3 w-3 text-green-500" />
              ) : (
                <AlertTriangle className="h-3 w-3 text-red-500" />
              )}
              <span className={isBalanced ? 'text-green-600' : 'text-red-600'}>
                {isBalanced ? 'Balanced' : 'Unbalanced'}
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              Dr: {formatCurrency(row.original.total_debit)}
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <div className="space-y-1">
          <Badge className={statusColors[row.original.status]}>
            {row.original.status}
          </Badge>
          {row.original.closed_at && (
            <div className="text-xs text-muted-foreground">
              {formatDate(row.original.closed_at)}
            </div>
          )}
        </div>
      ),
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
            <DropdownMenuItem>
              <FileText className="mr-2 h-4 w-4" />
              View Entries
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Download className="mr-2 h-4 w-4" />
              Export Report
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {row.original.status === 'OPEN' && (
              <DropdownMenuItem
                onClick={() => openConfirmDialog('close', row.original.id, row.original.name)}
                disabled={row.original.pending_entries > 0}
              >
                <Lock className="mr-2 h-4 w-4" />
                Close Period
              </DropdownMenuItem>
            )}
            {row.original.status === 'CLOSED' && (
              <>
                <DropdownMenuItem
                  onClick={() => openConfirmDialog('reopen', row.original.id, row.original.name)}
                >
                  <Unlock className="mr-2 h-4 w-4" />
                  Reopen Period
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => openConfirmDialog('lock', row.original.id, row.original.name)}
                  className="text-red-600"
                >
                  <Lock className="mr-2 h-4 w-4" />
                  Lock Permanently
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const years = yearsData?.items ?? [];
  const activeYear = years.find((y: FiscalYear) => y.id === selectedYear) || years[0];

  // Auto-select first year if none selected
  if (!selectedYear && years.length > 0 && !yearsLoading) {
    setSelectedYear(years[0].id);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Financial Periods"
        description="Manage fiscal years and accounting periods"
        actions={
          <Button onClick={() => setIsCreateYearOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Fiscal Year
          </Button>
        }
      />

      {/* Create Fiscal Year Dialog */}
      <Dialog open={isCreateYearOpen} onOpenChange={setIsCreateYearOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Fiscal Year</DialogTitle>
            <DialogDescription>
              Create a new fiscal year. Monthly periods will be generated automatically.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Year Name</Label>
              <Input
                id="name"
                placeholder="FY 2025-26"
                value={yearForm.name}
                onChange={(e) => setYearForm({ ...yearForm, name: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="start">Start Date</Label>
                <Input
                  id="start"
                  type="date"
                  value={yearForm.start_date}
                  onChange={(e) => setYearForm({ ...yearForm, start_date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end">End Date</Label>
                <Input
                  id="end"
                  type="date"
                  value={yearForm.end_date}
                  onChange={(e) => setYearForm({ ...yearForm, end_date: e.target.value })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateYearOpen(false)}>Cancel</Button>
            <Button
              onClick={() => createYearMutation.mutate(yearForm)}
              disabled={createYearMutation.isPending || !yearForm.name || !yearForm.start_date || !yearForm.end_date}
            >
              {createYearMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Year
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Fiscal Years */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {years.map((year: FiscalYear) => (
          <Card
            key={year.id}
            className={`cursor-pointer transition-all ${selectedYear === year.id ? 'ring-2 ring-primary' : 'hover:shadow-md'}`}
            onClick={() => setSelectedYear(year.id)}
          >
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">{year.name}</CardTitle>
                <Badge className={statusColors[year.status]}>{year.status}</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-xs text-muted-foreground mb-2">
                {formatDate(year.start_date)} - {formatDate(year.end_date)}
              </div>
              <div className="flex justify-between text-sm">
                <span>{year.periods_count} periods</span>
                <span className={year.open_periods > 0 ? 'text-green-600 font-medium' : 'text-muted-foreground'}>
                  {year.open_periods} open
                </span>
              </div>
            </CardContent>
          </Card>
        ))}

        {years.length === 0 && !yearsLoading && (
          <Card className="col-span-full py-12 text-center text-muted-foreground">
            <CardContent>
              <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No fiscal years created yet.</p>
              <p className="text-sm">Click "New Fiscal Year" to get started.</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Current Year Stats */}
      {activeYear && (
        <Card>
          <CardHeader>
            <CardTitle>{activeYear.name} Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-4">
              <div>
                <div className="text-sm text-muted-foreground">Total Periods</div>
                <div className="text-2xl font-bold">{activeYear.periods_count}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Open Periods</div>
                <div className="text-2xl font-bold text-green-600">{activeYear.open_periods}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Closed Periods</div>
                <div className="text-2xl font-bold">{activeYear.periods_count - activeYear.open_periods}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground mb-1">Progress</div>
                <Progress
                  value={activeYear.periods_count > 0 ? ((activeYear.periods_count - activeYear.open_periods) / activeYear.periods_count) * 100 : 0}
                  className="h-2"
                />
                <div className="text-xs text-muted-foreground mt-1">
                  {activeYear.periods_count > 0
                    ? Math.round(((activeYear.periods_count - activeYear.open_periods) / activeYear.periods_count) * 100)
                    : 0}% complete
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Period Filters */}
      <div className="flex items-center gap-4">
        <Select value={periodFilter} onValueChange={setPeriodFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter periods" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Periods</SelectItem>
            <SelectItem value="monthly">Monthly Only</SelectItem>
            <SelectItem value="quarterly">Quarterly Only</SelectItem>
            <SelectItem value="open">Open Only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Periods Table */}
      <DataTable<FiscalPeriod, unknown>
        columns={columns}
        data={filteredPeriods}
        searchKey="name"
        searchPlaceholder="Search periods..."
        isLoading={periodsLoading}
      />

      {/* Confirmation Dialog */}
      <AlertDialog open={isConfirmOpen} onOpenChange={setIsConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmAction?.type === 'close' && 'Close Period'}
              {confirmAction?.type === 'reopen' && 'Reopen Period'}
              {confirmAction?.type === 'lock' && 'Lock Period Permanently'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction?.type === 'close' && (
                <>Are you sure you want to close <strong>{confirmAction.periodName}</strong>? No new journal entries can be posted to this period after closing.</>
              )}
              {confirmAction?.type === 'reopen' && (
                <>Are you sure you want to reopen <strong>{confirmAction.periodName}</strong>? This will allow new journal entries to be posted.</>
              )}
              {confirmAction?.type === 'lock' && (
                <>
                  <span className="text-red-600 font-medium">Warning:</span> This action is irreversible. Are you sure you want to permanently lock <strong>{confirmAction.periodName}</strong>? This period cannot be reopened after locking.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmAction}
              className={confirmAction?.type === 'lock' ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90' : ''}
              disabled={closePeriodMutation.isPending || reopenPeriodMutation.isPending || lockPeriodMutation.isPending}
            >
              {(closePeriodMutation.isPending || reopenPeriodMutation.isPending || lockPeriodMutation.isPending) && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {confirmAction?.type === 'close' && 'Close Period'}
              {confirmAction?.type === 'reopen' && 'Reopen Period'}
              {confirmAction?.type === 'lock' && 'Lock Permanently'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
