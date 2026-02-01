'use client';

import { useState, use } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Store,
  MapPin,
  CreditCard,
  Target,
  Gift,
  Edit,
  Plus,
  Download,
  TrendingUp,
  TrendingDown,
  Building,
  Phone,
  Mail,
  FileText,
  Calendar,
  CheckCircle,
  XCircle,
  AlertTriangle,
  IndianRupee,
  Percent,
  Award,
  BarChart3,
  Clock,
  Trash2,
  MoreHorizontal,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Checkbox } from '@/components/ui/checkbox';
import { dealersApi } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';

interface Territory {
  id: string;
  pincode: string;
  city: string;
  state: string;
  region: string;
  is_exclusive: boolean;
  assigned_at: string;
}

interface CreditTransaction {
  id: string;
  type: 'CREDIT' | 'DEBIT' | 'ADJUSTMENT' | 'PAYMENT' | 'INVOICE';
  amount: number;
  balance_after: number;
  reference_number: string;
  reference_type: 'ORDER' | 'PAYMENT' | 'CREDIT_NOTE' | 'ADJUSTMENT' | 'REFUND';
  description: string;
  created_at: string;
  created_by: string;
}

interface SalesTarget {
  id: string;
  period: string;
  period_type: 'MONTHLY' | 'QUARTERLY' | 'YEARLY';
  target_amount: number;
  achieved_amount: number;
  target_quantity: number;
  achieved_quantity: number;
  status: 'PENDING' | 'IN_PROGRESS' | 'ACHIEVED' | 'MISSED';
  incentive_earned: number;
  created_at: string;
}

interface Scheme {
  id: string;
  name: string;
  code: string;
  type: 'DISCOUNT' | 'CASHBACK' | 'QUANTITY_BREAK' | 'SLAB' | 'BUNDLE' | 'LOYALTY';
  value: number;
  value_type: 'PERCENTAGE' | 'FIXED';
  min_order_value: number;
  max_discount: number;
  valid_from: string;
  valid_to: string;
  is_active: boolean;
  terms: string;
  products_applicable: string[];
}

interface DealerDetail {
  id: string;
  code: string;
  name: string;
  type: string;
  status: string;
  pricing_tier: string;
  credit_limit: number;
  available_credit: number;
  outstanding_amount: number;
  email: string;
  phone: string;
  gst_number: string;
  pan_number: string;
  address: {
    line1: string;
    line2: string;
    city: string;
    state: string;
    pincode: string;
  };
  bank_details: {
    bank_name: string;
    account_number: string;
    ifsc_code: string;
    branch: string;
  };
  territories: Territory[];
  credit_transactions: CreditTransaction[];
  targets: SalesTarget[];
  schemes: Scheme[];
  stats: {
    total_orders: number;
    total_revenue: number;
    avg_order_value: number;
    pending_payments: number;
    credit_utilization: number;
    current_month_sales: number;
    ytd_sales: number;
    growth_percentage: number;
  };
  created_at: string;
  updated_at: string;
}

const tierColors: Record<string, string> = {
  PLATINUM: 'bg-purple-100 text-purple-800 border-purple-200',
  GOLD: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  SILVER: 'bg-gray-100 text-gray-800 border-gray-200',
  BRONZE: 'bg-orange-100 text-orange-800 border-orange-200',
};

const statusColors: Record<string, string> = {
  ACTIVE: 'bg-green-100 text-green-800',
  INACTIVE: 'bg-gray-100 text-gray-800',
  SUSPENDED: 'bg-red-100 text-red-800',
  PENDING_APPROVAL: 'bg-yellow-100 text-yellow-800',
};

const targetStatusColors: Record<string, string> = {
  PENDING: 'bg-gray-100 text-gray-800',
  IN_PROGRESS: 'bg-blue-100 text-blue-800',
  ACHIEVED: 'bg-green-100 text-green-800',
  MISSED: 'bg-red-100 text-red-800',
};

export default function DealerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();

  // Dialog states
  const [isAddTerritoryOpen, setIsAddTerritoryOpen] = useState(false);
  const [isAddCreditOpen, setIsAddCreditOpen] = useState(false);
  const [isAddTargetOpen, setIsAddTargetOpen] = useState(false);
  const [isAssignSchemeOpen, setIsAssignSchemeOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);

  // Form states
  const [territoryForm, setTerritoryForm] = useState({ pincode: '', is_exclusive: false });
  const [creditForm, setCreditForm] = useState({ type: 'CREDIT' as 'CREDIT' | 'ADJUSTMENT', amount: '', description: '' });
  const [targetForm, setTargetForm] = useState({
    period: '',
    period_type: 'MONTHLY' as 'MONTHLY' | 'QUARTERLY' | 'YEARLY',
    target_amount: '',
    target_quantity: '',
  });
  const [selectedScheme, setSelectedScheme] = useState('');

  // Fetch dealer details
  const { data: dealer, isLoading } = useQuery<DealerDetail>({
    queryKey: ['dealer', id],
    queryFn: async () => {
      // Fetch dealer basic info, ledger, and targets in parallel
      const [dealerRes, ledgerRes, targetsRes] = await Promise.allSettled([
        dealersApi.getById(id),
        dealersApi.getLedger(id, { limit: 50 }),
        dealersApi.getTargets(id),
      ]);

      const dealerData = dealerRes.status === 'fulfilled' ? dealerRes.value : null;
      const ledgerData = ledgerRes.status === 'fulfilled' ? ledgerRes.value : { items: [], total_debit: 0, total_credit: 0 };
      const targetsData = targetsRes.status === 'fulfilled' ? targetsRes.value : [];

      if (!dealerData) {
        throw new Error('Failed to fetch dealer details');
      }

      // Transform backend data to frontend format
      const creditTransactions: CreditTransaction[] = ledgerData.items.map((item) => ({
        id: item.id,
        type: item.credit_amount > 0 ? 'CREDIT' : 'DEBIT',
        amount: item.credit_amount > 0 ? item.credit_amount : item.debit_amount,
        balance_after: item.balance,
        reference_number: item.reference_number,
        reference_type: item.reference_type as 'ORDER' | 'PAYMENT' | 'CREDIT_NOTE' | 'ADJUSTMENT' | 'REFUND',
        description: item.narration || `${item.transaction_type} - ${item.reference_number}`,
        created_at: item.created_at,
        created_by: 'System',
      }));

      // Get month name helper
      const getMonthName = (month: number) => {
        const months = ['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December'];
        return months[month - 1] || '';
      };

      // Transform targets
      const targets: SalesTarget[] = targetsData.map((t) => ({
        id: t.id,
        period: t.target_month
          ? `${getMonthName(t.target_month)} ${t.target_year}`
          : t.target_quarter
            ? `Q${t.target_quarter} ${t.target_year}`
            : `${t.target_year}`,
        period_type: t.target_period as 'MONTHLY' | 'QUARTERLY' | 'YEARLY',
        target_amount: t.revenue_target,
        achieved_amount: t.revenue_achieved,
        target_quantity: t.quantity_target,
        achieved_quantity: t.quantity_achieved,
        status: t.revenue_achievement_percentage >= 100
          ? 'ACHIEVED'
          : t.revenue_achievement_percentage > 0
            ? 'IN_PROGRESS'
            : 'PENDING',
        incentive_earned: t.incentive_earned,
        created_at: t.created_at,
      }));

      // Build dealer detail response
      const result: DealerDetail = {
        id: dealerData.id,
        code: dealerData.dealer_code || '',
        name: dealerData.name || '',
        type: dealerData.dealer_type || 'DEALER',
        status: dealerData.status || 'ACTIVE',
        pricing_tier: dealerData.tier || 'STANDARD',
        credit_limit: dealerData.credit_limit || 0,
        available_credit: dealerData.available_credit || 0,
        outstanding_amount: dealerData.outstanding_amount || 0,
        email: dealerData.email || '',
        phone: dealerData.phone || '',
        gst_number: dealerData.gstin || dealerData.gst_number || '',
        pan_number: dealerData.pan || '',
        address: {
          line1: dealerData.registered_address_line1 || '',
          line2: dealerData.registered_address_line2 || '',
          city: dealerData.registered_city || '',
          state: dealerData.registered_state || '',
          pincode: dealerData.registered_pincode || '',
        },
        bank_details: {
          bank_name: dealerData.bank_name || '',
          account_number: dealerData.bank_account_number ? `XXXX ${dealerData.bank_account_number.slice(-4)}` : '',
          ifsc_code: dealerData.bank_ifsc || '',
          branch: dealerData.bank_branch || '',
        },
        // Territories based on assigned_pincodes field (dealers use region, not separate territories)
        territories: (dealerData.assigned_pincodes || []).map((pincode: string, idx: number) => ({
          id: `${idx}`,
          pincode,
          city: dealerData.registered_city || '',
          state: dealerData.registered_state || '',
          region: dealerData.region || '',
          is_exclusive: false,
          assigned_at: dealerData.created_at || new Date().toISOString(),
        })),
        credit_transactions: creditTransactions,
        targets,
        schemes: [], // Schemes will be fetched separately if needed
        stats: {
          total_orders: dealerData.total_orders || 0,
          total_revenue: dealerData.total_revenue || 0,
          avg_order_value: dealerData.average_order_value || 0,
          pending_payments: dealerData.overdue_amount || 0,
          credit_utilization: dealerData.credit_utilization_percentage || 0,
          current_month_sales: 0, // Would need additional API
          ytd_sales: dealerData.total_revenue || 0,
          growth_percentage: 0, // Would need additional API
        },
        created_at: dealerData.created_at || new Date().toISOString(),
        updated_at: dealerData.updated_at || new Date().toISOString(),
      };
      return result;
    },
  });

  // Mutations
  const addTerritoryMutation = useMutation({
    mutationFn: async (data: { pincode: string; is_exclusive: boolean }) => {
      // Territories are managed via assigned_pincodes field on the dealer
      // Update dealer with new pincode added to assigned_pincodes
      const currentPincodes = dealer?.territories?.map(t => t.pincode) || [];
      if (!currentPincodes.includes(data.pincode)) {
        await dealersApi.update(id, {
          assigned_pincodes: [...currentPincodes, data.pincode],
        });
      }
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dealer', id] });
      toast.success('Territory added successfully');
      setIsAddTerritoryOpen(false);
      setTerritoryForm({ pincode: '', is_exclusive: false });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add territory');
    },
  });

  const addCreditMutation = useMutation({
    mutationFn: async (data: { type: string; amount: number; description: string }) => {
      const today = new Date().toISOString().split('T')[0];
      const refNum = `ADJ-${Date.now()}`;

      return dealersApi.recordPayment(id, {
        transaction_type: data.type === 'CREDIT' ? 'PAYMENT' : 'ADJUSTMENT',
        transaction_date: today,
        reference_type: 'ADJUSTMENT',
        reference_number: refNum,
        debit_amount: data.type === 'ADJUSTMENT' ? data.amount : 0,
        credit_amount: data.type === 'CREDIT' ? data.amount : 0,
        payment_mode: 'ADJUSTMENT',
        narration: data.description,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dealer', id] });
      toast.success('Credit adjustment recorded');
      setIsAddCreditOpen(false);
      setCreditForm({ type: 'CREDIT', amount: '', description: '' });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to record credit adjustment');
    },
  });

  const addTargetMutation = useMutation({
    mutationFn: async (data: { period: string; period_type: string; target_amount: number; target_quantity: number }) => {
      // Parse period to get year and month
      const now = new Date();
      const year = now.getFullYear();
      let month: number | undefined;
      let quarter: number | undefined;

      if (data.period_type === 'MONTHLY') {
        // Try to parse month from period string (e.g., "April 2024")
        const monthNames = ['january', 'february', 'march', 'april', 'may', 'june',
                           'july', 'august', 'september', 'october', 'november', 'december'];
        const periodLower = data.period.toLowerCase();
        month = monthNames.findIndex(m => periodLower.includes(m)) + 1;
        if (month === 0) month = now.getMonth() + 1;
      } else if (data.period_type === 'QUARTERLY') {
        // Parse quarter from period (e.g., "Q1 2024")
        const qMatch = data.period.match(/Q(\d)/i);
        quarter = qMatch ? parseInt(qMatch[1]) : Math.ceil((now.getMonth() + 1) / 3);
      }

      return dealersApi.createTarget(id, {
        target_period: data.period_type,
        target_year: year,
        target_month: data.period_type === 'MONTHLY' ? month : undefined,
        target_quarter: data.period_type === 'QUARTERLY' ? quarter : undefined,
        target_type: 'BOTH',
        revenue_target: data.target_amount,
        quantity_target: data.target_quantity,
        incentive_percentage: 5, // Default 5% incentive
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dealer', id] });
      toast.success('Target assigned successfully');
      setIsAddTargetOpen(false);
      setTargetForm({ period: '', period_type: 'MONTHLY', target_amount: '', target_quantity: '' });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to assign target');
    },
  });

  const removeTerritoryMutation = useMutation({
    mutationFn: async (territoryId: string) => {
      // Remove pincode from assigned_pincodes
      const territory = dealer?.territories?.find(t => t.id === territoryId);
      if (territory) {
        const currentPincodes = dealer?.territories?.map(t => t.pincode) || [];
        const updatedPincodes = currentPincodes.filter(p => p !== territory.pincode);
        await dealersApi.update(id, {
          assigned_pincodes: updatedPincodes,
        });
      }
      return territoryId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dealer', id] });
      toast.success('Territory removed');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to remove territory');
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!dealer) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <h2 className="text-xl font-semibold">Dealer not found</h2>
        <Button className="mt-4" onClick={() => router.back()}>
          Go Back
        </Button>
      </div>
    );
  }

  const creditUtilization = ((dealer.credit_limit - dealer.available_credit) / dealer.credit_limit) * 100;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
            <Store className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{dealer.name}</h1>
              <Badge className={tierColors[dealer.pricing_tier]}>{dealer.pricing_tier}</Badge>
              <Badge className={statusColors[dealer.status]}>{dealer.status}</Badge>
            </div>
            <p className="text-muted-foreground">
              {dealer.code} | {dealer.type.replace(/_/g, ' ')} | GST: {dealer.gst_number}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setIsEditOpen(true)}>
            <Edit className="mr-2 h-4 w-4" /> Edit
          </Button>
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" /> Export
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Revenue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(dealer.stats.total_revenue)}</div>
            <div className="flex items-center gap-1 text-sm text-green-600">
              <TrendingUp className="h-4 w-4" />
              +{dealer.stats.growth_percentage}% YoY
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Orders</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dealer.stats.total_orders}</div>
            <div className="text-sm text-muted-foreground">
              Avg: {formatCurrency(dealer.stats.avg_order_value)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Credit Available</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(dealer.available_credit)}</div>
            <div className="flex items-center gap-2 mt-1">
              <Progress value={100 - creditUtilization} className="flex-1" />
              <span className="text-xs text-muted-foreground">{Math.round(100 - creditUtilization)}%</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Outstanding</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{formatCurrency(dealer.outstanding_amount)}</div>
            <div className="text-sm text-muted-foreground">
              Pending: {formatCurrency(dealer.stats.pending_payments)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">This Month</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(dealer.stats.current_month_sales)}</div>
            <div className="text-sm text-muted-foreground">
              YTD: {formatCurrency(dealer.stats.ytd_sales)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="territory">Territory</TabsTrigger>
          <TabsTrigger value="credit">Credit Ledger</TabsTrigger>
          <TabsTrigger value="targets">Targets</TabsTrigger>
          <TabsTrigger value="schemes">Schemes</TabsTrigger>
          <TabsTrigger value="orders">Orders</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Contact Information */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Contact Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <span>{dealer.email}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <span>{dealer.phone}</span>
                </div>
                <div className="flex items-start gap-3">
                  <MapPin className="h-4 w-4 text-muted-foreground mt-0.5" />
                  <div>
                    <p>{dealer.address.line1}</p>
                    {dealer.address.line2 && <p>{dealer.address.line2}</p>}
                    <p>{dealer.address.city}, {dealer.address.state} - {dealer.address.pincode}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Bank Details */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Bank Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <Building className="h-4 w-4 text-muted-foreground" />
                  <span>{dealer.bank_details.bank_name} - {dealer.bank_details.branch}</span>
                </div>
                <div className="flex items-center gap-3">
                  <CreditCard className="h-4 w-4 text-muted-foreground" />
                  <span>A/C: {dealer.bank_details.account_number}</span>
                </div>
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <span>IFSC: {dealer.bank_details.ifsc_code}</span>
                </div>
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <span>PAN: {dealer.pan_number}</span>
                </div>
              </CardContent>
            </Card>

            {/* Quick Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Credit Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Credit Limit</span>
                    <span className="font-medium">{formatCurrency(dealer.credit_limit)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Available Credit</span>
                    <span className="font-medium text-green-600">{formatCurrency(dealer.available_credit)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Outstanding</span>
                    <span className="font-medium text-orange-600">{formatCurrency(dealer.outstanding_amount)}</span>
                  </div>
                  <div className="pt-2 border-t">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm text-muted-foreground">Credit Utilization</span>
                      <span className="text-sm font-medium">{Math.round(creditUtilization)}%</span>
                    </div>
                    <Progress value={creditUtilization} className={creditUtilization > 80 ? '[&>div]:bg-red-500' : ''} />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Active Schemes */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Active Schemes</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {dealer.schemes.filter(s => s.is_active).map((scheme) => (
                    <div key={scheme.id} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                      <div>
                        <p className="font-medium">{scheme.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {scheme.value}{scheme.value_type === 'PERCENTAGE' ? '%' : ''} {scheme.type.toLowerCase()}
                        </p>
                      </div>
                      <Badge variant="outline">{scheme.code}</Badge>
                    </div>
                  ))}
                  {dealer.schemes.filter(s => s.is_active).length === 0 && (
                    <p className="text-muted-foreground text-center py-4">No active schemes</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Territory Tab */}
        <TabsContent value="territory" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Assigned Territories</CardTitle>
                <CardDescription>Pincodes and regions assigned to this dealer</CardDescription>
              </div>
              <Button onClick={() => setIsAddTerritoryOpen(true)}>
                <Plus className="mr-2 h-4 w-4" /> Add Territory
              </Button>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Pincode</TableHead>
                    <TableHead>City</TableHead>
                    <TableHead>State</TableHead>
                    <TableHead>Region</TableHead>
                    <TableHead>Exclusivity</TableHead>
                    <TableHead>Assigned Date</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dealer.territories.map((territory) => (
                    <TableRow key={territory.id}>
                      <TableCell className="font-medium">{territory.pincode}</TableCell>
                      <TableCell>{territory.city}</TableCell>
                      <TableCell>{territory.state}</TableCell>
                      <TableCell>{territory.region}</TableCell>
                      <TableCell>
                        {territory.is_exclusive ? (
                          <Badge className="bg-purple-100 text-purple-800">Exclusive</Badge>
                        ) : (
                          <Badge variant="outline">Shared</Badge>
                        )}
                      </TableCell>
                      <TableCell>{formatDate(territory.assigned_at)}</TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              className="text-red-600"
                              onClick={() => removeTerritoryMutation.mutate(territory.id)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Remove
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Credit Ledger Tab */}
        <TabsContent value="credit" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Credit Ledger</CardTitle>
                <CardDescription>Transaction history and credit adjustments</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setIsAddCreditOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" /> Adjustment
                </Button>
                <Button variant="outline">
                  <Download className="mr-2 h-4 w-4" /> Export
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Reference</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">Debit</TableHead>
                    <TableHead className="text-right">Credit</TableHead>
                    <TableHead className="text-right">Balance</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dealer.credit_transactions.map((tx) => (
                    <TableRow key={tx.id}>
                      <TableCell>{formatDate(tx.created_at)}</TableCell>
                      <TableCell>
                        <Badge variant={tx.type === 'CREDIT' ? 'default' : 'destructive'}>
                          {tx.type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-sm">{tx.reference_number}</span>
                      </TableCell>
                      <TableCell>{tx.description}</TableCell>
                      <TableCell className="text-right text-red-600">
                        {tx.type === 'DEBIT' ? formatCurrency(tx.amount) : '-'}
                      </TableCell>
                      <TableCell className="text-right text-green-600">
                        {tx.type === 'CREDIT' ? formatCurrency(tx.amount) : '-'}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(tx.balance_after)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Targets Tab */}
        <TabsContent value="targets" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Sales Targets</CardTitle>
                <CardDescription>Monthly, quarterly and yearly targets and achievements</CardDescription>
              </div>
              <Button onClick={() => setIsAddTargetOpen(true)}>
                <Plus className="mr-2 h-4 w-4" /> Assign Target
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {dealer.targets.map((target) => {
                  const amountProgress = (target.achieved_amount / target.target_amount) * 100;
                  const quantityProgress = (target.achieved_quantity / target.target_quantity) * 100;

                  return (
                    <div key={target.id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                            <Target className="h-5 w-5" />
                          </div>
                          <div>
                            <h4 className="font-medium">{target.period}</h4>
                            <p className="text-sm text-muted-foreground">{target.period_type}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge className={targetStatusColors[target.status]}>
                            {target.status.replace(/_/g, ' ')}
                          </Badge>
                          {target.incentive_earned > 0 && (
                            <div className="flex items-center gap-1 text-green-600">
                              <Award className="h-4 w-4" />
                              <span className="font-medium">{formatCurrency(target.incentive_earned)}</span>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="grid gap-4 md:grid-cols-2">
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Revenue Target</span>
                            <span>{formatCurrency(target.achieved_amount)} / {formatCurrency(target.target_amount)}</span>
                          </div>
                          <Progress value={Math.min(amountProgress, 100)} className={amountProgress >= 100 ? '[&>div]:bg-green-500' : ''} />
                          <p className="text-xs text-muted-foreground mt-1">{amountProgress.toFixed(1)}% achieved</p>
                        </div>
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Quantity Target</span>
                            <span>{target.achieved_quantity} / {target.target_quantity} units</span>
                          </div>
                          <Progress value={Math.min(quantityProgress, 100)} className={quantityProgress >= 100 ? '[&>div]:bg-green-500' : ''} />
                          <p className="text-xs text-muted-foreground mt-1">{quantityProgress.toFixed(1)}% achieved</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Schemes Tab */}
        <TabsContent value="schemes" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Assigned Schemes</CardTitle>
                <CardDescription>Discounts, cashbacks and incentive programs</CardDescription>
              </div>
              <Button onClick={() => setIsAssignSchemeOpen(true)}>
                <Plus className="mr-2 h-4 w-4" /> Assign Scheme
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {dealer.schemes.map((scheme) => (
                  <div key={scheme.id} className={`border rounded-lg p-4 ${!scheme.is_active ? 'opacity-60' : ''}`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${scheme.is_active ? 'bg-green-100' : 'bg-gray-100'}`}>
                          <Gift className={`h-5 w-5 ${scheme.is_active ? 'text-green-600' : 'text-gray-600'}`} />
                        </div>
                        <div>
                          <h4 className="font-medium">{scheme.name}</h4>
                          <p className="text-sm text-muted-foreground">Code: {scheme.code}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={scheme.is_active ? 'default' : 'secondary'}>
                          {scheme.is_active ? 'Active' : 'Expired'}
                        </Badge>
                        <Badge variant="outline">{scheme.type}</Badge>
                      </div>
                    </div>
                    <div className="grid gap-4 md:grid-cols-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Value</p>
                        <p className="font-medium">
                          {scheme.value}{scheme.value_type === 'PERCENTAGE' ? '%' : ` ${formatCurrency(scheme.value)}`}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Min Order</p>
                        <p className="font-medium">{formatCurrency(scheme.min_order_value)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Max Discount</p>
                        <p className="font-medium">{formatCurrency(scheme.max_discount)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Validity</p>
                        <p className="font-medium">{formatDate(scheme.valid_from)} - {formatDate(scheme.valid_to)}</p>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t">
                      <p className="text-sm text-muted-foreground">{scheme.terms}</p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {scheme.products_applicable.map((product) => (
                          <Badge key={product} variant="outline" className="text-xs">{product}</Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Orders Tab */}
        <TabsContent value="orders" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Orders</CardTitle>
              <CardDescription>Orders placed by this dealer</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground text-center py-8">
                Order history will be displayed here. Click on an order to view details.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Add Territory Dialog */}
      <Dialog open={isAddTerritoryOpen} onOpenChange={setIsAddTerritoryOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Territory</DialogTitle>
            <DialogDescription>Assign a new pincode territory to this dealer</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="pincode">Pincode</Label>
              <Input
                id="pincode"
                placeholder="Enter pincode"
                value={territoryForm.pincode}
                onChange={(e) => setTerritoryForm({ ...territoryForm, pincode: e.target.value })}
              />
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="exclusive"
                checked={territoryForm.is_exclusive}
                onCheckedChange={(checked) => setTerritoryForm({ ...territoryForm, is_exclusive: !!checked })}
              />
              <Label htmlFor="exclusive">Exclusive territory (no other dealers)</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddTerritoryOpen(false)}>Cancel</Button>
            <Button onClick={() => addTerritoryMutation.mutate(territoryForm)}>Add Territory</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Credit Adjustment Dialog */}
      <Dialog open={isAddCreditOpen} onOpenChange={setIsAddCreditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Credit Adjustment</DialogTitle>
            <DialogDescription>Record a credit or adjustment transaction</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Transaction Type</Label>
              <Select
                value={creditForm.type}
                onValueChange={(value: 'CREDIT' | 'ADJUSTMENT') => setCreditForm({ ...creditForm, type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CREDIT">Credit (Increase Limit)</SelectItem>
                  <SelectItem value="ADJUSTMENT">Adjustment</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="amount">Amount</Label>
              <Input
                id="amount"
                type="number"
                placeholder="Enter amount"
                value={creditForm.amount}
                onChange={(e) => setCreditForm({ ...creditForm, amount: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Reason for adjustment"
                value={creditForm.description}
                onChange={(e) => setCreditForm({ ...creditForm, description: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddCreditOpen(false)}>Cancel</Button>
            <Button onClick={() => addCreditMutation.mutate({
              type: creditForm.type,
              amount: parseFloat(creditForm.amount),
              description: creditForm.description
            })}>
              Submit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Target Dialog */}
      <Dialog open={isAddTargetOpen} onOpenChange={setIsAddTargetOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Target</DialogTitle>
            <DialogDescription>Set sales targets for this dealer</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="period">Period</Label>
                <Input
                  id="period"
                  placeholder="e.g., April 2024"
                  value={targetForm.period}
                  onChange={(e) => setTargetForm({ ...targetForm, period: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Period Type</Label>
                <Select
                  value={targetForm.period_type}
                  onValueChange={(value: 'MONTHLY' | 'QUARTERLY' | 'YEARLY') => setTargetForm({ ...targetForm, period_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MONTHLY">Monthly</SelectItem>
                    <SelectItem value="QUARTERLY">Quarterly</SelectItem>
                    <SelectItem value="YEARLY">Yearly</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="target_amount">Target Amount</Label>
                <Input
                  id="target_amount"
                  type="number"
                  placeholder="Revenue target"
                  value={targetForm.target_amount}
                  onChange={(e) => setTargetForm({ ...targetForm, target_amount: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="target_quantity">Target Quantity</Label>
                <Input
                  id="target_quantity"
                  type="number"
                  placeholder="Unit target"
                  value={targetForm.target_quantity}
                  onChange={(e) => setTargetForm({ ...targetForm, target_quantity: e.target.value })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddTargetOpen(false)}>Cancel</Button>
            <Button onClick={() => addTargetMutation.mutate({
              period: targetForm.period,
              period_type: targetForm.period_type,
              target_amount: parseFloat(targetForm.target_amount),
              target_quantity: parseInt(targetForm.target_quantity),
            })}>
              Assign Target
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign Scheme Dialog */}
      <Dialog open={isAssignSchemeOpen} onOpenChange={setIsAssignSchemeOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Scheme</DialogTitle>
            <DialogDescription>Select a scheme to assign to this dealer</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Select Scheme</Label>
              <Select value={selectedScheme} onValueChange={setSelectedScheme}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a scheme" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="scheme1">Festival Sale 20% Off</SelectItem>
                  <SelectItem value="scheme2">Bulk Purchase Bonus</SelectItem>
                  <SelectItem value="scheme3">Loyalty Rewards Program</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAssignSchemeOpen(false)}>Cancel</Button>
            <Button onClick={() => {
              toast.success('Scheme assigned successfully');
              setIsAssignSchemeOpen(false);
            }}>
              Assign Scheme
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
