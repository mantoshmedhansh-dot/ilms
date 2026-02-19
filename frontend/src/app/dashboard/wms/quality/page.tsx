'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { ClipboardCheck, Plus, CheckCircle, XCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface QualityInspection {
  id: string;
  inspection_number: string;
  product_name: string;
  product_sku: string;
  lot_number?: string;
  batch_number?: string;
  inspection_type: 'RECEIVING' | 'IN_PROCESS' | 'FINAL' | 'RANDOM';
  quantity_inspected: number;
  quantity_passed: number;
  quantity_failed: number;
  defect_type?: string;
  inspector_name: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'PASSED' | 'FAILED' | 'ON_HOLD';
  inspected_at?: string;
  notes?: string;
}

interface QualityStats {
  total_inspections: number;
  pass_rate: number;
  pending_inspections: number;
  failed_today: number;
}

interface CreateInspectionData {
  inspection_type: 'RECEIVING' | 'IN_PROCESS' | 'FINAL' | 'RANDOM';
  reference_number: string;
  product_sku: string;
  product_name: string;
  quantity_inspected: number;
  inspector_name: string;
  notes?: string;
}

const qualityApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/qc/inspections', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<QualityStats> => {
    try {
      const { data } = await apiClient.get('/qc/inspections/stats');
      return data;
    } catch {
      return { total_inspections: 0, pass_rate: 0, pending_inspections: 0, failed_today: 0 };
    }
  },
  create: async (inspection: CreateInspectionData) => {
    const { data } = await apiClient.post('/qc/inspections', inspection);
    return data;
  },
};

const typeColors: Record<string, string> = {
  RECEIVING: 'bg-blue-100 text-blue-800',
  IN_PROCESS: 'bg-purple-100 text-purple-800',
  FINAL: 'bg-green-100 text-green-800',
  RANDOM: 'bg-orange-100 text-orange-800',
};

const inspectionTypes = [
  { label: 'Receiving Inspection', value: 'RECEIVING' },
  { label: 'In-Process Inspection', value: 'IN_PROCESS' },
  { label: 'Final Inspection', value: 'FINAL' },
  { label: 'Random Inspection', value: 'RANDOM' },
];

const columns: ColumnDef<QualityInspection>[] = [
  {
    accessorKey: 'inspection_number',
    header: 'Inspection',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <ClipboardCheck className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-mono font-medium">{row.original.inspection_number}</div>
          <div className="text-xs text-muted-foreground">{row.original.inspector_name}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'product_name',
    header: 'Product',
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.product_name}</div>
        <div className="text-xs text-muted-foreground font-mono">{row.original.product_sku}</div>
      </div>
    ),
  },
  {
    accessorKey: 'inspection_type',
    header: 'Type',
    cell: ({ row }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${typeColors[row.original.inspection_type]}`}>
        {row.original.inspection_type.replace('_', ' ')}
      </span>
    ),
  },
  {
    accessorKey: 'results',
    header: 'Results',
    cell: ({ row }) => {
      const passed = row.original.quantity_passed;
      const failed = row.original.quantity_failed;
      const total = row.original.quantity_inspected;
      const passRate = total > 0 ? (passed / total) * 100 : 0;
      return (
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <span>{passed}</span>
            <XCircle className="h-4 w-4 text-red-600 ml-2" />
            <span>{failed}</span>
          </div>
          <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-green-500" style={{ width: `${passRate}%` }} />
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'lot_number',
    header: 'Lot/Batch',
    cell: ({ row }) => (
      <div className="font-mono text-sm">
        {row.original.lot_number || row.original.batch_number || '-'}
      </div>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

const initialFormState = {
  inspection_type: 'RECEIVING' as 'RECEIVING' | 'IN_PROCESS' | 'FINAL' | 'RANDOM',
  reference_number: '',
  product_sku: '',
  product_name: '',
  quantity_inspected: '',
  inspector_name: '',
  notes: '',
};

export default function QualityPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState(initialFormState);

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['wms-quality', page, pageSize],
    queryFn: () => qualityApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['wms-quality-stats'],
    queryFn: qualityApi.getStats,
  });

  const createMutation = useMutation({
    mutationFn: qualityApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wms-quality'] });
      queryClient.invalidateQueries({ queryKey: ['wms-quality-stats'] });
      toast.success('Inspection created successfully');
      handleDialogClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create inspection');
    },
  });

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setFormData(initialFormState);
  };

  const handleSubmit = () => {
    if (!formData.reference_number.trim()) {
      toast.error('Reference number is required');
      return;
    }
    if (!formData.product_sku.trim()) {
      toast.error('Product SKU is required');
      return;
    }
    if (!formData.product_name.trim()) {
      toast.error('Product name is required');
      return;
    }
    if (!formData.quantity_inspected || parseInt(formData.quantity_inspected) <= 0) {
      toast.error('Quantity must be greater than 0');
      return;
    }
    if (!formData.inspector_name.trim()) {
      toast.error('Inspector name is required');
      return;
    }

    createMutation.mutate({
      inspection_type: formData.inspection_type,
      reference_number: formData.reference_number,
      product_sku: formData.product_sku,
      product_name: formData.product_name,
      quantity_inspected: parseInt(formData.quantity_inspected),
      inspector_name: formData.inspector_name,
      notes: formData.notes || undefined,
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quality Control"
        description="Manage product inspections and quality standards"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Inspection
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Inspections</CardTitle>
            <ClipboardCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_inspections || 0}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.pass_rate || 0}%</div>
            <p className="text-xs text-muted-foreground">Quality score</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.pending_inspections || 0}</div>
            <p className="text-xs text-muted-foreground">Awaiting inspection</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Today</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.failed_today || 0}</div>
            <p className="text-xs text-muted-foreground">Requires attention</p>
          </CardContent>
        </Card>
      </div>

      <Dialog open={isDialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create New Inspection</DialogTitle>
            <DialogDescription>
              Add a new quality control inspection for products.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
            <div className="space-y-2">
              <Label htmlFor="inspection_type">Inspection Type *</Label>
              <Select
                value={formData.inspection_type}
                onValueChange={(value: 'RECEIVING' | 'IN_PROCESS' | 'FINAL' | 'RANDOM') =>
                  setFormData({ ...formData, inspection_type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select inspection type" />
                </SelectTrigger>
                <SelectContent>
                  {inspectionTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reference_number">Reference Number *</Label>
              <Input
                id="reference_number"
                placeholder="PO-12345 or GRN-67890"
                value={formData.reference_number}
                onChange={(e) =>
                  setFormData({ ...formData, reference_number: e.target.value })
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="product_sku">Product SKU *</Label>
                <Input
                  id="product_sku"
                  placeholder="SKU-001"
                  value={formData.product_sku}
                  onChange={(e) =>
                    setFormData({ ...formData, product_sku: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="quantity_inspected">Quantity *</Label>
                <Input
                  id="quantity_inspected"
                  type="number"
                  min="1"
                  placeholder="100"
                  value={formData.quantity_inspected}
                  onChange={(e) =>
                    setFormData({ ...formData, quantity_inspected: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="product_name">Product Name *</Label>
              <Input
                id="product_name"
                placeholder="Product name"
                value={formData.product_name}
                onChange={(e) =>
                  setFormData({ ...formData, product_name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="inspector_name">Inspector *</Label>
              <Input
                id="inspector_name"
                placeholder="Inspector name"
                value={formData.inspector_name}
                onChange={(e) =>
                  setFormData({ ...formData, inspector_name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                placeholder="Additional notes or observations..."
                value={formData.notes}
                onChange={(e) =>
                  setFormData({ ...formData, notes: e.target.value })
                }
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleDialogClose}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {createMutation.isPending ? 'Creating...' : 'Create Inspection'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="inspection_number"
        searchPlaceholder="Search inspections..."
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
