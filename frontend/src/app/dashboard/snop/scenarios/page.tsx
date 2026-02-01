'use client';

import { useQuery } from '@tanstack/react-query';
import {
  Target,
  Plus,
  RefreshCw,
  Play,
  Pause,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';

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
import { snopApi } from '@/lib/api';

export default function ScenariosPage() {
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
          <div className="p-2 bg-purple-100 rounded-lg">
            <Target className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Scenario Analysis</h1>
            <p className="text-muted-foreground">
              What-if simulations for strategic planning
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Scenario
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
              <Play className="h-4 w-4 text-blue-600" />
              <span className="text-sm text-muted-foreground">Running</span>
            </div>
            <p className="text-2xl font-bold mt-2">
              {scenarios?.items?.filter((s: any) => s.status === 'RUNNING').length || 0}
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
              {scenarios?.items?.filter((s: any) => s.status === 'COMPLETED').length || 0}
            </p>
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

      {/* Scenarios Table */}
      <Card>
        <CardHeader>
          <CardTitle>Scenarios</CardTitle>
          <CardDescription>Compare different planning scenarios</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Scenario Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Revenue Impact</TableHead>
                <TableHead>Cost Impact</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {scenarios?.items?.length > 0 ? (
                scenarios.items.map((scenario: any) => (
                  <TableRow key={scenario.id}>
                    <TableCell className="font-medium">{scenario.name}</TableCell>
                    <TableCell className="text-muted-foreground max-w-xs truncate">
                      {scenario.description}
                    </TableCell>
                    <TableCell>
                      {scenario.results?.revenue_impact ? (
                        <span className={scenario.results.revenue_impact >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {scenario.results.revenue_impact >= 0 ? (
                            <TrendingUp className="h-4 w-4 inline mr-1" />
                          ) : (
                            <TrendingDown className="h-4 w-4 inline mr-1" />
                          )}
                          {scenario.results.revenue_impact.toFixed(1)}%
                        </span>
                      ) : '-'}
                    </TableCell>
                    <TableCell>
                      {scenario.results?.cost_impact ? (
                        <span className={scenario.results.cost_impact <= 0 ? 'text-green-600' : 'text-red-600'}>
                          {scenario.results.cost_impact.toFixed(1)}%
                        </span>
                      ) : '-'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={
                        scenario.status === 'COMPLETED' ? 'default' :
                        scenario.status === 'RUNNING' ? 'secondary' :
                        'outline'
                      }>
                        {scenario.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(scenario.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {scenario.status === 'DRAFT' && (
                        <Button variant="ghost" size="sm">
                          <Play className="h-4 w-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    <Target className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No scenarios created yet</p>
                    <p className="text-sm">Create what-if scenarios to compare strategies</p>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
