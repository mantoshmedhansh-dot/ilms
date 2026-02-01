'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Plus,
  ArrowLeft,
  Pencil,
  Trash2,
  Calendar,
  Tag,
  Percent,
  Clock,
  Gift,
  Loader2,
  Check,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { PageHeader } from '@/components/common';
import { channelsApi } from '@/lib/api';
import apiClient from '@/lib/api/client';
import { toast } from 'sonner';

interface PricingRule {
  id: string;
  code: string;
  name: string;
  description?: string;
  rule_type: string;
  channel_id?: string;
  category_id?: string;
  product_id?: string;
  brand_id?: string;
  conditions: Record<string, unknown>;
  discount_type: string;
  discount_value: number;
  effective_from?: string;
  effective_to?: string;
  priority: number;
  is_combinable: boolean;
  is_active: boolean;
  max_uses?: number;
  current_uses?: number;
  created_at: string;
  updated_at: string;
}

interface Channel {
  id: string;
  code: string;
  name: string;
  type: string;
}

const pricingRulesApi = {
  list: async (params?: { rule_type?: string; channel_id?: string; is_active?: boolean }) => {
    try {
      const { data } = await apiClient.get('/pricing-rules', { params });
      return data;
    } catch {
      return { items: [], total: 0 };
    }
  },
  create: async (rule: Omit<PricingRule, 'id' | 'created_at' | 'updated_at' | 'current_uses'>) => {
    const { data } = await apiClient.post('/pricing-rules', rule);
    return data;
  },
  update: async (id: string, rule: Partial<PricingRule>) => {
    const { data } = await apiClient.put(`/pricing-rules/${id}`, rule);
    return data;
  },
  delete: async (id: string) => {
    const { data } = await apiClient.delete(`/pricing-rules/${id}`);
    return data;
  },
};

const RULE_TYPES = [
  { value: 'PROMOTIONAL', label: 'Promotional', icon: Tag, description: 'Promo codes and campaigns' },
  { value: 'TIME_BASED', label: 'Time-Based', icon: Clock, description: 'Weekend, festival, or scheduled discounts' },
  { value: 'VOLUME_DISCOUNT', label: 'Volume Discount', icon: Gift, description: 'Quantity-based discounts' },
  { value: 'CUSTOMER_SEGMENT', label: 'Customer Segment', icon: Percent, description: 'VIP, Dealer, Corporate discounts' },
];

function getRuleTypeIcon(type: string) {
  const ruleType = RULE_TYPES.find(r => r.value === type);
  if (ruleType) {
    const Icon = ruleType.icon;
    return <Icon className="h-4 w-4" />;
  }
  return <Tag className="h-4 w-4" />;
}

function getRuleTypeBadgeColor(type: string): string {
  switch (type) {
    case 'PROMOTIONAL': return 'bg-purple-100 text-purple-800';
    case 'TIME_BASED': return 'bg-blue-100 text-blue-800';
    case 'VOLUME_DISCOUNT': return 'bg-green-100 text-green-800';
    case 'CUSTOMER_SEGMENT': return 'bg-orange-100 text-orange-800';
    default: return 'bg-gray-100 text-gray-800';
  }
}

function isRuleActive(rule: PricingRule): boolean {
  if (!rule.is_active) return false;

  const now = new Date();
  if (rule.effective_from && new Date(rule.effective_from) > now) return false;
  if (rule.effective_to && new Date(rule.effective_to) < now) return false;
  if (rule.max_uses && rule.current_uses && rule.current_uses >= rule.max_uses) return false;

  return true;
}

function formatDate(dateString?: string): string {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function PromotionalPricingPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedRule, setSelectedRule] = useState<PricingRule | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterChannel, setFilterChannel] = useState<string>('all');

  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    rule_type: 'PROMOTIONAL',
    channel_id: '',
    discount_type: 'PERCENTAGE',
    discount_value: 0,
    effective_from: '',
    effective_to: '',
    priority: 100,
    is_combinable: false,
    is_active: true,
    max_uses: 0,
    // Conditions based on rule type
    promo_code: '',
    min_quantity: 0,
    customer_segments: [] as string[],
  });

  const queryClient = useQueryClient();

  // Fetch channels
  const { data: channels = [] } = useQuery({
    queryKey: ['channels-dropdown'],
    queryFn: () => channelsApi.dropdown(),
  });

  // Fetch pricing rules
  const { data: rulesData, isLoading } = useQuery({
    queryKey: ['pricing-rules', filterType, filterChannel],
    queryFn: () => pricingRulesApi.list({
      rule_type: filterType !== 'all' ? filterType : undefined,
      channel_id: filterChannel !== 'all' ? filterChannel : undefined,
    }),
  });

  const rules: PricingRule[] = rulesData?.items || [];

  // Mutations
  const createMutation = useMutation({
    mutationFn: (rule: Parameters<typeof pricingRulesApi.create>[0]) =>
      pricingRulesApi.create(rule),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pricing-rules'] });
      toast.success('Pricing rule created successfully');
      setIsDialogOpen(false);
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create pricing rule');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, rule }: { id: string; rule: Partial<PricingRule> }) =>
      pricingRulesApi.update(id, rule),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pricing-rules'] });
      toast.success('Pricing rule updated successfully');
      setIsDialogOpen(false);
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update pricing rule');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => pricingRulesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pricing-rules'] });
      toast.success('Pricing rule deleted');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete pricing rule');
    },
  });

  const resetForm = () => {
    setSelectedRule(null);
    setFormData({
      code: '',
      name: '',
      description: '',
      rule_type: 'PROMOTIONAL',
      channel_id: '',
      discount_type: 'PERCENTAGE',
      discount_value: 0,
      effective_from: '',
      effective_to: '',
      priority: 100,
      is_combinable: false,
      is_active: true,
      max_uses: 0,
      promo_code: '',
      min_quantity: 0,
      customer_segments: [],
    });
  };

  const handleAddNew = () => {
    resetForm();
    setIsDialogOpen(true);
  };

  const handleEdit = (rule: PricingRule) => {
    setSelectedRule(rule);
    setFormData({
      code: rule.code,
      name: rule.name,
      description: rule.description || '',
      rule_type: rule.rule_type,
      channel_id: rule.channel_id || '',
      discount_type: rule.discount_type,
      discount_value: rule.discount_value,
      effective_from: rule.effective_from ? rule.effective_from.slice(0, 16) : '',
      effective_to: rule.effective_to ? rule.effective_to.slice(0, 16) : '',
      priority: rule.priority,
      is_combinable: rule.is_combinable,
      is_active: rule.is_active,
      max_uses: rule.max_uses || 0,
      promo_code: (rule.conditions as { promo_code?: string })?.promo_code || '',
      min_quantity: (rule.conditions as { min_quantity?: number })?.min_quantity || 0,
      customer_segments: (rule.conditions as { segments?: string[] })?.segments || [],
    });
    setIsDialogOpen(true);
  };

  const handleDelete = (rule: PricingRule) => {
    if (confirm(`Delete pricing rule "${rule.name}"?`)) {
      deleteMutation.mutate(rule.id);
    }
  };

  const handleSubmit = () => {
    // Build conditions based on rule type
    let conditions: Record<string, unknown> = {};

    if (formData.rule_type === 'PROMOTIONAL') {
      conditions = { promo_code: formData.promo_code };
    } else if (formData.rule_type === 'VOLUME_DISCOUNT') {
      conditions = { min_quantity: formData.min_quantity };
    } else if (formData.rule_type === 'CUSTOMER_SEGMENT') {
      conditions = { segments: formData.customer_segments };
    } else if (formData.rule_type === 'TIME_BASED') {
      conditions = {}; // Time-based uses effective_from/to dates
    }

    const ruleData = {
      code: formData.code,
      name: formData.name,
      description: formData.description || undefined,
      rule_type: formData.rule_type,
      channel_id: formData.channel_id || undefined,
      conditions,
      discount_type: formData.discount_type,
      discount_value: formData.discount_value,
      effective_from: formData.effective_from ? new Date(formData.effective_from).toISOString() : undefined,
      effective_to: formData.effective_to ? new Date(formData.effective_to).toISOString() : undefined,
      priority: formData.priority,
      is_combinable: formData.is_combinable,
      is_active: formData.is_active,
      max_uses: formData.max_uses || undefined,
    };

    if (selectedRule) {
      updateMutation.mutate({ id: selectedRule.id, rule: ruleData });
    } else {
      createMutation.mutate(ruleData as Parameters<typeof pricingRulesApi.create>[0]);
    }
  };

  // Stats
  const stats = useMemo(() => {
    const activeRules = rules.filter(isRuleActive);
    const promoRules = rules.filter(r => r.rule_type === 'PROMOTIONAL');
    const timeBasedRules = rules.filter(r => r.rule_type === 'TIME_BASED');
    const expiringSoon = rules.filter(r => {
      if (!r.effective_to) return false;
      const expiryDate = new Date(r.effective_to);
      const inWeek = new Date();
      inWeek.setDate(inWeek.getDate() + 7);
      return expiryDate <= inWeek && expiryDate > new Date();
    });

    return {
      total: rules.length,
      active: activeRules.length,
      promo: promoRules.length,
      timeBased: timeBasedRules.length,
      expiringSoon: expiringSoon.length,
    };
  }, [rules]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Promotional Pricing"
        description="Manage promotional and time-based pricing rules"
        actions={
          <div className="flex gap-2">
            <Link href="/dashboard/channels/pricing">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Pricing
              </Button>
            </Link>
            <Button onClick={handleAddNew}>
              <Plus className="mr-2 h-4 w-4" />
              Add Pricing Rule
            </Button>
          </div>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Rules</CardTitle>
            <Tag className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Now</CardTitle>
            <Check className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.active}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Promo Codes</CardTitle>
            <Gift className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">{stats.promo}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Time-Based</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats.timeBased}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Expiring Soon</CardTitle>
            <Calendar className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats.expiringSoon}</div>
            <p className="text-xs text-muted-foreground">Within 7 days</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Rule Type</Label>
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {RULE_TYPES.map(type => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Channel</Label>
          <Select value={filterChannel} onValueChange={setFilterChannel}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="All Channels" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Channels</SelectItem>
              {channels.map((channel: Channel) => (
                <SelectItem key={channel.id} value={channel.id}>
                  {channel.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Rules Table */}
      <Card>
        <CardHeader>
          <CardTitle>Pricing Rules</CardTitle>
          <CardDescription>
            Manage promotional and time-based discount rules
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : rules.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Tag className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-lg font-medium">No Pricing Rules</p>
              <p className="text-sm text-muted-foreground mb-4">
                Create promotional or time-based pricing rules
              </p>
              <Button onClick={handleAddNew}>
                <Plus className="mr-2 h-4 w-4" />
                Add First Rule
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Discount</TableHead>
                  <TableHead>Valid Period</TableHead>
                  <TableHead>Channel</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => {
                  const active = isRuleActive(rule);
                  return (
                    <TableRow key={rule.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{rule.name}</p>
                          <p className="text-sm text-muted-foreground font-mono">{rule.code}</p>
                          {rule.description && (
                            <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                              {rule.description}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={`${getRuleTypeBadgeColor(rule.rule_type)} flex items-center gap-1 w-fit`}>
                          {getRuleTypeIcon(rule.rule_type)}
                          {RULE_TYPES.find(t => t.value === rule.rule_type)?.label || rule.rule_type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold text-green-600">
                          {rule.discount_type === 'PERCENTAGE'
                            ? `${rule.discount_value}% off`
                            : `₹${rule.discount_value} off`}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          <p>{formatDate(rule.effective_from)}</p>
                          <p className="text-muted-foreground">to {formatDate(rule.effective_to)}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        {rule.channel_id ? (
                          <Badge variant="outline">
                            {channels.find((c: Channel) => c.id === rule.channel_id)?.name || 'Unknown'}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground text-sm">All Channels</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {rule.max_uses ? (
                          <div className="text-sm">
                            <span className="font-medium">{rule.current_uses || 0}</span>
                            <span className="text-muted-foreground"> / {rule.max_uses}</span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground text-sm">Unlimited</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge className={active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}>
                          {active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(rule)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive"
                            onClick={() => handleDelete(rule)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {selectedRule ? 'Edit Pricing Rule' : 'Create Pricing Rule'}
            </DialogTitle>
            <DialogDescription>
              {selectedRule
                ? 'Update the promotional or time-based pricing rule'
                : 'Create a new promotional, time-based, or volume discount rule'}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Rule Type */}
            <div className="space-y-2">
              <Label>Rule Type</Label>
              <Select
                value={formData.rule_type}
                onValueChange={(v) => setFormData({ ...formData, rule_type: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {RULE_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>
                      <div className="flex items-center gap-2">
                        <type.icon className="h-4 w-4" />
                        <span>{type.label}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {RULE_TYPES.find(t => t.value === formData.rule_type)?.description}
              </p>
            </div>

            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Code <span className="text-red-500">*</span></Label>
                <Input
                  placeholder="SUMMER2026"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                />
              </div>
              <div className="space-y-2">
                <Label>Name <span className="text-red-500">*</span></Label>
                <Input
                  placeholder="Summer Sale 2026"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                placeholder="Describe this pricing rule..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
              />
            </div>

            {/* Channel Scope */}
            <div className="space-y-2">
              <Label>Apply to Channel</Label>
              <Select
                value={formData.channel_id || 'all'}
                onValueChange={(v) => setFormData({ ...formData, channel_id: v === 'all' ? '' : v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Channels" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Channels</SelectItem>
                  {channels.map((channel: Channel) => (
                    <SelectItem key={channel.id} value={channel.id}>
                      {channel.name} ({channel.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Discount */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Discount Type</Label>
                <Select
                  value={formData.discount_type}
                  onValueChange={(v) => setFormData({ ...formData, discount_type: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PERCENTAGE">Percentage (%)</SelectItem>
                    <SelectItem value="FIXED_AMOUNT">Fixed Amount (₹)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Discount Value <span className="text-red-500">*</span></Label>
                <Input
                  type="number"
                  placeholder="10"
                  value={formData.discount_value || ''}
                  onChange={(e) => setFormData({ ...formData, discount_value: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>

            {/* Validity Period */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Valid From</Label>
                <Input
                  type="datetime-local"
                  value={formData.effective_from}
                  onChange={(e) => setFormData({ ...formData, effective_from: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Valid Until</Label>
                <Input
                  type="datetime-local"
                  value={formData.effective_to}
                  onChange={(e) => setFormData({ ...formData, effective_to: e.target.value })}
                />
              </div>
            </div>

            {/* Type-specific conditions */}
            {formData.rule_type === 'PROMOTIONAL' && (
              <div className="space-y-2">
                <Label>Promo Code</Label>
                <Input
                  placeholder="SUMMER20"
                  value={formData.promo_code}
                  onChange={(e) => setFormData({ ...formData, promo_code: e.target.value.toUpperCase() })}
                />
                <p className="text-xs text-muted-foreground">
                  Customers will enter this code at checkout
                </p>
              </div>
            )}

            {formData.rule_type === 'VOLUME_DISCOUNT' && (
              <div className="space-y-2">
                <Label>Minimum Quantity</Label>
                <Input
                  type="number"
                  placeholder="10"
                  value={formData.min_quantity || ''}
                  onChange={(e) => setFormData({ ...formData, min_quantity: parseInt(e.target.value) || 0 })}
                />
                <p className="text-xs text-muted-foreground">
                  Discount applies when quantity is at least this amount
                </p>
              </div>
            )}

            {formData.rule_type === 'CUSTOMER_SEGMENT' && (
              <div className="space-y-2">
                <Label>Customer Segments</Label>
                <Select
                  value={formData.customer_segments[0] || ''}
                  onValueChange={(v) => setFormData({ ...formData, customer_segments: [v] })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select segment" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="VIP">VIP</SelectItem>
                    <SelectItem value="DEALER">Dealer</SelectItem>
                    <SelectItem value="DISTRIBUTOR">Distributor</SelectItem>
                    <SelectItem value="CORPORATE">Corporate</SelectItem>
                    <SelectItem value="GOVERNMENT">Government</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Additional Options */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Priority</Label>
                <Input
                  type="number"
                  placeholder="100"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 100 })}
                />
                <p className="text-xs text-muted-foreground">
                  Lower = higher priority
                </p>
              </div>
              <div className="space-y-2">
                <Label>Max Uses</Label>
                <Input
                  type="number"
                  placeholder="0 (unlimited)"
                  value={formData.max_uses || ''}
                  onChange={(e) => setFormData({ ...formData, max_uses: parseInt(e.target.value) || 0 })}
                />
                <p className="text-xs text-muted-foreground">
                  0 = unlimited
                </p>
              </div>
            </div>

            {/* Switches */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Active</Label>
                <p className="text-xs text-muted-foreground">Enable this pricing rule</p>
              </div>
              <Switch
                checked={formData.is_active}
                onCheckedChange={(v) => setFormData({ ...formData, is_active: v })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Combinable</Label>
                <p className="text-xs text-muted-foreground">Can be combined with other rules</p>
              </div>
              <Switch
                checked={formData.is_combinable}
                onCheckedChange={(v) => setFormData({ ...formData, is_combinable: v })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createMutation.isPending || updateMutation.isPending || !formData.code || !formData.name || !formData.discount_value}
            >
              {(createMutation.isPending || updateMutation.isPending) && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {selectedRule ? 'Update Rule' : 'Create Rule'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
