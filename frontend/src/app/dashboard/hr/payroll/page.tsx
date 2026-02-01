'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { format } from 'date-fns';
import {
  CreditCard,
  DollarSign,
  Users,
  Check,
  Eye,
  Play,
  Plus,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
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
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { hrApi, PayrollRun } from '@/lib/api';

const payrollStatuses = [
  { value: 'DRAFT', label: 'Draft', variant: 'outline' as const },
  { value: 'PROCESSING', label: 'Processing', variant: 'secondary' as const },
  { value: 'PROCESSED', label: 'Processed', variant: 'default' as const },
  { value: 'APPROVED', label: 'Approved', variant: 'default' as const },
  { value: 'PAID', label: 'Paid', variant: 'default' as const },
];

function getStatusBadge(status: string) {
  const config = payrollStatuses.find((s) => s.value === status);
  return (
    <Badge variant={config?.variant || 'outline'}>
      {config?.label || status}
    </Badge>
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

function getFinancialYear(date: Date = new Date()): string {
  const year = date.getFullYear();
  const month = date.getMonth();
  if (month >= 3) {
    return `${year}-${(year + 1).toString().slice(-2)}`;
  }
  return `${year - 1}-${year.toString().slice(-2)}`;
}

export default function PayrollPage() {
  const [fyFilter, setFyFilter] = useState<string>(getFinancialYear());
  const [page, setPage] = useState(1);
  const [isProcessOpen, setIsProcessOpen] = useState(false);
  const [processMonth, setProcessMonth] = useState(format(new Date(), 'yyyy-MM'));
  const pageSize = 20;

  const queryClient = useQueryClient();

  const { data: payrollData, isLoading } = useQuery({
    queryKey: ['payrolls', page, fyFilter],
    queryFn: () =>
      hrApi.payroll.list({
        page,
        size: pageSize,
        financial_year: fyFilter || undefined,
      }),
  });

  const processMutation = useMutation({
    mutationFn: (data: { payroll_month: string; financial_year: string }) =>
      hrApi.payroll.process(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payrolls'] });
      queryClient.invalidateQueries({ queryKey: ['hr-dashboard'] });
      setIsProcessOpen(false);
      toast.success('Payroll processed successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Error processing payroll');
    },
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => hrApi.payroll.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payrolls'] });
      queryClient.invalidateQueries({ queryKey: ['hr-dashboard'] });
      toast.success('Payroll approved successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Error approving payroll');
    },
  });

  const handleProcess = () => {
    const monthDate = new Date(processMonth + '-01');
    const fy = getFinancialYear(monthDate);
    processMutation.mutate({
      payroll_month: processMonth + '-01',
      financial_year: fy,
    });
  };

  const payrolls = payrollData?.items || [];
  const totalPages = payrollData?.pages || 1;

  // Financial years dropdown
  const currentYear = new Date().getFullYear();
  const financialYears = Array.from({ length: 5 }, (_, i) => {
    const year = currentYear - i;
    return `${year}-${(year + 1).toString().slice(-2)}`;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Payroll</h1>
          <p className="text-muted-foreground">
            Process and manage monthly payroll
          </p>
        </div>
        <Dialog open={isProcessOpen} onOpenChange={setIsProcessOpen}>
          <DialogTrigger asChild>
            <Button>
              <Play className="mr-2 h-4 w-4" />
              Process Payroll
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Process Monthly Payroll</DialogTitle>
              <DialogDescription>
                Process payroll for all active employees for the selected month
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label>Payroll Month</Label>
                <Input
                  type="month"
                  value={processMonth}
                  onChange={(e) => setProcessMonth(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsProcessOpen(false)}>Cancel</Button>
              <Button onClick={handleProcess} disabled={processMutation.isPending}>
                {processMutation.isPending ? 'Processing...' : 'Process Payroll'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <Select value={fyFilter} onValueChange={(value) => { setFyFilter(value); setPage(1); }}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Financial Year" />
              </SelectTrigger>
              <SelectContent>
                {financialYears.map((fy) => (
                  <SelectItem key={fy} value={fy}>
                    FY {fy}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Payroll Runs Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Payroll Month</TableHead>
                <TableHead>FY</TableHead>
                <TableHead>Employees</TableHead>
                <TableHead>Gross</TableHead>
                <TableHead>Deductions</TableHead>
                <TableHead>Net Pay</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-[120px]">Actions</TableHead>
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
              ) : payrolls.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <CreditCard className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="font-medium">No payroll runs</h3>
                    <p className="text-sm text-muted-foreground">Process your first payroll to get started</p>
                  </TableCell>
                </TableRow>
              ) : (
                payrolls.map((payroll: PayrollRun) => (
                  <TableRow key={payroll.id}>
                    <TableCell className="font-medium">
                      {payroll.payroll_month
                        ? format(new Date(payroll.payroll_month), 'MMMM yyyy')
                        : '-'}
                    </TableCell>
                    <TableCell>{payroll.financial_year}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-muted-foreground" />
                        {payroll.total_employees}
                      </div>
                    </TableCell>
                    <TableCell>{formatCurrency(payroll.total_gross)}</TableCell>
                    <TableCell className="text-red-600">
                      -{formatCurrency(payroll.total_deductions)}
                    </TableCell>
                    <TableCell className="font-medium text-green-600">
                      {formatCurrency(payroll.total_net)}
                    </TableCell>
                    <TableCell>{getStatusBadge(payroll.status)}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="ghost" size="icon" asChild>
                          <Link href={`/dashboard/hr/payroll/${payroll.id}`}>
                            <Eye className="h-4 w-4" />
                          </Link>
                        </Button>
                        {payroll.status === 'PROCESSED' && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => approveMutation.mutate(payroll.id)}
                            disabled={approveMutation.isPending}
                          >
                            <Check className="h-4 w-4 text-green-600" />
                          </Button>
                        )}
                      </div>
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
    </div>
  );
}
