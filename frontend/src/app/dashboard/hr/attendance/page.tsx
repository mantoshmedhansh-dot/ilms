'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format, startOfMonth, endOfMonth } from 'date-fns';
import {
  Calendar,
  Search,
  UserCheck,
  UserX,
  Clock,
  Filter,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { hrApi, AttendanceRecord } from '@/lib/api';

const attendanceStatuses = [
  { value: 'PRESENT', label: 'Present', variant: 'default' as const, color: 'text-green-600' },
  { value: 'ABSENT', label: 'Absent', variant: 'destructive' as const, color: 'text-red-600' },
  { value: 'HALF_DAY', label: 'Half Day', variant: 'secondary' as const, color: 'text-yellow-600' },
  { value: 'ON_LEAVE', label: 'On Leave', variant: 'outline' as const, color: 'text-blue-600' },
  { value: 'HOLIDAY', label: 'Holiday', variant: 'outline' as const, color: 'text-purple-600' },
  { value: 'WEEKEND', label: 'Weekend', variant: 'outline' as const, color: 'text-gray-600' },
];

function getStatusBadge(status: string) {
  const config = attendanceStatuses.find((s) => s.value === status);
  return (
    <Badge variant={config?.variant || 'outline'}>
      {config?.label || status}
    </Badge>
  );
}

export default function AttendancePage() {
  const [dateFilter, setDateFilter] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [departmentFilter, setDepartmentFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { data: attendanceData, isLoading } = useQuery({
    queryKey: ['attendance', page, dateFilter, statusFilter, departmentFilter],
    queryFn: () =>
      hrApi.attendance.list({
        page,
        size: pageSize,
        from_date: dateFilter,
        to_date: dateFilter,
        status: statusFilter || undefined,
        department_id: departmentFilter || undefined,
      }),
  });

  const { data: departments } = useQuery({
    queryKey: ['departments-dropdown'],
    queryFn: hrApi.departments.dropdown,
  });

  const records = attendanceData?.items || [];
  const totalPages = attendanceData?.pages || 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Attendance</h1>
          <p className="text-muted-foreground">
            Track and manage employee attendance
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <Input
                type="date"
                value={dateFilter}
                onChange={(e) => {
                  setDateFilter(e.target.value);
                  setPage(1);
                }}
                className="w-[180px]"
              />
            </div>
            <Select
              value={statusFilter || 'all'}
              onValueChange={(value) => {
                setStatusFilter(value === 'all' ? '' : value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                {attendanceStatuses.map((status) => (
                  <SelectItem key={status.value} value={status.value}>
                    {status.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={departmentFilter || 'all'}
              onValueChange={(value) => {
                setDepartmentFilter(value === 'all' ? '' : value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Departments" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                {departments?.map((dept) => (
                  <SelectItem key={dept.id} value={dept.id}>
                    {dept.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Attendance Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 dark:bg-green-950 rounded-full">
                <UserCheck className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {records.filter((r: AttendanceRecord) => r.status === 'PRESENT').length}
                </div>
                <div className="text-sm text-muted-foreground">Present</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 dark:bg-red-950 rounded-full">
                <UserX className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {records.filter((r: AttendanceRecord) => r.status === 'ABSENT').length}
                </div>
                <div className="text-sm text-muted-foreground">Absent</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 dark:bg-yellow-950 rounded-full">
                <Clock className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {records.filter((r: AttendanceRecord) => r.status === 'HALF_DAY').length}
                </div>
                <div className="text-sm text-muted-foreground">Half Day</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-950 rounded-full">
                <Calendar className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {records.filter((r: AttendanceRecord) => r.status === 'ON_LEAVE').length}
                </div>
                <div className="text-sm text-muted-foreground">On Leave</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Attendance Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Check In</TableHead>
                <TableHead>Check Out</TableHead>
                <TableHead>Work Hours</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Late/Early</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-24" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : records.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <Calendar className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="font-medium">No attendance records</h3>
                    <p className="text-sm text-muted-foreground">No attendance marked for this date</p>
                  </TableCell>
                </TableRow>
              ) : (
                records.map((record: AttendanceRecord) => (
                  <TableRow key={record.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{record.employee_name}</div>
                        <div className="text-sm text-muted-foreground">{record.employee_code}</div>
                      </div>
                    </TableCell>
                    <TableCell>{record.department_name || '-'}</TableCell>
                    <TableCell>
                      {record.check_in ? format(new Date(record.check_in), 'hh:mm a') : '-'}
                    </TableCell>
                    <TableCell>
                      {record.check_out ? format(new Date(record.check_out), 'hh:mm a') : '-'}
                    </TableCell>
                    <TableCell>
                      {record.work_hours ? `${record.work_hours.toFixed(1)} hrs` : '-'}
                    </TableCell>
                    <TableCell>{getStatusBadge(record.status)}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {record.is_late && (
                          <Badge variant="outline" className="text-orange-600">
                            Late {record.late_minutes}m
                          </Badge>
                        )}
                        {record.is_early_out && (
                          <Badge variant="outline" className="text-yellow-600">
                            Early {record.early_out_minutes}m
                          </Badge>
                        )}
                        {!record.is_late && !record.is_early_out && '-'}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
