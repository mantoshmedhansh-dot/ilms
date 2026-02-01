'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Package,
  Truck,
  MapPin,
  CheckCircle,
  Clock,
  AlertCircle,
  Copy,
  ExternalLink,
  Loader2,
  Phone,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from 'sonner';
import { formatCurrency } from '@/lib/utils';

// API client
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://aquapurite-erp-api.onrender.com';

interface TrackingEvent {
  status: string;
  status_message: string;
  location: string | null;
  remarks: string | null;
  timestamp: string;
}

interface ShipmentTrackingResponse {
  awb_number: string;
  courier_name: string;
  status: string;
  status_message: string;
  origin_city: string | null;
  destination_city: string | null;
  destination_pincode: string | null;
  shipped_at: string | null;
  estimated_delivery: string | null;
  delivered_at: string | null;
  current_location: string | null;
  tracking_url: string | null;
  tracking_events: TrackingEvent[];
  order_number: string | null;
  payment_mode: string;
  cod_amount: number | null;
}

export default function AWBTrackingPage({ params }: { params: Promise<{ awb: string }> }) {
  const resolvedParams = use(params);
  const awb = resolvedParams.awb;

  const [shipment, setShipment] = useState<ShipmentTrackingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchTracking = async (showRefreshToast = false) => {
    try {
      if (showRefreshToast) setRefreshing(true);
      else setLoading(true);

      const response = await fetch(`${API_URL}/api/v1/storefront/track/${awb}`);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Shipment not found. Please check the AWB number.');
        }
        throw new Error('Failed to fetch tracking information');
      }

      const data = await response.json();
      setShipment(data);
      setError(null);

      if (showRefreshToast) {
        toast.success('Tracking updated');
      }
    } catch (err: any) {
      setError(err.message);
      if (showRefreshToast) {
        toast.error(err.message);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchTracking();
  }, [awb]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const getStatusColor = (status: string) => {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('deliver')) return 'bg-green-100 text-green-800 border-green-200';
    if (statusLower.includes('transit') || statusLower.includes('picked')) return 'bg-blue-100 text-blue-800 border-blue-200';
    if (statusLower.includes('rto') || statusLower.includes('return')) return 'bg-orange-100 text-orange-800 border-orange-200';
    if (statusLower.includes('fail') || statusLower.includes('lost')) return 'bg-red-100 text-red-800 border-red-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const getStatusIcon = (status: string) => {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('deliver')) return <CheckCircle className="h-5 w-5 text-green-600" />;
    if (statusLower.includes('transit') || statusLower.includes('out_for')) return <Truck className="h-5 w-5 text-blue-600" />;
    if (statusLower.includes('fail') || statusLower.includes('rto')) return <AlertCircle className="h-5 w-5 text-orange-600" />;
    return <Package className="h-5 w-5 text-gray-600" />;
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Fetching shipment details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-xl">
        <Link
          href="/track"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-primary mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Track
        </Link>

        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Shipment Not Found</h2>
            <p className="text-muted-foreground mb-6">{error}</p>
            <div className="space-y-3">
              <Button onClick={() => fetchTracking()} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              <p className="text-sm text-muted-foreground">
                AWB: <code className="bg-muted px-2 py-1 rounded">{awb}</code>
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!shipment) return null;

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <Link
        href="/track"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-primary mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to Track
      </Link>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl md:text-3xl font-bold">{shipment.awb_number}</h1>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => copyToClipboard(shipment.awb_number)}
              aria-label="Copy AWB number"
            >
              <Copy className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-muted-foreground mt-1">
            {shipment.courier_name || 'Courier'} | {shipment.status_message}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className={`${getStatusColor(shipment.status)} text-sm px-3 py-1`}>
            {getStatusIcon(shipment.status)}
            <span className="ml-2">{shipment.status.replace(/_/g, ' ')}</span>
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchTracking(true)}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Link to Order if available */}
      {shipment.order_number && (
        <Alert className="mb-6">
          <Package className="h-4 w-4" />
          <AlertDescription className="ml-2">
            This shipment is for order <strong>{shipment.order_number}</strong>.{' '}
            <Link href={`/track/order/${shipment.order_number}`} className="text-primary hover:underline">
              View full order details
            </Link>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Journey Progress */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Truck className="h-5 w-5" />
                Shipment Progress
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-6">
                <div className="text-center">
                  <div className="w-3 h-3 rounded-full bg-primary mx-auto mb-2" />
                  <p className="text-xs font-medium">{shipment.origin_city || 'Origin'}</p>
                </div>
                <div className="flex-1 h-1 bg-muted mx-4 relative">
                  <div
                    className="absolute h-full bg-primary rounded-full transition-all"
                    style={{
                      width: `${
                        shipment.status === 'DELIVERED' ? 100 :
                        shipment.status === 'OUT_FOR_DELIVERY' ? 90 :
                        ['IN_TRANSIT', 'REACHED_HUB'].includes(shipment.status) ? 60 :
                        ['PICKED_UP', 'MANIFESTED'].includes(shipment.status) ? 30 :
                        10
                      }%`,
                    }}
                  />
                  <Truck className="absolute top-1/2 -translate-y-1/2 text-primary h-5 w-5"
                    style={{
                      left: `${
                        shipment.status === 'DELIVERED' ? 95 :
                        shipment.status === 'OUT_FOR_DELIVERY' ? 85 :
                        ['IN_TRANSIT', 'REACHED_HUB'].includes(shipment.status) ? 55 :
                        ['PICKED_UP', 'MANIFESTED'].includes(shipment.status) ? 25 :
                        5
                      }%`,
                    }}
                  />
                </div>
                <div className="text-center">
                  <div className={`w-3 h-3 rounded-full mx-auto mb-2 ${shipment.status === 'DELIVERED' ? 'bg-green-600' : 'bg-muted'}`} />
                  <p className="text-xs font-medium">{shipment.destination_city || 'Destination'}</p>
                </div>
              </div>

              {shipment.current_location && (
                <div className="flex items-center gap-2 text-sm bg-muted/50 rounded-lg p-3">
                  <MapPin className="h-4 w-4 text-primary" />
                  <span>Current Location: <strong>{shipment.current_location}</strong></span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tracking History */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Tracking History
              </CardTitle>
            </CardHeader>
            <CardContent>
              {shipment.tracking_events.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  No tracking updates yet. Please check back later.
                </p>
              ) : (
                <div className="space-y-4" role="list">
                  {shipment.tracking_events.map((event, idx) => (
                    <div key={idx} className="flex gap-3" role="listitem">
                      <div className="flex flex-col items-center">
                        <div className={`w-3 h-3 rounded-full ${idx === 0 ? 'bg-primary' : 'bg-muted-foreground/50'}`} />
                        {idx < shipment.tracking_events.length - 1 && (
                          <div className="w-0.5 h-full bg-muted flex-1 mt-1" />
                        )}
                      </div>
                      <div className="flex-1 pb-4">
                        <p className={`text-sm ${idx === 0 ? 'font-semibold' : ''}`}>
                          {event.status_message}
                        </p>
                        {event.remarks && (
                          <p className="text-sm text-muted-foreground">{event.remarks}</p>
                        )}
                        {event.location && (
                          <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                            <MapPin className="h-3 w-3" />
                            {event.location}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(event.timestamp).toLocaleString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Shipment Details */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Shipment Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Courier</span>
                <span className="font-medium">{shipment.courier_name || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">AWB Number</span>
                <span className="font-medium">{shipment.awb_number}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Payment</span>
                <Badge variant="outline">
                  {shipment.payment_mode === 'COD' ? `COD ${formatCurrency(shipment.cod_amount || 0)}` : 'Prepaid'}
                </Badge>
              </div>
              {shipment.shipped_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Shipped</span>
                  <span>{new Date(shipment.shipped_at).toLocaleDateString('en-IN')}</span>
                </div>
              )}
              {shipment.estimated_delivery && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Est. Delivery</span>
                  <span>{new Date(shipment.estimated_delivery).toLocaleDateString('en-IN')}</span>
                </div>
              )}
              {shipment.delivered_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Delivered</span>
                  <span className="text-green-600 font-medium">
                    {new Date(shipment.delivered_at).toLocaleDateString('en-IN')}
                  </span>
                </div>
              )}

              {shipment.tracking_url && (
                <Button variant="outline" size="sm" className="w-full mt-4" asChild>
                  <a href={shipment.tracking_url} target="_blank" rel="noopener noreferrer">
                    Track on {shipment.courier_name}
                    <ExternalLink className="h-4 w-4 ml-2" />
                  </a>
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Destination */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <MapPin className="h-4 w-4" />
                Destination
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
              <p className="font-medium">{shipment.destination_city || '-'}</p>
              {shipment.destination_pincode && (
                <p className="text-muted-foreground">PIN: {shipment.destination_pincode}</p>
              )}
            </CardContent>
          </Card>

          {/* Help */}
          <Card>
            <CardContent className="pt-6 space-y-3">
              <p className="text-sm text-muted-foreground text-center">
                Need help with your shipment?
              </p>
              <Button variant="outline" className="w-full" asChild>
                <a href="tel:+919311939076">
                  <Phone className="h-4 w-4 mr-2" />
                  Call Support
                </a>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
