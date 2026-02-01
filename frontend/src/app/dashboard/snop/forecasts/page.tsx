'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  LineChart,
  Plus,
  RefreshCw,
  Filter,
  Download,
  Eye,
  CheckCircle,
  Clock,
  AlertCircle,
} from 'lucide-react';
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
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
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { snopApi } from '@/lib/api';
import { toast } from 'sonner';

const statusColors: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-800',
  PENDING_REVIEW: 'bg-yellow-100 text-yellow-800',
  UNDER_REVIEW: 'bg-blue-100 text-blue-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
};

export default function DemandForecastsPage() {
  const queryClient = useQueryClient();
  const [granularity, setGranularity] = useState<string>('MONTHLY');
  const [level, setLevel] = useState<string>('SKU');
  const [selectedForecast, setSelectedForecast] = useState<any>(null);

  const { data: forecasts, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['snop-forecasts', granularity, level],
    queryFn: () => snopApi.getForecasts({ granularity, level }),
  });

  const generateMutation = useMutation({
    mutationFn: () => snopApi.generateForecast({
      granularity,
      level,
      horizon_periods: 12,
    }),
    onSuccess: () => {
      toast.success('Forecast generation started');
      queryClient.invalidateQueries({ queryKey: ['snop-forecasts'] });
    },
    onError: () => {
      toast.error('Failed to generate forecast');
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <LineChart className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Demand Forecasting</h1>
            <p className="text-muted-foreground">
              AI-powered demand predictions using ensemble algorithms
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
            <Plus className="h-4 w-4 mr-2" />
            Generate Forecast
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <Select value={granularity} onValueChange={setGranularity}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Granularity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="DAILY">Daily</SelectItem>
                <SelectItem value="WEEKLY">Weekly</SelectItem>
                <SelectItem value="MONTHLY">Monthly</SelectItem>
                <SelectItem value="QUARTERLY">Quarterly</SelectItem>
              </SelectContent>
            </Select>
            <Select value={level} onValueChange={setLevel}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="SKU">By SKU</SelectItem>
                <SelectItem value="CATEGORY">By Category</SelectItem>
                <SelectItem value="REGION">By Region</SelectItem>
                <SelectItem value="CHANNEL">By Channel</SelectItem>
                <SelectItem value="COMPANY">Company-wide</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-yellow-600" />
              <span className="text-sm text-muted-foreground">Pending Review</span>
            </div>
            <p className="text-2xl font-bold mt-2">
              {forecasts?.items?.filter((f: any) => f.status === 'PENDING_REVIEW').length || 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span className="text-sm text-muted-foreground">Approved</span>
            </div>
            <p className="text-2xl font-bold mt-2">
              {forecasts?.items?.filter((f: any) => f.status === 'APPROVED').length || 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-blue-600" />
              <span className="text-sm text-muted-foreground">Avg Accuracy</span>
            </div>
            <p className="text-2xl font-bold mt-2">
              {forecasts?.avg_accuracy?.toFixed(1) || 85}%
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <LineChart className="h-4 w-4 text-purple-600" />
              <span className="text-sm text-muted-foreground">Total Forecasts</span>
            </div>
            <p className="text-2xl font-bold mt-2">{forecasts?.total || 0}</p>
          </CardContent>
        </Card>
      </div>

      {/* Forecasts Table */}
      <Card>
        <CardHeader>
          <CardTitle>Forecasts</CardTitle>
          <CardDescription>All demand forecasts with accuracy metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product/Category</TableHead>
                <TableHead>Level</TableHead>
                <TableHead>Granularity</TableHead>
                <TableHead>Algorithm</TableHead>
                <TableHead>Accuracy</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {forecasts?.items?.length > 0 ? (
                forecasts.items.map((forecast: any) => (
                  <TableRow key={forecast.id}>
                    <TableCell className="font-medium">
                      {forecast.product_name || forecast.category_name || 'All Products'}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{forecast.level}</Badge>
                    </TableCell>
                    <TableCell>{forecast.granularity}</TableCell>
                    <TableCell>{forecast.algorithm}</TableCell>
                    <TableCell>
                      <span className={forecast.accuracy >= 80 ? 'text-green-600' : 'text-amber-600'}>
                        {forecast.accuracy?.toFixed(1) || '-'}%
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge className={statusColors[forecast.status] || ''}>
                        {forecast.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(forecast.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedForecast(forecast)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-4xl">
                          <DialogHeader>
                            <DialogTitle>Forecast Details</DialogTitle>
                            <DialogDescription>
                              {forecast.product_name || forecast.category_name} - {forecast.granularity} forecast
                            </DialogDescription>
                          </DialogHeader>
                          <div className="h-80">
                            <ResponsiveContainer width="100%" height="100%">
                              <RechartsLineChart data={forecast.forecast_data || []}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="period" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Line
                                  type="monotone"
                                  dataKey="predicted_value"
                                  stroke="#3B82F6"
                                  strokeWidth={2}
                                  name="Predicted"
                                />
                                <Line
                                  type="monotone"
                                  dataKey="upper_bound"
                                  stroke="#93C5FD"
                                  strokeDasharray="3 3"
                                  name="Upper Bound"
                                />
                                <Line
                                  type="monotone"
                                  dataKey="lower_bound"
                                  stroke="#93C5FD"
                                  strokeDasharray="3 3"
                                  name="Lower Bound"
                                />
                              </RechartsLineChart>
                            </ResponsiveContainer>
                          </div>
                        </DialogContent>
                      </Dialog>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                    No forecasts found. Click &quot;Generate Forecast&quot; to create one.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
