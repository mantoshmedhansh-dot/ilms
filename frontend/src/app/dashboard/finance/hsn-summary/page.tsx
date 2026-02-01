'use client';

import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { FileText, Download, Plus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import { formatCurrency } from '@/lib/utils';
import { gstReportsApi, periodsApi } from '@/lib/api';

interface HSNItem {
  id: string;
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

interface HSNSummaryStats {
  total_hsn_codes: number;
  total_taxable_value: number;
  total_tax: number;
  gst_5_value: number;
  gst_12_value: number;
  gst_18_value: number;
  gst_28_value: number;
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

export default function HSNSummaryPage() {
  const [selectedPeriod, setSelectedPeriod] = useState<string>('');
  const [activeTab, setActiveTab] = useState('outward');

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

  // Fetch HSN summary data from real API
  const { data: hsnData, isLoading } = useQuery({
    queryKey: ['hsn-summary', month, year],
    queryFn: () => gstReportsApi.getHSNSummary(month, year),
  });

  // Derive stats from API response
  const stats: HSNSummaryStats | undefined = hsnData?.summary;

  // Get outward data (sales)
  const outwardData = {
    items: hsnData?.outward_items ?? [],
  };
  const outwardLoading = isLoading && activeTab === 'outward';

  // Get inward data (purchases)
  const inwardData = {
    items: hsnData?.inward_items ?? [],
  };
  const inwardLoading = isLoading && activeTab === 'inward';

  const columns: ColumnDef<HSNItem>[] = [
    {
      accessorKey: 'hsn_code',
      header: 'HSN/SAC',
      cell: ({ row }) => (
        <div>
          <div className="font-mono font-medium">{row.original.hsn_code}</div>
          <div className="text-xs text-muted-foreground max-w-56 truncate">{row.original.description}</div>
        </div>
      ),
    },
    {
      accessorKey: 'uqc',
      header: 'UQC',
      cell: ({ row }) => <Badge variant="outline">{row.original.uqc}</Badge>,
    },
    {
      accessorKey: 'total_quantity',
      header: 'Quantity',
      cell: ({ row }) => (row.original.total_quantity ?? 0).toLocaleString(),
    },
    {
      accessorKey: 'taxable_value',
      header: 'Taxable Value',
      cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.taxable_value)}</span>,
    },
    {
      accessorKey: 'rate',
      header: 'Rate',
      cell: ({ row }) => (
        <Badge className="bg-blue-100 text-blue-800">{row.original.rate}%</Badge>
      ),
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
    {
      accessorKey: 'total_value',
      header: 'Total Value',
      cell: ({ row }) => <span className="font-bold">{formatCurrency(row.original.total_value)}</span>,
    },
  ];

  const handleExportSummary = () => {
    if (!hsnData) {
      toast.error('No data to export');
      return;
    }
    const exportData = {
      period: `${month.toString().padStart(2, '0')}${year}`,
      summary: stats,
      outward_hsn: outwardData.items,
      inward_hsn: inwardData.items,
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `HSN_Summary_${month.toString().padStart(2, '0')}${year}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('HSN Summary exported');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="HSN Summary"
        description="HSN/SAC wise tax summary for GST returns"
        actions={
          <Button variant="outline" onClick={handleExportSummary}>
            <Download className="mr-2 h-4 w-4" />
            Export Summary
          </Button>
        }
      />

      {/* Period Selector */}
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

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total HSN Codes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_hsn_codes ?? 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Taxable Value</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats?.total_taxable_value ?? 0)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Tax</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats?.total_tax ?? 0)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Avg Tax Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {((stats?.total_tax ?? 0) / (stats?.total_taxable_value ?? 1) * 100).toFixed(1)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tax Rate Breakup */}
      <Card>
        <CardHeader>
          <CardTitle>Tax Rate Wise Breakup</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-sm text-green-600 font-medium">5% GST</div>
              <div className="text-xl font-bold">{formatCurrency(stats?.gst_5_value ?? 0)}</div>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-sm text-blue-600 font-medium">12% GST</div>
              <div className="text-xl font-bold">{formatCurrency(stats?.gst_12_value ?? 0)}</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-sm text-purple-600 font-medium">18% GST</div>
              <div className="text-xl font-bold">{formatCurrency(stats?.gst_18_value ?? 0)}</div>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded-lg">
              <div className="text-sm text-orange-600 font-medium">28% GST</div>
              <div className="text-xl font-bold">{formatCurrency(stats?.gst_28_value ?? 0)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* HSN Details */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="outward">Outward HSN (Sales)</TabsTrigger>
          <TabsTrigger value="inward">Inward HSN (Purchases)</TabsTrigger>
        </TabsList>

        <TabsContent value="outward" className="mt-4">
          <DataTable<HSNItem, unknown>
            columns={columns}
            data={outwardData?.items ?? []}
            searchKey="hsn_code"
            searchPlaceholder="Search HSN codes..."
            isLoading={outwardLoading}
          />
        </TabsContent>

        <TabsContent value="inward" className="mt-4">
          <DataTable<HSNItem, unknown>
            columns={columns}
            data={inwardData?.items ?? []}
            searchKey="hsn_code"
            searchPlaceholder="Search HSN codes..."
            isLoading={inwardLoading}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
