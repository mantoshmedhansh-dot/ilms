'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, Building2, Wallet, PiggyBank, TrendingUp, TrendingDown, Minus, Scale } from 'lucide-react';
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
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency } from '@/lib/utils';

interface BalanceSheetLineItem {
  account_code: string;
  account_name: string;
  current_balance: number;
  previous_balance: number;
  variance: number;
  variance_percentage: number;
  is_group: boolean;
  indent_level: number;
}

interface BalanceSheetSection {
  title: string;
  items: BalanceSheetLineItem[];
  total: number;
  previous_total: number;
}

interface BalanceSheetData {
  as_of_date: string;
  previous_date: string;
  assets: {
    current_assets: BalanceSheetSection;
    non_current_assets: BalanceSheetSection;
    total: number;
    previous_total: number;
  };
  liabilities: {
    current_liabilities: BalanceSheetSection;
    non_current_liabilities: BalanceSheetSection;
    total: number;
    previous_total: number;
  };
  equity: BalanceSheetSection;
  total_liabilities_and_equity: number;
  previous_total_liabilities_and_equity: number;
  is_balanced: boolean;
  difference: number;
  current_ratio: number;
  debt_to_equity: number;
  working_capital: number;
}

const reportsApi = {
  getBalanceSheet: async (params?: { as_of_date?: string; compare?: boolean }): Promise<BalanceSheetData> => {
    try {
      const { data } = await apiClient.get('/reports/balance-sheet', { params });
      return data;
    } catch {
      return {
        as_of_date: new Date().toISOString(),
        previous_date: new Date().toISOString(),
        assets: {
          current_assets: { title: 'Current Assets', items: [], total: 0, previous_total: 0 },
          non_current_assets: { title: 'Non-Current Assets', items: [], total: 0, previous_total: 0 },
          total: 0,
          previous_total: 0,
        },
        liabilities: {
          current_liabilities: { title: 'Current Liabilities', items: [], total: 0, previous_total: 0 },
          non_current_liabilities: { title: 'Non-Current Liabilities', items: [], total: 0, previous_total: 0 },
          total: 0,
          previous_total: 0,
        },
        equity: { title: 'Shareholders Equity', items: [], total: 0, previous_total: 0 },
        total_liabilities_and_equity: 0,
        previous_total_liabilities_and_equity: 0,
        is_balanced: true,
        difference: 0,
        current_ratio: 0,
        debt_to_equity: 0,
        working_capital: 0,
      };
    }
  },
};

function VarianceIndicator({ value, percentage }: { value: number; percentage: number }) {
  if (value === 0) {
    return (
      <div className="flex items-center gap-1 text-gray-500">
        <Minus className="h-3 w-3" />
        <span className="text-xs">0%</span>
      </div>
    );
  }
  return value > 0 ? (
    <div className="flex items-center gap-1 text-green-600">
      <TrendingUp className="h-3 w-3" />
      <span className="text-xs">+{percentage.toFixed(1)}%</span>
    </div>
  ) : (
    <div className="flex items-center gap-1 text-red-600">
      <TrendingDown className="h-3 w-3" />
      <span className="text-xs">{percentage.toFixed(1)}%</span>
    </div>
  );
}

function SectionTable({ section, showComparison }: { section: BalanceSheetSection; showComparison: boolean }) {
  return (
    <div className="mb-4">
      <h4 className="text-md font-semibold mb-2 text-muted-foreground">{section.title}</h4>
      <Table>
        <TableBody>
          {section.items.length === 0 ? (
            <TableRow>
              <TableCell colSpan={showComparison ? 4 : 2} className="text-center text-muted-foreground py-4">
                No data available
              </TableCell>
            </TableRow>
          ) : (
            section.items.map((item, index) => (
              <TableRow key={index} className={item.is_group ? 'font-semibold bg-muted/30' : ''}>
                <TableCell className="w-[50%]" style={{ paddingLeft: `${item.indent_level * 1.5 + 1}rem` }}>
                  {item.account_code && <span className="text-muted-foreground mr-2">{item.account_code}</span>}
                  {item.account_name}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {formatCurrency(item.current_balance)}
                </TableCell>
                {showComparison && (
                  <>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {formatCurrency(item.previous_balance)}
                    </TableCell>
                    <TableCell className="text-right">
                      <VarianceIndicator value={item.variance} percentage={item.variance_percentage} />
                    </TableCell>
                  </>
                )}
              </TableRow>
            ))
          )}
          <TableRow className="font-bold border-t-2">
            <TableCell>Total {section.title}</TableCell>
            <TableCell className="text-right font-mono">{formatCurrency(section.total)}</TableCell>
            {showComparison && (
              <>
                <TableCell className="text-right font-mono">{formatCurrency(section.previous_total)}</TableCell>
                <TableCell className="text-right">
                  <VarianceIndicator
                    value={section.total - section.previous_total}
                    percentage={section.previous_total !== 0 ? ((section.total - section.previous_total) / section.previous_total) * 100 : 0}
                  />
                </TableCell>
              </>
            )}
          </TableRow>
        </TableBody>
      </Table>
    </div>
  );
}

export default function BalanceSheetPage() {
  const [asOfDate, setAsOfDate] = useState<string>('today');
  const [showComparison, setShowComparison] = useState(true);

  const { data, isLoading } = useQuery({
    queryKey: ['balance-sheet', asOfDate, showComparison],
    queryFn: () => reportsApi.getBalanceSheet({ as_of_date: asOfDate, compare: showComparison }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Balance Sheet"
        description="Statement of financial position showing assets, liabilities, and equity"
        actions={
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        }
      />

      {/* Date Selection */}
      <div className="flex gap-4">
        <Select value={asOfDate} onValueChange={setAsOfDate}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="As of date" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="today">Today</SelectItem>
            <SelectItem value="month_end">Month End</SelectItem>
            <SelectItem value="quarter_end">Quarter End</SelectItem>
            <SelectItem value="year_end">Year End</SelectItem>
            <SelectItem value="last_month_end">Last Month End</SelectItem>
            <SelectItem value="last_quarter_end">Last Quarter End</SelectItem>
            <SelectItem value="last_year_end">Last Year End</SelectItem>
          </SelectContent>
        </Select>
        <Select value={showComparison ? 'yes' : 'no'} onValueChange={(v) => setShowComparison(v === 'yes')}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Show comparison" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="yes">Compare with Previous</SelectItem>
            <SelectItem value="no">Current Date Only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Balance Check Card */}
      <Card className={`border-l-4 ${data?.is_balanced ? 'border-l-green-500 bg-green-50' : 'border-l-red-500 bg-red-50'}`}>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Scale className={`h-8 w-8 ${data?.is_balanced ? 'text-green-600' : 'text-red-600'}`} />
              <div>
                <h3 className={`font-bold ${data?.is_balanced ? 'text-green-800' : 'text-red-800'}`}>
                  {data?.is_balanced ? 'Balance Sheet is Balanced' : 'Balance Sheet is NOT Balanced'}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {data?.is_balanced
                    ? 'Assets equal Liabilities + Equity'
                    : `Difference: ${formatCurrency(data?.difference || 0)}`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-8 font-mono">
              <div className="text-right">
                <div className="text-sm text-muted-foreground">Total Assets</div>
                <div className="text-xl font-bold">{formatCurrency(data?.assets?.total || 0)}</div>
              </div>
              <Scale className="h-6 w-6 text-muted-foreground" />
              <div className="text-right">
                <div className="text-sm text-muted-foreground">Liabilities + Equity</div>
                <div className="text-xl font-bold">{formatCurrency(data?.total_liabilities_and_equity || 0)}</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Ratios */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Assets</CardTitle>
            <Building2 className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(data?.assets?.total || 0)}</div>
            {showComparison && data?.assets && (
              <div className="flex items-center gap-2 mt-1">
                <VarianceIndicator
                  value={data.assets.total - data.assets.previous_total}
                  percentage={data.assets.previous_total !== 0 ? ((data.assets.total - data.assets.previous_total) / data.assets.previous_total) * 100 : 0}
                />
                <span className="text-xs text-muted-foreground">vs previous</span>
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Working Capital</CardTitle>
            <Wallet className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(data?.working_capital || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(data?.working_capital || 0)}
            </div>
            <p className="text-xs text-muted-foreground">Current Assets - Current Liabilities</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current Ratio</CardTitle>
            <Scale className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(data?.current_ratio || 0) >= 1 ? 'text-green-600' : 'text-red-600'}`}>
              {(data?.current_ratio || 0).toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">
              {(data?.current_ratio || 0) >= 1 ? 'Healthy liquidity' : 'Low liquidity'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Debt to Equity</CardTitle>
            <PiggyBank className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(data?.debt_to_equity || 0) <= 2 ? 'text-green-600' : 'text-orange-600'}`}>
              {(data?.debt_to_equity || 0).toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">
              {(data?.debt_to_equity || 0) <= 2 ? 'Conservative leverage' : 'High leverage'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Balance Sheet Statement */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Assets */}
        <Card>
          <CardHeader className="bg-blue-50">
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-blue-600" />
              Assets
            </CardTitle>
            <CardDescription>
              As of {data?.as_of_date ? new Date(data.as_of_date).toLocaleDateString('en-IN') : '-'}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              </div>
            ) : (
              <>
                {data?.assets?.current_assets && (
                  <SectionTable section={data.assets.current_assets} showComparison={showComparison} />
                )}
                {data?.assets?.non_current_assets && (
                  <SectionTable section={data.assets.non_current_assets} showComparison={showComparison} />
                )}
                <div className="border-t-4 border-blue-500 pt-3 mt-4">
                  <Table>
                    <TableBody>
                      <TableRow className="font-bold text-lg">
                        <TableCell className="w-[50%]">TOTAL ASSETS</TableCell>
                        <TableCell className="text-right font-mono text-blue-700">
                          {formatCurrency(data?.assets?.total || 0)}
                        </TableCell>
                        {showComparison && (
                          <>
                            <TableCell className="text-right font-mono">
                              {formatCurrency(data?.assets?.previous_total || 0)}
                            </TableCell>
                            <TableCell className="text-right">
                              <VarianceIndicator
                                value={(data?.assets?.total || 0) - (data?.assets?.previous_total || 0)}
                                percentage={(data?.assets?.previous_total || 0) !== 0 ? (((data?.assets?.total || 0) - (data?.assets?.previous_total || 0)) / (data?.assets?.previous_total || 1)) * 100 : 0}
                              />
                            </TableCell>
                          </>
                        )}
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Liabilities & Equity */}
        <Card>
          <CardHeader className="bg-purple-50">
            <CardTitle className="flex items-center gap-2">
              <PiggyBank className="h-5 w-5 text-purple-600" />
              Liabilities & Equity
            </CardTitle>
            <CardDescription>
              As of {data?.as_of_date ? new Date(data.as_of_date).toLocaleDateString('en-IN') : '-'}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              </div>
            ) : (
              <>
                {/* Liabilities */}
                <h3 className="text-lg font-semibold mb-3 text-red-700">Liabilities</h3>
                {data?.liabilities?.current_liabilities && (
                  <SectionTable section={data.liabilities.current_liabilities} showComparison={showComparison} />
                )}
                {data?.liabilities?.non_current_liabilities && (
                  <SectionTable section={data.liabilities.non_current_liabilities} showComparison={showComparison} />
                )}
                <div className="border-t-2 border-red-300 pt-2 mb-6">
                  <Table>
                    <TableBody>
                      <TableRow className="font-bold">
                        <TableCell className="w-[50%]">Total Liabilities</TableCell>
                        <TableCell className="text-right font-mono text-red-700">
                          {formatCurrency(data?.liabilities?.total || 0)}
                        </TableCell>
                        {showComparison && (
                          <>
                            <TableCell className="text-right font-mono">
                              {formatCurrency(data?.liabilities?.previous_total || 0)}
                            </TableCell>
                            <TableCell className="text-right">
                              <VarianceIndicator
                                value={(data?.liabilities?.total || 0) - (data?.liabilities?.previous_total || 0)}
                                percentage={(data?.liabilities?.previous_total || 0) !== 0 ? (((data?.liabilities?.total || 0) - (data?.liabilities?.previous_total || 0)) / (data?.liabilities?.previous_total || 1)) * 100 : 0}
                              />
                            </TableCell>
                          </>
                        )}
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>

                {/* Equity */}
                <h3 className="text-lg font-semibold mb-3 text-green-700">Shareholders Equity</h3>
                {data?.equity && <SectionTable section={data.equity} showComparison={showComparison} />}

                {/* Total Liabilities & Equity */}
                <div className="border-t-4 border-purple-500 pt-3 mt-4">
                  <Table>
                    <TableBody>
                      <TableRow className="font-bold text-lg">
                        <TableCell className="w-[50%]">TOTAL LIABILITIES & EQUITY</TableCell>
                        <TableCell className="text-right font-mono text-purple-700">
                          {formatCurrency(data?.total_liabilities_and_equity || 0)}
                        </TableCell>
                        {showComparison && (
                          <>
                            <TableCell className="text-right font-mono">
                              {formatCurrency(data?.previous_total_liabilities_and_equity || 0)}
                            </TableCell>
                            <TableCell className="text-right">
                              <VarianceIndicator
                                value={(data?.total_liabilities_and_equity || 0) - (data?.previous_total_liabilities_and_equity || 0)}
                                percentage={(data?.previous_total_liabilities_and_equity || 0) !== 0 ? (((data?.total_liabilities_and_equity || 0) - (data?.previous_total_liabilities_and_equity || 0)) / (data?.previous_total_liabilities_and_equity || 1)) * 100 : 0}
                              />
                            </TableCell>
                          </>
                        )}
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
