'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { format } from 'date-fns';
import {
  ArrowLeft,
  Check,
  Download,
  FileText,
  Users,
  DollarSign,
  AlertCircle,
  CreditCard,
  Eye,
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { hrApi, PayrollRun, Payslip } from '@/lib/api';

const payrollStatuses = [
  { value: 'DRAFT', label: 'Draft', variant: 'outline' as const },
  { value: 'PROCESSING', label: 'Processing', variant: 'secondary' as const },
  { value: 'PROCESSED', label: 'Processed', variant: 'default' as const },
  { value: 'APPROVED', label: 'Approved', variant: 'default' as const },
  { value: 'PAID', label: 'Paid', variant: 'default' as const },
];

function getStatusBadge(status: string) {
  const config = payrollStatuses.find((s) => s.value === status);
  return <Badge variant={config?.variant || 'outline'}>{config?.label || status}</Badge>;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

export default function PayrollDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();

  const payrollId = params.id as string;
  const [selectedPayslip, setSelectedPayslip] = useState<Payslip | null>(null);

  // Note: We need to get payroll details - may need to add a getById endpoint
  // For now, we'll list payrolls and find the matching one
  const { data: payslipsData, isLoading } = useQuery({
    queryKey: ['payroll-payslips', payrollId],
    queryFn: () => hrApi.payroll.listPayslips({ payroll_id: payrollId, page: 1, size: 500 }),
  });

  const approveMutation = useMutation({
    mutationFn: () => hrApi.payroll.approve(payrollId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payrolls'] });
      queryClient.invalidateQueries({ queryKey: ['payroll-payslips', payrollId] });
      toast.success('Payroll approved successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Error approving payroll');
    },
  });

  const payslips = payslipsData?.items || [];

  // Calculate totals from payslips
  const totals = payslips.reduce(
    (acc, p) => ({
      employees: acc.employees + 1,
      gross: acc.gross + p.gross_earnings,
      deductions: acc.deductions + p.total_deductions,
      net: acc.net + p.net_salary,
      pf: acc.pf + p.employee_pf + p.employer_pf,
      esic: acc.esic + p.employee_esic + p.employer_esic,
      pt: acc.pt + p.professional_tax,
      tds: acc.tds + p.tds,
    }),
    { employees: 0, gross: 0, deductions: 0, net: 0, pf: 0, esic: 0, pt: 0, tds: 0 }
  );

  // Get payroll month from first payslip
  const payrollMonth = payslips[0]?.created_at ? new Date(payslips[0].created_at) : new Date();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32 mt-2" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (payslips.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" asChild>
            <Link href="/dashboard/hr/payroll">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Payroll Details</h1>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold">No Payslips Found</h2>
          <p className="text-muted-foreground">This payroll run has no payslips.</p>
          <Button className="mt-4" asChild>
            <Link href="/dashboard/hr/payroll">Back to Payroll</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" asChild>
            <Link href="/dashboard/hr/payroll">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">
                Payroll - {format(payrollMonth, 'MMMM yyyy')}
              </h1>
            </div>
            <p className="text-muted-foreground">
              {totals.employees} employees processed
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button onClick={() => approveMutation.mutate()} disabled={approveMutation.isPending}>
            <Check className="mr-2 h-4 w-4" />
            {approveMutation.isPending ? 'Approving...' : 'Approve Payroll'}
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-950 rounded-full">
                <Users className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">{totals.employees}</div>
                <div className="text-sm text-muted-foreground">Employees</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 dark:bg-green-950 rounded-full">
                <DollarSign className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">{formatCurrency(totals.gross)}</div>
                <div className="text-sm text-muted-foreground">Gross Pay</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 dark:bg-red-950 rounded-full">
                <CreditCard className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">{formatCurrency(totals.deductions)}</div>
                <div className="text-sm text-muted-foreground">Total Deductions</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-100 dark:bg-emerald-950 rounded-full">
                <DollarSign className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">{formatCurrency(totals.net)}</div>
                <div className="text-sm text-muted-foreground">Net Pay</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Statutory Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Statutory Deductions Summary</CardTitle>
          <CardDescription>Total statutory contributions for this payroll</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="p-4 bg-muted rounded-lg">
              <div className="text-sm text-muted-foreground">Provident Fund</div>
              <div className="text-xl font-semibold">{formatCurrency(totals.pf)}</div>
              <div className="text-xs text-muted-foreground">Employee + Employer</div>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <div className="text-sm text-muted-foreground">ESIC</div>
              <div className="text-xl font-semibold">{formatCurrency(totals.esic)}</div>
              <div className="text-xs text-muted-foreground">Employee + Employer</div>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <div className="text-sm text-muted-foreground">Professional Tax</div>
              <div className="text-xl font-semibold">{formatCurrency(totals.pt)}</div>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <div className="text-sm text-muted-foreground">TDS</div>
              <div className="text-xl font-semibold">{formatCurrency(totals.tds)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Payslips Table */}
      <Card>
        <CardHeader>
          <CardTitle>Payslips</CardTitle>
          <CardDescription>Individual employee payslips</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Days</TableHead>
                <TableHead>Gross</TableHead>
                <TableHead>PF</TableHead>
                <TableHead>PT</TableHead>
                <TableHead>TDS</TableHead>
                <TableHead>Net Pay</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payslips.map((payslip: Payslip) => (
                <TableRow key={payslip.id}>
                  <TableCell>
                    <div>
                      <div className="font-medium">{payslip.employee_name}</div>
                      <div className="text-sm text-muted-foreground">{payslip.employee_code}</div>
                    </div>
                  </TableCell>
                  <TableCell>{payslip.department_name || '-'}</TableCell>
                  <TableCell>
                    <span className="text-green-600">{payslip.days_present}</span>
                    <span className="text-muted-foreground">/{payslip.working_days}</span>
                  </TableCell>
                  <TableCell>{formatCurrency(payslip.gross_earnings)}</TableCell>
                  <TableCell>{formatCurrency(payslip.employee_pf)}</TableCell>
                  <TableCell>{formatCurrency(payslip.professional_tax)}</TableCell>
                  <TableCell>{formatCurrency(payslip.tds)}</TableCell>
                  <TableCell className="font-medium text-green-600">
                    {formatCurrency(payslip.net_salary)}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon" onClick={() => setSelectedPayslip(payslip)}>
                        <Eye className="h-4 w-4" />
                      </Button>
                      {payslip.payslip_pdf_url && (
                        <Button variant="ghost" size="icon" asChild>
                          <a href={payslip.payslip_pdf_url} target="_blank" rel="noopener noreferrer">
                            <FileText className="h-4 w-4" />
                          </a>
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Payslip Detail Dialog */}
      <Dialog open={!!selectedPayslip} onOpenChange={(open) => !open && setSelectedPayslip(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Payslip Details - {selectedPayslip?.payslip_number}</DialogTitle>
          </DialogHeader>
          {selectedPayslip && (
            <div className="space-y-6">
              {/* Employee Info */}
              <div className="grid gap-2 md:grid-cols-3 p-4 bg-muted rounded-lg">
                <div>
                  <div className="text-sm text-muted-foreground">Employee</div>
                  <div className="font-medium">{selectedPayslip.employee_name}</div>
                  <div className="text-sm text-muted-foreground">{selectedPayslip.employee_code}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Department</div>
                  <div>{selectedPayslip.department_name || '-'}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Designation</div>
                  <div>{selectedPayslip.designation || '-'}</div>
                </div>
              </div>

              {/* Attendance Summary */}
              <div className="grid gap-4 md:grid-cols-4">
                <div className="text-center p-3 border rounded-lg">
                  <div className="text-2xl font-bold">{selectedPayslip.working_days}</div>
                  <div className="text-sm text-muted-foreground">Working Days</div>
                </div>
                <div className="text-center p-3 border rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{selectedPayslip.days_present}</div>
                  <div className="text-sm text-muted-foreground">Present</div>
                </div>
                <div className="text-center p-3 border rounded-lg">
                  <div className="text-2xl font-bold text-red-600">{selectedPayslip.days_absent}</div>
                  <div className="text-sm text-muted-foreground">Absent</div>
                </div>
                <div className="text-center p-3 border rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{selectedPayslip.leaves_taken}</div>
                  <div className="text-sm text-muted-foreground">Leaves</div>
                </div>
              </div>

              {/* Earnings & Deductions */}
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <h4 className="font-medium mb-3">Earnings</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Basic</span>
                      <span>{formatCurrency(selectedPayslip.basic_earned)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">HRA</span>
                      <span>{formatCurrency(selectedPayslip.hra_earned)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Conveyance</span>
                      <span>{formatCurrency(selectedPayslip.conveyance_earned)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Medical</span>
                      <span>{formatCurrency(selectedPayslip.medical_earned)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Special</span>
                      <span>{formatCurrency(selectedPayslip.special_earned)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Other</span>
                      <span>{formatCurrency(selectedPayslip.other_earned)}</span>
                    </div>
                    {selectedPayslip.overtime_amount > 0 && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Overtime</span>
                        <span>{formatCurrency(selectedPayslip.overtime_amount)}</span>
                      </div>
                    )}
                    {selectedPayslip.bonus > 0 && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Bonus</span>
                        <span>{formatCurrency(selectedPayslip.bonus)}</span>
                      </div>
                    )}
                    <div className="flex justify-between border-t pt-2 font-medium">
                      <span>Gross Earnings</span>
                      <span>{formatCurrency(selectedPayslip.gross_earnings)}</span>
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="font-medium mb-3">Deductions</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">PF (Employee)</span>
                      <span className="text-red-600">-{formatCurrency(selectedPayslip.employee_pf)}</span>
                    </div>
                    {selectedPayslip.employee_esic > 0 && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">ESIC (Employee)</span>
                        <span className="text-red-600">-{formatCurrency(selectedPayslip.employee_esic)}</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Professional Tax</span>
                      <span className="text-red-600">-{formatCurrency(selectedPayslip.professional_tax)}</span>
                    </div>
                    {selectedPayslip.tds > 0 && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">TDS</span>
                        <span className="text-red-600">-{formatCurrency(selectedPayslip.tds)}</span>
                      </div>
                    )}
                    {selectedPayslip.loan_deduction > 0 && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Loan</span>
                        <span className="text-red-600">-{formatCurrency(selectedPayslip.loan_deduction)}</span>
                      </div>
                    )}
                    {selectedPayslip.other_deductions > 0 && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Other</span>
                        <span className="text-red-600">-{formatCurrency(selectedPayslip.other_deductions)}</span>
                      </div>
                    )}
                    <div className="flex justify-between border-t pt-2 font-medium">
                      <span>Total Deductions</span>
                      <span className="text-red-600">-{formatCurrency(selectedPayslip.total_deductions)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Net Pay */}
              <div className="p-4 bg-green-50 dark:bg-green-950 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="text-lg font-medium">Net Pay</span>
                  <span className="text-2xl font-bold text-green-600">
                    {formatCurrency(selectedPayslip.net_salary)}
                  </span>
                </div>
              </div>

              {/* Employer Contributions Note */}
              <div className="text-sm text-muted-foreground p-3 bg-muted rounded-lg">
                <strong>Note:</strong> Employer contributions - PF: {formatCurrency(selectedPayslip.employer_pf)},
                ESIC: {formatCurrency(selectedPayslip.employer_esic)} (not deducted from employee salary)
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
