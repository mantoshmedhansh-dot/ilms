'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Plus,
  Pencil,
  Trash2,
  Landmark,
  Star,
  Loader2,
  FileCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { companyApi } from '@/lib/api';
import {
  CompanyBankAccount,
  CompanyBankAccountCreate,
  BankAccountType,
  BankAccountPurpose,
  bankAccountTypeLabels,
  bankAccountPurposeLabels,
} from '@/types/company';

interface BankAccountsSectionProps {
  companyId: string;
}

const defaultFormData: CompanyBankAccountCreate = {
  bank_name: '',
  branch_name: '',
  account_number: '',
  ifsc_code: '',
  account_type: 'CURRENT',
  account_name: '',
  upi_id: '',
  swift_code: '',
  purpose: 'GENERAL',
  is_primary: false,
  is_active: true,
  show_on_invoice: true,
};

export function BankAccountsSection({ companyId }: BankAccountsSectionProps) {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<CompanyBankAccount | null>(null);
  const [deletingAccount, setDeletingAccount] = useState<CompanyBankAccount | null>(null);
  const [formData, setFormData] = useState<CompanyBankAccountCreate>(defaultFormData);

  const { data: bankAccounts, isLoading } = useQuery({
    queryKey: ['company', companyId, 'bank-accounts'],
    queryFn: () => companyApi.listBankAccounts(companyId),
    enabled: !!companyId,
  });

  const createMutation = useMutation({
    mutationFn: (data: CompanyBankAccountCreate) => companyApi.createBankAccount(companyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company', companyId, 'bank-accounts'] });
      toast.success('Bank account added successfully');
      setIsCreateOpen(false);
      setFormData(defaultFormData);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add bank account');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CompanyBankAccountCreate> }) =>
      companyApi.updateBankAccount(companyId, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company', companyId, 'bank-accounts'] });
      toast.success('Bank account updated successfully');
      setIsEditOpen(false);
      setEditingAccount(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update bank account');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => companyApi.deleteBankAccount(companyId, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company', companyId, 'bank-accounts'] });
      toast.success('Bank account deleted successfully');
      setIsDeleteOpen(false);
      setDeletingAccount(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete bank account');
    },
  });

  const handleCreate = () => {
    if (!formData.bank_name || !formData.account_number || !formData.ifsc_code || !formData.account_name) {
      toast.error('Please fill all required fields');
      return;
    }
    createMutation.mutate(formData);
  };

  const handleEdit = (account: CompanyBankAccount) => {
    setEditingAccount(account);
    setFormData({
      bank_name: account.bank_name,
      branch_name: account.branch_name,
      account_number: account.account_number,
      ifsc_code: account.ifsc_code,
      account_type: account.account_type,
      account_name: account.account_name,
      upi_id: account.upi_id || '',
      swift_code: account.swift_code || '',
      purpose: account.purpose,
      is_primary: account.is_primary,
      is_active: account.is_active,
      show_on_invoice: account.show_on_invoice,
    });
    setIsEditOpen(true);
  };

  const handleUpdate = () => {
    if (!editingAccount) return;
    if (!formData.bank_name || !formData.account_number || !formData.ifsc_code || !formData.account_name) {
      toast.error('Please fill all required fields');
      return;
    }
    updateMutation.mutate({ id: editingAccount.id, data: formData });
  };

  const handleDelete = (account: CompanyBankAccount) => {
    if (account.is_primary) {
      toast.error('Cannot delete primary bank account. Set another account as primary first.');
      return;
    }
    setDeletingAccount(account);
    setIsDeleteOpen(true);
  };

  const confirmDelete = () => {
    if (deletingAccount) {
      deleteMutation.mutate(deletingAccount.id);
    }
  };

  const maskAccountNumber = (accountNumber: string) => {
    if (accountNumber.length <= 4) return accountNumber;
    return '*'.repeat(accountNumber.length - 4) + accountNumber.slice(-4);
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Bank Accounts</CardTitle>
            <CardDescription>Manage company bank accounts for transactions</CardDescription>
          </div>
          <Button onClick={() => { setFormData(defaultFormData); setIsCreateOpen(true); }}>
            <Plus className="mr-2 h-4 w-4" />
            Add Account
          </Button>
        </CardHeader>
        <CardContent>
          {(!bankAccounts || bankAccounts.length === 0) ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Landmark className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="font-medium text-lg">No Bank Accounts</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Add your company bank accounts to enable payments and collections.
              </p>
              <Button className="mt-4" onClick={() => { setFormData(defaultFormData); setIsCreateOpen(true); }}>
                <Plus className="mr-2 h-4 w-4" />
                Add First Account
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {bankAccounts.map((account) => (
                <div
                  key={account.id}
                  className="flex items-start justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <Landmark className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{account.bank_name}</span>
                        {account.branch_name && (
                          <span className="text-muted-foreground">- {account.branch_name}</span>
                        )}
                        {account.is_primary && (
                          <Badge variant="default" className="ml-2">
                            <Star className="h-3 w-3 mr-1" />
                            Primary
                          </Badge>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        A/C: {maskAccountNumber(account.account_number)} | IFSC: {account.ifsc_code}
                      </div>
                      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                        <span>{bankAccountTypeLabels[account.account_type]}</span>
                        <span>|</span>
                        <span>{bankAccountPurposeLabels[account.purpose]}</span>
                        <span>|</span>
                        <span className="flex items-center gap-1">
                          <FileCheck className="h-3 w-3" />
                          Show on Invoice: {account.show_on_invoice ? 'Yes' : 'No'}
                        </span>
                      </div>
                      {account.upi_id && (
                        <div className="text-xs text-muted-foreground mt-1">
                          UPI: {account.upi_id}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={() => handleEdit(account)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(account)}
                      disabled={account.is_primary}
                      className={account.is_primary ? 'opacity-50 cursor-not-allowed' : 'text-destructive hover:text-destructive'}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={isCreateOpen || isEditOpen} onOpenChange={(open) => {
        if (!open) {
          setIsCreateOpen(false);
          setIsEditOpen(false);
          setEditingAccount(null);
          setFormData(defaultFormData);
        }
      }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{isEditOpen ? 'Edit Bank Account' : 'Add Bank Account'}</DialogTitle>
            <DialogDescription>
              {isEditOpen
                ? 'Update bank account details'
                : 'Add a new bank account for your company'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="bank_name">Bank Name *</Label>
                <Input
                  id="bank_name"
                  value={formData.bank_name}
                  onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                  placeholder="e.g., HDFC Bank"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="branch_name">Branch Name *</Label>
                <Input
                  id="branch_name"
                  value={formData.branch_name}
                  onChange={(e) => setFormData({ ...formData, branch_name: e.target.value })}
                  placeholder="e.g., Andheri East"
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="account_number">Account Number *</Label>
                <Input
                  id="account_number"
                  value={formData.account_number}
                  onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                  placeholder="e.g., 50100123456789"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ifsc_code">IFSC Code *</Label>
                <Input
                  id="ifsc_code"
                  value={formData.ifsc_code}
                  onChange={(e) => setFormData({ ...formData, ifsc_code: e.target.value.toUpperCase() })}
                  placeholder="e.g., HDFC0001234"
                  maxLength={11}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="account_name">Account Holder Name *</Label>
              <Input
                id="account_name"
                value={formData.account_name}
                onChange={(e) => setFormData({ ...formData, account_name: e.target.value })}
                placeholder="Name as per bank records"
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="account_type">Account Type</Label>
                <Select
                  value={formData.account_type}
                  onValueChange={(value) => setFormData({ ...formData, account_type: value as BankAccountType })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(bankAccountTypeLabels).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="purpose">Purpose</Label>
                <Select
                  value={formData.purpose}
                  onValueChange={(value) => setFormData({ ...formData, purpose: value as BankAccountPurpose })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select purpose" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(bankAccountPurposeLabels).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="upi_id">UPI ID (Optional)</Label>
                <Input
                  id="upi_id"
                  value={formData.upi_id}
                  onChange={(e) => setFormData({ ...formData, upi_id: e.target.value })}
                  placeholder="e.g., company@bank"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="swift_code">SWIFT Code (Optional)</Label>
                <Input
                  id="swift_code"
                  value={formData.swift_code}
                  onChange={(e) => setFormData({ ...formData, swift_code: e.target.value.toUpperCase() })}
                  placeholder="For international transfers"
                />
              </div>
            </div>

            <div className="space-y-4 pt-4 border-t">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Primary Account</Label>
                  <p className="text-sm text-muted-foreground">Default account for transactions</p>
                </div>
                <Switch
                  checked={formData.is_primary}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_primary: checked })}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Show on Invoice</Label>
                  <p className="text-sm text-muted-foreground">Display this account on invoices</p>
                </div>
                <Switch
                  checked={formData.show_on_invoice}
                  onCheckedChange={(checked) => setFormData({ ...formData, show_on_invoice: checked })}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Active</Label>
                  <p className="text-sm text-muted-foreground">Account is active and can be used</p>
                </div>
                <Switch
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsCreateOpen(false);
                setIsEditOpen(false);
                setEditingAccount(null);
                setFormData(defaultFormData);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={isEditOpen ? handleUpdate : handleCreate}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {(createMutation.isPending || updateMutation.isPending) && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {isEditOpen ? 'Update Account' : 'Add Account'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Bank Account</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the bank account &quot;{deletingAccount?.bank_name} - {deletingAccount?.branch_name}&quot;?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setIsDeleteOpen(false); setDeletingAccount(null); }}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
