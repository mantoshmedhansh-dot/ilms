'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

const statusConfig: Record<string, { label: string; className: string }> = {
  active: {
    label: 'Active',
    className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  },
  pending: {
    label: 'Pending',
    className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  },
  pending_setup: {
    label: 'Pending Setup',
    className: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  },
  suspended: {
    label: 'Suspended',
    className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  },
  cancelled: {
    label: 'Cancelled',
    className: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
  },
};

interface TenantStatusBadgeProps {
  status: string;
}

export function TenantStatusBadge({ status }: TenantStatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.pending;

  return (
    <Badge variant="secondary" className={cn('font-medium', config.className)}>
      {config.label}
    </Badge>
  );
}
