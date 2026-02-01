'use client';

import { useState, useEffect } from 'react';
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
  ArrowRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { returnsApi, ReturnListItem } from '@/lib/storefront/api';
import { useAuthStore } from '@/lib/storefront/auth-store';
import { formatCurrency } from '@/lib/utils';

const statusConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  INITIATED: { label: 'Initiated', color: 'bg-blue-100 text-blue-800', icon: <Clock className="h-3 w-3" /> },
  AUTHORIZED: { label: 'Authorized', color: 'bg-indigo-100 text-indigo-800', icon: <CheckCircle2 className="h-3 w-3" /> },
  PICKUP_SCHEDULED: { label: 'Pickup Scheduled', color: 'bg-purple-100 text-purple-800', icon: <Clock className="h-3 w-3" /> },
  PICKED_UP: { label: 'Picked Up', color: 'bg-violet-100 text-violet-800', icon: <Package className="h-3 w-3" /> },
  IN_TRANSIT: { label: 'In Transit', color: 'bg-cyan-100 text-cyan-800', icon: <RefreshCw className="h-3 w-3" /> },
  RECEIVED: { label: 'Received', color: 'bg-teal-100 text-teal-800', icon: <Package className="h-3 w-3" /> },
  UNDER_INSPECTION: { label: 'Under Inspection', color: 'bg-amber-100 text-amber-800', icon: <RefreshCw className="h-3 w-3" /> },
  APPROVED: { label: 'Approved', color: 'bg-green-100 text-green-800', icon: <CheckCircle2 className="h-3 w-3" /> },
  REJECTED: { label: 'Rejected', color: 'bg-red-100 text-red-800', icon: <XCircle className="h-3 w-3" /> },
  REFUND_INITIATED: { label: 'Refund Processing', color: 'bg-orange-100 text-orange-800', icon: <RefreshCw className="h-3 w-3" /> },
  REFUND_PROCESSED: { label: 'Refund Completed', color: 'bg-emerald-100 text-emerald-800', icon: <CheckCircle2 className="h-3 w-3" /> },
  CLOSED: { label: 'Closed', color: 'bg-gray-100 text-gray-800', icon: <CheckCircle2 className="h-3 w-3" /> },
  CANCELLED: { label: 'Cancelled', color: 'bg-gray-100 text-gray-600', icon: <XCircle className="h-3 w-3" /> },
};

export default function ReturnsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuthStore();
  const [returns, setReturns] = useState<ReturnListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/account/login?redirect=/account/returns');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    const fetchReturns = async () => {
      if (!isAuthenticated) return;

      setLoading(true);
      try {
        const data = await returnsApi.getMyReturns(page, 10);
        setReturns(data.items);
        setTotalPages(data.pages);
      } catch (error) {
        console.error('Failed to fetch returns:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchReturns();
  }, [isAuthenticated, page]);

  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="bg-muted/50 min-h-screen py-6">
      <div className="container mx-auto px-4 max-w-4xl">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
          <Link href="/" className="hover:text-primary">Home</Link>
          <ChevronRight className="h-4 w-4" />
          <Link href="/account" className="hover:text-primary">Account</Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground">Returns</span>
        </nav>

        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl md:text-3xl font-bold">My Returns</h1>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : returns.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <RefreshCw className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No returns yet</h3>
              <p className="text-muted-foreground mb-6">
                You haven&apos;t requested any returns. If you need to return an item, go to your order and initiate a return.
              </p>
              <Button asChild>
                <Link href="/account/orders">View Orders</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {returns.map((ret) => {
              const statusInfo = statusConfig[ret.status] || statusConfig.INITIATED;

              return (
                <Card key={ret.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-4 md:p-6">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="font-mono font-semibold text-primary">
                            {ret.rma_number}
                          </span>
                          <Badge className={`${statusInfo.color} gap-1`}>
                            {statusInfo.icon}
                            {statusInfo.label}
                          </Badge>
                        </div>

                        <div className="text-sm text-muted-foreground space-y-1">
                          <p>Order: {ret.order_number}</p>
                          <p>Reason: {ret.return_reason.replace(/_/g, ' ')}</p>
                          <p>Items: {ret.items_count} | Requested: {new Date(ret.requested_at).toLocaleDateString()}</p>
                        </div>
                      </div>

                      <div className="flex flex-col items-end gap-2">
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground">Refund Amount</p>
                          <p className="text-lg font-bold text-primary">
                            {formatCurrency(ret.net_refund_amount)}
                          </p>
                        </div>
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/account/returns/${ret.rma_number}`}>
                            View Details
                            <ArrowRight className="h-4 w-4 ml-1" />
                          </Link>
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center gap-2 mt-6">
                <Button
                  variant="outline"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <span className="flex items-center px-4">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
