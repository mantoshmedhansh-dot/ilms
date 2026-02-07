'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, Building2, Loader2, TrendingUp, Wallet } from 'lucide-react';
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { costCentersApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

interface CostCenter {
  id: string;
  code: string;
  name: string;
  description?: string;
  cost_center_type: string;
  parent_id?: string;
  parent?: { name: string; code: string };
  annual_budget: number;
  current_spend: number;
  is_active: boolean;
  created_at: string;
}

const costCenterTypes = [
  { label: 'Department', value: 'DEPARTMENT' },
  { label: 'Location', value: 'LOCATION' },
  { label: 'Project', value: 'PROJECT' },
  { label: 'Division', value: 'DIVISION' },
  { label: 'Branch', value: 'BRANCH' },
];

const typeColors: Record<string, string> = {
  DEPARTMENT: 'bg-blue-100 text-blue-800',
  LOCATION: 'bg-green-100 text-green-800',
  PROJECT: 'bg-purple-100 text-purple-800',
  DIVISION: 'bg-orange-100 text-orange-800',
  BRANCH: 'bg-teal-100 text-teal-800',
};

export default function CostCentersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [formData, setFormData] = useState({
    id: '',
    code: '',
    name: '',
    cost_center_type: 'DEPARTMENT',
    parent_id: '',
    description: '',
    annual_budget: 0,
    is_active: true,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['cost-centers', page, pageSize],
    queryFn: () => costCentersApi.list({ page: page + 1, size: pageSize }),
  });

  const createMutation = useMutation({
    mutationFn: costCentersApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cost-centers'] });
      toast.success('Cost center created successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create cost center'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof costCentersApi.update>[1] }) =>
      costCentersApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cost-centers'] });
      toast.success('Cost center updated successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update cost center'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => costCentersApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cost-centers'] });
      toast.success('Cost center deleted successfully');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete cost center'),
  });

  const resetForm = () => {
    setFormData({
      id: '',
      code: '',
      name: '',
      cost_center_type: 'DEPARTMENT',
      parent_id: '',
      description: '',
      annual_budget: 0,
      is_active: true,
    });
    setIsEditMode(false);
    setIsDialogOpen(false);
  };

  const handleEdit = (costCenter: CostCenter) => {
    setFormData({
      id: costCenter.id,
      code: costCenter.code,
      name: costCenter.name,
      cost_center_type: costCenter.cost_center_type,
      parent_id: costCenter.parent_id || '',
      description: costCenter.description || '',
      annual_budget: costCenter.annual_budget,
      is_active: costCenter.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleDelete = (costCenter: CostCenter) => {
    // Convert to number for proper comparison (API may return string)
    const spent = Number(costCenter.current_spend) || 0;
    if (spent > 0) {
      toast.error(`Cannot delete cost center with expenses (₹${spent.toFixed(2)}). Deactivate it instead.`);
      return;
    }
    if (confirm(`Are you sure you want to delete cost center "${costCenter.name}"?`)) {
      deleteMutation.mutate(costCenter.id);
    }
  };

  const handleSubmit = () => {
    if (!formData.code.trim() || !formData.name.trim() || !formData.cost_center_type) {
      toast.error('Code, name, and type are required');
      return;
    }

    if (isEditMode) {
      updateMutation.mutate({
        id: formData.id,
        data: {
          name: formData.name,
          description: formData.description || undefined,
          annual_budget: formData.annual_budget,
          is_active: formData.is_active,
        },
      });
    } else {
      createMutation.mutate({
        code: formData.code.toUpperCase(),
        name: formData.name,
        cost_center_type: formData.cost_center_type,
        parent_id: formData.parent_id || undefined,
        description: formData.description || undefined,
        annual_budget: formData.annual_budget,
      });
    }
  };

  const getBudgetUtilization = (spent: number, budget: number) => {
    if (budget === 0) return 0;
    return Math.min((spent / budget) * 100, 100);
  };

  const columns: ColumnDef<CostCenter>[] = [
    {
      accessorKey: 'code',
      header: 'Code',
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.original.code}</span>
      ),
    },
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.original.name}</span>
        </div>
      ),
    },
    {
      accessorKey: 'cost_center_type',
      header: 'Type',
      cell: ({ row }) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${typeColors[row.original.cost_center_type] || 'bg-gray-100 text-gray-800'}`}>
          {row.original.cost_center_type}
        </span>
      ),
    },
    {
      accessorKey: 'parent',
      header: 'Parent',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {row.original.parent?.name || '-'}
        </span>
      ),
    },
    {
      accessorKey: 'annual_budget',
      header: 'Budget',
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">{formatCurrency(row.original.annual_budget)}</span>
          </div>
          {row.original.annual_budget > 0 && (
            <div className="flex items-center gap-2">
              <Progress
                value={getBudgetUtilization(row.original.current_spend, row.original.annual_budget)}
                className="h-1.5 w-20"
              />
              <span className="text-xs text-muted-foreground">
                {getBudgetUtilization(row.original.current_spend, row.original.annual_budget).toFixed(0)}%
              </span>
            </div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'current_spend',
      header: 'Spent',
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <TrendingUp className="h-3 w-3 text-muted-foreground" />
          <span className={`text-sm ${row.original.current_spend > row.original.annual_budget ? 'text-red-600 font-medium' : ''}`}>
            {formatCurrency(row.original.current_spend)}
          </span>
        </div>
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
            <DropdownMenuItem onClick={() => handleEdit(row.original)}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => handleDelete(row.original)}
              className="text-red-600"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  // Get parent cost centers for dropdown (excluding current one in edit mode)
  const parentCostCenters = (data?.items ?? data ?? []).filter(
    (cc: CostCenter) => cc.id && cc.id.trim() !== '' && cc.id !== formData.id
  );

  const costCenters = data?.items ?? data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cost Centers"
        description="Manage departmental cost centers for expense tracking"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Cost Center
          </Button>
        }
      />

      {/* Create/Edit Cost Center Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{isEditMode ? 'Edit Cost Center' : 'Add New Cost Center'}</DialogTitle>
            <DialogDescription>
              {isEditMode ? 'Update cost center details' : 'Create a new cost center for expense tracking'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Code *</Label>
                <Input
                  placeholder="CC001"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  disabled={isEditMode}
                />
              </div>
              <div className="space-y-2">
                <Label>Type *</Label>
                <Select
                  value={formData.cost_center_type}
                  onValueChange={(value) => setFormData({ ...formData, cost_center_type: value })}
                  disabled={isEditMode}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {costCenterTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                placeholder="Sales Department"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Parent Cost Center</Label>
              <Select
                value={formData.parent_id || 'none'}
                onValueChange={(value) => setFormData({ ...formData, parent_id: value === 'none' ? '' : value })}
                disabled={isEditMode}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select parent (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No Parent (Top Level)</SelectItem>
                  {parentCostCenters.map((cc: CostCenter) => (
                    <SelectItem key={cc.id} value={cc.id}>
                      {cc.code} - {cc.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Annual Budget</Label>
              <div className="relative">
                <Wallet className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="number"
                  min="0"
                  step="1000"
                  placeholder="0"
                  className="pl-10"
                  value={formData.annual_budget || ''}
                  onChange={(e) => setFormData({ ...formData, annual_budget: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                placeholder="Cost center description (optional)"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
            {isEditMode && (
              <div className="flex items-center space-x-2">
                <Switch
                  id="is_active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                />
                <Label htmlFor="is_active">Active</Label>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={resetForm}>Cancel</Button>
            <Button
              onClick={handleSubmit}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {(createMutation.isPending || updateMutation.isPending) && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {isEditMode ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <DataTable
        columns={columns}
        data={costCenters}
        searchKey="name"
        searchPlaceholder="Search cost centers..."
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
