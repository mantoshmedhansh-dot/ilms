'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, XCircle, AlertTriangle, FileText, Package, Truck, ArrowRight, RefreshCw, Eye, CheckSquare } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency, formatDate } from '@/lib/utils';

interface MatchItem {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  unit: string;
  // PO Details
  po_quantity: number;
  po_rate: number;
  po_amount: number;
  // GRN Details
  grn_quantity: number;
  grn_rate: number;
  grn_amount: number;
  // Invoice Details
  invoice_quantity: number;
  invoice_rate: number;
  invoice_amount: number;
  // Match Status
  quantity_match: boolean;
  rate_match: boolean;
  amount_match: boolean;
  match_status: 'MATCHED' | 'PARTIAL' | 'MISMATCH';
  variance_quantity: number;
  variance_rate: number;
  variance_amount: number;
}

interface ThreeWayMatch {
  id: string;
  invoice_number: string;
  invoice_id: string;
  invoice_date: string;
  invoice_amount: number;
  po_number: string;
  po_id: string;
  po_date: string;
  po_amount: number;
  grn_number: string;
  grn_id: string;
  grn_date: string;
  grn_amount: number;
  vendor_name: string;
  vendor_code: string;
  status: 'PENDING' | 'MATCHED' | 'PARTIAL_MATCH' | 'MISMATCH' | 'RESOLVED';
  match_percent: number;
  items: MatchItem[];
  total_variance: number;
  created_at: string;
}

interface MatchStats {
  total_pending: number;
  matched: number;
  partial: number;
  mismatch: number;
  total_variance_amount: number;
}

const threeWayMatchApi = {
  list: async (params?: { status?: string }): Promise<{ items: ThreeWayMatch[]; total: number }> => {
    try {
      const { data } = await apiClient.get('/purchase/three-way-match', { params });
      return data;
    } catch {
      return { items: [], total: 0 };
    }
  },
  getStats: async (): Promise<MatchStats> => {
    try {
      const { data } = await apiClient.get('/purchase/three-way-match/stats');
      return data;
    } catch {
      return { total_pending: 0, matched: 0, partial: 0, mismatch: 0, total_variance_amount: 0 };
    }
  },
  getDetail: async (id: string): Promise<ThreeWayMatch | null> => {
    try {
      const { data } = await apiClient.get(`/purchase/three-way-match/${id}`);
      return data;
    } catch {
      return null;
    }
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post(`/purchase/three-way-match/${id}/approve`);
    return data;
  },
  resolveVariance: async (id: string, resolution: { action: string; notes: string }) => {
    const { data } = await apiClient.post(`/purchase/three-way-match/${id}/resolve`, resolution);
    return data;
  },
};

const statusColors: Record<string, string> = {
  PENDING: 'bg-blue-100 text-blue-800',
  MATCHED: 'bg-green-100 text-green-800',
  PARTIAL_MATCH: 'bg-yellow-100 text-yellow-800',
  MISMATCH: 'bg-red-100 text-red-800',
  RESOLVED: 'bg-purple-100 text-purple-800',
};

const getMatchIcon = (status: string) => {
  switch (status) {
    case 'MATCHED':
      return <CheckCircle className="h-5 w-5 text-green-600" />;
    case 'PARTIAL':
    case 'PARTIAL_MATCH':
      return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
    case 'MISMATCH':
      return <XCircle className="h-5 w-5 text-red-600" />;
    default:
      return <RefreshCw className="h-5 w-5 text-blue-600" />;
  }
};

export default function ThreeWayMatchPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedMatch, setSelectedMatch] = useState<ThreeWayMatch | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['three-way-match', statusFilter],
    queryFn: () => threeWayMatchApi.list({
      status: statusFilter !== 'all' ? statusFilter : undefined,
    }),
  });

  const { data: stats } = useQuery({
    queryKey: ['three-way-match-stats'],
    queryFn: threeWayMatchApi.getStats,
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => threeWayMatchApi.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['three-way-match'] });
      queryClient.invalidateQueries({ queryKey: ['three-way-match-stats'] });
      toast.success('Match approved successfully');
      setIsDetailOpen(false);
    },
    onError: () => toast.error('Failed to approve match'),
  });

  const handleViewDetail = async (match: ThreeWayMatch) => {
    setSelectedMatch(match);
    setIsDetailOpen(true);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="3-Way Match"
        description="Match Purchase Orders, GRNs, and Vendor Invoices for payment verification"
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Match</CardTitle>
            <RefreshCw className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.total_pending || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Matched</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.matched || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Partial Match</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{stats?.partial || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mismatch</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.mismatch || 0}</div>
          </CardContent>
        </Card>
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-orange-800">Total Variance</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-orange-600">
              {formatCurrency(stats?.total_variance_amount || 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter */}
      <div className="flex gap-4">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="MATCHED">Matched</SelectItem>
            <SelectItem value="PARTIAL_MATCH">Partial Match</SelectItem>
            <SelectItem value="MISMATCH">Mismatch</SelectItem>
            <SelectItem value="RESOLVED">Resolved</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Match List */}
      <Card>
        <CardHeader>
          <CardTitle>Match Queue</CardTitle>
          <CardDescription>PO, GRN, and Invoice matching for payment processing</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : data?.items && data.items.length > 0 ? (
            <div className="space-y-4">
              {data.items.map((match) => (
                <div
                  key={match.id}
                  className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => handleViewDetail(match)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-6">
                      {/* PO */}
                      <div className="flex items-center gap-2">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
                          <FileText className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">Purchase Order</div>
                          <div className="font-mono font-medium">{match.po_number}</div>
                          <div className="text-sm text-muted-foreground">{formatCurrency(match.po_amount)}</div>
                        </div>
                      </div>

                      <ArrowRight className="h-5 w-5 text-muted-foreground" />

                      {/* GRN */}
                      <div className="flex items-center gap-2">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100">
                          <Package className="h-5 w-5 text-purple-600" />
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">Goods Receipt</div>
                          <div className="font-mono font-medium">{match.grn_number}</div>
                          <div className="text-sm text-muted-foreground">{formatCurrency(match.grn_amount)}</div>
                        </div>
                      </div>

                      <ArrowRight className="h-5 w-5 text-muted-foreground" />

                      {/* Invoice */}
                      <div className="flex items-center gap-2">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100">
                          <Truck className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">Vendor Invoice</div>
                          <div className="font-mono font-medium">{match.invoice_number}</div>
                          <div className="text-sm text-muted-foreground">{formatCurrency(match.invoice_amount)}</div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <div className="text-sm text-muted-foreground">{match.vendor_name}</div>
                        <div className="text-xs text-muted-foreground">{match.vendor_code}</div>
                      </div>

                      <div className="text-center">
                        <div className="text-2xl font-bold">{match.match_percent}%</div>
                        <div className="text-xs text-muted-foreground">Match</div>
                      </div>

                      <div className="flex items-center gap-2">
                        {getMatchIcon(match.status)}
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[match.status]}`}>
                          {match.status.replace('_', ' ')}
                        </span>
                      </div>

                      {match.total_variance !== 0 && (
                        <div className="text-right">
                          <div className={`text-sm font-medium ${match.total_variance > 0 ? 'text-red-600' : 'text-green-600'}`}>
                            {match.total_variance > 0 ? '+' : ''}{formatCurrency(match.total_variance)}
                          </div>
                          <div className="text-xs text-muted-foreground">Variance</div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <CheckSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No matches pending</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3">
              3-Way Match Detail
              {selectedMatch && getMatchIcon(selectedMatch.status)}
            </DialogTitle>
            <DialogDescription>
              Compare Purchase Order, Goods Receipt, and Invoice line items
            </DialogDescription>
          </DialogHeader>

          {selectedMatch && (
            <div className="space-y-6">
              {/* Document Summary */}
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Purchase Order
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="font-mono font-medium">{selectedMatch.po_number}</div>
                    <div className="text-sm text-muted-foreground">{formatDate(selectedMatch.po_date)}</div>
                    <div className="text-lg font-bold mt-2">{formatCurrency(selectedMatch.po_amount)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Package className="h-4 w-4" />
                      Goods Receipt
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="font-mono font-medium">{selectedMatch.grn_number}</div>
                    <div className="text-sm text-muted-foreground">{formatDate(selectedMatch.grn_date)}</div>
                    <div className="text-lg font-bold mt-2">{formatCurrency(selectedMatch.grn_amount)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Truck className="h-4 w-4" />
                      Vendor Invoice
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="font-mono font-medium">{selectedMatch.invoice_number}</div>
                    <div className="text-sm text-muted-foreground">{formatDate(selectedMatch.invoice_date)}</div>
                    <div className="text-lg font-bold mt-2">{formatCurrency(selectedMatch.invoice_amount)}</div>
                  </CardContent>
                </Card>
              </div>

              {/* Line Item Comparison */}
              <Tabs defaultValue="items">
                <TabsList>
                  <TabsTrigger value="items">Line Items</TabsTrigger>
                  <TabsTrigger value="variances">Variances Only</TabsTrigger>
                </TabsList>
                <TabsContent value="items" className="mt-4">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Product</TableHead>
                        <TableHead className="text-right">PO Qty</TableHead>
                        <TableHead className="text-right">GRN Qty</TableHead>
                        <TableHead className="text-right">Inv Qty</TableHead>
                        <TableHead className="text-right">PO Rate</TableHead>
                        <TableHead className="text-right">Inv Rate</TableHead>
                        <TableHead className="text-right">Variance</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {selectedMatch.items?.map((item) => (
                        <TableRow key={item.id} className={item.match_status === 'MISMATCH' ? 'bg-red-50' : ''}>
                          <TableCell>
                            <div>
                              <div className="font-medium">{item.product_name}</div>
                              <div className="text-sm text-muted-foreground">{item.sku}</div>
                            </div>
                          </TableCell>
                          <TableCell className="text-right font-mono">{item.po_quantity}</TableCell>
                          <TableCell className="text-right font-mono">
                            <span className={!item.quantity_match ? 'text-red-600 font-bold' : ''}>
                              {item.grn_quantity}
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            <span className={!item.quantity_match ? 'text-red-600 font-bold' : ''}>
                              {item.invoice_quantity}
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-mono">{formatCurrency(item.po_rate)}</TableCell>
                          <TableCell className="text-right font-mono">
                            <span className={!item.rate_match ? 'text-red-600 font-bold' : ''}>
                              {formatCurrency(item.invoice_rate)}
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {item.variance_amount !== 0 && (
                              <span className={item.variance_amount > 0 ? 'text-red-600' : 'text-green-600'}>
                                {item.variance_amount > 0 ? '+' : ''}{formatCurrency(item.variance_amount)}
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            {item.match_status === 'MATCHED' ? (
                              <CheckCircle className="h-5 w-5 text-green-600" />
                            ) : item.match_status === 'PARTIAL' ? (
                              <AlertTriangle className="h-5 w-5 text-yellow-600" />
                            ) : (
                              <XCircle className="h-5 w-5 text-red-600" />
                            )}
                          </TableCell>
                        </TableRow>
                      )) || (
                        <TableRow>
                          <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                            No items to display
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TabsContent>
                <TabsContent value="variances" className="mt-4">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Product</TableHead>
                        <TableHead>Issue</TableHead>
                        <TableHead className="text-right">Expected</TableHead>
                        <TableHead className="text-right">Actual</TableHead>
                        <TableHead className="text-right">Variance</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {selectedMatch.items?.filter(i => i.match_status !== 'MATCHED').map((item) => (
                        <>
                          {!item.quantity_match && (
                            <TableRow key={`${item.id}-qty`}>
                              <TableCell>{item.product_name}</TableCell>
                              <TableCell className="text-yellow-600">Quantity Mismatch</TableCell>
                              <TableCell className="text-right font-mono">{item.po_quantity}</TableCell>
                              <TableCell className="text-right font-mono">{item.invoice_quantity}</TableCell>
                              <TableCell className="text-right font-mono text-red-600">
                                {item.variance_quantity > 0 ? '+' : ''}{item.variance_quantity}
                              </TableCell>
                            </TableRow>
                          )}
                          {!item.rate_match && (
                            <TableRow key={`${item.id}-rate`}>
                              <TableCell>{item.product_name}</TableCell>
                              <TableCell className="text-orange-600">Rate Mismatch</TableCell>
                              <TableCell className="text-right font-mono">{formatCurrency(item.po_rate)}</TableCell>
                              <TableCell className="text-right font-mono">{formatCurrency(item.invoice_rate)}</TableCell>
                              <TableCell className="text-right font-mono text-red-600">
                                {formatCurrency(item.variance_rate)}
                              </TableCell>
                            </TableRow>
                          )}
                        </>
                      )) || (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center py-8 text-green-600">
                            <CheckCircle className="h-8 w-8 mx-auto mb-2" />
                            No variances found
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TabsContent>
              </Tabs>

              {/* Total Variance */}
              {selectedMatch.total_variance !== 0 && (
                <Card className="border-orange-200 bg-orange-50">
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <AlertTriangle className="h-6 w-6 text-orange-600" />
                        <div>
                          <div className="font-medium text-orange-800">Total Variance Detected</div>
                          <div className="text-sm text-orange-600">Review and resolve before approving for payment</div>
                        </div>
                      </div>
                      <div className="text-2xl font-bold text-orange-600">
                        {selectedMatch.total_variance > 0 ? '+' : ''}{formatCurrency(selectedMatch.total_variance)}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDetailOpen(false)}>Close</Button>
            {selectedMatch?.status === 'MISMATCH' && (
              <Button variant="secondary" onClick={() => toast.success('Opening variance resolution workflow')}>
                <AlertTriangle className="mr-2 h-4 w-4" />
                Resolve Variance
              </Button>
            )}
            {(selectedMatch?.status === 'MATCHED' || selectedMatch?.status === 'PARTIAL_MATCH') && (
              <Button onClick={() => selectedMatch && approveMutation.mutate(selectedMatch.id)}>
                <CheckCircle className="mr-2 h-4 w-4" />
                Approve for Payment
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
