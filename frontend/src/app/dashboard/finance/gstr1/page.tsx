'use client';

import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { FileText, Download, Upload, CheckCircle, AlertTriangle, Calendar, Building2, RefreshCw, ExternalLink, FileJson, FileSpreadsheet, Loader2, Send } from 'lucide-react';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import { formatDate, formatCurrency } from '@/lib/utils';
import { gstReportsApi, periodsApi, gstFilingApi } from '@/lib/api';

// API response types
interface B2BInvoiceAPI {
  gstin: string;
  invoice_number: string;
  invoice_date: string;
  invoice_value: number;
  place_of_supply: string;
  taxable_value: number;
  cgst: number;
  sgst: number;
  igst: number;
  cess: number;
}

interface HSNSummaryAPI {
  hsn_code: string;
  quantity: number;
  taxable_value: number;
  igst: number;
  cgst: number;
  sgst: number;
}

// Transformed types for display
interface B2BInvoiceDisplay {
  id: string;
  invoice_number: string;
  invoice_date: string;
  gstin: string;
  party_name: string;
  invoice_type: 'Regular' | 'SEZ with payment' | 'SEZ without payment' | 'Deemed Export';
  taxable_value: number;
  igst: number;
  cgst: number;
  sgst: number;
  cess: number;
  total_value: number;
  place_of_supply: string;
  reverse_charge: boolean;
  status: 'VALID' | 'ERROR' | 'WARNING';
  error_message?: string;
}

interface HSNSummaryDisplay {
  hsn_code: string;
  description: string;
  uqc: string;
  total_quantity: number;
  total_value: number;
  taxable_value: number;
  igst: number;
  cgst: number;
  sgst: number;
  cess: number;
  rate: number;
}

const statusColors: Record<string, string> = {
  VALID: 'bg-green-100 text-green-800',
  ERROR: 'bg-red-100 text-red-800',
  WARNING: 'bg-yellow-100 text-yellow-800',
  NOT_FILED: 'bg-yellow-100 text-yellow-800',
  FILED: 'bg-green-100 text-green-800',
  OVERDUE: 'bg-red-100 text-red-800',
};

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

export default function GSTR1Page() {
  const queryClient = useQueryClient();
  const [selectedPeriod, setSelectedPeriod] = useState<string>('');
  const [activeTab, setActiveTab] = useState('summary');

  // Fetch active financial periods from the database
  const { data: periodsData, isLoading: periodsLoading } = useQuery({
    queryKey: ['financial-periods'],
    queryFn: () => periodsApi.list({ size: 100 }),
  });

  // Transform periods for the dropdown - only MONTHLY periods that are OPEN
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

  const { data: gstr1Data, isLoading: summaryLoading } = useQuery({
    queryKey: ['gstr1-report', month, year],
    queryFn: () => gstReportsApi.getGSTR1(month, year),
  });

  // Calculate filing status based on due date
  const dueDate = new Date(year, month, 11); // GSTR-1 due on 11th of next month
  const isOverdue = new Date() > dueDate;

  // Derive summary from API data
  const summary = gstr1Data ? {
    return_period: gstr1Data.return_period,
    filing_status: (gstr1Data.filing_status as 'NOT_FILED' | 'FILED' | 'OVERDUE') || (isOverdue ? 'OVERDUE' : 'NOT_FILED'),
    due_date: dueDate.toISOString().split('T')[0],
    total_invoices: (gstr1Data.b2b?.length || 0) + (gstr1Data.b2cl?.length || 0),
    total_taxable_value: gstr1Data.b2b?.reduce((sum: number, inv: B2BInvoiceAPI) => sum + inv.taxable_value, 0) || 0,
    total_igst: gstr1Data.b2b?.reduce((sum: number, inv: B2BInvoiceAPI) => sum + inv.igst, 0) || 0,
    total_cgst: gstr1Data.b2b?.reduce((sum: number, inv: B2BInvoiceAPI) => sum + inv.cgst, 0) || 0,
    total_sgst: gstr1Data.b2b?.reduce((sum: number, inv: B2BInvoiceAPI) => sum + inv.sgst, 0) || 0,
    total_cess: gstr1Data.b2b?.reduce((sum: number, inv: B2BInvoiceAPI) => sum + inv.cess, 0) || 0,
    total_tax: 0,
    b2b_invoices: gstr1Data.b2b?.length || 0,
    b2b_value: gstr1Data.b2b?.reduce((sum: number, inv: B2BInvoiceAPI) => sum + inv.invoice_value, 0) || 0,
    b2c_large_invoices: gstr1Data.b2cl?.length || 0,
    b2c_large_value: gstr1Data.b2cl?.reduce((sum: number, inv: { invoice_value: number }) => sum + inv.invoice_value, 0) || 0,
    b2cs_value: gstr1Data.b2cs?.reduce((sum: number, item: { taxable_value: number }) => sum + item.taxable_value, 0) || 0,
    credit_debit_notes: gstr1Data.cdnr?.length || 0,
    cdn_value: gstr1Data.cdnr?.reduce((sum: number, note: { taxable_value: number }) => sum + note.taxable_value, 0) || 0,
    exports_invoices: 0,
    exports_value: 0,
    nil_rated_value: 0,
    hsn_summary_count: gstr1Data.hsn?.length || 0,
  } : null;

  // Derive B2B data from API
  const b2bData = gstr1Data ? {
    items: gstr1Data.b2b?.map((inv: B2BInvoiceAPI, idx: number) => ({
      id: String(idx + 1),
      invoice_number: inv.invoice_number,
      invoice_date: inv.invoice_date,
      gstin: inv.gstin,
      party_name: inv.gstin || 'Unknown',
      invoice_type: 'Regular' as const,
      taxable_value: inv.taxable_value,
      igst: inv.igst,
      cgst: inv.cgst,
      sgst: inv.sgst,
      cess: inv.cess,
      total_value: inv.invoice_value,
      place_of_supply: inv.place_of_supply,
      reverse_charge: false,
      status: inv.gstin ? 'VALID' as const : 'ERROR' as const,
      error_message: !inv.gstin ? 'Invalid GSTIN' : undefined,
    })) || [],
  } : { items: [] };

  // Derive HSN data from API
  const hsnData = gstr1Data ? {
    items: gstr1Data.hsn?.map((hsn: HSNSummaryAPI) => ({
      hsn_code: hsn.hsn_code,
      description: '',
      uqc: 'NOS',
      total_quantity: hsn.quantity,
      total_value: hsn.taxable_value,
      taxable_value: hsn.taxable_value,
      igst: hsn.igst,
      cgst: hsn.cgst,
      sgst: hsn.sgst,
      cess: 0,
      rate: 18,
    })) || [],
  } : { items: [] };

  const generateMutation = useMutation({
    mutationFn: async () => {
      // Refresh data
      await queryClient.invalidateQueries({ queryKey: ['gstr1-report'] });
    },
    onSuccess: () => {
      toast.success('GSTR-1 report refreshed successfully');
    },
  });

  const handleExportJSON = () => {
    if (!gstr1Data) {
      toast.error('No data to export');
      return;
    }
    const blob = new Blob([JSON.stringify(gstr1Data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `GSTR1_${month.toString().padStart(2, '0')}${year}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('GSTR-1 data exported');
  };

  const [isFiling, setIsFiling] = useState(false);
  const [showFilingDialog, setShowFilingDialog] = useState(false);
  const [filingPreview, setFilingPreview] = useState<any>(null);

  const handlePreviewFiling = async () => {
    try {
      setIsFiling(true);
      const preview = await gstFilingApi.fileGSTR1(month, year, { preview: true });
      setFilingPreview(preview);
      setShowFilingDialog(true);
    } catch (error: any) {
      toast.error(error.message || 'Failed to preview GSTR-1 filing');
    } finally {
      setIsFiling(false);
    }
  };

  const handleFileReturn = async () => {
    try {
      setIsFiling(true);
      const result = await gstFilingApi.fileGSTR1(month, year);
      if (result.success) {
        toast.success(`GSTR-1 filed successfully! ARN: ${result.arn || 'Pending'}`);
        setShowFilingDialog(false);
        queryClient.invalidateQueries({ queryKey: ['gstr1-report'] });
      } else {
        toast.error(result.message || 'Filing failed');
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to file GSTR-1');
    } finally {
      setIsFiling(false);
    }
  };

  const b2bColumns: ColumnDef<B2BInvoiceDisplay>[] = [
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
      accessorKey: 'party_name',
      header: 'Recipient',
      cell: ({ row }) => (
        <div>
          <div className="text-sm">{row.original.party_name}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.original.gstin || 'N/A'}</div>
        </div>
      ),
    },
    {
      accessorKey: 'invoice_type',
      header: 'Type',
      cell: ({ row }) => (
        <Badge variant="outline">{row.original.invoice_type}</Badge>
      ),
    },
    {
      accessorKey: 'place_of_supply',
      header: 'POS',
      cell: ({ row }) => (
        <span className="text-sm">{row.original.place_of_supply}</span>
      ),
    },
    {
      accessorKey: 'taxable_value',
      header: 'Taxable Value',
      cell: ({ row }) => (
        <span className="font-medium">{formatCurrency(row.original.taxable_value)}</span>
      ),
    },
    {
      accessorKey: 'tax',
      header: 'Tax',
      cell: ({ row }) => (
        <div className="text-sm">
          {row.original.igst > 0 ? (
            <div>IGST: {formatCurrency(row.original.igst)}</div>
          ) : (
            <>
              <div>CGST: {formatCurrency(row.original.cgst)}</div>
              <div>SGST: {formatCurrency(row.original.sgst)}</div>
            </>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'total_value',
      header: 'Total',
      cell: ({ row }) => (
        <span className="font-bold">{formatCurrency(row.original.total_value)}</span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <div>
          <Badge className={statusColors[row.original.status]}>
            {row.original.status}
          </Badge>
          {row.original.error_message && (
            <div className="text-xs text-red-600 mt-1">{row.original.error_message}</div>
          )}
        </div>
      ),
    },
  ];

  const hsnColumns: ColumnDef<HSNSummaryDisplay>[] = [
    {
      accessorKey: 'hsn_code',
      header: 'HSN Code',
      cell: ({ row }) => (
        <div>
          <div className="font-mono font-medium">{row.original.hsn_code}</div>
          <div className="text-xs text-muted-foreground max-w-48 truncate">{row.original.description}</div>
        </div>
      ),
    },
    {
      accessorKey: 'uqc',
      header: 'UQC',
    },
    {
      accessorKey: 'total_quantity',
      header: 'Qty',
      cell: ({ row }) => (row.original.total_quantity ?? 0).toLocaleString(),
    },
    {
      accessorKey: 'taxable_value',
      header: 'Taxable Value',
      cell: ({ row }) => formatCurrency(row.original.taxable_value),
    },
    {
      accessorKey: 'rate',
      header: 'Rate',
      cell: ({ row }) => `${row.original.rate}%`,
    },
    {
      accessorKey: 'igst',
      header: 'IGST',
      cell: ({ row }) => formatCurrency(row.original.igst),
    },
    {
      accessorKey: 'cgst',
      header: 'CGST',
      cell: ({ row }) => formatCurrency(row.original.cgst),
    },
    {
      accessorKey: 'sgst',
      header: 'SGST',
      cell: ({ row }) => formatCurrency(row.original.sgst),
    },
  ];

  const validInvoices = b2bData?.items.filter((i: B2BInvoiceDisplay) => i.status === 'VALID').length ?? 0;
  const errorInvoices = b2bData?.items.filter((i: B2BInvoiceDisplay) => i.status === 'ERROR').length ?? 0;
  const warningInvoices = b2bData?.items.filter((i: B2BInvoiceDisplay) => i.status === 'WARNING').length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="GSTR-1 Return"
        description="Outward supplies (Sales) - Monthly/Quarterly filing"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
              <RefreshCw className={`mr-2 h-4 w-4 ${generateMutation.isPending ? 'animate-spin' : ''}`} />
              {generateMutation.isPending ? 'Refreshing...' : 'Refresh Data'}
            </Button>
            <Button variant="outline" onClick={handleExportJSON}>
              <FileJson className="mr-2 h-4 w-4" />
              Export JSON
            </Button>
            <Button onClick={handlePreviewFiling} disabled={isFiling}>
              {isFiling ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              {isFiling ? 'Processing...' : 'File Return'}
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

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Invoices</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_invoices ?? 0}</div>
            <div className="text-xs text-muted-foreground">Across all sections</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Taxable Value</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(summary?.total_taxable_value ?? 0)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Tax</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(summary?.total_tax ?? 0)}</div>
            <div className="text-xs text-muted-foreground">IGST + CGST + SGST + Cess</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">HSN Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.hsn_summary_count ?? 0}</div>
            <div className="text-xs text-muted-foreground">Unique HSN codes</div>
          </CardContent>
        </Card>
      </div>

      {/* Tax Breakup */}
      <Card>
        <CardHeader>
          <CardTitle>Tax Breakup</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-sm text-blue-600 font-medium">IGST</div>
              <div className="text-xl font-bold">{formatCurrency(summary?.total_igst ?? 0)}</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-sm text-green-600 font-medium">CGST</div>
              <div className="text-xl font-bold">{formatCurrency(summary?.total_cgst ?? 0)}</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-sm text-purple-600 font-medium">SGST</div>
              <div className="text-xl font-bold">{formatCurrency(summary?.total_sgst ?? 0)}</div>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded-lg">
              <div className="text-sm text-orange-600 font-medium">Cess</div>
              <div className="text-xl font-bold">{formatCurrency(summary?.total_cess ?? 0)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs for Sections */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="summary">Section Summary</TabsTrigger>
          <TabsTrigger value="b2b">B2B Invoices</TabsTrigger>
          <TabsTrigger value="hsn">HSN Summary</TabsTrigger>
          <TabsTrigger value="errors">Errors & Warnings</TabsTrigger>
        </TabsList>

        <TabsContent value="summary" className="space-y-4 mt-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">B2B - Tax Invoice</CardTitle>
                <CardDescription>Supplies to registered persons</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{summary?.b2b_invoices ?? 0} invoices</div>
                <div className="text-sm text-muted-foreground">{formatCurrency(summary?.b2b_value ?? 0)}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">B2C Large</CardTitle>
                <CardDescription>Inter-state B2C &gt; ₹2.5L</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{summary?.b2c_large_invoices ?? 0} invoices</div>
                <div className="text-sm text-muted-foreground">{formatCurrency(summary?.b2c_large_value ?? 0)}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">B2CS</CardTitle>
                <CardDescription>Intra-state B2C supplies</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(summary?.b2cs_value ?? 0)}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Credit/Debit Notes</CardTitle>
                <CardDescription>Amendments to invoices</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{summary?.credit_debit_notes ?? 0} notes</div>
                <div className="text-sm text-muted-foreground">{formatCurrency(summary?.cdn_value ?? 0)}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Exports</CardTitle>
                <CardDescription>Export supplies</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{summary?.exports_invoices ?? 0} invoices</div>
                <div className="text-sm text-muted-foreground">{formatCurrency(summary?.exports_value ?? 0)}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Nil Rated/Exempt</CardTitle>
                <CardDescription>Zero-rated supplies</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(summary?.nil_rated_value ?? 0)}</div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="b2b" className="mt-4">
          <div className="flex items-center gap-4 mb-4">
            <Badge variant="outline" className="bg-green-50">
              <CheckCircle className="mr-1 h-3 w-3" /> {validInvoices} Valid
            </Badge>
            <Badge variant="outline" className="bg-yellow-50">
              <AlertTriangle className="mr-1 h-3 w-3" /> {warningInvoices} Warnings
            </Badge>
            <Badge variant="outline" className="bg-red-50">
              <AlertTriangle className="mr-1 h-3 w-3" /> {errorInvoices} Errors
            </Badge>
          </div>
          <DataTable<B2BInvoiceDisplay, unknown>
            columns={b2bColumns}
            data={b2bData?.items ?? []}
            searchKey="invoice_number"
            searchPlaceholder="Search invoices..."
            isLoading={summaryLoading}
          />
        </TabsContent>

        <TabsContent value="hsn" className="mt-4">
          <DataTable<HSNSummaryDisplay, unknown>
            columns={hsnColumns}
            data={hsnData?.items ?? []}
            searchKey="hsn_code"
            searchPlaceholder="Search HSN codes..."
            isLoading={summaryLoading}
          />
        </TabsContent>

        <TabsContent value="errors" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Validation Errors & Warnings</CardTitle>
              <CardDescription>Issues that need to be resolved before filing</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Invoice</TableHead>
                    <TableHead>Issue</TableHead>
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {b2bData?.items.filter((i: B2BInvoiceDisplay) => i.status !== 'VALID').map((item: B2BInvoiceDisplay) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <Badge className={statusColors[item.status]}>{item.status}</Badge>
                      </TableCell>
                      <TableCell className="font-medium">{item.invoice_number}</TableCell>
                      <TableCell>{item.error_message}</TableCell>
                      <TableCell>
                        <Button size="sm" variant="outline">Fix</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Filing Confirmation Dialog */}
      <Dialog open={showFilingDialog} onOpenChange={setShowFilingDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Confirm GSTR-1 Filing</DialogTitle>
            <DialogDescription>
              Review the details before filing to GST portal
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Period</p>
                <p className="font-medium">{summary?.return_period}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Invoices</p>
                <p className="font-medium">{summary?.total_invoices}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Taxable Value</p>
                <p className="font-medium">{formatCurrency(summary?.total_taxable_value ?? 0)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Tax</p>
                <p className="font-medium">{formatCurrency((summary?.total_igst ?? 0) + (summary?.total_cgst ?? 0) + (summary?.total_sgst ?? 0))}</p>
              </div>
            </div>
            {errorInvoices > 0 && (
              <div className="bg-red-50 p-3 rounded-md">
                <p className="text-sm text-red-600 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  {errorInvoices} invoice(s) have errors. Please fix before filing.
                </p>
              </div>
            )}
            <div className="border-t pt-4">
              <p className="text-sm text-muted-foreground">
                By clicking "File to GST Portal", you confirm that the data is accurate and authorize filing.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowFilingDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleFileReturn}
              disabled={isFiling || errorInvoices > 0}
            >
              {isFiling ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Send className="mr-2 h-4 w-4" />
              )}
              {isFiling ? 'Filing...' : 'File to GST Portal'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
