'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FileCheck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Calendar,
  ExternalLink,
  RefreshCw,
  Download,
  Loader2,
  TrendingUp,
  Shield,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
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
import { gstFilingApi } from '@/lib/api';

interface FilingRecord {
  id: string;
  return_type: string;
  period: string;
  status: 'PENDING' | 'FILED' | 'LATE' | 'ERROR';
  due_date: string;
  filed_date?: string;
  arn?: string;
  taxable_value: number;
  tax_liability: number;
}

const statusColors: Record<string, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  FILED: 'bg-green-100 text-green-800',
  LATE: 'bg-orange-100 text-orange-800',
  ERROR: 'bg-red-100 text-red-800',
};

const statusIcons: Record<string, React.ReactNode> = {
  PENDING: <Clock className="h-4 w-4" />,
  FILED: <CheckCircle2 className="h-4 w-4" />,
  LATE: <AlertTriangle className="h-4 w-4" />,
  ERROR: <AlertTriangle className="h-4 w-4" />,
};

export default function GSTFilingDashboardPage() {
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const currentYear = new Date().getFullYear();

  const { data: dashboardData, isLoading, refetch } = useQuery({
    queryKey: ['gst-filing-dashboard', currentYear],
    queryFn: () => gstFilingApi.getDashboard({ year: currentYear }),
  });

  const { data: filingHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['gst-filing-history'],
    queryFn: () => gstFilingApi.getFilingHistory({ limit: 12 }),
  });

  const handleAuthenticate = async () => {
    try {
      setIsAuthenticating(true);
      const result = await gstFilingApi.authenticate();
      if (result.success) {
        setIsAuthenticated(true);
        toast.success('Successfully authenticated with GST Portal');
      } else {
        toast.error(result.message || 'Authentication failed');
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to authenticate with GST Portal');
    } finally {
      setIsAuthenticating(false);
    }
  };

  // Default empty state when no data from API
  const filingStats = dashboardData || {
    total_returns: 0,
    filed_on_time: 0,
    filed_late: 0,
    pending: 0,
    compliance_rate: 0,
    total_tax_paid: 0,
    total_itc_claimed: 0,
  };

  // Calculate upcoming due dates dynamically based on current date
  const getUpcomingDueDates = () => {
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    // GSTR-1 due on 11th of next month, GSTR-3B due on 20th of next month
    const dates = [];

    // Current month returns (if not yet due)
    const gstr1DueDate = new Date(currentYear, currentMonth + 1, 11);
    const gstr3bDueDate = new Date(currentYear, currentMonth + 1, 20);

    if (gstr1DueDate > now) {
      dates.push({
        return_type: 'GSTR-1',
        period: now.toLocaleString('default', { month: 'long', year: 'numeric' }),
        due_date: gstr1DueDate.toISOString().split('T')[0],
        status: 'PENDING',
      });
    }

    if (gstr3bDueDate > now) {
      dates.push({
        return_type: 'GSTR-3B',
        period: now.toLocaleString('default', { month: 'long', year: 'numeric' }),
        due_date: gstr3bDueDate.toISOString().split('T')[0],
        status: 'PENDING',
      });
    }

    // Next month GSTR-1
    const nextMonth = new Date(currentYear, currentMonth + 1, 1);
    const nextGstr1DueDate = new Date(nextMonth.getFullYear(), nextMonth.getMonth() + 1, 11);
    dates.push({
      return_type: 'GSTR-1',
      period: nextMonth.toLocaleString('default', { month: 'long', year: 'numeric' }),
      due_date: nextGstr1DueDate.toISOString().split('T')[0],
      status: 'UPCOMING',
    });

    return dates.slice(0, 3); // Show max 3
  };

  const upcomingDueDates = getUpcomingDueDates();

  // Use actual API data, empty array if no data
  const recentFilings: FilingRecord[] = (filingHistory?.items || []) as FilingRecord[];

  return (
    <div className="space-y-6">
      <PageHeader
        title="GST Filing Dashboard"
        description="Monitor GST compliance status and file returns"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => refetch()} disabled={isLoading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            {!isAuthenticated ? (
              <Button onClick={handleAuthenticate} disabled={isAuthenticating}>
                {isAuthenticating ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Shield className="mr-2 h-4 w-4" />
                )}
                {isAuthenticating ? 'Connecting...' : 'Connect GST Portal'}
              </Button>
            ) : (
              <Badge variant="outline" className="bg-green-50 text-green-700 px-4 py-2">
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Connected to GST Portal
              </Badge>
            )}
          </div>
        }
      />

      {/* Compliance Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Compliance Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="text-3xl font-bold">{filingStats.compliance_rate}%</div>
              <Progress value={filingStats.compliance_rate} className="flex-1" />
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {filingStats.filed_on_time} of {filingStats.total_returns} returns filed on time
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Tax Paid (FY)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{formatCurrency(filingStats.total_tax_paid)}</div>
            <p className="text-xs text-muted-foreground mt-2">Across all GST returns</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              ITC Claimed (FY)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">
              {formatCurrency(filingStats.total_itc_claimed)}
            </div>
            <p className="text-xs text-muted-foreground mt-2">Input Tax Credit utilized</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Pending Returns
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {filingStats.pending}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {filingStats.filed_late > 0 && (
                <span className="text-orange-600">{filingStats.filed_late} filed late this year</span>
              )}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Upcoming Due Dates */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Upcoming Due Dates
          </CardTitle>
          <CardDescription>Returns due in the next 30 days</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {upcomingDueDates.map((item, idx) => (
              <Card key={idx} className="bg-muted/30">
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="outline">{item.return_type}</Badge>
                    <Badge className={item.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-800'}>
                      {item.status}
                    </Badge>
                  </div>
                  <p className="font-medium">{item.period}</p>
                  <p className="text-sm text-muted-foreground">
                    Due: {formatDate(item.due_date)}
                  </p>
                  {item.status === 'PENDING' && (
                    <Button size="sm" className="w-full mt-3" asChild>
                      <a href={item.return_type === 'GSTR-1' ? '/dashboard/finance/gstr1' : '/dashboard/finance/gstr3b'}>
                        File Now
                      </a>
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => window.location.href = '/dashboard/finance/gstr1'}>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <FileCheck className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h3 className="font-medium">GSTR-1</h3>
                <p className="text-sm text-muted-foreground">Outward Supplies</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => window.location.href = '/dashboard/finance/gstr2a'}>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-100 rounded-lg">
                <Download className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <h3 className="font-medium">GSTR-2A</h3>
                <p className="text-sm text-muted-foreground">Auto-drafted ITC</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => window.location.href = '/dashboard/finance/gstr3b'}>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-lg">
                <TrendingUp className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <h3 className="font-medium">GSTR-3B</h3>
                <p className="text-sm text-muted-foreground">Summary Return</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => window.location.href = '/dashboard/finance/itc'}>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-orange-100 rounded-lg">
                <Shield className="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <h3 className="font-medium">ITC Management</h3>
                <p className="text-sm text-muted-foreground">Reconcile & Claim</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filing History */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Filing History</CardTitle>
          <CardDescription>Last 12 months of GST returns</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Return Type</TableHead>
                <TableHead>Period</TableHead>
                <TableHead>Due Date</TableHead>
                <TableHead>Filed Date</TableHead>
                <TableHead>ARN</TableHead>
                <TableHead className="text-right">Tax Liability</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {historyLoading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : recentFilings.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    No filing history found
                  </TableCell>
                </TableRow>
              ) : (
                recentFilings.map((filing) => (
                  <TableRow key={filing.id}>
                    <TableCell>
                      <Badge variant="outline">{filing.return_type}</Badge>
                    </TableCell>
                    <TableCell className="font-medium">{filing.period}</TableCell>
                    <TableCell>{formatDate(filing.due_date)}</TableCell>
                    <TableCell>
                      {filing.filed_date ? formatDate(filing.filed_date) : '-'}
                    </TableCell>
                    <TableCell>
                      {filing.arn ? (
                        <span className="font-mono text-sm">{filing.arn}</span>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(filing.tax_liability)}
                    </TableCell>
                    <TableCell>
                      <Badge className={statusColors[filing.status]}>
                        <span className="flex items-center gap-1">
                          {statusIcons[filing.status]}
                          {filing.status}
                        </span>
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* GST Portal Link */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="font-medium">GST Portal</p>
                <p className="text-sm text-muted-foreground">
                  Access official GST portal for filing and verification
                </p>
              </div>
            </div>
            <Button variant="outline" asChild>
              <a href="https://gst.gov.in" target="_blank" rel="noopener noreferrer">
                <ExternalLink className="mr-2 h-4 w-4" />
                Open GST Portal
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
