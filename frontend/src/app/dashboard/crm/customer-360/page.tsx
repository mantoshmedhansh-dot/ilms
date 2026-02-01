'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Search, User, Phone, Mail, MapPin, Calendar, Package,
  ShoppingCart, Wrench, Shield, CreditCard, Clock, Star,
  TrendingUp, AlertCircle, CheckCircle, XCircle, FileText
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatDate, formatCurrency } from '@/lib/utils';

interface Customer360Data {
  customer: {
    id: string;
    name?: string;
    full_name?: string;
    email?: string;
    phone: string;
    alternate_phone?: string;
    gst_number?: string;
    customer_type: string;
    tier?: 'REGULAR' | 'SILVER' | 'GOLD' | 'PLATINUM';
    total_orders?: number;
    total_spent?: number;
    loyalty_points?: number;
    created_at: string;
  };
  stats?: {
    total_orders: number;
    total_order_value: number;
    delivered_orders: number;
    pending_orders: number;
    total_installations: number;
    completed_installations: number;
    total_service_requests: number;
    open_service_requests: number;
    total_calls: number;
    active_amc_contracts: number;
    average_rating?: number;
    customer_since_days: number;
  };
  addresses: Array<{
    id: string;
    type: 'HOME' | 'OFFICE' | 'OTHER';
    address_line1: string;
    address_line2?: string;
    city: string;
    state: string;
    pincode: string;
    is_default: boolean;
  }>;
  orders: Array<{
    id: string;
    order_number: string;
    status: string;
    total_amount: number;
    created_at: string;
    items_count: number;
  }>;
  installations: Array<{
    id: string;
    serial_number: string;
    product_name: string;
    installation_date: string;
    warranty_end_date: string;
    status: string;
  }>;
  service_requests: Array<{
    id: string;
    request_number: string;
    type: string;
    status: string;
    priority: string;
    created_at: string;
  }>;
  warranty_claims: Array<{
    id: string;
    claim_number: string;
    product_name: string;
    status: string;
    created_at: string;
  }>;
  invoices: Array<{
    id: string;
    invoice_number: string;
    total_amount: number;
    status: string;
    created_at: string;
  }>;
  interactions: Array<{
    id: string;
    type: 'CALL' | 'EMAIL' | 'CHAT' | 'VISIT';
    subject: string;
    outcome?: string;
    created_at: string;
    agent_name?: string;
  }>;
}

const customer360Api = {
  search: async (query: string) => {
    try {
      // Backend expects /customers?search=query, not /customers/search?q=query
      const { data } = await apiClient.get('/customers', { params: { search: query } });
      return data.items || [];  // Backend returns { items: [...], total: ... }
    } catch {
      return [];
    }
  },
  get360: async (customerId: string): Promise<Customer360Data | null> => {
    try {
      const { data } = await apiClient.get(`/customers/${customerId}/360`);
      return data;
    } catch {
      return null;
    }
  },
};

const tierColors: Record<string, string> = {
  REGULAR: 'bg-gray-100 text-gray-800',
  SILVER: 'bg-slate-200 text-slate-800',
  GOLD: 'bg-yellow-100 text-yellow-800',
  PLATINUM: 'bg-purple-100 text-purple-800',
};

export default function Customer360Page() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [showSearchResults, setShowSearchResults] = useState(false);

  const { data: searchResults = [], isLoading: searching } = useQuery({
    queryKey: ['customer-search', searchQuery],
    queryFn: () => customer360Api.search(searchQuery),
    enabled: searchQuery.length >= 3,
  });

  const { data: customer360, isLoading: loadingCustomer } = useQuery({
    queryKey: ['customer-360', selectedCustomerId],
    queryFn: () => customer360Api.get360(selectedCustomerId!),
    enabled: !!selectedCustomerId,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setShowSearchResults(true);
  };

  const handleSelectCustomer = (customerId: string) => {
    setSelectedCustomerId(customerId);
    setShowSearchResults(false);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Customer 360"
        description="Complete customer view with orders, service history, and interactions"
      />

      {/* Search Section */}
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSearch} className="flex gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name, phone, or email..."
                className="pl-10"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  if (e.target.value.length >= 3) setShowSearchResults(true);
                }}
              />
              {/* Search Results Dropdown */}
              {showSearchResults && searchQuery.length >= 3 && (
                <div className="absolute z-10 w-full mt-1 bg-background border rounded-md shadow-lg max-h-64 overflow-auto">
                  {searching ? (
                    <div className="p-4 text-center text-muted-foreground">Searching...</div>
                  ) : searchResults.length === 0 ? (
                    <div className="p-4 text-center text-muted-foreground">No customers found</div>
                  ) : (
                    searchResults.map((customer: any) => (
                      <div
                        key={customer.id}
                        className="p-3 hover:bg-muted cursor-pointer border-b last:border-0"
                        onClick={() => handleSelectCustomer(customer.id)}
                      >
                        <div className="font-medium">{customer.name || customer.full_name || 'Unknown'}</div>
                        <div className="text-sm text-muted-foreground">
                          {customer.phone} {customer.email && `| ${customer.email}`}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
            <Button type="submit">
              <Search className="mr-2 h-4 w-4" />
              Search
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Customer 360 View */}
      {loadingCustomer ? (
        <div className="grid gap-6 md:grid-cols-3">
          <Skeleton className="h-64" />
          <Skeleton className="h-64 md:col-span-2" />
        </div>
      ) : customer360?.customer ? (
        <div className="space-y-6">
          {/* Customer Profile Card */}
          <div className="grid gap-6 md:grid-cols-3">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                    <User className="h-8 w-8 text-primary" />
                  </div>
                  <div>
                    <CardTitle>{customer360.customer.name || customer360.customer.full_name}</CardTitle>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge className={tierColors[customer360.customer.tier || 'REGULAR']}>
                        {customer360.customer.tier || 'REGULAR'}
                      </Badge>
                      <Badge variant="outline">
                        {customer360.customer.customer_type}
                      </Badge>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  {customer360.customer.phone}
                </div>
                {customer360.customer.email && (
                  <div className="flex items-center gap-2 text-sm">
                    <Mail className="h-4 w-4 text-muted-foreground" />
                    {customer360.customer.email}
                  </div>
                )}
                <div className="flex items-center gap-2 text-sm">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  Customer since {formatDate(customer360.customer.created_at)}
                </div>
                {customer360.customer.gst_number && (
                  <div className="flex items-center gap-2 text-sm">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    GST: {customer360.customer.gst_number}
                  </div>
                )}
                <Separator className="my-4" />
                <div className="flex items-center gap-2 text-sm">
                  <Star className="h-4 w-4 text-yellow-500" />
                  {(customer360.customer.loyalty_points || 0).toLocaleString()} loyalty points
                </div>
              </CardContent>
            </Card>

            {/* Summary Stats */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Customer Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-muted/50 rounded-lg text-center">
                    <ShoppingCart className="h-6 w-6 mx-auto mb-2 text-blue-600" />
                    <div className="text-2xl font-bold">{customer360.stats?.total_orders || 0}</div>
                    <div className="text-xs text-muted-foreground">Total Orders</div>
                  </div>
                  <div className="p-4 bg-muted/50 rounded-lg text-center">
                    <TrendingUp className="h-6 w-6 mx-auto mb-2 text-green-600" />
                    <div className="text-2xl font-bold">{formatCurrency(customer360.stats?.total_order_value || 0)}</div>
                    <div className="text-xs text-muted-foreground">Total Spent</div>
                  </div>
                  <div className="p-4 bg-muted/50 rounded-lg text-center">
                    <Package className="h-6 w-6 mx-auto mb-2 text-purple-600" />
                    <div className="text-2xl font-bold">{customer360.installations?.length || 0}</div>
                    <div className="text-xs text-muted-foreground">Installations</div>
                  </div>
                  <div className="p-4 bg-muted/50 rounded-lg text-center">
                    <Wrench className="h-6 w-6 mx-auto mb-2 text-orange-600" />
                    <div className="text-2xl font-bold">{customer360.service_requests?.length || 0}</div>
                    <div className="text-xs text-muted-foreground">Service Requests</div>
                  </div>
                </div>

                {/* Addresses */}
                <div className="mt-6">
                  <h4 className="font-medium mb-3 flex items-center gap-2">
                    <MapPin className="h-4 w-4" /> Saved Addresses
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {(customer360.addresses || []).map((address) => (
                      <div key={address.id} className="p-3 border rounded-lg text-sm">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline" className="text-xs">{address.type}</Badge>
                          {address.is_default && <Badge className="text-xs">Default</Badge>}
                        </div>
                        <div>{address.address_line1}</div>
                        {address.address_line2 && <div>{address.address_line2}</div>}
                        <div>{address.city}, {address.state} - {address.pincode}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Tabs */}
          <Card>
            <Tabs defaultValue="orders" className="w-full">
              <CardHeader>
                <TabsList>
                  <TabsTrigger value="orders">Orders ({customer360.orders?.length || 0})</TabsTrigger>
                  <TabsTrigger value="installations">Installations ({customer360.installations?.length || 0})</TabsTrigger>
                  <TabsTrigger value="service">Service ({customer360.service_requests?.length || 0})</TabsTrigger>
                  <TabsTrigger value="warranty">Warranty ({customer360.warranty_claims?.length || 0})</TabsTrigger>
                  <TabsTrigger value="invoices">Invoices ({customer360.invoices?.length || 0})</TabsTrigger>
                  <TabsTrigger value="interactions">Interactions ({customer360.interactions?.length || 0})</TabsTrigger>
                </TabsList>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  {/* Orders Tab */}
                  <TabsContent value="orders" className="space-y-3">
                    {!customer360.orders?.length ? (
                      <div className="text-center py-8 text-muted-foreground">No orders yet</div>
                    ) : (
                      customer360.orders.map((order) => (
                        <div key={order.id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div>
                            <div className="font-medium">{order.order_number}</div>
                            <div className="text-sm text-muted-foreground">
                              {order.items_count} items | {formatDate(order.created_at)}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium">{formatCurrency(order.total_amount)}</div>
                            <StatusBadge status={order.status} />
                          </div>
                        </div>
                      ))
                    )}
                  </TabsContent>

                  {/* Installations Tab */}
                  <TabsContent value="installations" className="space-y-3">
                    {!customer360.installations?.length ? (
                      <div className="text-center py-8 text-muted-foreground">No installations</div>
                    ) : (
                      customer360.installations.map((installation) => (
                        <div key={installation.id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div>
                            <div className="font-medium">{installation.product_name}</div>
                            <div className="text-sm text-muted-foreground font-mono">
                              S/N: {installation.serial_number}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Installed: {formatDate(installation.installation_date)}
                            </div>
                          </div>
                          <div className="text-right">
                            <StatusBadge status={installation.status} />
                            <div className="text-xs text-muted-foreground mt-1">
                              Warranty until {formatDate(installation.warranty_end_date)}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </TabsContent>

                  {/* Service Requests Tab */}
                  <TabsContent value="service" className="space-y-3">
                    {!customer360.service_requests?.length ? (
                      <div className="text-center py-8 text-muted-foreground">No service requests</div>
                    ) : (
                      customer360.service_requests.map((sr) => (
                        <div key={sr.id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div>
                            <div className="font-medium">{sr.request_number}</div>
                            <div className="text-sm text-muted-foreground">
                              {sr.type} | {formatDate(sr.created_at)}
                            </div>
                          </div>
                          <div className="text-right">
                            <StatusBadge status={sr.status} />
                            <Badge variant="outline" className="ml-2">{sr.priority}</Badge>
                          </div>
                        </div>
                      ))
                    )}
                  </TabsContent>

                  {/* Warranty Claims Tab */}
                  <TabsContent value="warranty" className="space-y-3">
                    {!customer360.warranty_claims?.length ? (
                      <div className="text-center py-8 text-muted-foreground">No warranty claims</div>
                    ) : (
                      customer360.warranty_claims.map((claim) => (
                        <div key={claim.id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div>
                            <div className="font-medium">{claim.claim_number}</div>
                            <div className="text-sm text-muted-foreground">
                              {claim.product_name} | {formatDate(claim.created_at)}
                            </div>
                          </div>
                          <StatusBadge status={claim.status} />
                        </div>
                      ))
                    )}
                  </TabsContent>

                  {/* Invoices Tab */}
                  <TabsContent value="invoices" className="space-y-3">
                    {!customer360.invoices?.length ? (
                      <div className="text-center py-8 text-muted-foreground">No invoices</div>
                    ) : (
                      customer360.invoices.map((invoice) => (
                        <div key={invoice.id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div>
                            <div className="font-medium">{invoice.invoice_number}</div>
                            <div className="text-sm text-muted-foreground">
                              {formatDate(invoice.created_at)}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium">{formatCurrency(invoice.total_amount)}</div>
                            <StatusBadge status={invoice.status} />
                          </div>
                        </div>
                      ))
                    )}
                  </TabsContent>

                  {/* Interactions Tab */}
                  <TabsContent value="interactions" className="space-y-3">
                    {!customer360.interactions?.length ? (
                      <div className="text-center py-8 text-muted-foreground">No interactions recorded</div>
                    ) : (
                      customer360.interactions.map((interaction) => (
                        <div key={interaction.id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline">{interaction.type}</Badge>
                              <span className="font-medium">{interaction.subject}</span>
                            </div>
                            <div className="text-sm text-muted-foreground">
                              {interaction.agent_name && `By ${interaction.agent_name} | `}
                              {formatDate(interaction.created_at)}
                            </div>
                          </div>
                          {interaction.outcome && (
                            <Badge variant="secondary">{interaction.outcome}</Badge>
                          )}
                        </div>
                      ))
                    )}
                  </TabsContent>
                </ScrollArea>
              </CardContent>
            </Tabs>
          </Card>
        </div>
      ) : (
        <Card>
          <CardContent className="py-16 text-center">
            <User className="h-16 w-16 mx-auto mb-4 text-muted-foreground/50" />
            <h3 className="text-lg font-medium mb-2">Search for a Customer</h3>
            <p className="text-muted-foreground max-w-md mx-auto">
              Enter a customer name, phone number, or email to view their complete profile including orders, service history, and interactions.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
