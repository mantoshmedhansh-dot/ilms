'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Clock, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  getRecentlyViewed,
  RecentlyViewedProduct,
} from '@/lib/storefront/recently-viewed';
import { formatCurrency } from '@/lib/utils';

interface RecentlyViewedProps {
  excludeProductId?: string;
  maxItems?: number;
  title?: string;
}

export function RecentlyViewed({
  excludeProductId,
  maxItems = 8,
  title = 'Recently Viewed',
}: RecentlyViewedProps) {
  const [products, setProducts] = useState<RecentlyViewedProduct[]>([]);
  const [scrollPosition, setScrollPosition] = useState(0);

  useEffect(() => {
    let items = getRecentlyViewed();

    // Exclude current product if viewing a product page
    if (excludeProductId) {
      items = items.filter((p) => p.id !== excludeProductId);
    }

    setProducts(items.slice(0, maxItems));
  }, [excludeProductId, maxItems]);

  if (products.length === 0) {
    return null;
  }

  const scroll = (direction: 'left' | 'right') => {
    const container = document.getElementById('recently-viewed-container');
    if (!container) return;

    const scrollAmount = 280; // Approximate card width + gap
    const newPosition =
      direction === 'left'
        ? Math.max(0, scrollPosition - scrollAmount)
        : scrollPosition + scrollAmount;

    container.scrollTo({ left: newPosition, behavior: 'smooth' });
    setScrollPosition(newPosition);
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    setScrollPosition(e.currentTarget.scrollLeft);
  };

  return (
    <section className="py-8">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-muted-foreground" />
            <h2 className="text-xl font-semibold">{title}</h2>
          </div>

          {/* Navigation Buttons */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={() => scroll('left')}
              disabled={scrollPosition <= 0}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => scroll('right')}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Scrollable Container */}
        <div
          id="recently-viewed-container"
          className="flex gap-4 overflow-x-auto scrollbar-hide scroll-smooth pb-2"
          onScroll={handleScroll}
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          {products.map((product) => (
            <Link
              key={product.id}
              href={`/products/${product.slug}`}
              className="flex-shrink-0 w-[200px] sm:w-[240px]"
            >
              <Card className="h-full hover:shadow-md transition-shadow">
                <CardContent className="p-3">
                  {/* Product Image */}
                  <div className="relative aspect-square mb-3 bg-muted rounded-lg overflow-hidden">
                    {product.imageUrl ? (
                      <Image
                        src={product.imageUrl}
                        alt={product.name}
                        fill
                        className="object-cover"
                        sizes="(max-width: 640px) 200px, 240px"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                        No Image
                      </div>
                    )}
                  </div>

                  {/* Product Name */}
                  <h3 className="font-medium text-sm line-clamp-2 mb-2 min-h-[2.5rem]">
                    {product.name}
                  </h3>

                  {/* Price */}
                  <div className="flex items-baseline gap-2">
                    <span className="font-bold text-primary">
                      {formatCurrency(product.price)}
                    </span>
                    {product.mrp > product.price && (
                      <span className="text-xs text-muted-foreground line-through">
                        {formatCurrency(product.mrp)}
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

export default RecentlyViewed;
