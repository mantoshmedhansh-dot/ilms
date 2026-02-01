'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  MoreHorizontal,
  Plus,
  Eye,
  RefreshCw,
  Shield,
  AlertTriangle,
  Calendar,
  Clock,
  CheckCircle,
  XCircle,
  Download,
  Phone,
  Mail,
  MapPin,
  Wrench,
  IndianRupee,
  TrendingUp,
  Users,
  FileText,
  Bell,
  Settings,
  Filter,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import apiClient from '@/lib/api/client';
import { formatDate, formatCurrency } from '@/lib/utils';

interface AMCPlan {
  id: string;
  name: string;
  code: string;
  duration_months: number;
  visits_included: number;
  price: number;
  discount_percentage: number;
  parts_covered: boolean;
  labor_covered: boolean;
  priority_support: boolean;
  is_active: boolean;
  description: string;
  applicable_products: string[];
  contracts_count: number;
}

interface AMCContract {
  id: string;
  contract_number: string;
  customer_id: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  product_id: string;
  product_name: string;
  serial_number: string;
  plan_id: string;
  plan_name: string;
  start_date: string;
  end_date: string;
  amount: number;
  visits_included: number;
  visits_used: number;
  status: 'PENDING_ACTIVATION' | 'ACTIVE' | 'EXPIRED' | 'CANCELLED' | 'PENDING_RENEWAL' | 'SUSPENDED';
  auto_renew: boolean;
  payment_status: 'PENDING' | 'PAID' | 'PARTIAL';
  days_remaining: number;
  next_service_date?: string;
  created_at: string;
}

interface AMCStats {
  total_contracts: number;
  active_contracts: number;
  expiring_soon: number;
  pending_renewal: number;
  total_revenue: number;
  this_month_revenue: number;
  renewal_rate: number;
  avg_contract_value: number;
}

const amcApi = {
  getStats: async (): Promise<AMCStats> => {
    try {
      const { data } = await apiClient.get('/api/v1/amc/contracts/stats');
      return {
        total_contracts: data.total || 0,
        active_contracts: data.active_contracts || 0,
        expiring_soon: data.expiring_in_30_days || 0,
        pending_renewal: data.by_status?.PENDING_RENEWAL || 0,
        total_revenue: data.active_value || 0,
        this_month_revenue: 0, // Not provided by API
        renewal_rate: 0, // Calculate if needed
        avg_contract_value: data.active_contracts > 0 ? data.active_value / data.active_contracts : 0,
      };
    } catch {
      // Return defaults on error
      return {
        total_contracts: 0,
        active_contracts: 0,
        expiring_soon: 0,
        pending_renewal: 0,
        total_revenue: 0,
        this_month_revenue: 0,
        renewal_rate: 0,
        avg_contract_value: 0,
      };
    }
  },
  listPlans: async (): Promise<{ items: AMCPlan[]; total: number; pages: number }> => {
    try {
      const { data } = await apiClient.get('/api/v1/amc/plans');
      return {
        items: (data.items || []).map((p: Record<string, unknown>) => ({
          id: p.id,
          name: p.name,
          code: p.code,
          duration_months: p.duration_months,
          visits_included: p.services_included,
          price: p.base_price,
          discount_percentage: p.discount_on_parts || 0,
          parts_covered: p.parts_covered,
          labor_covered: p.labor_covered,
          priority_support: p.priority_service,
          is_active: p.is_active,
          description: p.description,
          applicable_products: [],
          contracts_count: 0,
        })),
        total: data.total || 0,
        pages: Math.ceil((data.total || 0) / 20),
      };
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  listContracts: async (params?: { page?: number; size?: number; status?: string }): Promise<{ items: AMCContract[]; total: number; pages: number }> => {
    try {
      const { data } = await apiClient.get('/api/v1/amc/contracts', { params });
      return {
        items: (data.items || []).map((c: Record<string, unknown>) => ({
          id: c.id,
          contract_number: c.contract_number,
          customer_id: c.customer_id,
          customer_name: c.customer_name,
          customer_phone: '',
          customer_email: '',
          product_id: '',
          product_name: c.product_name,
          serial_number: c.serial_number,
          plan_id: '',
          plan_name: c.amc_type,
          start_date: c.start_date,
          end_date: c.end_date,
          amount: c.total_amount,
          visits_included: c.total_services,
          visits_used: c.services_used,
          status: c.status as AMCContract['status'],
          auto_renew: false,
          payment_status: c.payment_status as AMCContract['payment_status'],
          days_remaining: c.days_remaining,
          next_service_date: c.next_service_due,
          created_at: '',
        })),
        total: data.total || 0,
        pages: Math.ceil((data.total || 0) / (params?.size || 20)),
      };
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  createContract: async (data: Record<string, unknown>) => {
    const { data: result } = await apiClient.post('/api/v1/amc/contracts', data);
    return result;
  },
  createPlan: async (data: Record<string, unknown>) => {
    const { data: result } = await apiClient.post('/api/v1/amc/plans', data);
    return result;
  },
  activateContract: async (contractId: string, paymentMode: string = 'ONLINE', paymentReference?: string) => {
    const { data: result } = await apiClient.post(`/api/v1/amc/contracts/${contractId}/activate`, null, {
      params: { payment_mode: paymentMode, payment_reference: paymentReference }
    });
    return result;
  },
  renewContract: async (contractId: string, newPlanId?: string, durationMonths: number = 12) => {
    const { data: result } = await apiClient.post(`/api/v1/amc/contracts/${contractId}/renew`, null, {
      params: { new_plan_id: newPlanId, duration_months: durationMonths }
    });
    return result;
  },
};

const statusColors: Record<string, string> = {
  PENDING_ACTIVATION: 'bg-yellow-100 text-yellow-800',
  ACTIVE: 'bg-green-100 text-green-800',
  EXPIRED: 'bg-gray-100 text-gray-800',
  CANCELLED: 'bg-red-100 text-red-800',
  PENDING_RENEWAL: 'bg-orange-100 text-orange-800',
  SUSPENDED: 'bg-red-100 text-red-800',
};

const paymentStatusColors: Record<string, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  PAID: 'bg-green-100 text-green-800',
  PARTIAL: 'bg-orange-100 text-orange-800',
};

export default function AMCPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [plansPage, setPlansPage] = useState(0);
  const [pageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Dialogs
  const [isCreateContractOpen, setIsCreateContractOpen] = useState(false);
  const [isCreatePlanOpen, setIsCreatePlanOpen] = useState(false);
  const [isRenewOpen, setIsRenewOpen] = useState(false);
  const [selectedContract, setSelectedContract] = useState<AMCContract | null>(null);

  // Form states
  const [contractForm, setContractForm] = useState({
    customer_phone: '',
    serial_number: '',
    plan_id: '',
    auto_renew: true,
  });

  const [planForm, setPlanForm] = useState({
    name: '',
    code: '',
    duration_months: '12',
    visits_included: '2',
    price: '',
    parts_covered: false,
    labor_covered: true,
    priority_support: false,
    description: '',
  });

  // Queries
  const { data: stats } = useQuery({
    queryKey: ['amc-stats'],
    queryFn: amcApi.getStats,
  });

  const { data: plansData, isLoading: plansLoading } = useQuery({
    queryKey: ['amc-plans'],
    queryFn: amcApi.listPlans,
  });

  const { data: contractsData, isLoading: contractsLoading } = useQuery({
    queryKey: ['amc-contracts', page, statusFilter],
    queryFn: () => amcApi.listContracts({ page: page + 1, size: pageSize, status: statusFilter !== 'all' ? statusFilter : undefined }),
  });

  // Mutations
  const createContractMutation = useMutation({
    mutationFn: async (data: typeof contractForm) => {
      return amcApi.createContract({
        customer_id: data.customer_phone, // Need to lookup customer by phone
        serial_number: data.serial_number,
        plan_id: data.plan_id || undefined,
        amc_type: 'STANDARD',
        start_date: new Date().toISOString().split('T')[0],
        duration_months: 12,
        total_services: 2,
        base_price: 2999, // Should come from plan
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['amc-contracts'] });
      queryClient.invalidateQueries({ queryKey: ['amc-stats'] });
      toast.success('AMC contract created');
      setIsCreateContractOpen(false);
      setContractForm({ customer_phone: '', serial_number: '', plan_id: '', auto_renew: true });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create AMC contract');
    },
  });

  const createPlanMutation = useMutation({
    mutationFn: async (data: typeof planForm) => {
      return amcApi.createPlan({
        name: data.name,
        code: data.code,
        duration_months: parseInt(data.duration_months),
        services_included: parseInt(data.visits_included),
        base_price: parseFloat(data.price),
        parts_covered: data.parts_covered,
        labor_covered: data.labor_covered,
        priority_service: data.priority_support,
        description: data.description,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['amc-plans'] });
      toast.success('AMC plan created');
      setIsCreatePlanOpen(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create AMC plan');
    },
  });

  const activateContractMutation = useMutation({
    mutationFn: async (contractId: string) => {
      return amcApi.activateContract(contractId, 'ONLINE');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['amc-contracts'] });
      queryClient.invalidateQueries({ queryKey: ['amc-stats'] });
      toast.success('Contract activated');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to activate contract');
    },
  });

  const renewContractMutation = useMutation({
    mutationFn: async (data: { contractId: string; planId: string }) => {
      return amcApi.renewContract(data.contractId, data.planId || undefined);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['amc-contracts'] });
      queryClient.invalidateQueries({ queryKey: ['amc-stats'] });
      toast.success('Contract renewed successfully');
      setIsRenewOpen(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to renew contract');
    },
  });

  const getColumns = (): ColumnDef<AMCContract>[] => [
    {
      accessorKey: 'contract_number',
      header: 'Contract',
      cell: ({ row }) => (
        <div
          className="flex items-center gap-2 cursor-pointer hover:opacity-80"
          onClick={() => router.push(`/dashboard/service/amc/${row.original.id}`)}
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
            <Shield className="h-4 w-4" />
          </div>
          <div>
            <div className="font-medium">{row.original.contract_number}</div>
            <div className="text-xs text-muted-foreground">{row.original.plan_name}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'customer_name',
      header: 'Customer',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.customer_name}</div>
          <div className="text-xs text-muted-foreground">{row.original.customer_phone}</div>
        </div>
      ),
    },
    {
      accessorKey: 'product_name',
      header: 'Product',
      cell: ({ row }) => (
        <div className="text-sm">
          <div>{row.original.product_name}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.original.serial_number}</div>
        </div>
      ),
    },
    {
      accessorKey: 'validity',
      header: 'Validity',
      cell: ({ row }) => {
        const isExpiringSoon = row.original.days_remaining <= 30 && row.original.status === 'ACTIVE';
        return (
          <div className="flex items-center gap-1">
            {isExpiringSoon && <AlertTriangle className="h-3 w-3 text-orange-500" />}
            <div className="text-sm">
              <div>{formatDate(row.original.end_date)}</div>
              <div className={`text-xs ${isExpiringSoon ? 'text-orange-600 font-medium' : 'text-muted-foreground'}`}>
                {row.original.days_remaining} days left
              </div>
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'visits',
      header: 'Visits',
      cell: ({ row }) => {
        const percentage = (row.original.visits_used / row.original.visits_included) * 100;
        return (
          <div className="space-y-1">
            <div className="text-sm">
              <span className="font-medium">{row.original.visits_used}</span>
              <span className="text-muted-foreground"> / {row.original.visits_included}</span>
            </div>
            <Progress value={percentage} className="h-1.5 w-16" />
          </div>
        );
      },
    },
    {
      accessorKey: 'amount',
      header: 'Amount',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{formatCurrency(row.original.amount)}</div>
          <Badge className={`text-xs ${paymentStatusColors[row.original.payment_status]}`}>
            {row.original.payment_status}
          </Badge>
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <div className="space-y-1">
          <Badge className={statusColors[row.original.status] ?? 'bg-gray-100 text-gray-800'}>
            {row.original.status?.replace(/_/g, ' ') ?? '-'}
          </Badge>
          {row.original.auto_renew && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <RefreshCw className="h-3 w-3" /> Auto-renew
            </div>
          )}
        </div>
      ),
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => router.push(`/dashboard/service/amc/${row.original.id}`)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            {row.original.status === 'PENDING_ACTIVATION' && (
              <DropdownMenuItem onClick={() => activateContractMutation.mutate(row.original.id)}>
                <CheckCircle className="mr-2 h-4 w-4" />
                Activate
              </DropdownMenuItem>
            )}
            {row.original.status === 'ACTIVE' && (
              <DropdownMenuItem>
                <Wrench className="mr-2 h-4 w-4" />
                Schedule Service
              </DropdownMenuItem>
            )}
            {(row.original.status === 'EXPIRED' || row.original.status === 'PENDING_RENEWAL') && (
              <DropdownMenuItem onClick={() => {
                setSelectedContract(row.original);
                setIsRenewOpen(true);
              }}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Renew Contract
              </DropdownMenuItem>
            )}
            <DropdownMenuItem>
              <FileText className="mr-2 h-4 w-4" />
              Download Contract
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const planColumns: ColumnDef<AMCPlan>[] = [
    {
      accessorKey: 'name',
      header: 'Plan',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.name}</div>
          <div className="text-xs text-muted-foreground">{row.original.code}</div>
        </div>
      ),
    },
    {
      accessorKey: 'duration_months',
      header: 'Duration',
      cell: ({ row }) => `${row.original.duration_months} months`,
    },
    {
      accessorKey: 'visits_included',
      header: 'Visits',
      cell: ({ row }) => row.original.visits_included,
    },
    {
      accessorKey: 'price',
      header: 'Price',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{formatCurrency(row.original.price)}</div>
          {row.original.discount_percentage > 0 && (
            <div className="text-xs text-green-600">{row.original.discount_percentage}% parts discount</div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'coverage',
      header: 'Coverage',
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.parts_covered && <Badge variant="outline" className="text-xs">Parts</Badge>}
          {row.original.labor_covered && <Badge variant="outline" className="text-xs">Labor</Badge>}
          {row.original.priority_support && <Badge className="text-xs bg-purple-100 text-purple-800">Priority</Badge>}
        </div>
      ),
    },
    {
      accessorKey: 'contracts_count',
      header: 'Contracts',
      cell: ({ row }) => row.original.contracts_count,
    },
    {
      accessorKey: 'is_active',
      header: 'Status',
      cell: ({ row }) => (
        <Badge variant={row.original.is_active ? 'default' : 'secondary'}>
          {row.original.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              Edit Plan
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="AMC Management"
        description="Annual Maintenance Contracts and service plans"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setIsCreatePlanOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Plan
            </Button>
            <Button onClick={() => setIsCreateContractOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Contract
            </Button>
          </div>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Contracts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.active_contracts || 0}</div>
            <div className="text-sm text-muted-foreground">
              of {stats?.total_contracts || 0} total
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Expiring Soon</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.expiring_soon || 0}</div>
            <div className="text-sm text-muted-foreground">
              Within 30 days
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Pending Renewal</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{stats?.pending_renewal || 0}</div>
            <div className="text-sm text-muted-foreground">
              Awaiting action
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Revenue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{formatCurrency(stats?.total_revenue || 0)}</div>
            <div className="text-sm text-muted-foreground">
              This month: {formatCurrency(stats?.this_month_revenue || 0)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Renewal Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.renewal_rate || 0}%</div>
            <Progress value={stats?.renewal_rate || 0} className="mt-2" />
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue="contracts">
        <TabsList>
          <TabsTrigger value="contracts">Contracts</TabsTrigger>
          <TabsTrigger value="plans">AMC Plans</TabsTrigger>
          <TabsTrigger value="renewals">Due for Renewal</TabsTrigger>
        </TabsList>

        <TabsContent value="contracts" className="mt-4 space-y-4">
          <div className="flex items-center gap-4">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="ACTIVE">Active</SelectItem>
                <SelectItem value="PENDING_ACTIVATION">Pending Activation</SelectItem>
                <SelectItem value="PENDING_RENEWAL">Pending Renewal</SelectItem>
                <SelectItem value="EXPIRED">Expired</SelectItem>
                <SelectItem value="CANCELLED">Cancelled</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm">
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
          <DataTable<AMCContract, unknown>
            columns={getColumns()}
            data={contractsData?.items ?? []}
            searchKey="contract_number"
            searchPlaceholder="Search contracts..."
            isLoading={contractsLoading}
            manualPagination
            pageCount={contractsData?.pages ?? 0}
            pageIndex={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={() => {}}
          />
        </TabsContent>

        <TabsContent value="plans" className="mt-4">
          <DataTable<AMCPlan, unknown>
            columns={planColumns}
            data={plansData?.items ?? []}
            searchKey="name"
            searchPlaceholder="Search plans..."
            isLoading={plansLoading}
          />
        </TabsContent>

        <TabsContent value="renewals" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Contracts Due for Renewal</CardTitle>
              <CardDescription>Contracts expiring in the next 30 days</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Contract</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Product</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead>Current Plan</TableHead>
                    <TableHead>Auto-Renew</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {contractsData?.items
                    .filter((c: AMCContract) => c.days_remaining <= 30 || c.status === 'PENDING_RENEWAL')
                    .map((contract: AMCContract) => (
                      <TableRow key={contract.id}>
                        <TableCell className="font-mono">{contract.contract_number}</TableCell>
                        <TableCell>
                          <div>{contract.customer_name}</div>
                          <div className="text-xs text-muted-foreground">{contract.customer_phone}</div>
                        </TableCell>
                        <TableCell>{contract.product_name}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3 text-orange-500" />
                            <span className="text-orange-600 font-medium">{contract.days_remaining} days</span>
                          </div>
                        </TableCell>
                        <TableCell>{contract.plan_name}</TableCell>
                        <TableCell>
                          {contract.auto_renew ? (
                            <Badge className="bg-green-100 text-green-800">Yes</Badge>
                          ) : (
                            <Badge variant="outline">No</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button size="sm" variant="outline" onClick={() => {
                              setSelectedContract(contract);
                              setIsRenewOpen(true);
                            }}>
                              <RefreshCw className="mr-1 h-3 w-3" />
                              Renew
                            </Button>
                            <Button size="sm" variant="ghost">
                              <Bell className="h-3 w-3" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create Contract Dialog */}
      <Dialog open={isCreateContractOpen} onOpenChange={setIsCreateContractOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create AMC Contract</DialogTitle>
            <DialogDescription>Create a new Annual Maintenance Contract</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="customer_phone">Customer Phone</Label>
              <Input
                id="customer_phone"
                placeholder="Enter customer phone number"
                value={contractForm.customer_phone}
                onChange={(e) => setContractForm({ ...contractForm, customer_phone: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="serial_number">Product Serial Number</Label>
              <Input
                id="serial_number"
                placeholder="Enter product serial number"
                value={contractForm.serial_number}
                onChange={(e) => setContractForm({ ...contractForm, serial_number: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>AMC Plan</Label>
              <Select
                value={contractForm.plan_id}
                onValueChange={(value) => setContractForm({ ...contractForm, plan_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a plan" />
                </SelectTrigger>
                <SelectContent>
                  {plansData?.items.map((plan: AMCPlan) => (
                    <SelectItem key={plan.id} value={plan.id}>
                      {plan.name} - {formatCurrency(plan.price)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="auto_renew"
                checked={contractForm.auto_renew}
                onCheckedChange={(checked) => setContractForm({ ...contractForm, auto_renew: !!checked })}
              />
              <Label htmlFor="auto_renew">Enable auto-renewal</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateContractOpen(false)}>Cancel</Button>
            <Button onClick={() => createContractMutation.mutate(contractForm)}>Create Contract</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Plan Dialog */}
      <Dialog open={isCreatePlanOpen} onOpenChange={setIsCreatePlanOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create AMC Plan</DialogTitle>
            <DialogDescription>Define a new AMC plan structure</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="plan_name">Plan Name</Label>
                <Input
                  id="plan_name"
                  placeholder="e.g., Premium Care"
                  value={planForm.name}
                  onChange={(e) => setPlanForm({ ...planForm, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="plan_code">Plan Code</Label>
                <Input
                  id="plan_code"
                  placeholder="e.g., AMC-PREM"
                  value={planForm.code}
                  onChange={(e) => setPlanForm({ ...planForm, code: e.target.value.toUpperCase() })}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="duration">Duration (months)</Label>
                <Input
                  id="duration"
                  type="number"
                  value={planForm.duration_months}
                  onChange={(e) => setPlanForm({ ...planForm, duration_months: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="visits">Visits Included</Label>
                <Input
                  id="visits"
                  type="number"
                  value={planForm.visits_included}
                  onChange={(e) => setPlanForm({ ...planForm, visits_included: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="price">Price</Label>
                <Input
                  id="price"
                  type="number"
                  placeholder="4999"
                  value={planForm.price}
                  onChange={(e) => setPlanForm({ ...planForm, price: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Coverage</Label>
              <div className="flex gap-4">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="parts"
                    checked={planForm.parts_covered}
                    onCheckedChange={(checked) => setPlanForm({ ...planForm, parts_covered: !!checked })}
                  />
                  <Label htmlFor="parts">Parts</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="labor"
                    checked={planForm.labor_covered}
                    onCheckedChange={(checked) => setPlanForm({ ...planForm, labor_covered: !!checked })}
                  />
                  <Label htmlFor="labor">Labor</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="priority"
                    checked={planForm.priority_support}
                    onCheckedChange={(checked) => setPlanForm({ ...planForm, priority_support: !!checked })}
                  />
                  <Label htmlFor="priority">Priority Support</Label>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe the plan benefits..."
                value={planForm.description}
                onChange={(e) => setPlanForm({ ...planForm, description: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreatePlanOpen(false)}>Cancel</Button>
            <Button onClick={() => createPlanMutation.mutate(planForm)}>Create Plan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Renew Contract Dialog */}
      <Dialog open={isRenewOpen} onOpenChange={setIsRenewOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Renew AMC Contract</DialogTitle>
            <DialogDescription>
              {selectedContract && `Renewing contract ${selectedContract.contract_number}`}
            </DialogDescription>
          </DialogHeader>
          {selectedContract && (
            <div className="space-y-4 py-4">
              <div className="rounded-lg bg-muted p-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Customer</span>
                  <span className="font-medium">{selectedContract.customer_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Product</span>
                  <span>{selectedContract.product_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Current Plan</span>
                  <span>{selectedContract.plan_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Expires</span>
                  <span>{formatDate(selectedContract.end_date)}</span>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Renewal Plan</Label>
                <Select defaultValue={selectedContract.plan_id}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {plansData?.items.map((plan: AMCPlan) => (
                      <SelectItem key={plan.id} value={plan.id}>
                        {plan.name} - {formatCurrency(plan.price)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox id="renew_auto" defaultChecked={selectedContract.auto_renew} />
                <Label htmlFor="renew_auto">Enable auto-renewal for next term</Label>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRenewOpen(false)}>Cancel</Button>
            <Button onClick={() => selectedContract && renewContractMutation.mutate({ contractId: selectedContract.id, planId: selectedContract.plan_id })}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Renew Contract
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
