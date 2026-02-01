/**
 * Search History - localStorage based tracking
 *
 * Tracks the last 10 search queries for quick access
 * and personalized search experience.
 */

const STORAGE_KEY = 'd2c-search-history';
const MAX_ITEMS = 10;

export interface SearchHistoryItem {
  query: string;
  timestamp: string;
}

/**
 * Get all recent search queries
 */
export function getSearchHistory(): SearchHistoryItem[] {
  if (typeof window === 'undefined') return [];

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    return JSON.parse(stored) as SearchHistoryItem[];
  } catch (error) {
    console.error('Failed to get search history:', error);
    return [];
  }
}

/**
 * Add a search query to history
 * Moves to front if already exists, removes oldest if at max capacity
 */
export function addToSearchHistory(query: string): void {
  if (typeof window === 'undefined') return;

  const trimmedQuery = query.trim().toLowerCase();
  if (!trimmedQuery || trimmedQuery.length < 2) return;

  try {
    const current = getSearchHistory();

    // Remove if already exists (will be added to front)
    const filtered = current.filter(
      (item) => item.query.toLowerCase() !== trimmedQuery
    );

    // Add to front with timestamp
    const updated: SearchHistoryItem[] = [
      {
        query: query.trim(),
        timestamp: new Date().toISOString(),
      },
      ...filtered,
    ].slice(0, MAX_ITEMS);

    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (error) {
    console.error('Failed to add to search history:', error);
  }
}

/**
 * Remove a search query from history
 */
export function removeFromSearchHistory(query: string): void {
  if (typeof window === 'undefined') return;

  try {
    const current = getSearchHistory();
    const filtered = current.filter(
      (item) => item.query.toLowerCase() !== query.toLowerCase()
    );
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  } catch (error) {
    console.error('Failed to remove from search history:', error);
  }
}

/**
 * Clear all search history
 */
export function clearSearchHistory(): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear search history:', error);
  }
}

/**
 * Get recent search queries as strings only
 */
export function getRecentSearchQueries(): string[] {
  return getSearchHistory().map((item) => item.query);
}
