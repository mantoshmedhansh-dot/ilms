'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  ShoppingCart,
  Truck,
  Building2,
  FileText,
  Package,
  CreditCard,
  Eye,
  Filter,
  ChevronDown,
  ChevronRight,
  Layers,
  User,
  Calendar,
  Timer,
  Check,
  X,
  History,
  ClipboardList,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { PageHeader, StatusBadge } from '@/components/common';
import { toast } from 'sonner';
import apiClient from '@/lib/api/client';
import { formatDate, formatDateTime, cn } from '@/lib/utils';

// Types
interface ApprovalItem {
  id: string;
  entity_type: 'PURCHASE_ORDER' | 'PURCHASE_REQUISITION' | 'VENDOR' | 'VENDOR_ONBOARDING' | 'TRANSFER' | 'JOURNAL_ENTRY' | 'GRN' | 'INVOICE' | 'EXPENSE' | 'CREDIT_NOTE';
  entity_id: string;
  reference: string;
  title: string;
  description?: string;
  amount: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'ESCALATED';
  level: 'L1' | 'L2' | 'L3' | 'L4' | 'L5';
  current_approver?: string;
  requested_by: string;
  requested_at: string;
  sla_due_at?: string;
  is_sla_breached: boolean;
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
  details?: Record<string, unknown>;
  approver_notes?: string;
  approval_chain?: ApprovalChainItem[];
}

interface ApprovalChainItem {
  level: string;
  approver_name: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'SKIPPED';
  approved_at?: string;
  notes?: string;
}

interface ApprovalStats {
  pending_count: number;
  approved_today: number;
  rejected_today: number;
  sla_breached: number;
  by_type: Record<string, number>;
  by_level: Record<string, number>;
}

// Entity type config
const entityConfig: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  PURCHASE_ORDER: { icon: <ShoppingCart className="h-4 w-4" />, label: 'Purchase Order', color: 'bg-blue-100 text-blue-800' },
  PURCHASE_REQUISITION: { icon: <ClipboardList className="h-4 w-4" />, label: 'Purchase Requisition', color: 'bg-indigo-100 text-indigo-800' },
  VENDOR: { icon: <Building2 className="h-4 w-4" />, label: 'Vendor', color: 'bg-green-100 text-green-800' },
  VENDOR_ONBOARDING: { icon: <Building2 className="h-4 w-4" />, label: 'Vendor', color: 'bg-green-100 text-green-800' },
  TRANSFER: { icon: <Truck className="h-4 w-4" />, label: 'Stock Transfer', color: 'bg-purple-100 text-purple-800' },
  JOURNAL_ENTRY: { icon: <FileText className="h-4 w-4" />, label: 'Journal Entry', color: 'bg-orange-100 text-orange-800' },
  GRN: { icon: <Package className="h-4 w-4" />, label: 'GRN', color: 'bg-cyan-100 text-cyan-800' },
  INVOICE: { icon: <CreditCard className="h-4 w-4" />, label: 'Invoice', color: 'bg-pink-100 text-pink-800' },
  EXPENSE: { icon: <CreditCard className="h-4 w-4" />, label: 'Expense', color: 'bg-amber-100 text-amber-800' },
  CREDIT_NOTE: { icon: <FileText className="h-4 w-4" />, label: 'Credit Note', color: 'bg-rose-100 text-rose-800' },
};

const levelConfig: Record<string, { label: string; color: string; minAmount: number }> = {
  L1: { label: 'Level 1', color: 'bg-green-100 text-green-800', minAmount: 0 },
  L2: { label: 'Level 2', color: 'bg-blue-100 text-blue-800', minAmount: 50000 },
  L3: { label: 'Level 3', color: 'bg-purple-100 text-purple-800', minAmount: 200000 },
  L4: { label: 'Level 4', color: 'bg-orange-100 text-orange-800', minAmount: 500000 },
  L5: { label: 'Level 5', color: 'bg-red-100 text-red-800', minAmount: 1000000 },
};

const priorityConfig: Record<string, { label: string; color: string }> = {
  LOW: { label: 'Low', color: 'bg-gray-100 text-gray-800' },
  NORMAL: { label: 'Normal', color: 'bg-blue-100 text-blue-800' },
  HIGH: { label: 'High', color: 'bg-orange-100 text-orange-800' },
  URGENT: { label: 'Urgent', color: 'bg-red-100 text-red-800 animate-pulse' },
};

// API functions
const approvalsApi = {
  getPending: async (): Promise<{ items: ApprovalItem[] }> => {
    const { data } = await apiClient.get('/approvals/pending');
    return data;
  },
  getStats: async (): Promise<ApprovalStats> => {
    const { data } = await apiClient.get('/approvals/stats');
    return data;
  },
  getMyPending: async (): Promise<{ items: ApprovalItem[] }> => {
    const { data } = await apiClient.get('/approvals/my-pending');
    return data;
  },
  getHistory: async (params?: { limit?: number }): Promise<{ items: ApprovalItem[] }> => {
    const { data } = await apiClient.get('/approvals/history', { params });
    return data;
  },
  getDetails: async (id: string): Promise<ApprovalItem> => {
    const { data } = await apiClient.get(`/approvals/${id}`);
    return data;
  },
  approve: async (id: string, notes?: string) => {
    const { data } = await apiClient.post(`/approvals/${id}/approve`, { notes });
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/approvals/${id}/reject`, { reason });
    return data;
  },
  bulkApprove: async (ids: string[], notes?: string) => {
    const { data } = await apiClient.post('/approvals/bulk-approve', { ids, notes });
    return data;
  },
  bulkReject: async (ids: string[], reason: string) => {
    const { data } = await apiClient.post('/approvals/bulk-reject', { ids, reason });
    return data;
  },
  escalate: async (id: string, notes: string) => {
    const { data } = await apiClient.post(`/approvals/${id}/escalate`, { notes });
    return data;
  },
};

export default function ApprovalsPage() {
  const queryClient = useQueryClient();
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [filterType, setFilterType] = useState<string>('all');
  const [filterLevel, setFilterLevel] = useState<string>('all');
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [showSlaOnly, setShowSlaOnly] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // Dialogs
  const [detailsDialog, setDetailsDialog] = useState(false);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalItem | null>(null);
  const [rejectDialog, setRejectDialog] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [approveNotes, setApproveNotes] = useState('');
  const [bulkAction, setBulkAction] = useState<'approve' | 'reject' | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null); // Track which item is being processed

  // Queries
  const { data: pendingData, isLoading: pendingLoading } = useQuery({
    queryKey: ['pending-approvals'],
    queryFn: approvalsApi.getPending,
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['approval-stats'],
    queryFn: approvalsApi.getStats,
  });

  const { data: historyData } = useQuery({
    queryKey: ['approval-history'],
    queryFn: () => approvalsApi.getHistory({ limit: 20 }),
  });

  // Mutations
  const approveMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      approvalsApi.approve(id, notes),
    onMutate: ({ id }) => {
      setProcessingId(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] });
      queryClient.invalidateQueries({ queryKey: ['approval-stats'] });
      queryClient.invalidateQueries({ queryKey: ['approval-history'] });
      toast.success('Approved successfully');
      setDetailsDialog(false);
      setProcessingId(null);
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      const message = error.response?.data?.detail || error.message || 'Failed to approve';
      toast.error(message);
      setProcessingId(null);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      approvalsApi.reject(id, reason),
    onMutate: ({ id }) => {
      setProcessingId(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] });
      queryClient.invalidateQueries({ queryKey: ['approval-stats'] });
      queryClient.invalidateQueries({ queryKey: ['approval-history'] });
      toast.success('Rejected successfully');
      setRejectDialog(false);
      setRejectReason('');
      setProcessingId(null);
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      const message = error.response?.data?.detail || error.message || 'Failed to reject';
      toast.error(message);
      setProcessingId(null);
    },
  });

  const bulkApproveMutation = useMutation({
    mutationFn: ({ ids, notes }: { ids: string[]; notes?: string }) =>
      approvalsApi.bulkApprove(ids, notes),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] });
      queryClient.invalidateQueries({ queryKey: ['approval-stats'] });
      toast.success(`${variables.ids.length} items approved`);
      setSelectedItems(new Set());
      setBulkAction(null);
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      const message = error.response?.data?.detail || error.message || 'Failed to approve items';
      toast.error(message);
    },
  });

  const bulkRejectMutation = useMutation({
    mutationFn: ({ ids, reason }: { ids: string[]; reason: string }) =>
      approvalsApi.bulkReject(ids, reason),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] });
      queryClient.invalidateQueries({ queryKey: ['approval-stats'] });
      toast.success(`${variables.ids.length} items rejected`);
      setSelectedItems(new Set());
      setBulkAction(null);
      setRejectReason('');
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      const message = error.response?.data?.detail || error.message || 'Failed to reject items';
      toast.error(message);
    },
  });

  // Filter items
  const filteredItems = useMemo(() => {
    let items = pendingData?.items ?? [];
    if (filterType !== 'all') {
      items = items.filter((item) => item.entity_type === filterType);
    }
    if (filterLevel !== 'all') {
      items = items.filter((item) => item.level === filterLevel);
    }
    if (filterPriority !== 'all') {
      items = items.filter((item) => item.priority === filterPriority);
    }
    if (showSlaOnly) {
      items = items.filter((item) => item.is_sla_breached);
    }
    return items;
  }, [pendingData?.items, filterType, filterLevel, filterPriority, showSlaOnly]);

  // Group by type
  const groupedItems = useMemo(() => {
    const groups: Record<string, ApprovalItem[]> = {};
    filteredItems.forEach((item) => {
      if (!groups[item.entity_type]) {
        groups[item.entity_type] = [];
      }
      groups[item.entity_type].push(item);
    });
    return groups;
  }, [filteredItems]);

  // Selection handlers
  const toggleSelectAll = () => {
    if (selectedItems.size === filteredItems.length) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(filteredItems.map((item) => item.id)));
    }
  };

  const toggleSelectItem = (id: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedItems(newSelected);
  };

  const toggleExpand = (type: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(type)) {
      newExpanded.delete(type);
    } else {
      newExpanded.add(type);
    }
    setExpandedItems(newExpanded);
  };

  // Format SLA time remaining
  const getSlaStatus = (item: ApprovalItem) => {
    if (item.is_sla_breached) {
      return { label: 'SLA Breached', color: 'text-red-600', icon: <AlertTriangle className="h-4 w-4" /> };
    }
    if (!item.sla_due_at) return null;

    const now = new Date();
    const due = new Date(item.sla_due_at);
    const hoursRemaining = Math.round((due.getTime() - now.getTime()) / (1000 * 60 * 60));

    if (hoursRemaining < 0) {
      return { label: 'Overdue', color: 'text-red-600', icon: <AlertTriangle className="h-4 w-4" /> };
    } else if (hoursRemaining < 4) {
      return { label: `${hoursRemaining}h left`, color: 'text-orange-600', icon: <Timer className="h-4 w-4" /> };
    } else if (hoursRemaining < 24) {
      return { label: `${hoursRemaining}h left`, color: 'text-yellow-600', icon: <Clock className="h-4 w-4" /> };
    }
    return { label: `${Math.floor(hoursRemaining / 24)}d left`, color: 'text-green-600', icon: <Clock className="h-4 w-4" /> };
  };

  const handleApprove = (item: ApprovalItem) => {
    setSelectedApproval(item);
    setDetailsDialog(true);
  };

  const handleReject = (item: ApprovalItem) => {
    setSelectedApproval(item);
    setRejectDialog(true);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Approvals"
        description="Review and approve pending requests"
        actions={
          selectedItems.size > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                {selectedItems.size} selected
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setBulkAction('reject')}
              >
                <X className="mr-1 h-4 w-4" />
                Reject All
              </Button>
              <Button size="sm" onClick={() => setBulkAction('approve')}>
                <Check className="mr-1 h-4 w-4" />
                Approve All
              </Button>
            </div>
          )
        }
      />

      {/* Stats Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading || pendingLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{pendingData?.items?.length ?? stats?.pending_count ?? 0}</div>
            )}
            <p className="text-xs text-muted-foreground">awaiting your action</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Approved Today</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold text-green-600">{stats?.approved_today ?? 0}</div>
            )}
            <p className="text-xs text-muted-foreground">processed</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Rejected Today</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold text-red-600">{stats?.rejected_today ?? 0}</div>
            )}
            <p className="text-xs text-muted-foreground">sent back</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">SLA Breached</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold text-orange-600">{stats?.sla_breached ?? 0}</div>
            )}
            <p className="text-xs text-muted-foreground">need attention</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="pending" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pending" className="gap-2">
            <Clock className="h-4 w-4" />
            Pending ({filteredItems.length})
          </TabsTrigger>
          <TabsTrigger value="history" className="gap-2">
            <History className="h-4 w-4" />
            History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pending" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Filters:</span>
                </div>
                <Select value={filterType} onValueChange={setFilterType}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="All Types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    {Object.entries(entityConfig).map(([key, config]) => (
                      <SelectItem key={key} value={key}>
                        <div className="flex items-center gap-2">
                          {config.icon}
                          {config.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={filterLevel} onValueChange={setFilterLevel}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="All Levels" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Levels</SelectItem>
                    {Object.entries(levelConfig).map(([key, config]) => (
                      <SelectItem key={key} value={key}>
                        {config.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={filterPriority} onValueChange={setFilterPriority}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="All Priorities" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Priorities</SelectItem>
                    {Object.entries(priorityConfig).map(([key, config]) => (
                      <SelectItem key={key} value={key}>
                        {config.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="sla-only"
                    checked={showSlaOnly}
                    onCheckedChange={(checked) => setShowSlaOnly(checked as boolean)}
                  />
                  <label htmlFor="sla-only" className="text-sm">
                    SLA Breached Only
                  </label>
                </div>
                {filteredItems.length > 0 && (
                  <div className="ml-auto flex items-center gap-2">
                    <Checkbox
                      id="select-all"
                      checked={selectedItems.size === filteredItems.length}
                      onCheckedChange={toggleSelectAll}
                    />
                    <label htmlFor="select-all" className="text-sm">
                      Select All
                    </label>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Grouped Items */}
          {pendingLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-32" />
              ))}
            </div>
          ) : filteredItems.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <CheckCircle className="h-12 w-12 text-green-600 mb-4" />
                <h3 className="text-lg font-semibold">All Caught Up!</h3>
                <p className="text-muted-foreground">No pending approvals matching your filters</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {Object.entries(groupedItems).map(([type, items]) => {
                const config = entityConfig[type] || { icon: <FileText className="h-4 w-4" />, label: type, color: 'bg-gray-100 text-gray-800' };
                const isExpanded = expandedItems.has(type) || expandedItems.size === 0;

                return (
                  <Card key={type}>
                    <Collapsible open={isExpanded} onOpenChange={() => toggleExpand(type)}>
                      <CollapsibleTrigger asChild>
                        <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              {isExpanded ? (
                                <ChevronDown className="h-5 w-5" />
                              ) : (
                                <ChevronRight className="h-5 w-5" />
                              )}
                              <Badge className={config.color}>
                                {config.icon}
                                <span className="ml-1">{config.label}</span>
                              </Badge>
                              <span className="text-muted-foreground">
                                {items.length} pending
                              </span>
                            </div>
                            <div className="text-sm text-muted-foreground">
                              Total: ₹{items.reduce((sum, item) => sum + (item.amount || 0), 0).toLocaleString()}
                            </div>
                          </div>
                        </CardHeader>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <CardContent className="pt-0">
                          <div className="space-y-3">
                            {items.map((item) => {
                              const slaStatus = getSlaStatus(item);
                              return (
                                <div
                                  key={item.id}
                                  className={cn(
                                    'flex items-center justify-between rounded-lg border p-4 transition-colors',
                                    item.is_sla_breached && 'border-red-200 bg-red-50',
                                    selectedItems.has(item.id) && 'bg-primary/5 border-primary'
                                  )}
                                >
                                  <div className="flex items-center gap-4">
                                    <Checkbox
                                      checked={selectedItems.has(item.id)}
                                      onCheckedChange={() => toggleSelectItem(item.id)}
                                    />
                                    <div className="space-y-1">
                                      <div className="flex items-center gap-2">
                                        <span className="font-medium">{item.reference}</span>
                                        <Badge className={levelConfig[item.level]?.color || 'bg-gray-100'}>
                                          {item.level}
                                        </Badge>
                                        <Badge className={priorityConfig[item.priority]?.color || 'bg-gray-100'}>
                                          {item.priority}
                                        </Badge>
                                      </div>
                                      <p className="text-sm text-muted-foreground">
                                        {item.title || item.description}
                                      </p>
                                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                        <span className="flex items-center gap-1">
                                          <User className="h-3 w-3" />
                                          {item.requested_by}
                                        </span>
                                        <span className="flex items-center gap-1">
                                          <Calendar className="h-3 w-3" />
                                          {formatDate(item.requested_at)}
                                        </span>
                                        {slaStatus && (
                                          <span className={cn('flex items-center gap-1', slaStatus.color)}>
                                            {slaStatus.icon}
                                            {slaStatus.label}
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-4">
                                    <div className="text-right">
                                      <p className="font-semibold">₹{item.amount.toLocaleString()}</p>
                                      {item.current_approver && (
                                        <p className="text-xs text-muted-foreground">
                                          Approver: {item.current_approver}
                                        </p>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => handleApprove(item)}
                                        title="View Details"
                                      >
                                        <Eye className="h-4 w-4" />
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="destructive"
                                        onClick={() => handleReject(item)}
                                        disabled={processingId === item.id}
                                      >
                                        <XCircle className="h-4 w-4 mr-1" />
                                        Reject
                                      </Button>
                                      <Button
                                        size="sm"
                                        className="bg-green-600 hover:bg-green-700"
                                        onClick={() => approveMutation.mutate({ id: item.id })}
                                        disabled={processingId === item.id}
                                      >
                                        <CheckCircle className="h-4 w-4 mr-1" />
                                        {processingId === item.id && approveMutation.isPending ? 'Approving...' : 'Approve'}
                                      </Button>
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </CardContent>
                      </CollapsibleContent>
                    </Collapsible>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Approval History</CardTitle>
              <CardDescription>Your recent approval decisions</CardDescription>
            </CardHeader>
            <CardContent>
              {historyData?.items && historyData.items.length > 0 ? (
                <div className="space-y-4">
                  {historyData.items.map((item) => {
                    const config = entityConfig[item.entity_type] || { icon: <FileText className="h-4 w-4" />, label: item.entity_type, color: 'bg-gray-100' };
                    return (
                      <div
                        key={item.id}
                        className="flex items-center justify-between rounded-lg border p-4"
                      >
                        <div className="flex items-center gap-4">
                          <div className={cn(
                            'w-10 h-10 rounded-full flex items-center justify-center',
                            item.status === 'APPROVED' ? 'bg-green-100' : 'bg-red-100'
                          )}>
                            {item.status === 'APPROVED' ? (
                              <CheckCircle className="h-5 w-5 text-green-600" />
                            ) : (
                              <XCircle className="h-5 w-5 text-red-600" />
                            )}
                          </div>
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{item.reference}</span>
                              <Badge className={config.color}>
                                {config.icon}
                                <span className="ml-1">{config.label}</span>
                              </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {item.title} • ₹{item.amount.toLocaleString()}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <StatusBadge status={item.status} />
                          <p className="text-xs text-muted-foreground mt-1">
                            {formatDateTime(item.requested_at)}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="flex items-center justify-center h-32 text-muted-foreground">
                  No approval history
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Details Dialog */}
      <Dialog open={detailsDialog} onOpenChange={setDetailsDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Approval Details</DialogTitle>
            <DialogDescription>
              Review the details before approving
            </DialogDescription>
          </DialogHeader>
          {selectedApproval && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-muted-foreground">Reference</Label>
                  <p className="font-medium">{selectedApproval.reference}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Amount</Label>
                  <p className="font-medium">₹{selectedApproval.amount.toLocaleString()}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Type</Label>
                  <Badge className={entityConfig[selectedApproval.entity_type]?.color}>
                    {entityConfig[selectedApproval.entity_type]?.label}
                  </Badge>
                </div>
                <div>
                  <Label className="text-muted-foreground">Level</Label>
                  <Badge className={levelConfig[selectedApproval.level]?.color}>
                    {selectedApproval.level}
                  </Badge>
                </div>
                <div>
                  <Label className="text-muted-foreground">Requested By</Label>
                  <p>{selectedApproval.requested_by}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Requested At</Label>
                  <p>{formatDateTime(selectedApproval.requested_at)}</p>
                </div>
              </div>
              {selectedApproval.description && (
                <div>
                  <Label className="text-muted-foreground">Description</Label>
                  <p className="mt-1">{selectedApproval.description}</p>
                </div>
              )}

              {/* Approval Chain */}
              {selectedApproval.approval_chain && selectedApproval.approval_chain.length > 0 && (
                <div>
                  <Label className="text-muted-foreground">Approval Chain</Label>
                  <div className="mt-2 space-y-2">
                    {selectedApproval.approval_chain.map((chain, index) => (
                      <div key={index} className="flex items-center gap-3 p-2 border rounded">
                        <div className={cn(
                          'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium',
                          chain.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
                          chain.status === 'REJECTED' ? 'bg-red-100 text-red-800' :
                          chain.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        )}>
                          {chain.level}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium">{chain.approver_name}</p>
                          {chain.approved_at && (
                            <p className="text-xs text-muted-foreground">
                              {formatDateTime(chain.approved_at)}
                            </p>
                          )}
                        </div>
                        <StatusBadge status={chain.status} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <Separator />

              <div className="space-y-2">
                <Label>Notes (Optional)</Label>
                <Textarea
                  value={approveNotes}
                  onChange={(e) => setApproveNotes(e.target.value)}
                  placeholder="Add any notes for this approval..."
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailsDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => selectedApproval && approveMutation.mutate({ id: selectedApproval.id, notes: approveNotes })}
              disabled={approveMutation.isPending}
            >
              {approveMutation.isPending ? 'Approving...' : 'Approve'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialog} onOpenChange={setRejectDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Reject Request</DialogTitle>
            <DialogDescription>
              Please provide a reason for rejection
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Rejection Reason *</Label>
              <Textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Enter the reason for rejection..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => selectedApproval && rejectMutation.mutate({ id: selectedApproval.id, reason: rejectReason })}
              disabled={!rejectReason.trim() || rejectMutation.isPending}
            >
              {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Action Dialog */}
      <Dialog open={bulkAction !== null} onOpenChange={() => setBulkAction(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {bulkAction === 'approve' ? 'Bulk Approve' : 'Bulk Reject'}
            </DialogTitle>
            <DialogDescription>
              {bulkAction === 'approve'
                ? `Approve ${selectedItems.size} selected items`
                : `Reject ${selectedItems.size} selected items`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {bulkAction === 'reject' ? (
              <div className="space-y-2">
                <Label>Rejection Reason *</Label>
                <Textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Enter the reason for rejection..."
                  rows={4}
                />
              </div>
            ) : (
              <div className="space-y-2">
                <Label>Notes (Optional)</Label>
                <Textarea
                  value={approveNotes}
                  onChange={(e) => setApproveNotes(e.target.value)}
                  placeholder="Add any notes for this bulk approval..."
                  rows={4}
                />
              </div>
            )}
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm font-medium mb-2">Selected Items:</p>
              <div className="text-sm text-muted-foreground">
                {Array.from(selectedItems).slice(0, 5).map((id) => {
                  const item = filteredItems.find((i) => i.id === id);
                  return item ? (
                    <div key={id}>{item.reference} - ₹{item.amount.toLocaleString()}</div>
                  ) : null;
                })}
                {selectedItems.size > 5 && (
                  <div className="text-muted-foreground">
                    ...and {selectedItems.size - 5} more
                  </div>
                )}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkAction(null)}>
              Cancel
            </Button>
            {bulkAction === 'approve' ? (
              <Button
                onClick={() => bulkApproveMutation.mutate({ ids: Array.from(selectedItems), notes: approveNotes })}
                disabled={bulkApproveMutation.isPending}
              >
                {bulkApproveMutation.isPending ? 'Approving...' : `Approve ${selectedItems.size} Items`}
              </Button>
            ) : (
              <Button
                variant="destructive"
                onClick={() => bulkRejectMutation.mutate({ ids: Array.from(selectedItems), reason: rejectReason })}
                disabled={!rejectReason.trim() || bulkRejectMutation.isPending}
              >
                {bulkRejectMutation.isPending ? 'Rejecting...' : `Reject ${selectedItems.size} Items`}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
