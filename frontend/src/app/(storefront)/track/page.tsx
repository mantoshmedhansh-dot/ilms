'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Search,
  Package,
  Truck,
  MapPin,
  ArrowRight,
  Phone,
  HelpCircle,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';

export default function TrackOrderPage() {
  const router = useRouter();
  const [orderNumber, setOrderNumber] = useState('');
  const [awbNumber, setAwbNumber] = useState('');
  const [loading, setLoading] = useState(false);

  const handleOrderTrack = (e: React.FormEvent) => {
    e.preventDefault();

    if (!orderNumber.trim()) {
      toast.error('Please enter your order number');
      return;
    }

    // Navigate to order tracking page
    router.push(`/track/order/${orderNumber.toUpperCase().trim()}`);
  };

  const handleAwbTrack = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!awbNumber.trim()) {
      toast.error('Please enter the AWB/tracking number');
      return;
    }

    setLoading(true);
    // Navigate to AWB tracking page
    router.push(`/track/${awbNumber.trim()}`);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Hero Section */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-full mb-4">
          <Truck className="h-8 w-8 text-primary" />
        </div>
        <h1 className="text-3xl md:text-4xl font-bold mb-2">Track Your Order</h1>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Enter your order number or AWB tracking number to see the real-time status of your shipment
        </p>
      </div>

      {/* Tracking Form */}
      <Card className="mb-8">
        <CardContent className="pt-6">
          <Tabs defaultValue="order" className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="order" className="gap-2">
                <Package className="h-4 w-4" />
                Track by Order
              </TabsTrigger>
              <TabsTrigger value="awb" className="gap-2">
                <Truck className="h-4 w-4" />
                Track by AWB
              </TabsTrigger>
            </TabsList>

            <TabsContent value="order">
              <form onSubmit={handleOrderTrack} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="orderNumber">Order Number</Label>
                  <div className="flex gap-2">
                    <Input
                      id="orderNumber"
                      type="text"
                      value={orderNumber}
                      onChange={(e) => setOrderNumber(e.target.value.toUpperCase())}
                      placeholder="e.g., ORD-20260127-0001"
                      className="flex-1 text-lg"
                      autoComplete="off"
                    />
                    <Button type="submit" size="lg" className="px-8">
                      <Search className="h-4 w-4 mr-2" />
                      Track
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    You can find your order number in your order confirmation email or SMS
                  </p>
                </div>
              </form>
            </TabsContent>

            <TabsContent value="awb">
              <form onSubmit={handleAwbTrack} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="awbNumber">AWB / Tracking Number</Label>
                  <div className="flex gap-2">
                    <Input
                      id="awbNumber"
                      type="text"
                      value={awbNumber}
                      onChange={(e) => setAwbNumber(e.target.value)}
                      placeholder="e.g., 12345678901234"
                      className="flex-1 text-lg"
                      autoComplete="off"
                    />
                    <Button type="submit" size="lg" className="px-8" disabled={loading}>
                      {loading ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Search className="h-4 w-4 mr-2" />
                      )}
                      Track
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    The AWB number is provided by the courier and sent via SMS after shipping
                  </p>
                </div>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* How It Works */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4 text-center">Order Journey</h2>
        <div className="grid md:grid-cols-4 gap-4">
          {[
            { icon: Package, title: 'Order Placed', desc: 'We receive your order' },
            { icon: MapPin, title: 'Processing', desc: 'Picked & packed at warehouse' },
            { icon: Truck, title: 'In Transit', desc: 'On the way to you' },
            { icon: Package, title: 'Delivered', desc: 'At your doorstep' },
          ].map((step, idx) => (
            <div key={idx} className="relative">
              <Card className="h-full">
                <CardContent className="pt-6 text-center">
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                    <step.icon className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="font-medium mb-1">{step.title}</h3>
                  <p className="text-sm text-muted-foreground">{step.desc}</p>
                </CardContent>
              </Card>
              {idx < 3 && (
                <ArrowRight className="hidden md:block absolute top-1/2 -right-4 transform -translate-y-1/2 text-muted-foreground/50 h-6 w-6" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Help Section */}
      <Card>
        <CardContent className="py-6">
          <div className="flex flex-col md:flex-row items-center gap-6">
            <div className="flex items-center gap-4 flex-1">
              <div className="p-3 bg-primary/10 rounded-full">
                <HelpCircle className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold">Need Help?</h3>
                <p className="text-sm text-muted-foreground">
                  Can't find your order? Contact our support team
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" asChild>
                <a href="tel:+919311939076">
                  <Phone className="h-4 w-4 mr-2" />
                  Call Us
                </a>
              </Button>
              <Button variant="outline" asChild>
                <Link href="/contact">
                  Contact Support
                </Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Links for Logged In Users */}
      <div className="mt-8 text-center">
        <p className="text-sm text-muted-foreground">
          Have an account?{' '}
          <Link href="/account/orders" className="text-primary hover:underline">
            View all your orders
          </Link>
        </p>
      </div>
    </div>
  );
}
