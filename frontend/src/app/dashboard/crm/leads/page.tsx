'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { toast } from 'sonner';
import {
  MoreHorizontal,
  Plus,
  Eye,
  UserPlus,
  Phone,
  Target,
  LayoutGrid,
  List,
  DollarSign,
  TrendingUp,
  Filter,
  ThermometerSun,
  Mail,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { leadsApi } from '@/lib/api';
import { formatDate, cn } from '@/lib/utils';

interface Lead {
  id: string;
  name: string;
  phone: string;
  email?: string;
  company?: string;
  source: string;
  status: 'NEW' | 'CONTACTED' | 'QUALIFIED' | 'PROPOSAL' | 'NEGOTIATION' | 'WON' | 'LOST';
  stage: string;
  temperature: 'HOT' | 'WARM' | 'COLD';
  assigned_to_id?: string;
  assigned_to?: { full_name: string };
  expected_value?: number;
  expected_close_date?: string;
  score?: { total: number; grade: string };
  notes?: string;
  created_at: string;
  last_contacted_at?: string;
}

const sourceColors: Record<string, string> = {
  WEBSITE: 'bg-blue-100 text-blue-800',
  REFERRAL: 'bg-green-100 text-green-800',
  SOCIAL_MEDIA: 'bg-purple-100 text-purple-800',
  CALL_CENTER: 'bg-orange-100 text-orange-800',
  WALK_IN: 'bg-gray-100 text-gray-800',
  EXHIBITION: 'bg-pink-100 text-pink-800',
  PARTNER: 'bg-cyan-100 text-cyan-800',
  OTHER: 'bg-gray-100 text-gray-800',
};

const temperatureConfig: Record<string, { color: string; bgColor: string; label: string }> = {
  HOT: { color: 'text-red-600', bgColor: 'bg-red-100', label: 'Hot' },
  WARM: { color: 'text-orange-600', bgColor: 'bg-orange-100', label: 'Warm' },
  COLD: { color: 'text-blue-600', bgColor: 'bg-blue-100', label: 'Cold' },
};

const statusConfig: Record<string, { color: string; label: string }> = {
  NEW: { color: 'bg-gray-100 text-gray-800', label: 'New' },
  CONTACTED: { color: 'bg-blue-100 text-blue-800', label: 'Contacted' },
  QUALIFIED: { color: 'bg-purple-100 text-purple-800', label: 'Qualified' },
  PROPOSAL: { color: 'bg-yellow-100 text-yellow-800', label: 'Proposal' },
  NEGOTIATION: { color: 'bg-orange-100 text-orange-800', label: 'Negotiation' },
  WON: { color: 'bg-green-100 text-green-800', label: 'Won' },
  LOST: { color: 'bg-red-100 text-red-800', label: 'Lost' },
};

const pipelineStages = ['NEW', 'CONTACTED', 'QUALIFIED', 'PROPOSAL', 'NEGOTIATION'];

interface LeadFormData {
  name: string;
  phone: string;
  email: string;
  company: string;
  source: string;
  temperature: 'HOT' | 'WARM' | 'COLD';
  expected_value: string;
  notes: string;
}

const initialLeadForm: LeadFormData = {
  name: '',
  phone: '',
  email: '',
  company: '',
  source: 'WEBSITE',
  temperature: 'WARM',
  expected_value: '',
  notes: '',
};

export default function LeadsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [view, setView] = useState<'list' | 'pipeline'>('list');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [temperatureFilter, setTemperatureFilter] = useState<string>('all');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState<LeadFormData>(initialLeadForm);

  const { data, isLoading } = useQuery({
    queryKey: ['leads', page, pageSize, statusFilter, sourceFilter, temperatureFilter],
    queryFn: () => leadsApi.list({
      page: page + 1,
      size: pageSize,
      status: statusFilter !== 'all' ? statusFilter : undefined,
      source: sourceFilter !== 'all' ? sourceFilter : undefined,
      temperature: temperatureFilter !== 'all' ? temperatureFilter : undefined,
    }),
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['lead-stats'],
    queryFn: leadsApi.getStats,
  });

  const { data: pipelineData } = useQuery({
    queryKey: ['lead-pipeline'],
    queryFn: leadsApi.getPipeline,
    enabled: view === 'pipeline',
  });

  const createMutation = useMutation({
    mutationFn: leadsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
      queryClient.invalidateQueries({ queryKey: ['lead-pipeline'] });
      toast.success('Lead created successfully');
      setIsDialogOpen(false);
      setFormData(initialLeadForm);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create lead');
    },
  });

  const handleSubmit = () => {
    if (!formData.name.trim()) {
      toast.error('Lead name is required');
      return;
    }
    if (!formData.phone.trim()) {
      toast.error('Phone number is required');
      return;
    }

    createMutation.mutate({
      name: formData.name,
      phone: formData.phone,
      email: formData.email || undefined,
      company: formData.company || undefined,
      source: formData.source,
      temperature: formData.temperature,
      expected_value: formData.expected_value ? parseInt(formData.expected_value) : undefined,
      notes: formData.notes || undefined,
    });
  };

  // Group leads by status for pipeline view
  const pipelineGroups: Record<string, Lead[]> = useMemo(() => {
    if (pipelineData) return pipelineData as Record<string, Lead[]>;

    // Fallback: group from list data
    const groups: Record<string, Lead[]> = {};
    pipelineStages.forEach((stage) => {
      groups[stage] = [];
    });
    (data?.items ?? []).forEach((lead: Lead) => {
      if (groups[lead.status]) {
        groups[lead.status].push(lead);
      }
    });
    return groups;
  }, [pipelineData, data?.items]);

  const columns: ColumnDef<Lead>[] = [
    {
      accessorKey: 'name',
      header: 'Lead',
      cell: ({ row }) => (
        <button
          onClick={() => router.push(`/dashboard/crm/leads/${row.original.id}`)}
          className="flex items-center gap-3 hover:text-primary transition-colors text-left"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
            <Target className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium">{row.original.name}</div>
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Phone className="h-3 w-3" />
              {row.original.phone}
            </div>
          </div>
        </button>
      ),
    },
    {
      accessorKey: 'temperature',
      header: 'Temp',
      cell: ({ row }) => {
        const config = temperatureConfig[row.original.temperature];
        return (
          <div className={cn('flex items-center gap-1', config.color)}>
            <ThermometerSun className="h-4 w-4" />
            <span className="text-sm font-medium">{config.label}</span>
          </div>
        );
      },
    },
    {
      accessorKey: 'source',
      header: 'Source',
      cell: ({ row }) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${sourceColors[row.original.source] || 'bg-gray-100'}`}>
          {row.original.source?.replace(/_/g, ' ') ?? '-'}
        </span>
      ),
    },
    {
      accessorKey: 'assigned_to',
      header: 'Assigned To',
      cell: ({ row }) => (
        <span className="text-sm">
          {row.original.assigned_to?.full_name || 'Unassigned'}
        </span>
      ),
    },
    {
      accessorKey: 'expected_value',
      header: 'Value',
      cell: ({ row }) => (
        <span className="font-medium">
          {row.original.expected_value
            ? `₹${row.original.expected_value.toLocaleString('en-IN')}`
            : '-'}
        </span>
      ),
    },
    {
      accessorKey: 'score',
      header: 'Score',
      cell: ({ row }) => {
        const score = row.original.score;
        if (!score) return <span className="text-muted-foreground">-</span>;
        return (
          <div className="flex items-center gap-2">
            <span className="font-medium">{score.total}</span>
            <Badge variant="outline" className="text-xs">{score.grade}</Badge>
          </div>
        );
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
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
            <DropdownMenuItem onClick={() => router.push(`/dashboard/crm/leads/${row.original.id}`)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Phone className="mr-2 h-4 w-4" />
              Call Lead
            </DropdownMenuItem>
            {row.original.email && (
              <DropdownMenuItem>
                <Mail className="mr-2 h-4 w-4" />
                Send Email
              </DropdownMenuItem>
            )}
            {row.original.status === 'WON' && (
              <DropdownMenuItem onClick={() => router.push(`/dashboard/crm/leads/${row.original.id}`)}>
                <UserPlus className="mr-2 h-4 w-4" />
                Convert to Customer
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  // Pipeline Card Component
  const PipelineCard = ({ lead }: { lead: Lead }) => {
    const tempConfig = temperatureConfig[lead.temperature];
    return (
      <Card
        className="cursor-pointer hover:shadow-md transition-shadow"
        onClick={() => router.push(`/dashboard/crm/leads/${lead.id}`)}
      >
        <CardContent className="p-3">
          <div className="flex items-start justify-between mb-2">
            <div className="font-medium text-sm">{lead.name}</div>
            <div className={cn('flex items-center gap-1 text-xs', tempConfig.color)}>
              <ThermometerSun className="h-3 w-3" />
            </div>
          </div>
          {lead.company && (
            <p className="text-xs text-muted-foreground mb-2">{lead.company}</p>
          )}
          <div className="flex items-center justify-between">
            <span className={`px-1.5 py-0.5 rounded text-xs ${sourceColors[lead.source] || 'bg-gray-100'}`}>
              {lead.source.replace(/_/g, ' ')}
            </span>
            {lead.expected_value && (
              <span className="text-xs font-medium text-green-600">
                ₹{(lead.expected_value / 1000).toFixed(0)}K
              </span>
            )}
          </div>
          {lead.score && (
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 bg-muted rounded-full h-1.5">
                <div
                  className="bg-primary rounded-full h-1.5"
                  style={{ width: `${lead.score.total}%` }}
                />
              </div>
              <span className="text-xs text-muted-foreground">{lead.score.total}</span>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Leads"
        description="Manage sales leads and pipeline"
        actions={
          <div className="flex items-center gap-2">
            <div className="flex items-center border rounded-lg">
              <Button
                variant={view === 'list' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setView('list')}
              >
                <List className="h-4 w-4" />
              </Button>
              <Button
                variant={view === 'pipeline' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setView('pipeline')}
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
            </div>
            <Button onClick={() => setIsDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Lead
            </Button>
          </div>
        }
      />

      {/* Stats Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Leads</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{stats?.total ?? 0}</div>
            )}
            <p className="text-xs text-muted-foreground">in pipeline</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pipeline Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">
                ₹{((stats?.total_pipeline_value ?? 0) / 100000).toFixed(1)}L
              </div>
            )}
            <p className="text-xs text-muted-foreground">expected revenue</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conversion Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold text-green-600">
                {((stats?.conversion_rate ?? 0) * 100).toFixed(1)}%
              </div>
            )}
            <p className="text-xs text-muted-foreground">lead to customer</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Hot Leads</CardTitle>
            <ThermometerSun className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold text-red-600">
                {Object.values(pipelineGroups).flat().filter((l) => l.temperature === 'HOT').length}
              </div>
            )}
            <p className="text-xs text-muted-foreground">need attention</p>
          </CardContent>
        </Card>
      </div>

      {view === 'list' ? (
        <>
          {/* Filters */}
          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Filters:</span>
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="All Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    {Object.entries(statusConfig).map(([key, config]) => (
                      <SelectItem key={key} value={key}>{config.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={sourceFilter} onValueChange={setSourceFilter}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="All Sources" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Sources</SelectItem>
                    {Object.keys(sourceColors).map((source) => (
                      <SelectItem key={source} value={source}>{source.replace(/_/g, ' ')}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={temperatureFilter} onValueChange={setTemperatureFilter}>
                  <SelectTrigger className="w-[130px]">
                    <SelectValue placeholder="All Temps" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Temps</SelectItem>
                    {Object.entries(temperatureConfig).map(([key, config]) => (
                      <SelectItem key={key} value={key}>{config.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <DataTable
            columns={columns}
            data={data?.items ?? []}
            searchKey="name"
            searchPlaceholder="Search leads..."
            isLoading={isLoading}
            manualPagination
            pageCount={data?.pages ?? 0}
            pageIndex={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        </>
      ) : (
        /* Pipeline View */
        <div className="grid grid-cols-5 gap-4">
          {pipelineStages.map((stage) => {
            const stageConfig = statusConfig[stage];
            const leads = pipelineGroups[stage] || [];
            const stageValue = leads.reduce((sum, l) => sum + (l.expected_value || 0), 0);

            return (
              <div key={stage} className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge className={stageConfig.color}>
                    {stageConfig.label}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{leads.length}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  ₹{(stageValue / 100000).toFixed(1)}L
                </div>
                <div className="space-y-2 min-h-[400px] bg-muted/50 rounded-lg p-2">
                  {leads.map((lead) => (
                    <PipelineCard key={lead.id} lead={lead} />
                  ))}
                  {leads.length === 0 && (
                    <div className="flex items-center justify-center h-20 text-xs text-muted-foreground">
                      No leads
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Lead Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add New Lead</DialogTitle>
            <DialogDescription>
              Enter lead details to add to your pipeline
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  placeholder="Lead name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone">Phone *</Label>
                <Input
                  id="phone"
                  placeholder="+91 98765 43210"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="email@example.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="company">Company</Label>
                <Input
                  id="company"
                  placeholder="Company name"
                  value={formData.company}
                  onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="source">Source</Label>
                <Select
                  value={formData.source}
                  onValueChange={(value) => setFormData({ ...formData, source: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select source" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.keys(sourceColors).map((source) => (
                      <SelectItem key={source} value={source}>
                        {source.replace(/_/g, ' ')}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="temperature">Temperature</Label>
                <Select
                  value={formData.temperature}
                  onValueChange={(value: 'HOT' | 'WARM' | 'COLD') => setFormData({ ...formData, temperature: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select temp" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(temperatureConfig).map(([key, config]) => (
                      <SelectItem key={key} value={key}>
                        {config.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="expected_value">Expected Value (₹)</Label>
              <Input
                id="expected_value"
                type="number"
                placeholder="50000"
                value={formData.expected_value}
                onChange={(e) => setFormData({ ...formData, expected_value: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                placeholder="Additional notes about the lead..."
                rows={2}
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Add Lead
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
