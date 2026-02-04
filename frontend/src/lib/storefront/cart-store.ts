'use client';

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { StorefrontProduct, ProductVariant, CartItem } from '@/types/storefront';
import { abandonedCartApi, CartSyncRequest, inventoryApi, productsApi } from './api';
import { toast } from 'sonner';

// Get partner referral code from httpOnly cookie via API
// This is secure because the cookie cannot be read by malicious JS (XSS protection)
export const getPartnerReferralCode = async (): Promise<string | null> => {
  if (typeof window === 'undefined') return null;
  try {
    const response = await fetch('/api/referral');
    if (!response.ok) return null;
    const data = await response.json();
    return data.partner_code || null;
  } catch {
    return null;
  }
};

// Clear partner referral cookie (after order placed) via API
export const clearPartnerReferralCode = async (): Promise<void> => {
  if (typeof window === 'undefined') return;
  try {
    await fetch('/api/referral', { method: 'DELETE' });
  } catch {
    // Silently ignore errors when clearing cookie
  }
};

// Generate a unique session ID for cart tracking
const generateSessionId = (): string => {
  return `sess_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
};

// Get or create session ID
const getSessionId = (): string => {
  if (typeof window === 'undefined') return '';
  let sessionId = sessionStorage.getItem('cart_session_id');
  if (!sessionId) {
    sessionId = generateSessionId();
    sessionStorage.setItem('cart_session_id', sessionId);
  }
  return sessionId;
};

// Get device type
const getDeviceType = (): string => {
  if (typeof window === 'undefined') return 'unknown';
  const width = window.innerWidth;
  if (width < 768) return 'mobile';
  if (width < 1024) return 'tablet';
  return 'desktop';
};

// Debounce sync to avoid too many API calls
let syncTimeout: NodeJS.Timeout | null = null;
const SYNC_DEBOUNCE_MS = 2000; // Sync after 2 seconds of inactivity

interface CartStore {
  items: CartItem[];
  isOpen: boolean;
  lastSyncedAt: number | null;
  recoveryToken: string | null;
  checkoutStep: string | null;
  couponCode: string | null;
  discountAmount: number;

  // Actions
  addItem: (product: StorefrontProduct, quantity?: number, variant?: ProductVariant) => void;
  removeItem: (itemId: string) => void;
  updateQuantity: (itemId: string, quantity: number) => void;
  clearCart: () => void;
  toggleCart: () => void;
  openCart: () => void;
  closeCart: () => void;
  setCheckoutStep: (step: string) => void;
  setCoupon: (code: string | null, discount: number) => void;

  // Sync actions
  syncToBackend: (additionalData?: Partial<CartSyncRequest>) => Promise<void>;
  recoverCart: (token: string) => Promise<boolean>;
  markAsConverted: (orderId: string) => Promise<void>;

  // Computed
  getItemCount: () => number;
  getSubtotal: () => number;
  getTax: () => number;
  getShipping: () => number;
  getTotal: () => number;
  getItemById: (itemId: string) => CartItem | undefined;
  isInCart: (productId: string, variantId?: string) => boolean;
}

const generateItemId = (productId: string, variantId?: string): string => {
  return variantId ? `${productId}-${variantId}` : productId;
};

const getItemPrice = (product: StorefrontProduct, variant?: ProductVariant): number => {
  if (variant?.selling_price) {
    return variant.selling_price;
  }
  return product.selling_price;
};

// Trigger debounced sync
const triggerSync = (get: () => CartStore) => {
  if (syncTimeout) {
    clearTimeout(syncTimeout);
  }
  syncTimeout = setTimeout(() => {
    get().syncToBackend();
  }, SYNC_DEBOUNCE_MS);
};

// Validate cart items after restore from localStorage
interface ValidationResult {
  validItems: CartItem[];
  invalidItems: CartItem[];
  priceChanges: { item: CartItem; oldPrice: number; newPrice: number }[];
}

async function validateCartItems(items: CartItem[]): Promise<ValidationResult> {
  const validItems: CartItem[] = [];
  const invalidItems: CartItem[] = [];
  const priceChanges: { item: CartItem; oldPrice: number; newPrice: number }[] = [];

  // Skip validation if no items
  if (items.length === 0) {
    return { validItems: [], invalidItems: [], priceChanges: [] };
  }

  try {
    // Verify stock availability in bulk
    const stockRequests = items.map((item) => ({
      product_id: item.product.id,
      variant_id: item.variant?.id,
      quantity: item.quantity,
    }));

    const stockResults = await inventoryApi.verifyStockBulk(stockRequests);
    const stockMap = new Map(stockResults.map((r) => [r.product_id, r]));

    // Get latest product prices
    const productIds = [...new Set(items.map((item) => item.product.id))];
    const productPrices = new Map<string, number>();

    // Fetch current prices for all products
    for (const productId of productIds) {
      try {
        const product = await productsApi.getBySlug(
          items.find((i) => i.product.id === productId)?.product.slug || productId
        );
        if (product) {
          productPrices.set(productId, product.selling_price);
        }
      } catch {
        // If product not found, mark for removal
        productPrices.set(productId, -1);
      }
    }

    // Validate each item
    for (const item of items) {
      const stockResult = stockMap.get(item.product.id);
      const currentPrice = productPrices.get(item.product.id);

      // Check if product is unavailable
      if (currentPrice === -1) {
        invalidItems.push(item);
        continue;
      }

      // Check if out of stock
      if (stockResult && !stockResult.in_stock) {
        invalidItems.push(item);
        continue;
      }

      // Check for price changes (more than 1% difference)
      if (currentPrice && Math.abs(currentPrice - item.price) > item.price * 0.01) {
        priceChanges.push({
          item,
          oldPrice: item.price,
          newPrice: currentPrice,
        });
        // Update item with new price
        validItems.push({
          ...item,
          price: currentPrice,
          product: { ...item.product, selling_price: currentPrice },
        });
      } else {
        // Item is valid with unchanged price
        validItems.push(item);
      }
    }
  } catch (error) {
    console.warn('Cart validation error:', error);
    // On error, keep all items (fail open)
    return { validItems: items, invalidItems: [], priceChanges: [] };
  }

  return { validItems, invalidItems, priceChanges };
}

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],
      isOpen: false,
      lastSyncedAt: null,
      recoveryToken: null,
      checkoutStep: null,
      couponCode: null,
      discountAmount: 0,

      addItem: (product, quantity = 1, variant) => {
        const itemId = generateItemId(product.id, variant?.id);
        const items = get().items;
        const existingItem = items.find((item) => item.id === itemId);

        if (existingItem) {
          // Update quantity if item exists
          set({
            items: items.map((item) =>
              item.id === itemId
                ? { ...item, quantity: item.quantity + quantity }
                : item
            ),
          });
        } else {
          // Add new item
          const newItem: CartItem = {
            id: itemId,
            product,
            variant,
            quantity,
            price: getItemPrice(product, variant),
          };
          set({ items: [...items, newItem] });
        }

        // Open cart drawer
        set({ isOpen: true });

        // Trigger sync
        triggerSync(get);
      },

      removeItem: (itemId) => {
        set({ items: get().items.filter((item) => item.id !== itemId) });
        triggerSync(get);
      },

      updateQuantity: (itemId, quantity) => {
        if (quantity <= 0) {
          get().removeItem(itemId);
          return;
        }

        set({
          items: get().items.map((item) =>
            item.id === itemId ? { ...item, quantity } : item
          ),
        });
        triggerSync(get);
      },

      clearCart: () => {
        set({ items: [], couponCode: null, discountAmount: 0, checkoutStep: null });
        triggerSync(get);
      },

      toggleCart: () => {
        set({ isOpen: !get().isOpen });
      },

      openCart: () => {
        set({ isOpen: true });
      },

      closeCart: () => {
        set({ isOpen: false });
      },

      setCheckoutStep: (step) => {
        set({ checkoutStep: step });
        // Sync immediately on checkout step change
        get().syncToBackend();
      },

      setCoupon: (code, discount) => {
        set({ couponCode: code, discountAmount: discount });
        triggerSync(get);
      },

      syncToBackend: async (additionalData) => {
        const state = get();
        const sessionId = getSessionId();

        if (!sessionId) return;

        try {
          const subtotal = state.getSubtotal();
          const tax = state.getTax();
          const shipping = state.getShipping();

          const syncRequest: CartSyncRequest = {
            session_id: sessionId,
            items: state.items.map(item => ({
              product_id: item.product.id,
              product_name: item.product.name,
              sku: item.product.sku || '',
              quantity: item.quantity,
              price: item.price,
              variant_id: item.variant?.id,
              variant_name: item.variant?.name,
              image_url: item.product.images?.[0]?.image_url || item.product.images?.[0]?.thumbnail_url,
            })),
            subtotal,
            tax_amount: tax,
            shipping_amount: shipping,
            discount_amount: state.discountAmount,
            total_amount: subtotal + tax + shipping - state.discountAmount,
            coupon_code: state.couponCode || undefined,
            checkout_step: state.checkoutStep || undefined,
            user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
            device_type: getDeviceType(),
            referrer_url: typeof document !== 'undefined' ? document.referrer : undefined,
            ...additionalData,
          };

          // Add UTM params from URL
          if (typeof window !== 'undefined') {
            const params = new URLSearchParams(window.location.search);
            if (params.get('utm_source')) syncRequest.utm_source = params.get('utm_source') || undefined;
            if (params.get('utm_medium')) syncRequest.utm_medium = params.get('utm_medium') || undefined;
            if (params.get('utm_campaign')) syncRequest.utm_campaign = params.get('utm_campaign') || undefined;
          }

          const response = await abandonedCartApi.sync(syncRequest);

          set({
            lastSyncedAt: Date.now(),
            recoveryToken: response.recovery_token || null,
          });
        } catch (error) {
          // Silently fail - cart persistence is best effort
          console.warn('Failed to sync cart:', error);
        }
      },

      recoverCart: async (token) => {
        try {
          const response = await abandonedCartApi.recover(token);

          // We need to fetch full product data for the recovered items
          // For now, we'll create simplified cart items
          // In production, you'd fetch the full product details
          const recoveredItems: CartItem[] = response.items.map(item => ({
            id: item.variant_id ? `${item.product_id}-${item.variant_id}` : item.product_id,
            product: {
              id: item.product_id,
              name: item.product_name,
              slug: item.product_id, // Use product_id as slug for recovered items
              sku: item.sku,
              selling_price: item.price,
              mrp: item.price,
              is_active: true,
              images: item.image_url ? [{
                id: '1',
                image_url: item.image_url,
                is_primary: true,
                sort_order: 0
              }] : [],
            } as StorefrontProduct,
            variant: item.variant_id ? {
              id: item.variant_id,
              name: item.variant_name || '',
              sku: item.sku,
            } as ProductVariant : undefined,
            quantity: item.quantity,
            price: item.price,
          }));

          set({
            items: recoveredItems,
            couponCode: response.coupon_code || null,
          });

          return true;
        } catch (error) {
          console.error('Failed to recover cart:', error);
          return false;
        }
      },

      markAsConverted: async (orderId) => {
        const sessionId = getSessionId();
        if (!sessionId) return;

        try {
          await abandonedCartApi.markConverted(sessionId, orderId);
        } catch (error) {
          console.warn('Failed to mark cart as converted:', error);
        }
      },

      getItemCount: () => {
        return get().items.reduce((total, item) => total + item.quantity, 0);
      },

      getSubtotal: () => {
        return get().items.reduce(
          (total, item) => total + item.price * item.quantity,
          0
        );
      },

      getTax: () => {
        // Calculate GST (assuming 18% average)
        const subtotal = get().getSubtotal();
        return Math.round(subtotal * 0.18);
      },

      getShipping: () => {
        const subtotal = get().getSubtotal();
        // Free shipping over ₹999
        return subtotal >= 999 ? 0 : 99;
      },

      getTotal: () => {
        const state = get();
        return state.getSubtotal() + state.getTax() + state.getShipping() - state.discountAmount;
      },

      getItemById: (itemId) => {
        return get().items.find((item) => item.id === itemId);
      },

      isInCart: (productId, variantId) => {
        const itemId = generateItemId(productId, variantId);
        return get().items.some((item) => item.id === itemId);
      },
    }),
    {
      name: 'ilms-cart',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        items: state.items,
        couponCode: state.couponCode,
        discountAmount: state.discountAmount,
      }),
      onRehydrateStorage: () => (state) => {
        // Validate cart items after restore from localStorage
        if (state && state.items.length > 0) {
          validateCartItems(state.items).then(({ validItems, invalidItems, priceChanges }) => {
            if (invalidItems.length > 0 || priceChanges.length > 0) {
              // Update cart with valid items only
              useCartStore.setState({ items: validItems });

              // Notify user about removed items
              if (invalidItems.length > 0) {
                toast.warning(
                  `${invalidItems.length} item(s) removed from cart (no longer available)`,
                  { duration: 5000 }
                );
              }

              // Notify about price changes
              if (priceChanges.length > 0) {
                toast.info(
                  `Prices updated for ${priceChanges.length} item(s)`,
                  { duration: 5000 }
                );
              }
            }
          }).catch((error) => {
            console.warn('Cart validation failed:', error);
          });
        }
      },
    }
  )
);

// Helper hook for cart summary
export const useCartSummary = () => {
  const items = useCartStore((state) => state.items);
  const getSubtotal = useCartStore((state) => state.getSubtotal);
  const getTax = useCartStore((state) => state.getTax);
  const getShipping = useCartStore((state) => state.getShipping);
  const getTotal = useCartStore((state) => state.getTotal);
  const getItemCount = useCartStore((state) => state.getItemCount);

  return {
    items,
    itemCount: getItemCount(),
    subtotal: getSubtotal(),
    tax: getTax(),
    shipping: getShipping(),
    total: getTotal(),
  };
};
