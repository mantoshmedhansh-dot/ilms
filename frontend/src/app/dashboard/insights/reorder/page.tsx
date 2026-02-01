'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Package,
  AlertTriangle,
  Clock,
  TrendingDown,
  ArrowLeft,
  RefreshCw,
  Download,
  Filter,
  Search,
} from 'lucide-react';
import Link from 'next/link';
import { insightsApi, ReorderRecommendation } from '@/lib/api';

export default function ReorderSuggestionsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [urgencyFilter, setUrgencyFilter] = useState<string>('all');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['reorder-recommendations'],
    queryFn: () => insightsApi.getReorderRecommendations({ limit: 100 }),
  });

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'HIGH':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'LOW':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getUrgencyIcon = (urgency: string) => {
    switch (urgency) {
      case 'CRITICAL':
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case 'HIGH':
        return <Clock className="h-4 w-4 text-orange-600" />;
      case 'MEDIUM':
        return <TrendingDown className="h-4 w-4 text-yellow-600" />;
      default:
        return <Package className="h-4 w-4 text-green-600" />;
    }
  };

  const filteredItems = data?.items?.filter((item: ReorderRecommendation) => {
    const matchesSearch =
      item.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.sku.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesUrgency =
      urgencyFilter === 'all' || item.urgency === urgencyFilter;
    return matchesSearch && matchesUrgency;
  }) || [];

  const urgencyCounts = {
    CRITICAL: data?.items?.filter((i: ReorderRecommendation) => i.urgency === 'CRITICAL').length || 0,
    HIGH: data?.items?.filter((i: ReorderRecommendation) => i.urgency === 'HIGH').length || 0,
    MEDIUM: data?.items?.filter((i: ReorderRecommendation) => i.urgency === 'MEDIUM').length || 0,
    LOW: data?.items?.filter((i: ReorderRecommendation) => i.urgency === 'LOW').length || 0,
  };

  const totalEstimatedCost = filteredItems.reduce(
    (sum: number, item: ReorderRecommendation) => sum + (item.estimated_cost || 0),
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
          Failed to load reorder recommendations. Please try again.
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
              Reorder Suggestions
            </h1>
            <p className="text-gray-500">
              AI-powered recommendations based on sales velocity and stock levels
            </p>
          </div>
        </div>
        <div className="flex gap-2">
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
            urgencyFilter === 'CRITICAL'
              ? 'border-red-500 bg-red-50'
              : 'border-red-200 bg-red-50 hover:border-red-400'
          }`}
          onClick={() =>
            setUrgencyFilter(urgencyFilter === 'CRITICAL' ? 'all' : 'CRITICAL')
          }
        >
          <div className="flex items-center justify-between">
            <span className="text-red-600 font-medium">Critical</span>
            <AlertTriangle className="h-5 w-5 text-red-600" />
          </div>
          <p className="text-2xl font-bold text-red-700 mt-2">
            {urgencyCounts.CRITICAL}
          </p>
          <p className="text-sm text-red-600">Stockout in &lt;3 days</p>
        </div>

        <div
          className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
            urgencyFilter === 'HIGH'
              ? 'border-orange-500 bg-orange-50'
              : 'border-orange-200 bg-orange-50 hover:border-orange-400'
          }`}
          onClick={() =>
            setUrgencyFilter(urgencyFilter === 'HIGH' ? 'all' : 'HIGH')
          }
        >
          <div className="flex items-center justify-between">
            <span className="text-orange-600 font-medium">High</span>
            <Clock className="h-5 w-5 text-orange-600" />
          </div>
          <p className="text-2xl font-bold text-orange-700 mt-2">
            {urgencyCounts.HIGH}
          </p>
          <p className="text-sm text-orange-600">Stockout in 3-7 days</p>
        </div>

        <div
          className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
            urgencyFilter === 'MEDIUM'
              ? 'border-yellow-500 bg-yellow-50'
              : 'border-yellow-200 bg-yellow-50 hover:border-yellow-400'
          }`}
          onClick={() =>
            setUrgencyFilter(urgencyFilter === 'MEDIUM' ? 'all' : 'MEDIUM')
          }
        >
          <div className="flex items-center justify-between">
            <span className="text-yellow-600 font-medium">Medium</span>
            <TrendingDown className="h-5 w-5 text-yellow-600" />
          </div>
          <p className="text-2xl font-bold text-yellow-700 mt-2">
            {urgencyCounts.MEDIUM}
          </p>
          <p className="text-sm text-yellow-600">Stockout in 7-14 days</p>
        </div>

        <div
          className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
            urgencyFilter === 'LOW'
              ? 'border-green-500 bg-green-50'
              : 'border-green-200 bg-green-50 hover:border-green-400'
          }`}
          onClick={() =>
            setUrgencyFilter(urgencyFilter === 'LOW' ? 'all' : 'LOW')
          }
        >
          <div className="flex items-center justify-between">
            <span className="text-green-600 font-medium">Low</span>
            <Package className="h-5 w-5 text-green-600" />
          </div>
          <p className="text-2xl font-bold text-green-700 mt-2">
            {urgencyCounts.LOW}
          </p>
          <p className="text-sm text-green-600">Plan for reorder</p>
        </div>
      </div>

      {/* Filters */}
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
        {urgencyFilter !== 'all' && (
          <button
            onClick={() => setUrgencyFilter('all')}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            <Filter className="h-4 w-4" />
            Clear filter
          </button>
        )}
        <div className="text-sm text-gray-500">
          Showing {filteredItems.length} of {data?.total || 0} items
        </div>
      </div>

      {/* Estimated Cost Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
        <div>
          <p className="text-blue-800 font-medium">
            Estimated Reorder Cost (Filtered)
          </p>
          <p className="text-sm text-blue-600">
            Based on recommended quantities and vendor pricing
          </p>
        </div>
        <p className="text-2xl font-bold text-blue-700">
          {new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0,
          }).format(totalEstimatedCost)}
        </p>
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
                Current Stock
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Daily Velocity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Days Until Stockout
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Recommended Qty
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Est. Cost
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Urgency
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredItems.map((item: ReorderRecommendation) => (
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
                  <span
                    className={`font-medium ${
                      item.current_stock <= item.reorder_level
                        ? 'text-red-600'
                        : 'text-gray-900'
                    }`}
                  >
                    {item.current_stock}
                  </span>
                  <span className="text-gray-400 text-sm">
                    {' '}
                    / {item.reorder_level} min
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-900">
                  {item.daily_velocity.toFixed(1)}/day
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`font-medium ${
                      item.days_until_stockout <= 3
                        ? 'text-red-600'
                        : item.days_until_stockout <= 7
                        ? 'text-orange-600'
                        : 'text-gray-900'
                    }`}
                  >
                    {item.days_until_stockout} days
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="font-bold text-primary">
                    {item.recommended_qty} units
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-900">
                  {new Intl.NumberFormat('en-IN', {
                    style: 'currency',
                    currency: 'INR',
                    maximumFractionDigits: 0,
                  }).format(item.estimated_cost || 0)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${getUrgencyColor(
                      item.urgency
                    )}`}
                  >
                    {getUrgencyIcon(item.urgency)}
                    {item.urgency}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <button className="text-primary hover:text-primary/80 font-medium text-sm">
                    Create PO
                  </button>
                </td>
              </tr>
            ))}
            {filteredItems.length === 0 && (
              <tr>
                <td
                  colSpan={8}
                  className="px-6 py-12 text-center text-gray-500"
                >
                  {searchTerm || urgencyFilter !== 'all'
                    ? 'No items match your filters'
                    : 'No reorder recommendations at this time'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
