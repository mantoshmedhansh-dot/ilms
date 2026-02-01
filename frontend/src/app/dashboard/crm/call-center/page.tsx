'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, Phone, PhoneIncoming, PhoneOutgoing, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { callCenterApi } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface Call {
  id: string;
  call_id: string;
  type: 'INBOUND' | 'OUTBOUND';
  customer_phone: string;
  customer_name?: string;
  agent_id: string;
  agent?: { full_name: string };
  status: 'IN_PROGRESS' | 'COMPLETED' | 'MISSED' | 'TRANSFERRED' | 'ABANDONED';
  disposition?: string;
  duration_seconds?: number;
  recording_url?: string;
  notes?: string;
  created_at: string;
  ended_at?: string;
}

const columns: ColumnDef<Call>[] = [
  {
    accessorKey: 'call_id',
    header: 'Call ID',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        {row.original.type === 'INBOUND' ? (
          <PhoneIncoming className="h-4 w-4 text-green-600" />
        ) : (
          <PhoneOutgoing className="h-4 w-4 text-blue-600" />
        )}
        <span className="font-mono text-sm">{row.original.call_id}</span>
      </div>
    ),
  },
  {
    accessorKey: 'customer',
    header: 'Customer',
    cell: ({ row }) => (
      <div>
        <div className="text-sm">{row.original.customer_name || 'Unknown'}</div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Phone className="h-3 w-3" />
          {row.original.customer_phone}
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'agent',
    header: 'Agent',
    cell: ({ row }) => (
      <span className="text-sm">{row.original.agent?.full_name || 'N/A'}</span>
    ),
  },
  {
    accessorKey: 'duration_seconds',
    header: 'Duration',
    cell: ({ row }) => {
      const duration = row.original.duration_seconds;
      if (!duration) return <span className="text-muted-foreground">-</span>;
      const mins = Math.floor(duration / 60);
      const secs = duration % 60;
      return (
        <div className="flex items-center gap-1 text-sm">
          <Clock className="h-3 w-3 text-muted-foreground" />
          {mins}:{secs.toString().padStart(2, '0')}
        </div>
      );
    },
  },
  {
    accessorKey: 'disposition',
    header: 'Disposition',
    cell: ({ row }) => (
      <span className="text-sm">{row.original.disposition || '-'}</span>
    ),
  },
  {
    accessorKey: 'created_at',
    header: 'Time',
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(row.original.created_at)}
      </span>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
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
          <DropdownMenuItem onClick={() => toast.success(`Viewing call ${row.original.call_id}`)}>
            <Eye className="mr-2 h-4 w-4" />
            View Details
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];

export default function CallCenterPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['calls', page, pageSize],
    queryFn: () => callCenterApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: dashboard } = useQuery({
    queryKey: ['call-center-dashboard'],
    queryFn: callCenterApi.getCenterDashboard,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Call Center"
        description="Manage call logs and agent activities"
        actions={
          <Button onClick={() => toast.success('Opening call log form')}>
            <Plus className="mr-2 h-4 w-4" />
            Log Call
          </Button>
        }
      />

      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Calls Today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard?.total_calls_today ?? 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Avg Handle Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard?.avg_handle_time ?? '0:00'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Calls in Queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard?.calls_in_queue ?? 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Available Agents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard?.available_agents ?? 0}</div>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="call_id"
        searchPlaceholder="Search calls..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />
    </div>
  );
}
