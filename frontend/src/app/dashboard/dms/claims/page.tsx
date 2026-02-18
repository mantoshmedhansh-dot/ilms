'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileOutput,
  Plus,
  Search,
  RefreshCw,
  IndianRupee,
  AlertCircle,
  Loader2,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  XCircle,
  Clock,
} from 'lucide-react';
import { toast } from 'sonner';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
import { dmsApi, dealersApi } from '@/lib/api';
import { DealerClaim, DealerClaimListResponse, Dealer } from '@/types';

function formatCurrency(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 10000000) return `\u20B9${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `\u20B9${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `\u20B9${(num / 1000).toFixed(1)}K`;
  return `\u20B9${num.toFixed(0)}`;
}

function getClaimStatusColor(status: string): string {
  const colors: Record<string, string> = {
    SUBMITTED: 'bg-blue-100 text-blue-800',
    UNDER_REVIEW: 'bg-yellow-100 text-yellow-800',
    APPROVED: 'bg-green-100 text-green-800',
    PARTIALLY_APPROVED: 'bg-teal-100 text-teal-800',
    REJECTED: 'bg-red-100 text-red-800',
    SETTLED: 'bg-purple-100 text-purple-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

const CLAIM_TYPES = [
  { value: 'PRODUCT_DEFECT', label: 'Product Defect' },
  { value: 'TRANSIT_DAMAGE', label: 'Transit Damage' },
  { value: 'QUANTITY_SHORT', label: 'Quantity Short' },
  { value: 'PRICING_ERROR', label: 'Pricing Error' },
  { value: 'SCHEME_DISPUTE', label: 'Scheme Dispute' },
  { value: 'WARRANTY', label: 'Warranty' },
];

const CLAIM_STATUSES = [
  { value: 'SUBMITTED', label: 'Submitted' },
  { value: 'UNDER_REVIEW', label: 'Under Review' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'PARTIALLY_APPROVED', label: 'Partially Approved' },
  { value: 'REJECTED', label: 'Rejected' },
  { value: 'SETTLED', label: 'Settled' },
];

const RESOLUTION_TYPES = [
  { value: 'REPLACEMENT', label: 'Replacement' },
  { value: 'CREDIT_NOTE', label: 'Credit Note' },
  { value: 'REFUND', label: 'Refund' },
  { value: 'REPAIR', label: 'Repair' },
];

export default function DMSClaimsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dealerFilter, setDealerFilter] = useState<string>('all');
  const [claimTypeFilter, setClaimTypeFilter] = useState<string>('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showReviewDialog, setShowReviewDialog] = useState(false);
  const [selectedClaim, setSelectedClaim] = useState<DealerClaim | null>(null);

  // Create claim form state
  const [createDealerId, setCreateDealerId] = useState('');
  const [createClaimType, setCreateClaimType] = useState('');
  const [createAmountClaimed, setCreateAmountClaimed] = useState('');
  const [createItems, setCreateItems] = useState('');
  const [createRemarks, setCreateRemarks] = useState('');

  // Review claim form state
  const [reviewStatus, setReviewStatus] = useState('');
  const [reviewAmountApproved, setReviewAmountApproved] = useState('');
  const [reviewResolution, setReviewResolution] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');

  const { data: claimsData, isLoading, refetch, isFetching } = useQuery<DealerClaimListResponse>({
    queryKey: ['dms-claims', page, statusFilter, dealerFilter, claimTypeFilter],
    queryFn: () => dmsApi.listClaims({
      page,
      size: 20,
      status: statusFilter !== 'all' ? statusFilter : undefined,
      dealer_id: dealerFilter !== 'all' ? dealerFilter : undefined,
      claim_type: claimTypeFilter !== 'all' ? claimTypeFilter : undefined,
    }),
    staleTime: 2 * 60 * 1000,
  });

  const { data: dealersData } = useQuery({
    queryKey: ['dealers-dropdown'],
    queryFn: () => dealersApi.list({ size: 100 }),
    staleTime: 10 * 60 * 1000,
  });

  const createClaimMutation = useMutation({
    mutationFn: (data: {
      dealer_id: string;
      claim_type: string;
      amount_claimed: number;
      items?: Array<{ product_id: string; product_name: string; quantity: number; issue_description: string }>;
      remarks?: string;
    }) => dmsApi.createClaim(data),
    onSuccess: () => {
      toast.success('Claim created successfully');
      queryClient.invalidateQueries({ queryKey: ['dms-claims'] });
      resetCreateForm();
      setShowCreateDialog(false);
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to create claim');
    },
  });

  const reviewClaimMutation = useMutation({
    mutationFn: (data: { claimId: string; review: { status: string; amount_approved?: number; resolution?: string; resolution_notes?: string } }) =>
      dmsApi.reviewClaim(data.claimId, data.review),
    onSuccess: () => {
      toast.success('Claim reviewed successfully');
      queryClient.invalidateQueries({ queryKey: ['dms-claims'] });
      setShowReviewDialog(false);
      setSelectedClaim(null);
      resetReviewForm();
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to review claim');
    },
  });

  const resetCreateForm = () => {
    setCreateDealerId('');
    setCreateClaimType('');
    setCreateAmountClaimed('');
    setCreateItems('');
    setCreateRemarks('');
  };

  const resetReviewForm = () => {
    setReviewStatus('');
    setReviewAmountApproved('');
    setReviewResolution('');
    setReviewNotes('');
  };

  const handleCreateClaim = () => {
    if (!createDealerId) { toast.error('Select a dealer'); return; }
    if (!createClaimType) { toast.error('Select a claim type'); return; }
    if (!createAmountClaimed || Number(createAmountClaimed) <= 0) { toast.error('Enter a valid amount'); return; }

    let parsedItems;
    if (createItems.trim()) {
      try {
        parsedItems = JSON.parse(createItems);
      } catch {
        toast.error('Items must be valid JSON array');
        return;
      }
    }

    createClaimMutation.mutate({
      dealer_id: createDealerId,
      claim_type: createClaimType,
      amount_claimed: Number(createAmountClaimed),
      items: parsedItems,
      remarks: createRemarks || undefined,
    });
  };

  const handleOpenReview = (claim: DealerClaim) => {
    setSelectedClaim(claim);
    setReviewAmountApproved(String(claim.amount_approved || ''));
    setReviewResolution(claim.resolution || '');
    setReviewNotes(claim.resolution_notes || '');
    setReviewStatus('');
    setShowReviewDialog(true);
  };

  const handleSubmitReview = () => {
    if (!selectedClaim) return;
    if (!reviewStatus) { toast.error('Select a review status'); return; }

    reviewClaimMutation.mutate({
      claimId: selectedClaim.id,
      review: {
        status: reviewStatus,
        amount_approved: reviewAmountApproved ? Number(reviewAmountApproved) : undefined,
        resolution: reviewResolution || undefined,
        resolution_notes: reviewNotes || undefined,
      },
    });
  };

  const claims = claimsData?.items || [];
  const totalClaims = claimsData?.total || 0;
  const totalPages = Math.ceil(totalClaims / 20);
  const dealers = (dealersData?.items || []) as Dealer[];

  // Compute KPIs from current page data
  const pendingCount = claims.filter(c => ['SUBMITTED', 'UNDER_REVIEW'].includes(c.status)).length;
  const approvedCount = claims.filter(c => ['APPROVED', 'PARTIALLY_APPROVED'].includes(c.status)).length;
  const settledCount = claims.filter(c => c.status === 'SETTLED').length;

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-100 rounded-lg">
            <FileOutput className="h-6 w-6 text-orange-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Claims Management</h1>
            <p className="text-muted-foreground">
              Manage dealer claims, disputes, and resolutions
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Claim
          </Button>
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="icon">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Total Claims</CardTitle>
            <FileOutput className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{totalClaims}</div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-yellow-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Pending</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{pendingCount}</div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-green-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Approved</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{approvedCount}</div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-purple-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Settled</CardTitle>
            <IndianRupee className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{settledCount}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Bar */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="min-w-[180px]">
              <Label className="text-xs text-muted-foreground mb-1 block">Dealer</Label>
              <Select value={dealerFilter} onValueChange={(v) => { setDealerFilter(v); setPage(1); }}>
                <SelectTrigger>
                  <SelectValue placeholder="All Dealers" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Dealers</SelectItem>
                  {dealers.map(d => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.dealer_code || d.code} - {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[160px]">
              <Label className="text-xs text-muted-foreground mb-1 block">Status</Label>
              <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
                <SelectTrigger>
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  {CLAIM_STATUSES.map(s => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[160px]">
              <Label className="text-xs text-muted-foreground mb-1 block">Claim Type</Label>
              <Select value={claimTypeFilter} onValueChange={(v) => { setClaimTypeFilter(v); setPage(1); }}>
                <SelectTrigger>
                  <SelectValue placeholder="All Types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  {CLAIM_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Claims Table */}
      <Card>
        <CardContent className="pt-4">
          {claims.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-3 font-medium text-muted-foreground">Claim #</th>
                      <th className="pb-3 font-medium text-muted-foreground">Dealer</th>
                      <th className="pb-3 font-medium text-muted-foreground">Type</th>
                      <th className="pb-3 font-medium text-muted-foreground text-right">Amount Claimed</th>
                      <th className="pb-3 font-medium text-muted-foreground text-right">Amount Approved</th>
                      <th className="pb-3 font-medium text-muted-foreground text-center">Status</th>
                      <th className="pb-3 font-medium text-muted-foreground text-right">Date</th>
                      <th className="pb-3 font-medium text-muted-foreground text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {claims.map((claim) => (
                      <tr key={claim.id} className="border-b last:border-0 hover:bg-muted/50">
                        <td className="py-3 font-mono text-xs font-medium">{claim.claim_number}</td>
                        <td className="py-3">
                          <div>
                            <span className="font-medium">{claim.dealer_name}</span>
                            {claim.dealer_code && (
                              <span className="text-xs text-muted-foreground ml-2">{claim.dealer_code}</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3">
                          <span className="text-xs">
                            {CLAIM_TYPES.find(t => t.value === claim.claim_type)?.label || claim.claim_type.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="py-3 text-right tabular-nums font-semibold">
                          {formatCurrency(claim.amount_claimed)}
                        </td>
                        <td className="py-3 text-right tabular-nums">
                          {claim.amount_approved ? formatCurrency(claim.amount_approved) : '-'}
                        </td>
                        <td className="py-3 text-center">
                          <Badge variant="outline" className={`text-[10px] ${getClaimStatusColor(claim.status)}`}>
                            {claim.status.replace(/_/g, ' ')}
                          </Badge>
                        </td>
                        <td className="py-3 text-right text-muted-foreground text-xs">
                          {claim.created_at ? new Date(claim.created_at).toLocaleDateString('en-IN') : ''}
                        </td>
                        <td className="py-3 text-center">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleOpenReview(claim)}
                          >
                            <Search className="h-3 w-3 mr-1" />
                            Review
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {totalPages} ({totalClaims} claims)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <FileOutput className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-muted-foreground">No claims found</p>
              <Button variant="outline" className="mt-3" onClick={() => setShowCreateDialog(true)}>
                <Plus className="h-4 w-4 mr-2" /> Create First Claim
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Claim Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={(open) => { if (!open) { resetCreateForm(); } setShowCreateDialog(open); }}>
        <DialogContent className="sm:max-w-[550px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileOutput className="h-5 w-5 text-orange-600" />
              New Claim
            </DialogTitle>
            <DialogDescription>
              Submit a new dealer claim for review and resolution.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label>Dealer *</Label>
              <Select value={createDealerId} onValueChange={setCreateDealerId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a dealer..." />
                </SelectTrigger>
                <SelectContent>
                  {dealers.filter(d => d.status === 'ACTIVE').map(d => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.dealer_code || d.code} - {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Claim Type *</Label>
              <Select value={createClaimType} onValueChange={setCreateClaimType}>
                <SelectTrigger>
                  <SelectValue placeholder="Select claim type..." />
                </SelectTrigger>
                <SelectContent>
                  {CLAIM_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Amount Claimed (INR) *</Label>
              <Input
                type="number"
                placeholder="Enter amount"
                value={createAmountClaimed}
                onChange={e => setCreateAmountClaimed(e.target.value)}
                min={0}
                step="0.01"
              />
            </div>

            <div>
              <Label>Items (JSON array, optional)</Label>
              <Textarea
                placeholder={'[\n  { "product_id": "...", "product_name": "...", "quantity": 1, "issue_description": "..." }\n]'}
                value={createItems}
                onChange={e => setCreateItems(e.target.value)}
                rows={4}
                className="font-mono text-xs"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Each item: product_id, product_name, quantity, issue_description
              </p>
            </div>

            <div>
              <Label>Remarks (optional)</Label>
              <Textarea
                placeholder="Additional remarks or context..."
                value={createRemarks}
                onChange={e => setCreateRemarks(e.target.value)}
                rows={2}
              />
            </div>

            {createDealerId && createClaimType && (
              <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-md">
                <AlertCircle className="h-4 w-4 text-blue-600 mt-0.5" />
                <p className="text-xs text-blue-700">
                  The claim will be submitted for review. Attach evidence and item details for faster processing.
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => { resetCreateForm(); setShowCreateDialog(false); }}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateClaim}
              disabled={createClaimMutation.isPending || !createDealerId || !createClaimType || !createAmountClaimed}
            >
              {createClaimMutation.isPending ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Submitting...</>
              ) : (
                <><FileOutput className="h-4 w-4 mr-2" /> Submit Claim</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Review Claim Dialog */}
      <Dialog open={showReviewDialog} onOpenChange={(open) => { if (!open) { setSelectedClaim(null); resetReviewForm(); } setShowReviewDialog(open); }}>
        <DialogContent className="sm:max-w-[550px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Search className="h-5 w-5 text-indigo-600" />
              Review Claim
            </DialogTitle>
            <DialogDescription>
              {selectedClaim ? `Claim ${selectedClaim.claim_number} by ${selectedClaim.dealer_name}` : 'Review and resolve the dealer claim.'}
            </DialogDescription>
          </DialogHeader>

          {selectedClaim && (
            <div className="space-y-4">
              {/* Claim Summary */}
              <div className="grid grid-cols-2 gap-3 p-3 bg-muted/50 rounded-md text-sm">
                <div>
                  <span className="text-muted-foreground text-xs">Type</span>
                  <p className="font-medium">
                    {CLAIM_TYPES.find(t => t.value === selectedClaim.claim_type)?.label || selectedClaim.claim_type}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Amount Claimed</span>
                  <p className="font-semibold">{formatCurrency(selectedClaim.amount_claimed)}</p>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Current Status</span>
                  <Badge variant="outline" className={`text-[10px] mt-1 ${getClaimStatusColor(selectedClaim.status)}`}>
                    {selectedClaim.status.replace(/_/g, ' ')}
                  </Badge>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Submitted</span>
                  <p className="text-xs">{selectedClaim.submitted_at ? new Date(selectedClaim.submitted_at).toLocaleDateString('en-IN') : selectedClaim.created_at ? new Date(selectedClaim.created_at).toLocaleDateString('en-IN') : '-'}</p>
                </div>
                {selectedClaim.remarks && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground text-xs">Remarks</span>
                    <p className="text-xs">{selectedClaim.remarks}</p>
                  </div>
                )}
              </div>

              {/* Review Fields */}
              <div>
                <Label>Review Decision *</Label>
                <Select value={reviewStatus} onValueChange={setReviewStatus}>
                  <SelectTrigger>
                    <SelectValue placeholder="Approve or Reject..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="APPROVED">
                      <span className="flex items-center gap-1">
                        <CheckCircle className="h-3 w-3 text-green-600" /> Approve
                      </span>
                    </SelectItem>
                    <SelectItem value="PARTIALLY_APPROVED">
                      <span className="flex items-center gap-1">
                        <CheckCircle className="h-3 w-3 text-teal-600" /> Partially Approve
                      </span>
                    </SelectItem>
                    <SelectItem value="REJECTED">
                      <span className="flex items-center gap-1">
                        <XCircle className="h-3 w-3 text-red-600" /> Reject
                      </span>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Amount Approved (INR)</Label>
                <Input
                  type="number"
                  placeholder="Enter approved amount"
                  value={reviewAmountApproved}
                  onChange={e => setReviewAmountApproved(e.target.value)}
                  min={0}
                  step="0.01"
                />
              </div>

              <div>
                <Label>Resolution Type</Label>
                <Select value={reviewResolution} onValueChange={setReviewResolution}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select resolution..." />
                  </SelectTrigger>
                  <SelectContent>
                    {RESOLUTION_TYPES.map(r => (
                      <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Resolution Notes</Label>
                <Textarea
                  placeholder="Notes about the review decision..."
                  value={reviewNotes}
                  onChange={e => setReviewNotes(e.target.value)}
                  rows={3}
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => { setSelectedClaim(null); resetReviewForm(); setShowReviewDialog(false); }}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmitReview}
              disabled={reviewClaimMutation.isPending || !reviewStatus}
            >
              {reviewClaimMutation.isPending ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Submitting...</>
              ) : (
                <><CheckCircle className="h-4 w-4 mr-2" /> Submit Review</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
