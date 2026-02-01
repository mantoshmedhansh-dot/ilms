'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, DollarSign } from 'lucide-react';
import Link from 'next/link';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { dealersApi } from '@/lib/api';
import { Dealer } from '@/types';
import { tierColors } from '@/config/site';
import { Badge } from '@/components/ui/badge';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
};

const columns: ColumnDef<Dealer>[] = [
  {
    accessorKey: 'name',
    header: 'Dealer',
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.name}</div>
        <div className="text-sm text-muted-foreground">{row.original.code}</div>
      </div>
    ),
  },
  {
    accessorKey: 'type',
    header: 'Type',
    cell: ({ row }) => (
      <span className="text-sm">{(row.original.type || row.original.dealer_type || 'DEALER').replace(/_/g, ' ')}</span>
    ),
  },
  {
    accessorKey: 'pricing_tier',
    header: 'Tier',
    cell: ({ row }) => {
      const tier = row.original.pricing_tier || row.original.tier || 'STANDARD';
      return (
        <Badge variant="outline" className={`border-0 ${tierColors[tier as keyof typeof tierColors] || tierColors.STANDARD}`}>
          {tier}
        </Badge>
      );
    },
  },
  {
    accessorKey: 'credit_limit',
    header: 'Credit Limit',
    cell: ({ row }) => formatCurrency(row.original.credit_limit || 0),
  },
  {
    accessorKey: 'available_credit',
    header: 'Available',
    cell: ({ row }) => formatCurrency(row.original.available_credit || 0),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status || 'ACTIVE'} />,
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
            <Link href={`/distribution/dealers/${row.original.id}`}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem>
            <DollarSign className="mr-2 h-4 w-4" />
            Manage Credit
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];

export default function DistributionPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['dealers', page, pageSize],
    queryFn: () => dealersApi.list({ page: page + 1, size: pageSize }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Distribution"
        description="Manage dealers, pricing tiers, and franchisees"
        actions={
          <Button asChild>
            <Link href="/dashboard/distribution/dealers/new">
              <Plus className="mr-2 h-4 w-4" />
              Add Dealer
            </Link>
          </Button>
        }
      />

      <Tabs defaultValue="dealers" className="space-y-4">
        <TabsList>
          <TabsTrigger value="dealers">Dealers</TabsTrigger>
          <TabsTrigger value="pricing">Pricing Tiers</TabsTrigger>
          <TabsTrigger value="franchisees">Franchisees</TabsTrigger>
        </TabsList>

        <TabsContent value="dealers">
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            searchKey="name"
            searchPlaceholder="Search dealers..."
            isLoading={isLoading}
            manualPagination
            pageCount={data?.pages ?? 0}
            pageIndex={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        </TabsContent>

        <TabsContent value="pricing">
          <div className="flex items-center justify-center h-32 border rounded-lg bg-muted/50">
            <Link href="/dashboard/distribution/pricing-tiers">
              <Button variant="outline">
                <DollarSign className="mr-2 h-4 w-4" />
                Go to Pricing Tiers Management
              </Button>
            </Link>
          </div>
        </TabsContent>

        <TabsContent value="franchisees">
          <div className="flex items-center justify-center h-32 border rounded-lg bg-muted/50">
            <Link href="/dashboard/distribution/franchisees">
              <Button variant="outline">
                <Eye className="mr-2 h-4 w-4" />
                Go to Franchisees Management
              </Button>
            </Link>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
