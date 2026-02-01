'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  User,
  Package,
  MapPin,
  LogOut,
  ChevronRight,
  ShoppingBag,
  Clock,
  Loader2,
  Heart,
  Wrench,
  Shield,
  Cpu,
  Gift,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useAuthStore, useIsAuthenticated, useCustomer } from '@/lib/storefront/auth-store';
import { authApi } from '@/lib/storefront/api';
import { formatCurrency } from '@/lib/utils';

interface OrderSummary {
  id: string;
  order_number: string;
  status: string;
  total_amount: number;
  created_at: string;
  items_count: number;
}

export default function AccountPage() {
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();
  const customer = useCustomer();
  const logout = useAuthStore((state) => state.logout);

  const [recentOrders, setRecentOrders] = useState<OrderSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/account/login');
      return;
    }

    // Fetch recent orders
    const fetchOrders = async () => {
      try {
        const data = await authApi.getOrders(1, 3);
        setRecentOrders(data.orders);
      } catch (error) {
        console.error('Failed to fetch orders:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, [isAuthenticated, router]);

  const handleLogout = async () => {
    await authApi.logout();
    logout();
    router.replace('/');
  };

  if (!isAuthenticated || !customer) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'delivered':
        return 'bg-green-100 text-green-800';
      case 'shipped':
        return 'bg-blue-100 text-blue-800';
      case 'processing':
      case 'confirmed':
        return 'bg-yellow-100 text-yellow-800';
      case 'cancelled':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-2xl md:text-3xl font-bold mb-8">My Account</h1>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Profile Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Profile
            </CardTitle>
            <Link href="/account/profile">
              <Button variant="ghost" size="sm">
                Edit
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p className="font-medium">
                {customer.first_name} {customer.last_name || ''}
              </p>
              <p className="text-sm text-muted-foreground">+91 {customer.phone}</p>
              {customer.email && (
                <p className="text-sm text-muted-foreground">{customer.email}</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link href="/account/orders" className="block">
              <Button variant="outline" className="w-full justify-start">
                <Package className="h-4 w-4 mr-2" />
                My Orders
                <ChevronRight className="h-4 w-4 ml-auto" />
              </Button>
            </Link>
            <Link href="/account/addresses" className="block">
              <Button variant="outline" className="w-full justify-start">
                <MapPin className="h-4 w-4 mr-2" />
                Saved Addresses
                <ChevronRight className="h-4 w-4 ml-auto" />
              </Button>
            </Link>
            <Link href="/account/wishlist" className="block">
              <Button variant="outline" className="w-full justify-start">
                <Heart className="h-4 w-4 mr-2" />
                Wishlist
                <ChevronRight className="h-4 w-4 ml-auto" />
              </Button>
            </Link>
            <Link href="/account/devices" className="block">
              <Button variant="outline" className="w-full justify-start">
                <Cpu className="h-4 w-4 mr-2" />
                My Devices
                <ChevronRight className="h-4 w-4 ml-auto" />
              </Button>
            </Link>
            <Link href="/account/services" className="block">
              <Button variant="outline" className="w-full justify-start">
                <Wrench className="h-4 w-4 mr-2" />
                Service Requests
                <ChevronRight className="h-4 w-4 ml-auto" />
              </Button>
            </Link>
            <Link href="/account/amc" className="block">
              <Button variant="outline" className="w-full justify-start">
                <Shield className="h-4 w-4 mr-2" />
                AMC Plans
                <ChevronRight className="h-4 w-4 ml-auto" />
              </Button>
            </Link>
            <Link href="/referral" className="block">
              <Button variant="outline" className="w-full justify-start text-primary border-primary/30 bg-primary/5 hover:bg-primary/10">
                <Gift className="h-4 w-4 mr-2" />
                Refer & Earn ₹500
                <ChevronRight className="h-4 w-4 ml-auto" />
              </Button>
            </Link>
            <Button
              variant="outline"
              className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50"
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Orders */}
      <Card className="mt-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <ShoppingBag className="h-5 w-5" />
            Recent Orders
          </CardTitle>
          <Link href="/account/orders">
            <Button variant="ghost" size="sm">
              View All
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : recentOrders.length === 0 ? (
            <div className="text-center py-8">
              <Package className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">No orders yet</p>
              <Link href="/products">
                <Button className="mt-4">Start Shopping</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {recentOrders.map((order) => (
                <div key={order.id}>
                  <Link
                    href={`/account/orders/${order.order_number}`}
                    className="flex items-center justify-between py-3 hover:bg-muted/50 rounded-lg px-2 -mx-2 transition-colors"
                  >
                    <div>
                      <p className="font-medium">Order #{order.order_number}</p>
                      <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5" />
                          {new Date(order.created_at).toLocaleDateString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </span>
                        <span>{order.items_count} item(s)</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{formatCurrency(order.total_amount)}</p>
                      <span
                        className={`inline-block px-2 py-0.5 text-xs rounded-full mt-1 ${getStatusColor(
                          order.status
                        )}`}
                      >
                        {order.status}
                      </span>
                    </div>
                  </Link>
                  <Separator />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
