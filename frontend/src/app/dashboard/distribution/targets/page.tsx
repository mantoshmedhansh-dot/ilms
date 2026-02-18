'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Target,
  Plus,
  RefreshCw,
  IndianRupee,
  TrendingUp,
  Package,
  Trophy,
  Loader2,
  CheckCircle,
  XCircle,
} from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
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
import { dealersApi } from '@/lib/api';
import { Dealer } from '@/types';

// DealerTarget is not exported from types, define locally
interface DealerTarget {
  id: string;
  dealer_id: string;
  target_period: string;
  target_year: number;
  target_month?: number;
  target_quarter?: number;
  revenue_target: number;
  quantity_target: number;
  revenue_achieved: number;
  quantity_achieved: number;
  revenue_achievement_percentage: number;
  quantity_achievement_percentage: number;
  incentive_earned: number;
  is_incentive_paid: boolean;
  created_at: string;
}

function formatCurrency(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 10000000) return `\u20B9${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `\u20B9${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `\u20B9${(num / 1000).toFixed(1)}K`;
  return `\u20B9${num.toFixed(0)}`;
}

function getAchievementColor(percentage: number): string {
  if (percentage >= 80) return 'bg-green-500';
  if (percentage >= 50) return 'bg-yellow-500';
  return 'bg-red-500';
}

function getAchievementTextColor(percentage: number): string {
  if (percentage >= 80) return 'text-green-700';
  if (percentage >= 50) return 'text-yellow-700';
  return 'text-red-700';
}

function formatPeriodLabel(target: DealerTarget): string {
  const period = target.target_period;
  const year = target.target_year;
  if (period === 'MONTHLY' && target.target_month) {
    const monthName = new Date(year, target.target_month - 1).toLocaleString('en-IN', { month: 'short' });
    return `${period} - ${monthName} ${year}`;
  }
  if (period === 'QUARTERLY' && target.target_quarter) {
    return `${period} - Q${target.target_quarter} ${year}`;
  }
  return `${period} - ${year}`;
}

const MONTHS = [
  { value: '1', label: 'January' },
  { value: '2', label: 'February' },
  { value: '3', label: 'March' },
  { value: '4', label: 'April' },
  { value: '5', label: 'May' },
  { value: '6', label: 'June' },
  { value: '7', label: 'July' },
  { value: '8', label: 'August' },
  { value: '9', label: 'September' },
  { value: '10', label: 'October' },
  { value: '11', label: 'November' },
  { value: '12', label: 'December' },
];

const QUARTERS = [
  { value: '1', label: 'Q1 (Jan - Mar)' },
  { value: '2', label: 'Q2 (Apr - Jun)' },
  { value: '3', label: 'Q3 (Jul - Sep)' },
  { value: '4', label: 'Q4 (Oct - Dec)' },
];

export default function DistributionTargetsPage() {
  const queryClient = useQueryClient();
  const [selectedDealerId, setSelectedDealerId] = useState<string>('');
  const [yearFilter, setYearFilter] = useState<number>(2026);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  // Create target form state
  const [formPeriod, setFormPeriod] = useState<string>('');
  const [formYear, setFormYear] = useState<string>('2026');
  const [formMonth, setFormMonth] = useState<string>('');
  const [formQuarter, setFormQuarter] = useState<string>('');
  const [formTargetType, setFormTargetType] = useState<string>('');
  const [formRevenueTarget, setFormRevenueTarget] = useState<string>('');
  const [formQuantityTarget, setFormQuantityTarget] = useState<string>('');
  const [formIncentivePercentage, setFormIncentivePercentage] = useState<string>('');

  // Fetch dealers for dropdown
  const { data: dealersData } = useQuery({
    queryKey: ['dealers-dropdown'],
    queryFn: () => dealersApi.list({ size: 100 }),
    staleTime: 10 * 60 * 1000,
  });

  // Fetch targets for selected dealer
  const {
    data: targets,
    isLoading: targetsLoading,
    refetch,
    isFetching,
  } = useQuery<DealerTarget[]>({
    queryKey: ['dealer-targets', selectedDealerId, yearFilter],
    queryFn: () => dealersApi.getTargets(selectedDealerId, { year: yearFilter }),
    enabled: !!selectedDealerId,
    staleTime: 2 * 60 * 1000,
  });

  // Create target mutation
  const createTargetMutation = useMutation({
    mutationFn: (data: {
      target_period: string;
      target_year: number;
      target_month?: number;
      target_quarter?: number;
      target_type: string;
      revenue_target: number;
      quantity_target: number;
      incentive_percentage?: number;
    }) => dealersApi.createTarget(selectedDealerId, data),
    onSuccess: () => {
      toast.success('Target created successfully');
      queryClient.invalidateQueries({ queryKey: ['dealer-targets'] });
      resetCreateForm();
      setShowCreateDialog(false);
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to create target');
    },
  });

  const dealers = (dealersData?.items || []) as Dealer[];
  const targetsList = targets || [];

  // KPI computations
  const totalRevenueTarget = targetsList.reduce((sum, t) => sum + (t.revenue_target || 0), 0);
  const totalRevenueAchieved = targetsList.reduce((sum, t) => sum + (t.revenue_achieved || 0), 0);
  const totalQuantityTarget = targetsList.reduce((sum, t) => sum + (t.quantity_target || 0), 0);
  const totalIncentiveEarned = targetsList.reduce((sum, t) => sum + (t.incentive_earned || 0), 0);

  const resetCreateForm = () => {
    setFormPeriod('');
    setFormYear('2026');
    setFormMonth('');
    setFormQuarter('');
    setFormTargetType('');
    setFormRevenueTarget('');
    setFormQuantityTarget('');
    setFormIncentivePercentage('');
  };

  const handleCreateTarget = () => {
    if (!selectedDealerId) {
      toast.error('Select a dealer first');
      return;
    }
    if (!formPeriod) {
      toast.error('Select a target period');
      return;
    }
    if (!formYear || Number(formYear) < 2020) {
      toast.error('Enter a valid year');
      return;
    }
    if (formPeriod === 'MONTHLY' && !formMonth) {
      toast.error('Select a month');
      return;
    }
    if (formPeriod === 'QUARTERLY' && !formQuarter) {
      toast.error('Select a quarter');
      return;
    }
    if (!formTargetType) {
      toast.error('Select a target type');
      return;
    }

    const revenueTarget = Number(formRevenueTarget) || 0;
    const quantityTarget = Number(formQuantityTarget) || 0;

    if (formTargetType === 'REVENUE' && revenueTarget <= 0) {
      toast.error('Enter a valid revenue target');
      return;
    }
    if (formTargetType === 'QUANTITY' && quantityTarget <= 0) {
      toast.error('Enter a valid quantity target');
      return;
    }
    if (formTargetType === 'BOTH' && revenueTarget <= 0 && quantityTarget <= 0) {
      toast.error('Enter at least one target value');
      return;
    }

    createTargetMutation.mutate({
      target_period: formPeriod,
      target_year: Number(formYear),
      target_month: formPeriod === 'MONTHLY' ? Number(formMonth) : undefined,
      target_quarter: formPeriod === 'QUARTERLY' ? Number(formQuarter) : undefined,
      target_type: formTargetType,
      revenue_target: revenueTarget,
      quantity_target: quantityTarget,
      incentive_percentage: formIncentivePercentage ? Number(formIncentivePercentage) : undefined,
    });
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-100 rounded-lg">
            <Target className="h-6 w-6 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Sales Targets</h1>
            <p className="text-muted-foreground">
              Set and track dealer sales targets and incentive achievement
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => setShowCreateDialog(true)}
            disabled={!selectedDealerId}
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Target
          </Button>
          <Button
            onClick={() => refetch()}
            disabled={isFetching || !selectedDealerId}
            variant="outline"
            size="icon"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Dealer Selector & Year Filter */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="min-w-[280px]">
              <Label className="text-xs text-muted-foreground mb-1 block">Dealer</Label>
              <Select
                value={selectedDealerId}
                onValueChange={(v) => setSelectedDealerId(v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a dealer..." />
                </SelectTrigger>
                <SelectContent>
                  {dealers.map((d) => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.dealer_code || d.code} - {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[120px]">
              <Label className="text-xs text-muted-foreground mb-1 block">Year</Label>
              <Select
                value={String(yearFilter)}
                onValueChange={(v) => setYearFilter(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Year" />
                </SelectTrigger>
                <SelectContent>
                  {[2024, 2025, 2026, 2027].map((y) => (
                    <SelectItem key={y} value={String(y)}>
                      {y}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Empty state when no dealer selected */}
      {!selectedDealerId && (
        <Card>
          <CardContent className="py-16">
            <div className="text-center">
              <Target className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-muted-foreground text-lg font-medium">
                Select a dealer to view and manage targets
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Choose a dealer from the dropdown above to get started
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading state */}
      {selectedDealerId && targetsLoading && (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
          <Skeleton className="h-96" />
        </div>
      )}

      {/* KPI Cards - shown when dealer selected and targets loaded */}
      {selectedDealerId && !targetsLoading && (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="border-l-4 border-l-blue-500">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Revenue Target
                </CardTitle>
                <div className="p-1.5 bg-blue-50 rounded-md">
                  <IndianRupee className="h-3.5 w-3.5 text-blue-600" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">
                  {formatCurrency(totalRevenueTarget)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Across {targetsList.length} target{targetsList.length !== 1 ? 's' : ''}
                </p>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-green-500">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Revenue Achieved
                </CardTitle>
                <div className="p-1.5 bg-green-50 rounded-md">
                  <TrendingUp className="h-3.5 w-3.5 text-green-600" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums text-green-600">
                  {formatCurrency(totalRevenueAchieved)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {totalRevenueTarget > 0
                    ? `${((totalRevenueAchieved / totalRevenueTarget) * 100).toFixed(0)}% of target`
                    : 'No target set'}
                </p>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-indigo-500">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Quantity Target
                </CardTitle>
                <div className="p-1.5 bg-indigo-50 rounded-md">
                  <Package className="h-3.5 w-3.5 text-indigo-600" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">
                  {totalQuantityTarget.toLocaleString('en-IN')}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Units targeted
                </p>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-amber-500">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Incentive Earned
                </CardTitle>
                <div className="p-1.5 bg-amber-50 rounded-md">
                  <Trophy className="h-3.5 w-3.5 text-amber-600" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums text-amber-600">
                  {formatCurrency(totalIncentiveEarned)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Total incentive earned
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Targets Table */}
          <Card>
            <CardContent className="pt-4">
              {targetsList.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="pb-3 font-medium text-muted-foreground">Period</th>
                        <th className="pb-3 font-medium text-muted-foreground text-right">Revenue Target</th>
                        <th className="pb-3 font-medium text-muted-foreground text-right">Revenue Achieved</th>
                        <th className="pb-3 font-medium text-muted-foreground text-center min-w-[160px]">Revenue %</th>
                        <th className="pb-3 font-medium text-muted-foreground text-right">Qty Target</th>
                        <th className="pb-3 font-medium text-muted-foreground text-right">Qty Achieved</th>
                        <th className="pb-3 font-medium text-muted-foreground text-center min-w-[120px]">Qty %</th>
                        <th className="pb-3 font-medium text-muted-foreground text-right">Incentive Earned</th>
                        <th className="pb-3 font-medium text-muted-foreground text-center">Paid</th>
                      </tr>
                    </thead>
                    <tbody>
                      {targetsList.map((target) => {
                        const revPct = target.revenue_achievement_percentage || 0;
                        const qtyPct = target.quantity_achievement_percentage || 0;

                        return (
                          <tr key={target.id} className="border-b last:border-0 hover:bg-muted/50">
                            <td className="py-3">
                              <div>
                                <Badge
                                  variant="outline"
                                  className="text-[10px] mr-2"
                                >
                                  {target.target_period}
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  {formatPeriodLabel(target).replace(`${target.target_period} - `, '')}
                                </span>
                              </div>
                            </td>
                            <td className="py-3 text-right tabular-nums font-semibold">
                              {formatCurrency(target.revenue_target)}
                            </td>
                            <td className="py-3 text-right tabular-nums">
                              {formatCurrency(target.revenue_achieved)}
                            </td>
                            <td className="py-3">
                              <div className="flex items-center gap-2 justify-center">
                                <Progress
                                  value={Math.min(revPct, 100)}
                                  className="h-2 w-20"
                                  indicatorClassName={getAchievementColor(revPct)}
                                />
                                <span className={`text-xs font-semibold tabular-nums ${getAchievementTextColor(revPct)}`}>
                                  {revPct.toFixed(1)}%
                                </span>
                              </div>
                            </td>
                            <td className="py-3 text-right tabular-nums font-semibold">
                              {target.quantity_target.toLocaleString('en-IN')}
                            </td>
                            <td className="py-3 text-right tabular-nums">
                              {target.quantity_achieved.toLocaleString('en-IN')}
                            </td>
                            <td className="py-3">
                              <div className="flex items-center gap-2 justify-center">
                                <Progress
                                  value={Math.min(qtyPct, 100)}
                                  className="h-2 w-16"
                                  indicatorClassName={getAchievementColor(qtyPct)}
                                />
                                <span className={`text-xs font-semibold tabular-nums ${getAchievementTextColor(qtyPct)}`}>
                                  {qtyPct.toFixed(1)}%
                                </span>
                              </div>
                            </td>
                            <td className="py-3 text-right tabular-nums font-medium">
                              {formatCurrency(target.incentive_earned)}
                            </td>
                            <td className="py-3 text-center">
                              {target.is_incentive_paid ? (
                                <Badge className="bg-green-100 text-green-800 hover:bg-green-100 text-[10px]">
                                  <CheckCircle className="h-3 w-3 mr-1" />
                                  Paid
                                </Badge>
                              ) : (
                                <Badge className="bg-red-100 text-red-800 hover:bg-red-100 text-[10px]">
                                  <XCircle className="h-3 w-3 mr-1" />
                                  Unpaid
                                </Badge>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12">
                  <Target className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
                  <p className="text-muted-foreground">No targets found for {yearFilter}</p>
                  <Button
                    variant="outline"
                    className="mt-3"
                    onClick={() => setShowCreateDialog(true)}
                  >
                    <Plus className="h-4 w-4 mr-2" /> Add First Target
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Create Target Dialog */}
      <Dialog
        open={showCreateDialog}
        onOpenChange={(open) => {
          if (!open) {
            resetCreateForm();
          }
          setShowCreateDialog(open);
        }}
      >
        <DialogContent className="sm:max-w-[550px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-emerald-600" />
              Add Target
            </DialogTitle>
            <DialogDescription>
              Set a new sales target for the selected dealer.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Target Period */}
            <div>
              <Label>Target Period *</Label>
              <Select value={formPeriod} onValueChange={setFormPeriod}>
                <SelectTrigger>
                  <SelectValue placeholder="Select period..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MONTHLY">Monthly</SelectItem>
                  <SelectItem value="QUARTERLY">Quarterly</SelectItem>
                  <SelectItem value="YEARLY">Yearly</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Target Year */}
            <div>
              <Label>Target Year *</Label>
              <Input
                type="number"
                placeholder="e.g. 2026"
                value={formYear}
                onChange={(e) => setFormYear(e.target.value)}
                min={2020}
                max={2030}
              />
            </div>

            {/* Target Month - shown only if MONTHLY */}
            {formPeriod === 'MONTHLY' && (
              <div>
                <Label>Month *</Label>
                <Select value={formMonth} onValueChange={setFormMonth}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select month..." />
                  </SelectTrigger>
                  <SelectContent>
                    {MONTHS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Target Quarter - shown only if QUARTERLY */}
            {formPeriod === 'QUARTERLY' && (
              <div>
                <Label>Quarter *</Label>
                <Select value={formQuarter} onValueChange={setFormQuarter}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select quarter..." />
                  </SelectTrigger>
                  <SelectContent>
                    {QUARTERS.map((q) => (
                      <SelectItem key={q.value} value={q.value}>
                        {q.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Target Type */}
            <div>
              <Label>Target Type *</Label>
              <Select value={formTargetType} onValueChange={setFormTargetType}>
                <SelectTrigger>
                  <SelectValue placeholder="Select type..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="REVENUE">Revenue</SelectItem>
                  <SelectItem value="QUANTITY">Quantity</SelectItem>
                  <SelectItem value="BOTH">Both</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Revenue Target */}
            {(formTargetType === 'REVENUE' || formTargetType === 'BOTH') && (
              <div>
                <Label>Revenue Target (INR) *</Label>
                <Input
                  type="number"
                  placeholder="e.g. 500000"
                  value={formRevenueTarget}
                  onChange={(e) => setFormRevenueTarget(e.target.value)}
                  min={0}
                  step={1000}
                />
              </div>
            )}

            {/* Quantity Target */}
            {(formTargetType === 'QUANTITY' || formTargetType === 'BOTH') && (
              <div>
                <Label>Quantity Target (Units) *</Label>
                <Input
                  type="number"
                  placeholder="e.g. 1000"
                  value={formQuantityTarget}
                  onChange={(e) => setFormQuantityTarget(e.target.value)}
                  min={0}
                  step={1}
                />
              </div>
            )}

            {/* Incentive Percentage */}
            <div>
              <Label>Incentive Percentage (optional)</Label>
              <Input
                type="number"
                placeholder="e.g. 5"
                value={formIncentivePercentage}
                onChange={(e) => setFormIncentivePercentage(e.target.value)}
                min={0}
                max={100}
                step={0.5}
              />
              <p className="text-xs text-muted-foreground mt-1">
                Percentage of revenue to be awarded as incentive on achievement.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                resetCreateForm();
                setShowCreateDialog(false);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateTarget}
              disabled={createTargetMutation.isPending || !formPeriod || !formTargetType}
            >
              {createTargetMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Creating...
                </>
              ) : (
                <>
                  <Target className="h-4 w-4 mr-2" /> Create Target
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
