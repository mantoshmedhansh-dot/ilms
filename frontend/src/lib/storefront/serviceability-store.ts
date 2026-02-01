/**
 * Edge-Based Serviceability Store
 *
 * This module provides near-instant pincode serviceability checks by:
 * 1. Loading all serviceability data from edge/CDN on app init
 * 2. Storing in localStorage for offline/instant access
 * 3. Falling back to API only when edge data unavailable
 *
 * Performance:
 * - Edge data: <10ms (preloaded)
 * - API fallback: 50-500ms (only when edge unavailable)
 *
 * Usage:
 *   import { initServiceability, checkServiceability } from '@/lib/storefront/serviceability-store';
 *
 *   // On app init (layout.tsx or _app.tsx)
 *   await initServiceability();
 *
 *   // On pincode check (instant)
 *   const result = checkServiceability('110001');
 */

const STORAGE_KEY = 'aq_serviceability';
const VERSION_KEY = 'aq_serviceability_v';
const LAST_SYNC_KEY = 'aq_serviceability_sync';

// Sync interval: 6 hours (in milliseconds)
const SYNC_INTERVAL = 6 * 60 * 60 * 1000;

// API URL for edge export
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://aquapurite-erp-api.onrender.com';
const EDGE_EXPORT_URL = `${API_BASE}/api/v1/serviceability/export/edge`;

// In-memory cache for fastest access
let memoryCache: ServiceabilityIndex | null = null;

/**
 * Serviceability data structure (compressed for storage efficiency)
 *
 * Data is AGGREGATED across all warehouses serving a pincode:
 * - Serviceable if ANY warehouse can deliver
 * - Days = fastest (MIN across warehouses)
 * - Cost = cheapest (MIN across warehouses)
 * - COD = true if ANY warehouse supports it
 * - w = warehouse count (enables hopping if primary out of stock)
 */
interface ServiceabilityEntry {
  s: boolean;    // serviceable
  c: boolean;    // cod_available (from ANY warehouse)
  p: boolean;    // prepaid_available (from ANY warehouse)
  d: number;     // estimated_days (fastest/MIN)
  $: number;     // shipping_cost (cheapest/MIN)
  z: string;     // zone (L/M/R/N)
  w?: number;    // warehouse count (for hopping capability)
  city: string;
  state: string;
}

interface ServiceabilityIndex {
  v: string;     // version (ISO timestamp)
  n: number;     // total count
  p: Record<string, ServiceabilityEntry>;  // pincode -> data
  z: Record<string, number>;  // zone counts
}

/**
 * Expanded result returned to consumers
 */
export interface ServiceabilityResult {
  serviceable: boolean;
  cod_available: boolean;
  prepaid_available: boolean;
  estimated_days: number | null;
  shipping_cost: number;
  zone: string | null;
  city: string | null;
  state: string | null;
  warehouse_count: number;  // Number of warehouses that can serve (enables hopping)
  source: 'memory' | 'localStorage' | 'api' | 'default';
}

const ZONE_MAP: Record<string, string> = {
  L: 'LOCAL',
  M: 'METRO',
  R: 'REGIONAL',
  N: 'NATIONAL',
};

/**
 * Initialize serviceability data.
 * Call this once on app startup (e.g., in layout.tsx).
 *
 * - Checks if localStorage data is fresh (< 6 hours old)
 * - If stale or missing, fetches from edge API
 * - Stores in both localStorage and memory for instant access
 */
export async function initServiceability(): Promise<void> {
  // First, try to load from localStorage into memory
  loadFromStorage();

  // Check if we need to sync
  const shouldSync = checkIfSyncNeeded();

  if (shouldSync) {
    try {
      await syncFromEdge();
    } catch (error) {
      console.warn('[Serviceability] Edge sync failed, using cached data:', error);
      // Continue with cached data if available
    }
  }
}

/**
 * Check if sync is needed based on last sync time
 */
function checkIfSyncNeeded(): boolean {
  if (typeof window === 'undefined') return false;

  try {
    const lastSync = localStorage.getItem(LAST_SYNC_KEY);
    if (!lastSync) return true;

    const lastSyncTime = parseInt(lastSync, 10);
    const now = Date.now();

    return now - lastSyncTime > SYNC_INTERVAL;
  } catch {
    return true;
  }
}

/**
 * Load serviceability data from localStorage into memory
 */
function loadFromStorage(): void {
  if (typeof window === 'undefined') return;

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      memoryCache = JSON.parse(stored);
    }
  } catch (error) {
    console.warn('[Serviceability] Failed to load from localStorage:', error);
  }
}

/**
 * Sync serviceability data from edge API
 */
async function syncFromEdge(): Promise<void> {
  const response = await fetch(EDGE_EXPORT_URL, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    // Use next.js revalidate for edge caching
    next: { revalidate: 3600 },
  } as RequestInit);

  if (!response.ok) {
    throw new Error(`Edge sync failed: ${response.status}`);
  }

  const data: ServiceabilityIndex = await response.json();

  // Update memory cache
  memoryCache = data;

  // Persist to localStorage
  if (typeof window !== 'undefined') {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      localStorage.setItem(VERSION_KEY, data.v);
      localStorage.setItem(LAST_SYNC_KEY, Date.now().toString());
    } catch (error) {
      console.warn('[Serviceability] Failed to save to localStorage:', error);
    }
  }

  console.log(`[Serviceability] Synced ${data.n} pincodes from edge`);
}

/**
 * Check serviceability for a pincode (INSTANT - no API call)
 *
 * @param pincode - 6-digit pincode
 * @returns ServiceabilityResult with delivery info
 */
export function checkServiceability(pincode: string): ServiceabilityResult {
  // Normalize pincode
  const normalizedPincode = pincode?.toString().trim();

  // Default result for non-serviceable
  const defaultResult: ServiceabilityResult = {
    serviceable: false,
    cod_available: false,
    prepaid_available: false,
    estimated_days: null,
    shipping_cost: 0,
    zone: null,
    city: null,
    state: null,
    warehouse_count: 0,
    source: 'default',
  };

  if (!normalizedPincode || normalizedPincode.length !== 6) {
    return defaultResult;
  }

  // Try memory cache first (fastest)
  if (memoryCache?.p?.[normalizedPincode]) {
    return expandEntry(memoryCache.p[normalizedPincode], 'memory');
  }

  // Try localStorage if memory cache doesn't have it
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const data: ServiceabilityIndex = JSON.parse(stored);
        if (data.p?.[normalizedPincode]) {
          // Update memory cache for next time
          memoryCache = data;
          return expandEntry(data.p[normalizedPincode], 'localStorage');
        }
      }
    } catch {
      // Ignore localStorage errors
    }
  }

  // Not found in edge data - return not serviceable
  return defaultResult;
}

/**
 * Check serviceability with API fallback
 * Use this when you need guaranteed fresh data
 */
export async function checkServiceabilityWithFallback(pincode: string): Promise<ServiceabilityResult> {
  // First try edge data
  const edgeResult = checkServiceability(pincode);
  if (edgeResult.serviceable) {
    return edgeResult;
  }

  // Fallback to API for non-cached pincodes
  try {
    const response = await fetch(`${API_BASE}/api/v1/serviceability/check/${pincode}`);
    if (response.ok) {
      const data = await response.json();
      return {
        serviceable: data.is_serviceable,
        cod_available: data.cod_available,
        prepaid_available: data.prepaid_available,
        estimated_days: data.estimated_delivery_days,
        shipping_cost: data.minimum_shipping_cost || 0,
        zone: data.zone,
        city: data.city,
        state: data.state,
        warehouse_count: data.warehouse_options?.length || 1,  // API returns warehouse options
        source: 'api',
      };
    }
  } catch (error) {
    console.warn('[Serviceability] API fallback failed:', error);
  }

  return { ...edgeResult, source: 'default' };
}

/**
 * Expand compressed entry to full result
 */
function expandEntry(entry: ServiceabilityEntry, source: 'memory' | 'localStorage'): ServiceabilityResult {
  return {
    serviceable: entry.s,
    cod_available: entry.c,
    prepaid_available: entry.p,
    estimated_days: entry.d,
    shipping_cost: entry.$,
    zone: ZONE_MAP[entry.z] || entry.z,
    city: entry.city,
    state: entry.state,
    warehouse_count: entry.w || 1,  // At least 1 warehouse if serviceable
    source,
  };
}

/**
 * Force refresh serviceability data
 * Call this after admin updates serviceability in ERP
 */
export async function refreshServiceability(): Promise<void> {
  // Clear last sync to force refresh
  if (typeof window !== 'undefined') {
    localStorage.removeItem(LAST_SYNC_KEY);
  }
  await initServiceability();
}

/**
 * Get serviceability stats (for debugging)
 */
export function getServiceabilityStats(): {
  loaded: boolean;
  totalPincodes: number;
  version: string | null;
  lastSync: Date | null;
  zones: Record<string, number>;
} {
  return {
    loaded: !!memoryCache,
    totalPincodes: memoryCache?.n || 0,
    version: memoryCache?.v || null,
    lastSync: typeof window !== 'undefined'
      ? new Date(parseInt(localStorage.getItem(LAST_SYNC_KEY) || '0', 10))
      : null,
    zones: memoryCache?.z || {},
  };
}

/**
 * Preload serviceability for SSR/SSG
 * Use in getStaticProps or getServerSideProps
 */
export async function preloadServiceability(): Promise<ServiceabilityIndex | null> {
  try {
    const response = await fetch(EDGE_EXPORT_URL);
    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.error('[Serviceability] Preload failed:', error);
  }
  return null;
}
