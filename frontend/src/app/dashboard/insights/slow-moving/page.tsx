'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Package,
  Clock,
  Percent,
  Trash2,
  ArrowLeft,
  RefreshCw,
  Download,
  Search,
  AlertTriangle,
  Tag,
  TrendingDown,
} from 'lucide-react';
import Link from 'next/link';
import { insightsApi, SlowMovingItem } from '@/lib/api';

export default function SlowMovingInventoryPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [recommendationFilter, setRecommendationFilter] = useState<string>('all');
  const [daysThreshold, setDaysThreshold] = useState(60);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['slow-moving-inventory', daysThreshold],
    queryFn: () => insightsApi.getSlowMovingInventory({ days_threshold: daysThreshold, limit: 100 }),
  });

  const getRecommendationColor = (recommendation: string) => {
    switch (recommendation) {
      case 'WRITE_OFF':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'HEAVY_DISCOUNT':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'DISCOUNT':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'PROMOTION':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getRecommendationIcon = (recommendation: string) => {
    switch (recommendation) {
      case 'WRITE_OFF':
        return <Trash2 className="h-4 w-4 text-red-600" />;
      case 'HEAVY_DISCOUNT':
        return <AlertTriangle className="h-4 w-4 text-orange-600" />;
      case 'DISCOUNT':
        return <Percent className="h-4 w-4 text-yellow-600" />;
      case 'PROMOTION':
        return <Tag className="h-4 w-4 text-blue-600" />;
      default:
        return <Package className="h-4 w-4 text-gray-600" />;
    }
  };

  const getRecommendationLabel = (recommendation: string) => {
    switch (recommendation) {
      case 'WRITE_OFF':
        return 'Write Off';
      case 'HEAVY_DISCOUNT':
        return 'Heavy Discount (40-50%)';
      case 'DISCOUNT':
        return 'Discount (20-30%)';
      case 'PROMOTION':
        return 'Promotion';
      default:
        return recommendation;
    }
  };

  const filteredItems = data?.items?.filter((item: SlowMovingItem) => {
    const matchesSearch =
      item.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.sku.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRecommendation =
      recommendationFilter === 'all' || item.recommendation === recommendationFilter;
    return matchesSearch && matchesRecommendation;
  }) || [];

  const recommendationCounts = {
    WRITE_OFF: data?.items?.filter((i: SlowMovingItem) => i.recommendation === 'WRITE_OFF').length || 0,
    HEAVY_DISCOUNT: data?.items?.filter((i: SlowMovingItem) => i.recommendation === 'HEAVY_DISCOUNT').length || 0,
    DISCOUNT: data?.items?.filter((i: SlowMovingItem) => i.recommendation === 'DISCOUNT').length || 0,
    PROMOTION: data?.items?.filter((i: SlowMovingItem) => i.recommendation === 'PROMOTION').length || 0,
  };

  const totalStockValue = filteredItems.reduce(
    (sum: number, item: SlowMovingItem) => sum + (item.stock_value || 0),
    0
  );

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="h-96 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          Failed to load slow-moving inventory data. Please try again.
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard/insights"
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Slow Moving Inventory
            </h1>
            <p className="text-gray-500">
              Items with no sales in the past {daysThreshold}+ days
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <select
            value={daysThreshold}
            onChange={(e) => setDaysThreshold(Number(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
          >
            <option value={30}>30+ days</option>
            <option value={60}>60+ days</option>
            <option value={90}>90+ days</option>
            <option value={120}>120+ days</option>
            <option value={180}>180+ days</option>
          </select>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors">
            <Download className="h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div
          className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
            recommendationFilter === 'WRITE_OFF'
              ? 'border-red-500 bg-red-50'
              : 'border-red-200 bg-red-50 hover:border-red-400'
          }`}
          onClick={() =>
            setRecommendationFilter(
              recommendationFilter === 'WRITE_OFF' ? 'all' : 'WRITE_OFF'
            )
          }
        >
          <div className="flex items-center justify-between">
            <span className="text-red-600 font-medium">Write Off</span>
            <Trash2 className="h-5 w-5 text-red-600" />
          </div>
          <p className="text-2xl font-bold text-red-700 mt-2">
            {recommendationCounts.WRITE_OFF}
          </p>
          <p className="text-sm text-red-600">&gt; 180 days unsold</p>
        </div>

        <div
          className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
            recommendationFilter === 'HEAVY_DISCOUNT'
              ? 'border-orange-500 bg-orange-50'
              : 'border-orange-200 bg-orange-50 hover:border-orange-400'
          }`}
          onClick={() =>
            setRecommendationFilter(
              recommendationFilter === 'HEAVY_DISCOUNT' ? 'all' : 'HEAVY_DISCOUNT'
            )
          }
        >
          <div className="flex items-center justify-between">
            <span className="text-orange-600 font-medium">Heavy Discount</span>
            <AlertTriangle className="h-5 w-5 text-orange-600" />
          </div>
          <p className="text-2xl font-bold text-orange-700 mt-2">
            {recommendationCounts.HEAVY_DISCOUNT}
          </p>
          <p className="text-sm text-orange-600">120-180 days unsold</p>
        </div>

        <div
          className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
            recommendationFilter === 'DISCOUNT'
              ? 'border-yellow-500 bg-yellow-50'
              : 'border-yellow-200 bg-yellow-50 hover:border-yellow-400'
          }`}
          onClick={() =>
            setRecommendationFilter(
              recommendationFilter === 'DISCOUNT' ? 'all' : 'DISCOUNT'
            )
          }
        >
          <div className="flex items-center justify-between">
            <span className="text-yellow-600 font-medium">Discount</span>
            <Percent className="h-5 w-5 text-yellow-600" />
          </div>
          <p className="text-2xl font-bold text-yellow-700 mt-2">
            {recommendationCounts.DISCOUNT}
          </p>
          <p className="text-sm text-yellow-600">90-120 days unsold</p>
        </div>

        <div
          className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
            recommendationFilter === 'PROMOTION'
              ? 'border-blue-500 bg-blue-50'
              : 'border-blue-200 bg-blue-50 hover:border-blue-400'
          }`}
          onClick={() =>
            setRecommendationFilter(
              recommendationFilter === 'PROMOTION' ? 'all' : 'PROMOTION'
            )
          }
        >
          <div className="flex items-center justify-between">
            <span className="text-blue-600 font-medium">Promotion</span>
            <Tag className="h-5 w-5 text-blue-600" />
          </div>
          <p className="text-2xl font-bold text-blue-700 mt-2">
            {recommendationCounts.PROMOTION}
          </p>
          <p className="text-sm text-blue-600">60-90 days unsold</p>
        </div>
      </div>

      {/* Stock Value Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center justify-between">
        <div>
          <p className="text-amber-800 font-medium">
            Total Slow-Moving Stock Value (Filtered)
          </p>
          <p className="text-sm text-amber-600">
            Capital tied up in non-moving inventory
          </p>
        </div>
        <p className="text-2xl font-bold text-amber-700">
          {new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0,
          }).format(totalStockValue)}
        </p>
      </div>

      {/* Search and Filters */}
      <div className="flex gap-4 items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by product name or SKU..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
          />
        </div>
        {recommendationFilter !== 'all' && (
          <button
            onClick={() => setRecommendationFilter('all')}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Clear filter
          </button>
        )}
        <div className="text-sm text-gray-500">
          Showing {filteredItems.length} of {data?.total || 0} items
        </div>
      </div>

      {/* Items Table */}
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Product
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Days Since Sale
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Stock Quantity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Stock Value
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Recommendation
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredItems.map((item: SlowMovingItem) => (
              <tr key={item.product_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <p className="font-medium text-gray-900">
                      {item.product_name}
                    </p>
                    <p className="text-sm text-gray-500">{item.sku}</p>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-gray-400" />
                    <span
                      className={`font-medium ${
                        item.days_since_last_sale > 180
                          ? 'text-red-600'
                          : item.days_since_last_sale > 120
                          ? 'text-orange-600'
                          : item.days_since_last_sale > 90
                          ? 'text-yellow-600'
                          : 'text-gray-900'
                      }`}
                    >
                      {item.days_since_last_sale} days
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-900">
                  {item.current_stock} units
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-900">
                  {new Intl.NumberFormat('en-IN', {
                    style: 'currency',
                    currency: 'INR',
                    maximumFractionDigits: 0,
                  }).format(item.stock_value || 0)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRecommendationColor(
                      item.recommendation
                    )}`}
                  >
                    {getRecommendationIcon(item.recommendation)}
                    {getRecommendationLabel(item.recommendation)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  {item.recommendation === 'WRITE_OFF' ? (
                    <button className="text-red-600 hover:text-red-800 font-medium text-sm">
                      Process Write-Off
                    </button>
                  ) : item.recommendation === 'HEAVY_DISCOUNT' ||
                    item.recommendation === 'DISCOUNT' ? (
                    <button className="text-orange-600 hover:text-orange-800 font-medium text-sm">
                      Create Discount
                    </button>
                  ) : (
                    <button className="text-blue-600 hover:text-blue-800 font-medium text-sm">
                      Add to Promotion
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {filteredItems.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-6 py-12 text-center text-gray-500"
                >
                  {searchTerm || recommendationFilter !== 'all'
                    ? 'No items match your filters'
                    : 'No slow-moving inventory found'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Action Summary */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
          <TrendingDown className="h-5 w-5 text-gray-600" />
          Recommended Actions Summary
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="bg-white rounded-lg p-3 border">
            <p className="text-gray-600">
              <strong>Write-Off Items:</strong> Consider writing off{' '}
              {recommendationCounts.WRITE_OFF} items that have been unsold for
              over 180 days. These items are likely obsolete.
            </p>
          </div>
          <div className="bg-white rounded-lg p-3 border">
            <p className="text-gray-600">
              <strong>Heavy Discount:</strong> Apply 40-50% discounts on{' '}
              {recommendationCounts.HEAVY_DISCOUNT} items to clear aging
              inventory.
            </p>
          </div>
          <div className="bg-white rounded-lg p-3 border">
            <p className="text-gray-600">
              <strong>Standard Discount:</strong> Apply 20-30% discounts on{' '}
              {recommendationCounts.DISCOUNT} items to accelerate sales.
            </p>
          </div>
          <div className="bg-white rounded-lg p-3 border">
            <p className="text-gray-600">
              <strong>Promotion:</strong> Include{' '}
              {recommendationCounts.PROMOTION} items in upcoming promotional
              campaigns.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
