'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Target,
  Plus,
  RefreshCw,
  Play,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  BarChart3,
  DollarSign,
  Dice5,
  SlidersHorizontal,
  Zap,
  Trophy,
  ArrowRight,
  Activity,
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
  PieChart,
  Pie,
} from 'recharts';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { apiClient } from '@/lib/api/client';
import { snopApi } from '@/lib/api';

const statusColors: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-800',
  RUNNING: 'bg-blue-100 text-blue-800',
  COMPLETED: 'bg-green-100 text-green-800',
  FAILED: 'bg-red-100 text-red-800',
  ARCHIVED: 'bg-purple-100 text-purple-800',
};

function formatCurrency(val: number | string | null | undefined) {
  const num = Number(val) || 0;
  if (num >= 10000000) return `${(num / 10000000).toFixed(2)} Cr`;
  if (num >= 100000) return `${(num / 100000).toFixed(2)} L`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)} K`;
  return num.toFixed(0);
}

export default function ScenariosPage() {
  const [activeTab, setActiveTab] = useState('scenarios');
  const queryClient = useQueryClient();

  // ---- What-If sliders state ----
  const [whatIf, setWhatIf] = useState({
    demand_change_pct: 0,
    price_change_pct: 0,
    supply_change_pct: 0,
    lead_time_change_pct: 0,
    cogs_change_pct: 0,
  });

  // ---- Queries ----
  const { data: scenarios, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['snop-scenarios'],
    queryFn: async () => {
      try {
        return await snopApi.getScenarios();
      } catch {
        return { items: [], total: 0 };
      }
    },
  });

  const { data: whatIfResult, isFetching: whatIfLoading } = useQuery({
    queryKey: ['snop-what-if', whatIf],
    queryFn: async () => {
      const res = await apiClient.post('/api/v1/snop/scenario/what-if', whatIf);
      return res.data;
    },
    enabled: activeTab === 'whatif',
  });

  // ---- Mutations ----
  const runMonteCarlo = useMutation({
    mutationFn: async (scenarioId: string) => {
      const res = await apiClient.post('/api/v1/snop/scenario/monte-carlo', {
        scenario_id: scenarioId,
        num_simulations: 1000,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snop-scenarios'] });
    },
  });

  const runPL = useMutation({
    mutationFn: async (scenarioId: string) => {
      const res = await apiClient.post('/api/v1/snop/scenario/financial-pl', {
        scenario_id: scenarioId,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snop-scenarios'] });
    },
  });

  const runSensitivity = useMutation({
    mutationFn: async (scenarioId: string) => {
      const res = await apiClient.post('/api/v1/snop/scenario/sensitivity', {
        scenario_id: scenarioId,
        variation_pct: 20,
      });
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  const completedScenarios = scenarios?.items?.filter((s: any) => s.status === 'COMPLETED') || [];
  const mcResult = runMonteCarlo.data;
  const plResult = runPL.data;
  const sensitivityResult = runSensitivity.data;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-lg dark:bg-purple-900/30">
            <Target className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Advanced Scenario Engine</h1>
            <p className="text-muted-foreground">
              Monte Carlo simulation, P&L projections, sensitivity analysis & digital twin
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-purple-600" />
              <span className="text-sm text-muted-foreground">Total Scenarios</span>
            </div>
            <p className="text-2xl font-bold mt-2">{scenarios?.total || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Dice5 className="h-4 w-4 text-blue-600" />
              <span className="text-sm text-muted-foreground">Monte Carlo Runs</span>
            </div>
            <p className="text-2xl font-bold mt-2">
              {completedScenarios.filter((s: any) => s.results?.monte_carlo).length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span className="text-sm text-muted-foreground">Completed</span>
            </div>
            <p className="text-2xl font-bold mt-2">{completedScenarios.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-600" />
              <span className="text-sm text-muted-foreground">Draft</span>
            </div>
            <p className="text-2xl font-bold mt-2">
              {scenarios?.items?.filter((s: any) => s.status === 'DRAFT').length || 0}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="scenarios" className="gap-1">
            <Target className="h-4 w-4" /> Scenarios
          </TabsTrigger>
          <TabsTrigger value="montecarlo" className="gap-1">
            <Dice5 className="h-4 w-4" /> Monte Carlo
          </TabsTrigger>
          <TabsTrigger value="pl" className="gap-1">
            <DollarSign className="h-4 w-4" /> P&L Projection
          </TabsTrigger>
          <TabsTrigger value="sensitivity" className="gap-1">
            <BarChart3 className="h-4 w-4" /> Sensitivity
          </TabsTrigger>
          <TabsTrigger value="whatif" className="gap-1">
            <SlidersHorizontal className="h-4 w-4" /> What-If
          </TabsTrigger>
        </TabsList>

        {/* ======= TAB: Scenarios List ======= */}
        <TabsContent value="scenarios">
          <Card>
            <CardHeader>
              <CardTitle>All Scenarios</CardTitle>
              <CardDescription>Select a scenario to run advanced analysis</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Scenario</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Projected Revenue</TableHead>
                    <TableHead>Service Level</TableHead>
                    <TableHead>Stockout Risk</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {scenarios?.items?.length > 0 ? (
                    scenarios.items.map((sc: any) => (
                      <TableRow key={sc.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{sc.name || sc.scenario_name}</p>
                            <p className="text-xs text-muted-foreground">{sc.description || 'No description'}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={statusColors[sc.status] || ''}>
                            {sc.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {sc.results?.projected_revenue
                            ? `INR ${formatCurrency(sc.results.projected_revenue)}`
                            : '-'
                          }
                        </TableCell>
                        <TableCell>
                          {sc.results?.service_level_pct
                            ? `${sc.results.service_level_pct.toFixed(1)}%`
                            : '-'
                          }
                        </TableCell>
                        <TableCell>
                          {sc.results?.stockout_probability != null
                            ? <span className={sc.results.stockout_probability > 0.1 ? 'text-red-600' : 'text-green-600'}>
                                {(sc.results.stockout_probability * 100).toFixed(1)}%
                              </span>
                            : '-'
                          }
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              size="sm" variant="outline"
                              onClick={() => runMonteCarlo.mutate(sc.id)}
                              disabled={runMonteCarlo.isPending}
                            >
                              <Dice5 className="h-3 w-3 mr-1" /> MC
                            </Button>
                            <Button
                              size="sm" variant="outline"
                              onClick={() => runPL.mutate(sc.id)}
                              disabled={runPL.isPending}
                            >
                              <DollarSign className="h-3 w-3 mr-1" /> P&L
                            </Button>
                            <Button
                              size="sm" variant="outline"
                              onClick={() => runSensitivity.mutate(sc.id)}
                              disabled={runSensitivity.isPending}
                            >
                              <BarChart3 className="h-3 w-3 mr-1" /> Tornado
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                        <Target className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>No scenarios created yet</p>
                        <p className="text-sm">Create what-if scenarios to run advanced simulations</p>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ======= TAB: Monte Carlo ======= */}
        <TabsContent value="montecarlo">
          {mcResult ? (
            <div className="space-y-6">
              {/* KPIs */}
              <div className="grid gap-4 md:grid-cols-5">
                {[
                  { label: 'Expected Revenue', value: `INR ${formatCurrency(mcResult.revenue?.mean || 0)}`, icon: DollarSign, color: 'text-green-600' },
                  { label: 'Expected Margin', value: `INR ${formatCurrency(mcResult.gross_margin?.mean || 0)}`, icon: TrendingUp, color: 'text-blue-600' },
                  { label: 'Stockout Probability', value: `${((mcResult.stockout_probability || 0) * 100).toFixed(1)}%`, icon: AlertCircle, color: mcResult.stockout_probability > 0.1 ? 'text-red-600' : 'text-green-600' },
                  { label: 'Service Level', value: `${(mcResult.service_level?.mean || 0).toFixed(1)}%`, icon: CheckCircle, color: 'text-emerald-600' },
                  { label: 'Simulations', value: mcResult.num_simulations, icon: Dice5, color: 'text-purple-600' },
                ].map((kpi, i) => (
                  <Card key={i}>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2">
                        <kpi.icon className={`h-4 w-4 ${kpi.color}`} />
                        <span className="text-xs text-muted-foreground">{kpi.label}</span>
                      </div>
                      <p className="text-xl font-bold mt-1">{kpi.value}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                {/* Revenue Distribution Histogram */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Revenue Distribution</CardTitle>
                    <CardDescription>Probability distribution across {mcResult.num_simulations} simulations</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={mcResult.revenue_histogram || []}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="range_start" tickFormatter={(v: number) => formatCurrency(v)} fontSize={11} />
                        <YAxis tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} fontSize={11} />
                        <Tooltip
                          formatter={(value: any) => `${(Number(value) * 100).toFixed(1)}%`}
                          labelFormatter={(v: any) => `INR ${formatCurrency(Number(v))}`}
                        />
                        <Bar dataKey="probability" fill="#8b5cf6" radius={[4, 4, 0, 0]}>
                          {(mcResult.revenue_histogram || []).map((_: any, idx: number) => (
                            <Cell key={idx} fill={idx === 4 || idx === 5 ? '#7c3aed' : '#c4b5fd'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                {/* Confidence Intervals */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Confidence Intervals</CardTitle>
                    <CardDescription>Percentile-based risk ranges</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {[
                        { label: 'Revenue', data: mcResult.revenue },
                        { label: 'Gross Margin', data: mcResult.gross_margin },
                        { label: 'Net Profit', data: mcResult.net_profit },
                        { label: 'Units Sold', data: mcResult.units_sold },
                        { label: 'Service Level %', data: mcResult.service_level },
                      ].map((item, i) => (
                        <div key={i} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="font-medium">{item.label}</span>
                            <span className="text-muted-foreground">
                              Mean: {item.label.includes('%') ? `${item.data?.mean?.toFixed(1)}%` : `INR ${formatCurrency(item.data?.mean || 0)}`}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span>P5: {formatCurrency(item.data?.p5 || 0)}</span>
                            <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-red-400 via-yellow-400 via-green-400 to-blue-400 rounded-full"
                                style={{ width: '100%' }}
                              />
                            </div>
                            <span>P95: {formatCurrency(item.data?.p95 || 0)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <Card>
              <CardContent className="p-12 text-center">
                <Dice5 className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold">No Monte Carlo Results</h3>
                <p className="text-muted-foreground mt-1">
                  Go to the Scenarios tab and click &quot;MC&quot; on a scenario to run Monte Carlo simulation
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ======= TAB: P&L Projection ======= */}
        <TabsContent value="pl">
          {plResult ? (
            <div className="space-y-6">
              {/* P&L Summary KPIs */}
              <div className="grid gap-4 md:grid-cols-5">
                {[
                  { label: 'Total Revenue', value: plResult.summary?.total_revenue, icon: DollarSign, color: 'text-green-600' },
                  { label: 'Gross Margin', value: plResult.summary?.total_gross_margin, sub: `${plResult.summary?.gross_margin_pct}%`, icon: TrendingUp, color: 'text-blue-600' },
                  { label: 'EBITDA', value: plResult.summary?.total_ebitda, sub: `${plResult.summary?.ebitda_pct}%`, icon: Activity, color: 'text-purple-600' },
                  { label: 'Net Income', value: plResult.summary?.total_net_income, sub: `${plResult.summary?.net_margin_pct}%`, icon: Trophy, color: 'text-emerald-600' },
                  { label: 'Units Sold', value: plResult.summary?.total_units, icon: Zap, color: 'text-orange-600', isCurrency: false },
                ].map((kpi, i) => (
                  <Card key={i}>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2">
                        <kpi.icon className={`h-4 w-4 ${kpi.color}`} />
                        <span className="text-xs text-muted-foreground">{kpi.label}</span>
                      </div>
                      <p className="text-xl font-bold mt-1">
                        {kpi.isCurrency === false ? formatCurrency(kpi.value || 0) : `INR ${formatCurrency(kpi.value || 0)}`}
                      </p>
                      {kpi.sub && <p className="text-xs text-muted-foreground">{kpi.sub} margin</p>}
                    </CardContent>
                  </Card>
                ))}
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                {/* Monthly Revenue & Margin Trend */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Monthly P&L Trend</CardTitle>
                    <CardDescription>Revenue, COGS, and Net Income by month</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={280}>
                      <AreaChart data={plResult.monthly_projections || []}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="month_label" fontSize={11} />
                        <YAxis tickFormatter={(v: number) => formatCurrency(v)} fontSize={11} />
                        <Tooltip formatter={(v: any) => `INR ${formatCurrency(Number(v))}`} />
                        <Area type="monotone" dataKey="revenue" stroke="#22c55e" fill="#22c55e" fillOpacity={0.1} name="Revenue" />
                        <Area type="monotone" dataKey="gross_margin" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.1} name="Gross Margin" />
                        <Area type="monotone" dataKey="net_income" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.1} name="Net Income" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                {/* Waterfall */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">P&L Waterfall</CardTitle>
                    <CardDescription>From revenue to net income</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={plResult.waterfall || []}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="label" fontSize={11} />
                        <YAxis tickFormatter={(v: number) => formatCurrency(Math.abs(v))} fontSize={11} />
                        <Tooltip formatter={(v: any) => `INR ${formatCurrency(Math.abs(Number(v)))}`} />
                        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                          {(plResult.waterfall || []).map((item: any, idx: number) => (
                            <Cell
                              key={idx}
                              fill={item.type === 'negative' ? '#ef4444' : item.type === 'subtotal' ? '#3b82f6' : '#22c55e'}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>

              {/* Monthly Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Monthly Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Month</TableHead>
                        <TableHead className="text-right">Revenue</TableHead>
                        <TableHead className="text-right">COGS</TableHead>
                        <TableHead className="text-right">Gross Margin</TableHead>
                        <TableHead className="text-right">GM%</TableHead>
                        <TableHead className="text-right">EBITDA</TableHead>
                        <TableHead className="text-right">Net Income</TableHead>
                        <TableHead className="text-right">Net%</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(plResult.monthly_projections || []).map((m: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium">{m.month_label}</TableCell>
                          <TableCell className="text-right">{formatCurrency(m.revenue)}</TableCell>
                          <TableCell className="text-right text-red-600">{formatCurrency(m.cogs)}</TableCell>
                          <TableCell className="text-right text-blue-600">{formatCurrency(m.gross_margin)}</TableCell>
                          <TableCell className="text-right">{m.gross_margin_pct}%</TableCell>
                          <TableCell className="text-right text-purple-600">{formatCurrency(m.ebitda)}</TableCell>
                          <TableCell className="text-right font-semibold text-green-600">{formatCurrency(m.net_income)}</TableCell>
                          <TableCell className="text-right">{m.net_margin_pct}%</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="p-12 text-center">
                <DollarSign className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold">No P&L Projections</h3>
                <p className="text-muted-foreground mt-1">
                  Go to the Scenarios tab and click &quot;P&L&quot; on a scenario to generate financial projections
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ======= TAB: Sensitivity (Tornado) ======= */}
        <TabsContent value="sensitivity">
          {sensitivityResult ? (
            <div className="space-y-6">
              {/* Header Info */}
              <div className="grid gap-4 md:grid-cols-3">
                <Card>
                  <CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Base Revenue</span>
                    <p className="text-xl font-bold">INR {formatCurrency(sensitivityResult.base_revenue || 0)}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Most Sensitive</span>
                    <p className="text-xl font-bold capitalize">{sensitivityResult.most_sensitive?.replace(/_/g, ' ') || '-'}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Variation Tested</span>
                    <p className="text-xl font-bold">+/- {sensitivityResult.variation_pct}%</p>
                  </CardContent>
                </Card>
              </div>

              {/* Tornado Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Revenue Sensitivity (Tornado Chart)</CardTitle>
                  <CardDescription>Impact of +/-{sensitivityResult.variation_pct}% change in each parameter on revenue</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={50 * (sensitivityResult.tornado_data?.length || 1) + 60}>
                    <BarChart
                      data={(sensitivityResult.tornado_data || []).map((d: any) => ({
                        parameter: d.parameter_label,
                        low: d.revenue.impact_low,
                        high: d.revenue.impact_high,
                      }))}
                      layout="vertical"
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" tickFormatter={(v: number) => formatCurrency(Math.abs(v))} fontSize={11} />
                      <YAxis type="category" dataKey="parameter" width={140} fontSize={12} />
                      <Tooltip formatter={(v: any) => `INR ${formatCurrency(Number(v))}`} />
                      <Bar dataKey="low" fill="#ef4444" name="Decrease" radius={[4, 0, 0, 4]} />
                      <Bar dataKey="high" fill="#22c55e" name="Increase" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Detail Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Parameter Impact Detail</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Parameter</TableHead>
                        <TableHead className="text-right">Revenue (Low)</TableHead>
                        <TableHead className="text-right">Revenue (High)</TableHead>
                        <TableHead className="text-right">Revenue Spread</TableHead>
                        <TableHead className="text-right">Net Income (Low)</TableHead>
                        <TableHead className="text-right">Net Income (High)</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(sensitivityResult.tornado_data || []).map((d: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium">{d.parameter_label}</TableCell>
                          <TableCell className="text-right text-red-600">
                            {d.revenue.impact_low >= 0 ? '+' : ''}{formatCurrency(d.revenue.impact_low)}
                          </TableCell>
                          <TableCell className="text-right text-green-600">
                            +{formatCurrency(d.revenue.impact_high)}
                          </TableCell>
                          <TableCell className="text-right font-semibold">
                            {formatCurrency(d.revenue.spread)}
                          </TableCell>
                          <TableCell className="text-right text-red-600">
                            {formatCurrency(d.net_income.impact_low)}
                          </TableCell>
                          <TableCell className="text-right text-green-600">
                            +{formatCurrency(d.net_income.impact_high)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="p-12 text-center">
                <BarChart3 className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold">No Sensitivity Analysis</h3>
                <p className="text-muted-foreground mt-1">
                  Go to the Scenarios tab and click &quot;Tornado&quot; on a scenario to run sensitivity analysis
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ======= TAB: Quick What-If ======= */}
        <TabsContent value="whatif">
          <div className="grid gap-6 md:grid-cols-3">
            {/* Sliders Panel */}
            <Card className="md:col-span-1">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <SlidersHorizontal className="h-4 w-4" /> Parameters
                </CardTitle>
                <CardDescription>Adjust to see instant impact</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                {[
                  { key: 'demand_change_pct', label: 'Demand Change', color: 'text-blue-600' },
                  { key: 'price_change_pct', label: 'Price Change', color: 'text-green-600' },
                  { key: 'supply_change_pct', label: 'Supply Change', color: 'text-purple-600' },
                  { key: 'lead_time_change_pct', label: 'Lead Time Change', color: 'text-orange-600' },
                  { key: 'cogs_change_pct', label: 'COGS Change', color: 'text-red-600' },
                ].map(({ key, label, color }) => (
                  <div key={key} className="space-y-1">
                    <div className="flex justify-between">
                      <Label className={`text-sm ${color}`}>{label}</Label>
                      <span className="text-sm font-mono font-semibold">
                        {(whatIf as any)[key] > 0 ? '+' : ''}{(whatIf as any)[key]}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="-50"
                      max="50"
                      value={(whatIf as any)[key]}
                      onChange={(e) => setWhatIf(prev => ({ ...prev, [key]: Number(e.target.value) }))}
                      className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                    />
                  </div>
                ))}

                <Button
                  variant="outline"
                  size="sm"
                  className="w-full mt-2"
                  onClick={() => setWhatIf({
                    demand_change_pct: 0, price_change_pct: 0, supply_change_pct: 0,
                    lead_time_change_pct: 0, cogs_change_pct: 0,
                  })}
                >
                  Reset All
                </Button>
              </CardContent>
            </Card>

            {/* Results Panel */}
            <div className="md:col-span-2 space-y-4">
              {whatIfLoading ? (
                <div className="space-y-4">
                  {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24" />)}
                </div>
              ) : whatIfResult ? (
                <>
                  {/* Impact Summary */}
                  <div className="grid gap-4 md:grid-cols-3">
                    <Card>
                      <CardContent className="p-4">
                        <span className="text-sm text-muted-foreground">Revenue Impact</span>
                        <p className={`text-2xl font-bold ${whatIfResult.impact?.revenue_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {whatIfResult.impact?.revenue_change >= 0 ? '+' : ''}{formatCurrency(whatIfResult.impact?.revenue_change || 0)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {whatIfResult.impact?.revenue_change_pct >= 0 ? '+' : ''}{whatIfResult.impact?.revenue_change_pct?.toFixed(1)}%
                        </p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4">
                        <span className="text-sm text-muted-foreground">Margin Impact</span>
                        <p className={`text-2xl font-bold ${whatIfResult.impact?.margin_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {whatIfResult.impact?.margin_change >= 0 ? '+' : ''}{formatCurrency(whatIfResult.impact?.margin_change || 0)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {whatIfResult.impact?.margin_change_pct >= 0 ? '+' : ''}{whatIfResult.impact?.margin_change_pct?.toFixed(1)}%
                        </p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4">
                        <span className="text-sm text-muted-foreground">Units Impact</span>
                        <p className={`text-2xl font-bold ${whatIfResult.impact?.units_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {whatIfResult.impact?.units_change >= 0 ? '+' : ''}{formatCurrency(whatIfResult.impact?.units_change || 0)}
                        </p>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Baseline vs Projected */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">90-Day Projection: Baseline vs Adjusted</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={250}>
                        <BarChart
                          data={[
                            { metric: 'Revenue', baseline: whatIfResult.baseline?.revenue || 0, projected: whatIfResult.projected?.revenue || 0 },
                            { metric: 'COGS', baseline: whatIfResult.baseline?.cogs || 0, projected: whatIfResult.projected?.cogs || 0 },
                            { metric: 'Gross Margin', baseline: whatIfResult.baseline?.gross_margin || 0, projected: whatIfResult.projected?.gross_margin || 0 },
                            { metric: 'Net Income', baseline: whatIfResult.baseline?.net_income || 0, projected: whatIfResult.projected?.net_income || 0 },
                          ]}
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="metric" fontSize={12} />
                          <YAxis tickFormatter={(v: number) => formatCurrency(v)} fontSize={11} />
                          <Tooltip formatter={(v: any) => `INR ${formatCurrency(Number(v))}`} />
                          <Bar dataKey="baseline" fill="#94a3b8" name="Baseline" radius={[4, 4, 0, 0]} />
                          <Bar dataKey="projected" fill="#8b5cf6" name="Projected" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </>
              ) : (
                <Card>
                  <CardContent className="p-12 text-center">
                    <SlidersHorizontal className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                    <p className="text-muted-foreground">Adjust the sliders to see projected impact</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
