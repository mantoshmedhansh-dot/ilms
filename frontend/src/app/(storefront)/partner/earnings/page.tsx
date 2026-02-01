'use client';

import { useEffect, useState } from 'react';
import { usePartnerStore, PartnerCommission } from '@/lib/storefront/partner-store';
import { partnerApi } from '@/lib/storefront/partner-api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Wallet, TrendingUp, Clock, CheckCircle, Loader2 } from 'lucide-react';
import { formatCurrency, formatDate } from '@/lib/utils';

const statusColors: Record<string, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  APPROVED: 'bg-blue-100 text-blue-800',
  PAID: 'bg-green-100 text-green-800',
  CANCELLED: 'bg-red-100 text-red-800',
};

export default function PartnerEarningsPage() {
  const { dashboardStats, commissions, setCommissions, setDashboardStats } = usePartnerStore();
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('all');
  const [selectedCommission, setSelectedCommission] = useState<PartnerCommission | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsResponse, commissionsResponse] = await Promise.all([
          partnerApi.getDashboardStats(),
          partnerApi.getCommissions(activeTab === 'all' ? undefined : activeTab, page, 20),
        ]);
        setDashboardStats(statsResponse);
        if (page === 1) {
          setCommissions(commissionsResponse.items || []);
        } else {
          setCommissions([...commissions, ...(commissionsResponse.items || [])]);
        }
        setHasMore((commissionsResponse.items || []).length === 20);
      } catch (error) {
        console.error('Failed to fetch earnings:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [activeTab, page]);

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    setPage(1);
    setIsLoading(true);
  };

  if (isLoading && page === 1) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const stats = dashboardStats || {
    total_earnings: 0,
    pending_earnings: 0,
    paid_earnings: 0,
    this_month_earnings: 0,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Earnings</h1>
        <p className="text-muted-foreground">Track your commissions and earnings</p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Earnings</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats.total_earnings)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">This Month</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats.this_month_earnings)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              {formatCurrency(stats.pending_earnings)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Paid Out</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {formatCurrency(stats.paid_earnings)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Commission History */}
      <Card>
        <CardHeader>
          <CardTitle>Commission History</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={handleTabChange}>
            <TabsList>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="PENDING">Pending</TabsTrigger>
              <TabsTrigger value="APPROVED">Approved</TabsTrigger>
              <TabsTrigger value="PAID">Paid</TabsTrigger>
            </TabsList>

            <TabsContent value={activeTab} className="mt-4">
              {commissions.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-muted-foreground">No commissions found</p>
                </div>
              ) : (
                <>
                  <div className="rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Order</TableHead>
                          <TableHead>Date</TableHead>
                          <TableHead>Customer</TableHead>
                          <TableHead className="text-right">Order Amount</TableHead>
                          <TableHead className="text-right">Commission</TableHead>
                          <TableHead>Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {commissions.map((commission) => (
                          <TableRow
                            key={commission.id}
                            className="cursor-pointer hover:bg-muted/50"
                            onClick={() => setSelectedCommission(commission)}
                          >
                            <TableCell className="font-mono text-sm">
                              {commission.order_number}
                            </TableCell>
                            <TableCell>{formatDate(commission.order_date)}</TableCell>
                            <TableCell>{commission.customer_name}</TableCell>
                            <TableCell className="text-right">
                              {formatCurrency(commission.order_amount)}
                            </TableCell>
                            <TableCell className="text-right font-medium">
                              {formatCurrency(commission.net_amount)}
                            </TableCell>
                            <TableCell>
                              <Badge className={statusColors[commission.status] || ''}>
                                {commission.status}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {hasMore && (
                    <div className="flex justify-center mt-4">
                      <Button
                        variant="outline"
                        onClick={() => setPage(page + 1)}
                        disabled={isLoading}
                      >
                        {isLoading ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : null}
                        Load More
                      </Button>
                    </div>
                  )}
                </>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Commission Detail Dialog */}
      <Dialog open={!!selectedCommission} onOpenChange={() => setSelectedCommission(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Commission Details</DialogTitle>
            <DialogDescription>
              Order {selectedCommission?.order_number}
            </DialogDescription>
          </DialogHeader>

          {selectedCommission && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Order Date</p>
                  <p className="font-medium">{formatDate(selectedCommission.order_date)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Customer</p>
                  <p className="font-medium">{selectedCommission.customer_name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Order Amount</p>
                  <p className="font-medium">{formatCurrency(selectedCommission.order_amount)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Commission Rate</p>
                  <p className="font-medium">{selectedCommission.commission_rate}%</p>
                </div>
              </div>

              <div className="border-t pt-4">
                <div className="flex justify-between mb-2">
                  <span className="text-muted-foreground">Gross Commission</span>
                  <span>{formatCurrency(selectedCommission.commission_amount)}</span>
                </div>
                <div className="flex justify-between mb-2 text-red-600">
                  <span>TDS Deducted (5%)</span>
                  <span>-{formatCurrency(selectedCommission.tds_amount)}</span>
                </div>
                <div className="flex justify-between font-bold text-lg border-t pt-2">
                  <span>Net Amount</span>
                  <span className="text-green-600">
                    {formatCurrency(selectedCommission.net_amount)}
                  </span>
                </div>
              </div>

              <div className="flex justify-center">
                <Badge className={statusColors[selectedCommission.status] || ''}>
                  {selectedCommission.status}
                </Badge>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
