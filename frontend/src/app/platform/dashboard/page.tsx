'use client';

import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import Link from 'next/link';
import { Building2, Users, DollarSign, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { platformAdminApi } from '@/lib/api/platform-admin';
import { StatCard } from '@/components/platform/stat-card';
import { TenantStatusBadge } from '@/components/platform/tenant-status-badge';

const STATUS_COLORS: Record<string, string> = {
  active: '#10B981',
  pending: '#F59E0B',
  pending_setup: '#F59E0B',
  suspended: '#EF4444',
  cancelled: '#6B7280',
};

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
};

export default function PlatformDashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['platform-statistics'],
    queryFn: platformAdminApi.getStatistics,
  });

  const { data: tenantsData } = useQuery({
    queryKey: ['platform-tenants-recent'],
    queryFn: () => platformAdminApi.listTenants({ page: 1, size: 100 }),
  });

  const statusData = stats
    ? [
        { name: 'Active', value: stats.active_tenants, color: STATUS_COLORS.active },
        { name: 'Pending', value: stats.pending_tenants, color: STATUS_COLORS.pending },
        { name: 'Suspended', value: stats.suspended_tenants, color: STATUS_COLORS.suspended },
      ].filter((d) => d.value > 0)
    : [];

  const moduleData = (stats?.most_popular_modules || []).slice(0, 8).map((m) => ({
    module_name: m.name,
    tenant_count: m.subscriptions,
  }));

  const recentTenants = tenantsData?.tenants?.slice(0, 5) || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Platform Overview</h1>
        <p className="text-muted-foreground">
          Monitor all tenants, revenue, and system health.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Clients"
          value={stats?.total_tenants ?? 0}
          icon={<Building2 className="h-4 w-4" />}
          description="All registered tenants"
          isLoading={isLoading}
        />
        <StatCard
          title="Active Clients"
          value={stats?.active_tenants ?? 0}
          icon={<Users className="h-4 w-4" />}
          description="Currently active"
          isLoading={isLoading}
        />
        <StatCard
          title="Monthly Revenue (MRR)"
          value={formatCurrency(stats?.total_revenue_monthly ?? 0)}
          icon={<DollarSign className="h-4 w-4" />}
          description="Recurring monthly"
          isLoading={isLoading}
        />
        <StatCard
          title="Annual Revenue (ARR)"
          value={formatCurrency(stats?.total_revenue_yearly ?? 0)}
          icon={<TrendingUp className="h-4 w-4" />}
          description="Projected yearly"
          isLoading={isLoading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Client Status Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Client Status Distribution</CardTitle>
            <CardDescription>Breakdown by tenant status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[250px]">
              {statusData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {statusData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                      }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  No data available
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Module Adoption */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Module Adoption</CardTitle>
            <CardDescription>Modules by number of tenants</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[250px]">
              {moduleData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={moduleData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis type="number" className="text-xs" />
                    <YAxis
                      type="category"
                      dataKey="module_name"
                      className="text-xs"
                      width={120}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                      }}
                      formatter={(value) => [`${value} tenants`, 'Adoption']}
                    />
                    <Bar dataKey="tenant_count" fill="#3B82F6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  No data available
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Clients Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">Recent Clients</CardTitle>
            <CardDescription>Last onboarded tenants</CardDescription>
          </div>
          <Link
            href="/platform/clients"
            className="text-sm text-primary hover:underline"
          >
            View all
          </Link>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Subdomain</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Modules</TableHead>
                <TableHead>Monthly Cost</TableHead>
                <TableHead>Onboarded</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentTenants.length > 0 ? (
                recentTenants.map((tenant) => (
                  <TableRow key={tenant.id}>
                    <TableCell className="font-medium">
                      <Link
                        href={`/platform/clients/${tenant.id}`}
                        className="hover:underline text-primary"
                      >
                        {tenant.name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{tenant.subdomain}</TableCell>
                    <TableCell>
                      <TenantStatusBadge status={tenant.status} />
                    </TableCell>
                    <TableCell>{tenant.total_subscriptions}</TableCell>
                    <TableCell>{formatCurrency(tenant.monthly_cost)}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {format(new Date(tenant.onboarded_at), 'MMM dd, yyyy')}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                    No tenants found
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
