'use client';

import { useState } from 'react';
import { Star, Loader2, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { reviewsApi } from '@/lib/storefront/api';
import { useIsAuthenticated } from '@/lib/storefront/auth-store';
import Link from 'next/link';

interface WriteReviewFormProps {
  productId: string;
  productName: string;
  onReviewSubmitted?: () => void;
}

export function WriteReviewForm({
  productId,
  productName,
  onReviewSubmitted,
}: WriteReviewFormProps) {
  const isAuthenticated = useIsAuthenticated();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [checkingEligibility, setCheckingEligibility] = useState(false);
  const [canReview, setCanReview] = useState<boolean | null>(null);
  const [isVerifiedPurchase, setIsVerifiedPurchase] = useState(false);
  const [reason, setReason] = useState<string | null>(null);

  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [title, setTitle] = useState('');
  const [reviewText, setReviewText] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const checkEligibility = async () => {
    if (!isAuthenticated) {
      setCanReview(false);
      setReason('Login required to write a review');
      return;
    }

    setCheckingEligibility(true);
    try {
      const result = await reviewsApi.canReview(productId);
      setCanReview(result.can_review);
      setIsVerifiedPurchase(result.is_verified_purchase);
      setReason(result.reason || null);
    } catch (error) {
      setCanReview(false);
      setReason('Unable to check eligibility');
    } finally {
      setCheckingEligibility(false);
    }
  };

  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen);
    if (isOpen) {
      checkEligibility();
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (rating === 0) {
      newErrors.rating = 'Please select a rating';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    setLoading(true);
    try {
      await reviewsApi.createReview(
        productId,
        rating,
        title || undefined,
        reviewText || undefined
      );
      toast.success('Review submitted successfully!');
      setOpen(false);
      // Reset form
      setRating(0);
      setTitle('');
      setReviewText('');
      onReviewSubmitted?.();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to submit review');
    } finally {
      setLoading(false);
    }
  };

  const renderStarSelector = () => {
    const labels = ['', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent'];
    return (
      <div className="flex gap-1" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            role="radio"
            aria-checked={rating === star}
            aria-label={`${star} star${star !== 1 ? 's' : ''} - ${labels[star]}`}
            onClick={() => setRating(star)}
            onMouseEnter={() => setHoverRating(star)}
            onMouseLeave={() => setHoverRating(0)}
            className="focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded"
          >
            <Star
              className={`h-8 w-8 transition-colors ${
                star <= (hoverRating || rating)
                  ? 'fill-yellow-400 text-yellow-400'
                  : 'fill-gray-200 text-gray-200 hover:fill-yellow-200 hover:text-yellow-200'
              }`}
              aria-hidden="true"
            />
          </button>
        ))}
      </div>
    );
  };

  const getRatingLabel = () => {
    const labels = ['', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent'];
    return labels[hoverRating || rating] || '';
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>Write a Review</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Write a Review</DialogTitle>
          <DialogDescription className="line-clamp-1">
            {productName}
          </DialogDescription>
        </DialogHeader>

        {checkingEligibility ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : canReview === false ? (
          <div className="py-6 text-center">
            <p className="text-muted-foreground mb-4">{reason}</p>
            {!isAuthenticated && (
              <Button asChild>
                <Link href={`/account/login?redirect=/products/${productId}`}>
                  Login to Write Review
                </Link>
              </Button>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            {isVerifiedPurchase && (
              <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 px-3 py-2 rounded-md">
                <CheckCircle className="h-4 w-4" />
                Your review will be marked as "Verified Purchase"
              </div>
            )}

            {/* Rating */}
            <div className="space-y-2">
              <Label>
                Rating <span className="text-red-500">*</span>
              </Label>
              <div className="flex items-center gap-3">
                {renderStarSelector()}
                <span className="text-sm font-medium text-muted-foreground">
                  {getRatingLabel()}
                </span>
              </div>
              {errors.rating && (
                <p className="text-sm text-red-500">{errors.rating}</p>
              )}
            </div>

            {/* Title */}
            <div className="space-y-2">
              <Label htmlFor="title">Review Title (Optional)</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Summarize your experience"
                maxLength={200}
              />
            </div>

            {/* Review Text */}
            <div className="space-y-2">
              <Label htmlFor="reviewText">Your Review (Optional)</Label>
              <Textarea
                id="reviewText"
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
                placeholder="What did you like or dislike about this product?"
                rows={4}
                maxLength={2000}
              />
              <p className="text-xs text-muted-foreground text-right">
                {reviewText.length}/2000
              </p>
            </div>

            {/* Submit */}
            <div className="flex justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  'Submit Review'
                )}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
