'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { format } from 'date-fns';
import {
  Target,
  TrendingUp,
  Users,
  Calendar,
  Star,
  MessageSquare,
  Plus,
  Filter,
  Clock,
  CheckCircle2,
  AlertTriangle,
  BarChart3,
  ArrowRight,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
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
  hrApi,
  PerformanceDashboardStats,
  AppraisalCycle,
  KPI,
  Goal,
  Appraisal,
  PerformanceFeedback as Feedback
} from '@/lib/api';

const KPI_CATEGORIES = [
  'SALES',
  'QUALITY',
  'PRODUCTIVITY',
  'CUSTOMER',
  'LEARNING',
  'OPERATIONS',
];

const GOAL_CATEGORIES = [
  'SALES',
  'QUALITY',
  'PRODUCTIVITY',
  'CUSTOMER',
  'LEARNING',
  'PROFESSIONAL',
];

const PERFORMANCE_BANDS = [
  { value: 'OUTSTANDING', label: 'Outstanding', color: 'bg-green-500' },
  { value: 'EXCEEDS', label: 'Exceeds Expectations', color: 'bg-blue-500' },
  { value: 'MEETS', label: 'Meets Expectations', color: 'bg-yellow-500' },
  { value: 'NEEDS_IMPROVEMENT', label: 'Needs Improvement', color: 'bg-orange-500' },
  { value: 'UNSATISFACTORY', label: 'Unsatisfactory', color: 'bg-red-500' },
];

export default function PerformanceManagementPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showCycleDialog, setShowCycleDialog] = useState(false);
  const [showKPIDialog, setShowKPIDialog] = useState(false);
  const [showGoalDialog, setShowGoalDialog] = useState(false);
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);

  // Form states
  const [cycleForm, setCycleForm] = useState({
    name: '',
    description: '',
    financial_year: '',
    start_date: '',
    end_date: '',
    review_start_date: '',
    review_end_date: '',
  });

  const [kpiForm, setKPIForm] = useState({
    name: '',
    description: '',
    category: '',
    unit_of_measure: '',
    target_value: '',
    weightage: '',
  });

  const [goalForm, setGoalForm] = useState({
    employee_id: '',
    cycle_id: '',
    title: '',
    description: '',
    category: '',
    target_value: '',
    weightage: '',
    start_date: '',
    due_date: '',
  });

  const [feedbackForm, setFeedbackForm] = useState({
    employee_id: '',
    feedback_type: '',
    title: '',
    content: '',
  });

  // Queries
  const { data: dashboard, isLoading: dashboardLoading } = useQuery({
    queryKey: ['performance-dashboard'],
    queryFn: () => hrApi.performance.getDashboard(),
  });

  const { data: cyclesData, isLoading: cyclesLoading } = useQuery({
    queryKey: ['appraisal-cycles'],
    queryFn: () => hrApi.performance.cycles.list(),
  });

  const { data: kpisData, isLoading: kpisLoading } = useQuery({
    queryKey: ['kpis'],
    queryFn: () => hrApi.performance.kpis.list(),
  });

  const { data: goalsData, isLoading: goalsLoading } = useQuery({
    queryKey: ['goals'],
    queryFn: () => hrApi.performance.goals.list(),
  });

  const { data: appraisalsData, isLoading: appraisalsLoading } = useQuery({
    queryKey: ['appraisals'],
    queryFn: () => hrApi.performance.appraisals.list(),
  });

  const { data: feedbackData, isLoading: feedbackLoading } = useQuery({
    queryKey: ['feedback'],
    queryFn: () => hrApi.performance.feedback.list(),
  });

  const { data: employeesData } = useQuery({
    queryKey: ['employees-dropdown'],
    queryFn: () => hrApi.employees.dropdown(),
  });

  // Mutations
  const createCycleMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; financial_year: string; start_date: string; end_date: string; review_start_date?: string; review_end_date?: string }) =>
      hrApi.performance.cycles.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appraisal-cycles'] });
      queryClient.invalidateQueries({ queryKey: ['performance-dashboard'] });
      setShowCycleDialog(false);
      setCycleForm({ name: '', description: '', financial_year: '', start_date: '', end_date: '', review_start_date: '', review_end_date: '' });
      toast.success('Appraisal cycle created successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create appraisal cycle');
    },
  });

  const createKPIMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; category: string; unit_of_measure: string; target_value?: number; weightage?: number }) =>
      hrApi.performance.kpis.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kpis'] });
      setShowKPIDialog(false);
      setKPIForm({ name: '', description: '', category: '', unit_of_measure: '', target_value: '', weightage: '' });
      toast.success('KPI created successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create KPI');
    },
  });

  const createGoalMutation = useMutation({
    mutationFn: (data: { employee_id: string; cycle_id: string; title: string; description?: string; category: string; target_value?: number; weightage?: number; start_date: string; due_date: string }) =>
      hrApi.performance.goals.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      queryClient.invalidateQueries({ queryKey: ['performance-dashboard'] });
      setShowGoalDialog(false);
      setGoalForm({ employee_id: '', cycle_id: '', title: '', description: '', category: '', target_value: '', weightage: '', start_date: '', due_date: '' });
      toast.success('Goal created successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create goal');
    },
  });

  const createFeedbackMutation = useMutation({
    mutationFn: (data: { employee_id: string; feedback_type: string; title: string; content: string }) =>
      hrApi.performance.feedback.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feedback'] });
      queryClient.invalidateQueries({ queryKey: ['performance-dashboard'] });
      setShowFeedbackDialog(false);
      setFeedbackForm({ employee_id: '', feedback_type: '', title: '', content: '' });
      toast.success('Feedback submitted successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to submit feedback');
    },
  });

  const getGoalStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <Badge className="bg-green-500">Completed</Badge>;
      case 'IN_PROGRESS':
        return <Badge className="bg-blue-500">In Progress</Badge>;
      case 'PENDING':
        return <Badge variant="secondary">Pending</Badge>;
      case 'CANCELLED':
        return <Badge variant="destructive">Cancelled</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getAppraisalStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <Badge className="bg-green-500">Completed</Badge>;
      case 'HR_REVIEW':
        return <Badge className="bg-purple-500">HR Review</Badge>;
      case 'MANAGER_REVIEW':
        return <Badge className="bg-blue-500">Manager Review</Badge>;
      case 'SELF_REVIEW':
        return <Badge className="bg-yellow-500">Self Review</Badge>;
      case 'NOT_STARTED':
        return <Badge variant="secondary">Not Started</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getFeedbackTypeBadge = (type: string) => {
    switch (type) {
      case 'APPRECIATION':
        return <Badge className="bg-green-500">Appreciation</Badge>;
      case 'IMPROVEMENT':
        return <Badge className="bg-orange-500">Improvement</Badge>;
      case 'SUGGESTION':
        return <Badge className="bg-blue-500">Suggestion</Badge>;
      default:
        return <Badge variant="outline">{type}</Badge>;
    }
  };

  const stats = dashboard || {
    active_cycles: 0,
    pending_self_reviews: 0,
    pending_manager_reviews: 0,
    pending_hr_reviews: 0,
    total_goals: 0,
    completed_goals: 0,
    in_progress_goals: 0,
    overdue_goals: 0,
    rating_distribution: [],
    recent_feedback_count: 0,
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Performance Management</h1>
          <p className="text-muted-foreground">
            Manage appraisals, goals, KPIs, and employee feedback
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowFeedbackDialog(true)}>
            <MessageSquare className="mr-2 h-4 w-4" />
            Give Feedback
          </Button>
          <Button onClick={() => setShowGoalDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Goal
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-6 w-full max-w-3xl">
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="cycles">Cycles</TabsTrigger>
          <TabsTrigger value="goals">Goals</TabsTrigger>
          <TabsTrigger value="kpis">KPIs</TabsTrigger>
          <TabsTrigger value="appraisals">Appraisals</TabsTrigger>
          <TabsTrigger value="feedback">Feedback</TabsTrigger>
        </TabsList>

        {/* Dashboard Tab */}
        <TabsContent value="dashboard" className="space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Cycles</CardTitle>
                <Calendar className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.active_cycles}</div>
                <p className="text-xs text-muted-foreground">Ongoing appraisal cycles</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Pending Reviews</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stats.pending_self_reviews + stats.pending_manager_reviews + stats.pending_hr_reviews}
                </div>
                <div className="text-xs text-muted-foreground space-y-1">
                  <div>Self: {stats.pending_self_reviews}</div>
                  <div>Manager: {stats.pending_manager_reviews}</div>
                  <div>HR: {stats.pending_hr_reviews}</div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Goals Progress</CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.completed_goals}/{stats.total_goals}</div>
                <Progress
                  value={stats.total_goals > 0 ? (stats.completed_goals / stats.total_goals) * 100 : 0}
                  className="mt-2"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {stats.overdue_goals > 0 && (
                    <span className="text-destructive">{stats.overdue_goals} overdue</span>
                  )}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Recent Feedback</CardTitle>
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.recent_feedback_count}</div>
                <p className="text-xs text-muted-foreground">In the last 30 days</p>
              </CardContent>
            </Card>
          </div>

          {/* Rating Distribution */}
          {stats.rating_distribution.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Performance Rating Distribution</CardTitle>
                <CardDescription>Breakdown by performance band</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {PERFORMANCE_BANDS.map((band) => {
                    const count = stats.rating_distribution.find(r => r.band === band.value)?.count || 0;
                    const total = stats.rating_distribution.reduce((sum, r) => sum + r.count, 0);
                    const percentage = total > 0 ? (count / total) * 100 : 0;
                    return (
                      <div key={band.value} className="flex items-center gap-4">
                        <div className="w-40 text-sm">{band.label}</div>
                        <div className="flex-1">
                          <div className="h-4 bg-secondary rounded-full overflow-hidden">
                            <div
                              className={`h-full ${band.color} transition-all`}
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                        </div>
                        <div className="w-16 text-sm text-right">{count} ({percentage.toFixed(0)}%)</div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Cycles Tab */}
        <TabsContent value="cycles" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Appraisal Cycles</h2>
            <Button onClick={() => setShowCycleDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Cycle
            </Button>
          </div>

          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Financial Year</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Review Period</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cyclesLoading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center">Loading...</TableCell>
                  </TableRow>
                ) : cyclesData?.items?.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
                      No appraisal cycles found
                    </TableCell>
                  </TableRow>
                ) : (
                  cyclesData?.items?.map((cycle) => (
                    <TableRow key={cycle.id}>
                      <TableCell className="font-medium">{cycle.name}</TableCell>
                      <TableCell>{cycle.financial_year}</TableCell>
                      <TableCell>
                        {format(new Date(cycle.start_date), 'MMM dd, yyyy')} -{' '}
                        {format(new Date(cycle.end_date), 'MMM dd, yyyy')}
                      </TableCell>
                      <TableCell>
                        {cycle.review_start_date ? (
                          <>
                            {format(new Date(cycle.review_start_date), 'MMM dd')} -{' '}
                            {cycle.review_end_date && format(new Date(cycle.review_end_date), 'MMM dd, yyyy')}
                          </>
                        ) : (
                          '-'
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={
                          cycle.status === 'ACTIVE' ? 'default' :
                          cycle.status === 'CLOSED' ? 'secondary' : 'outline'
                        }>
                          {cycle.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Goals Tab */}
        <TabsContent value="goals" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Employee Goals</h2>
            <Button onClick={() => setShowGoalDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Goal
            </Button>
          </div>

          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Employee</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Progress</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {goalsLoading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center">Loading...</TableCell>
                  </TableRow>
                ) : goalsData?.items?.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      No goals found
                    </TableCell>
                  </TableRow>
                ) : (
                  goalsData?.items?.map((goal) => (
                    <TableRow key={goal.id}>
                      <TableCell className="font-medium">{goal.title}</TableCell>
                      <TableCell>
                        <div>{goal.employee_name}</div>
                        <div className="text-sm text-muted-foreground">{goal.employee_code}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{goal.category}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress value={goal.completion_percentage} className="w-20" />
                          <span className="text-sm">{goal.completion_percentage}%</span>
                        </div>
                      </TableCell>
                      <TableCell>{format(new Date(goal.due_date), 'MMM dd, yyyy')}</TableCell>
                      <TableCell>{getGoalStatusBadge(goal.status)}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* KPIs Tab */}
        <TabsContent value="kpis" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Key Performance Indicators</h2>
            <Button onClick={() => setShowKPIDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add KPI
            </Button>
          </div>

          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Unit</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>Weightage</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {kpisLoading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center">Loading...</TableCell>
                  </TableRow>
                ) : kpisData?.items?.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      No KPIs found
                    </TableCell>
                  </TableRow>
                ) : (
                  kpisData?.items?.map((kpi) => (
                    <TableRow key={kpi.id}>
                      <TableCell>
                        <div className="font-medium">{kpi.name}</div>
                        {kpi.description && (
                          <div className="text-sm text-muted-foreground line-clamp-1">{kpi.description}</div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{kpi.category}</Badge>
                      </TableCell>
                      <TableCell>{kpi.unit_of_measure}</TableCell>
                      <TableCell>{kpi.target_value ?? '-'}</TableCell>
                      <TableCell>{kpi.weightage}%</TableCell>
                      <TableCell>
                        <Badge variant={kpi.is_active ? 'default' : 'secondary'}>
                          {kpi.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Appraisals Tab */}
        <TabsContent value="appraisals" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Employee Appraisals</h2>
          </div>

          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee</TableHead>
                  <TableHead>Cycle</TableHead>
                  <TableHead>Goals</TableHead>
                  <TableHead>Self Rating</TableHead>
                  <TableHead>Manager Rating</TableHead>
                  <TableHead>Final Rating</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {appraisalsLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center">Loading...</TableCell>
                  </TableRow>
                ) : appraisalsData?.items?.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No appraisals found
                    </TableCell>
                  </TableRow>
                ) : (
                  appraisalsData?.items?.map((appraisal) => (
                    <TableRow key={appraisal.id}>
                      <TableCell>
                        <div className="font-medium">{appraisal.employee_name}</div>
                        <div className="text-sm text-muted-foreground">{appraisal.employee_code}</div>
                      </TableCell>
                      <TableCell>{appraisal.cycle_name}</TableCell>
                      <TableCell>
                        {appraisal.goals_achieved}/{appraisal.goals_total}
                      </TableCell>
                      <TableCell>
                        {appraisal.self_rating ? (
                          <div className="flex items-center gap-1">
                            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                            {Number(appraisal.self_rating).toFixed(1)}
                          </div>
                        ) : '-'}
                      </TableCell>
                      <TableCell>
                        {appraisal.manager_rating ? (
                          <div className="flex items-center gap-1">
                            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                            {Number(appraisal.manager_rating).toFixed(1)}
                          </div>
                        ) : '-'}
                      </TableCell>
                      <TableCell>
                        {appraisal.final_rating ? (
                          <div>
                            <div className="flex items-center gap-1">
                              <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                              {Number(appraisal.final_rating).toFixed(1)}
                            </div>
                            {appraisal.performance_band && (
                              <Badge variant="outline" className="text-xs mt-1">
                                {appraisal.performance_band.replace('_', ' ')}
                              </Badge>
                            )}
                          </div>
                        ) : '-'}
                      </TableCell>
                      <TableCell>{getAppraisalStatusBadge(appraisal.status)}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Feedback Tab */}
        <TabsContent value="feedback" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Performance Feedback</h2>
            <Button onClick={() => setShowFeedbackDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Give Feedback
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {feedbackLoading ? (
              <Card>
                <CardContent className="p-6 text-center text-muted-foreground">
                  Loading...
                </CardContent>
              </Card>
            ) : feedbackData?.items?.length === 0 ? (
              <Card className="col-span-2">
                <CardContent className="p-6 text-center text-muted-foreground">
                  No feedback found
                </CardContent>
              </Card>
            ) : (
              feedbackData?.items?.map((fb) => (
                <Card key={fb.id}>
                  <CardHeader className="pb-2">
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-base">{fb.title}</CardTitle>
                        <CardDescription>
                          To: {fb.employee_name} ({fb.employee_code})
                        </CardDescription>
                      </div>
                      {getFeedbackTypeBadge(fb.feedback_type)}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground line-clamp-3">{fb.content}</p>
                    <div className="flex justify-between items-center mt-4 text-xs text-muted-foreground">
                      <span>By: {fb.given_by_name}</span>
                      <span>{format(new Date(fb.created_at), 'MMM dd, yyyy')}</span>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Create Cycle Dialog */}
      <Dialog open={showCycleDialog} onOpenChange={setShowCycleDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Appraisal Cycle</DialogTitle>
            <DialogDescription>
              Define a new performance appraisal cycle for employees.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                value={cycleForm.name}
                onChange={(e) => setCycleForm({ ...cycleForm, name: e.target.value })}
                placeholder="e.g., Annual Review 2025-26"
              />
            </div>
            <div className="space-y-2">
              <Label>Financial Year</Label>
              <Input
                value={cycleForm.financial_year}
                onChange={(e) => setCycleForm({ ...cycleForm, financial_year: e.target.value })}
                placeholder="e.g., 2025-26"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Start Date</Label>
                <Input
                  type="date"
                  value={cycleForm.start_date}
                  onChange={(e) => setCycleForm({ ...cycleForm, start_date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>End Date</Label>
                <Input
                  type="date"
                  value={cycleForm.end_date}
                  onChange={(e) => setCycleForm({ ...cycleForm, end_date: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Review Start</Label>
                <Input
                  type="date"
                  value={cycleForm.review_start_date}
                  onChange={(e) => setCycleForm({ ...cycleForm, review_start_date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Review End</Label>
                <Input
                  type="date"
                  value={cycleForm.review_end_date}
                  onChange={(e) => setCycleForm({ ...cycleForm, review_end_date: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={cycleForm.description}
                onChange={(e) => setCycleForm({ ...cycleForm, description: e.target.value })}
                placeholder="Optional description..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCycleDialog(false)}>Cancel</Button>
            <Button
              onClick={() => createCycleMutation.mutate(cycleForm)}
              disabled={createCycleMutation.isPending}
            >
              Create Cycle
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create KPI Dialog */}
      <Dialog open={showKPIDialog} onOpenChange={setShowKPIDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create KPI</DialogTitle>
            <DialogDescription>
              Define a new Key Performance Indicator.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                value={kpiForm.name}
                onChange={(e) => setKPIForm({ ...kpiForm, name: e.target.value })}
                placeholder="e.g., Monthly Sales Target"
              />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={kpiForm.category} onValueChange={(v) => setKPIForm({ ...kpiForm, category: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {KPI_CATEGORIES.map((cat) => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Unit of Measure</Label>
                <Input
                  value={kpiForm.unit_of_measure}
                  onChange={(e) => setKPIForm({ ...kpiForm, unit_of_measure: e.target.value })}
                  placeholder="e.g., PERCENTAGE"
                />
              </div>
              <div className="space-y-2">
                <Label>Target Value</Label>
                <Input
                  type="number"
                  value={kpiForm.target_value}
                  onChange={(e) => setKPIForm({ ...kpiForm, target_value: e.target.value })}
                  placeholder="e.g., 100"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Weightage (%)</Label>
              <Input
                type="number"
                value={kpiForm.weightage}
                onChange={(e) => setKPIForm({ ...kpiForm, weightage: e.target.value })}
                placeholder="e.g., 20"
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={kpiForm.description}
                onChange={(e) => setKPIForm({ ...kpiForm, description: e.target.value })}
                placeholder="Optional description..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowKPIDialog(false)}>Cancel</Button>
            <Button
              onClick={() => createKPIMutation.mutate({
                ...kpiForm,
                target_value: kpiForm.target_value ? parseFloat(kpiForm.target_value) : undefined,
                weightage: kpiForm.weightage ? parseFloat(kpiForm.weightage) : 0,
              })}
              disabled={createKPIMutation.isPending}
            >
              Create KPI
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Goal Dialog */}
      <Dialog open={showGoalDialog} onOpenChange={setShowGoalDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Goal</DialogTitle>
            <DialogDescription>
              Assign a new goal to an employee.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Employee</Label>
              <Select value={goalForm.employee_id} onValueChange={(v) => setGoalForm({ ...goalForm, employee_id: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select employee" />
                </SelectTrigger>
                <SelectContent>
                  {employeesData?.map((emp) => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.full_name} ({emp.employee_code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Appraisal Cycle</Label>
              <Select value={goalForm.cycle_id} onValueChange={(v) => setGoalForm({ ...goalForm, cycle_id: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select cycle" />
                </SelectTrigger>
                <SelectContent>
                  {cyclesData?.items?.map((cycle) => (
                    <SelectItem key={cycle.id} value={cycle.id}>
                      {cycle.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Title</Label>
              <Input
                value={goalForm.title}
                onChange={(e) => setGoalForm({ ...goalForm, title: e.target.value })}
                placeholder="e.g., Increase monthly sales by 20%"
              />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={goalForm.category} onValueChange={(v) => setGoalForm({ ...goalForm, category: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {GOAL_CATEGORIES.map((cat) => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Target Value</Label>
                <Input
                  type="number"
                  value={goalForm.target_value}
                  onChange={(e) => setGoalForm({ ...goalForm, target_value: e.target.value })}
                  placeholder="e.g., 100"
                />
              </div>
              <div className="space-y-2">
                <Label>Weightage (%)</Label>
                <Input
                  type="number"
                  value={goalForm.weightage}
                  onChange={(e) => setGoalForm({ ...goalForm, weightage: e.target.value })}
                  placeholder="e.g., 20"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Start Date</Label>
                <Input
                  type="date"
                  value={goalForm.start_date}
                  onChange={(e) => setGoalForm({ ...goalForm, start_date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Due Date</Label>
                <Input
                  type="date"
                  value={goalForm.due_date}
                  onChange={(e) => setGoalForm({ ...goalForm, due_date: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={goalForm.description}
                onChange={(e) => setGoalForm({ ...goalForm, description: e.target.value })}
                placeholder="Optional description..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowGoalDialog(false)}>Cancel</Button>
            <Button
              onClick={() => createGoalMutation.mutate({
                ...goalForm,
                target_value: goalForm.target_value ? parseFloat(goalForm.target_value) : undefined,
                weightage: goalForm.weightage ? parseFloat(goalForm.weightage) : 0,
              })}
              disabled={createGoalMutation.isPending}
            >
              Create Goal
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Feedback Dialog */}
      <Dialog open={showFeedbackDialog} onOpenChange={setShowFeedbackDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Give Feedback</DialogTitle>
            <DialogDescription>
              Provide performance feedback to an employee.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Employee</Label>
              <Select value={feedbackForm.employee_id} onValueChange={(v) => setFeedbackForm({ ...feedbackForm, employee_id: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select employee" />
                </SelectTrigger>
                <SelectContent>
                  {employeesData?.map((emp) => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.full_name} ({emp.employee_code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Feedback Type</Label>
              <Select value={feedbackForm.feedback_type} onValueChange={(v) => setFeedbackForm({ ...feedbackForm, feedback_type: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="APPRECIATION">Appreciation</SelectItem>
                  <SelectItem value="IMPROVEMENT">Improvement</SelectItem>
                  <SelectItem value="SUGGESTION">Suggestion</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Title</Label>
              <Input
                value={feedbackForm.title}
                onChange={(e) => setFeedbackForm({ ...feedbackForm, title: e.target.value })}
                placeholder="e.g., Great work on the project"
              />
            </div>
            <div className="space-y-2">
              <Label>Content</Label>
              <Textarea
                value={feedbackForm.content}
                onChange={(e) => setFeedbackForm({ ...feedbackForm, content: e.target.value })}
                placeholder="Provide detailed feedback..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowFeedbackDialog(false)}>Cancel</Button>
            <Button
              onClick={() => createFeedbackMutation.mutate(feedbackForm)}
              disabled={createFeedbackMutation.isPending}
            >
              Submit Feedback
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
