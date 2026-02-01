import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface CompareProduct {
  id: string;
  name: string;
  slug: string;
  image?: string;
  price: number;
  mrp: number;
  category?: string;
  brand?: string;
}

interface CompareState {
  items: CompareProduct[];
  maxItems: number;

  // Actions
  addToCompare: (product: CompareProduct) => boolean;
  removeFromCompare: (productId: string) => void;
  clearCompare: () => void;
  isInCompare: (productId: string) => boolean;
  canAddMore: () => boolean;
}

export const useCompareStore = create<CompareState>()(
  persist(
    (set, get) => ({
      items: [],
      maxItems: 4, // Maximum products that can be compared at once

      addToCompare: (product: CompareProduct): boolean => {
        const state = get();

        // Check if already in compare
        if (state.items.some((item) => item.id === product.id)) {
          return false;
        }

        // Check if max limit reached
        if (state.items.length >= state.maxItems) {
          return false;
        }

        set((state) => ({
          items: [...state.items, product],
        }));
        return true;
      },

      removeFromCompare: (productId: string) => {
        set((state) => ({
          items: state.items.filter((item) => item.id !== productId),
        }));
      },

      clearCompare: () => {
        set({ items: [] });
      },

      isInCompare: (productId: string): boolean => {
        return get().items.some((item) => item.id === productId);
      },

      canAddMore: (): boolean => {
        return get().items.length < get().maxItems;
      },
    }),
    {
      name: 'd2c-compare',
      partialize: (state) => ({
        items: state.items,
      }),
    }
  )
);

// Selector hooks for convenience
export const useCompareItems = () => useCompareStore((state) => state.items);
export const useCompareCount = () => useCompareStore((state) => state.items.length);
export const useIsInCompare = (productId: string) =>
  useCompareStore((state) => state.items.some((item) => item.id === productId));
export const useCanAddToCompare = () =>
  useCompareStore((state) => state.items.length < state.maxItems);
