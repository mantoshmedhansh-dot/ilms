'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { BookText, Download, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatDate, formatCurrency } from '@/lib/utils';

interface LedgerEntry {
  id: string;
  entry_date: string;
  entry_number: string;
  narration: string;
  debit: number;
  credit: number;
  running_balance: number;
  reference?: string;
}

interface Account {
  id: string;
  account_code: string;
  account_name: string;
  account_type: string;
}

const ledgerApi = {
  getAccounts: async () => {
    try {
      const { data } = await apiClient.get('/accounting/accounts');
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getLedger: async (accountId: string, params?: { page?: number; size?: number; from_date?: string; to_date?: string }) => {
    try {
      const { data } = await apiClient.get(`/accounting/ledger/${accountId}`, { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0, opening_balance: 0, closing_balance: 0 };
    }
  },
};

const columns: ColumnDef<LedgerEntry>[] = [
  {
    accessorKey: 'entry_date',
    header: 'Date',
    cell: ({ row }) => (
      <span className="text-sm">{formatDate(row.original.entry_date)}</span>
    ),
  },
  {
    accessorKey: 'entry_number',
    header: 'Voucher #',
    cell: ({ row }) => (
      <span className="font-mono text-sm">{row.original.entry_number}</span>
    ),
  },
  {
    accessorKey: 'narration',
    header: 'Particulars',
    cell: ({ row }) => (
      <div>
        <div className="text-sm">{row.original.narration}</div>
        {row.original.reference && (
          <div className="text-xs text-muted-foreground">Ref: {row.original.reference}</div>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'debit',
    header: 'Debit',
    cell: ({ row }) => (
      <span className={`font-medium ${row.original.debit > 0 ? 'text-green-600' : 'text-muted-foreground'}`}>
        {row.original.debit > 0 ? formatCurrency(row.original.debit) : '-'}
      </span>
    ),
  },
  {
    accessorKey: 'credit',
    header: 'Credit',
    cell: ({ row }) => (
      <span className={`font-medium ${row.original.credit > 0 ? 'text-red-600' : 'text-muted-foreground'}`}>
        {row.original.credit > 0 ? formatCurrency(row.original.credit) : '-'}
      </span>
    ),
  },
  {
    accessorKey: 'running_balance',
    header: 'Balance',
    cell: ({ row }) => (
      <span className={`font-medium ${row.original.running_balance < 0 ? 'text-red-600' : ''}`}>
        {formatCurrency(Math.abs(row.original.running_balance))}
        <span className="text-xs ml-1 text-muted-foreground">
          {row.original.running_balance >= 0 ? 'Dr' : 'Cr'}
        </span>
      </span>
    ),
  },
];

export default function GeneralLedgerPage() {
  const [selectedAccount, setSelectedAccount] = useState<string>('');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);

  const { data: accountsData } = useQuery({
    queryKey: ['accounts-list'],
    queryFn: ledgerApi.getAccounts,
  });

  const { data: ledgerData, isLoading } = useQuery({
    queryKey: ['ledger', selectedAccount, page, pageSize],
    queryFn: () => ledgerApi.getLedger(selectedAccount, { page: page + 1, size: pageSize }),
    enabled: !!selectedAccount,
  });

  // API returns { items: [...], total: ... }
  const accounts = accountsData?.items || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="General Ledger"
        description="View account-wise transaction details"
        actions={
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Filter className="h-5 w-5" />
            Select Account
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Select value={selectedAccount} onValueChange={setSelectedAccount}>
              <SelectTrigger className="w-[400px]">
                <SelectValue placeholder="Select an account to view ledger" />
              </SelectTrigger>
              <SelectContent>
                {accounts
                  .filter((account: Account) => account.id && String(account.id).trim() !== '')
                  .map((account: Account) => (
                    <SelectItem key={account.id} value={String(account.id)}>
                      <span className="font-mono mr-2">{account.account_code}</span>
                      {account.account_name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {selectedAccount ? (
        <DataTable
          columns={columns}
          data={ledgerData?.items ?? []}
          searchKey="narration"
          searchPlaceholder="Search transactions..."
          isLoading={isLoading}
          manualPagination
          pageCount={ledgerData?.pages ?? 0}
          pageIndex={page}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <BookText className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">Select an account to view its ledger</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
