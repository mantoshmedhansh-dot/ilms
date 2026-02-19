'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  BadgePercent,
  Plus,
  RefreshCw,
  IndianRupee,
  Calendar,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Edit,
  CheckCircle,
  XCircle,
} from 'lucide-react';

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
import { dmsApi } from '@/lib/api';
import { DealerScheme, DealerSchemeListResponse } from '@/types';

const SCHEME_TYPES = [
  'QUANTITY_DISCOUNT',
  'SLAB_DISCOUNT',
  'CASH_DISCOUNT',
  'EARLY_PAYMENT',
  'FESTIVE_SCHEME',
  'TARGET_INCENTIVE',
  'PRODUCT_COMBO',
  'FOC',
] as const;

function formatCurrency(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 10000000) return `\u20B9${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `\u20B9${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `\u20B9${(num / 1000).toFixed(1)}K`;
  return `\u20B9${num.toFixed(0)}`;
}

function getSchemeTypeColor(type: string): string {
  const colors: Record<string, string> = {
    QUANTITY_DISCOUNT: 'bg-blue-100 text-blue-800',
    SLAB_DISCOUNT: 'bg-indigo-100 text-indigo-800',
    CASH_DISCOUNT: 'bg-emerald-100 text-emerald-800',
    EARLY_PAYMENT: 'bg-teal-100 text-teal-800',
    FESTIVE_SCHEME: 'bg-pink-100 text-pink-800',
    TARGET_INCENTIVE: 'bg-amber-100 text-amber-800',
    PRODUCT_COMBO: 'bg-purple-100 text-purple-800',
    FOC: 'bg-orange-100 text-orange-800',
  };
  return colors[type] || 'bg-gray-100 text-gray-800';
}

function formatSchemeType(type: string): string {
  return type
    .split('_')
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(' ');
}

interface SchemeFormData {
  scheme_code: string;
  scheme_name: string;
  description: string;
  scheme_type: string;
  start_date: string;
  end_date: string;
  rules: string;
  total_budget: string;
  terms_and_conditions: string;
  can_combine: boolean;
}

const EMPTY_FORM: SchemeFormData = {
  scheme_code: '',
  scheme_name: '',
  description: '',
  scheme_type: '',
  start_date: '',
  end_date: '',
  rules: '{}',
  total_budget: '',
  terms_and_conditions: '',
  can_combine: false,
};

export default function DMSSchemesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [showDialog, setShowDialog] = useState(false);
  const [editingScheme, setEditingScheme] = useState<DealerScheme | null>(null);
  const [form, setForm] = useState<SchemeFormData>(EMPTY_FORM);

  // Fetch schemes
  const { data: schemesData, isLoading, refetch, isFetching } = useQuery<DealerSchemeListResponse>({
    queryKey: ['dms-schemes', page],
    queryFn: () => dmsApi.listSchemes({ skip: (page - 1) * 20, limit: 20 }),
    staleTime: 2 * 60 * 1000,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => dmsApi.createScheme(data),
    onSuccess: () => {
      toast.success('Scheme created successfully');
      queryClient.invalidateQueries({ queryKey: ['dms-schemes'] });
      closeDialog();
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to create scheme');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      dmsApi.updateScheme(id, data),
    onSuccess: () => {
      toast.success('Scheme updated successfully');
      queryClient.invalidateQueries({ queryKey: ['dms-schemes'] });
      closeDialog();
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to update scheme');
    },
  });

  const schemes = schemesData?.items || [];
  const totalSchemes = schemesData?.total || 0;
  const totalPages = Math.ceil(totalSchemes / 20);

  // KPI computations
  const activeSchemes = schemes.filter((s) => s.is_active && s.is_valid);
  const totalBudget = schemes.reduce((sum, s) => sum + (Number(s.total_budget) || 0), 0);
  const totalUtilized = schemes.reduce((sum, s) => sum + (Number(s.utilized_budget) || 0), 0);
  const totalRemaining = schemes.reduce((sum, s) => sum + (Number(s.budget_remaining) || 0), 0);

  const closeDialog = () => {
    setShowDialog(false);
    setEditingScheme(null);
    setForm(EMPTY_FORM);
  };

  const openCreateDialog = () => {
    setEditingScheme(null);
    setForm(EMPTY_FORM);
    setShowDialog(true);
  };

  const openEditDialog = (scheme: DealerScheme) => {
    setEditingScheme(scheme);
    setForm({
      scheme_code: scheme.scheme_code || '',
      scheme_name: scheme.scheme_name || '',
      description: scheme.description || '',
      scheme_type: scheme.scheme_type || '',
      start_date: scheme.start_date ? scheme.start_date.split('T')[0] : '',
      end_date: scheme.end_date ? scheme.end_date.split('T')[0] : '',
      rules: scheme.rules ? JSON.stringify(scheme.rules, null, 2) : '{}',
      total_budget: scheme.total_budget != null ? String(scheme.total_budget) : '',
      terms_and_conditions: scheme.terms_and_conditions || '',
      can_combine: scheme.can_combine ?? false,
    });
    setShowDialog(true);
  };

  const handleSubmit = () => {
    if (!editingScheme && !form.scheme_code.trim()) {
      toast.error('Scheme code is required');
      return;
    }
    if (!editingScheme && (form.scheme_code.trim().length < 3 || form.scheme_code.trim().length > 30)) {
      toast.error('Scheme code must be 3-30 characters');
      return;
    }
    if (!form.scheme_name.trim()) {
      toast.error('Scheme name is required');
      return;
    }
    if (!editingScheme && !form.scheme_type) {
      toast.error('Scheme type is required');
      return;
    }
    if (!editingScheme && (!form.start_date || !form.end_date)) {
      toast.error('Start date and end date are required');
      return;
    }

    let parsedRules: Record<string, unknown> = {};
    try {
      parsedRules = JSON.parse(form.rules);
    } catch {
      toast.error('Rules must be valid JSON');
      return;
    }

    if (editingScheme) {
      // DealerSchemeUpdate only accepts: scheme_name, description, end_date, is_active, rules, total_budget, terms_and_conditions
      const updatePayload: Record<string, unknown> = {
        scheme_name: form.scheme_name.trim(),
        description: form.description.trim() || undefined,
        end_date: form.end_date || undefined,
        rules: parsedRules,
        total_budget: form.total_budget ? Number(form.total_budget) : undefined,
        terms_and_conditions: form.terms_and_conditions.trim() || undefined,
      };
      updateMutation.mutate({ id: editingScheme.id, data: updatePayload });
    } else {
      // DealerSchemeCreate requires all DealerSchemeBase fields including scheme_code
      const createPayload: Record<string, unknown> = {
        scheme_code: form.scheme_code.trim(),
        scheme_name: form.scheme_name.trim(),
        description: form.description.trim() || undefined,
        scheme_type: form.scheme_type,
        start_date: form.start_date,
        end_date: form.end_date,
        rules: parsedRules,
        total_budget: form.total_budget ? Number(form.total_budget) : undefined,
        terms_and_conditions: form.terms_and_conditions.trim() || undefined,
        can_combine: form.can_combine,
      };
      createMutation.mutate(createPayload);
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
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
          <div className="p-2 bg-purple-100 rounded-lg">
            <BadgePercent className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Scheme Management</h1>
            <p className="text-muted-foreground">
              Create and manage distributor discount schemes
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={openCreateDialog}>
            <Plus className="h-4 w-4 mr-2" />
            Create Scheme
          </Button>
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="icon">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-l-4 border-l-emerald-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Active Schemes</CardTitle>
            <div className="p-1.5 bg-emerald-50 rounded-md">
              <CheckCircle className="h-3.5 w-3.5 text-emerald-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-emerald-600">
              {activeSchemes.length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              of {schemes.length} on this page
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-indigo-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Total Budget</CardTitle>
            <div className="p-1.5 bg-indigo-50 rounded-md">
              <IndianRupee className="h-3.5 w-3.5 text-indigo-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{formatCurrency(totalBudget)}</div>
            <p className="text-xs text-muted-foreground mt-1">Allocated budget</p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Utilized</CardTitle>
            <div className="p-1.5 bg-amber-50 rounded-md">
              <IndianRupee className="h-3.5 w-3.5 text-amber-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-amber-600">
              {formatCurrency(totalUtilized)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {totalBudget > 0 ? `${((totalUtilized / totalBudget) * 100).toFixed(0)}% of budget` : 'No budget set'}
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-teal-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Budget Remaining</CardTitle>
            <div className="p-1.5 bg-teal-50 rounded-md">
              <IndianRupee className="h-3.5 w-3.5 text-teal-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-teal-600">
              {formatCurrency(totalRemaining)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Available to spend</p>
          </CardContent>
        </Card>
      </div>

      {/* Schemes Table */}
      <Card>
        <CardContent className="pt-4">
          {schemes.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-3 font-medium text-muted-foreground">Code</th>
                      <th className="pb-3 font-medium text-muted-foreground">Name</th>
                      <th className="pb-3 font-medium text-muted-foreground text-center">Type</th>
                      <th className="pb-3 font-medium text-muted-foreground">Validity</th>
                      <th className="pb-3 font-medium text-muted-foreground text-right">Budget</th>
                      <th className="pb-3 font-medium text-muted-foreground text-right">Utilized</th>
                      <th className="pb-3 font-medium text-muted-foreground text-center">Status</th>
                      <th className="pb-3 font-medium text-muted-foreground text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schemes.map((scheme) => {
                      const isActive = scheme.is_active && scheme.is_valid;
                      return (
                        <tr key={scheme.id} className="border-b last:border-0 hover:bg-muted/50">
                          <td className="py-3 font-mono text-xs font-medium">
                            {scheme.scheme_code}
                          </td>
                          <td className="py-3">
                            <div>
                              <span className="font-medium">{scheme.scheme_name}</span>
                              {scheme.description && (
                                <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                  {scheme.description}
                                </p>
                              )}
                            </div>
                          </td>
                          <td className="py-3 text-center">
                            <Badge
                              variant="outline"
                              className={`text-[10px] ${getSchemeTypeColor(scheme.scheme_type)}`}
                            >
                              {formatSchemeType(scheme.scheme_type)}
                            </Badge>
                          </td>
                          <td className="py-3">
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                              <Calendar className="h-3 w-3" />
                              <span>
                                {scheme.start_date
                                  ? new Date(scheme.start_date).toLocaleDateString('en-IN')
                                  : ''}
                                {' - '}
                                {scheme.end_date
                                  ? new Date(scheme.end_date).toLocaleDateString('en-IN')
                                  : ''}
                              </span>
                            </div>
                          </td>
                          <td className="py-3 text-right tabular-nums font-medium">
                            {scheme.total_budget != null
                              ? formatCurrency(scheme.total_budget)
                              : '-'}
                          </td>
                          <td className="py-3 text-right tabular-nums">
                            {formatCurrency(scheme.utilized_budget)}
                          </td>
                          <td className="py-3 text-center">
                            {isActive ? (
                              <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100 text-[10px]">
                                <CheckCircle className="h-3 w-3 mr-1" />
                                Active
                              </Badge>
                            ) : (
                              <Badge className="bg-red-100 text-red-800 hover:bg-red-100 text-[10px]">
                                <XCircle className="h-3 w-3 mr-1" />
                                Expired
                              </Badge>
                            )}
                          </td>
                          <td className="py-3 text-center">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => openEditDialog(scheme)}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {totalPages} ({totalSchemes} schemes)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
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
              <BadgePercent className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-muted-foreground">No schemes found</p>
              <Button variant="outline" className="mt-3" onClick={openCreateDialog}>
                <Plus className="h-4 w-4 mr-2" /> Create First Scheme
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create / Edit Scheme Dialog */}
      <Dialog open={showDialog} onOpenChange={(open) => { if (!open) closeDialog(); else setShowDialog(open); }}>
        <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BadgePercent className="h-5 w-5 text-purple-600" />
              {editingScheme ? 'Edit Scheme' : 'Create Scheme'}
            </DialogTitle>
            <DialogDescription>
              {editingScheme
                ? `Update scheme: ${editingScheme.scheme_code}`
                : 'Define a new discount or incentive scheme for distributors.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Scheme Code (only for creation, not editable after creation) */}
            {!editingScheme && (
              <div>
                <Label htmlFor="scheme_code">Scheme Code *</Label>
                <Input
                  id="scheme_code"
                  placeholder="e.g. SCH-Q1-2026"
                  value={form.scheme_code}
                  onChange={(e) => setForm({ ...form, scheme_code: e.target.value.toUpperCase() })}
                  maxLength={30}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Unique code (3-30 characters). Cannot be changed after creation.
                </p>
              </div>
            )}

            {/* Scheme Name */}
            <div>
              <Label htmlFor="scheme_name">Scheme Name *</Label>
              <Input
                id="scheme_name"
                placeholder="e.g. Q1 Quantity Discount"
                value={form.scheme_name}
                onChange={(e) => setForm({ ...form, scheme_name: e.target.value })}
              />
            </div>

            {/* Description */}
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Brief description of the scheme..."
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={2}
              />
            </div>

            {/* Scheme Type */}
            <div>
              <Label>Scheme Type *</Label>
              <Select
                value={form.scheme_type}
                onValueChange={(v) => setForm({ ...form, scheme_type: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select scheme type..." />
                </SelectTrigger>
                <SelectContent>
                  {SCHEME_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {formatSchemeType(type)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Date Range */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="start_date">Start Date *</Label>
                <Input
                  id="start_date"
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="end_date">End Date *</Label>
                <Input
                  id="end_date"
                  type="date"
                  value={form.end_date}
                  onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                />
              </div>
            </div>

            {/* Total Budget */}
            <div>
              <Label htmlFor="total_budget">Total Budget</Label>
              <Input
                id="total_budget"
                type="number"
                placeholder="e.g. 500000"
                value={form.total_budget}
                onChange={(e) => setForm({ ...form, total_budget: e.target.value })}
                min={0}
                step={1000}
              />
            </div>

            {/* Rules JSON */}
            <div>
              <Label htmlFor="rules">Rules (JSON)</Label>
              <Textarea
                id="rules"
                placeholder='{"min_quantity": 100, "discount_pct": 5}'
                value={form.rules}
                onChange={(e) => setForm({ ...form, rules: e.target.value })}
                rows={4}
                className="font-mono text-xs"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Define scheme rules as a JSON object.
              </p>
            </div>

            {/* Terms & Conditions */}
            <div>
              <Label htmlFor="terms">Terms &amp; Conditions</Label>
              <Textarea
                id="terms"
                placeholder="Applicable terms and conditions..."
                value={form.terms_and_conditions}
                onChange={(e) => setForm({ ...form, terms_and_conditions: e.target.value })}
                rows={3}
              />
            </div>

            {/* Can Combine */}
            <div className="flex items-center gap-3">
              <input
                id="can_combine"
                type="checkbox"
                checked={form.can_combine}
                onChange={(e) => setForm({ ...form, can_combine: e.target.checked })}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <Label htmlFor="can_combine" className="cursor-pointer">
                Can be combined with other schemes
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeDialog}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={isSaving}>
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {editingScheme ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                <>
                  <BadgePercent className="h-4 w-4 mr-2" />
                  {editingScheme ? 'Update Scheme' : 'Create Scheme'}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
