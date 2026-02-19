'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  GitBranch,
  Plus,
  RefreshCw,
  Factory,
  ShoppingCart,
  Truck,
  CheckCircle,
  Clock,
  Gauge,
  Shield,
  AlertTriangle,
  Layers,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  AreaChart,
  Area,
} from 'recharts';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { snopApi } from '@/lib/api';
import { apiClient } from '@/lib/api/client';

const zoneColors: Record<string, string> = {
  RED: 'bg-red-500',
  YELLOW: 'bg-amber-400',
  GREEN: 'bg-green-500',
};

export default function SupplyPlansPage() {
  const [activeTab, setActiveTab] = useState<string>('plans');
  const queryClient = useQueryClient();

  const { data: plans, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['snop-supply-plans'],
    queryFn: async () => {
      try {
        return await snopApi.getSupplyPlans();
      } catch {
        toast.error('Failed to load supply plans');
        return { items: [], total: 0 };
      }
    },
  });

  const createPlanMutation = useMutation({
    mutationFn: async () => {
      const today = new Date();
      const endDate = new Date(today);
      endDate.setDate(endDate.getDate() + 90);
      return await snopApi.createSupplyPlan({
        plan_name: `Supply Plan - ${today.toLocaleDateString()}`,
        plan_start_date: today.toISOString().split('T')[0],
        plan_end_date: endDate.toISOString().split('T')[0],
      });
    },
    onSuccess: () => {
      toast.success('Supply plan created');
      queryClient.invalidateQueries({ queryKey: ['snop-supply-plans'] });
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to create supply plan');
    },
  });

  // Capacity analysis
  const { data: capacity, isLoading: isLoadingCapacity } = useQuery({
    queryKey: ['snop-capacity-analysis'],
    queryFn: async () => {
      const res = await apiClient.get('/snop/supply-plan/capacity-analysis?horizon_days=90&daily_capacity=1000');
      return res.data;
    },
    enabled: activeTab === 'capacity',
  });

  // DDMRP buffers
  const { data: ddmrp, isLoading: isLoadingDdmrp } = useQuery({
    queryKey: ['snop-ddmrp-buffers'],
    queryFn: async () => {
      const res = await apiClient.get('/snop/supply-plan/ddmrp-buffers?lookback_days=90');
      return res.data;
    },
    enabled: activeTab === 'ddmrp',
  });

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24" />)}
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
          <div className="p-2 bg-green-100 rounded-lg">
            <GitBranch className="h-6 w-6 text-green-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Intelligent Supply Planning</h1>
            <p className="text-muted-foreground">
              Constraint-based optimization, DDMRP buffers & capacity analysis
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={() => createPlanMutation.mutate()} disabled={createPlanMutation.isPending}>
            <Plus className="h-4 w-4 mr-2" />
            {createPlanMutation.isPending ? 'Creating...' : 'Create Plan'}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="plans">
            <GitBranch className="h-4 w-4 mr-1.5" />
            Supply Plans
          </TabsTrigger>
          <TabsTrigger value="capacity">
            <Gauge className="h-4 w-4 mr-1.5" />
            Capacity Analysis
          </TabsTrigger>
          <TabsTrigger value="ddmrp">
            <Shield className="h-4 w-4 mr-1.5" />
            DDMRP Buffers
          </TabsTrigger>
        </TabsList>

        {/* Supply Plans Tab */}
        <TabsContent value="plans" className="space-y-4">
          {/* Summary Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Factory className="h-4 w-4 text-blue-600" />
                  <span className="text-sm text-muted-foreground">Production Plans</span>
                </div>
                <p className="text-2xl font-bold mt-2">
                  {plans?.items?.filter((p: any) => p.plan_type === 'PRODUCTION').length || 0}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <ShoppingCart className="h-4 w-4 text-purple-600" />
                  <span className="text-sm text-muted-foreground">Procurement Plans</span>
                </div>
                <p className="text-2xl font-bold mt-2">
                  {plans?.items?.filter((p: any) => p.plan_type === 'PROCUREMENT').length || 0}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-amber-600" />
                  <span className="text-sm text-muted-foreground">In Execution</span>
                </div>
                <p className="text-2xl font-bold mt-2">
                  {plans?.items?.filter((p: any) => p.status === 'IN_EXECUTION').length || 0}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span className="text-sm text-muted-foreground">Completed</span>
                </div>
                <p className="text-2xl font-bold mt-2">
                  {plans?.items?.filter((p: any) => p.status === 'COMPLETED').length || 0}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Supply Plans Table */}
          <Card>
            <CardHeader>
              <CardTitle>Supply Plans</CardTitle>
              <CardDescription>Production and procurement schedules</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Plan Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead>Total Quantity</TableHead>
                    <TableHead>Capacity %</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {plans?.items?.length > 0 ? (
                    plans.items.map((plan: any) => (
                      <TableRow key={plan.id}>
                        <TableCell className="font-medium">{plan.plan_name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {plan.plan_type === 'PRODUCTION' ? (
                              <><Factory className="h-3 w-3 mr-1" /> Production</>
                            ) : (
                              <><Truck className="h-3 w-3 mr-1" /> Procurement</>
                            )}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {new Date(plan.start_date).toLocaleDateString()} -{' '}
                          {new Date(plan.end_date).toLocaleDateString()}
                        </TableCell>
                        <TableCell>{Number(plan.total_quantity || 0).toLocaleString() || '-'}</TableCell>
                        <TableCell>
                          <span className={Number(plan.capacity_utilization) >= 90 ? 'text-red-600' : 'text-green-600'}>
                            {plan.capacity_utilization != null ? Number(plan.capacity_utilization).toFixed(1) : '-'}%
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={plan.status === 'APPROVED' ? 'default' : 'secondary'}>
                            {plan.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {new Date(plan.created_at).toLocaleDateString()}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        <GitBranch className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>No supply plans created yet</p>
                        <p className="text-sm">Create a plan based on demand forecasts</p>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Capacity Analysis Tab */}
        <TabsContent value="capacity" className="space-y-4">
          {isLoadingCapacity ? (
            <div className="grid gap-4 md:grid-cols-2">
              {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-40" />)}
            </div>
          ) : capacity ? (
            <>
              {/* Capacity KPIs */}
              <div className="grid gap-4 md:grid-cols-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <Gauge className="h-4 w-4 text-blue-600" />
                      <span className="text-sm text-muted-foreground">Avg Utilization</span>
                    </div>
                    <p className={`text-2xl font-bold mt-2 ${
                      capacity.avg_utilization_pct > 85 ? 'text-red-600' :
                      capacity.avg_utilization_pct > 70 ? 'text-amber-600' : 'text-green-600'
                    }`}>
                      {capacity.avg_utilization_pct?.toFixed(1)}%
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <Factory className="h-4 w-4 text-purple-600" />
                      <span className="text-sm text-muted-foreground">Daily Capacity</span>
                    </div>
                    <p className="text-2xl font-bold mt-2">
                      {capacity.daily_capacity?.toLocaleString()} units
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                      <span className="text-sm text-muted-foreground">Bottlenecks</span>
                    </div>
                    <p className="text-2xl font-bold mt-2 text-red-600">
                      {capacity.bottleneck_periods || 0}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <Layers className="h-4 w-4 text-amber-600" />
                      <span className="text-sm text-muted-foreground">Peak Demand</span>
                    </div>
                    <p className="text-2xl font-bold mt-2">
                      {capacity.peak_demand?.toLocaleString()}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Capacity Utilization Chart */}
              {capacity.timeline && capacity.timeline.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Capacity Utilization Timeline</CardTitle>
                    <CardDescription>
                      Demand vs. capacity over {capacity.horizon_days} day horizon
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={capacity.timeline}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis
                            dataKey="date"
                            tickFormatter={(v) => new Date(v).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}
                          />
                          <YAxis />
                          <Tooltip
                            labelFormatter={(v) => new Date(v as string).toLocaleDateString()}
                            formatter={(value) => [Number(value).toLocaleString(), '']}
                          />
                          <Area
                            type="monotone"
                            dataKey="capacity"
                            stroke="#22C55E"
                            fill="#22C55E"
                            fillOpacity={0.1}
                            strokeDasharray="5 5"
                            name="Capacity"
                          />
                          <Area
                            type="monotone"
                            dataKey="demand"
                            stroke="#3B82F6"
                            fill="#3B82F6"
                            fillOpacity={0.2}
                            name="Demand"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Recommendations */}
              {capacity.recommendations && capacity.recommendations.length > 0 && (
                <Card className="border-amber-200 bg-amber-50/30">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                      Capacity Recommendations
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {capacity.recommendations.map((rec: string, i: number) => (
                        <li key={i} className="text-sm flex items-start gap-2">
                          <span className="text-amber-500 mt-0.5">&#8226;</span>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                No capacity data available. Generate forecasts first.
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* DDMRP Buffers Tab */}
        <TabsContent value="ddmrp" className="space-y-4">
          {isLoadingDdmrp ? (
            <Skeleton className="h-96" />
          ) : ddmrp ? (
            <>
              {/* Buffer Summary */}
              <div className="grid gap-4 md:grid-cols-4">
                <Card className="border-red-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500" />
                      <span className="text-sm text-muted-foreground">Red Zone</span>
                    </div>
                    <p className="text-2xl font-bold mt-2 text-red-600">
                      {ddmrp.summary?.red || 0}
                    </p>
                    <p className="text-xs text-red-500">Urgent replenishment needed</p>
                  </CardContent>
                </Card>
                <Card className="border-amber-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-amber-400" />
                      <span className="text-sm text-muted-foreground">Yellow Zone</span>
                    </div>
                    <p className="text-2xl font-bold mt-2 text-amber-600">
                      {ddmrp.summary?.yellow || 0}
                    </p>
                    <p className="text-xs text-amber-500">Order soon</p>
                  </CardContent>
                </Card>
                <Card className="border-green-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-green-500" />
                      <span className="text-sm text-muted-foreground">Green Zone</span>
                    </div>
                    <p className="text-2xl font-bold mt-2 text-green-600">
                      {ddmrp.summary?.green || 0}
                    </p>
                    <p className="text-xs text-green-500">Adequate stock</p>
                  </CardContent>
                </Card>
                <Card className="border-orange-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-orange-600" />
                      <span className="text-sm text-muted-foreground">Action Needed</span>
                    </div>
                    <p className="text-2xl font-bold mt-2 text-orange-600">
                      {ddmrp.summary?.action_needed || 0}
                    </p>
                    <p className="text-xs text-orange-500">Require immediate attention</p>
                  </CardContent>
                </Card>
              </div>

              {/* Buffer Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">DDMRP Buffer Status</CardTitle>
                  <CardDescription>
                    {ddmrp.total_products} products with buffer zones (Red=safety, Yellow=lead time, Green=replenishment)
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Product</TableHead>
                        <TableHead>Zone</TableHead>
                        <TableHead>Buffer Fill</TableHead>
                        <TableHead>On Hand</TableHead>
                        <TableHead>Red</TableHead>
                        <TableHead>Yellow</TableHead>
                        <TableHead>Green</TableHead>
                        <TableHead>Total Buffer</TableHead>
                        <TableHead>Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {ddmrp.buffers?.length > 0 ? (
                        ddmrp.buffers.slice(0, 50).map((item: any) => (
                          <TableRow key={item.product_id}>
                            <TableCell className="font-medium max-w-[160px] truncate">
                              {item.product_name}
                            </TableCell>
                            <TableCell>
                              <Badge className={
                                item.current_zone === 'RED' ? 'bg-red-100 text-red-800' :
                                item.current_zone === 'YELLOW' ? 'bg-amber-100 text-amber-800' :
                                'bg-green-100 text-green-800'
                              }>
                                {item.current_zone}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2 min-w-[120px]">
                                <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden flex">
                                  <div
                                    className="h-full bg-red-500"
                                    style={{ width: `${item.total_buffer ? Math.min(100, (item.top_of_red / item.total_buffer) * 100) : 0}%` }}
                                  />
                                  <div
                                    className="h-full bg-amber-400"
                                    style={{ width: `${item.total_buffer ? Math.min(100, (item.yellow_zone / item.total_buffer) * 100) : 0}%` }}
                                  />
                                  <div
                                    className="h-full bg-green-500"
                                    style={{ width: `${item.total_buffer ? Math.min(100, (item.green_zone / item.total_buffer) * 100) : 0}%` }}
                                  />
                                </div>
                                <span className="text-xs font-mono text-muted-foreground">
                                  {item.buffer_penetration_pct?.toFixed(0)}%
                                </span>
                              </div>
                            </TableCell>
                            <TableCell className="font-mono text-sm">
                              {item.on_hand?.toLocaleString()}
                            </TableCell>
                            <TableCell className="font-mono text-sm text-red-600">
                              {item.red_zone?.toLocaleString()}
                            </TableCell>
                            <TableCell className="font-mono text-sm text-amber-600">
                              {item.yellow_zone?.toLocaleString()}
                            </TableCell>
                            <TableCell className="font-mono text-sm text-green-600">
                              {item.green_zone?.toLocaleString()}
                            </TableCell>
                            <TableCell className="font-mono text-sm">
                              {item.total_buffer?.toLocaleString()}
                            </TableCell>
                            <TableCell>
                              {item.action_needed && (
                                <Badge variant="destructive" className="text-xs">
                                  Replenish
                                </Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        ))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                            No products with demand data for buffer calculation.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                No DDMRP data available. Ensure products have demand history.
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
