/**
 * Recently Viewed Products - localStorage based tracking
 *
 * Tracks the last 20 products viewed by the user for personalization
 * and easy access to previously browsed items.
 */

const STORAGE_KEY = 'd2c-recently-viewed';
const MAX_ITEMS = 20;

export interface RecentlyViewedProduct {
  id: string;
  slug: string;
  name: string;
  imageUrl?: string;
  price: number;
  mrp: number;
  viewedAt: string;
}

/**
 * Get all recently viewed products
 */
export function getRecentlyViewed(): RecentlyViewedProduct[] {
  if (typeof window === 'undefined') return [];

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    return JSON.parse(stored) as RecentlyViewedProduct[];
  } catch (error) {
    console.error('Failed to get recently viewed:', error);
    return [];
  }
}

/**
 * Add a product to recently viewed list
 * Moves to front if already exists, removes oldest if at max capacity
 */
export function addToRecentlyViewed(product: Omit<RecentlyViewedProduct, 'viewedAt'>): void {
  if (typeof window === 'undefined') return;

  try {
    const current = getRecentlyViewed();

    // Remove if already exists (will be added to front)
    const filtered = current.filter((p) => p.id !== product.id);

    // Add to front with timestamp
    const updated: RecentlyViewedProduct[] = [
      {
        ...product,
        viewedAt: new Date().toISOString(),
      },
      ...filtered,
    ].slice(0, MAX_ITEMS);

    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (error) {
    console.error('Failed to add to recently viewed:', error);
  }
}

/**
 * Remove a product from recently viewed
 */
export function removeFromRecentlyViewed(productId: string): void {
  if (typeof window === 'undefined') return;

  try {
    const current = getRecentlyViewed();
    const filtered = current.filter((p) => p.id !== productId);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  } catch (error) {
    console.error('Failed to remove from recently viewed:', error);
  }
}

/**
 * Clear all recently viewed products
 */
export function clearRecentlyViewed(): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear recently viewed:', error);
  }
}

/**
 * Get recently viewed product IDs only (for efficient checks)
 */
export function getRecentlyViewedIds(): string[] {
  return getRecentlyViewed().map((p) => p.id);
}

/**
 * Check if a product was recently viewed
 */
export function wasRecentlyViewed(productId: string): boolean {
  return getRecentlyViewedIds().includes(productId);
}
