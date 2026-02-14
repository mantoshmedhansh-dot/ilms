'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  ArrowLeft,
  Shield,
  ShieldOff,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
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

export default function TenantDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const tenantId = params.tenantId as string;

  const { data: tenant, isLoading } = useQuery({
    queryKey: ['platform-tenant', tenantId],
    queryFn: () => platformAdminApi.getTenantDetails(tenantId),
  });

  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['platform-tenant-users', tenantId],
    queryFn: () => platformAdminApi.getTenantUsers(tenantId),
  });

  const { data: billing, isLoading: billingLoading } = useQuery({
    queryKey: ['platform-tenant-billing', tenantId],
    queryFn: () => platformAdminApi.getBillingHistory({ tenant_id: tenantId }),
  });

  const statusMutation = useMutation({
    mutationFn: ({ status }: { status: string }) =>
      platformAdminApi.updateTenantStatus(tenantId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['platform-tenant', tenantId] });
      queryClient.invalidateQueries({ queryKey: ['platform-tenants'] });
      toast.success('Tenant status updated');
    },
    onError: () => {
      toast.error('Failed to update status');
    },
  });

  // Extract admin info from settings
  const adminEmail =
    (tenant?.settings as Record<string, unknown>)?.pending_admin &&
    typeof (tenant?.settings as Record<string, unknown>).pending_admin === 'object'
      ? ((tenant?.settings as Record<string, unknown>).pending_admin as Record<string, string>)
          ?.email
      : null;
  const adminName =
    (tenant?.settings as Record<string, unknown>)?.pending_admin &&
    typeof (tenant?.settings as Record<string, unknown>).pending_admin === 'object'
      ? `${((tenant?.settings as Record<string, unknown>).pending_admin as Record<string, string>)?.first_name || ''} ${((tenant?.settings as Record<string, unknown>).pending_admin as Record<string, string>)?.last_name || ''}`.trim()
      : null;

  const users = usersData?.users || [];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Tenant not found</p>
        <Button variant="link" onClick={() => router.push('/platform/clients')}>
          Back to clients
        </Button>
      </div>
    );
  }

  const canActivate =
    tenant.status === 'suspended' ||
    tenant.status === 'pending' ||
    tenant.status === 'pending_setup';
  const canSuspend = tenant.status === 'active';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push('/platform/clients')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{tenant.name}</h1>
              <TenantStatusBadge status={tenant.status} />
            </div>
            <p className="text-muted-foreground">
              {tenant.subdomain} &middot; {tenant.database_schema}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {(tenant.status === 'active' || tenant.status === 'pending_setup') && (
            <Button variant="outline" size="sm" asChild>
              <a
                href={`/t/${tenant.subdomain}/login`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <ExternalLink className="mr-2 h-4 w-4" />
                Open Dashboard
              </a>
            </Button>
          )}
          {canActivate && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="default" size="sm">
                  <Shield className="mr-2 h-4 w-4" />
                  Activate
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Activate Tenant</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will activate {tenant.name} and allow them to access the platform.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => statusMutation.mutate({ status: 'active' })}
                  >
                    {statusMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : null}
                    Activate
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
          {canSuspend && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" size="sm">
                  <ShieldOff className="mr-2 h-4 w-4" />
                  Suspend
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Suspend Tenant</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will suspend {tenant.name} and prevent access. This can be reversed.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => statusMutation.mutate({ status: 'suspended' })}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    {statusMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : null}
                    Suspend
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="users">Users ({usersData?.user_count ?? 0})</TabsTrigger>
          <TabsTrigger value="modules">
            Modules ({tenant.subscriptions?.length ?? 0})
          </TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Subscription Plan
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{tenant.plan_name || 'Standard'}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Monthly Cost
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{formatCurrency(tenant.total_monthly_cost)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Users
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{tenant.total_users}</p>
              </CardContent>
            </Card>
            {adminEmail && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Admin Email
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm font-medium">{adminEmail}</p>
                  {adminName && (
                    <p className="text-xs text-muted-foreground">{adminName}</p>
                  )}
                </CardContent>
              </Card>
            )}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Onboarded
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm font-medium">
                  {format(new Date(tenant.onboarded_at), 'MMMM dd, yyyy')}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Database Schema
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm font-mono">{tenant.database_schema}</p>
                {tenant.storage_used_mb && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {tenant.storage_used_mb} MB used
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Users Tab */}
        <TabsContent value="users">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Tenant Users</CardTitle>
              <CardDescription>
                {usersData?.user_count ?? 0} users in schema {usersData?.schema}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Verified</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {usersLoading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                      <TableRow key={i}>
                        {Array.from({ length: 5 }).map((_, j) => (
                          <TableCell key={j}>
                            <Skeleton className="h-4 w-20" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  ) : users.length > 0 ? (
                    users.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell className="font-medium">
                          {user.first_name} {user.last_name}
                        </TableCell>
                        <TableCell className="text-muted-foreground">{user.email}</TableCell>
                        <TableCell>
                          <Badge variant={user.is_active ? 'default' : 'secondary'}>
                            {user.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={user.is_verified ? 'default' : 'secondary'}>
                            {user.is_verified ? 'Yes' : 'No'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {format(new Date(user.created_at), 'MMM dd, yyyy')}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                        No users found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Modules Tab */}
        <TabsContent value="modules">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Subscribed Modules</CardTitle>
              <CardDescription>Active module subscriptions and pricing</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Module</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Price</TableHead>
                    <TableHead>Billing</TableHead>
                    <TableHead>Started</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tenant.subscriptions && tenant.subscriptions.length > 0 ? (
                    tenant.subscriptions.map((sub, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-medium">{sub.module_name}</TableCell>
                        <TableCell className="text-muted-foreground font-mono text-sm">
                          {sub.module_code}
                        </TableCell>
                        <TableCell>
                          <Badge variant={sub.status === 'active' ? 'default' : 'secondary'}>
                            {sub.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{formatCurrency(sub.price_paid)}</TableCell>
                        <TableCell className="text-muted-foreground capitalize">
                          {sub.billing_cycle}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {format(new Date(sub.starts_at), 'MMM dd, yyyy')}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                        No modules configured
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Billing Tab */}
        <TabsContent value="billing">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Billing History</CardTitle>
              <CardDescription>Invoice and payment records</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Invoice #</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {billingLoading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                      <TableRow key={i}>
                        {Array.from({ length: 5 }).map((_, j) => (
                          <TableCell key={j}>
                            <Skeleton className="h-4 w-20" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  ) : billing?.invoices && billing.invoices.length > 0 ? (
                    billing.invoices.map((invoice) => (
                      <TableRow key={invoice.id}>
                        <TableCell className="font-mono text-sm">
                          {invoice.invoice_number}
                        </TableCell>
                        <TableCell className="font-medium">
                          {formatCurrency(invoice.amount)}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="secondary"
                            className={
                              invoice.status === 'paid'
                                ? 'bg-green-100 text-green-800'
                                : invoice.status === 'overdue'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }
                          >
                            {invoice.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {format(new Date(invoice.billing_period_start), 'MMM dd')} -{' '}
                          {format(new Date(invoice.billing_period_end), 'MMM dd, yyyy')}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {format(new Date(invoice.created_at), 'MMM dd, yyyy')}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                        No billing records yet
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
