'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  Edit,
  UserCheck,
  UserX,
  Phone,
  Mail,
  MapPin,
  Calendar,
  Shield,
  CreditCard,
  TrendingUp,
  Wallet,
  ShoppingCart,
  Award,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  FileText,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/common';
import { partnersApi, PartnerCommission, PartnerPayout, PartnerOrder } from '@/lib/api';
import { toast } from 'sonner';

const statusColors: Record<string, string> = {
  ACTIVE: 'bg-green-100 text-green-800',
  PENDING_KYC: 'bg-yellow-100 text-yellow-800',
  KYC_SUBMITTED: 'bg-blue-100 text-blue-800',
  KYC_REJECTED: 'bg-red-100 text-red-800',
  SUSPENDED: 'bg-orange-100 text-orange-800',
  BLOCKED: 'bg-red-100 text-red-800',
  INACTIVE: 'bg-gray-100 text-gray-800',
};

const kycStatusColors: Record<string, string> = {
  NOT_SUBMITTED: 'bg-gray-100 text-gray-800',
  PENDING: 'bg-yellow-100 text-yellow-800',
  VERIFIED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
};

const commissionStatusColors: Record<string, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  APPROVED: 'bg-blue-100 text-blue-800',
  PAID: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
};

const payoutStatusColors: Record<string, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  PROCESSING: 'bg-blue-100 text-blue-800',
  COMPLETED: 'bg-green-100 text-green-800',
  FAILED: 'bg-red-100 text-red-800',
};

export default function PartnerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const partnerId = params.id as string;

  const [isKycDialogOpen, setIsKycDialogOpen] = useState(false);
  const [isSuspendDialogOpen, setIsSuspendDialogOpen] = useState(false);
  const [kycAction, setKycAction] = useState<'VERIFIED' | 'REJECTED'>('VERIFIED');
  const [kycNotes, setKycNotes] = useState('');
  const [suspendReason, setSuspendReason] = useState('');

  // Fetch partner details
  const { data: partner, isLoading } = useQuery({
    queryKey: ['partner', partnerId],
    queryFn: () => partnersApi.getById(partnerId),
    enabled: !!partnerId,
  });

  // Fetch partner commissions
  const { data: commissionsData } = useQuery({
    queryKey: ['partner-commissions', partnerId],
    queryFn: () => partnersApi.getCommissions(partnerId, { size: 5 }),
    enabled: !!partnerId,
  });

  // Fetch partner payouts
  const { data: payoutsData } = useQuery({
    queryKey: ['partner-payouts', partnerId],
    queryFn: () => partnersApi.getPayouts(partnerId, { size: 5 }),
    enabled: !!partnerId,
  });

  // KYC verification mutation
  const verifyKycMutation = useMutation({
    mutationFn: (verification: { status: 'VERIFIED' | 'REJECTED'; notes?: string }) =>
      partnersApi.verifyKyc(partnerId, verification),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['partner', partnerId] });
      queryClient.invalidateQueries({ queryKey: ['partners'] });
      toast.success(`KYC ${kycAction === 'VERIFIED' ? 'approved' : 'rejected'} successfully`);
      setIsKycDialogOpen(false);
      setKycNotes('');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to verify KYC');
    },
  });

  // Suspend mutation
  const suspendMutation = useMutation({
    mutationFn: (reason: string) => partnersApi.suspend(partnerId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['partner', partnerId] });
      queryClient.invalidateQueries({ queryKey: ['partners'] });
      toast.success('Partner suspended successfully');
      setIsSuspendDialogOpen(false);
      setSuspendReason('');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to suspend partner');
    },
  });

  // Activate mutation
  const activateMutation = useMutation({
    mutationFn: () => partnersApi.activate(partnerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['partner', partnerId] });
      queryClient.invalidateQueries({ queryKey: ['partners'] });
      toast.success('Partner activated successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to activate partner');
    },
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatDateTime = (dateString?: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!partner) {
    return (
      <div className="text-center py-12">
        <h2 className="text-lg font-semibold">Partner not found</h2>
        <Button asChild className="mt-4">
          <Link href="/dashboard/partners">Back to Partners</Link>
        </Button>
      </div>
    );
  }

  const commissions = commissionsData?.items || [];
  const payouts = payoutsData?.items || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard/partners">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <PageHeader
            title={partner.full_name}
            description={`Partner Code: ${partner.partner_code}`}
          />
        </div>
        <div className="flex gap-2">
          {partner.status === 'SUSPENDED' || partner.status === 'BLOCKED' ? (
            <Button
              variant="outline"
              onClick={() => activateMutation.mutate()}
              disabled={activateMutation.isPending}
            >
              {activateMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <UserCheck className="h-4 w-4 mr-2" />
              )}
              Activate
            </Button>
          ) : (
            <Button variant="outline" onClick={() => setIsSuspendDialogOpen(true)}>
              <UserX className="h-4 w-4 mr-2" />
              Suspend
            </Button>
          )}
          {partner.kyc_status === 'PENDING' && (
            <Button variant="outline" onClick={() => setIsKycDialogOpen(true)}>
              <Shield className="h-4 w-4 mr-2" />
              Verify KYC
            </Button>
          )}
          <Button asChild>
            <Link href={`/dashboard/partners/${partnerId}/edit`}>
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Link>
          </Button>
        </div>
      </div>

      {/* Status Badges */}
      <div className="flex gap-2">
        <Badge className={statusColors[partner.status] || 'bg-gray-100'}>
          {partner.status.replace(/_/g, ' ')}
        </Badge>
        <Badge className={kycStatusColors[partner.kyc_status] || 'bg-gray-100'}>
          KYC: {partner.kyc_status.replace(/_/g, ' ')}
        </Badge>
        {partner.tier && (
          <Badge variant="outline">
            <Award className="h-3 w-3 mr-1" />
            {partner.tier.name}
          </Badge>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Orders</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{partner.total_sales_count}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Sales</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(partner.total_sales_value)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Commission Earned</CardTitle>
            <CreditCard className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {formatCurrency(partner.total_commission_earned)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Commission Paid</CardTitle>
            <CheckCircle className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(partner.total_commission_paid)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Wallet Balance</CardTitle>
            <Wallet className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {formatCurrency(partner.wallet_balance)}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>Partner personal details</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Phone className="h-4 w-4 text-muted-foreground" />
              <span>{partner.phone}</span>
            </div>
            {partner.email && (
              <div className="flex items-center gap-3">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <span>{partner.email}</span>
              </div>
            )}
            <div className="flex items-center gap-3">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <span>
                {[partner.city, partner.district, partner.state, partner.pincode]
                  .filter(Boolean)
                  .join(', ') || '-'}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span>Registered: {formatDate(partner.registered_at || partner.created_at)}</span>
            </div>
            <div className="flex items-center gap-3">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span>Referral Code: <code className="text-sm bg-muted px-2 py-1 rounded">{partner.referral_code}</code></span>
            </div>
            {partner.partner_type && (
              <div className="flex items-center gap-3">
                <Award className="h-4 w-4 text-muted-foreground" />
                <span>Type: {partner.partner_type}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* KYC Status */}
        <Card>
          <CardHeader>
            <CardTitle>KYC Verification</CardTitle>
            <CardDescription>Identity and bank verification status</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span>Aadhaar Verified</span>
              {partner.aadhaar_verified ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-400" />
              )}
            </div>
            <div className="flex items-center justify-between">
              <span>PAN Verified</span>
              {partner.pan_verified ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-400" />
              )}
            </div>
            <div className="flex items-center justify-between">
              <span>Bank Verified</span>
              {partner.bank_verified ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-400" />
              )}
            </div>
            <div className="flex items-center justify-between">
              <span>Training Completed</span>
              {partner.training_completed ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-400" />
              )}
            </div>
            {partner.kyc_verified_at && (
              <div className="text-sm text-muted-foreground">
                Verified on: {formatDateTime(partner.kyc_verified_at)}
              </div>
            )}
            {partner.kyc_rejection_reason && (
              <div className="p-3 bg-red-50 rounded-md">
                <div className="flex items-center gap-2 text-red-800">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="font-medium">Rejection Reason</span>
                </div>
                <p className="text-sm text-red-700 mt-1">{partner.kyc_rejection_reason}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tabs for Commissions, Payouts */}
      <Card>
        <Tabs defaultValue="commissions">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Activity</CardTitle>
              <TabsList>
                <TabsTrigger value="commissions">Commissions</TabsTrigger>
                <TabsTrigger value="payouts">Payouts</TabsTrigger>
              </TabsList>
            </div>
          </CardHeader>
          <CardContent>
            <TabsContent value="commissions" className="mt-0">
              {commissions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-8 w-8 mx-auto mb-2" />
                  No commissions yet
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Order</TableHead>
                      <TableHead className="text-right">Order Amount</TableHead>
                      <TableHead className="text-right">Rate</TableHead>
                      <TableHead className="text-right">Commission</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {commissions.map((commission: PartnerCommission) => (
                      <TableRow key={commission.id}>
                        <TableCell className="font-mono text-sm">
                          {commission.order_id.slice(0, 8)}...
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(commission.order_amount)}
                        </TableCell>
                        <TableCell className="text-right">{commission.commission_rate}%</TableCell>
                        <TableCell className="text-right font-medium text-green-600">
                          {formatCurrency(commission.commission_amount)}
                        </TableCell>
                        <TableCell>
                          <Badge className={commissionStatusColors[commission.status] || 'bg-gray-100'}>
                            {commission.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{formatDate(commission.created_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
              {commissions.length > 0 && (
                <div className="mt-4 text-center">
                  <Button variant="link" asChild>
                    <Link href={`/dashboard/partners/commissions?partner_id=${partnerId}`}>
                      View All Commissions
                    </Link>
                  </Button>
                </div>
              )}
            </TabsContent>

            <TabsContent value="payouts" className="mt-0">
              {payouts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Wallet className="h-8 w-8 mx-auto mb-2" />
                  No payouts yet
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Reference</TableHead>
                      <TableHead>Requested</TableHead>
                      <TableHead>Processed</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {payouts.map((payout: PartnerPayout) => (
                      <TableRow key={payout.id}>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(payout.amount)}
                        </TableCell>
                        <TableCell>
                          <Badge className={payoutStatusColors[payout.status] || 'bg-gray-100'}>
                            {payout.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {payout.bank_reference || '-'}
                        </TableCell>
                        <TableCell>{formatDate(payout.requested_at)}</TableCell>
                        <TableCell>{formatDate(payout.processed_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
              {payouts.length > 0 && (
                <div className="mt-4 text-center">
                  <Button variant="link" asChild>
                    <Link href={`/dashboard/partners/payouts?partner_id=${partnerId}`}>
                      View All Payouts
                    </Link>
                  </Button>
                </div>
              )}
            </TabsContent>
          </CardContent>
        </Tabs>
      </Card>

      {/* KYC Verification Dialog */}
      <Dialog open={isKycDialogOpen} onOpenChange={setIsKycDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Verify KYC</DialogTitle>
            <DialogDescription>
              Review and verify the KYC documents for {partner.full_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Action</Label>
              <Select
                value={kycAction}
                onValueChange={(value: 'VERIFIED' | 'REJECTED') => setKycAction(value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="VERIFIED">Approve KYC</SelectItem>
                  <SelectItem value="REJECTED">Reject KYC</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Notes {kycAction === 'REJECTED' && '(Required for rejection)'}</Label>
              <Textarea
                placeholder={kycAction === 'REJECTED' ? 'Enter rejection reason...' : 'Optional notes...'}
                value={kycNotes}
                onChange={(e) => setKycNotes(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsKycDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => verifyKycMutation.mutate({ status: kycAction, notes: kycNotes })}
              disabled={verifyKycMutation.isPending || (kycAction === 'REJECTED' && !kycNotes)}
              variant={kycAction === 'REJECTED' ? 'destructive' : 'default'}
            >
              {verifyKycMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : null}
              {kycAction === 'VERIFIED' ? 'Approve' : 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Suspend Dialog */}
      <Dialog open={isSuspendDialogOpen} onOpenChange={setIsSuspendDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Suspend Partner</DialogTitle>
            <DialogDescription>
              This will suspend {partner.full_name}&apos;s account and prevent them from earning commissions.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Reason for Suspension</Label>
              <Textarea
                placeholder="Enter reason for suspension..."
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsSuspendDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => suspendMutation.mutate(suspendReason)}
              disabled={suspendMutation.isPending || !suspendReason}
            >
              {suspendMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : null}
              Suspend Partner
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
