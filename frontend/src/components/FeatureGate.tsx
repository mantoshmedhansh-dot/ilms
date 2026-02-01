'use client';

import { useModules } from '@/hooks/useModules';
import { ReactNode } from 'react';

interface FeatureGateProps {
  moduleCode: string;
  children: ReactNode;
  fallback?: ReactNode;
}

export function FeatureGate({ moduleCode, children, fallback }: FeatureGateProps) {
  const { isModuleEnabled, loading } = useModules();

  if (loading) {
    return null;
  }

  if (!isModuleEnabled(moduleCode)) {
    return fallback ? <>{fallback}</> : null;
  }

  return <>{children}</>;
}

// Usage example:
// <FeatureGate moduleCode="scm_ai">
//   <AdvancedForecastingChart />
// </FeatureGate>
//
// Or with fallback:
// <FeatureGate
//   moduleCode="finance"
//   fallback={<UpgradePrompt module="Finance & Accounting" />}
// >
//   <FinancialDashboard />
// </FeatureGate>
