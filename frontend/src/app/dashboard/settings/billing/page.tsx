'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';

interface BillingHistory {
  id: string;
  invoice_number: string;
  billing_period_start: string;
  billing_period_end: string;
  amount: number;
  tax_amount: number;
  total_amount: number;
  status: string;
  payment_method: string | null;
  paid_at: string | null;
  created_at: string;
}

interface CurrentBilling {
  monthly_cost: number;
  yearly_cost: number;
  active_modules_count: number;
  billing_cycle: string;
}

export default function BillingPage() {
  const router = useRouter();
  const [currentBilling, setCurrentBilling] = useState<CurrentBilling | null>(null);
  const [billingHistory, setBillingHistory] = useState<BillingHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchBillingData() {
      try {
        // Fetch current billing
        const currentResponse = await fetch('/api/v1/billing/subscription-billing/current', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'X-Tenant-ID': localStorage.getItem('tenant_id') || '',
          }
        });

        if (currentResponse.ok) {
          const currentData = await currentResponse.json();
          setCurrentBilling(currentData);
        }

        // Fetch billing history
        const historyResponse = await fetch('/api/v1/billing/subscription-billing/history', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'X-Tenant-ID': localStorage.getItem('tenant_id') || '',
          }
        });

        if (historyResponse.ok) {
          const historyData = await historyResponse.json();
          setBillingHistory(historyData);
        }
      } catch (error) {
        console.error('Failed to load billing data:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchBillingData();
  }, []);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading billing information...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Billing & Subscription</h1>
        <p className="text-gray-600">
          Manage your subscription billing and view payment history
        </p>
      </div>

      {/* Current Plan */}
      <Card className="mb-6">
        <CardHeader>
          <h2 className="text-xl font-semibold">Current Subscription</h2>
        </CardHeader>
        <CardContent>
          {currentBilling ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-2">Monthly Cost</p>
                <p className="text-3xl font-bold text-blue-600">
                  {formatCurrency(currentBilling.monthly_cost)}
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Yearly: {formatCurrency(currentBilling.yearly_cost)} (Save 20%)
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Billing Cycle: {currentBilling.billing_cycle}
                </p>
              </div>
              <div className="text-right">
                <Button
                  onClick={() => router.push('/dashboard/settings/subscriptions')}
                  className="mb-2"
                >
                  Manage Modules
                </Button>
                <br />
                <Button variant="outline" size="sm">
                  Switch to Yearly (Save 20%)
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">No billing information available</p>
          )}
        </CardContent>
      </Card>

      {/* Billing History */}
      <Card>
        <CardHeader>
          <h2 className="text-xl font-semibold">Billing History</h2>
        </CardHeader>
        <CardContent>
          {billingHistory.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4">Invoice #</th>
                    <th className="text-left py-3 px-4">Billing Period</th>
                    <th className="text-right py-3 px-4">Amount</th>
                    <th className="text-right py-3 px-4">Tax</th>
                    <th className="text-right py-3 px-4">Total</th>
                    <th className="text-center py-3 px-4">Status</th>
                    <th className="text-center py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {billingHistory.map((invoice) => (
                    <tr key={invoice.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4 font-mono text-sm">
                        {invoice.invoice_number}
                      </td>
                      <td className="py-3 px-4 text-sm">
                        {formatDate(invoice.billing_period_start)} - {formatDate(invoice.billing_period_end)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {formatCurrency(invoice.amount)}
                      </td>
                      <td className="py-3 px-4 text-right text-sm text-gray-600">
                        {formatCurrency(invoice.tax_amount)}
                      </td>
                      <td className="py-3 px-4 text-right font-semibold">
                        {formatCurrency(invoice.total_amount)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge
                          className={
                            invoice.status === 'paid'
                              ? 'bg-green-500'
                              : invoice.status === 'pending'
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                          }
                        >
                          {invoice.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Button variant="ghost" size="sm">
                          Download
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-4">No billing history yet</p>
              <p className="text-sm text-gray-400">
                Your subscription invoices will appear here
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Payment Method */}
      <Card className="mt-6">
        <CardHeader>
          <h2 className="text-xl font-semibold">Payment Method</h2>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">No payment method configured</p>
              <p className="text-xs text-gray-400 mt-1">
                Add a payment method to enable automatic renewals
              </p>
            </div>
            <Button variant="outline">Add Payment Method</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
