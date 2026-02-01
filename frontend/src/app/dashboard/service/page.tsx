'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, UserPlus, Calendar } from 'lucide-react';
import Link from 'next/link';
import { format } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { serviceRequestsApi } from '@/lib/api';
import { ServiceRequest, ServiceRequestStatus } from '@/types';

const serviceStatuses: ServiceRequestStatus[] = [
  'PENDING',
  'ASSIGNED',
  'SCHEDULED',
  'IN_PROGRESS',
  'COMPLETED',
  'CLOSED',
  'CANCELLED',
];

const columns: ColumnDef<ServiceRequest>[] = [
  {
    accessorKey: 'request_number',
    header: 'Request #',
    cell: ({ row }) => (
      <Link
        href={`/service/requests/${row.original.id}`}
        className="font-medium text-primary hover:underline"
      >
        {row.original.request_number}
      </Link>
    ),
  },
  {
    accessorKey: 'customer',
    header: 'Customer',
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.customer?.name || '-'}</div>
        <div className="text-sm text-muted-foreground">
          {row.original.customer?.phone || '-'}
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'type',
    header: 'Type',
    cell: ({ row }) => (
      <span className="text-sm">{row.original.type?.replace(/_/g, ' ') ?? '-'}</span>
    ),
  },
  {
    accessorKey: 'priority',
    header: 'Priority',
    cell: ({ row }) => <StatusBadge status={row.original.priority} />,
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: 'scheduled_date',
    header: 'Scheduled',
    cell: ({ row }) =>
      row.original.scheduled_date
        ? format(new Date(row.original.scheduled_date), 'MMM d, yyyy')
        : '-',
  },
  {
    accessorKey: 'created_at',
    header: 'Created',
    cell: ({ row }) => format(new Date(row.original.created_at), 'MMM d, yyyy'),
  },
  {
    id: 'actions',
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Actions</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/service/requests/${row.original.id}`}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/service/requests/${row.original.id}?action=assign`}>
              <UserPlus className="mr-2 h-4 w-4" />
              Assign Technician
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/service/requests/${row.original.id}?action=schedule`}>
              <Calendar className="mr-2 h-4 w-4" />
              Schedule Visit
            </Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];

export default function ServicePage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['service-requests', page, pageSize, statusFilter],
    queryFn: () =>
      serviceRequestsApi.list({
        page: page + 1,
        size: pageSize,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Service"
        description="Manage service requests and technicians"
        actions={
          <Button asChild>
            <Link href="/dashboard/service/requests/new">
              <Plus className="mr-2 h-4 w-4" />
              Create Request
            </Link>
          </Button>
        }
      />

      <Tabs defaultValue="requests" className="space-y-4">
        <TabsList>
          <TabsTrigger value="requests">Service Requests</TabsTrigger>
          <TabsTrigger value="installations">Installations</TabsTrigger>
          <TabsTrigger value="amc">AMC Contracts</TabsTrigger>
          <TabsTrigger value="technicians">Technicians</TabsTrigger>
        </TabsList>

        <TabsContent value="requests" className="space-y-4">
          <div className="flex items-center gap-4">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                {serviceStatuses.map((status) => (
                  <SelectItem key={status} value={status}>
                    {status.replace(/_/g, ' ')}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DataTable
            columns={columns}
            data={data?.items ?? []}
            searchKey="request_number"
            searchPlaceholder="Search requests..."
            isLoading={isLoading}
            manualPagination
            pageCount={data?.pages ?? 0}
            pageIndex={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        </TabsContent>

        <TabsContent value="installations">
          <div className="flex items-center justify-center py-8">
            <Button asChild>
              <Link href="/dashboard/service/installations">
                Go to Installations
              </Link>
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="amc">
          <div className="flex items-center justify-center py-8">
            <Button asChild>
              <Link href="/dashboard/service/amc">
                Go to AMC Contracts
              </Link>
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="technicians">
          <div className="flex items-center justify-center py-8">
            <Button asChild>
              <Link href="/dashboard/service/technicians">
                Go to Technicians
              </Link>
            </Button>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
