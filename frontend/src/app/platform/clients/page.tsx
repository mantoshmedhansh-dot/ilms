'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import Link from 'next/link';
import { Search } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { platformAdminApi } from '@/lib/api/platform-admin';
import { TenantStatusBadge } from '@/components/platform/tenant-status-badge';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
};

export default function PlatformClientsPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['platform-tenants', statusFilter, search],
    queryFn: () =>
      platformAdminApi.listTenants({
        status: statusFilter === 'all' ? undefined : statusFilter,
        search: search || undefined,
        size: 100,
      }),
  });

  const tenants = data?.tenants || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Clients</h1>
        <p className="text-muted-foreground">
          Manage all tenant organizations on the platform.
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <CardTitle className="text-lg">
              All Clients {data && `(${data.total})`}
            </CardTitle>
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search clients..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
          <Tabs value={statusFilter} onValueChange={setStatusFilter} className="mt-2">
            <TabsList>
              <TabsTrigger value="all">All ({data?.total ?? 0})</TabsTrigger>
              <TabsTrigger value="active">Active ({data?.active ?? 0})</TabsTrigger>
              <TabsTrigger value="pending">Pending ({data?.pending ?? 0})</TabsTrigger>
              <TabsTrigger value="suspended">Suspended ({data?.suspended ?? 0})</TabsTrigger>
            </TabsList>
          </Tabs>
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
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-20" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : tenants.length > 0 ? (
                tenants.map((tenant) => (
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
                    No clients found
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
