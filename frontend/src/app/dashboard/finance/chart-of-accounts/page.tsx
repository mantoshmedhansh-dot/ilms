'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Pencil, Trash2, ChevronRight, FileSpreadsheet, Loader2, Landmark } from 'lucide-react';
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
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { accountsApi } from '@/lib/api';

interface Account {
  id: string;
  account_code: string;
  account_name: string;
  account_type: 'ASSET' | 'LIABILITY' | 'EQUITY' | 'REVENUE' | 'EXPENSE';
  account_sub_type?: string;
  parent_id?: string;
  description?: string;
  is_active: boolean;
  is_group: boolean;
  is_system: boolean;
  allow_direct_posting: boolean;
  opening_balance: number;
  current_balance: number;
  level: number;
  created_at: string;
  updated_at: string;
  // Bank-specific fields
  bank_name?: string;
  bank_account_number?: string;
  bank_ifsc?: string;
}

const accountTypes = [
  { label: 'Asset', value: 'ASSET' },
  { label: 'Liability', value: 'LIABILITY' },
  { label: 'Equity', value: 'EQUITY' },
  { label: 'Revenue', value: 'REVENUE' },
  { label: 'Expense', value: 'EXPENSE' },
];

// Sub-types mapped by account type
// Note: BANK accounts are created automatically via Settings → Bank
const accountSubTypes: Record<string, { label: string; value: string }[]> = {
  ASSET: [
    { label: 'Cash', value: 'CASH' },
    { label: 'Accounts Receivable', value: 'ACCOUNTS_RECEIVABLE' },
    { label: 'Inventory', value: 'INVENTORY' },
    { label: 'Fixed Asset', value: 'FIXED_ASSET' },
    { label: 'Current Asset', value: 'CURRENT_ASSET' },
    { label: 'Prepaid Expense', value: 'PREPAID_EXPENSE' },
  ],
  LIABILITY: [
    { label: 'Accounts Payable', value: 'ACCOUNTS_PAYABLE' },
    { label: 'Tax Payable', value: 'TAX_PAYABLE' },
    { label: 'Current Liability', value: 'CURRENT_LIABILITY' },
    { label: 'Long Term Liability', value: 'LONG_TERM_LIABILITY' },
  ],
  EQUITY: [
    { label: 'Retained Earnings', value: 'RETAINED_EARNINGS' },
    { label: 'Share Capital', value: 'SHARE_CAPITAL' },
  ],
  REVENUE: [
    { label: 'Operating Revenue', value: 'OPERATING_REVENUE' },
    { label: 'Non-Operating Revenue', value: 'NON_OPERATING_REVENUE' },
  ],
  EXPENSE: [
    { label: 'Operating Expense', value: 'OPERATING_EXPENSE' },
    { label: 'Non-Operating Expense', value: 'NON_OPERATING_EXPENSE' },
    { label: 'Cost of Goods Sold', value: 'COST_OF_GOODS_SOLD' },
  ],
};

const typeColors: Record<string, string> = {
  ASSET: 'bg-blue-100 text-blue-800',
  LIABILITY: 'bg-red-100 text-red-800',
  EQUITY: 'bg-purple-100 text-purple-800',
  REVENUE: 'bg-green-100 text-green-800',
  EXPENSE: 'bg-orange-100 text-orange-800',
};

export default function ChartOfAccountsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [formData, setFormData] = useState({
    id: '',
    code: '',
    name: '',
    type: 'ASSET',
    sub_type: '',
    parent_id: '',
    description: '',
    is_group: false,
    is_active: true,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['accounts', page, pageSize],
    queryFn: () => accountsApi.list({ page: page + 1, size: pageSize }),
  });

  const createMutation = useMutation({
    mutationFn: accountsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      toast.success('Account created successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create account'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { account_name?: string; description?: string; is_active?: boolean } }) =>
      accountsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      toast.success('Account updated successfully');
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update account'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => accountsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      toast.success('Account deleted successfully');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete account'),
  });

  const resetForm = () => {
    setFormData({
      id: '',
      code: '',
      name: '',
      type: 'ASSET',
      sub_type: '',
      parent_id: '',
      description: '',
      is_group: false,
      is_active: true,
    });
    setIsEditMode(false);
    setIsDialogOpen(false);
  };

  const handleEdit = (account: Account) => {
    setFormData({
      id: account.id,
      code: account.account_code,
      name: account.account_name,
      type: account.account_type,
      sub_type: account.account_sub_type || '',
      parent_id: account.parent_id || '',
      description: account.description || '',
      is_group: account.is_group,
      is_active: account.is_active,
    });
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleDelete = (account: Account) => {
    if (account.is_system) {
      toast.error('System accounts cannot be deleted');
      return;
    }
    // Convert to number for proper comparison (API may return string or Decimal)
    const balance = Number(account.current_balance) || 0;
    if (balance !== 0) {
      toast.error(`Cannot delete account with non-zero balance (₹${balance.toFixed(2)})`);
      return;
    }
    if (confirm(`Are you sure you want to delete account "${account.account_name}"?`)) {
      deleteMutation.mutate(account.id);
    }
  };

  const handleSubmit = () => {
    if (!formData.code.trim() || !formData.name.trim() || !formData.type) {
      toast.error('Code, name, and type are required');
      return;
    }

    if (isEditMode) {
      updateMutation.mutate({
        id: formData.id,
        data: {
          account_name: formData.name,
          description: formData.description || undefined,
          is_active: formData.is_active,
        },
      });
    } else {
      createMutation.mutate({
        code: formData.code.toUpperCase(),
        name: formData.name,
        type: formData.type,
        account_sub_type: formData.sub_type || undefined,
        parent_id: formData.parent_id || undefined,
        description: formData.description || undefined,
        is_group: formData.is_group,
      });
    }
  };

  const columns: ColumnDef<Account>[] = [
    {
      accessorKey: 'account_code',
      header: 'Code',
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.original.account_code}</span>
      ),
    },
    {
      accessorKey: 'account_name',
      header: 'Account Name',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          {row.original.is_group && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
          {row.original.account_sub_type === 'BANK' ? (
            <Landmark className="h-4 w-4 text-blue-600" />
          ) : (
            <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
          )}
          <span className={row.original.is_group ? 'font-medium' : ''}>
            {row.original.account_name}
          </span>
          {row.original.account_sub_type === 'BANK' && row.original.bank_name && (
            <span className="text-xs text-muted-foreground">({row.original.bank_name})</span>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'account_type',
      header: 'Type',
      cell: ({ row }) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${typeColors[row.original.account_type] || 'bg-gray-100 text-gray-800'}`}>
          {row.original.account_type}
        </span>
      ),
    },
    {
      accessorKey: 'level',
      header: 'Parent',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {row.original.parent_id ? `Level ${row.original.level}` : '-'}
        </span>
      ),
    },
    {
      accessorKey: 'current_balance',
      header: 'Balance',
      cell: ({ row }) => {
        const balance = row.original.current_balance || 0;
        return (
          <span className={`font-medium ${balance < 0 ? 'text-red-600' : ''}`}>
            ₹{Math.abs(balance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            {balance !== 0 && (
              <span className="text-xs ml-1">{balance < 0 ? 'Cr' : 'Dr'}</span>
            )}
          </span>
        );
      },
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
              disabled={row.original.is_system}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  // Get parent accounts (groups only) for dropdown
  const parentAccounts = (data?.items?.filter((a: Account) => a.is_group) ?? []) as Account[];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Chart of Accounts"
        description="Manage accounting structure and ledger accounts"
        actions={
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Account
          </Button>
        }
      />

      {/* Create/Edit Account Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsDialogOpen(true); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{isEditMode ? 'Edit Account' : 'Add New Account'}</DialogTitle>
            <DialogDescription>
              {isEditMode ? 'Update account details' : 'Create a new ledger account'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Code *</Label>
                <Input
                  placeholder="1001"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  disabled={isEditMode}
                />
              </div>
              <div className="space-y-2">
                <Label>Type *</Label>
                <Select
                  value={formData.type}
                  onValueChange={(value) => setFormData({ ...formData, type: value, sub_type: '' })}
                  disabled={isEditMode}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {accountTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Sub-Type</Label>
              <Select
                value={formData.sub_type || 'none'}
                onValueChange={(value) => setFormData({ ...formData, sub_type: value === 'none' ? '' : value })}
                disabled={isEditMode}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select sub-type (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  {(accountSubTypes[formData.type] || []).map((subType) => (
                    <SelectItem key={subType.value} value={subType.value}>
                      {subType.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                placeholder="Cash in Hand"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Parent Account</Label>
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
                  {parentAccounts
                    .filter((acc: Account) => acc.id && acc.id.trim() !== '')
                    .map((acc: Account) => (
                      <SelectItem key={acc.id} value={acc.id}>
                        {acc.account_code} - {acc.account_name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>


            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                placeholder="Account description (optional)"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Switch
                  id="is_group"
                  checked={formData.is_group}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_group: checked })}
                  disabled={isEditMode}
                />
                <Label htmlFor="is_group">Group Account</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="is_active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                />
                <Label htmlFor="is_active">Active</Label>
              </div>
            </div>
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
        data={data?.items ?? []}
        searchKey="account_name"
        searchPlaceholder="Search accounts..."
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
