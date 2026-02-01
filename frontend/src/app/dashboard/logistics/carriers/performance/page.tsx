'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
  TrendingUp, TrendingDown, Truck, Package, Clock,
  AlertTriangle, CheckCircle, XCircle, BarChart3, Target
} from 'lucide-react';
import { format } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader } from '@/components/common';
import { rateCardsApi, transportersApi } from '@/lib/api';
import { cn } from '@/lib/utils';

interface CarrierPerformance {
  id: string;
  transporter_id: string;
  transporter_name?: string;
  transporter_code?: string;
  period_start: string;
  period_end: string;
  zone?: string;
  total_shipments: number;
  on_time_delivery_count: number;
  rto_count: number;
  damage_count: number;
  delivery_score: number;
  rto_score: number;
  overall_score: number;
  created_at: string;
}

interface Transporter {
  id: string;
  name: string;
  code: string;
}

const zones = ['A', 'B', 'C', 'D', 'E', 'F'];

function ScoreIndicator({ score, label }: { score: number; label: string }) {
  const getScoreColor = (s: number) => {
    if (s >= 90) return 'text-green-600';
    if (s >= 75) return 'text-emerald-600';
    if (s >= 60) return 'text-yellow-600';
    if (s >= 40) return 'text-orange-600';
    return 'text-red-600';
  };

  const getProgressColor = (s: number) => {
    if (s >= 90) return 'bg-green-500';
    if (s >= 75) return 'bg-emerald-500';
    if (s >= 60) return 'bg-yellow-500';
    if (s >= 40) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className={cn("text-sm font-semibold", getScoreColor(score))}>
          {score?.toFixed(1)}%
        </span>
      </div>
      <Progress value={score} className="h-2" indicatorClassName={getProgressColor(score)} />
    </div>
  );
}

export default function CarrierPerformancePage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [transporterFilter, setTransporterFilter] = useState<string>('all');
  const [zoneFilter, setZoneFilter] = useState<string>('all');

  // Queries
  const { data, isLoading } = useQuery({
    queryKey: ['carrier-performance', page, pageSize, transporterFilter, zoneFilter],
    queryFn: () => rateCardsApi.performance.list({
      page: page + 1,
      size: pageSize,
      transporter_id: transporterFilter !== 'all' ? transporterFilter : undefined,
      zone: zoneFilter !== 'all' ? zoneFilter : undefined,
    }),
  });

  const { data: transportersData } = useQuery({
    queryKey: ['transporters'],
    queryFn: () => transportersApi.list({ is_active: true }),
  });

  const transporters = transportersData?.items ?? transportersData ?? [];
  const performanceData = data?.items ?? [];

  // Calculate summary stats
  const stats = {
    totalCarriers: new Set(performanceData.map((p: CarrierPerformance) => p.transporter_id)).size,
    avgDeliveryScore: performanceData.length > 0
      ? performanceData.reduce((sum: number, p: CarrierPerformance) => sum + (p.delivery_score || 0), 0) / performanceData.length
      : 0,
    avgRtoScore: performanceData.length > 0
      ? performanceData.reduce((sum: number, p: CarrierPerformance) => sum + (p.rto_score || 0), 0) / performanceData.length
      : 0,
    avgOverallScore: performanceData.length > 0
      ? performanceData.reduce((sum: number, p: CarrierPerformance) => sum + (p.overall_score || 0), 0) / performanceData.length
      : 0,
    totalShipments: performanceData.reduce((sum: number, p: CarrierPerformance) => sum + (p.total_shipments || 0), 0),
    totalOnTime: performanceData.reduce((sum: number, p: CarrierPerformance) => sum + (p.on_time_delivery_count || 0), 0),
    totalRto: performanceData.reduce((sum: number, p: CarrierPerformance) => sum + (p.rto_count || 0), 0),
  };

  const columns: ColumnDef<CarrierPerformance>[] = [
    {
      accessorKey: 'transporter',
      header: 'Carrier',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-950">
            <Truck className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <div className="font-medium">{row.original.transporter_name || 'N/A'}</div>
            <div className="text-sm text-muted-foreground">{row.original.transporter_code}</div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'zone',
      header: 'Zone',
      cell: ({ row }) => (
        row.original.zone ? (
          <Badge variant="outline">Zone {row.original.zone}</Badge>
        ) : (
          <span className="text-muted-foreground">All Zones</span>
        )
      ),
    },
    {
      accessorKey: 'period',
      header: 'Period',
      cell: ({ row }) => (
        <div className="text-sm">
          {format(new Date(row.original.period_start), 'MMM d')} - {format(new Date(row.original.period_end), 'MMM d, yyyy')}
        </div>
      ),
    },
    {
      accessorKey: 'total_shipments',
      header: 'Shipments',
      cell: ({ row }) => (
        <div className="text-center font-medium">{row.original.total_shipments || 0}</div>
      ),
    },
    {
      accessorKey: 'on_time_delivery_count',
      header: 'On-Time',
      cell: ({ row }) => {
        const onTime = row.original.on_time_delivery_count || 0;
        const total = row.original.total_shipments || 1;
        const percentage = (onTime / total) * 100;
        return (
          <div className="flex items-center gap-2">
            {percentage >= 90 ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : percentage >= 70 ? (
              <Clock className="h-4 w-4 text-yellow-500" />
            ) : (
              <XCircle className="h-4 w-4 text-red-500" />
            )}
            <span>{onTime} ({percentage.toFixed(0)}%)</span>
          </div>
        );
      },
    },
    {
      accessorKey: 'rto_count',
      header: 'RTO',
      cell: ({ row }) => {
        const rto = row.original.rto_count || 0;
        const total = row.original.total_shipments || 1;
        const percentage = (rto / total) * 100;
        return (
          <div className="flex items-center gap-2">
            {percentage <= 5 ? (
              <TrendingDown className="h-4 w-4 text-green-500" />
            ) : percentage <= 10 ? (
              <TrendingUp className="h-4 w-4 text-yellow-500" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-red-500" />
            )}
            <span className={cn(percentage > 10 && 'text-red-600 font-medium')}>
              {rto} ({percentage.toFixed(1)}%)
            </span>
          </div>
        );
      },
    },
    {
      accessorKey: 'delivery_score',
      header: 'Delivery Score',
      cell: ({ row }) => <ScoreIndicator score={row.original.delivery_score || 0} label="" />,
    },
    {
      accessorKey: 'overall_score',
      header: 'Overall',
      cell: ({ row }) => {
        const score = row.original.overall_score || 0;
        return (
          <Badge
            className={cn(
              score >= 90 ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200' :
              score >= 75 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200' :
              score >= 60 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200' :
              score >= 40 ? 'bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-200' :
              'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200'
            )}
          >
            {score.toFixed(1)}%
          </Badge>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Carrier Performance"
        description="Monitor and analyze carrier delivery performance, RTO rates, and SLA compliance"
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Shipments</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalShipments.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              {stats.totalOnTime.toLocaleString()} delivered on time
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Delivery Score</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              stats.avgDeliveryScore >= 90 ? 'text-green-600' :
              stats.avgDeliveryScore >= 75 ? 'text-emerald-600' :
              stats.avgDeliveryScore >= 60 ? 'text-yellow-600' : 'text-red-600'
            )}>
              {stats.avgDeliveryScore.toFixed(1)}%
            </div>
            <Progress
              value={stats.avgDeliveryScore}
              className="mt-2 h-2"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">RTO Rate</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              stats.totalShipments > 0 && (stats.totalRto / stats.totalShipments) * 100 <= 5 ? 'text-green-600' :
              stats.totalShipments > 0 && (stats.totalRto / stats.totalShipments) * 100 <= 10 ? 'text-yellow-600' : 'text-red-600'
            )}>
              {stats.totalShipments > 0
                ? ((stats.totalRto / stats.totalShipments) * 100).toFixed(1)
                : '0'}%
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.totalRto.toLocaleString()} RTO shipments
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overall Score</CardTitle>
            <Target className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              stats.avgOverallScore >= 90 ? 'text-green-600' :
              stats.avgOverallScore >= 75 ? 'text-emerald-600' :
              stats.avgOverallScore >= 60 ? 'text-yellow-600' : 'text-red-600'
            )}>
              {stats.avgOverallScore.toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">
              Across {stats.totalCarriers} carriers
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Performance Breakdown by Zone */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Zone-wise Performance
          </CardTitle>
          <CardDescription>
            Compare carrier performance across different delivery zones
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-6 gap-4">
            {zones.map((zone) => {
              const zoneData = performanceData.filter((p: CarrierPerformance) => p.zone === zone);
              const avgScore = zoneData.length > 0
                ? zoneData.reduce((sum: number, p: CarrierPerformance) => sum + (p.overall_score || 0), 0) / zoneData.length
                : 0;
              const shipmentCount = zoneData.reduce((sum: number, p: CarrierPerformance) => sum + (p.total_shipments || 0), 0);

              return (
                <div key={zone} className="text-center p-4 rounded-lg border">
                  <div className="text-lg font-bold mb-1">Zone {zone}</div>
                  <div className={cn(
                    "text-2xl font-bold mb-2",
                    avgScore >= 90 ? 'text-green-600' :
                    avgScore >= 75 ? 'text-emerald-600' :
                    avgScore >= 60 ? 'text-yellow-600' :
                    avgScore > 0 ? 'text-red-600' : 'text-muted-foreground'
                  )}>
                    {avgScore > 0 ? `${avgScore.toFixed(0)}%` : '-'}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {shipmentCount.toLocaleString()} shipments
                  </div>
                  <Progress
                    value={avgScore}
                    className="mt-2 h-1"
                  />
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={transporterFilter} onValueChange={setTransporterFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="All Carriers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Carriers</SelectItem>
            {transporters.filter((t: Transporter) => t.id && t.id.trim() !== '').map((t: Transporter) => (
              <SelectItem key={t.id} value={t.id}>
                {t.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={zoneFilter} onValueChange={setZoneFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="All Zones" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Zones</SelectItem>
            {zones.map((zone) => (
              <SelectItem key={zone} value={zone}>Zone {zone}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={performanceData}
        searchKey="transporter_name"
        searchPlaceholder="Search carriers..."
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
