'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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

export default function PlatformSettingsPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['platform-statistics'],
    queryFn: platformAdminApi.getStatistics,
  });

  const modules = stats?.most_popular_modules || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Platform configuration and module catalog.
        </p>
      </div>

      {/* Module Catalog from statistics */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Module Catalog</CardTitle>
          <CardDescription>Available modules and adoption across tenants</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Module</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Subscriptions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 3 }).map((_, j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-20" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : modules.length > 0 ? (
                modules.map((mod) => (
                  <TableRow key={mod.code}>
                    <TableCell className="font-medium">{mod.name}</TableCell>
                    <TableCell className="font-mono text-sm text-muted-foreground">
                      {mod.code}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{mod.subscriptions} tenants</Badge>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
                    No modules found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Platform Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Platform Info</CardTitle>
          <CardDescription>System statistics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <p className="text-sm text-muted-foreground">Total Tenants</p>
              <p className="text-2xl font-bold">{stats?.total_tenants ?? '-'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Avg Modules/Tenant</p>
              <p className="text-2xl font-bold">
                {stats?.avg_modules_per_tenant?.toFixed(1) ?? '-'}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Users (all tenants)</p>
              <p className="text-2xl font-bold">{stats?.total_users ?? '-'}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
