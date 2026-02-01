'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Target,
  Phone,
  Mail,
  MapPin,
  Calendar,
  Clock,
  User,
  DollarSign,
  Star,
  MessageSquare,
  CheckCircle,
  XCircle,
  AlertTriangle,
  TrendingUp,
  Building,
  ArrowRight,
  PhoneCall,
  FileText,
  Plus,
  Edit,
  UserPlus,
  Zap,
  BarChart3,
  History,
  ThermometerSun,
  Send,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import apiClient from '@/lib/api/client';
import { formatDate, formatDateTime, cn } from '@/lib/utils';

// Types
interface LeadScore {
  total: number;
  breakdown: {
    demographic: number;
    behavioral: number;
    engagement: number;
    intent: number;
  };
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  last_updated: string;
}

interface LeadActivity {
  id: string;
  type: 'CALL' | 'EMAIL' | 'MEETING' | 'NOTE' | 'WHATSAPP' | 'SMS' | 'SYSTEM';
  title: string;
  description?: string;
  outcome?: string;
  performed_by: string;
  created_at: string;
  duration_minutes?: number;
  scheduled_at?: string;
}

interface Lead {
  id: string;
  name: string;
  phone: string;
  alternate_phone?: string;
  email?: string;
  company?: string;
  designation?: string;
  source: 'WEBSITE' | 'REFERRAL' | 'SOCIAL_MEDIA' | 'CALL_CENTER' | 'WALK_IN' | 'EXHIBITION' | 'PARTNER' | 'OTHER';
  campaign_id?: string;
  campaign_name?: string;
  status: 'NEW' | 'CONTACTED' | 'QUALIFIED' | 'PROPOSAL' | 'NEGOTIATION' | 'WON' | 'LOST';
  stage: string;
  temperature: 'HOT' | 'WARM' | 'COLD';
  score?: LeadScore;
  assigned_to_id?: string;
  assigned_to?: { id: string; full_name: string; email: string };
  expected_value?: number;
  expected_close_date?: string;
  product_interest?: string[];
  requirements?: string;
  budget_range?: { min: number; max: number };
  address?: {
    line1: string;
    line2?: string;
    city: string;
    state: string;
    pincode: string;
  };
  lost_reason?: string;
  won_order_id?: string;
  customer_id?: string;
  notes?: string;
  tags?: string[];
  created_at: string;
  updated_at: string;
  last_contacted_at?: string;
  next_followup_at?: string;
  activities?: LeadActivity[];
  conversion_probability?: number;
}

// Status workflow
const statusFlow: Record<string, string[]> = {
  NEW: ['CONTACTED'],
  CONTACTED: ['QUALIFIED', 'LOST'],
  QUALIFIED: ['PROPOSAL', 'LOST'],
  PROPOSAL: ['NEGOTIATION', 'LOST'],
  NEGOTIATION: ['WON', 'LOST'],
  WON: [],
  LOST: ['NEW'],
};

const statusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  NEW: { color: 'bg-gray-100 text-gray-800', icon: <Target className="h-4 w-4" />, label: 'New' },
  CONTACTED: { color: 'bg-blue-100 text-blue-800', icon: <Phone className="h-4 w-4" />, label: 'Contacted' },
  QUALIFIED: { color: 'bg-purple-100 text-purple-800', icon: <CheckCircle className="h-4 w-4" />, label: 'Qualified' },
  PROPOSAL: { color: 'bg-yellow-100 text-yellow-800', icon: <FileText className="h-4 w-4" />, label: 'Proposal' },
  NEGOTIATION: { color: 'bg-orange-100 text-orange-800', icon: <MessageSquare className="h-4 w-4" />, label: 'Negotiation' },
  WON: { color: 'bg-green-100 text-green-800', icon: <CheckCircle className="h-4 w-4" />, label: 'Won' },
  LOST: { color: 'bg-red-100 text-red-800', icon: <XCircle className="h-4 w-4" />, label: 'Lost' },
};

const temperatureConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  HOT: { color: 'text-red-600', icon: <ThermometerSun className="h-4 w-4" />, label: 'Hot' },
  WARM: { color: 'text-orange-600', icon: <ThermometerSun className="h-4 w-4" />, label: 'Warm' },
  COLD: { color: 'text-blue-600', icon: <ThermometerSun className="h-4 w-4" />, label: 'Cold' },
};

const scoreGradeConfig: Record<string, { color: string; label: string }> = {
  A: { color: 'bg-green-100 text-green-800', label: 'Excellent' },
  B: { color: 'bg-blue-100 text-blue-800', label: 'Good' },
  C: { color: 'bg-yellow-100 text-yellow-800', label: 'Average' },
  D: { color: 'bg-orange-100 text-orange-800', label: 'Below Average' },
  F: { color: 'bg-red-100 text-red-800', label: 'Poor' },
};

const activityTypeConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  CALL: { icon: <PhoneCall className="h-4 w-4" />, color: 'bg-blue-100' },
  EMAIL: { icon: <Mail className="h-4 w-4" />, color: 'bg-purple-100' },
  MEETING: { icon: <User className="h-4 w-4" />, color: 'bg-green-100' },
  NOTE: { icon: <FileText className="h-4 w-4" />, color: 'bg-gray-100' },
  WHATSAPP: { icon: <MessageSquare className="h-4 w-4" />, color: 'bg-green-100' },
  SMS: { icon: <Send className="h-4 w-4" />, color: 'bg-cyan-100' },
  SYSTEM: { icon: <Zap className="h-4 w-4" />, color: 'bg-yellow-100' },
};

// API functions
const leadsApi = {
  getById: async (id: string): Promise<Lead> => {
    const { data } = await apiClient.get(`/leads/${id}`);
    return data;
  },
  updateStatus: async (id: string, status: string, notes?: string, lostReason?: string) => {
    const { data } = await apiClient.put(`/leads/${id}/status`, { status, notes, lost_reason: lostReason });
    return data;
  },
  updateTemperature: async (id: string, temperature: string) => {
    const { data } = await apiClient.put(`/leads/${id}/temperature`, { temperature });
    return data;
  },
  assignTo: async (id: string, userId: string) => {
    const { data } = await apiClient.put(`/leads/${id}/assign`, { user_id: userId });
    return data;
  },
  qualify: async (id: string, qualificationData: {
    expected_value?: number;
    expected_close_date?: string;
    product_interest?: string[];
    requirements?: string;
    budget_min?: number;
    budget_max?: number;
  }) => {
    const { data } = await apiClient.post(`/leads/${id}/qualify`, qualificationData);
    return data;
  },
  convert: async (id: string) => {
    const { data } = await apiClient.post(`/leads/${id}/convert`);
    return data;
  },
  addActivity: async (id: string, activity: {
    type: string;
    title: string;
    description?: string;
    outcome?: string;
    duration_minutes?: number;
    scheduled_at?: string;
  }) => {
    const { data } = await apiClient.post(`/leads/${id}/activities`, activity);
    return data;
  },
  getActivities: async (id: string): Promise<LeadActivity[]> => {
    const { data } = await apiClient.get(`/leads/${id}/activities`);
    return data;
  },
  recalculateScore: async (id: string): Promise<LeadScore> => {
    const { data } = await apiClient.post(`/leads/${id}/recalculate-score`);
    return data;
  },
  scheduleFollowup: async (id: string, scheduledAt: string, notes?: string) => {
    const { data } = await apiClient.post(`/leads/${id}/schedule-followup`, { scheduled_at: scheduledAt, notes });
    return data;
  },
};

export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const id = params.id as string;

  // Dialogs
  const [qualifyDialog, setQualifyDialog] = useState(false);
  const [activityDialog, setActivityDialog] = useState(false);
  const [convertDialog, setConvertDialog] = useState(false);
  const [lostDialog, setLostDialog] = useState(false);
  const [followupDialog, setFollowupDialog] = useState(false);

  // Form states
  const [expectedValue, setExpectedValue] = useState('');
  const [expectedCloseDate, setExpectedCloseDate] = useState('');
  const [requirements, setRequirements] = useState('');
  const [budgetMin, setBudgetMin] = useState('');
  const [budgetMax, setBudgetMax] = useState('');

  const [activityType, setActivityType] = useState('CALL');
  const [activityTitle, setActivityTitle] = useState('');
  const [activityDescription, setActivityDescription] = useState('');
  const [activityOutcome, setActivityOutcome] = useState('');
  const [activityDuration, setActivityDuration] = useState('');

  const [lostReason, setLostReason] = useState('');
  const [followupDate, setFollowupDate] = useState('');
  const [followupNotes, setFollowupNotes] = useState('');

  // Query
  const { data: lead, isLoading, error } = useQuery({
    queryKey: ['lead', id],
    queryFn: () => leadsApi.getById(id),
  });

  // Mutations
  const updateStatusMutation = useMutation({
    mutationFn: ({ status, notes, lostReason }: { status: string; notes?: string; lostReason?: string }) =>
      leadsApi.updateStatus(id, status, notes, lostReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', id] });
      toast.success('Status updated successfully');
      setLostDialog(false);
      setLostReason('');
    },
    onError: () => toast.error('Failed to update status'),
  });

  const updateTemperatureMutation = useMutation({
    mutationFn: (temperature: string) => leadsApi.updateTemperature(id, temperature),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', id] });
      toast.success('Temperature updated');
    },
    onError: () => toast.error('Failed to update temperature'),
  });

  const qualifyMutation = useMutation({
    mutationFn: () => leadsApi.qualify(id, {
      expected_value: expectedValue ? parseFloat(expectedValue) : undefined,
      expected_close_date: expectedCloseDate || undefined,
      requirements: requirements || undefined,
      budget_min: budgetMin ? parseFloat(budgetMin) : undefined,
      budget_max: budgetMax ? parseFloat(budgetMax) : undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', id] });
      toast.success('Lead qualified successfully');
      setQualifyDialog(false);
    },
    onError: () => toast.error('Failed to qualify lead'),
  });

  const addActivityMutation = useMutation({
    mutationFn: () => leadsApi.addActivity(id, {
      type: activityType,
      title: activityTitle,
      description: activityDescription || undefined,
      outcome: activityOutcome || undefined,
      duration_minutes: activityDuration ? parseInt(activityDuration) : undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', id] });
      toast.success('Activity logged');
      setActivityDialog(false);
      setActivityTitle('');
      setActivityDescription('');
      setActivityOutcome('');
      setActivityDuration('');
    },
    onError: () => toast.error('Failed to log activity'),
  });

  const convertMutation = useMutation({
    mutationFn: () => leadsApi.convert(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['lead', id] });
      toast.success('Lead converted to customer!');
      setConvertDialog(false);
      if (data.customer_id) {
        router.push(`/crm/customers/${data.customer_id}`);
      }
    },
    onError: () => toast.error('Failed to convert lead'),
  });

  const recalculateScoreMutation = useMutation({
    mutationFn: () => leadsApi.recalculateScore(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', id] });
      toast.success('Score recalculated');
    },
    onError: () => toast.error('Failed to recalculate score'),
  });

  const scheduleFollowupMutation = useMutation({
    mutationFn: () => leadsApi.scheduleFollowup(id, followupDate, followupNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', id] });
      toast.success('Follow-up scheduled');
      setFollowupDialog(false);
    },
    onError: () => toast.error('Failed to schedule follow-up'),
  });

  const handleStatusChange = (newStatus: string) => {
    if (newStatus === 'LOST') {
      setLostDialog(true);
    } else if (newStatus === 'QUALIFIED') {
      setQualifyDialog(true);
    } else if (newStatus === 'WON') {
      setConvertDialog(true);
    } else {
      updateStatusMutation.mutate({ status: newStatus });
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-64" />
            <Skeleton className="h-48" />
          </div>
          <div className="space-y-6">
            <Skeleton className="h-48" />
            <Skeleton className="h-48" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !lead) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold">Lead Not Found</h2>
        <p className="text-muted-foreground mt-2">The requested lead could not be found.</p>
        <Button variant="outline" className="mt-4" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Go Back
        </Button>
      </div>
    );
  }

  const config = statusConfig[lead.status];
  const nextStatuses = statusFlow[lead.status] || [];
  const tempConfig = temperatureConfig[lead.temperature];
  const scoreGrade = lead.score ? scoreGradeConfig[lead.score.grade] : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{lead.name}</h1>
              <Badge className={config.color}>
                {config.icon}
                <span className="ml-1">{config.label}</span>
              </Badge>
              <div className={cn('flex items-center gap-1', tempConfig.color)}>
                {tempConfig.icon}
                <span className="text-sm font-medium">{tempConfig.label}</span>
              </div>
            </div>
            <p className="text-muted-foreground mt-1">
              {lead.company ? `${lead.company} • ` : ''}
              Created {formatDate(lead.created_at)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setActivityDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Log Activity
          </Button>
          <Button variant="outline" onClick={() => setFollowupDialog(true)}>
            <Calendar className="mr-2 h-4 w-4" />
            Schedule Follow-up
          </Button>
          {nextStatuses.map((status) => (
            <Button
              key={status}
              variant={status === 'WON' ? 'default' : status === 'LOST' ? 'destructive' : 'outline'}
              onClick={() => handleStatusChange(status)}
              disabled={updateStatusMutation.isPending}
            >
              {status === 'WON' && <CheckCircle className="mr-2 h-4 w-4" />}
              {status === 'LOST' && <XCircle className="mr-2 h-4 w-4" />}
              {statusConfig[status]?.label || status}
            </Button>
          ))}
        </div>
      </div>

      {/* Pipeline Progress */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between gap-4">
            {['NEW', 'CONTACTED', 'QUALIFIED', 'PROPOSAL', 'NEGOTIATION', 'WON'].map((stage, index) => {
              const stageConfig = statusConfig[stage];
              const isActive = lead.status === stage;
              const isPast = ['NEW', 'CONTACTED', 'QUALIFIED', 'PROPOSAL', 'NEGOTIATION', 'WON'].indexOf(lead.status) > index;
              const isLost = lead.status === 'LOST';

              return (
                <div key={stage} className="flex-1">
                  <div className="flex items-center">
                    <div
                      className={cn(
                        'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors',
                        isActive ? 'bg-primary text-primary-foreground' :
                        isPast ? 'bg-green-100 text-green-800' :
                        isLost ? 'bg-red-100 text-red-800' :
                        'bg-muted text-muted-foreground'
                      )}
                    >
                      {isPast ? <CheckCircle className="h-4 w-4" /> : index + 1}
                    </div>
                    {index < 5 && (
                      <div
                        className={cn(
                          'flex-1 h-1 mx-2',
                          isPast ? 'bg-green-500' : 'bg-muted'
                        )}
                      />
                    )}
                  </div>
                  <p className={cn(
                    'text-xs mt-2 text-center',
                    isActive ? 'font-medium text-foreground' : 'text-muted-foreground'
                  )}>
                    {stageConfig.label}
                  </p>
                </div>
              );
            })}
          </div>
          {lead.status === 'LOST' && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center gap-2 text-red-800">
                <XCircle className="h-4 w-4" />
                <span className="font-medium">Lead Lost</span>
              </div>
              {lead.lost_reason && (
                <p className="mt-1 text-sm text-red-700">Reason: {lead.lost_reason}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <Tabs defaultValue="overview" className="space-y-4">
            <TabsList>
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="activities">Activities</TabsTrigger>
              <TabsTrigger value="scoring">Lead Scoring</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              {/* Contact Info */}
              <Card>
                <CardHeader>
                  <CardTitle>Contact Information</CardTitle>
                </CardHeader>
                <CardContent className="grid md:grid-cols-2 gap-4">
                  <div className="flex items-center gap-3">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm text-muted-foreground">Phone</p>
                      <p className="font-medium">{lead.phone}</p>
                    </div>
                  </div>
                  {lead.alternate_phone && (
                    <div className="flex items-center gap-3">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-sm text-muted-foreground">Alternate Phone</p>
                        <p className="font-medium">{lead.alternate_phone}</p>
                      </div>
                    </div>
                  )}
                  {lead.email && (
                    <div className="flex items-center gap-3">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-sm text-muted-foreground">Email</p>
                        <p className="font-medium">{lead.email}</p>
                      </div>
                    </div>
                  )}
                  {lead.company && (
                    <div className="flex items-center gap-3">
                      <Building className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-sm text-muted-foreground">Company</p>
                        <p className="font-medium">{lead.company}</p>
                        {lead.designation && <p className="text-sm text-muted-foreground">{lead.designation}</p>}
                      </div>
                    </div>
                  )}
                  {lead.address && (
                    <div className="flex items-start gap-3 md:col-span-2">
                      <MapPin className="h-4 w-4 text-muted-foreground mt-1" />
                      <div>
                        <p className="text-sm text-muted-foreground">Address</p>
                        <p>{lead.address.line1}</p>
                        {lead.address.line2 && <p>{lead.address.line2}</p>}
                        <p>{lead.address.city}, {lead.address.state} - {lead.address.pincode}</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Deal Info */}
              <Card>
                <CardHeader>
                  <CardTitle>Deal Information</CardTitle>
                </CardHeader>
                <CardContent className="grid md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Expected Value</p>
                    <p className="text-xl font-bold">
                      {lead.expected_value ? `₹${lead.expected_value.toLocaleString()}` : 'Not set'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Expected Close Date</p>
                    <p className="font-medium">
                      {lead.expected_close_date ? formatDate(lead.expected_close_date) : 'Not set'}
                    </p>
                  </div>
                  {lead.budget_range && (
                    <div>
                      <p className="text-sm text-muted-foreground">Budget Range</p>
                      <p className="font-medium">
                        ₹{lead.budget_range.min.toLocaleString()} - ₹{lead.budget_range.max.toLocaleString()}
                      </p>
                    </div>
                  )}
                  {lead.conversion_probability !== undefined && (
                    <div>
                      <p className="text-sm text-muted-foreground">Conversion Probability</p>
                      <div className="flex items-center gap-2">
                        <Progress value={lead.conversion_probability} className="flex-1" />
                        <span className="font-medium">{lead.conversion_probability}%</span>
                      </div>
                    </div>
                  )}
                  {lead.product_interest && lead.product_interest.length > 0 && (
                    <div className="md:col-span-2">
                      <p className="text-sm text-muted-foreground mb-2">Product Interest</p>
                      <div className="flex flex-wrap gap-2">
                        {lead.product_interest.map((product, index) => (
                          <Badge key={index} variant="secondary">{product}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {lead.requirements && (
                    <div className="md:col-span-2">
                      <p className="text-sm text-muted-foreground">Requirements</p>
                      <p className="mt-1">{lead.requirements}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Notes */}
              {lead.notes && (
                <Card>
                  <CardHeader>
                    <CardTitle>Notes</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="whitespace-pre-wrap">{lead.notes}</p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="activities" className="space-y-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle>Activity Timeline</CardTitle>
                    <CardDescription>All interactions with this lead</CardDescription>
                  </div>
                  <Button onClick={() => setActivityDialog(true)}>
                    <Plus className="mr-2 h-4 w-4" />
                    Log Activity
                  </Button>
                </CardHeader>
                <CardContent>
                  {lead.activities && lead.activities.length > 0 ? (
                    <div className="relative space-y-0">
                      {lead.activities.map((activity, index) => {
                        const typeConfig = activityTypeConfig[activity.type] || activityTypeConfig.NOTE;
                        return (
                          <div key={activity.id} className="flex gap-4 pb-8 last:pb-0">
                            <div className="relative">
                              <div className={cn('w-10 h-10 rounded-full flex items-center justify-center', typeConfig.color)}>
                                {typeConfig.icon}
                              </div>
                              {index < lead.activities!.length - 1 && (
                                <div className="absolute top-10 left-1/2 -translate-x-1/2 w-0.5 h-full bg-border" />
                              )}
                            </div>
                            <div className="flex-1 pt-1">
                              <div className="flex items-center justify-between">
                                <p className="font-medium">{activity.title}</p>
                                <span className="text-sm text-muted-foreground">
                                  {formatDateTime(activity.created_at)}
                                </span>
                              </div>
                              {activity.description && (
                                <p className="text-sm text-muted-foreground mt-1">{activity.description}</p>
                              )}
                              {activity.outcome && (
                                <p className="text-sm mt-1">
                                  <span className="text-muted-foreground">Outcome:</span> {activity.outcome}
                                </p>
                              )}
                              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                                <span>By: {activity.performed_by}</span>
                                {activity.duration_minutes && (
                                  <span>Duration: {activity.duration_minutes} min</span>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <History className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-muted-foreground">No activities recorded yet</p>
                      <Button variant="outline" className="mt-4" onClick={() => setActivityDialog(true)}>
                        <Plus className="mr-2 h-4 w-4" />
                        Log First Activity
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="scoring" className="space-y-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle>Lead Score</CardTitle>
                    <CardDescription>AI-powered lead scoring based on multiple factors</CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => recalculateScoreMutation.mutate()}
                    disabled={recalculateScoreMutation.isPending}
                  >
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Recalculate
                  </Button>
                </CardHeader>
                <CardContent>
                  {lead.score ? (
                    <div className="space-y-6">
                      <div className="flex items-center gap-6">
                        <div className="text-center">
                          <div className="text-5xl font-bold">{lead.score.total}</div>
                          <p className="text-sm text-muted-foreground">out of 100</p>
                        </div>
                        <Badge className={cn('text-lg px-4 py-2', scoreGrade?.color)}>
                          Grade {lead.score.grade}
                        </Badge>
                        <div>
                          <p className="font-medium">{scoreGrade?.label}</p>
                          <p className="text-sm text-muted-foreground">
                            Last updated: {formatDateTime(lead.score.last_updated)}
                          </p>
                        </div>
                      </div>

                      <Separator />

                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>Demographic Score</span>
                            <span className="font-medium">{lead.score.breakdown.demographic}/25</span>
                          </div>
                          <Progress value={(lead.score.breakdown.demographic / 25) * 100} className="h-2" />
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>Behavioral Score</span>
                            <span className="font-medium">{lead.score.breakdown.behavioral}/25</span>
                          </div>
                          <Progress value={(lead.score.breakdown.behavioral / 25) * 100} className="h-2" />
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>Engagement Score</span>
                            <span className="font-medium">{lead.score.breakdown.engagement}/25</span>
                          </div>
                          <Progress value={(lead.score.breakdown.engagement / 25) * 100} className="h-2" />
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>Intent Score</span>
                            <span className="font-medium">{lead.score.breakdown.intent}/25</span>
                          </div>
                          <Progress value={(lead.score.breakdown.intent / 25) * 100} className="h-2" />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-muted-foreground">No score calculated yet</p>
                      <Button
                        className="mt-4"
                        onClick={() => recalculateScoreMutation.mutate()}
                        disabled={recalculateScoreMutation.isPending}
                      >
                        Calculate Score
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Lead Source */}
          <Card>
            <CardHeader>
              <CardTitle>Source & Attribution</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Lead Source</p>
                <Badge variant="secondary" className="mt-1">
                  {lead.source.replace(/_/g, ' ')}
                </Badge>
              </div>
              {lead.campaign_name && (
                <div>
                  <p className="text-sm text-muted-foreground">Campaign</p>
                  <p className="font-medium">{lead.campaign_name}</p>
                </div>
              )}
              {lead.tags && lead.tags.length > 0 && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Tags</p>
                  <div className="flex flex-wrap gap-1">
                    {lead.tags.map((tag, index) => (
                      <Badge key={index} variant="outline">{tag}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Assignment */}
          <Card>
            <CardHeader>
              <CardTitle>Assignment</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium">
                    {lead.assigned_to?.full_name || 'Unassigned'}
                  </p>
                  {lead.assigned_to?.email && (
                    <p className="text-sm text-muted-foreground">{lead.assigned_to.email}</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Temperature */}
          <Card>
            <CardHeader>
              <CardTitle>Lead Temperature</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                {['HOT', 'WARM', 'COLD'].map((temp) => {
                  const tConfig = temperatureConfig[temp];
                  const isActive = lead.temperature === temp;
                  return (
                    <Button
                      key={temp}
                      variant={isActive ? 'default' : 'outline'}
                      size="sm"
                      className={cn('flex-1', isActive && temp === 'HOT' && 'bg-red-500 hover:bg-red-600')}
                      onClick={() => updateTemperatureMutation.mutate(temp)}
                      disabled={updateTemperatureMutation.isPending}
                    >
                      {tConfig.icon}
                      <span className="ml-1">{tConfig.label}</span>
                    </Button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Key Dates */}
          <Card>
            <CardHeader>
              <CardTitle>Key Dates</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Created</span>
                <span className="text-sm">{formatDate(lead.created_at)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Last Contact</span>
                <span className="text-sm">
                  {lead.last_contacted_at ? formatDate(lead.last_contacted_at) : 'Never'}
                </span>
              </div>
              {lead.next_followup_at && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Next Follow-up</span>
                  <span className="text-sm font-medium text-primary">
                    {formatDateTime(lead.next_followup_at)}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full justify-start">
                <PhoneCall className="mr-2 h-4 w-4" />
                Call Lead
              </Button>
              <Button variant="outline" className="w-full justify-start">
                <Mail className="mr-2 h-4 w-4" />
                Send Email
              </Button>
              <Button variant="outline" className="w-full justify-start">
                <MessageSquare className="mr-2 h-4 w-4" />
                Send WhatsApp
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Qualify Dialog */}
      <Dialog open={qualifyDialog} onOpenChange={setQualifyDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Qualify Lead</DialogTitle>
            <DialogDescription>
              Enter qualification details for this lead
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Expected Value (₹)</Label>
                <Input
                  type="number"
                  value={expectedValue}
                  onChange={(e) => setExpectedValue(e.target.value)}
                  placeholder="0"
                />
              </div>
              <div className="space-y-2">
                <Label>Expected Close Date</Label>
                <Input
                  type="date"
                  value={expectedCloseDate}
                  onChange={(e) => setExpectedCloseDate(e.target.value)}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Budget Min (₹)</Label>
                <Input
                  type="number"
                  value={budgetMin}
                  onChange={(e) => setBudgetMin(e.target.value)}
                  placeholder="0"
                />
              </div>
              <div className="space-y-2">
                <Label>Budget Max (₹)</Label>
                <Input
                  type="number"
                  value={budgetMax}
                  onChange={(e) => setBudgetMax(e.target.value)}
                  placeholder="0"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Requirements</Label>
              <Textarea
                value={requirements}
                onChange={(e) => setRequirements(e.target.value)}
                placeholder="Describe customer requirements..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setQualifyDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => qualifyMutation.mutate()}
              disabled={qualifyMutation.isPending}
            >
              {qualifyMutation.isPending ? 'Qualifying...' : 'Qualify Lead'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Activity Dialog */}
      <Dialog open={activityDialog} onOpenChange={setActivityDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Log Activity</DialogTitle>
            <DialogDescription>
              Record an interaction with this lead
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Activity Type</Label>
              <Select value={activityType} onValueChange={setActivityType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CALL">Phone Call</SelectItem>
                  <SelectItem value="EMAIL">Email</SelectItem>
                  <SelectItem value="MEETING">Meeting</SelectItem>
                  <SelectItem value="WHATSAPP">WhatsApp</SelectItem>
                  <SelectItem value="SMS">SMS</SelectItem>
                  <SelectItem value="NOTE">Note</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Title *</Label>
              <Input
                value={activityTitle}
                onChange={(e) => setActivityTitle(e.target.value)}
                placeholder="e.g., Initial discovery call"
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={activityDescription}
                onChange={(e) => setActivityDescription(e.target.value)}
                placeholder="Details of the interaction..."
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label>Outcome</Label>
              <Input
                value={activityOutcome}
                onChange={(e) => setActivityOutcome(e.target.value)}
                placeholder="e.g., Scheduled demo for next week"
              />
            </div>
            {(activityType === 'CALL' || activityType === 'MEETING') && (
              <div className="space-y-2">
                <Label>Duration (minutes)</Label>
                <Input
                  type="number"
                  value={activityDuration}
                  onChange={(e) => setActivityDuration(e.target.value)}
                  placeholder="0"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setActivityDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => addActivityMutation.mutate()}
              disabled={!activityTitle || addActivityMutation.isPending}
            >
              {addActivityMutation.isPending ? 'Logging...' : 'Log Activity'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Convert Dialog */}
      <Dialog open={convertDialog} onOpenChange={setConvertDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Convert to Customer</DialogTitle>
            <DialogDescription>
              This will create a new customer record and mark the lead as won.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="p-4 bg-muted rounded-lg">
              <p className="font-medium">{lead.name}</p>
              <p className="text-sm text-muted-foreground">{lead.phone}</p>
              {lead.email && <p className="text-sm text-muted-foreground">{lead.email}</p>}
            </div>
            <p className="text-sm text-muted-foreground">
              A new customer will be created with the lead&apos;s contact information. You can then create orders for this customer.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConvertDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => convertMutation.mutate()}
              disabled={convertMutation.isPending}
            >
              {convertMutation.isPending ? 'Converting...' : 'Convert to Customer'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Lost Dialog */}
      <Dialog open={lostDialog} onOpenChange={setLostDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Mark as Lost</DialogTitle>
            <DialogDescription>
              Please provide a reason for losing this lead
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Lost Reason *</Label>
              <Select value={lostReason} onValueChange={setLostReason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a reason" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="BUDGET">Budget constraints</SelectItem>
                  <SelectItem value="COMPETITOR">Chose competitor</SelectItem>
                  <SelectItem value="NO_RESPONSE">No response</SelectItem>
                  <SelectItem value="NOT_INTERESTED">Not interested</SelectItem>
                  <SelectItem value="TIMING">Bad timing</SelectItem>
                  <SelectItem value="REQUIREMENTS_NOT_MET">Requirements not met</SelectItem>
                  <SelectItem value="OTHER">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLostDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => updateStatusMutation.mutate({ status: 'LOST', lostReason })}
              disabled={!lostReason || updateStatusMutation.isPending}
            >
              {updateStatusMutation.isPending ? 'Updating...' : 'Mark as Lost'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Follow-up Dialog */}
      <Dialog open={followupDialog} onOpenChange={setFollowupDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Schedule Follow-up</DialogTitle>
            <DialogDescription>
              Set a reminder to follow up with this lead
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Follow-up Date & Time *</Label>
              <Input
                type="datetime-local"
                value={followupDate}
                onChange={(e) => setFollowupDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={followupNotes}
                onChange={(e) => setFollowupNotes(e.target.value)}
                placeholder="What to discuss in the follow-up..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFollowupDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => scheduleFollowupMutation.mutate()}
              disabled={!followupDate || scheduleFollowupMutation.isPending}
            >
              {scheduleFollowupMutation.isPending ? 'Scheduling...' : 'Schedule'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
