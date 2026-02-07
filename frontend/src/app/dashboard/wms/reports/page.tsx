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
  FileSpreadsheet,
  FileType,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
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
      const { data } = await apiClient.get('/wms-reports/summary');
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

// Mock data for report preview
const getMockReportData = (reportId: string) => {
  const mockData: Record<string, { headers: string[]; rows: (string | number)[][] }> = {
    '1': { // Inventory Valuation
      headers: ['Category', 'Location', 'Quantity', 'Unit Cost', 'Total Value', 'Aging (Days)'],
      rows: [
        ['Electronics', 'Zone A', 1250, '$45.00', '$56,250', 15],
        ['Apparel', 'Zone B', 3400, '$22.50', '$76,500', 8],
        ['Home & Garden', 'Zone C', 890, '$35.00', '$31,150', 22],
        ['Sports', 'Zone A', 560, '$65.00', '$36,400', 5],
        ['Books', 'Zone D', 2100, '$12.00', '$25,200', 30],
      ],
    },
    '2': { // Stock Movement
      headers: ['Date', 'Product', 'Type', 'From', 'To', 'Quantity'],
      rows: [
        ['2026-02-06', 'SKU-001', 'Transfer', 'Zone A', 'Zone B', 150],
        ['2026-02-06', 'SKU-045', 'Adjustment', 'Zone C', '-', -25],
        ['2026-02-05', 'SKU-102', 'Receipt', 'Dock 1', 'Zone A', 500],
        ['2026-02-05', 'SKU-078', 'Transfer', 'Zone B', 'Zone D', 200],
        ['2026-02-04', 'SKU-033', 'Shipment', 'Zone A', 'Shipped', 75],
      ],
    },
    '3': { // Order Fulfillment
      headers: ['Order ID', 'Items', 'Pick Time', 'Pack Time', 'Ship Time', 'Status'],
      rows: [
        ['ORD-5521', 5, '12 min', '8 min', '5 min', 'Shipped'],
        ['ORD-5520', 3, '8 min', '5 min', '4 min', 'Shipped'],
        ['ORD-5519', 12, '25 min', '15 min', '7 min', 'In Transit'],
        ['ORD-5518', 1, '3 min', '2 min', '3 min', 'Delivered'],
        ['ORD-5517', 8, '18 min', '10 min', '6 min', 'Delivered'],
      ],
    },
    '4': { // Receiving Performance
      headers: ['Date', 'Dock', 'POs Received', 'Items', 'Putaway Time', 'Utilization'],
      rows: [
        ['2026-02-06', 'Dock 1', 12, 1450, '45 min', '85%'],
        ['2026-02-06', 'Dock 2', 8, 920, '38 min', '72%'],
        ['2026-02-05', 'Dock 1', 15, 2100, '52 min', '92%'],
        ['2026-02-05', 'Dock 2', 10, 1200, '41 min', '78%'],
        ['2026-02-04', 'Dock 1', 11, 1350, '44 min', '81%'],
      ],
    },
    '5': { // Labor Productivity
      headers: ['Worker', 'Shift', 'Tasks', 'Units Processed', 'Efficiency', 'Rating'],
      rows: [
        ['John Smith', 'Morning', 145, 1820, '94%', 'Excellent'],
        ['Maria Garcia', 'Morning', 138, 1650, '91%', 'Excellent'],
        ['David Lee', 'Afternoon', 125, 1480, '87%', 'Good'],
        ['Sarah Johnson', 'Afternoon', 132, 1580, '89%', 'Good'],
        ['Mike Brown', 'Night', 118, 1350, '82%', 'Average'],
      ],
    },
    '6': { // Picker Performance
      headers: ['Picker', 'Picks/Hour', 'Accuracy', 'Travel Time', 'Idle Time', 'Score'],
      rows: [
        ['John Smith', 85, '99.2%', '18%', '5%', 95],
        ['Maria Garcia', 78, '99.5%', '20%', '7%', 92],
        ['David Lee', 72, '98.8%', '22%', '8%', 88],
        ['Sarah Johnson', 80, '99.0%', '19%', '6%', 91],
        ['Mike Brown', 65, '98.5%', '25%', '10%', 82],
      ],
    },
    '7': { // Storage Utilization
      headers: ['Zone', 'Total Slots', 'Used', 'Available', 'Utilization', 'Status'],
      rows: [
        ['Zone A', 500, 425, 75, '85%', 'Optimal'],
        ['Zone B', 400, 380, 20, '95%', 'Near Capacity'],
        ['Zone C', 350, 280, 70, '80%', 'Optimal'],
        ['Zone D', 300, 150, 150, '50%', 'Underutilized'],
        ['Cold Storage', 100, 92, 8, '92%', 'Near Capacity'],
      ],
    },
    '8': { // Cost Analysis
      headers: ['Category', 'Orders', 'Per-Order Cost', 'Storage Cost', 'Handling', 'Total'],
      rows: [
        ['Standard', 1250, '$3.50', '$0.45', '$1.20', '$6,437.50'],
        ['Express', 450, '$5.25', '$0.45', '$2.10', '$3,510.00'],
        ['Bulk', 85, '$8.00', '$1.20', '$3.50', '$1,079.50'],
        ['Returns', 180, '$4.00', '$0.30', '$1.80', '$1,098.00'],
        ['International', 120, '$12.50', '$0.60', '$4.50', '$2,112.00'],
      ],
    },
  };
  return mockData[reportId] || { headers: ['No Data'], rows: [] };
};

export default function ReportsPage() {
  const [dateRange, setDateRange] = useState('30');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  // Dialog states
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<ReportCard | null>(null);
  const [exportFormat, setExportFormat] = useState<string>('pdf');
  const [isExporting, setIsExporting] = useState(false);

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

  const handleViewReport = (report: ReportCard) => {
    setSelectedReport(report);
    setViewDialogOpen(true);
  };

  const handleExportReport = (report: ReportCard) => {
    setSelectedReport(report);
    setExportFormat('pdf');
    setExportDialogOpen(true);
  };

  const handleExportConfirm = async () => {
    if (!selectedReport) return;

    setIsExporting(true);

    // Simulate export process
    await new Promise(resolve => setTimeout(resolve, 1500));

    const formatLabels: Record<string, string> = {
      pdf: 'PDF',
      excel: 'Excel',
      csv: 'CSV',
    };

    // Create a mock file download
    const reportData = getMockReportData(selectedReport.id);
    let content = '';
    let mimeType = '';
    let extension = '';

    if (exportFormat === 'csv') {
      content = [reportData.headers.join(','), ...reportData.rows.map(row => row.join(','))].join('\n');
      mimeType = 'text/csv';
      extension = 'csv';
    } else if (exportFormat === 'excel') {
      // For demo, we'll create a tab-separated file that Excel can open
      content = [reportData.headers.join('\t'), ...reportData.rows.map(row => row.join('\t'))].join('\n');
      mimeType = 'application/vnd.ms-excel';
      extension = 'xls';
    } else {
      // For PDF, we'll create a text representation (in production, use a PDF library)
      content = `${selectedReport.name}\n${'='.repeat(50)}\n\n`;
      content += `Generated: ${new Date().toLocaleString()}\n`;
      content += `Date Range: Last ${dateRange} days\n\n`;
      content += reportData.headers.join(' | ') + '\n';
      content += '-'.repeat(80) + '\n';
      content += reportData.rows.map(row => row.join(' | ')).join('\n');
      mimeType = 'text/plain';
      extension = 'txt';
    }

    // Create and trigger download
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${selectedReport.name.toLowerCase().replace(/\s+/g, '-')}-report.${extension}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setIsExporting(false);
    setExportDialogOpen(false);
    toast.success(`${selectedReport.name} exported as ${formatLabels[exportFormat]}`);
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
                <Button variant="outline" size="sm" onClick={() => handleViewReport(report)}>
                  <FileText className="h-4 w-4 mr-2" />
                  View
                </Button>
                <Button variant="ghost" size="sm" onClick={() => handleExportReport(report)}>
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* View Report Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedReport && getIcon(selectedReport.icon)}
              {selectedReport?.name}
            </DialogTitle>
            <DialogDescription>
              {selectedReport?.description} | Date range: Last {dateRange} days
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-auto">
            {selectedReport && (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      {getMockReportData(selectedReport.id).headers.map((header, idx) => (
                        <th key={idx} className="px-4 py-3 text-left font-medium">
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {getMockReportData(selectedReport.id).rows.map((row, rowIdx) => (
                      <tr key={rowIdx} className="border-t hover:bg-muted/50">
                        {row.map((cell, cellIdx) => (
                          <td key={cellIdx} className="px-4 py-3">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setViewDialogOpen(false)}>
              Close
            </Button>
            <Button onClick={() => {
              setViewDialogOpen(false);
              if (selectedReport) handleExportReport(selectedReport);
            }}>
              <Download className="h-4 w-4 mr-2" />
              Export Report
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Export Report Dialog */}
      <Dialog open={exportDialogOpen} onOpenChange={setExportDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Export Report</DialogTitle>
            <DialogDescription>
              Choose a format to export &quot;{selectedReport?.name}&quot;
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <RadioGroup value={exportFormat} onValueChange={setExportFormat} className="gap-4">
              <div className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-muted/50 cursor-pointer">
                <RadioGroupItem value="pdf" id="pdf" />
                <Label htmlFor="pdf" className="flex-1 cursor-pointer">
                  <div className="flex items-center gap-3">
                    <FileType className="h-5 w-5 text-red-500" />
                    <div>
                      <div className="font-medium">PDF Document</div>
                      <div className="text-sm text-muted-foreground">Best for printing and sharing</div>
                    </div>
                  </div>
                </Label>
              </div>
              <div className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-muted/50 cursor-pointer">
                <RadioGroupItem value="excel" id="excel" />
                <Label htmlFor="excel" className="flex-1 cursor-pointer">
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="h-5 w-5 text-green-600" />
                    <div>
                      <div className="font-medium">Excel Spreadsheet</div>
                      <div className="text-sm text-muted-foreground">Best for data analysis</div>
                    </div>
                  </div>
                </Label>
              </div>
              <div className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-muted/50 cursor-pointer">
                <RadioGroupItem value="csv" id="csv" />
                <Label htmlFor="csv" className="flex-1 cursor-pointer">
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-blue-500" />
                    <div>
                      <div className="font-medium">CSV File</div>
                      <div className="text-sm text-muted-foreground">Best for importing to other systems</div>
                    </div>
                  </div>
                </Label>
              </div>
            </RadioGroup>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setExportDialogOpen(false)} disabled={isExporting}>
              Cancel
            </Button>
            <Button onClick={handleExportConfirm} disabled={isExporting}>
              {isExporting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
