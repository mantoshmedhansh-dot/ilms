'use client';

import { useState, useEffect, useCallback } from 'react';
import { Loader2, Star, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { reviewsApi } from '@/lib/storefront/api';
import { ReviewSummary } from './review-summary';
import { ReviewCard } from './review-card';
import { WriteReviewForm } from './write-review-form';

interface ProductReviewsProps {
  productId: string;
  productName: string;
}

type SortOption = 'recent' | 'helpful' | 'rating_high' | 'rating_low';

interface Review {
  id: string;
  rating: number;
  title?: string;
  review_text?: string;
  is_verified_purchase: boolean;
  helpful_count: number;
  created_at: string;
  customer_name: string;
  admin_response?: string;
  admin_response_at?: string;
}

interface ReviewData {
  reviews: Review[];
  summary: {
    average_rating: number;
    total_reviews: number;
    rating_distribution: Record<string, number>;
    verified_purchase_count: number;
  };
  total: number;
}

export function ProductReviews({ productId, productName }: ProductReviewsProps) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<ReviewData | null>(null);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<SortOption>('recent');
  const [ratingFilter, setRatingFilter] = useState<number | undefined>(undefined);

  const fetchReviews = useCallback(async () => {
    setLoading(true);
    try {
      const result = await reviewsApi.getProductReviews(
        productId,
        page,
        10,
        sortBy,
        ratingFilter
      );
      setData(result);
    } catch (error) {
      console.error('Failed to fetch reviews:', error);
    } finally {
      setLoading(false);
    }
  }, [productId, page, sortBy, ratingFilter]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  const handleSortChange = (value: string) => {
    setSortBy(value as SortOption);
    setPage(1);
  };

  const handleRatingFilterChange = (value: string) => {
    setRatingFilter(value === 'all' ? undefined : parseInt(value));
    setPage(1);
  };

  const handleReviewSubmitted = () => {
    // Refresh reviews after submission
    setPage(1);
    fetchReviews();
  };

  const totalPages = data ? Math.ceil(data.total / 10) : 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-2xl font-bold">Customer Reviews</h2>
        <WriteReviewForm
          productId={productId}
          productName={productName}
          onReviewSubmitted={handleReviewSubmitted}
        />
      </div>

      {loading && !data ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : data ? (
        <>
          {/* Summary */}
          {data.summary.total_reviews > 0 ? (
            <ReviewSummary
              averageRating={data.summary.average_rating}
              totalReviews={data.summary.total_reviews}
              ratingDistribution={data.summary.rating_distribution}
              verifiedPurchaseCount={data.summary.verified_purchase_count}
            />
          ) : (
            <div className="text-center py-8">
              <Star className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-lg font-medium">No reviews yet</p>
              <p className="text-muted-foreground">
                Be the first to review this product!
              </p>
            </div>
          )}

          {data.summary.total_reviews > 0 && (
            <>
              <Separator />

              {/* Filters */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Select value={sortBy} onValueChange={handleSortChange}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Sort by" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="recent">Most Recent</SelectItem>
                    <SelectItem value="helpful">Most Helpful</SelectItem>
                    <SelectItem value="rating_high">Highest Rating</SelectItem>
                    <SelectItem value="rating_low">Lowest Rating</SelectItem>
                  </SelectContent>
                </Select>

                <Select
                  value={ratingFilter?.toString() || 'all'}
                  onValueChange={handleRatingFilterChange}
                >
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <Filter className="h-4 w-4 mr-2" />
                    <SelectValue placeholder="Filter by rating" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Ratings</SelectItem>
                    <SelectItem value="5">5 Stars</SelectItem>
                    <SelectItem value="4">4 Stars</SelectItem>
                    <SelectItem value="3">3 Stars</SelectItem>
                    <SelectItem value="2">2 Stars</SelectItem>
                    <SelectItem value="1">1 Star</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Reviews List */}
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : data.reviews.length > 0 ? (
                <div className="space-y-4">
                  {data.reviews.map((review) => (
                    <ReviewCard key={review.id} review={review} />
                  ))}
                </div>
              ) : (
                <p className="text-center py-8 text-muted-foreground">
                  No reviews match your filters
                </p>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1 || loading}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground px-4">
                    Page {page} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages || loading}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </>
      ) : null}
    </div>
  );
}
