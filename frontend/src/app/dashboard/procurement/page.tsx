'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, FileText, CheckCircle } from 'lucide-react';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { purchaseOrdersApi, vendorsApi } from '@/lib/api';
import { PurchaseOrder, Vendor } from '@/types';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
};

const poColumns: ColumnDef<PurchaseOrder>[] = [
  {
    accessorKey: 'po_number',
    header: 'PO Number',
    cell: ({ row }) => (
      <Link
        href={`/procurement/purchase-orders/${row.original.id}`}
        className="font-medium text-primary hover:underline"
      >
        {row.original.po_number}
      </Link>
    ),
  },
  {
    accessorKey: 'vendor',
    header: 'Vendor',
    cell: ({ row }) => row.original.vendor?.name || '-',
  },
  {
    accessorKey: 'warehouse',
    header: 'Delivery To',
    cell: ({ row }) => row.original.warehouse?.name || '-',
  },
  {
    accessorKey: 'grand_total',
    header: 'Amount',
    cell: ({ row }) => formatCurrency(row.original.grand_total),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: 'expected_delivery_date',
    header: 'Expected Delivery',
    cell: ({ row }) =>
      row.original.expected_delivery_date
        ? format(new Date(row.original.expected_delivery_date), 'MMM d, yyyy')
        : '-',
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
            <Link href={`/procurement/purchase-orders/${row.original.id}`}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem>
            <FileText className="mr-2 h-4 w-4" />
            Print PO
          </DropdownMenuItem>
          {row.original.status === 'PENDING_APPROVAL' && (
            <DropdownMenuItem>
              <CheckCircle className="mr-2 h-4 w-4" />
              Approve
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];

const vendorColumns: ColumnDef<Vendor>[] = [
  {
    accessorKey: 'name',
    header: 'Vendor Name',
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.name}</div>
        <div className="text-sm text-muted-foreground">{row.original.code}</div>
      </div>
    ),
  },
  {
    accessorKey: 'phone',
    header: 'Contact',
    cell: ({ row }) => row.original.phone || '-',
  },
  {
    accessorKey: 'gst_number',
    header: 'GST Number',
    cell: ({ row }) => row.original.gst_number || '-',
  },
  {
    accessorKey: 'tier',
    header: 'Tier',
    cell: ({ row }) => <StatusBadge status={row.original.tier || row.original.grade || 'N/A'} />,
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

export default function ProcurementPage() {
  const [poPage, setPoPage] = useState(0);
  const [vendorPage, setVendorPage] = useState(0);
  const pageSize = 10;

  const { data: poData, isLoading: poLoading } = useQuery({
    queryKey: ['purchase-orders', poPage],
    queryFn: () => purchaseOrdersApi.list({ page: poPage + 1, size: pageSize }),
  });

  const { data: vendorData, isLoading: vendorLoading } = useQuery({
    queryKey: ['vendors', vendorPage],
    queryFn: () => vendorsApi.list({ page: vendorPage + 1, size: pageSize }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Procurement"
        description="Manage vendors and purchase orders"
        actions={
          <Button asChild>
            <Link href="/dashboard/procurement/purchase-orders/new">
              <Plus className="mr-2 h-4 w-4" />
              Create PO
            </Link>
          </Button>
        }
      />

      <Tabs defaultValue="purchase-orders" className="space-y-4">
        <TabsList>
          <TabsTrigger value="purchase-orders">Purchase Orders</TabsTrigger>
          <TabsTrigger value="vendors">Vendors</TabsTrigger>
          <TabsTrigger value="grn">GRN</TabsTrigger>
        </TabsList>

        <TabsContent value="purchase-orders">
          <DataTable
            columns={poColumns}
            data={poData?.items ?? []}
            searchKey="po_number"
            searchPlaceholder="Search POs..."
            isLoading={poLoading}
            manualPagination
            pageCount={poData?.pages ?? 0}
            pageIndex={poPage}
            pageSize={pageSize}
            onPageChange={setPoPage}
          />
        </TabsContent>

        <TabsContent value="vendors">
          <div className="mb-4 flex justify-end">
            <Button asChild>
              <Link href="/dashboard/procurement/vendors/new">
                <Plus className="mr-2 h-4 w-4" />
                Add Vendor
              </Link>
            </Button>
          </div>
          <DataTable
            columns={vendorColumns}
            data={vendorData?.items ?? []}
            searchKey="name"
            searchPlaceholder="Search vendors..."
            isLoading={vendorLoading}
            manualPagination
            pageCount={vendorData?.pages ?? 0}
            pageIndex={vendorPage}
            pageSize={pageSize}
            onPageChange={setVendorPage}
          />
        </TabsContent>

        <TabsContent value="grn">
          <div className="flex items-center justify-center h-32 border rounded-lg bg-muted/50">
            <Link href="/dashboard/procurement/grn">
              <Button variant="outline">
                <FileText className="mr-2 h-4 w-4" />
                Go to GRN Management
              </Button>
            </Link>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
