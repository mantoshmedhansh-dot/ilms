'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ChevronRight,
  Package,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Truck,
  AlertCircle,
  Phone,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { returnsApi, ReturnStatus } from '@/lib/storefront/api';
import { useAuthStore } from '@/lib/storefront/auth-store';
import { formatCurrency } from '@/lib/utils';

const statusConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  INITIATED: { label: 'Return Initiated', color: 'bg-blue-100 text-blue-800 border-blue-200', icon: <Clock className="h-4 w-4" /> },
  AUTHORIZED: { label: 'Authorized', color: 'bg-indigo-100 text-indigo-800 border-indigo-200', icon: <CheckCircle2 className="h-4 w-4" /> },
  PICKUP_SCHEDULED: { label: 'Pickup Scheduled', color: 'bg-purple-100 text-purple-800 border-purple-200', icon: <Truck className="h-4 w-4" /> },
  PICKED_UP: { label: 'Picked Up', color: 'bg-violet-100 text-violet-800 border-violet-200', icon: <Package className="h-4 w-4" /> },
  IN_TRANSIT: { label: 'In Transit', color: 'bg-cyan-100 text-cyan-800 border-cyan-200', icon: <RefreshCw className="h-4 w-4" /> },
  RECEIVED: { label: 'Received at Warehouse', color: 'bg-teal-100 text-teal-800 border-teal-200', icon: <Package className="h-4 w-4" /> },
  UNDER_INSPECTION: { label: 'Under Inspection', color: 'bg-amber-100 text-amber-800 border-amber-200', icon: <RefreshCw className="h-4 w-4" /> },
  APPROVED: { label: 'Return Approved', color: 'bg-green-100 text-green-800 border-green-200', icon: <CheckCircle2 className="h-4 w-4" /> },
  REJECTED: { label: 'Return Rejected', color: 'bg-red-100 text-red-800 border-red-200', icon: <XCircle className="h-4 w-4" /> },
  REFUND_INITIATED: { label: 'Refund Processing', color: 'bg-orange-100 text-orange-800 border-orange-200', icon: <RefreshCw className="h-4 w-4" /> },
  REFUND_PROCESSED: { label: 'Refund Completed', color: 'bg-emerald-100 text-emerald-800 border-emerald-200', icon: <CheckCircle2 className="h-4 w-4" /> },
  CLOSED: { label: 'Closed', color: 'bg-gray-100 text-gray-800 border-gray-200', icon: <CheckCircle2 className="h-4 w-4" /> },
  CANCELLED: { label: 'Cancelled', color: 'bg-gray-100 text-gray-600 border-gray-200', icon: <XCircle className="h-4 w-4" /> },
};

export default function ReturnDetailPage({ params }: { params: Promise<{ rmaNumber: string }> }) {
  const resolvedParams = use(params);
  const router = useRouter();
  const { isAuthenticated, customer } = useAuthStore();
  const [returnData, setReturnData] = useState<ReturnStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [phone, setPhone] = useState('');
  const [needsVerification, setNeedsVerification] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    const fetchReturn = async () => {
      // If logged in, use customer's phone
      if (isAuthenticated && customer?.phone) {
        try {
          const data = await returnsApi.trackReturn(resolvedParams.rmaNumber, customer.phone);
          setReturnData(data);
          setNeedsVerification(false);
        } catch (error: any) {
          if (error.response?.status === 403) {
            setNeedsVerification(true);
          } else {
            toast.error('Return not found');
            router.push('/account/returns');
          }
        } finally {
          setLoading(false);
        }
      } else {
        // Guest user needs to verify phone
        setNeedsVerification(true);
        setLoading(false);
      }
    };

    fetchReturn();
  }, [resolvedParams.rmaNumber, isAuthenticated, customer, router]);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone || phone.length < 10) {
      toast.error('Please enter a valid phone number');
      return;
    }

    setVerifying(true);
    try {
      const data = await returnsApi.trackReturn(resolvedParams.rmaNumber, phone);
      setReturnData(data);
      setNeedsVerification(false);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Phone number does not match');
    } finally {
      setVerifying(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this return request?')) return;

    setCancelling(true);
    try {
      await returnsApi.cancelReturn(resolvedParams.rmaNumber);
      toast.success('Return cancelled successfully');
      // Refresh the data
      if (customer?.phone) {
        const data = await returnsApi.trackReturn(resolvedParams.rmaNumber, customer.phone);
        setReturnData(data);
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to cancel return');
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (needsVerification) {
    return (
      <div className="bg-muted/50 min-h-screen py-6">
        <div className="container mx-auto px-4 max-w-md">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Phone className="h-5 w-5" />
                Verify Phone Number
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Enter the phone number used in the order to view return details.
              </p>
              <form onSubmit={handleVerify} className="space-y-4">
                <div>
                  <Label htmlFor="phone">Phone Number</Label>
                  <Input
                    id="phone"
                    type="tel"
                    placeholder="Enter 10-digit phone"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                    maxLength={10}
                  />
                </div>
                <Button type="submit" className="w-full" disabled={verifying}>
                  {verifying ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    'Verify & View Return'
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (!returnData) {
    return (
      <div className="bg-muted/50 min-h-screen py-6">
        <div className="container mx-auto px-4 max-w-4xl text-center py-12">
          <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Return Not Found</h2>
          <p className="text-muted-foreground mb-4">
            We couldn&apos;t find a return with this RMA number.
          </p>
          <Button asChild>
            <Link href="/account/returns">Back to Returns</Link>
          </Button>
        </div>
      </div>
    );
  }

  const statusInfo = statusConfig[returnData.status] || statusConfig.INITIATED;
  const canCancel = ['INITIATED', 'AUTHORIZED'].includes(returnData.status);

  return (
    <div className="bg-muted/50 min-h-screen py-6">
      <div className="container mx-auto px-4 max-w-4xl">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
          <Link href="/" className="hover:text-primary">Home</Link>
          <ChevronRight className="h-4 w-4" />
          <Link href="/account" className="hover:text-primary">Account</Link>
          <ChevronRight className="h-4 w-4" />
          <Link href="/account/returns" className="hover:text-primary">Returns</Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground">{returnData.rma_number}</span>
        </nav>

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold">{returnData.rma_number}</h1>
            <p className="text-muted-foreground">
              Requested on {new Date(returnData.requested_at).toLocaleDateString('en-IN', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })}
            </p>
          </div>
          <Badge className={`${statusInfo.color} gap-2 px-4 py-2 text-sm border`}>
            {statusInfo.icon}
            {statusInfo.label}
          </Badge>
        </div>

        {/* Status Message */}
        <Alert className="mb-6">
          <AlertDescription className="flex items-center gap-2">
            {statusInfo.icon}
            <span>{returnData.status_message}</span>
          </AlertDescription>
        </Alert>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="md:col-span-2 space-y-6">
            {/* Items */}
            <Card>
              <CardHeader>
                <CardTitle>Return Items</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {returnData.items.map((item) => (
                  <div key={item.id} className="flex justify-between items-start p-4 bg-muted/50 rounded-lg">
                    <div className="flex-1">
                      <h4 className="font-medium">{item.product_name}</h4>
                      <p className="text-sm text-muted-foreground">SKU: {item.sku}</p>
                      <p className="text-sm text-muted-foreground">
                        Qty: {item.quantity_returned} of {item.quantity_ordered} | Condition: {item.condition.replace(/_/g, ' ')}
                      </p>
                      {item.inspection_result && (
                        <Badge variant={item.inspection_result === 'ACCEPTED' ? 'default' : 'destructive'} className="mt-2">
                          Inspection: {item.inspection_result}
                          {item.accepted_quantity !== undefined && item.accepted_quantity !== item.quantity_returned && (
                            <span> ({item.accepted_quantity} accepted)</span>
                          )}
                        </Badge>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{formatCurrency(item.total_amount)}</p>
                      {item.refund_amount > 0 && item.refund_amount !== item.total_amount && (
                        <p className="text-sm text-green-600">Refund: {formatCurrency(item.refund_amount)}</p>
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Timeline */}
            <Card>
              <CardHeader>
                <CardTitle>Return Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative">
                  {returnData.timeline.map((event, index) => {
                    const eventStatus = statusConfig[event.to_status] || statusConfig.INITIATED;
                    return (
                      <div key={event.id} className="flex gap-4 pb-6 last:pb-0">
                        <div className="relative">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${eventStatus.color}`}>
                            {eventStatus.icon}
                          </div>
                          {index < returnData.timeline.length - 1 && (
                            <div className="absolute top-8 left-1/2 -translate-x-1/2 w-0.5 h-full bg-border" />
                          )}
                        </div>
                        <div className="flex-1 pt-1">
                          <p className="font-medium">{statusConfig[event.to_status]?.label || event.to_status}</p>
                          {event.notes && (
                            <p className="text-sm text-muted-foreground">{event.notes}</p>
                          )}
                          <p className="text-xs text-muted-foreground mt-1">
                            {new Date(event.created_at).toLocaleString('en-IN')}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Refund Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Refund Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Refund Amount</span>
                  <span className="font-semibold text-lg text-primary">
                    {formatCurrency(returnData.refund_amount || 0)}
                  </span>
                </div>

                {returnData.refund_status && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Refund Status</span>
                    <Badge variant={returnData.refund_status === 'COMPLETED' ? 'default' : 'secondary'}>
                      {returnData.refund_status}
                    </Badge>
                  </div>
                )}

                {returnData.estimated_refund_date && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Expected By</span>
                    <span>
                      {new Date(returnData.estimated_refund_date).toLocaleDateString('en-IN')}
                    </span>
                  </div>
                )}

                <Separator />

                <p className="text-xs text-muted-foreground">
                  Refunds are typically processed within 5-7 business days after return approval.
                </p>
              </CardContent>
            </Card>

            {/* Return Tracking */}
            {returnData.tracking_number && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Truck className="h-5 w-5" />
                    Return Shipment
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">
                    <span className="text-muted-foreground">Courier:</span>{' '}
                    {returnData.courier || 'N/A'}
                  </p>
                  <p className="text-sm mt-1">
                    <span className="text-muted-foreground">Tracking:</span>{' '}
                    <span className="font-mono">{returnData.tracking_number}</span>
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Actions */}
            {canCancel && isAuthenticated && (
              <Card>
                <CardContent className="pt-6">
                  <Button
                    variant="destructive"
                    className="w-full"
                    onClick={handleCancel}
                    disabled={cancelling}
                  >
                    {cancelling ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Cancelling...
                      </>
                    ) : (
                      'Cancel Return'
                    )}
                  </Button>
                  <p className="text-xs text-muted-foreground mt-2 text-center">
                    You can cancel this return before it&apos;s picked up.
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Help */}
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground mb-3">
                  Need help with your return?
                </p>
                <Button variant="outline" className="w-full" asChild>
                  <Link href="/contact">Contact Support</Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
