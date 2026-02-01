'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, AlertCircle, CheckCircle2, Scale } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency } from '@/lib/utils';

interface TrialBalanceAccount {
  account_code: string;
  account_name: string;
  account_type: 'ASSET' | 'LIABILITY' | 'EQUITY' | 'REVENUE' | 'EXPENSE';
  debit_balance: number;
  credit_balance: number;
  opening_debit: number;
  opening_credit: number;
  period_debit: number;
  period_credit: number;
}

interface TrialBalanceData {
  as_of_date: string;
  period_start: string;
  period_end: string;
  accounts: TrialBalanceAccount[];
  total_debits: number;
  total_credits: number;
  is_balanced: boolean;
  difference: number;
}

const reportsApi = {
  getTrialBalance: async (params?: { period?: string; as_of_date?: string }): Promise<TrialBalanceData> => {
    try {
      const { data } = await apiClient.get('/reports/trial-balance', { params });
      return data;
    } catch {
      return {
        as_of_date: new Date().toISOString(),
        period_start: new Date().toISOString(),
        period_end: new Date().toISOString(),
        accounts: [],
        total_debits: 0,
        total_credits: 0,
        is_balanced: true,
        difference: 0
      };
    }
  },
};

const accountTypeColors: Record<string, string> = {
  ASSET: 'bg-blue-100 text-blue-800',
  LIABILITY: 'bg-red-100 text-red-800',
  EQUITY: 'bg-green-100 text-green-800',
  REVENUE: 'bg-purple-100 text-purple-800',
  EXPENSE: 'bg-orange-100 text-orange-800',
};

export default function TrialBalancePage() {
  const [period, setPeriod] = useState<string>('this_month');
  const [searchQuery, setSearchQuery] = useState('');
  const [accountTypeFilter, setAccountTypeFilter] = useState<string>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['trial-balance', period],
    queryFn: () => reportsApi.getTrialBalance({ period }),
  });

  const filteredAccounts = data?.accounts?.filter(account => {
    const matchesSearch = account.account_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      account.account_code.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = accountTypeFilter === 'all' || account.account_type === accountTypeFilter;
    return matchesSearch && matchesType;
  }) || [];

  // Group accounts by type for summary
  const accountSummary = data?.accounts?.reduce((acc, account) => {
    if (!acc[account.account_type]) {
      acc[account.account_type] = { debit: 0, credit: 0, count: 0 };
    }
    acc[account.account_type].debit += account.debit_balance;
    acc[account.account_type].credit += account.credit_balance;
    acc[account.account_type].count += 1;
    return acc;
  }, {} as Record<string, { debit: number; credit: number; count: number }>) || {};

  return (
    <div className="space-y-6">
      <PageHeader
        title="Trial Balance"
        description="View account balances and verify that debits equal credits"
        actions={
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        }
      />

      {/* Period Selection */}
      <div className="flex gap-4">
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select period" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="this_month">This Month</SelectItem>
            <SelectItem value="last_month">Last Month</SelectItem>
            <SelectItem value="this_quarter">This Quarter</SelectItem>
            <SelectItem value="last_quarter">Last Quarter</SelectItem>
            <SelectItem value="this_year">This Year</SelectItem>
            <SelectItem value="last_year">Last Year</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Balance Status */}
      <Card className={`border-l-4 ${data?.is_balanced ? 'border-l-green-500 bg-green-50' : 'border-l-red-500 bg-red-50'}`}>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {data?.is_balanced ? (
                <CheckCircle2 className="h-8 w-8 text-green-600" />
              ) : (
                <AlertCircle className="h-8 w-8 text-red-600" />
              )}
              <div>
                <h3 className={`font-bold ${data?.is_balanced ? 'text-green-800' : 'text-red-800'}`}>
                  {data?.is_balanced ? 'Trial Balance is Balanced' : 'Trial Balance is NOT Balanced'}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {data?.is_balanced
                    ? 'Total debits equal total credits'
                    : `Difference: ${formatCurrency(data?.difference || 0)}`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-8 font-mono">
              <div className="text-right">
                <div className="text-sm text-muted-foreground">Total Debits</div>
                <div className="text-xl font-bold">{formatCurrency(data?.total_debits || 0)}</div>
              </div>
              <Scale className="h-6 w-6 text-muted-foreground" />
              <div className="text-right">
                <div className="text-sm text-muted-foreground">Total Credits</div>
                <div className="text-xl font-bold">{formatCurrency(data?.total_credits || 0)}</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Account Type Summary */}
      <div className="grid gap-4 md:grid-cols-5">
        {(['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'] as const).map(type => (
          <Card key={type} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setAccountTypeFilter(type)}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                {type}
                <span className={`text-xs px-2 py-0.5 rounded ${accountTypeColors[type]}`}>
                  {accountSummary[type]?.count || 0}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1 text-sm font-mono">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Dr</span>
                  <span>{formatCurrency(accountSummary[type]?.debit || 0)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Cr</span>
                  <span>{formatCurrency(accountSummary[type]?.credit || 0)}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Trial Balance Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Account Balances</CardTitle>
              <CardDescription>
                Period: {data?.period_start ? new Date(data.period_start).toLocaleDateString('en-IN') : '-'} to {data?.period_end ? new Date(data.period_end).toLocaleDateString('en-IN') : '-'}
              </CardDescription>
            </div>
            <div className="flex gap-4">
              <Input
                placeholder="Search accounts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-[250px]"
              />
              <Select value={accountTypeFilter} onValueChange={setAccountTypeFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="All Types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="ASSET">Assets</SelectItem>
                  <SelectItem value="LIABILITY">Liabilities</SelectItem>
                  <SelectItem value="EQUITY">Equity</SelectItem>
                  <SelectItem value="REVENUE">Revenue</SelectItem>
                  <SelectItem value="EXPENSE">Expenses</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account Code</TableHead>
                  <TableHead>Account Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Opening Dr</TableHead>
                  <TableHead className="text-right">Opening Cr</TableHead>
                  <TableHead className="text-right">Period Dr</TableHead>
                  <TableHead className="text-right">Period Cr</TableHead>
                  <TableHead className="text-right">Closing Dr</TableHead>
                  <TableHead className="text-right">Closing Cr</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAccounts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                      No accounts found
                    </TableCell>
                  </TableRow>
                ) : (
                  <>
                    {filteredAccounts.map((account) => (
                      <TableRow key={account.account_code}>
                        <TableCell className="font-mono">{account.account_code}</TableCell>
                        <TableCell>{account.account_name}</TableCell>
                        <TableCell>
                          <span className={`text-xs px-2 py-0.5 rounded ${accountTypeColors[account.account_type]}`}>
                            {account.account_type}
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {account.opening_debit > 0 ? formatCurrency(account.opening_debit) : '-'}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {account.opening_credit > 0 ? formatCurrency(account.opening_credit) : '-'}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {account.period_debit > 0 ? formatCurrency(account.period_debit) : '-'}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {account.period_credit > 0 ? formatCurrency(account.period_credit) : '-'}
                        </TableCell>
                        <TableCell className="text-right font-mono font-medium">
                          {account.debit_balance > 0 ? formatCurrency(account.debit_balance) : '-'}
                        </TableCell>
                        <TableCell className="text-right font-mono font-medium">
                          {account.credit_balance > 0 ? formatCurrency(account.credit_balance) : '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                    {/* Totals Row */}
                    <TableRow className="bg-muted font-bold">
                      <TableCell colSpan={3}>TOTALS</TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(filteredAccounts.reduce((sum, a) => sum + a.opening_debit, 0))}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(filteredAccounts.reduce((sum, a) => sum + a.opening_credit, 0))}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(filteredAccounts.reduce((sum, a) => sum + a.period_debit, 0))}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(filteredAccounts.reduce((sum, a) => sum + a.period_credit, 0))}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(filteredAccounts.reduce((sum, a) => sum + a.debit_balance, 0))}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(filteredAccounts.reduce((sum, a) => sum + a.credit_balance, 0))}
                      </TableCell>
                    </TableRow>
                  </>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
