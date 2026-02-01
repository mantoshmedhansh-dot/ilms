'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, TrendingUp, TrendingDown, Minus, DollarSign, BarChart3 } from 'lucide-react';
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

interface ProfitLossLineItem {
  account_code: string;
  account_name: string;
  current_period: number;
  previous_period: number;
  variance: number;
  variance_percentage: number;
  is_group: boolean;
  indent_level: number;
}

interface ProfitLossSection {
  title: string;
  items: ProfitLossLineItem[];
  total: number;
  previous_total: number;
}

interface ProfitLossData {
  period_name: string;
  from_date: string;
  to_date: string;
  previous_period_name: string;
  revenue: ProfitLossSection;
  cost_of_goods_sold: ProfitLossSection;
  gross_profit: number;
  previous_gross_profit: number;
  operating_expenses: ProfitLossSection;
  operating_income: number;
  previous_operating_income: number;
  other_income: ProfitLossSection;
  other_expenses: ProfitLossSection;
  net_profit_before_tax: number;
  previous_net_profit_before_tax: number;
  tax_expense: number;
  previous_tax_expense: number;
  net_profit: number;
  previous_net_profit: number;
  gross_margin_percentage: number;
  operating_margin_percentage: number;
  net_margin_percentage: number;
}

const reportsApi = {
  getProfitLoss: async (params?: { period?: string; compare?: boolean }): Promise<ProfitLossData> => {
    try {
      const { data } = await apiClient.get('/reports/profit-loss', { params });
      return data;
    } catch {
      return {
        period_name: 'Current Period',
        from_date: new Date().toISOString(),
        to_date: new Date().toISOString(),
        previous_period_name: 'Previous Period',
        revenue: { title: 'Revenue', items: [], total: 0, previous_total: 0 },
        cost_of_goods_sold: { title: 'Cost of Goods Sold', items: [], total: 0, previous_total: 0 },
        gross_profit: 0,
        previous_gross_profit: 0,
        operating_expenses: { title: 'Operating Expenses', items: [], total: 0, previous_total: 0 },
        operating_income: 0,
        previous_operating_income: 0,
        other_income: { title: 'Other Income', items: [], total: 0, previous_total: 0 },
        other_expenses: { title: 'Other Expenses', items: [], total: 0, previous_total: 0 },
        net_profit_before_tax: 0,
        previous_net_profit_before_tax: 0,
        tax_expense: 0,
        previous_tax_expense: 0,
        net_profit: 0,
        previous_net_profit: 0,
        gross_margin_percentage: 0,
        operating_margin_percentage: 0,
        net_margin_percentage: 0,
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

function SectionTable({ section, showComparison }: { section: ProfitLossSection; showComparison: boolean }) {
  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-3 text-primary">{section.title}</h3>
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50">
            <TableHead className="w-[40%]">Account</TableHead>
            <TableHead className="text-right">Current Period</TableHead>
            {showComparison && (
              <>
                <TableHead className="text-right">Previous Period</TableHead>
                <TableHead className="text-right">Variance</TableHead>
              </>
            )}
          </TableRow>
        </TableHeader>
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
                <TableCell style={{ paddingLeft: `${item.indent_level * 1.5 + 1}rem` }}>
                  {item.account_code && <span className="text-muted-foreground mr-2">{item.account_code}</span>}
                  {item.account_name}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {formatCurrency(item.current_period)}
                </TableCell>
                {showComparison && (
                  <>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {formatCurrency(item.previous_period)}
                    </TableCell>
                    <TableCell className="text-right">
                      <VarianceIndicator value={item.variance} percentage={item.variance_percentage} />
                    </TableCell>
                  </>
                )}
              </TableRow>
            ))
          )}
          <TableRow className="font-bold bg-muted">
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

export default function ProfitLossPage() {
  const [period, setPeriod] = useState<string>('this_month');
  const [showComparison, setShowComparison] = useState(true);

  const { data, isLoading } = useQuery({
    queryKey: ['profit-loss', period, showComparison],
    queryFn: () => reportsApi.getProfitLoss({ period, compare: showComparison }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Profit & Loss Statement"
        description="Income statement showing revenues, costs, and expenses"
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
        <Select value={showComparison ? 'yes' : 'no'} onValueChange={(v) => setShowComparison(v === 'yes')}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Show comparison" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="yes">Compare with Previous</SelectItem>
            <SelectItem value="no">Current Period Only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(data?.revenue?.total || 0)}</div>
            {showComparison && data?.revenue && (
              <div className="flex items-center gap-2 mt-1">
                <VarianceIndicator
                  value={data.revenue.total - data.revenue.previous_total}
                  percentage={data.revenue.previous_total !== 0 ? ((data.revenue.total - data.revenue.previous_total) / data.revenue.previous_total) * 100 : 0}
                />
                <span className="text-xs text-muted-foreground">vs previous</span>
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Gross Profit</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(data?.gross_profit || 0)}</div>
            <p className="text-xs text-muted-foreground">
              Margin: {data?.gross_margin_percentage?.toFixed(1) || 0}%
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Operating Income</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(data?.operating_income || 0)}</div>
            <p className="text-xs text-muted-foreground">
              Margin: {data?.operating_margin_percentage?.toFixed(1) || 0}%
            </p>
          </CardContent>
        </Card>
        <Card className={`border-l-4 ${(data?.net_profit || 0) >= 0 ? 'border-l-green-500' : 'border-l-red-500'}`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Net Profit</CardTitle>
            {(data?.net_profit || 0) >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-600" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(data?.net_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(data?.net_profit || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Net Margin: {data?.net_margin_percentage?.toFixed(1) || 0}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* P&L Statement */}
      <Card>
        <CardHeader>
          <CardTitle>Income Statement</CardTitle>
          <CardDescription>
            {data?.period_name}: {data?.from_date ? new Date(data.from_date).toLocaleDateString('en-IN') : '-'} to {data?.to_date ? new Date(data.to_date).toLocaleDateString('en-IN') : '-'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : (
            <div className="space-y-6">
              {/* Revenue Section */}
              {data?.revenue && <SectionTable section={data.revenue} showComparison={showComparison} />}

              {/* Cost of Goods Sold */}
              {data?.cost_of_goods_sold && <SectionTable section={data.cost_of_goods_sold} showComparison={showComparison} />}

              {/* Gross Profit */}
              <div className="border-t-2 border-b-2 py-3 bg-blue-50">
                <Table>
                  <TableBody>
                    <TableRow className="font-bold text-lg">
                      <TableCell className="w-[40%]">Gross Profit</TableCell>
                      <TableCell className="text-right font-mono">{formatCurrency(data?.gross_profit || 0)}</TableCell>
                      {showComparison && (
                        <>
                          <TableCell className="text-right font-mono">{formatCurrency(data?.previous_gross_profit || 0)}</TableCell>
                          <TableCell className="text-right">
                            <VarianceIndicator
                              value={(data?.gross_profit || 0) - (data?.previous_gross_profit || 0)}
                              percentage={(data?.previous_gross_profit || 0) !== 0 ? (((data?.gross_profit || 0) - (data?.previous_gross_profit || 0)) / (data?.previous_gross_profit || 1)) * 100 : 0}
                            />
                          </TableCell>
                        </>
                      )}
                    </TableRow>
                  </TableBody>
                </Table>
              </div>

              {/* Operating Expenses */}
              {data?.operating_expenses && <SectionTable section={data.operating_expenses} showComparison={showComparison} />}

              {/* Operating Income */}
              <div className="border-t-2 border-b-2 py-3 bg-purple-50">
                <Table>
                  <TableBody>
                    <TableRow className="font-bold text-lg">
                      <TableCell className="w-[40%]">Operating Income</TableCell>
                      <TableCell className="text-right font-mono">{formatCurrency(data?.operating_income || 0)}</TableCell>
                      {showComparison && (
                        <>
                          <TableCell className="text-right font-mono">{formatCurrency(data?.previous_operating_income || 0)}</TableCell>
                          <TableCell className="text-right">
                            <VarianceIndicator
                              value={(data?.operating_income || 0) - (data?.previous_operating_income || 0)}
                              percentage={(data?.previous_operating_income || 0) !== 0 ? (((data?.operating_income || 0) - (data?.previous_operating_income || 0)) / (data?.previous_operating_income || 1)) * 100 : 0}
                            />
                          </TableCell>
                        </>
                      )}
                    </TableRow>
                  </TableBody>
                </Table>
              </div>

              {/* Other Income/Expenses */}
              {data?.other_income && data.other_income.items.length > 0 && (
                <SectionTable section={data.other_income} showComparison={showComparison} />
              )}
              {data?.other_expenses && data.other_expenses.items.length > 0 && (
                <SectionTable section={data.other_expenses} showComparison={showComparison} />
              )}

              {/* Net Profit Before Tax */}
              <div className="border-t-2 py-3 bg-gray-50">
                <Table>
                  <TableBody>
                    <TableRow className="font-bold">
                      <TableCell className="w-[40%]">Net Profit Before Tax</TableCell>
                      <TableCell className="text-right font-mono">{formatCurrency(data?.net_profit_before_tax || 0)}</TableCell>
                      {showComparison && (
                        <>
                          <TableCell className="text-right font-mono">{formatCurrency(data?.previous_net_profit_before_tax || 0)}</TableCell>
                          <TableCell className="text-right">
                            <VarianceIndicator
                              value={(data?.net_profit_before_tax || 0) - (data?.previous_net_profit_before_tax || 0)}
                              percentage={(data?.previous_net_profit_before_tax || 0) !== 0 ? (((data?.net_profit_before_tax || 0) - (data?.previous_net_profit_before_tax || 0)) / (data?.previous_net_profit_before_tax || 1)) * 100 : 0}
                            />
                          </TableCell>
                        </>
                      )}
                    </TableRow>
                    <TableRow>
                      <TableCell className="w-[40%] pl-8">Less: Tax Expense</TableCell>
                      <TableCell className="text-right font-mono">{formatCurrency(data?.tax_expense || 0)}</TableCell>
                      {showComparison && (
                        <>
                          <TableCell className="text-right font-mono">{formatCurrency(data?.previous_tax_expense || 0)}</TableCell>
                          <TableCell className="text-right" />
                        </>
                      )}
                    </TableRow>
                  </TableBody>
                </Table>
              </div>

              {/* Net Profit */}
              <div className={`border-t-4 border-b-4 py-4 ${(data?.net_profit || 0) >= 0 ? 'bg-green-50 border-green-500' : 'bg-red-50 border-red-500'}`}>
                <Table>
                  <TableBody>
                    <TableRow className="font-bold text-xl">
                      <TableCell className="w-[40%]">Net Profit / (Loss)</TableCell>
                      <TableCell className={`text-right font-mono ${(data?.net_profit || 0) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                        {formatCurrency(data?.net_profit || 0)}
                      </TableCell>
                      {showComparison && (
                        <>
                          <TableCell className="text-right font-mono">{formatCurrency(data?.previous_net_profit || 0)}</TableCell>
                          <TableCell className="text-right">
                            <VarianceIndicator
                              value={(data?.net_profit || 0) - (data?.previous_net_profit || 0)}
                              percentage={(data?.previous_net_profit || 0) !== 0 ? (((data?.net_profit || 0) - (data?.previous_net_profit || 0)) / Math.abs(data?.previous_net_profit || 1)) * 100 : 0}
                            />
                          </TableCell>
                        </>
                      )}
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
