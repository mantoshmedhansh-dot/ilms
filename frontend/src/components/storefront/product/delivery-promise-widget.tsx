'use client';

import { useState, useEffect } from 'react';
import {
  MapPin,
  Truck,
  Loader2,
  Calendar,
  Shield,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface DeliveryPromiseResult {
  product_id: string;
  pincode: string;
  serviceable: boolean;
  earliest_date?: string;
  expected_date?: string;
  latest_date?: string;
  confidence?: number;
  breakdown?: {
    processing_days?: number;
    transit_days?: number;
    buffer_days?: number;
  };
  warehouse_name?: string;
  message?: string;
}

interface DeliveryPromiseWidgetProps {
  productId?: string;
  quantity?: number;
  className?: string;
}

const PINCODE_STORAGE_KEY = 'ilms_delivery_pincode';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export function DeliveryPromiseWidget({
  productId,
  quantity = 1,
  className,
}: DeliveryPromiseWidgetProps) {
  const [pincode, setPincode] = useState('');
  const [savedPincode, setSavedPincode] = useState<string | null>(null);
  const [promise, setPromise] = useState<DeliveryPromiseResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [showInput, setShowInput] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem(PINCODE_STORAGE_KEY);
    if (saved && /^\d{6}$/.test(saved)) {
      setSavedPincode(saved);
      setPincode(saved);
      if (productId) {
        checkPromise(saved);
      }
    }
  }, [productId]);

  const checkPromise = async (code: string) => {
    if (!code || code.length !== 6) return;

    setLoading(true);
    try {
      const params = new URLSearchParams({ pincode: code, quantity: String(quantity) });
      if (productId) params.set('product_id', productId);

      const res = await fetch(`${API_BASE}/api/v1/storefront/delivery-promise?${params}`);
      if (!res.ok) throw new Error('Failed to check delivery promise');
      const data = await res.json();
      setPromise(data);
      if (data.serviceable !== false) {
        localStorage.setItem(PINCODE_STORAGE_KEY, code);
        setSavedPincode(code);
      }
    } catch {
      setPromise({
        product_id: productId || '',
        pincode: code,
        serviceable: false,
        message: 'Unable to check delivery promise. Please try again.',
      });
    } finally {
      setLoading(false);
      setShowInput(false);
    }
  };

  const handleCheck = () => checkPromise(pincode);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleCheck();
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
  };

  const confidenceLabel = (conf: number) => {
    if (conf >= 0.8) return { text: 'High confidence', color: 'text-green-600 bg-green-100 dark:bg-green-900/30' };
    if (conf >= 0.5) return { text: 'Moderate', color: 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30' };
    return { text: 'Estimate', color: 'text-orange-600 bg-orange-100 dark:bg-orange-900/30' };
  };

  // Prompt state
  if (!savedPincode && !showInput && !promise) {
    return (
      <div className={cn('rounded-lg border bg-card p-4', className)}>
        <button
          onClick={() => setShowInput(true)}
          className="w-full flex items-center justify-between text-left hover:bg-muted/50 -m-4 p-4 rounded-lg transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
              <Calendar className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="font-medium text-sm">AI Delivery Estimate</p>
              <p className="text-xs text-muted-foreground">Enter pincode for delivery date prediction</p>
            </div>
          </div>
          <ChevronRight className="h-5 w-5 text-muted-foreground" />
        </button>
      </div>
    );
  }

  // Input state
  if (showInput || (!promise && !loading)) {
    return (
      <div className={cn('rounded-lg border bg-card p-4', className)}>
        <div className="flex items-center gap-2 mb-3">
          <Calendar className="h-4 w-4 text-blue-600" />
          <span className="font-medium text-sm">AI Delivery Estimate</span>
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
          <Button onClick={handleCheck} disabled={loading || pincode.length !== 6} className="shrink-0">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Check'}
          </Button>
        </div>
        {savedPincode && (
          <button
            onClick={() => { setPincode(savedPincode); checkPromise(savedPincode); }}
            className="mt-2 text-xs text-primary hover:underline"
          >
            Use saved pincode: {savedPincode}
          </button>
        )}
      </div>
    );
  }

  // Loading
  if (loading) {
    return (
      <div className={cn('rounded-lg border bg-card p-4', className)}>
        <div className="flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
          <span className="text-sm text-muted-foreground">Calculating delivery estimate for {pincode}...</span>
        </div>
      </div>
    );
  }

  // Result state
  if (promise) {
    const conf = promise.confidence ? confidenceLabel(promise.confidence) : null;

    return (
      <div className={cn('rounded-lg border bg-card overflow-hidden', className)}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 bg-muted/50 border-b">
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">
              Deliver to <span className="font-semibold">{savedPincode}</span>
            </span>
          </div>
          <button
            onClick={() => { setShowInput(true); setPromise(null); }}
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            <RefreshCw className="h-3 w-3" /> Change
          </button>
        </div>

        <div className="p-4 space-y-3">
          {promise.expected_date ? (
            <>
              {/* Main delivery date */}
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center shrink-0">
                  <Truck className="h-4 w-4 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Expected delivery by</p>
                  <p className="text-lg font-semibold text-green-600">
                    {formatDate(promise.expected_date)}
                  </p>
                  {promise.earliest_date && promise.latest_date && (
                    <p className="text-xs text-muted-foreground">
                      {formatDate(promise.earliest_date)} - {formatDate(promise.latest_date)}
                    </p>
                  )}
                </div>
              </div>

              {/* Confidence + Breakdown */}
              <div className="flex items-center gap-2 flex-wrap">
                {conf && (
                  <Badge variant="outline" className={`text-xs ${conf.color}`}>
                    <Shield className="h-3 w-3 mr-1" />
                    {conf.text}
                  </Badge>
                )}
                {promise.breakdown && (
                  <span className="text-xs text-muted-foreground">
                    Processing: {promise.breakdown.processing_days || 0}d + Transit: {promise.breakdown.transit_days || 0}d
                    {promise.breakdown.buffer_days ? ` + Buffer: ${promise.breakdown.buffer_days}d` : ''}
                  </span>
                )}
              </div>

              {promise.warehouse_name && (
                <p className="text-xs text-muted-foreground">
                  Ships from: {promise.warehouse_name}
                </p>
              )}
            </>
          ) : (
            <div className="flex items-start gap-3">
              <div className="h-8 w-8 rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center shrink-0">
                <Calendar className="h-4 w-4 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  {promise.message || 'Delivery estimate not available for this pincode.'}
                </p>
                <button
                  onClick={() => { setShowInput(true); setPromise(null); }}
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

export default DeliveryPromiseWidget;
