'use client';

import { useState, useEffect } from 'react';
import {
  Package,
  AlertTriangle,
  XCircle,
  CheckCircle,
  Clock,
  Loader2,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { inventoryApi } from '@/lib/storefront/api';

interface StockStatusProps {
  productId: string;
  variantId?: string;
  showQuantity?: boolean;
  className?: string;
  // Allow passing stock info directly to avoid extra API call
  inStock?: boolean;
  stockQuantity?: number;
}

interface StockInfo {
  inStock: boolean;
  quantity: number;
  lowStock: boolean;
  message: string;
}

export default function StockStatus({
  productId,
  variantId,
  showQuantity = false,
  className = '',
  inStock: propInStock,
  stockQuantity: propStockQuantity,
}: StockStatusProps) {
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // If stock info is provided directly, use it without API call
    if (propInStock !== undefined) {
      const quantity = propStockQuantity || 0;
      const lowStockThreshold = 5;
      setStockInfo({
        inStock: propInStock,
        quantity,
        lowStock: propInStock && quantity > 0 && quantity <= lowStockThreshold,
        message: propInStock ? 'In Stock' : 'Out of Stock',
      });
      setLoading(false);
      return;
    }

    const checkStock = async () => {
      setLoading(true);
      try {
        const result = await inventoryApi.verifyStock({
          product_id: variantId || productId,
          quantity: 1,
        });

        const quantity = result.available_quantity || 0;
        const lowStockThreshold = 5;

        setStockInfo({
          inStock: result.in_stock,
          quantity,
          lowStock: result.in_stock && quantity <= lowStockThreshold,
          message: result.message || '',
        });
      } catch (error) {
        console.error('Failed to check stock:', error);
        // Default to in stock if API fails
        setStockInfo({
          inStock: true,
          quantity: 100,
          lowStock: false,
          message: 'In Stock',
        });
      } finally {
        setLoading(false);
      }
    };

    checkStock();
  }, [productId, variantId, propInStock, propStockQuantity]);

  if (loading) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Checking availability...</span>
      </div>
    );
  }

  if (!stockInfo) return null;

  // Out of stock
  if (!stockInfo.inStock) {
    return (
      <div className={`${className}`}>
        <Badge variant="secondary" className="gap-1 bg-gray-800 text-white hover:bg-gray-700">
          <XCircle className="h-3.5 w-3.5" />
          Out of Stock - Coming Soon
        </Badge>
        <p className="text-sm text-muted-foreground mt-1">
          Currently unavailable. We&apos;re restocking soon - check back later!
        </p>
      </div>
    );
  }

  // Low stock
  if (stockInfo.lowStock) {
    return (
      <div className={`${className}`}>
        <Badge className="gap-1 bg-orange-500 hover:bg-orange-600">
          <AlertTriangle className="h-3.5 w-3.5" />
          Only {stockInfo.quantity} left!
        </Badge>
        <p className="text-sm text-orange-600 mt-1 font-medium">
          Hurry! Limited stock available
        </p>
      </div>
    );
  }

  // In stock
  return (
    <div className={`${className}`}>
      <Badge variant="secondary" className="gap-1 bg-green-100 text-green-800 hover:bg-green-100">
        <CheckCircle className="h-3.5 w-3.5" />
        In Stock
      </Badge>
      {showQuantity && stockInfo.quantity > 0 && (
        <p className="text-sm text-muted-foreground mt-1">
          {stockInfo.quantity} units available
        </p>
      )}
    </div>
  );
}

// Compact version for product cards
export function StockBadge({
  inStock,
  quantity,
}: {
  inStock: boolean;
  quantity?: number;
}) {
  if (!inStock) {
    return (
      <Badge variant="destructive" className="text-xs">
        Out of Stock
      </Badge>
    );
  }

  if (quantity !== undefined && quantity <= 5) {
    return (
      <Badge className="text-xs bg-orange-500 hover:bg-orange-600">
        Only {quantity} left
      </Badge>
    );
  }

  return null; // Don't show badge for normal stock
}

// Delivery estimate component
export function DeliveryEstimate({
  pincode,
  estimateDays,
  codAvailable,
}: {
  pincode: string;
  estimateDays?: number;
  codAvailable?: boolean;
}) {
  if (!pincode) return null;

  const deliveryDate = new Date();
  if (estimateDays) {
    deliveryDate.setDate(deliveryDate.getDate() + estimateDays);
  }

  return (
    <div className="bg-muted/50 rounded-lg p-3 space-y-2">
      <div className="flex items-center gap-2 text-sm">
        <Clock className="h-4 w-4 text-primary" />
        <span>
          Delivery by{' '}
          <span className="font-medium">
            {deliveryDate.toLocaleDateString('en-IN', {
              weekday: 'short',
              day: 'numeric',
              month: 'short',
            })}
          </span>
        </span>
      </div>
      {codAvailable !== undefined && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Package className="h-4 w-4" />
          <span>
            {codAvailable
              ? 'Cash on Delivery available'
              : 'Prepaid orders only'}
          </span>
        </div>
      )}
    </div>
  );
}
