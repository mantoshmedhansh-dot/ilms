'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Wrench,
  ArrowLeft,
  User,
  Phone,
  MapPin,
  Calendar,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  UserPlus,
  Play,
  Pause,
  Package,
  Star,
  MessageSquare,
  History,
  FileText,
  Send,
  Navigation,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
import { ServiceRequest, ServiceRequestStatus } from '@/types';
import { formatDate, formatDateTime, cn } from '@/lib/utils';

// Extended interfaces
interface Technician {
  id: string;
  name: string;
  phone: string;
  email?: string;
  skill_level: 'TRAINEE' | 'JUNIOR' | 'SENIOR' | 'EXPERT';
  rating?: number;
  total_jobs?: number;
  available: boolean;
  current_location?: { lat: number; lng: number };
}

interface ServiceHistory {
  id: string;
  action: string;
  status: string;
  notes?: string;
  performed_by?: string;
  created_at: string;
}

interface PartsUsed {
  id: string;
  part_name: string;
  part_code: string;
  quantity: number;
  unit_price: number;
  is_warranty: boolean;
}

interface ServiceFeedback {
  rating: number;
  service_quality: number;
  technician_behavior: number;
  issue_resolved: boolean;
  comments?: string;
  would_recommend: boolean;
  submitted_at: string;
}

interface ExtendedServiceRequest extends ServiceRequest {
  address?: {
    line1: string;
    line2?: string;
    city: string;
    state: string;
    pincode: string;
  };
  installation_id?: string;
  serial_number?: string;
  warranty_status?: 'IN_WARRANTY' | 'OUT_OF_WARRANTY' | 'EXTENDED_WARRANTY';
  warranty_expiry?: string;
  reported_issue?: string;
  diagnosis?: string;
  resolution?: string;
  estimated_cost?: number;
  actual_cost?: number;
  scheduled_time_slot?: string;
  technician?: Technician;
  parts_used?: PartsUsed[];
  history?: ServiceHistory[];
  feedback?: ServiceFeedback;
  sla_due_at?: string;
  sla_breached?: boolean;
  visit_count?: number;
  job_started_at?: string;
  job_completed_at?: string;
  customer_signature_url?: string;
  job_photos?: string[];
}

// Status configuration
const statusConfig: Record<ServiceRequestStatus, { color: string; icon: React.ReactNode; label: string }> = {
  DRAFT: { color: 'bg-gray-100 text-gray-800', icon: <FileText className="h-4 w-4" />, label: 'Draft' },
  PENDING: { color: 'bg-yellow-100 text-yellow-800', icon: <Clock className="h-4 w-4" />, label: 'Pending' },
  ASSIGNED: { color: 'bg-blue-100 text-blue-800', icon: <UserPlus className="h-4 w-4" />, label: 'Assigned' },
  SCHEDULED: { color: 'bg-purple-100 text-purple-800', icon: <Calendar className="h-4 w-4" />, label: 'Scheduled' },
  EN_ROUTE: { color: 'bg-indigo-100 text-indigo-800', icon: <Navigation className="h-4 w-4" />, label: 'En Route' },
  IN_PROGRESS: { color: 'bg-cyan-100 text-cyan-800', icon: <Wrench className="h-4 w-4" />, label: 'In Progress' },
  PARTS_REQUIRED: { color: 'bg-orange-100 text-orange-800', icon: <Package className="h-4 w-4" />, label: 'Parts Required' },
  ON_HOLD: { color: 'bg-amber-100 text-amber-800', icon: <Pause className="h-4 w-4" />, label: 'On Hold' },
  COMPLETED: { color: 'bg-green-100 text-green-800', icon: <CheckCircle className="h-4 w-4" />, label: 'Completed' },
  CLOSED: { color: 'bg-gray-100 text-gray-800', icon: <CheckCircle className="h-4 w-4" />, label: 'Closed' },
  CANCELLED: { color: 'bg-red-100 text-red-800', icon: <XCircle className="h-4 w-4" />, label: 'Cancelled' },
  REOPENED: { color: 'bg-rose-100 text-rose-800', icon: <AlertTriangle className="h-4 w-4" />, label: 'Reopened' },
};

// Status workflow actions
const statusActions: Record<string, { next: string; label: string; icon: React.ReactNode }[]> = {
  PENDING: [
    { next: 'ASSIGNED', label: 'Assign Technician', icon: <UserPlus className="h-4 w-4" /> },
    { next: 'CANCELLED', label: 'Cancel Request', icon: <XCircle className="h-4 w-4" /> },
  ],
  ASSIGNED: [
    { next: 'SCHEDULED', label: 'Schedule Visit', icon: <Calendar className="h-4 w-4" /> },
    { next: 'PENDING', label: 'Unassign', icon: <UserPlus className="h-4 w-4" /> },
  ],
  SCHEDULED: [
    { next: 'EN_ROUTE', label: 'Start Journey', icon: <Navigation className="h-4 w-4" /> },
    { next: 'ASSIGNED', label: 'Reschedule', icon: <Calendar className="h-4 w-4" /> },
  ],
  EN_ROUTE: [
    { next: 'IN_PROGRESS', label: 'Start Service', icon: <Play className="h-4 w-4" /> },
  ],
  IN_PROGRESS: [
    { next: 'COMPLETED', label: 'Complete Service', icon: <CheckCircle className="h-4 w-4" /> },
    { next: 'PARTS_REQUIRED', label: 'Parts Needed', icon: <Package className="h-4 w-4" /> },
    { next: 'ON_HOLD', label: 'Put On Hold', icon: <Pause className="h-4 w-4" /> },
  ],
  PARTS_REQUIRED: [
    { next: 'IN_PROGRESS', label: 'Resume Service', icon: <Play className="h-4 w-4" /> },
    { next: 'SCHEDULED', label: 'Schedule Next Visit', icon: <Calendar className="h-4 w-4" /> },
  ],
  ON_HOLD: [
    { next: 'IN_PROGRESS', label: 'Resume Service', icon: <Play className="h-4 w-4" /> },
    { next: 'CANCELLED', label: 'Cancel Request', icon: <XCircle className="h-4 w-4" /> },
  ],
  COMPLETED: [
    { next: 'CLOSED', label: 'Close Request', icon: <CheckCircle className="h-4 w-4" /> },
    { next: 'REOPENED', label: 'Reopen Issue', icon: <AlertTriangle className="h-4 w-4" /> },
  ],
  REOPENED: [
    { next: 'ASSIGNED', label: 'Reassign', icon: <UserPlus className="h-4 w-4" /> },
  ],
};

const priorityColors: Record<string, string> = {
  LOW: 'bg-gray-100 text-gray-800',
  NORMAL: 'bg-blue-100 text-blue-800',
  HIGH: 'bg-orange-100 text-orange-800',
  URGENT: 'bg-red-100 text-red-800 animate-pulse',
  CRITICAL: 'bg-purple-100 text-purple-800 animate-pulse',
};

const typeLabels: Record<string, string> = {
  INSTALLATION: 'Installation',
  WARRANTY_REPAIR: 'Warranty Repair',
  PAID_REPAIR: 'Paid Repair',
  AMC_SERVICE: 'AMC Service',
  DEMO: 'Demo',
  PREVENTIVE_MAINTENANCE: 'Preventive Maintenance',
  COMPLAINT: 'Complaint',
  FILTER_CHANGE: 'Filter Change',
  INSPECTION: 'Inspection',
  UNINSTALLATION: 'Uninstallation',
};

// API functions
const serviceRequestApi = {
  getById: async (id: string): Promise<ExtendedServiceRequest> => {
    const { data } = await apiClient.get(`/service-requests/${id}`);
    return data;
  },
  updateStatus: async (id: string, status: string, notes?: string) => {
    const { data } = await apiClient.put(`/service-requests/${id}/status`, { status, notes });
    return data;
  },
  assignTechnician: async (id: string, technicianId: string, scheduledDate?: string, timeSlot?: string) => {
    const { data } = await apiClient.post(`/service-requests/${id}/assign`, {
      technician_id: technicianId,
      scheduled_date: scheduledDate,
      time_slot: timeSlot,
    });
    return data;
  },
  startService: async (id: string) => {
    const { data } = await apiClient.post(`/service-requests/${id}/start`);
    return data;
  },
  completeService: async (id: string, completionData: {
    diagnosis: string;
    resolution: string;
    parts_used?: Array<{ part_id: string; quantity: number; is_warranty: boolean }>;
    actual_cost?: number;
    customer_signature?: string;
    photos?: string[];
  }) => {
    const { data } = await apiClient.post(`/service-requests/${id}/complete`, completionData);
    return data;
  },
  addParts: async (id: string, parts: Array<{ part_id: string; quantity: number; is_warranty: boolean }>) => {
    const { data } = await apiClient.post(`/service-requests/${id}/parts`, { parts });
    return data;
  },
  submitFeedback: async (id: string, feedback: Partial<ServiceFeedback>) => {
    const { data } = await apiClient.post(`/service-requests/${id}/feedback`, feedback);
    return data;
  },
  getHistory: async (id: string): Promise<ServiceHistory[]> => {
    const { data } = await apiClient.get(`/service-requests/${id}/history`);
    return data;
  },
};

const techniciansApi = {
  getAvailable: async (pincode?: string): Promise<Technician[]> => {
    const { data } = await apiClient.get('/technicians/available', { params: { pincode } });
    return data;
  },
};

export default function ServiceRequestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const id = params.id as string;

  // Dialogs
  const [assignDialog, setAssignDialog] = useState(false);
  const [scheduleDialog, setScheduleDialog] = useState(false);
  const [completeDialog, setCompleteDialog] = useState(false);
  const [partsDialog, setPartsDialog] = useState(false);
  const [feedbackDialog, setFeedbackDialog] = useState(false);
  const [statusNotes, setStatusNotes] = useState('');

  // Form states
  const [selectedTechnician, setSelectedTechnician] = useState('');
  const [scheduledDate, setScheduledDate] = useState('');
  const [timeSlot, setTimeSlot] = useState('');
  const [diagnosis, setDiagnosis] = useState('');
  const [resolution, setResolution] = useState('');
  const [actualCost, setActualCost] = useState('');

  // Feedback form
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [serviceQuality, setServiceQuality] = useState(0);
  const [techBehavior, setTechBehavior] = useState(0);
  const [issueResolved, setIssueResolved] = useState(false);
  const [feedbackComments, setFeedbackComments] = useState('');
  const [wouldRecommend, setWouldRecommend] = useState(false);

  // Queries
  const { data: request, isLoading, error } = useQuery({
    queryKey: ['service-request', id],
    queryFn: () => serviceRequestApi.getById(id),
  });

  const { data: technicians = [] } = useQuery({
    queryKey: ['available-technicians', request?.address?.pincode],
    queryFn: () => techniciansApi.getAvailable(request?.address?.pincode),
    enabled: assignDialog,
  });

  // Mutations
  const updateStatusMutation = useMutation({
    mutationFn: ({ status, notes }: { status: string; notes?: string }) =>
      serviceRequestApi.updateStatus(id, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['service-request', id] });
      toast.success('Status updated successfully');
      setStatusNotes('');
    },
    onError: () => toast.error('Failed to update status'),
  });

  const assignMutation = useMutation({
    mutationFn: () => serviceRequestApi.assignTechnician(id, selectedTechnician, scheduledDate, timeSlot),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['service-request', id] });
      toast.success('Technician assigned successfully');
      setAssignDialog(false);
      setSelectedTechnician('');
    },
    onError: () => toast.error('Failed to assign technician'),
  });

  const startServiceMutation = useMutation({
    mutationFn: () => serviceRequestApi.startService(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['service-request', id] });
      toast.success('Service started');
    },
    onError: () => toast.error('Failed to start service'),
  });

  const completeServiceMutation = useMutation({
    mutationFn: () => serviceRequestApi.completeService(id, {
      diagnosis,
      resolution,
      actual_cost: actualCost ? parseFloat(actualCost) : undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['service-request', id] });
      toast.success('Service completed successfully');
      setCompleteDialog(false);
    },
    onError: () => toast.error('Failed to complete service'),
  });

  const submitFeedbackMutation = useMutation({
    mutationFn: () => serviceRequestApi.submitFeedback(id, {
      rating: feedbackRating,
      service_quality: serviceQuality,
      technician_behavior: techBehavior,
      issue_resolved: issueResolved,
      comments: feedbackComments || undefined,
      would_recommend: wouldRecommend,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['service-request', id] });
      toast.success('Feedback submitted successfully');
      setFeedbackDialog(false);
    },
    onError: () => toast.error('Failed to submit feedback'),
  });

  const handleStatusChange = (status: string) => {
    if (status === 'ASSIGNED') {
      setAssignDialog(true);
    } else if (status === 'SCHEDULED') {
      setScheduleDialog(true);
    } else if (status === 'COMPLETED') {
      setCompleteDialog(true);
    } else if (status === 'IN_PROGRESS' && request?.status === 'EN_ROUTE') {
      startServiceMutation.mutate();
    } else {
      updateStatusMutation.mutate({ status, notes: statusNotes });
    }
  };

  // Star rating component
  const StarRating = ({ value, onChange, disabled = false }: { value: number; onChange: (v: number) => void; disabled?: boolean }) => (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={disabled}
          onClick={() => onChange(star)}
          className={cn(
            'transition-colors',
            star <= value ? 'text-yellow-500' : 'text-gray-300',
            !disabled && 'hover:text-yellow-400'
          )}
        >
          <Star className="h-6 w-6 fill-current" />
        </button>
      ))}
    </div>
  );

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

  if (error || !request) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold">Service Request Not Found</h2>
        <p className="text-muted-foreground mt-2">The requested service request could not be found.</p>
        <Button variant="outline" className="mt-4" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Go Back
        </Button>
      </div>
    );
  }

  const config = statusConfig[request.status];
  const actions = statusActions[request.status] || [];
  const canCollectFeedback = request.status === 'COMPLETED' && !request.feedback;

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
              <h1 className="text-2xl font-bold">{request.request_number}</h1>
              <Badge className={config.color}>
                {config.icon}
                <span className="ml-1">{config.label}</span>
              </Badge>
              <Badge className={priorityColors[request.priority]}>
                {request.priority}
              </Badge>
              {request.sla_breached && (
                <Badge variant="destructive" className="animate-pulse">
                  SLA Breached
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground mt-1">
              {typeLabels[request.type]} • Created {formatDateTime(request.created_at)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {canCollectFeedback && (
            <Button variant="outline" onClick={() => setFeedbackDialog(true)}>
              <Star className="mr-2 h-4 w-4" />
              Collect Feedback
            </Button>
          )}
          {actions.map((action) => (
            <Button
              key={action.next}
              variant={action.next === 'CANCELLED' ? 'destructive' : 'default'}
              onClick={() => handleStatusChange(action.next)}
              disabled={updateStatusMutation.isPending}
            >
              {action.icon}
              <span className="ml-2">{action.label}</span>
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <Tabs defaultValue="details" className="space-y-4">
            <TabsList>
              <TabsTrigger value="details">Details</TabsTrigger>
              <TabsTrigger value="diagnosis">Diagnosis & Resolution</TabsTrigger>
              <TabsTrigger value="parts">Parts Used</TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
              {request.feedback && <TabsTrigger value="feedback">Feedback</TabsTrigger>}
            </TabsList>

            <TabsContent value="details" className="space-y-6">
              {/* Issue Details */}
              <Card>
                <CardHeader>
                  <CardTitle>Issue Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="text-muted-foreground">Reported Issue</Label>
                    <p className="mt-1">{request.reported_issue || request.description || 'No description provided'}</p>
                  </div>
                  {request.product && (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label className="text-muted-foreground">Product</Label>
                        <p className="mt-1 font-medium">{request.product.name}</p>
                        <p className="text-sm text-muted-foreground">SKU: {request.product.sku}</p>
                      </div>
                      {request.serial_number && (
                        <div>
                          <Label className="text-muted-foreground">Serial Number</Label>
                          <p className="mt-1 font-mono">{request.serial_number}</p>
                        </div>
                      )}
                    </div>
                  )}
                  {request.warranty_status && (
                    <div className="flex items-center gap-4">
                      <div>
                        <Label className="text-muted-foreground">Warranty Status</Label>
                        <Badge
                          variant={request.warranty_status === 'IN_WARRANTY' ? 'default' : 'secondary'}
                          className="mt-1"
                        >
                          {request.warranty_status.replace(/_/g, ' ')}
                        </Badge>
                      </div>
                      {request.warranty_expiry && (
                        <div>
                          <Label className="text-muted-foreground">Warranty Expiry</Label>
                          <p className="mt-1">{formatDate(request.warranty_expiry)}</p>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Schedule Info */}
              {(request.scheduled_date || request.scheduled_time_slot) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Calendar className="h-5 w-5" />
                      Schedule
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label className="text-muted-foreground">Scheduled Date</Label>
                        <p className="mt-1 font-medium">{formatDate(request.scheduled_date!)}</p>
                      </div>
                      {request.scheduled_time_slot && (
                        <div>
                          <Label className="text-muted-foreground">Time Slot</Label>
                          <p className="mt-1">{request.scheduled_time_slot}</p>
                        </div>
                      )}
                      {request.sla_due_at && (
                        <div>
                          <Label className="text-muted-foreground">SLA Due</Label>
                          <p className={cn(
                            'mt-1',
                            request.sla_breached && 'text-destructive font-medium'
                          )}>
                            {formatDateTime(request.sla_due_at)}
                          </p>
                        </div>
                      )}
                      {request.visit_count && request.visit_count > 1 && (
                        <div>
                          <Label className="text-muted-foreground">Visit Count</Label>
                          <Badge variant="secondary" className="mt-1">{request.visit_count} visits</Badge>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Job Timing */}
              {(request.job_started_at || request.job_completed_at) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Clock className="h-5 w-5" />
                      Job Timing
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4">
                      {request.job_started_at && (
                        <div>
                          <Label className="text-muted-foreground">Started At</Label>
                          <p className="mt-1">{formatDateTime(request.job_started_at)}</p>
                        </div>
                      )}
                      {request.job_completed_at && (
                        <div>
                          <Label className="text-muted-foreground">Completed At</Label>
                          <p className="mt-1">{formatDateTime(request.job_completed_at)}</p>
                        </div>
                      )}
                      {request.job_started_at && request.job_completed_at && (
                        <div>
                          <Label className="text-muted-foreground">Duration</Label>
                          <p className="mt-1 font-medium">
                            {Math.round(
                              (new Date(request.job_completed_at).getTime() -
                                new Date(request.job_started_at).getTime()) /
                                60000
                            )}{' '}
                            minutes
                          </p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="diagnosis" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Diagnosis & Resolution</CardTitle>
                  <CardDescription>Technical findings and resolution provided by the technician</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="text-muted-foreground">Diagnosis</Label>
                    <p className="mt-1">{request.diagnosis || 'Not yet diagnosed'}</p>
                  </div>
                  <Separator />
                  <div>
                    <Label className="text-muted-foreground">Resolution</Label>
                    <p className="mt-1">{request.resolution || 'Not yet resolved'}</p>
                  </div>
                  {(request.estimated_cost || request.actual_cost) && (
                    <>
                      <Separator />
                      <div className="grid grid-cols-2 gap-4">
                        {request.estimated_cost && (
                          <div>
                            <Label className="text-muted-foreground">Estimated Cost</Label>
                            <p className="mt-1 font-medium">₹{request.estimated_cost.toLocaleString()}</p>
                          </div>
                        )}
                        {request.actual_cost && (
                          <div>
                            <Label className="text-muted-foreground">Actual Cost</Label>
                            <p className="mt-1 font-medium text-green-600">
                              ₹{request.actual_cost.toLocaleString()}
                            </p>
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>

              {/* Job Photos */}
              {request.job_photos && request.job_photos.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Job Photos</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4">
                      {request.job_photos.map((photo, index) => (
                        <div key={index} className="aspect-video bg-muted rounded-lg overflow-hidden">
                          <img src={photo} alt={`Job photo ${index + 1}`} className="w-full h-full object-cover" />
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="parts" className="space-y-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle>Parts Used</CardTitle>
                    <CardDescription>Spare parts consumed during service</CardDescription>
                  </div>
                  {request.status === 'IN_PROGRESS' && (
                    <Button variant="outline" onClick={() => setPartsDialog(true)}>
                      <Package className="mr-2 h-4 w-4" />
                      Add Parts
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {request.parts_used && request.parts_used.length > 0 ? (
                    <div className="space-y-4">
                      {request.parts_used.map((part) => (
                        <div
                          key={part.id}
                          className="flex items-center justify-between p-4 border rounded-lg"
                        >
                          <div>
                            <p className="font-medium">{part.part_name}</p>
                            <p className="text-sm text-muted-foreground">Code: {part.part_code}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium">Qty: {part.quantity}</p>
                            <p className="text-sm text-muted-foreground">
                              {part.is_warranty ? (
                                <Badge variant="secondary">Warranty</Badge>
                              ) : (
                                `₹${part.unit_price.toLocaleString()}`
                              )}
                            </p>
                          </div>
                        </div>
                      ))}
                      <Separator />
                      <div className="flex justify-between font-medium">
                        <span>Total Parts Cost</span>
                        <span>
                          ₹
                          {request.parts_used
                            .filter((p) => !p.is_warranty)
                            .reduce((sum, p) => sum + p.unit_price * p.quantity, 0)
                            .toLocaleString()}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-8">No parts used yet</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="history" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <History className="h-5 w-5" />
                    Activity History
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="relative space-y-0">
                    {request.history && request.history.length > 0 ? (
                      request.history.map((entry, index) => (
                        <div key={entry.id} className="flex gap-4 pb-8 last:pb-0">
                          <div className="relative">
                            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                              {statusConfig[entry.status as ServiceRequestStatus]?.icon || (
                                <FileText className="h-4 w-4" />
                              )}
                            </div>
                            {index < request.history!.length - 1 && (
                              <div className="absolute top-10 left-1/2 -translate-x-1/2 w-0.5 h-full bg-border" />
                            )}
                          </div>
                          <div className="flex-1 pt-1">
                            <div className="flex items-center justify-between">
                              <p className="font-medium">{entry.action}</p>
                              <span className="text-sm text-muted-foreground">
                                {formatDateTime(entry.created_at)}
                              </span>
                            </div>
                            {entry.notes && (
                              <p className="text-sm text-muted-foreground mt-1">{entry.notes}</p>
                            )}
                            {entry.performed_by && (
                              <p className="text-xs text-muted-foreground mt-1">
                                By: {entry.performed_by}
                              </p>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-muted-foreground text-center py-8">No history available</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {request.feedback && (
              <TabsContent value="feedback" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Star className="h-5 w-5" />
                      Customer Feedback
                    </CardTitle>
                    <CardDescription>
                      Submitted {formatDateTime(request.feedback.submitted_at)}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="grid grid-cols-3 gap-6">
                      <div className="text-center p-4 bg-muted rounded-lg">
                        <p className="text-sm text-muted-foreground mb-2">Overall Rating</p>
                        <div className="flex justify-center">
                          <StarRating value={request.feedback.rating} onChange={() => {}} disabled />
                        </div>
                        <p className="text-2xl font-bold mt-2">{request.feedback.rating}/5</p>
                      </div>
                      <div className="text-center p-4 bg-muted rounded-lg">
                        <p className="text-sm text-muted-foreground mb-2">Service Quality</p>
                        <div className="flex justify-center">
                          <StarRating value={request.feedback.service_quality} onChange={() => {}} disabled />
                        </div>
                        <p className="text-2xl font-bold mt-2">{request.feedback.service_quality}/5</p>
                      </div>
                      <div className="text-center p-4 bg-muted rounded-lg">
                        <p className="text-sm text-muted-foreground mb-2">Technician Behavior</p>
                        <div className="flex justify-center">
                          <StarRating value={request.feedback.technician_behavior} onChange={() => {}} disabled />
                        </div>
                        <p className="text-2xl font-bold mt-2">{request.feedback.technician_behavior}/5</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex items-center gap-3 p-4 border rounded-lg">
                        {request.feedback.issue_resolved ? (
                          <ThumbsUp className="h-8 w-8 text-green-600" />
                        ) : (
                          <ThumbsDown className="h-8 w-8 text-red-600" />
                        )}
                        <div>
                          <p className="font-medium">Issue Resolved</p>
                          <p className="text-sm text-muted-foreground">
                            {request.feedback.issue_resolved ? 'Yes, issue was resolved' : 'No, issue not resolved'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 p-4 border rounded-lg">
                        {request.feedback.would_recommend ? (
                          <ThumbsUp className="h-8 w-8 text-green-600" />
                        ) : (
                          <ThumbsDown className="h-8 w-8 text-red-600" />
                        )}
                        <div>
                          <p className="font-medium">Would Recommend</p>
                          <p className="text-sm text-muted-foreground">
                            {request.feedback.would_recommend ? 'Yes, would recommend' : 'No, would not recommend'}
                          </p>
                        </div>
                      </div>
                    </div>

                    {request.feedback.comments && (
                      <div>
                        <Label className="text-muted-foreground">Comments</Label>
                        <p className="mt-1 p-4 bg-muted rounded-lg italic">
                          &ldquo;{request.feedback.comments}&rdquo;
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            )}
          </Tabs>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Customer Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Customer
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="font-medium">{request.customer?.name || 'Unknown'}</p>
                <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                  <Phone className="h-4 w-4" />
                  {request.customer?.phone || 'N/A'}
                </div>
              </div>
              {request.address && (
                <div>
                  <div className="flex items-start gap-2 text-sm">
                    <MapPin className="h-4 w-4 mt-0.5 text-muted-foreground" />
                    <div>
                      <p>{request.address.line1}</p>
                      {request.address.line2 && <p>{request.address.line2}</p>}
                      <p>
                        {request.address.city}, {request.address.state} - {request.address.pincode}
                      </p>
                    </div>
                  </div>
                </div>
              )}
              <Button variant="outline" className="w-full" asChild>
                <a href={`/crm/customers/${request.customer_id}`}>
                  View Customer Profile
                </a>
              </Button>
            </CardContent>
          </Card>

          {/* Technician Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Wrench className="h-5 w-5" />
                Assigned Technician
              </CardTitle>
            </CardHeader>
            <CardContent>
              {request.technician ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <User className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-medium">{request.technician.name}</p>
                      <Badge variant="secondary" className="text-xs">
                        {request.technician.skill_level}
                      </Badge>
                    </div>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                      {request.technician.phone}
                    </div>
                    {request.technician.rating && (
                      <div className="flex items-center gap-2">
                        <Star className="h-4 w-4 text-yellow-500" />
                        {request.technician.rating.toFixed(1)} ({request.technician.total_jobs} jobs)
                      </div>
                    )}
                  </div>
                  {request.status === 'ASSIGNED' && (
                    <Button variant="outline" className="w-full" onClick={() => setScheduleDialog(true)}>
                      <Calendar className="mr-2 h-4 w-4" />
                      Schedule Visit
                    </Button>
                  )}
                </div>
              ) : (
                <div className="text-center py-4">
                  <UserPlus className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No technician assigned</p>
                  {request.status === 'PENDING' && (
                    <Button className="mt-4" onClick={() => setAssignDialog(true)}>
                      <UserPlus className="mr-2 h-4 w-4" />
                      Assign Now
                    </Button>
                  )}
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
              <Button variant="outline" className="w-full justify-start" asChild>
                <a href={`/service/installations?customer_id=${request.customer_id}`}>
                  <Wrench className="mr-2 h-4 w-4" />
                  View Installations
                </a>
              </Button>
              {request.installation_id && (
                <Button variant="outline" className="w-full justify-start" asChild>
                  <a href={`/service/installations/${request.installation_id}`}>
                    <FileText className="mr-2 h-4 w-4" />
                    View Installation Record
                  </a>
                </Button>
              )}
              <Button variant="outline" className="w-full justify-start">
                <MessageSquare className="mr-2 h-4 w-4" />
                Send SMS Update
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Assign Technician Dialog */}
      <Dialog open={assignDialog} onOpenChange={setAssignDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Assign Technician</DialogTitle>
            <DialogDescription>
              Select a technician to handle this service request
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Available Technicians</Label>
              <Select value={selectedTechnician} onValueChange={setSelectedTechnician}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a technician" />
                </SelectTrigger>
                <SelectContent>
                  {technicians.length > 0 ? (
                    technicians.map((tech) => (
                      <SelectItem key={tech.id} value={tech.id}>
                        <div className="flex items-center gap-2">
                          <span>{tech.name}</span>
                          <Badge variant="secondary" className="text-xs">{tech.skill_level}</Badge>
                          {tech.rating && (
                            <span className="text-xs text-muted-foreground">
                              ⭐ {tech.rating.toFixed(1)}
                            </span>
                          )}
                        </div>
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="none" disabled>
                      No technicians available
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Schedule Date (Optional)</Label>
              <Input
                type="date"
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
              />
            </div>
            <div className="space-y-2">
              <Label>Time Slot (Optional)</Label>
              <Select value={timeSlot} onValueChange={setTimeSlot}>
                <SelectTrigger>
                  <SelectValue placeholder="Select time slot" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="09:00-12:00">Morning (9 AM - 12 PM)</SelectItem>
                  <SelectItem value="12:00-15:00">Afternoon (12 PM - 3 PM)</SelectItem>
                  <SelectItem value="15:00-18:00">Evening (3 PM - 6 PM)</SelectItem>
                  <SelectItem value="18:00-21:00">Night (6 PM - 9 PM)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => assignMutation.mutate()}
              disabled={!selectedTechnician || assignMutation.isPending}
            >
              {assignMutation.isPending ? 'Assigning...' : 'Assign Technician'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Schedule Dialog */}
      <Dialog open={scheduleDialog} onOpenChange={setScheduleDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Schedule Visit</DialogTitle>
            <DialogDescription>
              Set the date and time for the service visit
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Visit Date</Label>
              <Input
                type="date"
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
              />
            </div>
            <div className="space-y-2">
              <Label>Time Slot</Label>
              <Select value={timeSlot} onValueChange={setTimeSlot}>
                <SelectTrigger>
                  <SelectValue placeholder="Select time slot" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="09:00-12:00">Morning (9 AM - 12 PM)</SelectItem>
                  <SelectItem value="12:00-15:00">Afternoon (12 PM - 3 PM)</SelectItem>
                  <SelectItem value="15:00-18:00">Evening (3 PM - 6 PM)</SelectItem>
                  <SelectItem value="18:00-21:00">Night (6 PM - 9 PM)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setScheduleDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                updateStatusMutation.mutate({ status: 'SCHEDULED' });
                setScheduleDialog(false);
              }}
              disabled={!scheduledDate || updateStatusMutation.isPending}
            >
              Schedule Visit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Complete Service Dialog */}
      <Dialog open={completeDialog} onOpenChange={setCompleteDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Complete Service</DialogTitle>
            <DialogDescription>
              Enter the diagnosis and resolution details
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Diagnosis *</Label>
              <Textarea
                value={diagnosis}
                onChange={(e) => setDiagnosis(e.target.value)}
                placeholder="Describe the issue found..."
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label>Resolution *</Label>
              <Textarea
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                placeholder="Describe the action taken..."
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label>Service Charges (if applicable)</Label>
              <Input
                type="number"
                value={actualCost}
                onChange={(e) => setActualCost(e.target.value)}
                placeholder="0.00"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCompleteDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => completeServiceMutation.mutate()}
              disabled={!diagnosis || !resolution || completeServiceMutation.isPending}
            >
              {completeServiceMutation.isPending ? 'Completing...' : 'Complete Service'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Feedback Dialog */}
      <Dialog open={feedbackDialog} onOpenChange={setFeedbackDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Collect Customer Feedback</DialogTitle>
            <DialogDescription>
              Record the customer&apos;s feedback for this service
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6">
            <div className="space-y-2">
              <Label>Overall Rating *</Label>
              <StarRating value={feedbackRating} onChange={setFeedbackRating} />
            </div>
            <div className="space-y-2">
              <Label>Service Quality *</Label>
              <StarRating value={serviceQuality} onChange={setServiceQuality} />
            </div>
            <div className="space-y-2">
              <Label>Technician Behavior *</Label>
              <StarRating value={techBehavior} onChange={setTechBehavior} />
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="issue-resolved"
                checked={issueResolved}
                onCheckedChange={(checked) => setIssueResolved(checked as boolean)}
              />
              <Label htmlFor="issue-resolved">Issue was resolved satisfactorily</Label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="would-recommend"
                checked={wouldRecommend}
                onCheckedChange={(checked) => setWouldRecommend(checked as boolean)}
              />
              <Label htmlFor="would-recommend">Would recommend to others</Label>
            </div>
            <div className="space-y-2">
              <Label>Additional Comments</Label>
              <Textarea
                value={feedbackComments}
                onChange={(e) => setFeedbackComments(e.target.value)}
                placeholder="Any additional feedback..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFeedbackDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => submitFeedbackMutation.mutate()}
              disabled={!feedbackRating || !serviceQuality || !techBehavior || submitFeedbackMutation.isPending}
            >
              {submitFeedbackMutation.isPending ? 'Submitting...' : 'Submit Feedback'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
