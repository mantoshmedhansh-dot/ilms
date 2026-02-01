'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft, Wrench, User, MapPin, Calendar, Clock, CheckCircle, XCircle,
  AlertTriangle, Phone, Camera, FileText, ClipboardCheck, Star,
  Droplets, ThermometerSun, Package, UserCheck, Play, Pause
} from 'lucide-react';
import { toast } from 'sonner';
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
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatDate } from '@/lib/utils';

interface Technician {
  id: string;
  name: string;
  phone: string;
  skill_level: string;
}

interface Installation {
  id: string;
  installation_number: string;
  order_id: string;
  order_number: string;
  shipment_id?: string;
  customer: {
    id: string;
    name: string;
    phone: string;
    email?: string;
  };
  address: {
    address_line1: string;
    address_line2?: string;
    city: string;
    state: string;
    pincode: string;
    landmark?: string;
  };
  product: {
    id: string;
    name: string;
    sku: string;
    model?: string;
  };
  serial_numbers: string[];
  status: 'NEW' | 'SCHEDULED' | 'ASSIGNED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  technician?: Technician;
  franchisee_id?: string;
  franchisee_name?: string;
  scheduled_date?: string;
  scheduled_time_slot?: string;
  started_at?: string;
  completed_at?: string;
  // Pre-installation checklist
  pre_checklist?: {
    site_ready: boolean;
    power_available: boolean;
    water_connection_available: boolean;
    space_adequate: boolean;
    notes?: string;
  };
  // Post-installation data
  post_data?: {
    tds_input?: number;
    tds_output?: number;
    flow_rate?: number;
    pressure?: number;
    accessories_used?: string[];
    photos?: string[];
    customer_signature?: string;
    demo_given: boolean;
    notes?: string;
  };
  // Customer feedback
  feedback?: {
    rating: number;
    comments?: string;
    would_recommend: boolean;
  };
  warranty_months: number;
  warranty_start_date?: string;
  warranty_end_date?: string;
  created_at: string;
  updated_at: string;
}

const installationApi = {
  get: async (id: string): Promise<Installation | null> => {
    try {
      const { data } = await apiClient.get(`/installations/${id}`);
      return data;
    } catch {
      return null;
    }
  },
  schedule: async (id: string, data: { scheduled_date: string; scheduled_time_slot: string }) => {
    const { data: result } = await apiClient.post(`/installations/${id}/schedule`, data);
    return result;
  },
  assign: async (id: string, technicianId: string) => {
    const { data } = await apiClient.post(`/installations/${id}/assign`, { technician_id: technicianId });
    return data;
  },
  start: async (id: string) => {
    const { data } = await apiClient.post(`/installations/${id}/start`);
    return data;
  },
  updatePreChecklist: async (id: string, checklist: Installation['pre_checklist']) => {
    const { data } = await apiClient.put(`/installations/${id}/pre-checklist`, checklist);
    return data;
  },
  complete: async (id: string, completionData: {
    tds_input?: number;
    tds_output?: number;
    flow_rate?: number;
    accessories_used?: string[];
    demo_given: boolean;
    notes?: string;
  }) => {
    const { data } = await apiClient.post(`/installations/${id}/complete`, completionData);
    return data;
  },
  recordFeedback: async (id: string, feedback: { rating: number; comments?: string; would_recommend: boolean }) => {
    const { data } = await apiClient.post(`/installations/${id}/feedback`, feedback);
    return data;
  },
  getTechnicians: async (pincode: string): Promise<Technician[]> => {
    try {
      const { data } = await apiClient.get('/technicians', { params: { pincode, available: true } });
      return data.items || [];
    } catch {
      return [];
    }
  },
};

const statusColors: Record<string, string> = {
  NEW: 'bg-blue-100 text-blue-800',
  SCHEDULED: 'bg-purple-100 text-purple-800',
  ASSIGNED: 'bg-indigo-100 text-indigo-800',
  IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
  COMPLETED: 'bg-green-100 text-green-800',
  CANCELLED: 'bg-gray-100 text-gray-600',
};

const timeSlots = [
  { value: '09:00-11:00', label: '9:00 AM - 11:00 AM' },
  { value: '11:00-13:00', label: '11:00 AM - 1:00 PM' },
  { value: '14:00-16:00', label: '2:00 PM - 4:00 PM' },
  { value: '16:00-18:00', label: '4:00 PM - 6:00 PM' },
];

export default function InstallationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const installationId = params.id as string;

  const [isScheduleDialogOpen, setIsScheduleDialogOpen] = useState(false);
  const [isAssignDialogOpen, setIsAssignDialogOpen] = useState(false);
  const [isCompleteDialogOpen, setIsCompleteDialogOpen] = useState(false);
  const [isFeedbackDialogOpen, setIsFeedbackDialogOpen] = useState(false);

  const [scheduleForm, setScheduleForm] = useState({
    scheduled_date: '',
    scheduled_time_slot: '',
  });

  const [selectedTechnician, setSelectedTechnician] = useState('');

  const [preChecklist, setPreChecklist] = useState({
    site_ready: false,
    power_available: false,
    water_connection_available: false,
    space_adequate: false,
    notes: '',
  });

  const [completionForm, setCompletionForm] = useState({
    tds_input: 0,
    tds_output: 0,
    flow_rate: 0,
    accessories_used: [] as string[],
    demo_given: false,
    notes: '',
  });

  const [feedbackForm, setFeedbackForm] = useState({
    rating: 5,
    comments: '',
    would_recommend: true,
  });

  const queryClient = useQueryClient();

  const { data: installation, isLoading } = useQuery({
    queryKey: ['installation', installationId],
    queryFn: () => installationApi.get(installationId),
    enabled: !!installationId,
  });

  const { data: technicians } = useQuery({
    queryKey: ['technicians', installation?.address?.pincode],
    queryFn: () => installationApi.getTechnicians(installation?.address?.pincode || ''),
    enabled: !!installation?.address?.pincode && isAssignDialogOpen,
  });

  const scheduleMutation = useMutation({
    mutationFn: () => installationApi.schedule(installationId, scheduleForm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['installation', installationId] });
      toast.success('Installation scheduled');
      setIsScheduleDialogOpen(false);
    },
    onError: () => toast.error('Failed to schedule'),
  });

  const assignMutation = useMutation({
    mutationFn: () => installationApi.assign(installationId, selectedTechnician),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['installation', installationId] });
      toast.success('Technician assigned');
      setIsAssignDialogOpen(false);
    },
    onError: () => toast.error('Failed to assign technician'),
  });

  const startMutation = useMutation({
    mutationFn: () => installationApi.start(installationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['installation', installationId] });
      toast.success('Installation started');
    },
    onError: () => toast.error('Failed to start'),
  });

  const completeMutation = useMutation({
    mutationFn: () => installationApi.complete(installationId, completionForm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['installation', installationId] });
      toast.success('Installation completed');
      setIsCompleteDialogOpen(false);
    },
    onError: () => toast.error('Failed to complete'),
  });

  const feedbackMutation = useMutation({
    mutationFn: () => installationApi.recordFeedback(installationId, feedbackForm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['installation', installationId] });
      toast.success('Feedback recorded');
      setIsFeedbackDialogOpen(false);
    },
    onError: () => toast.error('Failed to record feedback'),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!installation) {
    return (
      <div className="text-center py-12">
        <Wrench className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h2 className="text-lg font-medium">Installation not found</h2>
        <Button variant="outline" className="mt-4" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Go Back
        </Button>
      </div>
    );
  }

  const canSchedule = installation.status === 'NEW';
  const canAssign = ['NEW', 'SCHEDULED'].includes(installation.status);
  const canStart = installation.status === 'ASSIGNED' && installation.technician;
  const canComplete = installation.status === 'IN_PROGRESS';
  const canRecordFeedback = installation.status === 'COMPLETED' && !installation.feedback;

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
              <Wrench className="h-5 w-5" />
              <h1 className="text-2xl font-bold">Installation {installation.installation_number}</h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[installation.status]}`}>
                {installation.status.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-muted-foreground">Order: {installation.order_number}</p>
          </div>
        </div>
        <div className="flex gap-2">
          {canSchedule && (
            <Button variant="outline" onClick={() => setIsScheduleDialogOpen(true)}>
              <Calendar className="mr-2 h-4 w-4" /> Schedule
            </Button>
          )}
          {canAssign && (
            <Button variant="outline" onClick={() => setIsAssignDialogOpen(true)}>
              <UserCheck className="mr-2 h-4 w-4" /> Assign Technician
            </Button>
          )}
          {canStart && (
            <Button onClick={() => startMutation.mutate()}>
              <Play className="mr-2 h-4 w-4" /> Start Installation
            </Button>
          )}
          {canComplete && (
            <Button className="bg-green-600 hover:bg-green-700" onClick={() => setIsCompleteDialogOpen(true)}>
              <CheckCircle className="mr-2 h-4 w-4" /> Complete
            </Button>
          )}
          {canRecordFeedback && (
            <Button variant="outline" onClick={() => setIsFeedbackDialogOpen(true)}>
              <Star className="mr-2 h-4 w-4" /> Record Feedback
            </Button>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Product</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-medium">{installation.product.name}</div>
            <div className="text-sm text-muted-foreground">{installation.product.sku}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Technician</CardTitle>
          </CardHeader>
          <CardContent>
            {installation.technician ? (
              <div>
                <div className="font-medium">{installation.technician.name}</div>
                <div className="text-sm text-muted-foreground">{installation.technician.phone}</div>
              </div>
            ) : (
              <div className="text-muted-foreground">Not Assigned</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Scheduled</CardTitle>
          </CardHeader>
          <CardContent>
            {installation.scheduled_date ? (
              <div>
                <div className="font-medium">{formatDate(installation.scheduled_date)}</div>
                <div className="text-sm text-muted-foreground">{installation.scheduled_time_slot}</div>
              </div>
            ) : (
              <div className="text-muted-foreground">Not Scheduled</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Warranty</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-medium">{installation.warranty_months} months</div>
            {installation.warranty_end_date && (
              <div className="text-sm text-muted-foreground">
                Until {formatDate(installation.warranty_end_date)}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="details" className="space-y-4">
        <TabsList>
          <TabsTrigger value="details">Details</TabsTrigger>
          <TabsTrigger value="checklist">Pre-Installation Checklist</TabsTrigger>
          <TabsTrigger value="completion">Completion Data</TabsTrigger>
          <TabsTrigger value="feedback">Customer Feedback</TabsTrigger>
        </TabsList>

        {/* Details Tab */}
        <TabsContent value="details">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" /> Customer
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="font-medium">{installation.customer.name}</div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Phone className="h-4 w-4" />
                  {installation.customer.phone}
                </div>
                {installation.customer.email && (
                  <div className="text-sm text-muted-foreground">{installation.customer.email}</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="h-5 w-5" /> Installation Address
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm space-y-1">
                  <div>{installation.address.address_line1}</div>
                  {installation.address.address_line2 && (
                    <div>{installation.address.address_line2}</div>
                  )}
                  <div>
                    {installation.address.city}, {installation.address.state}
                  </div>
                  <div className="font-medium">{installation.address.pincode}</div>
                  {installation.address.landmark && (
                    <div className="text-muted-foreground">Landmark: {installation.address.landmark}</div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="h-5 w-5" /> Product & Serial Numbers
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-medium">{installation.product.name}</div>
                <div className="text-sm text-muted-foreground mb-2">
                  SKU: {installation.product.sku}
                  {installation.product.model && ` | Model: ${installation.product.model}`}
                </div>
                {installation.serial_numbers.length > 0 && (
                  <div>
                    <div className="text-sm font-medium mb-1">Serial Numbers:</div>
                    <div className="flex flex-wrap gap-2">
                      {installation.serial_numbers.map((sn) => (
                        <span key={sn} className="px-2 py-1 bg-muted rounded text-xs font-mono">
                          {sn}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" /> Timeline
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created:</span>
                  <span>{formatDate(installation.created_at)}</span>
                </div>
                {installation.scheduled_date && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Scheduled:</span>
                    <span>{formatDate(installation.scheduled_date)}</span>
                  </div>
                )}
                {installation.started_at && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Started:</span>
                    <span>{formatDate(installation.started_at)}</span>
                  </div>
                )}
                {installation.completed_at && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Completed:</span>
                    <span>{formatDate(installation.completed_at)}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Pre-Installation Checklist Tab */}
        <TabsContent value="checklist">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ClipboardCheck className="h-5 w-5" /> Pre-Installation Checklist
              </CardTitle>
              <CardDescription>Verify site readiness before installation</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="site_ready"
                    checked={installation.pre_checklist?.site_ready || preChecklist.site_ready}
                    onCheckedChange={(checked) => setPreChecklist({ ...preChecklist, site_ready: !!checked })}
                    disabled={installation.status !== 'IN_PROGRESS'}
                  />
                  <label htmlFor="site_ready" className="text-sm font-medium">
                    Site is ready for installation
                  </label>
                </div>
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="power_available"
                    checked={installation.pre_checklist?.power_available || preChecklist.power_available}
                    onCheckedChange={(checked) => setPreChecklist({ ...preChecklist, power_available: !!checked })}
                    disabled={installation.status !== 'IN_PROGRESS'}
                  />
                  <label htmlFor="power_available" className="text-sm font-medium">
                    Power supply available (220V)
                  </label>
                </div>
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="water_connection"
                    checked={installation.pre_checklist?.water_connection_available || preChecklist.water_connection_available}
                    onCheckedChange={(checked) => setPreChecklist({ ...preChecklist, water_connection_available: !!checked })}
                    disabled={installation.status !== 'IN_PROGRESS'}
                  />
                  <label htmlFor="water_connection" className="text-sm font-medium">
                    Water connection available
                  </label>
                </div>
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="space_adequate"
                    checked={installation.pre_checklist?.space_adequate || preChecklist.space_adequate}
                    onCheckedChange={(checked) => setPreChecklist({ ...preChecklist, space_adequate: !!checked })}
                    disabled={installation.status !== 'IN_PROGRESS'}
                  />
                  <label htmlFor="space_adequate" className="text-sm font-medium">
                    Adequate space for installation
                  </label>
                </div>
                <Separator />
                <div className="space-y-2">
                  <label className="text-sm font-medium">Notes</label>
                  <Textarea
                    value={installation.pre_checklist?.notes || preChecklist.notes}
                    onChange={(e) => setPreChecklist({ ...preChecklist, notes: e.target.value })}
                    placeholder="Any additional notes about site conditions..."
                    disabled={installation.status !== 'IN_PROGRESS'}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Completion Data Tab */}
        <TabsContent value="completion">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Droplets className="h-5 w-5" /> Installation Readings
              </CardTitle>
              <CardDescription>Post-installation test readings and data</CardDescription>
            </CardHeader>
            <CardContent>
              {installation.post_data ? (
                <div className="space-y-6">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-4 bg-blue-50 rounded-lg text-center">
                      <Droplets className="h-6 w-6 mx-auto text-blue-600 mb-2" />
                      <div className="text-2xl font-bold text-blue-600">{installation.post_data.tds_input}</div>
                      <div className="text-xs text-muted-foreground">TDS Input (ppm)</div>
                    </div>
                    <div className="p-4 bg-green-50 rounded-lg text-center">
                      <Droplets className="h-6 w-6 mx-auto text-green-600 mb-2" />
                      <div className="text-2xl font-bold text-green-600">{installation.post_data.tds_output}</div>
                      <div className="text-xs text-muted-foreground">TDS Output (ppm)</div>
                    </div>
                    <div className="p-4 bg-purple-50 rounded-lg text-center">
                      <ThermometerSun className="h-6 w-6 mx-auto text-purple-600 mb-2" />
                      <div className="text-2xl font-bold text-purple-600">{installation.post_data.flow_rate}</div>
                      <div className="text-xs text-muted-foreground">Flow Rate (LPH)</div>
                    </div>
                    <div className="p-4 bg-orange-50 rounded-lg text-center">
                      <CheckCircle className="h-6 w-6 mx-auto text-orange-600 mb-2" />
                      <div className="text-2xl font-bold text-orange-600">
                        {installation.post_data.demo_given ? 'Yes' : 'No'}
                      </div>
                      <div className="text-xs text-muted-foreground">Demo Given</div>
                    </div>
                  </div>

                  {installation.post_data.accessories_used && installation.post_data.accessories_used.length > 0 && (
                    <div>
                      <div className="text-sm font-medium mb-2">Accessories Used:</div>
                      <div className="flex flex-wrap gap-2">
                        {installation.post_data.accessories_used.map((acc) => (
                          <span key={acc} className="px-2 py-1 bg-muted rounded text-sm">
                            {acc}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {installation.post_data.photos && installation.post_data.photos.length > 0 && (
                    <div>
                      <div className="text-sm font-medium mb-2">Installation Photos:</div>
                      <div className="flex gap-2">
                        {installation.post_data.photos.map((photo, i) => (
                          <img key={i} src={photo} alt={`Installation ${i + 1}`} className="h-24 w-24 object-cover rounded border" />
                        ))}
                      </div>
                    </div>
                  )}

                  {installation.post_data.customer_signature && (
                    <div>
                      <div className="text-sm font-medium mb-2">Customer Signature:</div>
                      <img src={installation.post_data.customer_signature} alt="Signature" className="h-16 border rounded" />
                    </div>
                  )}

                  {installation.post_data.notes && (
                    <div>
                      <div className="text-sm font-medium mb-1">Notes:</div>
                      <p className="text-sm text-muted-foreground">{installation.post_data.notes}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Wrench className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No completion data recorded yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Feedback Tab */}
        <TabsContent value="feedback">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Star className="h-5 w-5" /> Customer Feedback
              </CardTitle>
            </CardHeader>
            <CardContent>
              {installation.feedback ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <div className="text-3xl font-bold">{installation.feedback.rating}</div>
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <Star
                          key={star}
                          className={`h-6 w-6 ${star <= installation.feedback!.rating ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}`}
                        />
                      ))}
                    </div>
                    <span className="text-muted-foreground">/ 5</span>
                  </div>
                  {installation.feedback.comments && (
                    <div>
                      <div className="text-sm font-medium mb-1">Comments:</div>
                      <p className="text-sm text-muted-foreground">{installation.feedback.comments}</p>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="text-sm">Would Recommend:</span>
                    {installation.feedback.would_recommend ? (
                      <span className="text-green-600 font-medium">Yes</span>
                    ) : (
                      <span className="text-red-600 font-medium">No</span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Star className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No feedback recorded yet</p>
                  {canRecordFeedback && (
                    <Button className="mt-4" onClick={() => setIsFeedbackDialogOpen(true)}>
                      Record Feedback
                    </Button>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Schedule Dialog */}
      <Dialog open={isScheduleDialogOpen} onOpenChange={setIsScheduleDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Schedule Installation</DialogTitle>
            <DialogDescription>Select a date and time slot for the installation</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Date</label>
              <Input
                type="date"
                value={scheduleForm.scheduled_date}
                onChange={(e) => setScheduleForm({ ...scheduleForm, scheduled_date: e.target.value })}
                min={new Date().toISOString().split('T')[0]}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Time Slot</label>
              <Select
                value={scheduleForm.scheduled_time_slot}
                onValueChange={(v) => setScheduleForm({ ...scheduleForm, scheduled_time_slot: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select time slot" />
                </SelectTrigger>
                <SelectContent>
                  {timeSlots.map((slot) => (
                    <SelectItem key={slot.value} value={slot.value}>
                      {slot.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsScheduleDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => scheduleMutation.mutate()} disabled={!scheduleForm.scheduled_date || !scheduleForm.scheduled_time_slot}>
              <Calendar className="mr-2 h-4 w-4" /> Schedule
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign Technician Dialog */}
      <Dialog open={isAssignDialogOpen} onOpenChange={setIsAssignDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Technician</DialogTitle>
            <DialogDescription>Select a technician for this installation</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Available Technicians</label>
              <Select value={selectedTechnician} onValueChange={setSelectedTechnician}>
                <SelectTrigger>
                  <SelectValue placeholder="Select technician" />
                </SelectTrigger>
                <SelectContent>
                  {technicians?.map((tech) => (
                    <SelectItem key={tech.id} value={tech.id}>
                      {tech.name} - {tech.skill_level} ({tech.phone})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAssignDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => assignMutation.mutate()} disabled={!selectedTechnician}>
              <UserCheck className="mr-2 h-4 w-4" /> Assign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Complete Installation Dialog */}
      <Dialog open={isCompleteDialogOpen} onOpenChange={setIsCompleteDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Complete Installation</DialogTitle>
            <DialogDescription>Enter post-installation readings and data</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">TDS Input (ppm)</label>
                <Input
                  type="number"
                  value={completionForm.tds_input}
                  onChange={(e) => setCompletionForm({ ...completionForm, tds_input: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">TDS Output (ppm)</label>
                <Input
                  type="number"
                  value={completionForm.tds_output}
                  onChange={(e) => setCompletionForm({ ...completionForm, tds_output: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Flow Rate (LPH)</label>
              <Input
                type="number"
                value={completionForm.flow_rate}
                onChange={(e) => setCompletionForm({ ...completionForm, flow_rate: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="demo_given"
                checked={completionForm.demo_given}
                onCheckedChange={(checked) => setCompletionForm({ ...completionForm, demo_given: !!checked })}
              />
              <label htmlFor="demo_given" className="text-sm font-medium">
                Product demo given to customer
              </label>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Notes</label>
              <Textarea
                value={completionForm.notes}
                onChange={(e) => setCompletionForm({ ...completionForm, notes: e.target.value })}
                placeholder="Any additional notes..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCompleteDialogOpen(false)}>Cancel</Button>
            <Button className="bg-green-600 hover:bg-green-700" onClick={() => completeMutation.mutate()}>
              <CheckCircle className="mr-2 h-4 w-4" /> Complete Installation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Feedback Dialog */}
      <Dialog open={isFeedbackDialogOpen} onOpenChange={setIsFeedbackDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record Customer Feedback</DialogTitle>
            <DialogDescription>Capture customer satisfaction for this installation</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Rating</label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setFeedbackForm({ ...feedbackForm, rating: star })}
                    className="focus:outline-none"
                  >
                    <Star
                      className={`h-8 w-8 ${star <= feedbackForm.rating ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'} hover:text-yellow-400`}
                    />
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Comments</label>
              <Textarea
                value={feedbackForm.comments}
                onChange={(e) => setFeedbackForm({ ...feedbackForm, comments: e.target.value })}
                placeholder="Customer comments..."
              />
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="would_recommend"
                checked={feedbackForm.would_recommend}
                onCheckedChange={(checked) => setFeedbackForm({ ...feedbackForm, would_recommend: !!checked })}
              />
              <label htmlFor="would_recommend" className="text-sm font-medium">
                Customer would recommend to others
              </label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsFeedbackDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => feedbackMutation.mutate()}>
              <Star className="mr-2 h-4 w-4" /> Save Feedback
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
