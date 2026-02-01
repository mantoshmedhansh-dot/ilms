'use client';

import { useQuery } from '@tanstack/react-query';
import {
  GitBranch,
  Plus,
  RefreshCw,
  Factory,
  ShoppingCart,
  Truck,
  CheckCircle,
  Clock,
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

export default function SupplyPlansPage() {
  const { data: plans, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['snop-supply-plans'],
    queryFn: async () => {
      try {
        return await snopApi.getSupplyPlans();
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
          <div className="p-2 bg-green-100 rounded-lg">
            <GitBranch className="h-6 w-6 text-green-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Supply Planning</h1>
            <p className="text-muted-foreground">
              Production scheduling and procurement planning
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
            Create Plan
          </Button>
        </div>
      </div>

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
                    <TableCell>{plan.total_quantity?.toLocaleString() || '-'}</TableCell>
                    <TableCell>
                      <span className={plan.capacity_utilization >= 90 ? 'text-red-600' : 'text-green-600'}>
                        {plan.capacity_utilization?.toFixed(1) || '-'}%
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
    </div>
  );
}
