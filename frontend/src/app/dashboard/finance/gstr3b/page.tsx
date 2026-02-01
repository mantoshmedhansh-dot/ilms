'use client';

import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, Download, Upload, CheckCircle, AlertTriangle, Calendar, IndianRupee, Calculator, CreditCard, RefreshCw, Eye, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { PageHeader } from '@/components/common';
import { formatCurrency } from '@/lib/utils';
import { gstReportsApi, periodsApi, gstFilingApi } from '@/lib/api';

interface GSTR3BSummary {
  return_period: string;
  filing_status: 'NOT_FILED' | 'FILED' | 'OVERDUE';
  due_date: string;
  filed_date?: string;
  arn?: string;
  // 3.1 Outward Supplies
  outward_taxable: { taxable_value: number; igst: number; cgst: number; sgst: number; cess: number };
  outward_zero_rated: { taxable_value: number; igst: number };
  outward_nil_rated: { taxable_value: number };
  outward_exempt: { taxable_value: number };
  outward_non_gst: { taxable_value: number };
  // 3.2 Inter-state supplies
  inter_state_unreg: { taxable_value: number; igst: number };
  inter_state_comp: { taxable_value: number; igst: number };
  inter_state_uin: { taxable_value: number; igst: number };
  // 4. ITC Available
  itc_igst: number;
  itc_cgst: number;
  itc_sgst: number;
  itc_cess: number;
  itc_ineligible_igst: number;
  itc_ineligible_cgst: number;
  itc_ineligible_sgst: number;
  // 5. Exempt/Nil/Non-GST inward supplies
  inward_exempt: number;
  inward_nil: number;
  inward_non_gst: number;
  // 6. Tax Payable
  tax_payable_igst: number;
  tax_payable_cgst: number;
  tax_payable_sgst: number;
  tax_payable_cess: number;
  // ITC utilized
  itc_utilized_igst: number;
  itc_utilized_cgst: number;
  itc_utilized_sgst: number;
  itc_utilized_cess: number;
  // Cash payment
  cash_igst: number;
  cash_cgst: number;
  cash_sgst: number;
  cash_cess: number;
  // Interest/Late fee
  interest: number;
  late_fee: number;
}

// Helper to parse period string to month/year
const parsePeriod = (period: string): { month: number; year: number } => {
  const month = parseInt(period.substring(0, 2), 10);
  const year = parseInt(period.substring(2), 10);
  return { month, year };
};

// Get current period dynamically
const getCurrentPeriod = (): string => {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const year = now.getFullYear();
  return `${month}${year}`;
};

const statusColors: Record<string, string> = {
  NOT_FILED: 'bg-yellow-100 text-yellow-800',
  FILED: 'bg-green-100 text-green-800',
  OVERDUE: 'bg-red-100 text-red-800',
};

export default function GSTR3BPage() {
  const queryClient = useQueryClient();
  const [selectedPeriod, setSelectedPeriod] = useState<string>('');
  const [isPaymentOpen, setIsPaymentOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');

  // Fetch active financial periods from the database
  const { data: periodsData, isLoading: periodsLoading } = useQuery({
    queryKey: ['financial-periods'],
    queryFn: () => periodsApi.list({ size: 100 }),
  });

  // Transform periods for the dropdown
  const periods = useMemo(() => {
    if (!periodsData?.items) return [];

    return periodsData.items
      .filter((p: any) => p.period_type === 'MONTHLY' && (p.status === 'OPEN' || p.status === 'CLOSED'))
      .sort((a: any, b: any) => new Date(b.start_date).getTime() - new Date(a.start_date).getTime())
      .map((p: any) => {
        const startDate = new Date(p.start_date);
        const monthNum = String(startDate.getMonth() + 1).padStart(2, '0');
        const yearNum = startDate.getFullYear();
        return {
          value: `${monthNum}${yearNum}`,
          label: p.period_name,
          isCurrent: p.is_current,
        };
      });
  }, [periodsData]);

  // Set default period to current period or first available period
  useEffect(() => {
    if (periods.length > 0 && !selectedPeriod) {
      const currentPeriod = periods.find((p: any) => p.isCurrent);
      setSelectedPeriod(currentPeriod?.value || periods[0]?.value || '');
    }
  }, [periods, selectedPeriod]);

  const { month, year } = parsePeriod(selectedPeriod || getCurrentPeriod());

  const { data: gstr3bData, isLoading } = useQuery({
    queryKey: ['gstr3b-report', month, year],
    queryFn: () => gstReportsApi.getGSTR3B(month, year),
  });

  // Derive summary from API data
  const summary: GSTR3BSummary | null = gstr3bData ? {
    return_period: gstr3bData.return_period,
    filing_status: 'NOT_FILED',
    due_date: new Date(year, month, 20).toISOString().split('T')[0],
    outward_taxable: {
      taxable_value: gstr3bData.outward_taxable_supplies?.taxable_value || 0,
      igst: gstr3bData.outward_taxable_supplies?.igst || 0,
      cgst: gstr3bData.outward_taxable_supplies?.cgst || 0,
      sgst: gstr3bData.outward_taxable_supplies?.sgst || 0,
      cess: gstr3bData.outward_taxable_supplies?.cess || 0,
    },
    outward_zero_rated: { taxable_value: 0, igst: 0 },
    outward_nil_rated: { taxable_value: 0 },
    outward_exempt: { taxable_value: 0 },
    outward_non_gst: { taxable_value: 0 },
    inter_state_unreg: {
      taxable_value: gstr3bData.inter_state_supplies?.taxable_value || 0,
      igst: gstr3bData.inter_state_supplies?.igst || 0,
    },
    inter_state_comp: { taxable_value: 0, igst: 0 },
    inter_state_uin: { taxable_value: 0, igst: 0 },
    itc_igst: 0,
    itc_cgst: 0,
    itc_sgst: 0,
    itc_cess: 0,
    itc_ineligible_igst: 0,
    itc_ineligible_cgst: 0,
    itc_ineligible_sgst: 0,
    inward_exempt: 0,
    inward_nil: 0,
    inward_non_gst: 0,
    tax_payable_igst: gstr3bData.tax_payable?.igst || 0,
    tax_payable_cgst: gstr3bData.tax_payable?.cgst || 0,
    tax_payable_sgst: gstr3bData.tax_payable?.sgst || 0,
    tax_payable_cess: gstr3bData.tax_payable?.cess || 0,
    itc_utilized_igst: 0,
    itc_utilized_cgst: 0,
    itc_utilized_sgst: 0,
    itc_utilized_cess: 0,
    cash_igst: gstr3bData.tax_payable?.igst || 0,
    cash_cgst: gstr3bData.tax_payable?.cgst || 0,
    cash_sgst: gstr3bData.tax_payable?.sgst || 0,
    cash_cess: gstr3bData.tax_payable?.cess || 0,
    interest: 0,
    late_fee: 0,
  } : null;

  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      // Refresh the data from backend
      await queryClient.invalidateQueries({ queryKey: ['gstr3b-report', month, year] });
      toast.success('GSTR-3B report data refreshed from invoices');
    } catch (error) {
      toast.error('Failed to refresh report data');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExportJSON = () => {
    if (!gstr3bData) {
      toast.error('No data to export');
      return;
    }
    const blob = new Blob([JSON.stringify(gstr3bData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `GSTR3B_${month.toString().padStart(2, '0')}${year}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('GSTR-3B data exported');
  };

  const [isFiling, setIsFiling] = useState(false);

  const handleFileReturn = async () => {
    try {
      setIsFiling(true);
      const result = await gstFilingApi.fileGSTR3B(month, year);
      if (result.success) {
        toast.success(`GSTR-3B filed successfully! ARN: ${result.arn || 'Pending'}`);
        setIsPaymentOpen(false);
        queryClient.invalidateQueries({ queryKey: ['gstr3b-report'] });
      } else {
        toast.error(result.message || 'Filing failed');
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to file GSTR-3B');
    } finally {
      setIsFiling(false);
    }
  };

  const totalTaxPayable = (summary?.tax_payable_igst ?? 0) + (summary?.tax_payable_cgst ?? 0) +
    (summary?.tax_payable_sgst ?? 0) + (summary?.tax_payable_cess ?? 0);
  const totalITCUtilized = (summary?.itc_utilized_igst ?? 0) + (summary?.itc_utilized_cgst ?? 0) +
    (summary?.itc_utilized_sgst ?? 0) + (summary?.itc_utilized_cess ?? 0);
  const totalCashPayment = (summary?.cash_igst ?? 0) + (summary?.cash_cgst ?? 0) +
    (summary?.cash_sgst ?? 0) + (summary?.cash_cess ?? 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="GSTR-3B Return"
        description="Summary return - Monthly filing with tax payment"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleGenerate} disabled={isGenerating}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isGenerating ? 'animate-spin' : ''}`} />
              {isGenerating ? 'Refreshing...' : 'Refresh Data'}
            </Button>
            <Button variant="outline" onClick={handleExportJSON}>
              <Download className="mr-2 h-4 w-4" />
              Export JSON
            </Button>
            <Button onClick={() => setIsPaymentOpen(true)}>
              <Upload className="mr-2 h-4 w-4" />
              File & Pay
            </Button>
          </div>
        }
      />

      {/* Period Selector & Status */}
      <div className="flex items-center justify-between">
        <Select value={selectedPeriod} onValueChange={setSelectedPeriod} disabled={periodsLoading}>
          <SelectTrigger className="w-56">
            {periodsLoading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading periods...
              </span>
            ) : (
              <SelectValue placeholder="Select period" />
            )}
          </SelectTrigger>
          <SelectContent>
            {periods.length === 0 ? (
              <div className="p-2 text-sm text-muted-foreground text-center">
                No active periods found.<br />
                Please configure Financial Periods.
              </div>
            ) : (
              periods.map((p: any) => (
                <SelectItem key={p.value} value={p.value}>
                  {p.label} {p.isCurrent && '(Current)'}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">Due: {summary?.due_date}</span>
          </div>
          <Badge className={statusColors[summary?.filing_status ?? 'NOT_FILED']}>
            {summary?.filing_status?.replace(/_/g, ' ')}
          </Badge>
        </div>
      </div>

      {/* Payment Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-blue-50 border-blue-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-blue-800">Total Tax Payable</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-900">{formatCurrency(totalTaxPayable)}</div>
          </CardContent>
        </Card>
        <Card className="bg-green-50 border-green-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-green-800">ITC Utilized</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-900">{formatCurrency(totalITCUtilized)}</div>
          </CardContent>
        </Card>
        <Card className="bg-orange-50 border-orange-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-orange-800">Cash Payment</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-900">{formatCurrency(totalCashPayment)}</div>
          </CardContent>
        </Card>
        <Card className="bg-purple-50 border-purple-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-purple-800">Interest + Late Fee</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-900">
              {formatCurrency((summary?.interest ?? 0) + (summary?.late_fee ?? 0))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="summary">Return Summary</TabsTrigger>
          <TabsTrigger value="outward">3.1 Outward Supplies</TabsTrigger>
          <TabsTrigger value="itc">4. ITC Available</TabsTrigger>
          <TabsTrigger value="payment">6. Tax Payment</TabsTrigger>
        </TabsList>

        <TabsContent value="summary" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>GSTR-3B Summary</CardTitle>
              <CardDescription>Overview of all sections</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Section</TableHead>
                    <TableHead className="text-right">Taxable Value</TableHead>
                    <TableHead className="text-right">IGST</TableHead>
                    <TableHead className="text-right">CGST</TableHead>
                    <TableHead className="text-right">SGST</TableHead>
                    <TableHead className="text-right">Cess</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow className="font-medium">
                    <TableCell>3.1(a) Outward Taxable Supplies</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_taxable.taxable_value ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_taxable.igst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_taxable.cgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_taxable.sgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_taxable.cess ?? 0)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>3.1(b) Zero Rated Supplies</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_zero_rated.taxable_value ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_zero_rated.igst ?? 0)}</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>3.1(c) Nil Rated Supplies</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_nil_rated.taxable_value ?? 0)}</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>3.1(d) Exempt Supplies</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_exempt.taxable_value ?? 0)}</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                  </TableRow>
                  <TableRow className="bg-muted/50">
                    <TableCell className="font-bold">4. ITC Available</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right font-bold">{formatCurrency(summary?.itc_igst ?? 0)}</TableCell>
                    <TableCell className="text-right font-bold">{formatCurrency(summary?.itc_cgst ?? 0)}</TableCell>
                    <TableCell className="text-right font-bold">{formatCurrency(summary?.itc_sgst ?? 0)}</TableCell>
                    <TableCell className="text-right font-bold">{formatCurrency(summary?.itc_cess ?? 0)}</TableCell>
                  </TableRow>
                  <TableRow className="bg-blue-50">
                    <TableCell className="font-bold">6.1 Tax Payable</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right font-bold">{formatCurrency(summary?.tax_payable_igst ?? 0)}</TableCell>
                    <TableCell className="text-right font-bold">{formatCurrency(summary?.tax_payable_cgst ?? 0)}</TableCell>
                    <TableCell className="text-right font-bold">{formatCurrency(summary?.tax_payable_sgst ?? 0)}</TableCell>
                    <TableCell className="text-right font-bold">{formatCurrency(summary?.tax_payable_cess ?? 0)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="outward" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>3.1 Details of Outward Supplies</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nature of Supplies</TableHead>
                    <TableHead className="text-right">Taxable Value</TableHead>
                    <TableHead className="text-right">IGST</TableHead>
                    <TableHead className="text-right">CGST</TableHead>
                    <TableHead className="text-right">SGST</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell>
                      <div>(a) Outward Taxable Supplies (other than zero rated, nil rated and exempted)</div>
                    </TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_taxable.taxable_value ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_taxable.igst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_taxable.cgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_taxable.sgst ?? 0)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>(b) Outward taxable supplies (zero rated)</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_zero_rated.taxable_value ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_zero_rated.igst ?? 0)}</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>(c) Other outward supplies (nil rated, exempted)</TableCell>
                    <TableCell className="text-right">{formatCurrency((summary?.outward_nil_rated.taxable_value ?? 0) + (summary?.outward_exempt.taxable_value ?? 0))}</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>(d) Inward supplies (liable to reverse charge)</TableCell>
                    <TableCell className="text-right">0</TableCell>
                    <TableCell className="text-right">0</TableCell>
                    <TableCell className="text-right">0</TableCell>
                    <TableCell className="text-right">0</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>(e) Non-GST outward supplies</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.outward_non_gst.taxable_value ?? 0)}</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>3.2 Inter-State Supplies to Unregistered Persons, Composition Dealers, UIN Holders</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nature of Supplies</TableHead>
                    <TableHead className="text-right">Taxable Value</TableHead>
                    <TableHead className="text-right">IGST</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell>Supplies to Unregistered Persons</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.inter_state_unreg.taxable_value ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.inter_state_unreg.igst ?? 0)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Supplies to Composition Dealers</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.inter_state_comp.taxable_value ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.inter_state_comp.igst ?? 0)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Supplies to UIN Holders</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.inter_state_uin.taxable_value ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.inter_state_uin.igst ?? 0)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="itc" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>4. Eligible ITC</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Details</TableHead>
                    <TableHead className="text-right">IGST</TableHead>
                    <TableHead className="text-right">CGST</TableHead>
                    <TableHead className="text-right">SGST</TableHead>
                    <TableHead className="text-right">Cess</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow className="font-medium">
                    <TableCell>(A) ITC Available</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_igst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_cgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_sgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_cess ?? 0)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="pl-8">Import of goods</TableCell>
                    <TableCell className="text-right">0</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">0</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="pl-8">Import of services</TableCell>
                    <TableCell className="text-right">0</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">0</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="pl-8">Inward supplies liable to reverse charge</TableCell>
                    <TableCell className="text-right">0</TableCell>
                    <TableCell className="text-right">0</TableCell>
                    <TableCell className="text-right">0</TableCell>
                    <TableCell className="text-right">0</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="pl-8">Inward supplies from ISD</TableCell>
                    <TableCell className="text-right">0</TableCell>
                    <TableCell className="text-right">0</TableCell>
                    <TableCell className="text-right">0</TableCell>
                    <TableCell className="text-right">0</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="pl-8">All other ITC</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_igst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_cgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_sgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_cess ?? 0)}</TableCell>
                  </TableRow>
                  <TableRow className="text-red-600">
                    <TableCell>(B) ITC Reversed</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_ineligible_igst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_ineligible_cgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_ineligible_sgst ?? 0)}</TableCell>
                    <TableCell className="text-right">0</TableCell>
                  </TableRow>
                  <TableRow className="font-bold bg-green-50">
                    <TableCell>(C) Net ITC Available (A - B)</TableCell>
                    <TableCell className="text-right">{formatCurrency((summary?.itc_igst ?? 0) - (summary?.itc_ineligible_igst ?? 0))}</TableCell>
                    <TableCell className="text-right">{formatCurrency((summary?.itc_cgst ?? 0) - (summary?.itc_ineligible_cgst ?? 0))}</TableCell>
                    <TableCell className="text-right">{formatCurrency((summary?.itc_sgst ?? 0) - (summary?.itc_ineligible_sgst ?? 0))}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.itc_cess ?? 0)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="payment" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>6. Payment of Tax</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">IGST</TableHead>
                    <TableHead className="text-right">CGST</TableHead>
                    <TableHead className="text-right">SGST</TableHead>
                    <TableHead className="text-right">Cess</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow className="font-medium">
                    <TableCell>6.1 Tax Payable</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.tax_payable_igst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.tax_payable_cgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.tax_payable_sgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.tax_payable_cess ?? 0)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="text-green-600">6.2 ITC Utilized</TableCell>
                    <TableCell className="text-right text-green-600">{formatCurrency(summary?.itc_utilized_igst ?? 0)}</TableCell>
                    <TableCell className="text-right text-green-600">{formatCurrency(summary?.itc_utilized_cgst ?? 0)}</TableCell>
                    <TableCell className="text-right text-green-600">{formatCurrency(summary?.itc_utilized_sgst ?? 0)}</TableCell>
                    <TableCell className="text-right text-green-600">{formatCurrency(summary?.itc_utilized_cess ?? 0)}</TableCell>
                  </TableRow>
                  <TableRow className="font-bold bg-orange-50">
                    <TableCell>6.3 Tax Paid in Cash</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.cash_igst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.cash_cgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.cash_sgst ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(summary?.cash_cess ?? 0)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Interest</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(summary?.interest ?? 0)}</div>
                <p className="text-sm text-muted-foreground">18% p.a. on delayed payment</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Late Fee</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(summary?.late_fee ?? 0)}</div>
                <p className="text-sm text-muted-foreground">₹50/day CGST + ₹50/day SGST</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Payment Dialog */}
      <Dialog open={isPaymentOpen} onOpenChange={setIsPaymentOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>File GSTR-3B & Make Payment</DialogTitle>
            <DialogDescription>
              Review and confirm the payment details before filing
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Total Tax Payable</Label>
              <div className="text-2xl font-bold">{formatCurrency(totalTaxPayable)}</div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-muted-foreground">ITC Utilized</Label>
                <div className="font-medium text-green-600">{formatCurrency(totalITCUtilized)}</div>
              </div>
              <div>
                <Label className="text-muted-foreground">Cash Payment</Label>
                <div className="font-medium text-orange-600">{formatCurrency(totalCashPayment)}</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-muted-foreground">Interest</Label>
                <div className="font-medium">{formatCurrency(summary?.interest ?? 0)}</div>
              </div>
              <div>
                <Label className="text-muted-foreground">Late Fee</Label>
                <div className="font-medium">{formatCurrency(summary?.late_fee ?? 0)}</div>
              </div>
            </div>
            <div className="border-t pt-4">
              <div className="flex justify-between items-center">
                <Label className="text-lg">Total Amount</Label>
                <div className="text-2xl font-bold text-primary">
                  {formatCurrency(totalCashPayment + (summary?.interest ?? 0) + (summary?.late_fee ?? 0))}
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsPaymentOpen(false)} disabled={isFiling}>Cancel</Button>
            <Button onClick={handleFileReturn} disabled={isFiling}>
              {isFiling ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <CreditCard className="mr-2 h-4 w-4" />
              )}
              {isFiling ? 'Filing...' : 'Pay & File'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
