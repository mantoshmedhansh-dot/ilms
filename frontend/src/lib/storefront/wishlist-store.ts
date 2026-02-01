import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi } from './api';
import { useAuthStore } from './auth-store';

export interface WishlistProduct {
  id: string;
  productId: string;
  productName: string;
  productSlug: string;
  productImage?: string;
  productPrice: number;
  productMrp: number;
  variantId?: string;
  variantName?: string;
  priceWhenAdded?: number;
  isInStock: boolean;
  priceDropped: boolean;
  createdAt: string;
}

interface WishlistState {
  items: WishlistProduct[];
  isLoading: boolean;
  lastSynced: string | null;

  // Actions
  fetchWishlist: () => Promise<void>;
  addToWishlist: (productId: string, variantId?: string) => Promise<boolean>;
  removeFromWishlist: (productId: string) => Promise<boolean>;
  isInWishlist: (productId: string) => boolean;
  clearWishlist: () => void;
}

export const useWishlistStore = create<WishlistState>()(
  persist(
    (set, get) => ({
      items: [],
      isLoading: false,
      lastSynced: null,

      fetchWishlist: async () => {
        const { isAuthenticated } = useAuthStore.getState();
        if (!isAuthenticated) {
          set({ items: [], isLoading: false });
          return;
        }

        try {
          set({ isLoading: true });
          const response = await authApi.getWishlist();
          set({
            items: response.items.map((item) => ({
              id: item.id,
              productId: item.product_id,
              productName: item.product_name,
              productSlug: item.product_slug,
              productImage: item.product_image,
              productPrice: item.product_price,
              productMrp: item.product_mrp,
              variantId: item.variant_id,
              variantName: item.variant_name,
              priceWhenAdded: item.price_when_added,
              isInStock: item.is_in_stock,
              priceDropped: item.price_dropped,
              createdAt: item.created_at,
            })),
            lastSynced: new Date().toISOString(),
            isLoading: false,
          });
        } catch (error) {
          console.error('Failed to fetch wishlist:', error);
          set({ isLoading: false });
        }
      },

      addToWishlist: async (productId: string, variantId?: string): Promise<boolean> => {
        const { isAuthenticated } = useAuthStore.getState();
        if (!isAuthenticated) {
          return false;
        }

        try {
          const response = await authApi.addToWishlist(productId, variantId);
          const newItem: WishlistProduct = {
            id: response.id,
            productId: response.product_id,
            productName: response.product_name,
            productSlug: response.product_slug,
            productImage: response.product_image,
            productPrice: response.product_price,
            productMrp: response.product_mrp,
            isInStock: true,
            priceDropped: false,
            createdAt: response.created_at,
          };

          set((state) => ({
            items: [newItem, ...state.items],
          }));
          return true;
        } catch (error) {
          console.error('Failed to add to wishlist:', error);
          return false;
        }
      },

      removeFromWishlist: async (productId: string): Promise<boolean> => {
        const { isAuthenticated } = useAuthStore.getState();
        if (!isAuthenticated) {
          return false;
        }

        try {
          await authApi.removeFromWishlist(productId);
          set((state) => ({
            items: state.items.filter((item) => item.productId !== productId),
          }));
          return true;
        } catch (error) {
          console.error('Failed to remove from wishlist:', error);
          return false;
        }
      },

      isInWishlist: (productId: string): boolean => {
        return get().items.some((item) => item.productId === productId);
      },

      clearWishlist: () => {
        set({ items: [], lastSynced: null });
      },
    }),
    {
      name: 'd2c-wishlist',
      partialize: (state) => ({
        items: state.items,
        lastSynced: state.lastSynced,
      }),
    }
  )
);

// Selector hooks for convenience
export const useWishlistItems = () => useWishlistStore((state) => state.items);
export const useWishlistCount = () => useWishlistStore((state) => state.items.length);
export const useIsInWishlist = (productId: string) =>
  useWishlistStore((state) => state.items.some((item) => item.productId === productId));
