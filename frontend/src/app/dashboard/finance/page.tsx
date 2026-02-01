'use client';

import { useQuery } from '@tanstack/react-query';
import { BookOpen, FileSpreadsheet, Landmark, Calendar, FileText, TrendingUp, TrendingDown, IndianRupee, ArrowUpRight, ArrowDownRight, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/common';
import { formatCurrency, formatDate } from '@/lib/utils';
import { gstReportsApi } from '@/lib/api';

interface FinanceStats {
  total_revenue: number;
  revenue_change: number;
  total_expenses: number;
  expenses_change: number;
  gross_profit: number;
  profit_margin: number;
  accounts_receivable: number;
  accounts_payable: number;
  pending_approvals: number;
  current_period: {
    name: string;
    start_date: string;
    end_date: string;
    status: 'OPEN' | 'CLOSING' | 'CLOSED';
  };
  gst_filing: {
    gstr1_due: string;
    gstr1_status: 'FILED' | 'PENDING' | 'OVERDUE';
    gstr3b_due: string;
    gstr3b_status: 'FILED' | 'PENDING' | 'OVERDUE';
  };
}

const gstStatusColors: Record<string, string> = {
  FILED: 'bg-green-100 text-green-800',
  PENDING: 'bg-yellow-100 text-yellow-800',
  OVERDUE: 'bg-red-100 text-red-800',
};

const periodStatusColors: Record<string, string> = {
  OPEN: 'bg-green-100 text-green-800',
  CLOSING: 'bg-yellow-100 text-yellow-800',
  CLOSED: 'bg-gray-100 text-gray-800',
};

export default function FinancePage() {
  const { data: stats, isLoading } = useQuery<FinanceStats>({
    queryKey: ['finance-dashboard'],
    queryFn: gstReportsApi.getFinanceDashboard,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Finance"
        description="Accounting, journal entries, and financial reporting"
        actions={
          <Button asChild>
            <Link href="/dashboard/finance/journal-entries/new">
              <FileSpreadsheet className="mr-2 h-4 w-4" />
              New Entry
            </Link>
          </Button>
        }
      />

      {/* Financial Summary */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <IndianRupee className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats?.total_revenue ?? 0)}</div>
            <div className={`flex items-center text-xs mt-1 ${(stats?.revenue_change ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {(stats?.revenue_change ?? 0) >= 0 ? <ArrowUpRight className="h-3 w-3 mr-1" /> : <ArrowDownRight className="h-3 w-3 mr-1" />}
              {(stats?.revenue_change ?? 0) >= 0 ? '+' : ''}{stats?.revenue_change ?? 0}% from last month
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Expenses</CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats?.total_expenses ?? 0)}</div>
            <div className="flex items-center text-xs text-red-600 mt-1">
              <ArrowDownRight className="h-3 w-3 mr-1" />
              +{stats?.expenses_change ?? 0}% from last month
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Gross Profit</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats?.gross_profit ?? 0)}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {stats?.profit_margin ?? 0}% profit margin
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Approvals</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.pending_approvals ?? 0}</div>
            <div className="text-xs text-muted-foreground mt-1">
              Journal entries awaiting review
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Current Period & GST Status */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Current Financial Period</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-semibold">{stats?.current_period?.name}</div>
                <div className="text-sm text-muted-foreground">
                  {stats?.current_period?.start_date} to {stats?.current_period?.end_date}
                </div>
              </div>
              <Badge className={periodStatusColors[stats?.current_period?.status ?? 'OPEN']}>
                {stats?.current_period?.status}
              </Badge>
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Receivables</span>
                <span className="font-medium">{formatCurrency(stats?.accounts_receivable ?? 0)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Payables</span>
                <span className="font-medium">{formatCurrency(stats?.accounts_payable ?? 0)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">GST Filing Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">GSTR-1 (Sales)</div>
                <div className="text-xs text-muted-foreground">Due: {stats?.gst_filing?.gstr1_due}</div>
              </div>
              <div className="flex items-center gap-2">
                <Badge className={gstStatusColors[stats?.gst_filing?.gstr1_status ?? 'PENDING']}>
                  {stats?.gst_filing?.gstr1_status}
                </Badge>
                <Button size="sm" variant="outline" asChild>
                  <Link href="/dashboard/finance/gstr1">View</Link>
                </Button>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">GSTR-3B (Summary)</div>
                <div className="text-xs text-muted-foreground">Due: {stats?.gst_filing?.gstr3b_due}</div>
              </div>
              <div className="flex items-center gap-2">
                <Badge className={gstStatusColors[stats?.gst_filing?.gstr3b_status ?? 'PENDING']}>
                  {stats?.gst_filing?.gstr3b_status}
                </Badge>
                <Button size="sm" variant="outline" asChild>
                  <Link href="/dashboard/finance/gstr3b">View</Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Module Links */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Link href="/dashboard/finance/chart-of-accounts">
          <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Chart of Accounts</CardTitle>
              <BookOpen className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Manage account structure</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/finance/journal-entries">
          <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Journal Entries</CardTitle>
              <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Record transactions</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/finance/general-ledger">
          <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">General Ledger</CardTitle>
              <Landmark className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">View account balances</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/finance/periods">
          <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Financial Periods</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Manage fiscal periods</p>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* GST Reports */}
      <div>
        <h3 className="text-lg font-semibold mb-4">GST Reports</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Link href="/dashboard/finance/gstr1">
            <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">GSTR-1</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Outward supplies (Sales)</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/dashboard/finance/gstr3b">
            <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">GSTR-3B</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Summary returns filing</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/dashboard/finance/gstr2a">
            <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">GSTR-2A</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Auto-populated purchase data</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/dashboard/finance/hsn-summary">
            <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">HSN Summary</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">HSN-wise tax summary</p>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>
    </div>
  );
}
