'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, Play, Pause, Megaphone, Calendar } from 'lucide-react';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatDate, formatCurrency } from '@/lib/utils';

interface Campaign {
  id: string;
  name: string;
  type: 'EMAIL' | 'SMS' | 'WHATSAPP' | 'PUSH_NOTIFICATION' | 'MULTI_CHANNEL';
  status: 'DRAFT' | 'SCHEDULED' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'CANCELLED';
  target_audience?: string;
  audience_count?: number;
  start_date?: string;
  end_date?: string;
  budget?: number;
  spent?: number;
  metrics?: {
    sent?: number;
    delivered?: number;
    opened?: number;
    clicked?: number;
  };
  created_at: string;
}

const campaignsApi = {
  list: async (params?: { page?: number; size?: number; status?: string }) => {
    try {
      const { data } = await apiClient.get('/campaigns', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
};

const typeColors: Record<string, string> = {
  EMAIL: 'bg-blue-100 text-blue-800',
  SMS: 'bg-green-100 text-green-800',
  WHATSAPP: 'bg-emerald-100 text-emerald-800',
  PUSH_NOTIFICATION: 'bg-purple-100 text-purple-800',
  MULTI_CHANNEL: 'bg-orange-100 text-orange-800',
};

const columns: ColumnDef<Campaign>[] = [
  {
    accessorKey: 'name',
    header: 'Campaign',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Megaphone className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-medium">{row.original.name}</div>
          <span className={`px-2 py-0.5 rounded text-xs ${typeColors[row.original.type] ?? 'bg-gray-100 text-gray-800'}`}>
            {row.original.type?.replace(/_/g, ' ') ?? '-'}
          </span>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'audience',
    header: 'Audience',
    cell: ({ row }) => (
      <div className="text-sm">
        <div>{row.original.target_audience || 'All'}</div>
        <div className="text-muted-foreground">
          {row.original.audience_count?.toLocaleString() || 0} recipients
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'schedule',
    header: 'Schedule',
    cell: ({ row }) => (
      <div className="flex items-center gap-1 text-sm">
        <Calendar className="h-3 w-3 text-muted-foreground" />
        <div>
          <div>{row.original.start_date ? formatDate(row.original.start_date) : 'Not scheduled'}</div>
          {row.original.end_date && (
            <div className="text-muted-foreground">to {formatDate(row.original.end_date)}</div>
          )}
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'metrics',
    header: 'Performance',
    cell: ({ row }) => {
      const metrics = row.original.metrics;
      if (!metrics) return <span className="text-muted-foreground">-</span>;
      const openRate = metrics.sent ? ((metrics.opened || 0) / metrics.sent * 100).toFixed(1) : 0;
      return (
        <div className="text-sm">
          <div>Sent: {metrics.sent?.toLocaleString() || 0}</div>
          <div className="text-muted-foreground">
            Open rate: {openRate}%
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'budget',
    header: 'Budget',
    cell: ({ row }) => (
      <div className="text-sm">
        {row.original.budget ? (
          <>
            <div>{formatCurrency(row.original.spent || 0)}</div>
            <div className="text-muted-foreground">of {formatCurrency(row.original.budget)}</div>
          </>
        ) : (
          <span className="text-muted-foreground">No budget</span>
        )}
      </div>
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
          <DropdownMenuItem onClick={() => toast.success(`Viewing campaign: ${row.original.name}`)}>
            <Eye className="mr-2 h-4 w-4" />
            View Details
          </DropdownMenuItem>
          {row.original.status === 'SCHEDULED' && (
            <DropdownMenuItem onClick={() => toast.success(`Starting campaign: ${row.original.name}`)}>
              <Play className="mr-2 h-4 w-4" />
              Start Now
            </DropdownMenuItem>
          )}
          {row.original.status === 'RUNNING' && (
            <DropdownMenuItem onClick={() => toast.success(`Pausing campaign: ${row.original.name}`)}>
              <Pause className="mr-2 h-4 w-4" />
              Pause
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];

export default function CampaignsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['campaigns', page, pageSize],
    queryFn: () => campaignsApi.list({ page: page + 1, size: pageSize }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Campaigns"
        description="Create and manage marketing campaigns"
        actions={
          <Button onClick={() => toast.success('Opening campaign creation wizard')}>
            <Plus className="mr-2 h-4 w-4" />
            Create Campaign
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="name"
        searchPlaceholder="Search campaigns..."
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
