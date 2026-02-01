'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  FileText,
  Plus,
  Download,
  Upload,
  Calculator,
  CheckCircle,
  Clock,
  AlertTriangle,
  Search,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { PageHeader } from '@/components/common';
import { tdsApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

// Calculate current fiscal year dynamically (Indian FY: April to March)
const getCurrentFiscalYear = (): string => {
  const now = new Date();
  const month = now.getMonth(); // 0-11
  const year = now.getFullYear();
  // FY starts in April (month 3)
  // If current month is Jan-Mar (0-2), FY is previous year to current year
  // If current month is Apr-Dec (3-11), FY is current year to next year
  if (month < 3) {
    return `${year - 1}-${String(year).slice(-2)}`;
  }
  return `${year}-${String(year + 1).slice(-2)}`;
};

const CURRENT_FY = getCurrentFiscalYear();
const QUARTERS = ['Q1', 'Q2', 'Q3', 'Q4'];

// Generate last N fiscal years dynamically
const getRecentFiscalYears = (count: number = 5): string[] => {
  const years: string[] = [];
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth();
  // Start from current FY
  let startYear = currentMonth < 3 ? currentYear - 1 : currentYear;

  for (let i = 0; i < count; i++) {
    const fy = `${startYear - i}-${String(startYear - i + 1).slice(-2)}`;
    years.push(fy);
  }
  return years;
};

const FISCAL_YEARS = getRecentFiscalYears(5);

interface TDSDeduction {
  id: string;
  deductee_name: string;
  deductee_pan: string;
  section: string;
  deduction_date: string;
  financial_year: string;
  quarter: string;
  gross_amount: number;
  tds_rate: number;
  total_tds: number;
  status: string;
  challan_number?: string;
  certificate_issued: boolean;
}

interface TDSSummary {
  financial_year: string;
  by_section: Array<{ section: string; count: number; total_gross: number; total_tds: number }>;
  by_quarter: Array<{ quarter: string; count: number; total_tds: number }>;
  by_status: Array<{ status: string; count: number; total_tds: number }>;
  totals: { total_deductions: number; total_gross_amount: number; total_tds_amount: number };
}

export default function TDSManagementPage() {
  const [selectedFY, setSelectedFY] = useState(CURRENT_FY);
  const [selectedQuarter, setSelectedQuarter] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isDepositDialogOpen, setIsDepositDialogOpen] = useState(false);
  const [selectedDeductions, setSelectedDeductions] = useState<string[]>([]);

  const queryClient = useQueryClient();

  // Form state for new deduction
  const [newDeduction, setNewDeduction] = useState({
    deductee_name: '',
    deductee_pan: '',
    deductee_type: 'VENDOR',
    section: '194C',
    deduction_date: format(new Date(), 'yyyy-MM-dd'),
    gross_amount: '',
  });

  // Deposit form state
  const [depositData, setDepositData] = useState({
    deposit_date: format(new Date(), 'yyyy-MM-dd'),
    challan_number: '',
    challan_date: format(new Date(), 'yyyy-MM-dd'),
    bsr_code: '',
    cin: '',
  });

  // Fetch TDS deductions
  const { data: deductions, isLoading: deductionsLoading } = useQuery({
    queryKey: ['tds-deductions', selectedFY, selectedQuarter, selectedStatus],
    queryFn: () => tdsApi.listDeductions({
      financial_year: selectedFY,
      quarter: selectedQuarter || undefined,
      status: selectedStatus || undefined,
    }),
  });

  // Fetch TDS summary
  const { data: summary } = useQuery({
    queryKey: ['tds-summary', selectedFY],
    queryFn: () => tdsApi.getSummary(selectedFY),
  });

  // Fetch pending deposits
  const { data: pendingDeposits } = useQuery({
    queryKey: ['tds-pending-deposits', selectedFY],
    queryFn: () => tdsApi.getPendingDeposits(selectedFY),
  });

  // Fetch TDS sections
  const { data: sections } = useQuery({
    queryKey: ['tds-sections'],
    queryFn: () => tdsApi.getSections(),
  });

  // Calculate TDS mutation
  const calculateMutation = useMutation({
    mutationFn: () => tdsApi.calculate(
      parseFloat(newDeduction.gross_amount),
      newDeduction.section,
      true
    ),
  });

  // Record deduction mutation
  const recordMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => tdsApi.recordDeduction(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tds-deductions'] });
      queryClient.invalidateQueries({ queryKey: ['tds-summary'] });
      queryClient.invalidateQueries({ queryKey: ['tds-pending-deposits'] });
      setIsAddDialogOpen(false);
      setNewDeduction({
        deductee_name: '',
        deductee_pan: '',
        deductee_type: 'VENDOR',
        section: '194C',
        deduction_date: format(new Date(), 'yyyy-MM-dd'),
        gross_amount: '',
      });
      toast.success('TDS deduction recorded successfully');
    },
    onError: () => {
      toast.error('Failed to record TDS deduction');
    },
  });

  // Mark deposited mutation
  const depositMutation = useMutation({
    mutationFn: () => tdsApi.markDeposited(
      selectedDeductions,
      depositData.deposit_date,
      depositData.challan_number,
      depositData.challan_date,
      depositData.bsr_code,
      depositData.cin || undefined
    ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tds-deductions'] });
      queryClient.invalidateQueries({ queryKey: ['tds-summary'] });
      queryClient.invalidateQueries({ queryKey: ['tds-pending-deposits'] });
      setIsDepositDialogOpen(false);
      setSelectedDeductions([]);
      toast.success('TDS marked as deposited');
    },
    onError: () => {
      toast.error('Failed to update deposit status');
    },
  });

  // Generate Form 16A mutation
  const form16AMutation = useMutation({
    mutationFn: ({ pan, fy, quarter }: { pan: string; fy: string; quarter: string }) =>
      tdsApi.downloadForm16A(pan, fy, quarter),
    onSuccess: (data) => {
      // Handle PDF download
      if (data.content_base64) {
        const byteCharacters = atob(data.content_base64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename || 'Form16A.pdf';
        a.click();
        URL.revokeObjectURL(url);
      }
      toast.success('Form 16A generated successfully');
    },
    onError: () => {
      toast.error('Failed to generate Form 16A');
    },
  });

  const handleCalculateTDS = async () => {
    if (!newDeduction.gross_amount) return;
    const result = await calculateMutation.mutateAsync();
    toast.info(`TDS Amount: ${formatCurrency(result.total_tds)} at ${result.tds_rate}%`);
  };

  const handleRecordDeduction = () => {
    if (!newDeduction.deductee_name || !newDeduction.deductee_pan || !newDeduction.gross_amount) {
      toast.error('Please fill all required fields');
      return;
    }
    recordMutation.mutate({
      ...newDeduction,
      gross_amount: parseFloat(newDeduction.gross_amount),
      pan_available: true,
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING':
        return <Badge variant="outline" className="text-orange-600"><Clock className="h-3 w-3 mr-1" />Pending</Badge>;
      case 'DEPOSITED':
        return <Badge variant="default" className="bg-green-100 text-green-800"><CheckCircle className="h-3 w-3 mr-1" />Deposited</Badge>;
      case 'CERTIFICATE_ISSUED':
        return <Badge variant="default" className="bg-blue-100 text-blue-800"><FileText className="h-3 w-3 mr-1" />Certificate Issued</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const filteredDeductions = (deductions || []).filter((d: TDSDeduction) =>
    d.deductee_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.deductee_pan.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const pendingCount = summary?.by_status?.find((s: { status: string }) => s.status === 'PENDING')?.count || 0;
  const pendingAmount = summary?.by_status?.find((s: { status: string }) => s.status === 'PENDING')?.total_tds || 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="TDS Management"
        description="Tax Deducted at Source - Deductions, Deposits & Certificates"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setIsAddDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Record TDS
            </Button>
            {selectedDeductions.length > 0 && (
              <Button onClick={() => setIsDepositDialogOpen(true)}>
                <Upload className="mr-2 h-4 w-4" />
                Mark Deposited ({selectedDeductions.length})
              </Button>
            )}
          </div>
        }
      />

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Deductions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.totals?.total_deductions || 0}</div>
            <p className="text-xs text-muted-foreground">FY {selectedFY}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total TDS Amount</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(summary?.totals?.total_tds_amount || 0)}</div>
            <p className="text-xs text-muted-foreground">Gross: {formatCurrency(summary?.totals?.total_gross_amount || 0)}</p>
          </CardContent>
        </Card>
        <Card className={pendingCount > 0 ? 'border-orange-300' : ''}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              Pending Deposit
              {pendingCount > 0 && <AlertTriangle className="h-4 w-4 text-orange-500" />}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{pendingCount}</div>
            <p className="text-xs text-muted-foreground">{formatCurrency(pendingAmount)} to deposit</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Certificates Issued</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary?.by_status?.find((s: { status: string }) => s.status === 'CERTIFICATE_ISSUED')?.count || 0}
            </div>
            <p className="text-xs text-muted-foreground">Form 16A generated</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="deductions" className="space-y-4">
        <TabsList>
          <TabsTrigger value="deductions">Deductions</TabsTrigger>
          <TabsTrigger value="summary">Summary by Section</TabsTrigger>
          <TabsTrigger value="certificates">Certificates</TabsTrigger>
        </TabsList>

        <TabsContent value="deductions" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-wrap gap-4">
                <div className="flex-1 min-w-[200px]">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search by name or PAN..."
                      className="pl-9"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                    />
                  </div>
                </div>
                <Select value={selectedFY} onValueChange={setSelectedFY}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="Financial Year" />
                  </SelectTrigger>
                  <SelectContent>
                    {FISCAL_YEARS.map(fy => (
                      <SelectItem key={fy} value={fy}>FY {fy}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={selectedQuarter || 'all'} onValueChange={(v) => setSelectedQuarter(v === 'all' ? '' : v)}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="All Quarters" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Quarters</SelectItem>
                    {QUARTERS.map(q => (
                      <SelectItem key={q} value={q}>{q}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={selectedStatus || 'all'} onValueChange={(v) => setSelectedStatus(v === 'all' ? '' : v)}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="All Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="PENDING">Pending</SelectItem>
                    <SelectItem value="DEPOSITED">Deposited</SelectItem>
                    <SelectItem value="CERTIFICATE_ISSUED">Certificate Issued</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Deductions Table */}
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[40px]">
                      <input
                        type="checkbox"
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedDeductions(
                              filteredDeductions
                                .filter((d: TDSDeduction) => d.status === 'PENDING')
                                .map((d: TDSDeduction) => d.id)
                            );
                          } else {
                            setSelectedDeductions([]);
                          }
                        }}
                      />
                    </TableHead>
                    <TableHead>Deductee</TableHead>
                    <TableHead>PAN</TableHead>
                    <TableHead>Section</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Gross Amount</TableHead>
                    <TableHead className="text-right">TDS</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {deductionsLoading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                      <TableRow key={i}>
                        {Array.from({ length: 9 }).map((_, j) => (
                          <TableCell key={j}><Skeleton className="h-4 w-20" /></TableCell>
                        ))}
                      </TableRow>
                    ))
                  ) : filteredDeductions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                        No TDS deductions found
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredDeductions.map((deduction: TDSDeduction) => (
                      <TableRow key={deduction.id}>
                        <TableCell>
                          {deduction.status === 'PENDING' && (
                            <input
                              type="checkbox"
                              checked={selectedDeductions.includes(deduction.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedDeductions([...selectedDeductions, deduction.id]);
                                } else {
                                  setSelectedDeductions(selectedDeductions.filter(id => id !== deduction.id));
                                }
                              }}
                            />
                          )}
                        </TableCell>
                        <TableCell className="font-medium">{deduction.deductee_name}</TableCell>
                        <TableCell className="font-mono text-sm">{deduction.deductee_pan}</TableCell>
                        <TableCell>{deduction.section}</TableCell>
                        <TableCell>{format(new Date(deduction.deduction_date), 'dd/MM/yyyy')}</TableCell>
                        <TableCell className="text-right">{formatCurrency(deduction.gross_amount)}</TableCell>
                        <TableCell className="text-right font-medium">{formatCurrency(deduction.total_tds)}</TableCell>
                        <TableCell>{getStatusBadge(deduction.status)}</TableCell>
                        <TableCell>
                          {deduction.status === 'DEPOSITED' && !deduction.certificate_issued && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => form16AMutation.mutate({
                                pan: deduction.deductee_pan,
                                fy: deduction.financial_year,
                                quarter: deduction.quarter,
                              })}
                            >
                              <Download className="h-3 w-3 mr-1" />
                              Form 16A
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="summary">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>By Section</CardTitle>
                <CardDescription>TDS deductions grouped by section</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Section</TableHead>
                      <TableHead className="text-right">Count</TableHead>
                      <TableHead className="text-right">Gross Amount</TableHead>
                      <TableHead className="text-right">TDS Amount</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary?.by_section?.map((row: { section: string; count: number; total_gross: number; total_tds: number }) => (
                      <TableRow key={row.section}>
                        <TableCell className="font-medium">{row.section}</TableCell>
                        <TableCell className="text-right">{row.count}</TableCell>
                        <TableCell className="text-right">{formatCurrency(row.total_gross)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(row.total_tds)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>By Quarter</CardTitle>
                <CardDescription>TDS deductions grouped by quarter</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Quarter</TableHead>
                      <TableHead className="text-right">Count</TableHead>
                      <TableHead className="text-right">TDS Amount</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary?.by_quarter?.map((row: { quarter: string; count: number; total_tds: number }) => (
                      <TableRow key={row.quarter}>
                        <TableCell className="font-medium">{row.quarter}</TableCell>
                        <TableCell className="text-right">{row.count}</TableCell>
                        <TableCell className="text-right">{formatCurrency(row.total_tds)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="certificates">
          <Card>
            <CardHeader>
              <CardTitle>Form 16A Certificates</CardTitle>
              <CardDescription>Generate and download TDS certificates for deductees</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground text-sm">
                Click "Form 16A" button on deposited deductions to generate certificates.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Add TDS Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Record TDS Deduction</DialogTitle>
            <DialogDescription>Enter details of the TDS deducted</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Deductee Name *</Label>
              <Input
                value={newDeduction.deductee_name}
                onChange={(e) => setNewDeduction({ ...newDeduction, deductee_name: e.target.value })}
                placeholder="Vendor/Contractor name"
              />
            </div>
            <div className="grid gap-2">
              <Label>PAN *</Label>
              <Input
                value={newDeduction.deductee_pan}
                onChange={(e) => setNewDeduction({ ...newDeduction, deductee_pan: e.target.value.toUpperCase() })}
                placeholder="ABCDE1234F"
                maxLength={10}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>Section</Label>
                <Select
                  value={newDeduction.section}
                  onValueChange={(value) => setNewDeduction({ ...newDeduction, section: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {sections?.sections?.map((s: { code: string; description: string }) => (
                      <SelectItem key={s.code} value={s.code}>{s.code} - {s.description}</SelectItem>
                    )) || (
                      <>
                        <SelectItem value="194C">194C - Contractors</SelectItem>
                        <SelectItem value="194J">194J - Professional</SelectItem>
                        <SelectItem value="194H">194H - Commission</SelectItem>
                        <SelectItem value="194I">194I - Rent</SelectItem>
                        <SelectItem value="194A">194A - Interest</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label>Deduction Date</Label>
                <Input
                  type="date"
                  value={newDeduction.deduction_date}
                  onChange={(e) => setNewDeduction({ ...newDeduction, deduction_date: e.target.value })}
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label>Gross Amount *</Label>
              <div className="flex gap-2">
                <Input
                  type="number"
                  value={newDeduction.gross_amount}
                  onChange={(e) => setNewDeduction({ ...newDeduction, gross_amount: e.target.value })}
                  placeholder="0.00"
                />
                <Button variant="outline" onClick={handleCalculateTDS} disabled={!newDeduction.gross_amount}>
                  <Calculator className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleRecordDeduction} disabled={recordMutation.isPending}>
              {recordMutation.isPending ? 'Recording...' : 'Record TDS'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Mark Deposited Dialog */}
      <Dialog open={isDepositDialogOpen} onOpenChange={setIsDepositDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mark TDS as Deposited</DialogTitle>
            <DialogDescription>Enter challan details for {selectedDeductions.length} deduction(s)</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>Deposit Date *</Label>
                <Input
                  type="date"
                  value={depositData.deposit_date}
                  onChange={(e) => setDepositData({ ...depositData, deposit_date: e.target.value })}
                />
              </div>
              <div className="grid gap-2">
                <Label>Challan Date *</Label>
                <Input
                  type="date"
                  value={depositData.challan_date}
                  onChange={(e) => setDepositData({ ...depositData, challan_date: e.target.value })}
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label>Challan Number *</Label>
              <Input
                value={depositData.challan_number}
                onChange={(e) => setDepositData({ ...depositData, challan_number: e.target.value })}
                placeholder="e.g., 12345678"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>BSR Code *</Label>
                <Input
                  value={depositData.bsr_code}
                  onChange={(e) => setDepositData({ ...depositData, bsr_code: e.target.value })}
                  placeholder="7-digit BSR code"
                />
              </div>
              <div className="grid gap-2">
                <Label>CIN (Optional)</Label>
                <Input
                  value={depositData.cin}
                  onChange={(e) => setDepositData({ ...depositData, cin: e.target.value })}
                  placeholder="Challan ID Number"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDepositDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => depositMutation.mutate()} disabled={depositMutation.isPending}>
              {depositMutation.isPending ? 'Updating...' : 'Mark Deposited'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
