'use client';

import { useEffect } from 'react';
import { initServiceability } from '@/lib/storefront/serviceability-store';

/**
 * Serviceability Provider
 *
 * Initializes edge-based serviceability data on app startup.
 * This enables instant pincode checks without API calls.
 *
 * Place this in the storefront layout to ensure data is loaded
 * before any checkout/delivery checks.
 */
export function ServiceabilityProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initialize serviceability data from edge/localStorage
    initServiceability().catch((error) => {
      console.warn('[ServiceabilityProvider] Init failed:', error);
      // App continues to work - will fallback to API calls
    });
  }, []);

  return <>{children}</>;
}

export default ServiceabilityProvider;
