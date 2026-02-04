'use client';

import { useState, useEffect } from 'react';
import {
  MapPin,
  Truck,
  Check,
  X,
  Loader2,
  RefreshCw,
  Clock,
  CreditCard,
  Banknote,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { inventoryApi } from '@/lib/storefront/api';
import { cn } from '@/lib/utils';

interface DeliveryInfo {
  serviceable: boolean;
  estimate_days?: number;
  message?: string;
  cod_available?: boolean;
  shipping_cost?: number;
}

interface PinCodeCheckerProps {
  productPrice?: number;
  className?: string;
}

const PINCODE_STORAGE_KEY = 'ilms_delivery_pincode';
const FREE_DELIVERY_THRESHOLD = 999; // Free delivery above this amount

export function PinCodeChecker({ productPrice = 0, className }: PinCodeCheckerProps) {
  const [pincode, setPincode] = useState('');
  const [savedPincode, setSavedPincode] = useState<string | null>(null);
  const [deliveryInfo, setDeliveryInfo] = useState<DeliveryInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [showInput, setShowInput] = useState(false);

  // Load saved pincode on mount
  useEffect(() => {
    const saved = localStorage.getItem(PINCODE_STORAGE_KEY);
    if (saved && /^\d{6}$/.test(saved)) {
      setSavedPincode(saved);
      setPincode(saved);
      // Auto-check saved pincode
      checkDelivery(saved);
    }
  }, []);

  const checkDelivery = async (code: string) => {
    if (!code || code.length !== 6) return;

    setLoading(true);
    try {
      const result = await inventoryApi.checkDelivery(code);
      setDeliveryInfo(result);
      // Save pincode if serviceable
      if (result.serviceable) {
        localStorage.setItem(PINCODE_STORAGE_KEY, code);
        setSavedPincode(code);
      }
    } catch (error) {
      setDeliveryInfo({
        serviceable: false,
        message: 'Unable to check delivery. Please try again.',
      });
    } finally {
      setLoading(false);
      setShowInput(false);
    }
  };

  const handleCheck = () => {
    checkDelivery(pincode);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleCheck();
    }
  };

  const handleChangePincode = () => {
    setShowInput(true);
    setDeliveryInfo(null);
  };

  const getDeliveryDate = (days: number): string => {
    const date = new Date();
    date.setDate(date.getDate() + days);
    return date.toLocaleDateString('en-IN', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
    });
  };

  const isFreeDelivery = productPrice >= FREE_DELIVERY_THRESHOLD;

  // If no saved pincode and not showing input, show prompt
  if (!savedPincode && !showInput && !deliveryInfo) {
    return (
      <div className={cn('rounded-lg border bg-card p-4', className)}>
        <button
          onClick={() => setShowInput(true)}
          className="w-full flex items-center justify-between text-left hover:bg-muted/50 -m-4 p-4 rounded-lg transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
              <MapPin className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="font-medium text-sm">Check Delivery Availability</p>
              <p className="text-xs text-muted-foreground">Enter pincode for delivery info</p>
            </div>
          </div>
          <ChevronRight className="h-5 w-5 text-muted-foreground" />
        </button>
      </div>
    );
  }

  // Show input form
  if (showInput || (!deliveryInfo && !loading)) {
    return (
      <div className={cn('rounded-lg border bg-card p-4', className)}>
        <div className="flex items-center gap-2 mb-3">
          <MapPin className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">Delivery Location</span>
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="Enter 6-digit pincode"
            value={pincode}
            onChange={(e) => setPincode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            onKeyDown={handleKeyDown}
            className="flex-1"
            autoFocus
          />
          <Button
            onClick={handleCheck}
            disabled={loading || pincode.length !== 6}
            className="shrink-0"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              'Check'
            )}
          </Button>
        </div>
        {savedPincode && (
          <button
            onClick={() => {
              setPincode(savedPincode);
              checkDelivery(savedPincode);
            }}
            className="mt-2 text-xs text-primary hover:underline"
          >
            Use saved pincode: {savedPincode}
          </button>
        )}
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className={cn('rounded-lg border bg-card p-4', className)}>
        <div className="flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">Checking delivery for {pincode}...</span>
        </div>
      </div>
    );
  }

  // Show delivery info
  if (deliveryInfo) {
    return (
      <div className={cn('rounded-lg border bg-card overflow-hidden', className)}>
        {/* Header with pincode */}
        <div className="flex items-center justify-between px-4 py-2 bg-muted/50 border-b">
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">
              Deliver to <span className="font-semibold">{savedPincode}</span>
            </span>
          </div>
          <button
            onClick={handleChangePincode}
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            <RefreshCw className="h-3 w-3" />
            Change
          </button>
        </div>

        <div className="p-4 space-y-3">
          {deliveryInfo.serviceable ? (
            <>
              {/* Delivery Estimate */}
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center shrink-0">
                  <Truck className="h-4 w-4 text-green-600" />
                </div>
                <div>
                  <p className="font-medium text-green-600 flex items-center gap-1">
                    <Check className="h-4 w-4" />
                    Delivery Available
                  </p>
                  {deliveryInfo.estimate_days && (
                    <p className="text-sm">
                      Get it by{' '}
                      <span className="font-semibold text-foreground">
                        {getDeliveryDate(deliveryInfo.estimate_days)}
                      </span>
                    </p>
                  )}
                </div>
              </div>

              {/* Shipping Cost */}
              <div className="flex items-center gap-3 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground" />
                {isFreeDelivery ? (
                  <span className="text-green-600 font-medium">FREE Delivery</span>
                ) : deliveryInfo.shipping_cost ? (
                  <span>
                    Shipping: <span className="font-medium">₹{deliveryInfo.shipping_cost}</span>
                    <span className="text-xs text-muted-foreground ml-1">
                      (Free above ₹{FREE_DELIVERY_THRESHOLD})
                    </span>
                  </span>
                ) : (
                  <span className="text-green-600 font-medium">FREE Delivery</span>
                )}
              </div>

              {/* COD Availability */}
              <div className="flex items-center gap-3 text-sm">
                {deliveryInfo.cod_available ? (
                  <>
                    <Banknote className="h-4 w-4 text-muted-foreground" />
                    <span className="flex items-center gap-1">
                      <Check className="h-3 w-3 text-green-600" />
                      Cash on Delivery available
                    </span>
                  </>
                ) : (
                  <>
                    <CreditCard className="h-4 w-4 text-muted-foreground" />
                    <span className="flex items-center gap-1">
                      Prepaid only
                      <span className="text-xs text-muted-foreground">(No COD)</span>
                    </span>
                  </>
                )}
              </div>
            </>
          ) : (
            /* Not Serviceable */
            <div className="flex items-start gap-3">
              <div className="h-8 w-8 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center shrink-0">
                <X className="h-4 w-4 text-red-600" />
              </div>
              <div>
                <p className="font-medium text-red-600">
                  Delivery Not Available
                </p>
                <p className="text-sm text-muted-foreground">
                  {deliveryInfo.message || `Sorry, we don't deliver to ${savedPincode} currently.`}
                </p>
                <button
                  onClick={handleChangePincode}
                  className="text-sm text-primary hover:underline mt-1"
                >
                  Try another pincode
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return null;
}

export default PinCodeChecker;
