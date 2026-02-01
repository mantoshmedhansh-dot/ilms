'use client';

import dynamic from 'next/dynamic';

// Dynamically import CompareBar with no SSR to avoid hydration issues
const CompareBar = dynamic(() => import('./compare-bar'), {
  ssr: false,
});

export default function CompareBarWrapper() {
  return <CompareBar />;
}
