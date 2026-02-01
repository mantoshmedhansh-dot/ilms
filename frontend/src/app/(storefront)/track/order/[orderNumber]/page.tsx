'use client';

import { useState, use } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Package,
  Loader2,
  MapPin,
  CreditCard,
  Truck,
  CheckCircle,
  XCircle,
  Circle,
  Copy,
  ExternalLink,
  Clock,
  Receipt,
  Undo2,
  Phone,
  Search,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from 'sonner';
import { orderTrackingApi, OrderTrackingResponse, TimelineEvent } from '@/lib/storefront/api';
import { formatCurrency } from '@/lib/utils';

const eventTypeIcons: Record<string, React.ReactNode> = {
  ORDER: <Package className="h-4 w-4" />,
  PAYMENT: <CreditCard className="h-4 w-4" />,
  SHIPMENT: <Truck className="h-4 w-4" />,
  DELIVERY: <CheckCircle className="h-4 w-4" />,
  RETURN: <Undo2 className="h-4 w-4" />,
};

const eventTypeColors: Record<string, string> = {
  ORDER: 'bg-blue-100 text-blue-800 border-blue-200',
  PAYMENT: 'bg-green-100 text-green-800 border-green-200',
  SHIPMENT: 'bg-purple-100 text-purple-800 border-purple-200',
  DELIVERY: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  RETURN: 'bg-orange-100 text-orange-800 border-orange-200',
};

export default function PublicOrderTrackingPage({ params }: { params: Promise<{ orderNumber: string }> }) {
  const resolvedParams = use(params);
  const orderNumber = resolvedParams.orderNumber.toUpperCase();

  const [phone, setPhone] = useState('');
  const [order, setOrder] = useState<OrderTrackingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verified, setVerified] = useState(false);

  const handleTrack = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!phone || phone.length !== 10) {
      toast.error('Please enter a valid 10-digit phone number');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await orderTrackingApi.trackPublic(orderNumber, phone);
      setOrder(data);
      setVerified(true);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Unable to track order';
      setError(errorMessage);
      if (errorMessage.includes("doesn't match")) {
        toast.error('Phone number does not match the order');
      } else if (errorMessage.includes('not found')) {
        toast.error('Order not found');
      } else {
        toast.error(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const getStatusColor = (status: string) => {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('deliver')) return 'bg-green-100 text-green-800 border-green-200';
    if (statusLower.includes('ship') || statusLower.includes('transit')) return 'bg-blue-100 text-blue-800 border-blue-200';
    if (statusLower.includes('cancel')) return 'bg-red-100 text-red-800 border-red-200';
    if (statusLower.includes('refund')) return 'bg-orange-100 text-orange-800 border-orange-200';
    if (statusLower.includes('return') || statusLower.includes('rto')) return 'bg-amber-100 text-amber-800 border-amber-200';
    if (statusLower.includes('confirm') || statusLower.includes('paid')) return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  // Phone verification form
  if (!verified) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-md">
        <Link
          href="/"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-primary mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Home
        </Link>

        <Card>
          <CardHeader className="text-center">
            <div className="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-4">
              <Search className="h-6 w-6 text-primary" />
            </div>
            <CardTitle>Track Your Order</CardTitle>
            <CardDescription>
              Enter your phone number to verify and track order <strong>{orderNumber}</strong>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleTrack} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="phone">Phone Number</Label>
                <div className="flex gap-2">
                  <span className="flex items-center px-3 bg-muted rounded-l-md border border-r-0 text-sm text-muted-foreground">
                    +91
                  </span>
                  <Input
                    id="phone"
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                    placeholder="Enter 10-digit number"
                    className="rounded-l-none"
                    maxLength={10}
                    autoComplete="tel"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Enter the phone number used for this order
                </p>
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" className="w-full" disabled={loading || phone.length !== 10}>
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <Phone className="h-4 w-4 mr-2" />
                    Track Order
                  </>
                )}
              </Button>
            </form>

            <Separator className="my-6" />

            <p className="text-center text-sm text-muted-foreground">
              Have an account?{' '}
              <Link href={`/account/login?redirect=/account/orders/${orderNumber}`} className="text-primary hover:underline">
                Login
              </Link>{' '}
              for full order details
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Order tracking view (after verification)
  if (!order) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Group timeline by date
  const groupedTimeline = order.timeline.reduce((groups, event) => {
    const date = new Date(event.timestamp).toLocaleDateString('en-IN');
    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(event);
    return groups;
  }, {} as Record<string, TimelineEvent[]>);

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <Link
        href="/"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-primary mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to Home
      </Link>

      {/* Order Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl md:text-3xl font-bold">#{order.order_number}</h1>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => copyToClipboard(order.order_number)}
              aria-label="Copy order number"
            >
              <Copy className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-muted-foreground mt-1">
            {order.status_message} | Placed on{' '}
            {new Date(order.placed_at).toLocaleDateString('en-IN', {
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
          </p>
        </div>
        <Badge variant="outline" className={`${getStatusColor(order.status)} text-sm px-3 py-1`}>
          {order.status.replace(/_/g, ' ')}
        </Badge>
      </div>

      {/* Active Return Alert */}
      {order.active_return && (
        <Alert className="mb-6 bg-amber-50 border-amber-200">
          <Undo2 className="h-4 w-4 text-amber-600" />
          <AlertDescription className="ml-2">
            <span className="font-medium">Return in Progress:</span>{' '}
            RMA {order.active_return.rma_number} - {order.active_return.status.replace(/_/g, ' ')}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Order Progress */}
          {!['CANCELLED', 'REFUNDED'].includes(order.status) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Truck className="h-5 w-5" />
                  Order Progress
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between relative" role="progressbar" aria-label="Order progress">
                  {/* Progress Line */}
                  <div className="absolute top-4 left-0 right-0 h-1 bg-muted mx-8 rounded-full">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{
                        width: `${
                          order.status === 'DELIVERED' ? 100 :
                          order.status === 'OUT_FOR_DELIVERY' ? 85 :
                          ['IN_TRANSIT', 'SHIPPED'].includes(order.status) ? 65 :
                          ['MANIFESTED', 'READY_TO_SHIP', 'PACKED'].includes(order.status) ? 45 :
                          ['CONFIRMED', 'ALLOCATED', 'PICKING', 'PICKED', 'PACKING'].includes(order.status) ? 25 :
                          10
                        }%`,
                      }}
                    />
                  </div>

                  {[
                    { status: 'PLACED', label: 'Placed', icon: Receipt },
                    { status: 'CONFIRMED', label: 'Confirmed', icon: CheckCircle },
                    { status: 'SHIPPED', label: 'Shipped', icon: Truck },
                    { status: 'DELIVERED', label: 'Delivered', icon: Package },
                  ].map((step) => {
                    const isCompleted =
                      step.status === 'PLACED' ? true :
                      step.status === 'CONFIRMED' ? ['CONFIRMED', 'ALLOCATED', 'PICKLIST_CREATED', 'PICKING', 'PICKED', 'PACKING', 'PACKED', 'MANIFESTED', 'READY_TO_SHIP', 'SHIPPED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'DELIVERED'].includes(order.status) :
                      step.status === 'SHIPPED' ? ['SHIPPED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'DELIVERED'].includes(order.status) :
                      step.status === 'DELIVERED' ? order.status === 'DELIVERED' : false;

                    const Icon = step.icon;

                    return (
                      <div key={step.status} className="flex flex-col items-center relative z-10">
                        <div
                          className={`h-8 w-8 rounded-full flex items-center justify-center transition-colors ${
                            isCompleted
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-muted text-muted-foreground'
                          }`}
                          aria-label={`${step.label}: ${isCompleted ? 'Completed' : 'Pending'}`}
                        >
                          <Icon className="h-4 w-4" />
                        </div>
                        <p className="text-xs font-medium mt-2 text-center">{step.label}</p>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Shipment Tracking */}
          {order.shipments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Truck className="h-5 w-5" />
                  Shipment Tracking
                </CardTitle>
              </CardHeader>
              <CardContent>
                {order.shipments.map((shipment) => (
                  <div key={shipment.shipment_id} className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                      <div>
                        <p className="font-medium">{shipment.courier_name || 'Courier'}</p>
                        {shipment.tracking_number && (
                          <p className="text-sm text-muted-foreground">
                            AWB: {shipment.tracking_number}
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 ml-1"
                              onClick={() => copyToClipboard(shipment.tracking_number!)}
                              aria-label="Copy tracking number"
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                          </p>
                        )}
                        <Badge className={getStatusColor(shipment.status)} variant="outline">
                          {shipment.status_message}
                        </Badge>
                      </div>
                      {shipment.tracking_url && (
                        <Button variant="outline" size="sm" asChild>
                          <a href={shipment.tracking_url} target="_blank" rel="noopener noreferrer">
                            Track
                            <ExternalLink className="h-4 w-4 ml-1" />
                          </a>
                        </Button>
                      )}
                    </div>

                    {/* Tracking Events */}
                    {shipment.tracking_events.length > 0 && (
                      <div className="space-y-3 ml-4" role="list" aria-label="Tracking events">
                        {shipment.tracking_events.slice(0, 5).map((event, idx) => (
                          <div key={idx} className="flex gap-3" role="listitem">
                            <div className="flex flex-col items-center">
                              <div className={`w-2 h-2 rounded-full ${idx === 0 ? 'bg-primary' : 'bg-muted-foreground'}`} />
                              {idx < shipment.tracking_events.slice(0, 5).length - 1 && (
                                <div className="w-0.5 h-full bg-muted flex-1" />
                              )}
                            </div>
                            <div className="flex-1 pb-3">
                              <p className={`text-sm ${idx === 0 ? 'font-medium' : ''}`}>{event.message}</p>
                              {event.location && (
                                <p className="text-xs text-muted-foreground">{event.location}</p>
                              )}
                              {event.timestamp && (
                                <p className="text-xs text-muted-foreground">
                                  {new Date(event.timestamp).toLocaleString('en-IN')}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Order Items */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Package className="h-5 w-5" />
                Order Items ({order.items.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {order.items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between py-3 border-b last:border-0"
                  >
                    <div className="flex-1">
                      <p className="font-medium">{item.product_name}</p>
                      <p className="text-sm text-muted-foreground">
                        SKU: {item.sku} | Qty: {item.quantity}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{formatCurrency(item.total_price)}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatCurrency(item.unit_price)} each
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              <Separator className="my-4" />

              {/* Order Summary */}
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span>{formatCurrency(order.subtotal)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tax (GST)</span>
                  <span>{formatCurrency(order.tax_amount)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Shipping</span>
                  <span>
                    {order.shipping_amount === 0 ? 'FREE' : formatCurrency(order.shipping_amount)}
                  </span>
                </div>
                {order.discount_amount > 0 && (
                  <div className="flex justify-between text-green-600">
                    <span>Discount</span>
                    <span>-{formatCurrency(order.discount_amount)}</span>
                  </div>
                )}
                <Separator />
                <div className="flex justify-between text-lg font-semibold pt-2">
                  <span>Total</span>
                  <span className="text-primary">{formatCurrency(order.total_amount)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Timeline */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Order Timeline
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6" role="list" aria-label="Order timeline">
                {Object.entries(groupedTimeline).map(([date, events]) => (
                  <div key={date}>
                    <p className="text-sm font-medium text-muted-foreground mb-3">{date}</p>
                    <div className="space-y-3">
                      {events.map((event, idx) => (
                        <div key={idx} className="flex gap-3" role="listitem">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center border ${eventTypeColors[event.event_type] || 'bg-gray-100'}`}>
                            {eventTypeIcons[event.event_type] || <Circle className="h-4 w-4" />}
                          </div>
                          <div className="flex-1">
                            <p className="font-medium">{event.title}</p>
                            {event.description && (
                              <p className="text-sm text-muted-foreground">{event.description}</p>
                            )}
                            {event.location && (
                              <p className="text-xs text-muted-foreground flex items-center gap-1">
                                <MapPin className="h-3 w-3" />
                                {event.location}
                              </p>
                            )}
                            <p className="text-xs text-muted-foreground mt-1">
                              {new Date(event.timestamp).toLocaleTimeString('en-IN', {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Shipping Address */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <MapPin className="h-4 w-4" />
                Shipping Address
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
              <p className="font-medium">{order.shipping_address.full_name}</p>
              <p className="text-muted-foreground mt-1">
                {order.shipping_address.address_line1}
                {order.shipping_address.address_line2 && (
                  <>, {order.shipping_address.address_line2}</>
                )}
              </p>
              <p className="text-muted-foreground">
                {order.shipping_address.city}, {order.shipping_address.state} -{' '}
                {order.shipping_address.pincode}
              </p>
            </CardContent>
          </Card>

          {/* Payment Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <CreditCard className="h-4 w-4" />
                Payment
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Method</span>
                  <span className="font-medium">
                    {order.payment_method === 'RAZORPAY' ? 'Online' :
                     order.payment_method === 'COD' ? 'Cash on Delivery' : order.payment_method}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <Badge
                    variant="outline"
                    className={
                      order.payment_status === 'PAID'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }
                  >
                    {order.payment_status}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Help Card */}
          <Card>
            <CardContent className="pt-6 space-y-3">
              <p className="text-sm text-muted-foreground text-center">
                Need help with your order?
              </p>
              <Button variant="outline" className="w-full" asChild>
                <Link href="/contact">Contact Support</Link>
              </Button>
              <Button variant="ghost" className="w-full" asChild>
                <Link href={`/account/login?redirect=/account/orders/${orderNumber}`}>
                  Login for More Options
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
