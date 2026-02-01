'use client';

import { useState, useMemo, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, Download, RefreshCw, CheckCircle, AlertTriangle, Calendar, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
import { PageHeader } from '@/components/common';
import { formatCurrency, formatDate } from '@/lib/utils';
import { gstReportsApi, periodsApi } from '@/lib/api';

interface GSTR2AInvoice {
  id: string;
  gstin: string | null;
  vendor_name: string;
  party_name: string;
  invoice_number: string;
  invoice_date: string | null;
  taxable_value: number;
  igst: number;
  cgst: number;
  sgst: number;
  total_value: number;
  status: 'MATCHED' | 'PENDING';
  match_status: string;
  mismatch_reason?: string;
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

const matchStatusColors: Record<string, string> = {
  MATCHED: 'bg-green-100 text-green-800',
  MISMATCHED: 'bg-red-100 text-red-800',
  NEW: 'bg-blue-100 text-blue-800',
  MISSING: 'bg-yellow-100 text-yellow-800',
};

export default function GSTR2APage() {
  const queryClient = useQueryClient();
  const [selectedPeriod, setSelectedPeriod] = useState<string>('');

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

  const { data: gstr2aData, isLoading } = useQuery({
    queryKey: ['gstr2a-report', month, year],
    queryFn: () => gstReportsApi.getGSTR2A(month, year),
  });

  // Derive summary from API data
  const summary = gstr2aData?.summary ? {
    return_period: gstr2aData.return_period,
    last_synced: new Date().toISOString(),
    total_invoices: gstr2aData.summary.total_invoices || 0,
    matched_invoices: gstr2aData.invoices?.filter((inv: GSTR2AInvoice) => inv.status === 'MATCHED').length || 0,
    mismatched_invoices: 0,
    new_invoices: gstr2aData.invoices?.filter((inv: GSTR2AInvoice) => inv.status === 'PENDING').length || 0,
    total_taxable_value: gstr2aData.summary.total_taxable_value || 0,
    total_igst: gstr2aData.summary.total_igst || 0,
    total_cgst: gstr2aData.summary.total_cgst || 0,
    total_sgst: gstr2aData.summary.total_sgst || 0,
    itc_available: gstr2aData.summary.itc_available || 0,
  } : null;

  // Transform invoices data
  const invoicesData = gstr2aData ? {
    items: gstr2aData.invoices?.map((inv: GSTR2AInvoice) => ({
      ...inv,
      party_name: inv.vendor_name,
      match_status: inv.status,
    })) || [],
  } : { items: [] };

  const [isSyncing, setIsSyncing] = useState(false);

  const handleSyncFromPortal = async () => {
    setIsSyncing(true);
    try {
      // For now, just refresh the data from our backend
      await queryClient.invalidateQueries({ queryKey: ['gstr2a-report', month, year] });
      toast.info('GSTR-2A sync from GST portal is coming soon. Data refreshed from local records.');
    } catch (error) {
      toast.error('Failed to refresh data');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleExport = () => {
    if (!gstr2aData) {
      toast.error('No data to export');
      return;
    }
    const blob = new Blob([JSON.stringify(gstr2aData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `GSTR2A_${month.toString().padStart(2, '0')}${year}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('GSTR-2A data exported');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="GSTR-2A"
        description="Auto-populated purchase register from supplier filings"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleSyncFromPortal} disabled={isSyncing}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isSyncing ? 'animate-spin' : ''}`} />
              {isSyncing ? 'Syncing...' : 'Sync from GST Portal'}
            </Button>
            <Button variant="outline" onClick={handleExport}>
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
        }
      />

      {/* Period Selector */}
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
        <div className="text-sm text-muted-foreground">
          Last synced: {summary?.last_synced}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Invoices</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_invoices ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="bg-green-50 border-green-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-green-800">Matched</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-900">{summary?.matched_invoices ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="bg-red-50 border-red-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-red-800">Mismatched</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-900">{summary?.mismatched_invoices ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="bg-blue-50 border-blue-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-blue-800">New (Not in Books)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-900">{summary?.new_invoices ?? 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* ITC Summary */}
      <Card>
        <CardHeader>
          <CardTitle>ITC Available as per GSTR-2A</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="text-center p-4 bg-muted rounded-lg">
              <div className="text-sm text-muted-foreground">Taxable Value</div>
              <div className="text-xl font-bold">{formatCurrency(summary?.total_taxable_value ?? 0)}</div>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-sm text-blue-600">IGST</div>
              <div className="text-xl font-bold">{formatCurrency(summary?.total_igst ?? 0)}</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-sm text-green-600">CGST</div>
              <div className="text-xl font-bold">{formatCurrency(summary?.total_cgst ?? 0)}</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-sm text-purple-600">SGST</div>
              <div className="text-xl font-bold">{formatCurrency(summary?.total_sgst ?? 0)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Invoice List */}
      <Card>
        <CardHeader>
          <CardTitle>Invoice Details</CardTitle>
          <CardDescription>Invoices reported by your suppliers</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Supplier</TableHead>
                <TableHead>Invoice</TableHead>
                <TableHead className="text-right">Taxable Value</TableHead>
                <TableHead className="text-right">Tax</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoicesData?.items.map((invoice: GSTR2AInvoice) => (
                <TableRow key={invoice.id}>
                  <TableCell>
                    <div>{invoice.party_name}</div>
                    <div className="text-xs text-muted-foreground font-mono">{invoice.gstin}</div>
                  </TableCell>
                  <TableCell>
                    <div>{invoice.invoice_number}</div>
                    <div className="text-xs text-muted-foreground">{invoice.invoice_date}</div>
                  </TableCell>
                  <TableCell className="text-right">{formatCurrency(invoice.taxable_value)}</TableCell>
                  <TableCell className="text-right">
                    {invoice.igst > 0 ? (
                      <span>IGST: {formatCurrency(invoice.igst)}</span>
                    ) : (
                      <span>C+S: {formatCurrency(invoice.cgst + invoice.sgst)}</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right font-medium">{formatCurrency(invoice.total_value)}</TableCell>
                  <TableCell>
                    <Badge className={matchStatusColors[invoice.match_status]}>
                      {invoice.match_status}
                    </Badge>
                    {invoice.mismatch_reason && (
                      <div className="text-xs text-red-600 mt-1">{invoice.mismatch_reason}</div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
