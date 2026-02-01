'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  CheckCircle, XCircle, Clock, Warehouse, Truck, Package,
  MapPin, Info, ChevronDown, ChevronRight, FileText
} from 'lucide-react';
import { format } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { serviceabilityApi } from '@/lib/api';
import { cn, formatDate } from '@/lib/utils';

interface AllocationLog {
  id: string;
  order_id: string;
  rule_id?: string;
  warehouse_id?: string;
  customer_pincode: string;
  is_successful: boolean;
  failure_reason?: string;
  decision_factors?: string;
  candidates_considered?: string;
  created_at: string;
}

interface WarehouseCandidate {
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  city: string;
  estimated_days: number;
  shipping_cost: number;
  priority: number;
  cod_available: boolean;
  prepaid_available: boolean;
}

function AllocationLogActionsCell({
  log,
  onViewDetails,
}: {
  log: AllocationLog;
  onViewDetails: (log: AllocationLog) => void;
}) {
  return (
    <Button variant="ghost" size="sm" onClick={() => onViewDetails(log)}>
      <Info className="h-4 w-4 mr-1" />
      Details
    </Button>
  );
}

export default function AllocationLogsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchOrderId, setSearchOrderId] = useState('');
  const [selectedLog, setSelectedLog] = useState<AllocationLog | null>(null);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);

  // Query
  const { data, isLoading } = useQuery({
    queryKey: ['allocation-logs', page, pageSize, statusFilter, searchOrderId],
    queryFn: async () => {
      const params: { is_successful?: boolean; order_id?: string; limit?: number } = {
        limit: 100,
      };
      if (statusFilter === 'success') params.is_successful = true;
      if (statusFilter === 'failed') params.is_successful = false;

      const logs = await serviceabilityApi.getAllocationLogs(params);
      return logs;
    },
  });

  const allLogs = data ?? [];

  // Filter by order ID if searching
  const filteredLogs = searchOrderId
    ? allLogs.filter((log: AllocationLog) =>
        log.order_id.toLowerCase().includes(searchOrderId.toLowerCase())
      )
    : allLogs;

  // Paginate
  const paginatedLogs = filteredLogs.slice(page * pageSize, (page + 1) * pageSize);
  const totalPages = Math.ceil(filteredLogs.length / pageSize);

  // Stats
  const stats = {
    total: allLogs.length,
    successful: allLogs.filter((l: AllocationLog) => l.is_successful).length,
    failed: allLogs.filter((l: AllocationLog) => !l.is_successful).length,
    successRate: allLogs.length > 0
      ? (allLogs.filter((l: AllocationLog) => l.is_successful).length / allLogs.length) * 100
      : 0,
  };

  const handleViewDetails = (log: AllocationLog) => {
    setSelectedLog(log);
    setIsDetailsOpen(true);
  };

  const parseJSON = (str?: string) => {
    if (!str) return null;
    try {
      return JSON.parse(str);
    } catch {
      return null;
    }
  };

  const columns: ColumnDef<AllocationLog>[] = [
    {
      accessorKey: 'created_at',
      header: 'Time',
      cell: ({ row }) => (
        <div className="text-sm">
          <div className="font-medium">{format(new Date(row.original.created_at), 'MMM d, yyyy')}</div>
          <div className="text-muted-foreground">{format(new Date(row.original.created_at), 'HH:mm:ss')}</div>
        </div>
      ),
    },
    {
      accessorKey: 'order_id',
      header: 'Order ID',
      cell: ({ row }) => (
        <code className="text-xs font-mono bg-muted px-2 py-1 rounded">
          {row.original.order_id?.slice(0, 8) ?? '-'}...
        </code>
      ),
    },
    {
      accessorKey: 'customer_pincode',
      header: 'Destination',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.original.customer_pincode}</span>
        </div>
      ),
    },
    {
      accessorKey: 'is_successful',
      header: 'Status',
      cell: ({ row }) => (
        row.original.is_successful ? (
          <Badge className="bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200">
            <CheckCircle className="h-3 w-3 mr-1" />
            Allocated
          </Badge>
        ) : (
          <Badge className="bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200">
            <XCircle className="h-3 w-3 mr-1" />
            Failed
          </Badge>
        )
      ),
    },
    {
      accessorKey: 'warehouse_id',
      header: 'Warehouse',
      cell: ({ row }) => (
        row.original.warehouse_id ? (
          <div className="flex items-center gap-2">
            <Warehouse className="h-4 w-4 text-blue-500" />
            <code className="text-xs font-mono">{row.original.warehouse_id.slice(0, 8)}...</code>
          </div>
        ) : (
          <span className="text-muted-foreground">-</span>
        )
      ),
    },
    {
      accessorKey: 'failure_reason',
      header: 'Reason',
      cell: ({ row }) => {
        const factors = parseJSON(row.original.decision_factors);
        if (row.original.failure_reason) {
          return (
            <span className="text-sm text-red-600 dark:text-red-400 max-w-[200px] truncate block">
              {row.original.failure_reason}
            </span>
          );
        }
        if (factors?.rule_name) {
          return (
            <span className="text-sm text-muted-foreground">
              Rule: {factors.rule_name}
            </span>
          );
        }
        return <span className="text-muted-foreground">-</span>;
      },
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <AllocationLogActionsCell
          log={row.original}
          onViewDetails={handleViewDetails}
        />
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Allocation Logs"
        description="View order allocation decisions and troubleshoot failed allocations"
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Allocations</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">Allocation attempts logged</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Successful</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.successful}</div>
            <p className="text-xs text-muted-foreground">Orders allocated</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
            <p className="text-xs text-muted-foreground">Allocation failures</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <Package className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              stats.successRate >= 90 ? 'text-green-600' :
              stats.successRate >= 70 ? 'text-yellow-600' : 'text-red-600'
            )}>
              {stats.successRate.toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">Allocation success</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Input
          placeholder="Search by Order ID..."
          className="max-w-xs"
          value={searchOrderId}
          onChange={(e) => setSearchOrderId(e.target.value)}
        />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="success">Successful Only</SelectItem>
            <SelectItem value="failed">Failed Only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={paginatedLogs}
        searchKey="order_id"
        searchPlaceholder="Search logs..."
        isLoading={isLoading}
        manualPagination
        pageCount={totalPages}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Details Dialog */}
      <Dialog open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Allocation Details</DialogTitle>
            <DialogDescription>
              Order ID: {selectedLog?.order_id}
            </DialogDescription>
          </DialogHeader>

          {selectedLog && (
            <div className="space-y-6">
              {/* Status */}
              <div className="flex items-center gap-4">
                {selectedLog.is_successful ? (
                  <Badge className="bg-green-100 text-green-800 text-lg px-4 py-2">
                    <CheckCircle className="h-5 w-5 mr-2" />
                    Allocation Successful
                  </Badge>
                ) : (
                  <Badge className="bg-red-100 text-red-800 text-lg px-4 py-2">
                    <XCircle className="h-5 w-5 mr-2" />
                    Allocation Failed
                  </Badge>
                )}
              </div>

              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Customer Pincode</p>
                  <p className="font-medium flex items-center gap-2">
                    <MapPin className="h-4 w-4" />
                    {selectedLog.customer_pincode}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Time</p>
                  <p className="font-medium flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    {format(new Date(selectedLog.created_at), 'PPpp')}
                  </p>
                </div>
                {selectedLog.warehouse_id && (
                  <div>
                    <p className="text-sm text-muted-foreground">Allocated Warehouse</p>
                    <p className="font-medium flex items-center gap-2">
                      <Warehouse className="h-4 w-4" />
                      {selectedLog.warehouse_id}
                    </p>
                  </div>
                )}
                {selectedLog.rule_id && (
                  <div>
                    <p className="text-sm text-muted-foreground">Rule Applied</p>
                    <p className="font-medium">{selectedLog.rule_id}</p>
                  </div>
                )}
              </div>

              {/* Failure Reason */}
              {selectedLog.failure_reason && (
                <div className="p-4 bg-red-50 dark:bg-red-950/20 rounded-lg border border-red-200 dark:border-red-900">
                  <h4 className="font-medium text-red-800 dark:text-red-200 mb-2">Failure Reason</h4>
                  <p className="text-red-700 dark:text-red-300">{selectedLog.failure_reason}</p>
                </div>
              )}

              {/* Decision Factors */}
              {selectedLog.decision_factors && (
                <Collapsible>
                  <CollapsibleTrigger asChild>
                    <Button variant="outline" className="w-full justify-between">
                      <span>Decision Factors</span>
                      <ChevronDown className="h-4 w-4" />
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-2">
                    <pre className="bg-muted p-4 rounded-lg text-sm overflow-x-auto">
                      {JSON.stringify(parseJSON(selectedLog.decision_factors), null, 2)}
                    </pre>
                  </CollapsibleContent>
                </Collapsible>
              )}

              {/* Candidates Considered */}
              {selectedLog.candidates_considered && (
                <Collapsible>
                  <CollapsibleTrigger asChild>
                    <Button variant="outline" className="w-full justify-between">
                      <span>Candidates Considered</span>
                      <ChevronDown className="h-4 w-4" />
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-2">
                    {(() => {
                      const candidates = parseJSON(selectedLog.candidates_considered) as WarehouseCandidate[] | null;
                      if (!candidates || candidates.length === 0) {
                        return <p className="text-muted-foreground">No candidates data available</p>;
                      }
                      return (
                        <div className="space-y-2">
                          {candidates.map((candidate, index) => (
                            <div key={index} className="p-3 bg-muted rounded-lg">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <Warehouse className="h-4 w-4" />
                                  <span className="font-medium">{candidate.warehouse_name}</span>
                                  <Badge variant="outline" className="text-xs">{candidate.warehouse_code}</Badge>
                                </div>
                                <Badge>Priority: {candidate.priority}</Badge>
                              </div>
                              <div className="mt-2 flex gap-4 text-sm text-muted-foreground">
                                <span>City: {candidate.city}</span>
                                <span>Delivery: {candidate.estimated_days} days</span>
                                <span>Cost: ₹{candidate.shipping_cost}</span>
                                {candidate.cod_available && <Badge variant="secondary" className="text-xs">COD</Badge>}
                              </div>
                            </div>
                          ))}
                        </div>
                      );
                    })()}
                  </CollapsibleContent>
                </Collapsible>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
