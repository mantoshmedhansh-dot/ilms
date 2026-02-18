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
  RotateCcw,
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

const statusConfig: Record<string, { dot: string; badge: string }> = {
  DRAFT: { dot: 'bg-gray-400', badge: 'bg-gray-100 text-gray-700 dark:bg-gray-800/50 dark:text-gray-300' },
  RUNNING: { dot: 'bg-blue-500 animate-pulse', badge: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  COMPLETED: { dot: 'bg-green-500', badge: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300' },
  FAILED: { dot: 'bg-red-500', badge: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300' },
  ARCHIVED: { dot: 'bg-purple-500', badge: 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300' },
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
      const res = await apiClient.post('/snop/scenario/what-if', whatIf);
      return res.data;
    },
    enabled: activeTab === 'whatif',
  });

  // ---- Mutations ----
  const runMonteCarlo = useMutation({
    mutationFn: async (scenarioId: string) => {
      const res = await apiClient.post('/snop/scenario/monte-carlo', {
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
      const res = await apiClient.post('/snop/scenario/financial-pl', {
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
      const res = await apiClient.post('/snop/scenario/sensitivity', {
        scenario_id: scenarioId,
        variation_pct: 20,
      });
      return res.data;
    },
  });

  // ---- Loading Skeleton ----
  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="rounded-xl bg-gradient-to-r from-purple-600/5 via-indigo-600/5 to-blue-600/5 p-6">
          <div className="flex items-center gap-4">
            <Skeleton className="h-12 w-12 rounded-xl" />
            <div className="space-y-2">
              <Skeleton className="h-7 w-72" />
              <Skeleton className="h-4 w-96" />
            </div>
          </div>
        </div>
        <div className="grid gap-5 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="overflow-hidden">
              <div className="h-0.5 bg-muted animate-pulse" />
              <CardContent className="p-5 space-y-3">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-8 w-8 rounded-lg" />
                  <Skeleton className="h-4 w-24" />
                </div>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Skeleton className="h-11 w-full max-w-2xl rounded-lg" />
        <Card>
          <CardContent className="p-6 space-y-4">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-64 rounded-lg" />
          </CardContent>
        </Card>
      </div>
    );
  }

  const completedScenarios = scenarios?.items?.filter((s: any) => s.status === 'COMPLETED') || [];

  // Use fresh mutation data if available, otherwise load from latest completed scenario
  const latestMC = completedScenarios.find((s: any) => s.results?.monte_carlo);
  const latestPL = completedScenarios.find((s: any) => s.results?.financial_pl);
  const latestSensitivity = completedScenarios.find((s: any) => s.results?.sensitivity);

  const mcResult = runMonteCarlo.data || latestMC?.results?.monte_carlo || null;
  const plResult = runPL.data || latestPL?.results?.financial_pl || null;
  const sensitivityResult = runSensitivity.data || latestSensitivity?.results?.sensitivity || null;

  return (
    <div className="space-y-6 p-6">
      {/* ===== Header ===== */}
      <div className="rounded-xl bg-gradient-to-r from-purple-600/10 via-indigo-600/5 to-blue-600/10 border border-purple-200/40 dark:border-purple-500/10 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="icon-bg-lg bg-purple-100 dark:bg-purple-900/40 ring-4 ring-purple-500/10 dark:ring-purple-500/20">
              <Target className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight">Advanced Scenario Engine</h1>
                <Badge variant="secondary" className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 border-0 gap-1.5 text-xs">
                  <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                  Live
                </Badge>
              </div>
              <p className="text-muted-foreground mt-0.5">
                Monte Carlo simulation, P&L projections, sensitivity analysis & digital twin
              </p>
            </div>
          </div>
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* ===== Summary KPI Cards ===== */}
      <div className="grid gap-5 md:grid-cols-4">
        {[
          { label: 'Total Scenarios', value: scenarios?.total || 0, icon: Target, topBorder: 'border-t-purple-500', iconBg: 'bg-purple-100 dark:bg-purple-900/30', iconColor: 'text-purple-600 dark:text-purple-400' },
          { label: 'Monte Carlo Runs', value: completedScenarios.filter((s: any) => s.results?.monte_carlo).length, icon: Dice5, topBorder: 'border-t-blue-500', iconBg: 'bg-blue-100 dark:bg-blue-900/30', iconColor: 'text-blue-600 dark:text-blue-400' },
          { label: 'Completed', value: completedScenarios.length, icon: CheckCircle, topBorder: 'border-t-green-500', iconBg: 'bg-green-100 dark:bg-green-900/30', iconColor: 'text-green-600 dark:text-green-400' },
          { label: 'Draft', value: scenarios?.items?.filter((s: any) => s.status === 'DRAFT').length || 0, icon: AlertCircle, topBorder: 'border-t-amber-500', iconBg: 'bg-amber-100 dark:bg-amber-900/30', iconColor: 'text-amber-600 dark:text-amber-400' },
        ].map((card, i) => (
          <Card key={i} className={`card-lift border-t-2 ${card.topBorder} overflow-hidden`}>
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className={`icon-bg-sm ${card.iconBg}`}>
                  <card.icon className={`h-4 w-4 ${card.iconColor}`} />
                </div>
                <span className="text-sm text-muted-foreground">{card.label}</span>
              </div>
              <p className="text-2xl font-bold mt-3 tabular-nums">{card.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ===== Tabs ===== */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full justify-start h-11 p-1 bg-muted/60">
          <TabsTrigger value="scenarios" className="gap-1.5 text-sm px-4 data-[state=active]:shadow-sm">
            <Target className="h-4 w-4" /> Scenarios
          </TabsTrigger>
          <TabsTrigger value="montecarlo" className="gap-1.5 text-sm px-4 data-[state=active]:shadow-sm">
            <Dice5 className="h-4 w-4" /> Monte Carlo
            {mcResult && <span className="ml-1 h-1.5 w-1.5 rounded-full bg-purple-500" />}
          </TabsTrigger>
          <TabsTrigger value="pl" className="gap-1.5 text-sm px-4 data-[state=active]:shadow-sm">
            <DollarSign className="h-4 w-4" /> P&L Projection
            {plResult && <span className="ml-1 h-1.5 w-1.5 rounded-full bg-green-500" />}
          </TabsTrigger>
          <TabsTrigger value="sensitivity" className="gap-1.5 text-sm px-4 data-[state=active]:shadow-sm">
            <BarChart3 className="h-4 w-4" /> Sensitivity
            {sensitivityResult && <span className="ml-1 h-1.5 w-1.5 rounded-full bg-blue-500" />}
          </TabsTrigger>
          <TabsTrigger value="whatif" className="gap-1.5 text-sm px-4 data-[state=active]:shadow-sm">
            <SlidersHorizontal className="h-4 w-4" /> What-If
          </TabsTrigger>
        </TabsList>

        {/* ======= TAB: Scenarios List ======= */}
        <TabsContent value="scenarios" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>All Scenarios</CardTitle>
              <CardDescription>Select a scenario to run advanced analysis</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
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
                    scenarios.items.map((sc: any, idx: number) => (
                      <TableRow key={sc.id} className={`hover:bg-muted/50 transition-colors ${idx % 2 !== 0 ? 'bg-muted/20' : ''}`}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{sc.name || sc.scenario_name}</p>
                            <p className="text-xs text-muted-foreground">{sc.description || 'No description'}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary" className={`gap-1.5 border-0 ${statusConfig[sc.status]?.badge || ''}`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${statusConfig[sc.status]?.dot || 'bg-gray-400'}`} />
                            {sc.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="tabular-nums">
                          {sc.results?.projected_revenue
                            ? `INR ${formatCurrency(sc.results.projected_revenue)}`
                            : <span className="text-muted-foreground">-</span>
                          }
                        </TableCell>
                        <TableCell className="tabular-nums">
                          {sc.results?.service_level_pct
                            ? `${sc.results.service_level_pct.toFixed(1)}%`
                            : <span className="text-muted-foreground">-</span>
                          }
                        </TableCell>
                        <TableCell className="tabular-nums">
                          {sc.results?.stockout_probability != null
                            ? <span className={`font-medium ${sc.results.stockout_probability > 0.1 ? 'text-red-600' : 'text-green-600'}`}>
                                {(sc.results.stockout_probability * 100).toFixed(1)}%
                              </span>
                            : <span className="text-muted-foreground">-</span>
                          }
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button
                              size="sm" variant="outline"
                              onClick={() => runMonteCarlo.mutate(sc.id)}
                              disabled={runMonteCarlo.isPending}
                              className="h-8 text-xs"
                              title="Run Monte Carlo simulation"
                            >
                              <Dice5 className="h-3.5 w-3.5 mr-1.5" /> MC
                            </Button>
                            <Button
                              size="sm" variant="outline"
                              onClick={() => runPL.mutate(sc.id)}
                              disabled={runPL.isPending}
                              className="h-8 text-xs"
                              title="Generate P&L projection"
                            >
                              <DollarSign className="h-3.5 w-3.5 mr-1.5" /> P&L
                            </Button>
                            <Button
                              size="sm" variant="outline"
                              onClick={() => runSensitivity.mutate(sc.id)}
                              disabled={runSensitivity.isPending}
                              className="h-8 text-xs"
                              title="Run sensitivity analysis"
                            >
                              <BarChart3 className="h-3.5 w-3.5 mr-1.5" /> Tornado
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={6} className="h-64">
                        <div className="flex flex-col items-center justify-center text-center">
                          <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-100 to-indigo-100 dark:from-purple-900/20 dark:to-indigo-900/20">
                            <Target className="h-10 w-10 text-purple-400" />
                          </div>
                          <h3 className="text-lg font-semibold">No scenarios created yet</h3>
                          <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                            Create what-if scenarios to run advanced simulations like Monte Carlo, P&L projections, and sensitivity analysis
                          </p>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ======= TAB: Monte Carlo ======= */}
        <TabsContent value="montecarlo" className="mt-4">
          {mcResult ? (
            <div className="space-y-6">
              {/* KPIs */}
              <div className="grid gap-5 md:grid-cols-5">
                {[
                  { label: 'Expected Revenue', value: `INR ${formatCurrency(mcResult.revenue?.mean || 0)}`, icon: DollarSign, color: 'text-green-600 dark:text-green-400', borderColor: 'border-l-green-500', iconBg: 'bg-green-100 dark:bg-green-900/30' },
                  { label: 'Expected Margin', value: `INR ${formatCurrency(mcResult.gross_margin?.mean || 0)}`, icon: TrendingUp, color: 'text-blue-600 dark:text-blue-400', borderColor: 'border-l-blue-500', iconBg: 'bg-blue-100 dark:bg-blue-900/30' },
                  { label: 'Stockout Probability', value: `${((mcResult.stockout_probability || 0) * 100).toFixed(1)}%`, icon: AlertCircle, color: mcResult.stockout_probability > 0.1 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400', borderColor: mcResult.stockout_probability > 0.1 ? 'border-l-red-500' : 'border-l-green-500', iconBg: mcResult.stockout_probability > 0.1 ? 'bg-red-100 dark:bg-red-900/30' : 'bg-green-100 dark:bg-green-900/30' },
                  { label: 'Service Level', value: `${(mcResult.service_level?.mean || 0).toFixed(1)}%`, icon: CheckCircle, color: 'text-emerald-600 dark:text-emerald-400', borderColor: 'border-l-emerald-500', iconBg: 'bg-emerald-100 dark:bg-emerald-900/30' },
                  { label: 'Simulations', value: mcResult.num_simulations, icon: Dice5, color: 'text-purple-600 dark:text-purple-400', borderColor: 'border-l-purple-500', iconBg: 'bg-purple-100 dark:bg-purple-900/30' },
                ].map((kpi, i) => (
                  <Card key={i} className={`card-lift border-l-[3px] ${kpi.borderColor}`}>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2.5">
                        <div className={`icon-bg-sm ${kpi.iconBg}`}>
                          <kpi.icon className={`h-4 w-4 ${kpi.color}`} />
                        </div>
                        <span className="text-xs text-muted-foreground">{kpi.label}</span>
                      </div>
                      <p className="text-xl font-bold mt-2 tabular-nums">{kpi.value}</p>
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
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis dataKey="range_start" tickFormatter={(v: number) => formatCurrency(v)} fontSize={11} />
                        <YAxis tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} fontSize={11} />
                        <Tooltip
                          formatter={(value: any) => `${(Number(value) * 100).toFixed(1)}%`}
                          labelFormatter={(v: any) => `INR ${formatCurrency(Number(v))}`}
                          contentStyle={{ borderRadius: '8px', border: '1px solid hsl(var(--border))', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                        />
                        <Bar dataKey="probability" radius={[6, 6, 0, 0]}>
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
                    <div className="space-y-5">
                      {[
                        { label: 'Revenue', data: mcResult.revenue, color: 'from-green-400 to-emerald-500' },
                        { label: 'Gross Margin', data: mcResult.gross_margin, color: 'from-blue-400 to-indigo-500' },
                        { label: 'Net Profit', data: mcResult.net_profit, color: 'from-purple-400 to-violet-500' },
                        { label: 'Units Sold', data: mcResult.units_sold, color: 'from-orange-400 to-amber-500' },
                        { label: 'Service Level %', data: mcResult.service_level, color: 'from-teal-400 to-cyan-500' },
                      ].map((item, i) => (
                        <div key={i} className="space-y-1.5">
                          <div className="flex justify-between text-sm">
                            <span className="font-medium">{item.label}</span>
                            <span className="text-muted-foreground tabular-nums">
                              Mean: {item.label.includes('%') ? `${item.data?.mean?.toFixed(1)}%` : `INR ${formatCurrency(item.data?.mean || 0)}`}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span className="tabular-nums w-14 text-right shrink-0">P5: {formatCurrency(item.data?.p5 || 0)}</span>
                            <div className="flex-1 h-2.5 bg-muted rounded-full overflow-hidden">
                              <div
                                className={`h-full bg-gradient-to-r ${item.color} rounded-full`}
                                style={{ width: '100%' }}
                              />
                            </div>
                            <span className="tabular-nums w-16 shrink-0">P95: {formatCurrency(item.data?.p95 || 0)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <Card className="border-dashed">
              <CardContent className="p-16 text-center">
                <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-100 to-indigo-100 dark:from-purple-900/20 dark:to-indigo-900/20">
                  <Dice5 className="h-10 w-10 text-purple-400" />
                </div>
                <h3 className="text-lg font-semibold">No Monte Carlo Results</h3>
                <p className="text-muted-foreground mt-2 max-w-sm mx-auto">
                  Go to the Scenarios tab and click &quot;MC&quot; on a scenario to run Monte Carlo simulation
                </p>
                <Button variant="outline" className="mt-5" onClick={() => setActiveTab('scenarios')}>
                  <ArrowRight className="h-4 w-4 mr-2" /> Go to Scenarios
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ======= TAB: P&L Projection ======= */}
        <TabsContent value="pl" className="mt-4">
          {plResult ? (
            <div className="space-y-6">
              {/* P&L Summary KPIs */}
              <div className="grid gap-5 md:grid-cols-5">
                {[
                  { label: 'Total Revenue', value: plResult.summary?.total_revenue, icon: DollarSign, color: 'text-green-600 dark:text-green-400', borderColor: 'border-l-green-500', iconBg: 'bg-green-100 dark:bg-green-900/30', sub: null as string | null, isCurrency: true },
                  { label: 'Gross Margin', value: plResult.summary?.total_gross_margin, sub: `${plResult.summary?.gross_margin_pct}%`, icon: TrendingUp, color: 'text-blue-600 dark:text-blue-400', borderColor: 'border-l-blue-500', iconBg: 'bg-blue-100 dark:bg-blue-900/30', isCurrency: true },
                  { label: 'EBITDA', value: plResult.summary?.total_ebitda, sub: `${plResult.summary?.ebitda_pct}%`, icon: Activity, color: 'text-purple-600 dark:text-purple-400', borderColor: 'border-l-purple-500', iconBg: 'bg-purple-100 dark:bg-purple-900/30', isCurrency: true },
                  { label: 'Net Income', value: plResult.summary?.total_net_income, sub: `${plResult.summary?.net_margin_pct}%`, icon: Trophy, color: 'text-emerald-600 dark:text-emerald-400', borderColor: 'border-l-emerald-500', iconBg: 'bg-emerald-100 dark:bg-emerald-900/30', isCurrency: true },
                  { label: 'Units Sold', value: plResult.summary?.total_units, icon: Zap, color: 'text-orange-600 dark:text-orange-400', borderColor: 'border-l-orange-500', iconBg: 'bg-orange-100 dark:bg-orange-900/30', isCurrency: false, sub: null as string | null },
                ].map((kpi, i) => (
                  <Card key={i} className={`card-lift border-l-[3px] ${kpi.borderColor}`}>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2.5">
                        <div className={`icon-bg-sm ${kpi.iconBg}`}>
                          <kpi.icon className={`h-4 w-4 ${kpi.color}`} />
                        </div>
                        <span className="text-xs text-muted-foreground">{kpi.label}</span>
                      </div>
                      <p className="text-xl font-bold mt-2 tabular-nums">
                        {kpi.isCurrency === false ? formatCurrency(kpi.value || 0) : `INR ${formatCurrency(kpi.value || 0)}`}
                      </p>
                      {kpi.sub && (
                        <Badge variant="secondary" className="mt-1.5 text-xs font-medium">
                          {kpi.sub} margin
                        </Badge>
                      )}
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
                        <defs>
                          <linearGradient id="gradRevenue" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                          </linearGradient>
                          <linearGradient id="gradMargin" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                          </linearGradient>
                          <linearGradient id="gradNetIncome" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis dataKey="month_label" fontSize={11} />
                        <YAxis tickFormatter={(v: number) => formatCurrency(v)} fontSize={11} />
                        <Tooltip
                          formatter={(v: any) => `INR ${formatCurrency(Number(v))}`}
                          contentStyle={{ borderRadius: '8px', border: '1px solid hsl(var(--border))', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                        />
                        <Area type="monotone" dataKey="revenue" stroke="#22c55e" strokeWidth={2} fill="url(#gradRevenue)" name="Revenue" />
                        <Area type="monotone" dataKey="gross_margin" stroke="#3b82f6" strokeWidth={2} fill="url(#gradMargin)" name="Gross Margin" />
                        <Area type="monotone" dataKey="net_income" stroke="#8b5cf6" strokeWidth={2} fill="url(#gradNetIncome)" name="Net Income" />
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
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis dataKey="label" fontSize={11} />
                        <YAxis tickFormatter={(v: number) => formatCurrency(Math.abs(v))} fontSize={11} />
                        <Tooltip
                          formatter={(v: any) => `INR ${formatCurrency(Math.abs(Number(v)))}`}
                          contentStyle={{ borderRadius: '8px', border: '1px solid hsl(var(--border))', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                        />
                        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                          {(plResult.waterfall || []).map((item: any, idx: number) => (
                            <Cell
                              key={idx}
                              fill={item.type === 'negative' ? '#ef4444' : item.type === 'subtotal' ? '#6366f1' : '#22c55e'}
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
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-muted/30">
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
                          <TableRow key={i} className={`hover:bg-muted/50 transition-colors ${i % 2 !== 0 ? 'bg-muted/20' : ''}`}>
                            <TableCell className="font-medium">{m.month_label}</TableCell>
                            <TableCell className="text-right tabular-nums">{formatCurrency(m.revenue)}</TableCell>
                            <TableCell className="text-right tabular-nums text-red-600 dark:text-red-400">{formatCurrency(m.cogs)}</TableCell>
                            <TableCell className="text-right tabular-nums text-blue-600 dark:text-blue-400">{formatCurrency(m.gross_margin)}</TableCell>
                            <TableCell className="text-right tabular-nums">{m.gross_margin_pct}%</TableCell>
                            <TableCell className="text-right tabular-nums text-purple-600 dark:text-purple-400">{formatCurrency(m.ebitda)}</TableCell>
                            <TableCell className="text-right tabular-nums font-semibold text-green-600 dark:text-green-400">{formatCurrency(m.net_income)}</TableCell>
                            <TableCell className="text-right tabular-nums">{m.net_margin_pct}%</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card className="border-dashed">
              <CardContent className="p-16 text-center">
                <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-green-100 to-emerald-100 dark:from-green-900/20 dark:to-emerald-900/20">
                  <DollarSign className="h-10 w-10 text-green-400" />
                </div>
                <h3 className="text-lg font-semibold">No P&L Projections</h3>
                <p className="text-muted-foreground mt-2 max-w-sm mx-auto">
                  Go to the Scenarios tab and click &quot;P&L&quot; on a scenario to generate financial projections
                </p>
                <Button variant="outline" className="mt-5" onClick={() => setActiveTab('scenarios')}>
                  <ArrowRight className="h-4 w-4 mr-2" /> Go to Scenarios
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ======= TAB: Sensitivity (Tornado) ======= */}
        <TabsContent value="sensitivity" className="mt-4">
          {sensitivityResult ? (
            <div className="space-y-6">
              {/* Header Info */}
              <div className="grid gap-5 md:grid-cols-3">
                <Card className="card-lift border-l-[3px] border-l-green-500">
                  <CardContent className="p-5">
                    <div className="flex items-center gap-2.5">
                      <div className="icon-bg-sm bg-green-100 dark:bg-green-900/30">
                        <DollarSign className="h-4 w-4 text-green-600 dark:text-green-400" />
                      </div>
                      <span className="text-sm text-muted-foreground">Base Revenue</span>
                    </div>
                    <p className="text-xl font-bold mt-2 tabular-nums">INR {formatCurrency(sensitivityResult.base_revenue || 0)}</p>
                  </CardContent>
                </Card>
                <Card className="card-lift border-l-[3px] border-l-amber-500">
                  <CardContent className="p-5">
                    <div className="flex items-center gap-2.5">
                      <div className="icon-bg-sm bg-amber-100 dark:bg-amber-900/30">
                        <Zap className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                      </div>
                      <span className="text-sm text-muted-foreground">Most Sensitive</span>
                    </div>
                    <p className="text-xl font-bold mt-2 capitalize">{sensitivityResult.most_sensitive?.replace(/_/g, ' ') || '-'}</p>
                  </CardContent>
                </Card>
                <Card className="card-lift border-l-[3px] border-l-blue-500">
                  <CardContent className="p-5">
                    <div className="flex items-center gap-2.5">
                      <div className="icon-bg-sm bg-blue-100 dark:bg-blue-900/30">
                        <Activity className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                      </div>
                      <span className="text-sm text-muted-foreground">Variation Tested</span>
                    </div>
                    <p className="text-xl font-bold mt-2 tabular-nums">+/- {sensitivityResult.variation_pct}%</p>
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
                      <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                      <XAxis type="number" tickFormatter={(v: number) => formatCurrency(Math.abs(v))} fontSize={11} />
                      <YAxis type="category" dataKey="parameter" width={140} fontSize={12} />
                      <Tooltip
                        formatter={(v: any) => `INR ${formatCurrency(Number(v))}`}
                        contentStyle={{ borderRadius: '8px', border: '1px solid hsl(var(--border))', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      />
                      <Bar dataKey="low" fill="#ef4444" name="Decrease" radius={[6, 0, 0, 6]} />
                      <Bar dataKey="high" fill="#22c55e" name="Increase" radius={[0, 6, 6, 0]} />
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
                      <TableRow className="bg-muted/30">
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
                        <TableRow key={i} className={`hover:bg-muted/50 transition-colors ${i % 2 !== 0 ? 'bg-muted/20' : ''}`}>
                          <TableCell className="font-medium">{d.parameter_label}</TableCell>
                          <TableCell className="text-right tabular-nums text-red-600 dark:text-red-400">
                            {d.revenue.impact_low >= 0 ? '+' : ''}{formatCurrency(d.revenue.impact_low)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-green-600 dark:text-green-400">
                            +{formatCurrency(d.revenue.impact_high)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums font-semibold">
                            {formatCurrency(d.revenue.spread)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-red-600 dark:text-red-400">
                            {formatCurrency(d.net_income.impact_low)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-green-600 dark:text-green-400">
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
            <Card className="border-dashed">
              <CardContent className="p-16 text-center">
                <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/20 dark:to-indigo-900/20">
                  <BarChart3 className="h-10 w-10 text-blue-400" />
                </div>
                <h3 className="text-lg font-semibold">No Sensitivity Analysis</h3>
                <p className="text-muted-foreground mt-2 max-w-sm mx-auto">
                  Go to the Scenarios tab and click &quot;Tornado&quot; on a scenario to run sensitivity analysis
                </p>
                <Button variant="outline" className="mt-5" onClick={() => setActiveTab('scenarios')}>
                  <ArrowRight className="h-4 w-4 mr-2" /> Go to Scenarios
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ======= TAB: Quick What-If ======= */}
        <TabsContent value="whatif" className="mt-4">
          <div className="grid gap-6 md:grid-cols-3">
            {/* Sliders Panel */}
            <Card className="md:col-span-1">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2.5">
                  <div className="icon-bg-sm bg-indigo-100 dark:bg-indigo-900/30">
                    <SlidersHorizontal className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                  </div>
                  Parameters
                </CardTitle>
                <CardDescription>Adjust to see instant impact</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { key: 'demand_change_pct', label: 'Demand Change', color: 'text-blue-600', accent: 'border-l-blue-500', bg: 'bg-blue-50/50 dark:bg-blue-950/20' },
                  { key: 'price_change_pct', label: 'Price Change', color: 'text-green-600', accent: 'border-l-green-500', bg: 'bg-green-50/50 dark:bg-green-950/20' },
                  { key: 'supply_change_pct', label: 'Supply Change', color: 'text-purple-600', accent: 'border-l-purple-500', bg: 'bg-purple-50/50 dark:bg-purple-950/20' },
                  { key: 'lead_time_change_pct', label: 'Lead Time Change', color: 'text-orange-600', accent: 'border-l-orange-500', bg: 'bg-orange-50/50 dark:bg-orange-950/20' },
                  { key: 'cogs_change_pct', label: 'COGS Change', color: 'text-red-600', accent: 'border-l-red-500', bg: 'bg-red-50/50 dark:bg-red-950/20' },
                ].map(({ key, label, color, accent, bg }) => (
                  <div key={key} className={`rounded-lg border border-l-[3px] ${accent} p-3 ${bg}`}>
                    <div className="flex justify-between mb-2">
                      <Label className={`text-sm font-medium ${color}`}>{label}</Label>
                      <span className="text-sm font-mono font-semibold tabular-nums">
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
                  variant="ghost"
                  size="sm"
                  className="w-full mt-2 text-muted-foreground hover:text-foreground"
                  onClick={() => setWhatIf({
                    demand_change_pct: 0, price_change_pct: 0, supply_change_pct: 0,
                    lead_time_change_pct: 0, cogs_change_pct: 0,
                  })}
                >
                  <RotateCcw className="h-3.5 w-3.5 mr-2" />
                  Reset All
                </Button>
              </CardContent>
            </Card>

            {/* Results Panel */}
            <div className="md:col-span-2 space-y-4">
              {whatIfLoading ? (
                <div className="space-y-4">
                  {[...Array(3)].map((_, i) => (
                    <Card key={i}>
                      <CardContent className="p-4 space-y-3">
                        <Skeleton className="h-4 w-32" />
                        <Skeleton className="h-8 w-24" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : whatIfResult ? (
                <>
                  {/* Impact Summary */}
                  <div className="grid gap-4 md:grid-cols-3">
                    {[
                      { label: 'Revenue Impact', value: whatIfResult.impact?.revenue_change, pct: whatIfResult.impact?.revenue_change_pct, borderColor: 'border-l-green-500', iconBg: 'bg-green-100 dark:bg-green-900/30', icon: DollarSign, iconColor: 'text-green-600 dark:text-green-400' },
                      { label: 'Margin Impact', value: whatIfResult.impact?.margin_change, pct: whatIfResult.impact?.margin_change_pct, borderColor: 'border-l-blue-500', iconBg: 'bg-blue-100 dark:bg-blue-900/30', icon: TrendingUp, iconColor: 'text-blue-600 dark:text-blue-400' },
                      { label: 'Units Impact', value: whatIfResult.impact?.units_change, pct: null as number | null, borderColor: 'border-l-purple-500', iconBg: 'bg-purple-100 dark:bg-purple-900/30', icon: Zap, iconColor: 'text-purple-600 dark:text-purple-400' },
                    ].map((card, i) => (
                      <Card key={i} className={`card-lift border-l-[3px] ${card.borderColor}`}>
                        <CardContent className="p-4">
                          <div className="flex items-center gap-2.5">
                            <div className={`icon-bg-sm ${card.iconBg}`}>
                              <card.icon className={`h-4 w-4 ${card.iconColor}`} />
                            </div>
                            <span className="text-sm text-muted-foreground">{card.label}</span>
                          </div>
                          <p className={`text-2xl font-bold mt-2 tabular-nums ${(card.value || 0) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                            {(card.value || 0) >= 0 ? '+' : ''}{formatCurrency(card.value || 0)}
                          </p>
                          {card.pct != null && (
                            <p className="text-xs text-muted-foreground mt-0.5 tabular-nums">
                              {card.pct >= 0 ? '+' : ''}{card.pct?.toFixed(1)}%
                            </p>
                          )}
                        </CardContent>
                      </Card>
                    ))}
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
                          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                          <XAxis dataKey="metric" fontSize={12} />
                          <YAxis tickFormatter={(v: number) => formatCurrency(v)} fontSize={11} />
                          <Tooltip
                            formatter={(v: any) => `INR ${formatCurrency(Number(v))}`}
                            contentStyle={{ borderRadius: '8px', border: '1px solid hsl(var(--border))', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                          />
                          <Bar dataKey="baseline" fill="#94a3b8" name="Baseline" radius={[6, 6, 0, 0]} />
                          <Bar dataKey="projected" fill="#8b5cf6" name="Projected" radius={[6, 6, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </>
              ) : (
                <Card className="border-dashed">
                  <CardContent className="p-16 text-center">
                    <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-100 to-purple-100 dark:from-indigo-900/20 dark:to-purple-900/20">
                      <SlidersHorizontal className="h-10 w-10 text-indigo-400" />
                    </div>
                    <h3 className="text-lg font-semibold">Adjust Parameters</h3>
                    <p className="text-muted-foreground mt-2">
                      Move the sliders to see projected impact on your supply chain
                    </p>
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
