'use client';

import { Star } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface ReviewSummaryProps {
  averageRating: number;
  totalReviews: number;
  ratingDistribution: Record<string, number>;
  verifiedPurchaseCount: number;
}

export function ReviewSummary({
  averageRating,
  totalReviews,
  ratingDistribution,
  verifiedPurchaseCount,
}: ReviewSummaryProps) {
  const renderStars = (rating: number, size: 'sm' | 'lg' = 'sm') => {
    const sizeClass = size === 'lg' ? 'h-6 w-6' : 'h-4 w-4';
    return (
      <div className="flex gap-0.5" role="img" aria-label={`${rating.toFixed(1)} out of 5 stars`}>
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`${sizeClass} ${
              star <= Math.round(rating)
                ? 'fill-yellow-400 text-yellow-400'
                : 'fill-gray-200 text-gray-200'
            }`}
            aria-hidden="true"
          />
        ))}
      </div>
    );
  };

  const getPercentage = (count: number) => {
    if (totalReviews === 0) return 0;
    return Math.round((count / totalReviews) * 100);
  };

  return (
    <div className="flex flex-col md:flex-row gap-8">
      {/* Average Rating */}
      <div className="text-center md:text-left">
        <div className="text-5xl font-bold text-primary">{averageRating.toFixed(1)}</div>
        <div className="mt-2">{renderStars(averageRating, 'lg')}</div>
        <p className="text-sm text-muted-foreground mt-2">
          Based on {totalReviews} review{totalReviews !== 1 ? 's' : ''}
        </p>
        {verifiedPurchaseCount > 0 && (
          <p className="text-xs text-green-600 mt-1">
            {verifiedPurchaseCount} verified purchase{verifiedPurchaseCount !== 1 ? 's' : ''}
          </p>
        )}
      </div>

      {/* Rating Distribution */}
      <div className="flex-1 space-y-2">
        {[5, 4, 3, 2, 1].map((rating) => {
          const count = ratingDistribution[rating.toString()] || 0;
          const percentage = getPercentage(count);
          return (
            <div key={rating} className="flex items-center gap-3" aria-label={`${rating} star reviews: ${count}`}>
              <div className="flex items-center gap-1 w-12">
                <span className="text-sm">{rating}</span>
                <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" aria-hidden="true" />
              </div>
              <Progress value={percentage} className="flex-1 h-2" />
              <span className="text-sm text-muted-foreground w-12 text-right">
                {count}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
