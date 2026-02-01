'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  UserMinus,
  AlertTriangle,
  Phone,
  Mail,
  Gift,
  ArrowLeft,
  RefreshCw,
  Download,
  Search,
  TrendingDown,
  DollarSign,
  Calendar,
} from 'lucide-react';
import Link from 'next/link';
import { insightsApi, ChurnRiskCustomer } from '@/lib/api';

export default function ChurnRiskPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState<string>('all');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['churn-risk-customers'],
    queryFn: () => insightsApi.getChurnRiskCustomers({ threshold: 0.5, limit: 100 }),
  });

  const getRiskLevel = (score: number): string => {
    if (score >= 0.8) return 'CRITICAL';
    if (score >= 0.7) return 'HIGH';
    if (score >= 0.6) return 'MEDIUM';
    return 'LOW';
  };

  const getRiskColor = (score: number) => {
    const level = getRiskLevel(score);
    switch (level) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'HIGH':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-green-100 text-green-800 border-green-200';
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'URGENT_CALL':
        return <Phone className="h-4 w-4" />;
      case 'PERSONAL_EMAIL':
        return <Mail className="h-4 w-4" />;
      case 'SPECIAL_OFFER':
        return <Gift className="h-4 w-4" />;
      case 'LOYALTY_PROGRAM':
        return <Gift className="h-4 w-4" />;
      default:
        return <Mail className="h-4 w-4" />;
    }
  };

  const getActionLabel = (action: string) => {
    switch (action) {
      case 'URGENT_CALL':
        return 'Urgent Call';
      case 'PERSONAL_EMAIL':
        return 'Personal Email';
      case 'SPECIAL_OFFER':
        return 'Special Offer';
      case 'LOYALTY_PROGRAM':
        return 'Loyalty Program';
      default:
        return action;
    }
  };

  const filteredItems = data?.items?.filter((item: ChurnRiskCustomer) => {
    const matchesSearch =
      item.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.phone?.includes(searchTerm);
    const level = getRiskLevel(item.risk_score);
    const matchesRisk = riskFilter === 'all' || level === riskFilter;
    return matchesSearch && matchesRisk;
  }) || [];

  const riskCounts = {
    CRITICAL: data?.items?.filter((i: ChurnRiskCustomer) => getRiskLevel(i.risk_score) === 'CRITICAL').length || 0,
    HIGH: data?.items?.filter((i: ChurnRiskCustomer) => getRiskLevel(i.risk_score) === 'HIGH').length || 0,
    MEDIUM: data?.items?.filter((i: ChurnRiskCustomer) => getRiskLevel(i.risk_score) === 'MEDIUM').length || 0,
  };

  const totalAtRiskRevenue = filteredItems.reduce(
    (sum: number, item: ChurnRiskCustomer) => sum + (item.total_spent || 0),
    0
  );

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
          <div className="grid grid-cols-3 gap-4 mb-6">
            {[...Array(3)].map((_, i) => (
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
          Failed to load churn risk data. Please try again.
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
              Churn Risk Customers
            </h1>
            <p className="text-gray-500">
              Customers at risk of leaving based on RFM analysis
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
            riskFilter === 'CRITICAL'
              ? 'border-red-500 bg-red-50'
              : 'border-red-200 bg-red-50 hover:border-red-400'
          }`}
          onClick={() =>
            setRiskFilter(riskFilter === 'CRITICAL' ? 'all' : 'CRITICAL')
          }
        >
          <div className="flex items-center justify-between">
            <span className="text-red-600 font-medium">Critical Risk</span>
            <AlertTriangle className="h-5 w-5 text-red-600" />
          </div>
          <p className="text-2xl font-bold text-red-700 mt-2">
            {riskCounts.CRITICAL}
          </p>
          <p className="text-sm text-red-600">Risk score &gt; 80%</p>
        </div>

        <div
          className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
            riskFilter === 'HIGH'
              ? 'border-orange-500 bg-orange-50'
              : 'border-orange-200 bg-orange-50 hover:border-orange-400'
          }`}
          onClick={() =>
            setRiskFilter(riskFilter === 'HIGH' ? 'all' : 'HIGH')
          }
        >
          <div className="flex items-center justify-between">
            <span className="text-orange-600 font-medium">High Risk</span>
            <UserMinus className="h-5 w-5 text-orange-600" />
          </div>
          <p className="text-2xl font-bold text-orange-700 mt-2">
            {riskCounts.HIGH}
          </p>
          <p className="text-sm text-orange-600">Risk score 70-80%</p>
        </div>

        <div
          className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
            riskFilter === 'MEDIUM'
              ? 'border-yellow-500 bg-yellow-50'
              : 'border-yellow-200 bg-yellow-50 hover:border-yellow-400'
          }`}
          onClick={() =>
            setRiskFilter(riskFilter === 'MEDIUM' ? 'all' : 'MEDIUM')
          }
        >
          <div className="flex items-center justify-between">
            <span className="text-yellow-600 font-medium">Medium Risk</span>
            <TrendingDown className="h-5 w-5 text-yellow-600" />
          </div>
          <p className="text-2xl font-bold text-yellow-700 mt-2">
            {riskCounts.MEDIUM}
          </p>
          <p className="text-sm text-yellow-600">Risk score 60-70%</p>
        </div>
      </div>

      {/* Revenue at Risk Banner */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center justify-between">
        <div>
          <p className="text-red-800 font-medium">
            Total Revenue at Risk (Filtered)
          </p>
          <p className="text-sm text-red-600">
            Historical spend from customers at churn risk
          </p>
        </div>
        <p className="text-2xl font-bold text-red-700">
          {new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0,
          }).format(totalAtRiskRevenue)}
        </p>
      </div>

      {/* Search */}
      <div className="flex gap-4 items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by name, email, or phone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
          />
        </div>
        {riskFilter !== 'all' && (
          <button
            onClick={() => setRiskFilter('all')}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Clear filter
          </button>
        )}
        <div className="text-sm text-gray-500">
          Showing {filteredItems.length} of {data?.total || 0} customers
        </div>
      </div>

      {/* Customer Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredItems.map((customer: ChurnRiskCustomer) => (
          <div
            key={customer.customer_id}
            className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-medium text-gray-900">
                  {customer.customer_name}
                </h3>
                <p className="text-sm text-gray-500">{customer.email}</p>
                {customer.phone && (
                  <p className="text-sm text-gray-500">{customer.phone}</p>
                )}
              </div>
              <span
                className={`px-2.5 py-1 rounded-full text-xs font-medium border ${getRiskColor(
                  customer.risk_score
                )}`}
              >
                {Math.round(customer.risk_score * 100)}% Risk
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="h-4 w-4 text-gray-400" />
                <span className="text-gray-600">
                  {customer.days_since_last_order} days ago
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <DollarSign className="h-4 w-4 text-gray-400" />
                <span className="text-gray-600">
                  {new Intl.NumberFormat('en-IN', {
                    style: 'currency',
                    currency: 'INR',
                    maximumFractionDigits: 0,
                  }).format(customer.total_spent)}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t">
              <div className="text-sm text-gray-500">
                {customer.total_orders} orders | Avg{' '}
                {new Intl.NumberFormat('en-IN', {
                  style: 'currency',
                  currency: 'INR',
                  maximumFractionDigits: 0,
                }).format(customer.avg_order_value)}
              </div>
              <button
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  customer.recommended_action === 'URGENT_CALL'
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : customer.recommended_action === 'PERSONAL_EMAIL'
                    ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                    : customer.recommended_action === 'SPECIAL_OFFER'
                    ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                    : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                }`}
              >
                {getActionIcon(customer.recommended_action)}
                {getActionLabel(customer.recommended_action)}
              </button>
            </div>
          </div>
        ))}
        {filteredItems.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-500">
            {searchTerm || riskFilter !== 'all'
              ? 'No customers match your filters'
              : 'No customers at churn risk currently'}
          </div>
        )}
      </div>
    </div>
  );
}
