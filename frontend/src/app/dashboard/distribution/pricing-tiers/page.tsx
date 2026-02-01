'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Tag, Percent } from 'lucide-react';
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

interface PricingTier {
  id: string;
  name: string;
  code: string;
  discount_percentage: number;
  min_order_value?: number;
  max_credit_days: number;
  priority: number;
  is_active: boolean;
  dealers_count?: number;
  created_at: string;
}

const pricingTiersApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/dealers/tiers/pricing', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
};

const tierColors: Record<string, string> = {
  PLATINUM: 'bg-purple-100 text-purple-800',
  GOLD: 'bg-yellow-100 text-yellow-800',
  SILVER: 'bg-gray-100 text-gray-800',
  BRONZE: 'bg-orange-100 text-orange-800',
};

const columns: ColumnDef<PricingTier>[] = [
  {
    accessorKey: 'name',
    header: 'Tier Name',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Tag className="h-4 w-4 text-muted-foreground" />
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${tierColors[row.original.code] || 'bg-gray-100'}`}>
          {row.original.name}
        </span>
      </div>
    ),
  },
  {
    accessorKey: 'discount_percentage',
    header: 'Discount',
    cell: ({ row }) => (
      <div className="flex items-center gap-1">
        <Percent className="h-4 w-4 text-green-600" />
        <span className="font-medium text-green-600">
          {row.original.discount_percentage}%
        </span>
      </div>
    ),
  },
  {
    accessorKey: 'min_order_value',
    header: 'Min Order',
    cell: ({ row }) => (
      <span className="text-sm">
        {row.original.min_order_value
          ? `₹${row.original.min_order_value.toLocaleString('en-IN')}`
          : 'No minimum'}
      </span>
    ),
  },
  {
    accessorKey: 'max_credit_days',
    header: 'Credit Days',
    cell: ({ row }) => (
      <span className="text-sm">{row.original.max_credit_days} days</span>
    ),
  },
  {
    accessorKey: 'dealers_count',
    header: 'Dealers',
    cell: ({ row }) => (
      <span className="text-sm">{row.original.dealers_count ?? 0}</span>
    ),
  },
  {
    accessorKey: 'priority',
    header: 'Priority',
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">#{row.original.priority}</span>
    ),
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) => (
      <StatusBadge status={row.original.is_active ? 'ACTIVE' : 'INACTIVE'} />
    ),
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
          <DropdownMenuItem>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];

export default function PricingTiersPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['pricing-tiers', page, pageSize],
    queryFn: () => pricingTiersApi.list({ page: page + 1, size: pageSize }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pricing Tiers"
        description="Configure dealer pricing tiers and discounts"
        actions={
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Add Tier
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="name"
        searchPlaceholder="Search tiers..."
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
