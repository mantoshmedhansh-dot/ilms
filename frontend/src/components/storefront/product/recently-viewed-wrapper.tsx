'use client';

import RecentlyViewed from './recently-viewed';

interface RecentlyViewedWrapperProps {
  excludeProductId?: string;
  maxItems?: number;
}

/**
 * Client wrapper for RecentlyViewed component
 * Needed because RecentlyViewed uses localStorage
 */
export default function RecentlyViewedWrapper({
  excludeProductId,
  maxItems = 6,
}: RecentlyViewedWrapperProps) {
  return <RecentlyViewed excludeProductId={excludeProductId} maxItems={maxItems} />;
}
