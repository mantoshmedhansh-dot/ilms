'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  Download,
  FileText,
  TrendingUp,
  Package,
  Truck,
  Users,
  Calendar,
  Filter,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';

interface ReportSummary {
  total_orders_processed: number;
  total_items_shipped: number;
  avg_fulfillment_time: number;
  inventory_accuracy: number;
  on_time_shipping: number;
  return_rate: number;
}

interface ReportCard {
  id: string;
  name: string;
  description: string;
  category: 'INVENTORY' | 'OPERATIONS' | 'PRODUCTIVITY' | 'FINANCIAL';
  icon: string;
  lastGenerated?: string;
}

const reportsApi = {
  getSummary: async (): Promise<ReportSummary> => {
    try {
      const { data } = await apiClient.get('/wms/reports/summary');
      return data;
    } catch {
      return {
        total_orders_processed: 0,
        total_items_shipped: 0,
        avg_fulfillment_time: 0,
        inventory_accuracy: 0,
        on_time_shipping: 0,
        return_rate: 0,
      };
    }
  },
  getReportsList: async (): Promise<ReportCard[]> => {
    // Mock data for available reports
    return [
      {
        id: '1',
        name: 'Inventory Valuation',
        description: 'Current inventory value by category, location, and aging',
        category: 'INVENTORY',
        icon: 'package',
      },
      {
        id: '2',
        name: 'Stock Movement',
        description: 'Track inventory movements, transfers, and adjustments',
        category: 'INVENTORY',
        icon: 'trending',
      },
      {
        id: '3',
        name: 'Order Fulfillment',
        description: 'Order processing times, pick accuracy, and shipping metrics',
        category: 'OPERATIONS',
        icon: 'truck',
      },
      {
        id: '4',
        name: 'Receiving Performance',
        description: 'Inbound processing times, dock utilization, and putaway efficiency',
        category: 'OPERATIONS',
        icon: 'truck',
      },
      {
        id: '5',
        name: 'Labor Productivity',
        description: 'Worker performance, tasks completed, and efficiency metrics',
        category: 'PRODUCTIVITY',
        icon: 'users',
      },
      {
        id: '6',
        name: 'Picker Performance',
        description: 'Pick rates, accuracy, and travel time analysis',
        category: 'PRODUCTIVITY',
        icon: 'users',
      },
      {
        id: '7',
        name: 'Storage Utilization',
        description: 'Warehouse space usage, zone capacity, and optimization opportunities',
        category: 'FINANCIAL',
        icon: 'chart',
      },
      {
        id: '8',
        name: 'Cost Analysis',
        description: 'Per-order costs, storage costs, and handling expenses',
        category: 'FINANCIAL',
        icon: 'chart',
      },
    ];
  },
};

const categoryColors: Record<string, string> = {
  INVENTORY: 'border-l-blue-500',
  OPERATIONS: 'border-l-green-500',
  PRODUCTIVITY: 'border-l-purple-500',
  FINANCIAL: 'border-l-orange-500',
};

const categoryLabels: Record<string, string> = {
  INVENTORY: 'Inventory',
  OPERATIONS: 'Operations',
  PRODUCTIVITY: 'Productivity',
  FINANCIAL: 'Financial',
};

export default function ReportsPage() {
  const [dateRange, setDateRange] = useState('30');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const { data: summary } = useQuery({
    queryKey: ['wms-reports-summary', dateRange],
    queryFn: reportsApi.getSummary,
  });

  const { data: reports = [] } = useQuery({
    queryKey: ['wms-reports-list'],
    queryFn: reportsApi.getReportsList,
  });

  const filteredReports = categoryFilter === 'all'
    ? reports
    : reports.filter(r => r.category === categoryFilter);

  const getIcon = (icon: string) => {
    switch (icon) {
      case 'package': return <Package className="h-5 w-5" />;
      case 'trending': return <TrendingUp className="h-5 w-5" />;
      case 'truck': return <Truck className="h-5 w-5" />;
      case 'users': return <Users className="h-5 w-5" />;
      case 'chart': return <BarChart3 className="h-5 w-5" />;
      default: return <FileText className="h-5 w-5" />;
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="WMS Reports"
        description="Generate and view warehouse management reports"
        actions={
          <div className="flex items-center gap-2">
            <Select value={dateRange} onValueChange={setDateRange}>
              <SelectTrigger className="w-[150px]">
                <Calendar className="h-4 w-4 mr-2" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
                <SelectItem value="365">Last year</SelectItem>
              </SelectContent>
            </Select>
          </div>
        }
      />

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Orders Processed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_orders_processed?.toLocaleString() || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Items Shipped</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_items_shipped?.toLocaleString() || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Fulfillment</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.avg_fulfillment_time || 0}h</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Inventory Accuracy</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{summary?.inventory_accuracy || 0}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">On-Time Shipping</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{summary?.on_time_shipping || 0}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Return Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{summary?.return_rate || 0}%</div>
          </CardContent>
        </Card>
      </div>

      {/* Category Filter */}
      <div className="flex items-center gap-4">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            <SelectItem value="INVENTORY">Inventory</SelectItem>
            <SelectItem value="OPERATIONS">Operations</SelectItem>
            <SelectItem value="PRODUCTIVITY">Productivity</SelectItem>
            <SelectItem value="FINANCIAL">Financial</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Reports Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {filteredReports.map((report) => (
          <Card
            key={report.id}
            className={`cursor-pointer hover:shadow-md transition-shadow border-l-4 ${categoryColors[report.category]}`}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                  {getIcon(report.icon)}
                </div>
                <span className="text-xs px-2 py-1 rounded-full bg-muted">
                  {categoryLabels[report.category]}
                </span>
              </div>
              <CardTitle className="text-base mt-3">{report.name}</CardTitle>
              <CardDescription className="text-sm">{report.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <Button variant="outline" size="sm">
                  <FileText className="h-4 w-4 mr-2" />
                  View
                </Button>
                <Button variant="ghost" size="sm">
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
