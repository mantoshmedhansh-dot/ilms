"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Package,
  FileText,
  Headphones,
  Award,
  ChevronRight,
  Clock,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  User,
} from "lucide-react";

// Demo customer ID - in production, this comes from authentication
const DEMO_CUSTOMER_ID = "00000000-0000-0000-0000-000000000001";

interface DashboardData {
  customer: {
    name: string;
    loyalty_points: number;
    member_since: string;
  };
  stats: {
    total_orders: number;
    open_tickets: number;
    pending_invoices: number;
  };
  recent_orders: Array<{
    id: string;
    order_number: string;
    order_date: string;
    status: string;
    total_amount: number;
    items_count: number;
  }>;
  open_service_requests: Array<{
    id: string;
    ticket_number: string;
    subject: string;
    status: string;
    created_at: string;
  }>;
  pending_invoices: Array<{
    id: string;
    invoice_number: string;
    amount: number;
    due_date: string;
  }>;
}

export default function CustomerPortalPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `/api/v1/portal/dashboard?customer_id=${DEMO_CUSTOMER_ID}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
            'X-Tenant-ID': localStorage.getItem('tenant_id') || '',
          }
        }
      );
      if (response.ok) {
        const data = await response.json();
        setDashboard(data);
      } else {
        // Use demo data if API not available
        setDashboard(getDemoData());
      }
    } catch (err) {
      setDashboard(getDemoData());
    } finally {
      setLoading(false);
    }
  };

  const getDemoData = (): DashboardData => ({
    customer: {
      name: "John Doe",
      loyalty_points: 2500,
      member_since: "January 2024",
    },
    stats: {
      total_orders: 12,
      open_tickets: 1,
      pending_invoices: 2,
    },
    recent_orders: [
      {
        id: "1",
        order_number: "ORD-2024-0012",
        order_date: "2024-01-10",
        status: "DELIVERED",
        total_amount: 45000,
        items_count: 2,
      },
      {
        id: "2",
        order_number: "ORD-2024-0011",
        order_date: "2024-01-05",
        status: "SHIPPED",
        total_amount: 12500,
        items_count: 1,
      },
    ],
    open_service_requests: [
      {
        id: "1",
        ticket_number: "SR202401001",
        subject: "Installation support needed",
        status: "IN_PROGRESS",
        created_at: "2024-01-08",
      },
    ],
    pending_invoices: [
      {
        id: "1",
        invoice_number: "INV-2024-0045",
        amount: 45000,
        due_date: "2024-01-25",
      },
    ],
  });

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
      DELIVERED: { variant: "default", label: "Delivered" },
      SHIPPED: { variant: "secondary", label: "Shipped" },
      PROCESSING: { variant: "outline", label: "Processing" },
      PENDING: { variant: "outline", label: "Pending" },
      OPEN: { variant: "destructive", label: "Open" },
      IN_PROGRESS: { variant: "secondary", label: "In Progress" },
      CLOSED: { variant: "default", label: "Closed" },
    };
    const config = statusConfig[status] || { variant: "outline" as const, label: status };
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto" />
          <p className="mt-4 text-gray-600">Unable to load dashboard</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="h-10 w-10 bg-blue-600 rounded-full flex items-center justify-center">
                <User className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  Welcome, {dashboard.customer.name}
                </h1>
                <p className="text-sm text-gray-500">
                  Member since {dashboard.customer.member_since}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Award className="h-5 w-5 text-yellow-500" />
              <span className="font-medium">{dashboard.customer.loyalty_points} points</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Total Orders</p>
                  <p className="text-2xl font-bold">{dashboard.stats.total_orders}</p>
                </div>
                <Package className="h-10 w-10 text-blue-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Open Tickets</p>
                  <p className="text-2xl font-bold">{dashboard.stats.open_tickets}</p>
                </div>
                <Headphones className="h-10 w-10 text-orange-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Pending Invoices</p>
                  <p className="text-2xl font-bold">{dashboard.stats.pending_invoices}</p>
                </div>
                <FileText className="h-10 w-10 text-red-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Loyalty Points</p>
                  <p className="text-2xl font-bold">{dashboard.customer.loyalty_points}</p>
                </div>
                <Award className="h-10 w-10 text-yellow-500 opacity-50" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Tabs */}
        <Tabs defaultValue="orders" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="orders" className="flex items-center gap-2">
              <Package className="h-4 w-4" />
              Orders
            </TabsTrigger>
            <TabsTrigger value="invoices" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Invoices
            </TabsTrigger>
            <TabsTrigger value="support" className="flex items-center gap-2">
              <Headphones className="h-4 w-4" />
              Support
            </TabsTrigger>
            <TabsTrigger value="loyalty" className="flex items-center gap-2">
              <Award className="h-4 w-4" />
              Loyalty
            </TabsTrigger>
          </TabsList>

          {/* Orders Tab */}
          <TabsContent value="orders">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Recent Orders</CardTitle>
                    <CardDescription>Track and manage your orders</CardDescription>
                  </div>
                  <Button variant="outline" size="sm">
                    View All
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {dashboard.recent_orders.map((order) => (
                    <div
                      key={order.id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <div className="flex items-center gap-4">
                        <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
                          <Package className="h-6 w-6 text-blue-600" />
                        </div>
                        <div>
                          <p className="font-medium">{order.order_number}</p>
                          <p className="text-sm text-gray-500">
                            {formatDate(order.order_date)} | {order.items_count} items
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="font-medium">{formatCurrency(order.total_amount)}</p>
                          {getStatusBadge(order.status)}
                        </div>
                        <ChevronRight className="h-5 w-5 text-gray-400" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Invoices Tab */}
          <TabsContent value="invoices">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Invoices</CardTitle>
                    <CardDescription>View and download your invoices</CardDescription>
                  </div>
                  <Button variant="outline" size="sm">
                    View All
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {dashboard.pending_invoices.map((invoice) => (
                    <div
                      key={invoice.id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50"
                    >
                      <div className="flex items-center gap-4">
                        <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center">
                          <FileText className="h-6 w-6 text-green-600" />
                        </div>
                        <div>
                          <p className="font-medium">{invoice.invoice_number}</p>
                          <p className="text-sm text-gray-500">
                            Due: {formatDate(invoice.due_date)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="font-medium">{formatCurrency(invoice.amount)}</p>
                          <Badge variant="destructive">Pending</Badge>
                        </div>
                        <Button size="sm">Download</Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Support Tab */}
          <TabsContent value="support">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Support Requests</CardTitle>
                    <CardDescription>View and create support tickets</CardDescription>
                  </div>
                  <Button size="sm">
                    New Request
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {dashboard.open_service_requests.length > 0 ? (
                    dashboard.open_service_requests.map((request) => (
                      <div
                        key={request.id}
                        className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 cursor-pointer"
                      >
                        <div className="flex items-center gap-4">
                          <div className="h-12 w-12 bg-orange-100 rounded-lg flex items-center justify-center">
                            <Headphones className="h-6 w-6 text-orange-600" />
                          </div>
                          <div>
                            <p className="font-medium">{request.ticket_number}</p>
                            <p className="text-sm text-gray-500">{request.subject}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <p className="text-sm text-gray-500">{formatDate(request.created_at)}</p>
                            {getStatusBadge(request.status)}
                          </div>
                          <ChevronRight className="h-5 w-5 text-gray-400" />
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8">
                      <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                      <p className="text-gray-500">No open support requests</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Loyalty Tab */}
          <TabsContent value="loyalty">
            <Card>
              <CardHeader>
                <CardTitle>Loyalty Program</CardTitle>
                <CardDescription>Track your rewards and benefits</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="p-6 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-xl text-white">
                    <Award className="h-12 w-12 mb-4" />
                    <p className="text-4xl font-bold">{dashboard.customer.loyalty_points}</p>
                    <p className="text-lg opacity-90">Available Points</p>
                    <p className="text-sm mt-2 opacity-75">
                      Worth {formatCurrency(dashboard.customer.loyalty_points / 100)}
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">Current Tier</span>
                        <Badge variant="secondary">Silver</Badge>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: "50%" }}
                        ></div>
                      </div>
                      <p className="text-sm text-gray-500 mt-2">
                        500 more points to Gold tier
                      </p>
                    </div>

                    <div className="p-4 border rounded-lg">
                      <h4 className="font-medium mb-2">Your Benefits</h4>
                      <ul className="space-y-2 text-sm text-gray-600">
                        <li className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          5% discount on all orders
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          Free shipping on orders above Rs. 1000
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          Priority customer support
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
