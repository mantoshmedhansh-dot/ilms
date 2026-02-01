'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Gauge, AlertTriangle, CheckCircle, Clock, TrendingUp, TrendingDown, Truck, Package, Timer, XCircle } from 'lucide-react';
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
import { formatCurrency } from '@/lib/utils';

interface SLAStats {
  total_shipments: number;
  on_time_count: number;
  delayed_count: number;
  at_risk_count: number;
  sla_compliance_percent: number;
  avg_delivery_days: number;
  promised_days_avg: number;
}

interface TransporterPerformance {
  transporter_id: string;
  transporter_name: string;
  total_shipments: number;
  on_time_percent: number;
  avg_delay_hours: number;
  total_penalties: number;
  trend: 'UP' | 'DOWN' | 'STABLE';
}

interface AtRiskShipment {
  id: string;
  awb_number: string;
  order_id: string;
  transporter_name: string;
  customer_name: string;
  destination_city: string;
  promised_date: string;
  expected_date: string;
  delay_days: number;
  status: string;
}

const slaDashboardApi = {
  getStats: async (params?: { period?: string }): Promise<SLAStats> => {
    try {
      const { data } = await apiClient.get('/shipments/sla/stats', { params });
      return data;
    } catch {
      return {
        total_shipments: 0,
        on_time_count: 0,
        delayed_count: 0,
        at_risk_count: 0,
        sla_compliance_percent: 0,
        avg_delivery_days: 0,
        promised_days_avg: 0
      };
    }
  },
  getTransporterPerformance: async (params?: { period?: string }): Promise<TransporterPerformance[]> => {
    try {
      const { data } = await apiClient.get('/shipments/sla/transporter-performance', { params });
      return data.items || [];
    } catch {
      return [];
    }
  },
  getAtRiskShipments: async (): Promise<AtRiskShipment[]> => {
    try {
      const { data } = await apiClient.get('/shipments/sla/at-risk');
      return data.items || [];
    } catch {
      return [];
    }
  },
};

export default function SLADashboardPage() {
  const [period, setPeriod] = useState<string>('this_month');

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['sla-stats', period],
    queryFn: () => slaDashboardApi.getStats({ period }),
  });

  const { data: transporterPerformance, isLoading: performanceLoading } = useQuery({
    queryKey: ['transporter-performance', period],
    queryFn: () => slaDashboardApi.getTransporterPerformance({ period }),
  });

  const { data: atRiskShipments, isLoading: atRiskLoading } = useQuery({
    queryKey: ['at-risk-shipments'],
    queryFn: slaDashboardApi.getAtRiskShipments,
  });

  const isLoading = statsLoading || performanceLoading || atRiskLoading;

  // Compute SLA gauge color
  const getSLAColor = (percent: number) => {
    if (percent >= 95) return 'text-green-600';
    if (percent >= 85) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getSLABgColor = (percent: number) => {
    if (percent >= 95) return 'bg-green-100';
    if (percent >= 85) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="SLA Dashboard"
        description="Monitor shipment delivery performance and SLA compliance"
        actions={
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="yesterday">Yesterday</SelectItem>
              <SelectItem value="this_week">This Week</SelectItem>
              <SelectItem value="last_week">Last Week</SelectItem>
              <SelectItem value="this_month">This Month</SelectItem>
              <SelectItem value="last_month">Last Month</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      {/* Main SLA Gauge */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className={`col-span-1 ${getSLABgColor(stats?.sla_compliance_percent || 0)}`}>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">SLA Compliance Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center py-4">
              <div className="relative">
                <Gauge className={`h-32 w-32 ${getSLAColor(stats?.sla_compliance_percent || 0)}`} />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className={`text-4xl font-bold ${getSLAColor(stats?.sla_compliance_percent || 0)}`}>
                    {(stats?.sla_compliance_percent || 0).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
            <div className="text-center text-sm text-muted-foreground">
              Target: 95%
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-2">
          <CardHeader>
            <CardTitle>Delivery Performance</CardTitle>
            <CardDescription>Breakdown of shipment delivery status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center p-4 bg-muted rounded-lg">
                <Package className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                <div className="text-2xl font-bold">{stats?.total_shipments || 0}</div>
                <div className="text-sm text-muted-foreground">Total Shipments</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <CheckCircle className="h-8 w-8 mx-auto text-green-600 mb-2" />
                <div className="text-2xl font-bold text-green-600">{stats?.on_time_count || 0}</div>
                <div className="text-sm text-muted-foreground">On Time</div>
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <Clock className="h-8 w-8 mx-auto text-yellow-600 mb-2" />
                <div className="text-2xl font-bold text-yellow-600">{stats?.at_risk_count || 0}</div>
                <div className="text-sm text-muted-foreground">At Risk</div>
              </div>
              <div className="text-center p-4 bg-red-50 rounded-lg">
                <XCircle className="h-8 w-8 mx-auto text-red-600 mb-2" />
                <div className="text-2xl font-bold text-red-600">{stats?.delayed_count || 0}</div>
                <div className="text-sm text-muted-foreground">Delayed</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Delivery Time Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Delivery Time</CardTitle>
            <Timer className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(stats?.avg_delivery_days || 0).toFixed(1)} days</div>
            <p className="text-xs text-muted-foreground">
              Promised: {(stats?.promised_days_avg || 0).toFixed(1)} days
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Delay</CardTitle>
            <Clock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {((stats?.avg_delivery_days || 0) - (stats?.promised_days_avg || 0)).toFixed(1)} days
            </div>
            <p className="text-xs text-muted-foreground">Behind schedule</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">On-Time Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {stats?.total_shipments ? ((stats.on_time_count / stats.total_shipments) * 100).toFixed(1) : 0}%
            </div>
            <p className="text-xs text-muted-foreground">Of total delivered</p>
          </CardContent>
        </Card>
      </div>

      {/* Transporter Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Transporter Performance</CardTitle>
          <CardDescription>SLA compliance by transporter</CardDescription>
        </CardHeader>
        <CardContent>
          {performanceLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : transporterPerformance && transporterPerformance.length > 0 ? (
            <div className="space-y-4">
              {transporterPerformance.map((transporter) => (
                <div key={transporter.transporter_id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
                      <Truck className="h-6 w-6 text-muted-foreground" />
                    </div>
                    <div>
                      <div className="font-medium">{transporter.transporter_name}</div>
                      <div className="text-sm text-muted-foreground">
                        {transporter.total_shipments} shipments
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-8">
                    <div className="text-right">
                      <div className={`text-lg font-bold ${getSLAColor(transporter.on_time_percent)}`}>
                        {transporter.on_time_percent.toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground">On-time</div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-medium text-orange-600">
                        {transporter.avg_delay_hours > 0 ? `+${transporter.avg_delay_hours.toFixed(1)}h` : '-'}
                      </div>
                      <div className="text-xs text-muted-foreground">Avg delay</div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-medium text-red-600">
                        {transporter.total_penalties > 0 ? formatCurrency(transporter.total_penalties) : '-'}
                      </div>
                      <div className="text-xs text-muted-foreground">Penalties</div>
                    </div>
                    <div className="flex items-center">
                      {transporter.trend === 'UP' ? (
                        <TrendingUp className="h-5 w-5 text-green-600" />
                      ) : transporter.trend === 'DOWN' ? (
                        <TrendingDown className="h-5 w-5 text-red-600" />
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Truck className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No transporter data available</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* At Risk Shipments */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
                At-Risk Shipments
              </CardTitle>
              <CardDescription>Shipments likely to miss SLA</CardDescription>
            </div>
            <span className="text-2xl font-bold text-yellow-600">{atRiskShipments?.length || 0}</span>
          </div>
        </CardHeader>
        <CardContent>
          {atRiskLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : atRiskShipments && atRiskShipments.length > 0 ? (
            <div className="space-y-3">
              {atRiskShipments.slice(0, 10).map((shipment) => (
                <div key={shipment.id} className="flex items-center justify-between p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <div className="flex items-center gap-4">
                    <div>
                      <div className="font-mono font-medium">{shipment.awb_number}</div>
                      <div className="text-sm text-muted-foreground">
                        {shipment.customer_name} - {shipment.destination_city}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-sm">
                      <div className="text-muted-foreground">Transporter</div>
                      <div>{shipment.transporter_name}</div>
                    </div>
                    <div className="text-sm">
                      <div className="text-muted-foreground">Promised</div>
                      <div>{new Date(shipment.promised_date).toLocaleDateString('en-IN')}</div>
                    </div>
                    <div className="text-sm text-right">
                      <div className="text-muted-foreground">Expected Delay</div>
                      <div className="font-medium text-red-600">+{shipment.delay_days} days</div>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      shipment.status === 'IN_TRANSIT' ? 'bg-blue-100 text-blue-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {shipment.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ))}
              {atRiskShipments.length > 10 && (
                <div className="text-center text-sm text-muted-foreground">
                  +{atRiskShipments.length - 10} more at-risk shipments
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-600" />
              <p>No at-risk shipments</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
