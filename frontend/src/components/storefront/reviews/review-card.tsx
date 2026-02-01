'use client';

import { useState } from 'react';
import { Star, ThumbsUp, CheckCircle, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { toast } from 'sonner';
import { reviewsApi } from '@/lib/storefront/api';
import { useIsAuthenticated } from '@/lib/storefront/auth-store';

interface ReviewCardProps {
  review: {
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
  };
}

export function ReviewCard({ review }: ReviewCardProps) {
  const isAuthenticated = useIsAuthenticated();
  const [helpfulCount, setHelpfulCount] = useState(review.helpful_count);
  const [hasVoted, setHasVoted] = useState(false);

  const handleHelpfulVote = async (isHelpful: boolean) => {
    if (!isAuthenticated) {
      toast.error('Please login to vote');
      return;
    }

    try {
      await reviewsApi.voteHelpful(review.id, isHelpful);
      if (isHelpful) {
        setHelpfulCount((prev) => prev + 1);
      }
      setHasVoted(true);
      toast.success('Thanks for your feedback!');
    } catch (error: any) {
      if (error.response?.status === 400) {
        toast.error(error.response.data.detail || 'Unable to vote');
      } else {
        toast.error('Failed to submit vote');
      }
    }
  };

  const renderStars = (rating: number) => (
    <div className="flex gap-0.5" role="img" aria-label={`Rated ${rating} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={`h-4 w-4 ${
            star <= rating
              ? 'fill-yellow-400 text-yellow-400'
              : 'fill-gray-200 text-gray-200'
          }`}
          aria-hidden="true"
        />
      ))}
    </div>
  );

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <Card>
      <CardContent className="pt-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              {renderStars(review.rating)}
              {review.title && (
                <span className="font-medium">{review.title}</span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <span>{review.customer_name}</span>
              <span>|</span>
              <span>{formatDate(review.created_at)}</span>
              {review.is_verified_purchase && (
                <>
                  <span>|</span>
                  <span className="flex items-center gap-1 text-green-600">
                    <CheckCircle className="h-3.5 w-3.5" />
                    Verified Purchase
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Review Text */}
        {review.review_text && (
          <p className="mt-3 text-sm leading-relaxed">{review.review_text}</p>
        )}

        {/* Admin Response */}
        {review.admin_response && (
          <div className="mt-4 p-3 bg-muted rounded-lg">
            <div className="flex items-center gap-2 text-sm font-medium mb-1">
              <MessageSquare className="h-4 w-4" />
              Response from Seller
            </div>
            <p className="text-sm text-muted-foreground">{review.admin_response}</p>
            {review.admin_response_at && (
              <p className="text-xs text-muted-foreground mt-1">
                {formatDate(review.admin_response_at)}
              </p>
            )}
          </div>
        )}

        {/* Helpful */}
        <div className="mt-4 flex items-center gap-4">
          <span className="text-sm text-muted-foreground">
            {helpfulCount > 0
              ? `${helpfulCount} ${helpfulCount === 1 ? 'person' : 'people'} found this helpful`
              : 'Was this review helpful?'}
          </span>
          {!hasVoted && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleHelpfulVote(true)}
              className="h-8"
            >
              <ThumbsUp className="h-4 w-4 mr-1" />
              Helpful
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
