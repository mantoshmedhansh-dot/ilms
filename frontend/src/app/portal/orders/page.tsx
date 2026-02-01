"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Package,
  Search,
  ArrowLeft,
  ChevronRight,
  Truck,
  CheckCircle,
  Clock,
  XCircle,
} from "lucide-react";

const DEMO_CUSTOMER_ID = "00000000-0000-0000-0000-000000000001";

interface Order {
  id: string;
  order_number: string;
  order_date: string;
  status: string;
  total_amount: number;
  items_count: number;
  payment_status: string;
  delivery_date: string | null;
}

export default function CustomerOrdersPage() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    fetchOrders();
  }, [statusFilter]);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const statusParam = statusFilter !== "all" ? `&status=${statusFilter}` : "";
      const response = await fetch(
        `/api/v1/portal/orders?customer_id=${DEMO_CUSTOMER_ID}${statusParam}`
      );
      if (response.ok) {
        const data = await response.json();
        setOrders(data.orders);
      } else {
        setOrders(getDemoOrders());
      }
    } catch {
      setOrders(getDemoOrders());
    } finally {
      setLoading(false);
    }
  };

  const getDemoOrders = (): Order[] => [
    {
      id: "1",
      order_number: "ORD-2024-0012",
      order_date: "2024-01-10T10:30:00",
      status: "DELIVERED",
      total_amount: 45000,
      items_count: 2,
      payment_status: "PAID",
      delivery_date: "2024-01-15",
    },
    {
      id: "2",
      order_number: "ORD-2024-0011",
      order_date: "2024-01-05T14:20:00",
      status: "SHIPPED",
      total_amount: 12500,
      items_count: 1,
      payment_status: "PAID",
      delivery_date: null,
    },
    {
      id: "3",
      order_number: "ORD-2024-0010",
      order_date: "2024-01-02T09:15:00",
      status: "PROCESSING",
      total_amount: 8500,
      items_count: 3,
      payment_status: "PENDING",
      delivery_date: null,
    },
    {
      id: "4",
      order_number: "ORD-2023-0095",
      order_date: "2023-12-20T16:45:00",
      status: "DELIVERED",
      total_amount: 32000,
      items_count: 1,
      payment_status: "PAID",
      delivery_date: "2023-12-28",
    },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "DELIVERED":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "SHIPPED":
        return <Truck className="h-5 w-5 text-blue-500" />;
      case "PROCESSING":
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case "CANCELLED":
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Package className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const config: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
      DELIVERED: { variant: "default", label: "Delivered" },
      SHIPPED: { variant: "secondary", label: "Shipped" },
      PROCESSING: { variant: "outline", label: "Processing" },
      PENDING: { variant: "outline", label: "Pending" },
      CANCELLED: { variant: "destructive", label: "Cancelled" },
    };
    const c = config[status] || { variant: "outline" as const, label: status };
    return <Badge variant={c.variant}>{c.label}</Badge>;
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

  const filteredOrders = orders.filter((order) =>
    order.order_number.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => router.push("/portal")}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">My Orders</h1>
              <p className="text-sm text-gray-500">View and track your orders</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card>
          <CardHeader>
            <div className="flex flex-col md:flex-row gap-4 justify-between">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search by order number..."
                  className="pl-10"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Orders</SelectItem>
                  <SelectItem value="PENDING">Pending</SelectItem>
                  <SelectItem value="PROCESSING">Processing</SelectItem>
                  <SelectItem value="SHIPPED">Shipped</SelectItem>
                  <SelectItem value="DELIVERED">Delivered</SelectItem>
                  <SelectItem value="CANCELLED">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-gray-500">Loading orders...</p>
              </div>
            ) : filteredOrders.length === 0 ? (
              <div className="text-center py-8">
                <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">No orders found</p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredOrders.map((order) => (
                  <div
                    key={order.id}
                    className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => router.push(`/portal/orders/${order.id}`)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        {getStatusIcon(order.status)}
                        <div>
                          <p className="font-medium text-gray-900">{order.order_number}</p>
                          <p className="text-sm text-gray-500">
                            Ordered on {formatDate(order.order_date)} | {order.items_count} item(s)
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="font-semibold">{formatCurrency(order.total_amount)}</p>
                          {getStatusBadge(order.status)}
                        </div>
                        <ChevronRight className="h-5 w-5 text-gray-400" />
                      </div>
                    </div>
                    {order.status === "DELIVERED" && order.delivery_date && (
                      <p className="mt-2 text-sm text-green-600 ml-9">
                        Delivered on {formatDate(order.delivery_date)}
                      </p>
                    )}
                    {order.status === "SHIPPED" && (
                      <p className="mt-2 text-sm text-blue-600 ml-9">
                        Your order is on the way
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
