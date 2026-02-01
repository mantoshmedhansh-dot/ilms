'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Module {
  code: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  price_monthly: number;
  price_yearly: number;
  isEnabled: boolean;
  is_base_module: boolean;
}

interface Subscription {
  module_code: string;
  module_name: string;
  status: string;
}

export default function SubscriptionsPage() {
  const [modules, setModules] = useState<Module[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        // Fetch current subscriptions
        const subsResponse = await fetch('/api/v1/modules/subscriptions', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'X-Tenant-ID': localStorage.getItem('tenant_id') || '',
          }
        });

        let currentSubscriptions: Subscription[] = [];
        if (subsResponse.ok) {
          const subsData = await subsResponse.json();
          currentSubscriptions = subsData.subscriptions || [];
          setSubscriptions(currentSubscriptions);
        }

        // Fetch available modules (all modules from public.modules)
        const modulesResponse = await fetch('/api/v1/modules', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          }
        });

        if (modulesResponse.ok) {
          const modulesData = await modulesResponse.json();

          // Mark which modules are enabled based on subscriptions
          const modulesWithStatus = modulesData.map((module: Module) => ({
            ...module,
            isEnabled: currentSubscriptions.some(
              (sub: Subscription) => sub.module_code === module.code && sub.status === 'active'
            ) || false,
          }));

          setModules(modulesWithStatus);
        }
      } catch (error) {
        console.error('Failed to load modules:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const handleToggleModule = async (moduleCode: string, isCurrentlyEnabled: boolean) => {
    try {
      const endpoint = isCurrentlyEnabled
        ? '/api/v1/modules/unsubscribe'
        : '/api/v1/modules/subscribe';

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'X-Tenant-ID': localStorage.getItem('tenant_id') || '',
        },
        body: JSON.stringify({
          module_codes: [moduleCode],
          billing_cycle: 'monthly'
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to toggle module');
      }

      // Refresh the page to show updated subscriptions
      window.location.reload();
    } catch (error) {
      alert('Failed to toggle module. Please try again.');
      console.error(error);
    }
  };

  const groupedModules = modules.reduce((acc, module) => {
    if (!acc[module.category]) acc[module.category] = [];
    acc[module.category].push(module);
    return acc;
  }, {} as Record<string, Module[]>);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading subscriptions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Your Subscriptions</h1>
        <p className="text-gray-600">
          Manage your module subscriptions. Enable or disable modules based on your business needs.
        </p>
      </div>

      {Object.entries(groupedModules).map(([category, categoryModules]) => (
        <div key={category} className="mb-8">
          <h2 className="text-xl font-semibold mb-4 capitalize">{category}</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {categoryModules.map((module) => (
              <Card key={module.code} className={module.isEnabled ? 'border-blue-500 border-2' : ''}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{module.icon}</span>
                      <h3 className="font-semibold">{module.name}</h3>
                    </div>
                    {module.isEnabled && (
                      <Badge className="bg-green-500">Active</Badge>
                    )}
                  </div>
                </CardHeader>

                <CardContent>
                  <p className="text-sm text-gray-600 mb-4">{module.description}</p>

                  <div className="mb-4">
                    <div className="text-lg font-bold">
                      ₹{module.price_monthly.toLocaleString()}/month
                    </div>
                    <div className="text-sm text-gray-500">
                      ₹{module.price_yearly.toLocaleString()}/year (save 20%)
                    </div>
                  </div>

                  {!module.is_base_module ? (
                    <Button
                      onClick={() => handleToggleModule(module.code, module.isEnabled)}
                      variant={module.isEnabled ? 'outline' : 'default'}
                      className="w-full"
                    >
                      {module.isEnabled ? 'Disable Module' : 'Enable Module'}
                    </Button>
                  ) : (
                    <div className="text-sm text-gray-500 text-center py-2">
                      Base module (always enabled)
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
