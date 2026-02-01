'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Users,
  Building2,
  UserCheck,
  UserX,
  Clock,
  Calendar,
  TrendingUp,
  CreditCard,
  AlertCircle,
  ChevronRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { hrApi, HRDashboardStats } from '@/lib/api';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down';
  isLoading?: boolean;
  href?: string;
}

function StatCard({ title, value, subtitle, icon, isLoading, href }: StatCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-4" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-32 mb-2" />
          <Skeleton className="h-4 w-20" />
        </CardContent>
      </Card>
    );
  }

  const content = (
    <Card className={href ? 'hover:bg-muted/50 transition-colors cursor-pointer' : ''}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className="text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }

  return content;
}

export default function HRDashboardPage() {
  const { data: stats, isLoading } = useQuery<HRDashboardStats>({
    queryKey: ['hr-dashboard'],
    queryFn: hrApi.getDashboard,
  });

  const defaultStats: HRDashboardStats = stats ?? {
    total_employees: 0,
    active_employees: 0,
    on_leave_today: 0,
    new_joinings_this_month: 0,
    exits_this_month: 0,
    present_today: 0,
    absent_today: 0,
    not_marked: 0,
    pending_leave_requests: 0,
    pending_payroll_approval: 0,
    department_wise: [],
  };

  const attendancePercent = defaultStats.active_employees > 0
    ? Math.round((defaultStats.present_today / defaultStats.active_employees) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">HR Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your workforce and HR operations
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href="/dashboard/hr/employees/new">Add Employee</Link>
          </Button>
          <Button asChild>
            <Link href="/dashboard/hr/employees">View All Employees</Link>
          </Button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Employees"
          value={defaultStats.total_employees}
          subtitle={`${defaultStats.active_employees} active`}
          icon={<Users className="h-4 w-4" />}
          isLoading={isLoading}
          href="/dashboard/hr/employees"
        />
        <StatCard
          title="Present Today"
          value={defaultStats.present_today}
          subtitle={`${attendancePercent}% attendance`}
          icon={<UserCheck className="h-4 w-4" />}
          isLoading={isLoading}
          href="/dashboard/hr/attendance"
        />
        <StatCard
          title="On Leave"
          value={defaultStats.on_leave_today}
          subtitle="Today"
          icon={<Calendar className="h-4 w-4" />}
          isLoading={isLoading}
          href="/dashboard/hr/leaves"
        />
        <StatCard
          title="Pending Leaves"
          value={defaultStats.pending_leave_requests}
          subtitle="Awaiting approval"
          icon={<Clock className="h-4 w-4" />}
          isLoading={isLoading}
          href="/dashboard/hr/leaves"
        />
      </div>

      {/* Attendance Overview & Pending Actions */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Attendance Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Today&apos;s Attendance</CardTitle>
            <CardDescription>Real-time attendance tracking</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <>
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
              </>
            ) : (
              <>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>Overall Attendance</span>
                    <span className="font-medium">{attendancePercent}%</span>
                  </div>
                  <Progress value={attendancePercent} className="h-2" />
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="p-3 bg-green-50 dark:bg-green-950 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">{defaultStats.present_today}</div>
                    <div className="text-xs text-muted-foreground">Present</div>
                  </div>
                  <div className="p-3 bg-red-50 dark:bg-red-950 rounded-lg">
                    <div className="text-2xl font-bold text-red-600">{defaultStats.absent_today}</div>
                    <div className="text-xs text-muted-foreground">Absent</div>
                  </div>
                  <div className="p-3 bg-yellow-50 dark:bg-yellow-950 rounded-lg">
                    <div className="text-2xl font-bold text-yellow-600">{defaultStats.not_marked}</div>
                    <div className="text-xs text-muted-foreground">Not Marked</div>
                  </div>
                </div>
                <Button asChild variant="outline" className="w-full">
                  <Link href="/dashboard/hr/attendance">
                    View Full Attendance
                    <ChevronRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        {/* Pending Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Pending Actions</CardTitle>
            <CardDescription>Items requiring your attention</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <>
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </>
            ) : (
              <>
                <Link href="/dashboard/hr/leaves" className="block">
                  <div className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-orange-100 dark:bg-orange-950 rounded-full">
                        <Clock className="h-4 w-4 text-orange-600" />
                      </div>
                      <div>
                        <div className="font-medium">Leave Requests</div>
                        <div className="text-xs text-muted-foreground">Pending approval</div>
                      </div>
                    </div>
                    <Badge variant={defaultStats.pending_leave_requests > 0 ? 'destructive' : 'secondary'}>
                      {defaultStats.pending_leave_requests}
                    </Badge>
                  </div>
                </Link>
                <Link href="/dashboard/hr/payroll" className="block">
                  <div className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-100 dark:bg-blue-950 rounded-full">
                        <CreditCard className="h-4 w-4 text-blue-600" />
                      </div>
                      <div>
                        <div className="font-medium">Payroll Approval</div>
                        <div className="text-xs text-muted-foreground">Processed payrolls</div>
                      </div>
                    </div>
                    <Badge variant={defaultStats.pending_payroll_approval > 0 ? 'destructive' : 'secondary'}>
                      {defaultStats.pending_payroll_approval}
                    </Badge>
                  </div>
                </Link>
                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-green-100 dark:bg-green-950 rounded-full">
                      <TrendingUp className="h-4 w-4 text-green-600" />
                    </div>
                    <div>
                      <div className="font-medium">New Joinings</div>
                      <div className="text-xs text-muted-foreground">This month</div>
                    </div>
                  </div>
                  <Badge variant="outline">{defaultStats.new_joinings_this_month}</Badge>
                </div>
                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-red-100 dark:bg-red-950 rounded-full">
                      <UserX className="h-4 w-4 text-red-600" />
                    </div>
                    <div>
                      <div className="font-medium">Exits</div>
                      <div className="text-xs text-muted-foreground">This month</div>
                    </div>
                  </div>
                  <Badge variant="outline">{defaultStats.exits_this_month}</Badge>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Department Distribution */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Department Distribution</CardTitle>
              <CardDescription>Employee count by department</CardDescription>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/hr/departments">
                Manage Departments
                <ChevronRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-20" />
              ))}
            </div>
          ) : defaultStats.department_wise.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {defaultStats.department_wise.map((dept) => (
                <div key={dept.department} className="p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium truncate">{dept.department}</span>
                  </div>
                  <div className="text-2xl font-bold">{dept.count}</div>
                  <div className="text-xs text-muted-foreground">employees</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="font-medium">No departments found</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Create departments to organize your workforce
              </p>
              <Button asChild className="mt-4">
                <Link href="/dashboard/hr/departments">Create Department</Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-4">
        <Button asChild variant="outline" className="h-auto py-4">
          <Link href="/dashboard/hr/employees/new" className="flex flex-col items-center gap-2">
            <Users className="h-6 w-6" />
            <span>Add Employee</span>
          </Link>
        </Button>
        <Button asChild variant="outline" className="h-auto py-4">
          <Link href="/dashboard/hr/attendance" className="flex flex-col items-center gap-2">
            <UserCheck className="h-6 w-6" />
            <span>Mark Attendance</span>
          </Link>
        </Button>
        <Button asChild variant="outline" className="h-auto py-4">
          <Link href="/dashboard/hr/leaves" className="flex flex-col items-center gap-2">
            <Calendar className="h-6 w-6" />
            <span>Leave Management</span>
          </Link>
        </Button>
        <Button asChild variant="outline" className="h-auto py-4">
          <Link href="/dashboard/hr/payroll" className="flex flex-col items-center gap-2">
            <CreditCard className="h-6 w-6" />
            <span>Process Payroll</span>
          </Link>
        </Button>
      </div>
    </div>
  );
}
