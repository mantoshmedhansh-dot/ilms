'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { format } from 'date-fns';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { auditLogsApi } from '@/lib/api';

interface AuditLog {
  id: string;
  user_id: string;
  user_name: string;
  action: string;
  entity_type: string;
  entity_id: string;
  changes: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}

const columns: ColumnDef<AuditLog>[] = [
  {
    accessorKey: 'created_at',
    header: 'Timestamp',
    cell: ({ row }) =>
      format(new Date(row.original.created_at), 'MMM d, yyyy HH:mm:ss'),
  },
  {
    accessorKey: 'user_name',
    header: 'User',
    cell: ({ row }) => row.original.user_name || 'System',
  },
  {
    accessorKey: 'action',
    header: 'Action',
    cell: ({ row }) => (
      <StatusBadge status={row.original.action?.toUpperCase() ?? 'UNKNOWN'} />
    ),
  },
  {
    accessorKey: 'entity_type',
    header: 'Entity Type',
    cell: ({ row }) => (
      <span className="capitalize">{row.original.entity_type?.replace(/_/g, ' ') ?? '-'}</span>
    ),
  },
  {
    accessorKey: 'entity_id',
    header: 'Entity ID',
    cell: ({ row }) => (
      <code className="rounded bg-muted px-2 py-1 text-xs">
        {row.original.entity_id?.slice(0, 8) ?? '-'}...
      </code>
    ),
  },
  {
    accessorKey: 'ip_address',
    header: 'IP Address',
    cell: ({ row }) => row.original.ip_address || '-',
  },
];

const entityTypes = [
  'user',
  'role',
  'product',
  'order',
  'customer',
  'vendor',
  'purchase_order',
  'service_request',
  'inventory',
  'warehouse',
];

const actions = ['create', 'update', 'delete', 'login', 'logout'];

export default function AuditLogsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [entityFilter, setEntityFilter] = useState<string>('all');
  const [actionFilter, setActionFilter] = useState<string>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs', page, pageSize, entityFilter, actionFilter],
    queryFn: () =>
      auditLogsApi.list({
        page: page + 1,
        size: pageSize,
        entity_type: entityFilter !== 'all' ? entityFilter : undefined,
        action: actionFilter !== 'all' ? actionFilter : undefined,
      }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Logs"
        description="View system activity and changes"
      />

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Select value={entityFilter} onValueChange={setEntityFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Entity Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Entities</SelectItem>
            {entityTypes.map((type) => (
              <SelectItem key={type} value={type}>
                {type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={actionFilter} onValueChange={setActionFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Action" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Actions</SelectItem>
            {actions.map((action) => (
              <SelectItem key={action} value={action}>
                {action.charAt(0).toUpperCase() + action.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
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
