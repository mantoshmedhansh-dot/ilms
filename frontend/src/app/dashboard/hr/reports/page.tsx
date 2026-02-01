'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  FileText,
  Download,
  Building2,
  Users,
  IndianRupee,
  FileSpreadsheet,
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { hrApi, PFReportItem, ESICReportItem, SalaryRegisterResponse } from '@/lib/api';

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

function downloadCSV(data: Record<string, unknown>[], filename: string) {
  if (data.length === 0) {
    toast.error('No data to download');
    return;
  }

  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map(row =>
      headers.map(header => {
        const value = row[header];
        // Escape commas and quotes in values
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value ?? '';
      }).join(',')
    )
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}_${format(new Date(), 'yyyy-MM-dd')}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
  toast.success('Report downloaded successfully');
}

export default function HRReportsPage() {
  const [selectedMonth, setSelectedMonth] = useState(format(new Date(), 'yyyy-MM'));
  const [selectedDepartment, setSelectedDepartment] = useState<string>('');
  const [activeTab, setActiveTab] = useState('salary-register');

  const payrollMonth = selectedMonth + '-01';

  // Fetch departments for filter
  const { data: departments } = useQuery({
    queryKey: ['departments-dropdown'],
    queryFn: hrApi.departments.dropdown,
  });

  // Fetch PF ECR Report
  const { data: pfReport, isLoading: pfLoading } = useQuery({
    queryKey: ['pf-ecr-report', payrollMonth, selectedDepartment],
    queryFn: () => hrApi.reports.getPFECR({
      payroll_month: payrollMonth,
      department_id: selectedDepartment || undefined,
    }),
    enabled: activeTab === 'pf-ecr',
  });

  // Fetch ESIC Report
  const { data: esicReport, isLoading: esicLoading } = useQuery({
    queryKey: ['esic-report', payrollMonth, selectedDepartment],
    queryFn: () => hrApi.reports.getESIC({
      payroll_month: payrollMonth,
      department_id: selectedDepartment || undefined,
    }),
    enabled: activeTab === 'esic',
  });

  // Fetch Salary Register
  const { data: salaryRegister, isLoading: salaryLoading } = useQuery({
    queryKey: ['salary-register', payrollMonth, selectedDepartment],
    queryFn: () => hrApi.reports.getSalaryRegister({
      payroll_month: payrollMonth,
      department_id: selectedDepartment || undefined,
    }),
    enabled: activeTab === 'salary-register',
  });

  const handleDownloadPF = () => {
    if (!pfReport || pfReport.length === 0) {
      toast.error('No PF data available for download');
      return;
    }
    const csvData = pfReport.map(item => ({
      'UAN': item.uan_number || '',
      'Employee Code': item.employee_code,
      'Employee Name': item.employee_name,
      'Gross Wages': item.gross_wages,
      'EPF Wages': item.epf_wages,
      'EPS Wages': item.eps_wages,
      'EDLI Wages': item.edli_wages,
      'EPF (EE)': item.epf_contribution_employee,
      'EPF (ER)': item.epf_contribution_employer,
      'EPS': item.eps_contribution,
      'EDLI': item.edli_contribution,
      'NCP Days': item.ncp_days,
    }));
    downloadCSV(csvData as Record<string, unknown>[], `PF_ECR_${selectedMonth}`);
  };

  const handleDownloadESIC = () => {
    if (!esicReport || esicReport.length === 0) {
      toast.error('No ESIC data available for download');
      return;
    }
    const csvData = esicReport.map(item => ({
      'ESIC Number': item.esic_number || '',
      'Employee Code': item.employee_code,
      'Employee Name': item.employee_name,
      'Gross Wages': item.gross_wages,
      'Employee Contribution': item.employee_contribution,
      'Employer Contribution': item.employer_contribution,
      'Total Contribution': item.total_contribution,
      'Days Worked': item.days_worked,
    }));
    downloadCSV(csvData as Record<string, unknown>[], `ESIC_${selectedMonth}`);
  };

  const handleDownloadSalaryRegister = () => {
    if (!salaryRegister || salaryRegister.employees.length === 0) {
      toast.error('No salary data available for download');
      return;
    }
    const csvData = salaryRegister.employees.map(emp => ({
      'Employee Code': emp.employee_code,
      'Employee Name': emp.employee_name,
      'Department': emp.department || '',
      'Designation': emp.designation || '',
      'PAN': emp.pan_number || '',
      'Bank Name': emp.bank_name || '',
      'Account No': emp.bank_account || '',
      'IFSC': emp.ifsc_code || '',
      'Working Days': emp.working_days,
      'Days Present': emp.days_present,
      'Days Absent': emp.days_absent,
      'Leaves': emp.leaves_taken,
      'Basic': emp.basic,
      'HRA': emp.hra,
      'Conveyance': emp.conveyance,
      'Medical': emp.medical,
      'Special': emp.special,
      'Other Earnings': emp.other_earnings,
      'Gross': emp.gross_earnings,
      'PF (EE)': emp.employee_pf,
      'ESIC (EE)': emp.employee_esic,
      'PT': emp.professional_tax,
      'TDS': emp.tds,
      'Loan': emp.loan_deduction,
      'Advance': emp.advance_deduction,
      'Other Deductions': emp.other_deductions,
      'Total Deductions': emp.total_deductions,
      'Net Salary': emp.net_salary,
    }));
    downloadCSV(csvData as Record<string, unknown>[], `Salary_Register_${selectedMonth}`);
  };

  // Calculate totals for PF report
  const pfTotals = pfReport?.reduce((acc, item) => ({
    gross_wages: acc.gross_wages + item.gross_wages,
    epf_wages: acc.epf_wages + item.epf_wages,
    epf_employee: acc.epf_employee + item.epf_contribution_employee,
    epf_employer: acc.epf_employer + item.epf_contribution_employer,
    eps: acc.eps + item.eps_contribution,
    edli: acc.edli + item.edli_contribution,
  }), { gross_wages: 0, epf_wages: 0, epf_employee: 0, epf_employer: 0, eps: 0, edli: 0 });

  // Calculate totals for ESIC report
  const esicTotals = esicReport?.reduce((acc, item) => ({
    gross_wages: acc.gross_wages + item.gross_wages,
    employee_contribution: acc.employee_contribution + item.employee_contribution,
    employer_contribution: acc.employer_contribution + item.employer_contribution,
    total_contribution: acc.total_contribution + item.total_contribution,
  }), { gross_wages: 0, employee_contribution: 0, employer_contribution: 0, total_contribution: 0 });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">HR Reports</h1>
          <p className="text-muted-foreground">
            Generate statutory compliance reports
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end">
            <div className="grid gap-2">
              <Label>Payroll Month</Label>
              <Input
                type="month"
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="w-[180px]"
              />
            </div>
            <div className="grid gap-2">
              <Label>Department</Label>
              <Select
                value={selectedDepartment}
                onValueChange={setSelectedDepartment}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="All Departments" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Departments</SelectItem>
                  {departments?.map((dept) => (
                    <SelectItem key={dept.id} value={dept.id}>
                      {dept.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Report Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="salary-register" className="flex items-center gap-2">
            <FileSpreadsheet className="h-4 w-4" />
            Salary Register
          </TabsTrigger>
          <TabsTrigger value="pf-ecr" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            PF ECR
          </TabsTrigger>
          <TabsTrigger value="esic" className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            ESIC
          </TabsTrigger>
        </TabsList>

        {/* Salary Register Tab */}
        <TabsContent value="salary-register" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Salary Register</CardTitle>
                <CardDescription>
                  Detailed salary breakdown for {format(new Date(payrollMonth), 'MMMM yyyy')}
                </CardDescription>
              </div>
              <Button onClick={handleDownloadSalaryRegister} disabled={!salaryRegister?.employees.length}>
                <Download className="mr-2 h-4 w-4" />
                Download CSV
              </Button>
            </CardHeader>
            <CardContent>
              {/* Summary Cards */}
              {salaryRegister && (
                <div className="grid gap-4 md:grid-cols-5 mb-6">
                  <Card>
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">Employees</span>
                      </div>
                      <p className="text-2xl font-bold">{salaryRegister.total_employees}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2">
                        <IndianRupee className="h-4 w-4 text-green-600" />
                        <span className="text-sm text-muted-foreground">Total Gross</span>
                      </div>
                      <p className="text-2xl font-bold text-green-600">
                        {formatCurrency(salaryRegister.summary.total_gross)}
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2">
                        <IndianRupee className="h-4 w-4 text-red-600" />
                        <span className="text-sm text-muted-foreground">Total Deductions</span>
                      </div>
                      <p className="text-2xl font-bold text-red-600">
                        {formatCurrency(salaryRegister.summary.total_deductions)}
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2">
                        <IndianRupee className="h-4 w-4 text-blue-600" />
                        <span className="text-sm text-muted-foreground">Net Payable</span>
                      </div>
                      <p className="text-2xl font-bold text-blue-600">
                        {formatCurrency(salaryRegister.summary.total_net)}
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-purple-600" />
                        <span className="text-sm text-muted-foreground">Total PF</span>
                      </div>
                      <p className="text-2xl font-bold text-purple-600">
                        {formatCurrency(salaryRegister.summary.total_pf)}
                      </p>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Table */}
              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky left-0 bg-background">Employee</TableHead>
                      <TableHead>Dept</TableHead>
                      <TableHead className="text-right">Days</TableHead>
                      <TableHead className="text-right">Basic</TableHead>
                      <TableHead className="text-right">HRA</TableHead>
                      <TableHead className="text-right">Other</TableHead>
                      <TableHead className="text-right">Gross</TableHead>
                      <TableHead className="text-right">PF</TableHead>
                      <TableHead className="text-right">ESIC</TableHead>
                      <TableHead className="text-right">PT</TableHead>
                      <TableHead className="text-right">TDS</TableHead>
                      <TableHead className="text-right">Deductions</TableHead>
                      <TableHead className="text-right font-bold">Net</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {salaryLoading ? (
                      Array.from({ length: 5 }).map((_, i) => (
                        <TableRow key={i}>
                          {Array.from({ length: 13 }).map((_, j) => (
                            <TableCell key={j}><Skeleton className="h-4 w-16" /></TableCell>
                          ))}
                        </TableRow>
                      ))
                    ) : !salaryRegister?.employees.length ? (
                      <TableRow>
                        <TableCell colSpan={13} className="text-center py-8">
                          <FileSpreadsheet className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                          <h3 className="font-medium">No salary data</h3>
                          <p className="text-sm text-muted-foreground">
                            No payroll processed for {format(new Date(payrollMonth), 'MMMM yyyy')}
                          </p>
                        </TableCell>
                      </TableRow>
                    ) : (
                      salaryRegister.employees.map((emp) => (
                        <TableRow key={emp.employee_id}>
                          <TableCell className="sticky left-0 bg-background">
                            <div>
                              <div className="font-medium">{emp.employee_name}</div>
                              <div className="text-xs text-muted-foreground">{emp.employee_code}</div>
                            </div>
                          </TableCell>
                          <TableCell className="text-xs">{emp.department || '-'}</TableCell>
                          <TableCell className="text-right">{emp.days_present}/{emp.working_days}</TableCell>
                          <TableCell className="text-right">{formatCurrency(emp.basic)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(emp.hra)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(emp.conveyance + emp.medical + emp.special + emp.other_earnings)}</TableCell>
                          <TableCell className="text-right font-medium">{formatCurrency(emp.gross_earnings)}</TableCell>
                          <TableCell className="text-right text-red-600">{formatCurrency(emp.employee_pf)}</TableCell>
                          <TableCell className="text-right text-red-600">{formatCurrency(emp.employee_esic)}</TableCell>
                          <TableCell className="text-right text-red-600">{formatCurrency(emp.professional_tax)}</TableCell>
                          <TableCell className="text-right text-red-600">{formatCurrency(emp.tds)}</TableCell>
                          <TableCell className="text-right text-red-600">{formatCurrency(emp.total_deductions)}</TableCell>
                          <TableCell className="text-right font-bold text-green-600">{formatCurrency(emp.net_salary)}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* PF ECR Tab */}
        <TabsContent value="pf-ecr" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>PF ECR Report</CardTitle>
                <CardDescription>
                  Electronic Challan cum Return for {format(new Date(payrollMonth), 'MMMM yyyy')}
                </CardDescription>
              </div>
              <Button onClick={handleDownloadPF} disabled={!pfReport?.length}>
                <Download className="mr-2 h-4 w-4" />
                Download CSV
              </Button>
            </CardHeader>
            <CardContent>
              {/* Summary */}
              {pfTotals && pfReport && pfReport.length > 0 && (
                <div className="grid gap-4 md:grid-cols-4 mb-6">
                  <Card>
                    <CardContent className="pt-4">
                      <span className="text-sm text-muted-foreground">Total EPF Wages</span>
                      <p className="text-xl font-bold">{formatCurrency(pfTotals.epf_wages)}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <span className="text-sm text-muted-foreground">Employee EPF (12%)</span>
                      <p className="text-xl font-bold">{formatCurrency(pfTotals.epf_employee)}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <span className="text-sm text-muted-foreground">Employer EPF (3.67%)</span>
                      <p className="text-xl font-bold">{formatCurrency(pfTotals.epf_employer)}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <span className="text-sm text-muted-foreground">EPS (8.33%)</span>
                      <p className="text-xl font-bold">{formatCurrency(pfTotals.eps)}</p>
                    </CardContent>
                  </Card>
                </div>
              )}

              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>UAN</TableHead>
                      <TableHead>Employee</TableHead>
                      <TableHead className="text-right">Gross Wages</TableHead>
                      <TableHead className="text-right">EPF Wages</TableHead>
                      <TableHead className="text-right">EPF (EE)</TableHead>
                      <TableHead className="text-right">EPF (ER)</TableHead>
                      <TableHead className="text-right">EPS</TableHead>
                      <TableHead className="text-right">EDLI</TableHead>
                      <TableHead className="text-right">NCP Days</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pfLoading ? (
                      Array.from({ length: 5 }).map((_, i) => (
                        <TableRow key={i}>
                          {Array.from({ length: 9 }).map((_, j) => (
                            <TableCell key={j}><Skeleton className="h-4 w-16" /></TableCell>
                          ))}
                        </TableRow>
                      ))
                    ) : !pfReport?.length ? (
                      <TableRow>
                        <TableCell colSpan={9} className="text-center py-8">
                          <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                          <h3 className="font-medium">No PF data</h3>
                          <p className="text-sm text-muted-foreground">
                            No PF contributions for {format(new Date(payrollMonth), 'MMMM yyyy')}
                          </p>
                        </TableCell>
                      </TableRow>
                    ) : (
                      pfReport.map((item) => (
                        <TableRow key={item.employee_id}>
                          <TableCell className="font-mono text-sm">{item.uan_number || '-'}</TableCell>
                          <TableCell>
                            <div>
                              <div className="font-medium">{item.employee_name}</div>
                              <div className="text-xs text-muted-foreground">{item.employee_code}</div>
                            </div>
                          </TableCell>
                          <TableCell className="text-right">{formatCurrency(item.gross_wages)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(item.epf_wages)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(item.epf_contribution_employee)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(item.epf_contribution_employer)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(item.eps_contribution)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(item.edli_contribution)}</TableCell>
                          <TableCell className="text-right">{item.ncp_days}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ESIC Tab */}
        <TabsContent value="esic" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>ESIC Report</CardTitle>
                <CardDescription>
                  Employee State Insurance for {format(new Date(payrollMonth), 'MMMM yyyy')}
                </CardDescription>
              </div>
              <Button onClick={handleDownloadESIC} disabled={!esicReport?.length}>
                <Download className="mr-2 h-4 w-4" />
                Download CSV
              </Button>
            </CardHeader>
            <CardContent>
              {/* Summary */}
              {esicTotals && esicReport && esicReport.length > 0 && (
                <div className="grid gap-4 md:grid-cols-4 mb-6">
                  <Card>
                    <CardContent className="pt-4">
                      <span className="text-sm text-muted-foreground">Total Gross Wages</span>
                      <p className="text-xl font-bold">{formatCurrency(esicTotals.gross_wages)}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <span className="text-sm text-muted-foreground">Employee (0.75%)</span>
                      <p className="text-xl font-bold">{formatCurrency(esicTotals.employee_contribution)}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <span className="text-sm text-muted-foreground">Employer (3.25%)</span>
                      <p className="text-xl font-bold">{formatCurrency(esicTotals.employer_contribution)}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <span className="text-sm text-muted-foreground">Total Contribution</span>
                      <p className="text-xl font-bold text-purple-600">{formatCurrency(esicTotals.total_contribution)}</p>
                    </CardContent>
                  </Card>
                </div>
              )}

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ESIC Number</TableHead>
                      <TableHead>Employee</TableHead>
                      <TableHead className="text-right">Gross Wages</TableHead>
                      <TableHead className="text-right">Employee (0.75%)</TableHead>
                      <TableHead className="text-right">Employer (3.25%)</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Days Worked</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {esicLoading ? (
                      Array.from({ length: 5 }).map((_, i) => (
                        <TableRow key={i}>
                          {Array.from({ length: 7 }).map((_, j) => (
                            <TableCell key={j}><Skeleton className="h-4 w-16" /></TableCell>
                          ))}
                        </TableRow>
                      ))
                    ) : !esicReport?.length ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8">
                          <Building2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                          <h3 className="font-medium">No ESIC data</h3>
                          <p className="text-sm text-muted-foreground">
                            No ESIC contributions for {format(new Date(payrollMonth), 'MMMM yyyy')}
                          </p>
                        </TableCell>
                      </TableRow>
                    ) : (
                      esicReport.map((item) => (
                        <TableRow key={item.employee_id}>
                          <TableCell className="font-mono text-sm">{item.esic_number || '-'}</TableCell>
                          <TableCell>
                            <div>
                              <div className="font-medium">{item.employee_name}</div>
                              <div className="text-xs text-muted-foreground">{item.employee_code}</div>
                            </div>
                          </TableCell>
                          <TableCell className="text-right">{formatCurrency(item.gross_wages)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(item.employee_contribution)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(item.employer_contribution)}</TableCell>
                          <TableCell className="text-right font-medium">{formatCurrency(item.total_contribution)}</TableCell>
                          <TableCell className="text-right">{item.days_worked}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
