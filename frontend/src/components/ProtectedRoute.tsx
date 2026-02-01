'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useModules } from '@/hooks/useModules';

interface ProtectedRouteProps {
  moduleCode: string;
  children: React.ReactNode;
}

export function ProtectedRoute({ moduleCode, children }: ProtectedRouteProps) {
  const router = useRouter();
  const { isModuleEnabled, loading } = useModules();
  const [hasAccess, setHasAccess] = useState(false);

  useEffect(() => {
    if (!loading) {
      const enabled = isModuleEnabled(moduleCode);
      setHasAccess(enabled);

      if (!enabled) {
        // Redirect to upgrade page
        router.push('/dashboard/settings/subscriptions?upgrade=' + moduleCode);
      }
    }
  }, [loading, moduleCode, isModuleEnabled, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!hasAccess) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center max-w-md p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Module Not Available</h2>
          <p className="text-gray-600 mb-6">
            This feature requires an active subscription to the {moduleCode} module.
          </p>
          <button
            onClick={() => router.push('/dashboard/settings/subscriptions')}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
          >
            Upgrade Now
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

// Usage in page:
// export default function WMSPage() {
//   return (
//     <ProtectedRoute moduleCode="oms_fulfillment">
//       <WMSContent />
//     </ProtectedRoute>
//   );
// }
