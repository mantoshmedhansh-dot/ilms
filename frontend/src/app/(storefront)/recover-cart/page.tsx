'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { ShoppingCart, ArrowRight, AlertCircle, CheckCircle, Loader2, Package } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useCartStore } from '@/lib/storefront/cart-store';
import { abandonedCartApi, RecoveredCartResponse } from '@/lib/storefront/api';

function RecoverCartContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');
  const { recoverCart, openCart } = useCartStore();

  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'expired'>('loading');
  const [recoveredData, setRecoveredData] = useState<RecoveredCartResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const handleRecovery = async () => {
      if (!token) {
        setStatus('error');
        setErrorMessage('No recovery token provided');
        return;
      }

      try {
        // First, fetch the cart data directly to show summary
        const data = await abandonedCartApi.recover(token);
        setRecoveredData(data);

        // Then recover the cart into the store
        const success = await recoverCart(token);

        if (success) {
          setStatus('success');
        } else {
          setStatus('error');
          setErrorMessage('Failed to recover cart');
        }
      } catch (error: any) {
        if (error.response?.status === 410) {
          setStatus('expired');
          setErrorMessage('This recovery link has expired');
        } else if (error.response?.status === 404) {
          setStatus('error');
          setErrorMessage('Cart not found or already converted to an order');
        } else {
          setStatus('error');
          setErrorMessage(error.response?.data?.detail || 'Failed to recover cart');
        }
      }
    };

    handleRecovery();
  }, [token, recoverCart]);

  const handleContinueShopping = () => {
    openCart();
    router.push('/');
  };

  const handleGoToCheckout = () => {
    router.push('/checkout');
  };

  if (status === 'loading') {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <h1 className="text-xl font-semibold mb-2">Recovering Your Cart</h1>
          <p className="text-muted-foreground">Please wait while we restore your items...</p>
        </div>
      </div>
    );
  }

  if (status === 'expired') {
    return (
      <div className="container mx-auto px-4 py-12 max-w-2xl">
        <Card>
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-yellow-100 flex items-center justify-center">
              <AlertCircle className="h-8 w-8 text-yellow-600" />
            </div>
            <CardTitle className="text-2xl">Link Expired</CardTitle>
            <CardDescription>
              This recovery link has expired. Recovery links are valid for 7 days.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <p className="text-muted-foreground">
              Don&apos;t worry! You can still browse our products and add items to your cart.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button asChild>
                <Link href="/products">
                  Browse Products
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link href="/">
                  Go to Homepage
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="container mx-auto px-4 py-12 max-w-2xl">
        <Card>
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-red-100 flex items-center justify-center">
              <AlertCircle className="h-8 w-8 text-red-600" />
            </div>
            <CardTitle className="text-2xl">Unable to Recover Cart</CardTitle>
            <CardDescription>
              {errorMessage || 'We were unable to restore your cart.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <p className="text-muted-foreground">
              The cart may have already been converted to an order, or the link may be invalid.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button asChild>
                <Link href="/products">
                  Browse Products
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link href="/account/orders">
                  Check Your Orders
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Success state
  return (
    <div className="container mx-auto px-4 py-12 max-w-3xl">
      <Card>
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-green-100 flex items-center justify-center">
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
          <CardTitle className="text-2xl">Welcome Back!</CardTitle>
          <CardDescription>
            Your cart has been restored. Pick up where you left off.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Cart Items Summary */}
          {recoveredData && recoveredData.items.length > 0 && (
            <div className="space-y-4">
              <h3 className="font-semibold flex items-center gap-2">
                <ShoppingCart className="h-5 w-5" />
                Your Cart Items ({recoveredData.items.length})
              </h3>
              <div className="divide-y border rounded-lg">
                {recoveredData.items.map((item, index) => (
                  <div key={index} className="flex items-center gap-4 p-4">
                    <div className="h-16 w-16 bg-muted rounded-md flex items-center justify-center overflow-hidden">
                      {item.image_url ? (
                        <Image
                          src={item.image_url}
                          alt={item.product_name}
                          width={64}
                          height={64}
                          className="object-cover"
                        />
                      ) : (
                        <Package className="h-8 w-8 text-muted-foreground" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{item.product_name}</p>
                      {item.variant_name && (
                        <p className="text-sm text-muted-foreground">{item.variant_name}</p>
                      )}
                      <p className="text-sm text-muted-foreground">Qty: {item.quantity}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">
                        {new Intl.NumberFormat('en-IN', {
                          style: 'currency',
                          currency: 'INR',
                          maximumFractionDigits: 0,
                        }).format(item.price * item.quantity)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Price Summary */}
          {recoveredData && (
            <div className="bg-muted/50 rounded-lg p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span>Subtotal</span>
                <span>
                  {new Intl.NumberFormat('en-IN', {
                    style: 'currency',
                    currency: 'INR',
                    maximumFractionDigits: 0,
                  }).format(recoveredData.subtotal)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Tax (GST)</span>
                <span>
                  {new Intl.NumberFormat('en-IN', {
                    style: 'currency',
                    currency: 'INR',
                    maximumFractionDigits: 0,
                  }).format(recoveredData.tax_amount)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Shipping</span>
                <span>
                  {recoveredData.shipping_amount > 0
                    ? new Intl.NumberFormat('en-IN', {
                        style: 'currency',
                        currency: 'INR',
                        maximumFractionDigits: 0,
                      }).format(recoveredData.shipping_amount)
                    : 'FREE'}
                </span>
              </div>
              {recoveredData.discount_amount > 0 && (
                <div className="flex justify-between text-sm text-green-600">
                  <span>Discount</span>
                  <span>
                    -
                    {new Intl.NumberFormat('en-IN', {
                      style: 'currency',
                      currency: 'INR',
                      maximumFractionDigits: 0,
                    }).format(recoveredData.discount_amount)}
                  </span>
                </div>
              )}
              <div className="border-t pt-2 flex justify-between font-semibold">
                <span>Total</span>
                <span>
                  {new Intl.NumberFormat('en-IN', {
                    style: 'currency',
                    currency: 'INR',
                    maximumFractionDigits: 0,
                  }).format(recoveredData.total_amount)}
                </span>
              </div>
            </div>
          )}

          {/* Special Offer Alert */}
          <Alert>
            <AlertDescription className="flex items-center gap-2">
              <span>Complete your order now and enjoy special savings!</span>
            </AlertDescription>
          </Alert>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3">
            <Button className="flex-1" size="lg" onClick={handleGoToCheckout}>
              Proceed to Checkout
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <Button variant="outline" className="flex-1" size="lg" onClick={handleContinueShopping}>
              Continue Shopping
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function RecoverCartPage() {
  return (
    <Suspense fallback={
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <h1 className="text-xl font-semibold mb-2">Loading...</h1>
        </div>
      </div>
    }>
      <RecoverCartContent />
    </Suspense>
  );
}
