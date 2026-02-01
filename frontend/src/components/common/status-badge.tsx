import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { statusColors } from '@/config/site';

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const colorClass = statusColors[status] || 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';

  return (
    <Badge
      variant="outline"
      className={cn('border-0', colorClass, className)}
    >
      {status.replace(/_/g, ' ')}
    </Badge>
  );
}
