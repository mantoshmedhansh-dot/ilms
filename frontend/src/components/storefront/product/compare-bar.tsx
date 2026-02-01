'use client';

import { X, GitCompareArrows } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { useCompareStore, useCompareItems, useCompareCount } from '@/lib/storefront/compare-store';
import { formatCurrency } from '@/lib/utils';

export default function CompareBar() {
  const items = useCompareItems();
  const count = useCompareCount();
  const removeFromCompare = useCompareStore((state) => state.removeFromCompare);
  const clearCompare = useCompareStore((state) => state.clearCompare);

  if (count === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-background border-t shadow-lg z-50 p-4">
      <div className="container mx-auto">
        <div className="flex items-center justify-between gap-4">
          {/* Selected Products */}
          <div className="flex items-center gap-3 overflow-x-auto flex-1">
            <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">
              Compare ({count}/4):
            </span>
            <div className="flex items-center gap-2">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="relative flex items-center gap-2 bg-muted rounded-lg p-2 pr-8 min-w-[200px]"
                >
                  {item.image ? (
                    <img
                      src={item.image}
                      alt={item.name}
                      className="w-10 h-10 object-cover rounded"
                    />
                  ) : (
                    <div className="w-10 h-10 bg-gray-200 rounded flex items-center justify-center">
                      <GitCompareArrows className="h-5 w-5 text-gray-400" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate">{item.name}</p>
                    <p className="text-xs text-primary font-bold">
                      {formatCurrency(item.price)}
                    </p>
                  </div>
                  <button
                    onClick={() => removeFromCompare(item.id)}
                    className="absolute top-1 right-1 p-1 hover:bg-background rounded-full"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}

              {/* Empty slots */}
              {Array.from({ length: 4 - count }).map((_, i) => (
                <div
                  key={`empty-${i}`}
                  className="w-[200px] h-[58px] border-2 border-dashed border-muted-foreground/30 rounded-lg flex items-center justify-center"
                >
                  <span className="text-xs text-muted-foreground">Add product</span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <Button variant="outline" size="sm" onClick={clearCompare}>
              Clear All
            </Button>
            <Button asChild size="sm" disabled={count < 2}>
              <Link href="/products/compare">
                <GitCompareArrows className="h-4 w-4 mr-2" />
                Compare Now
              </Link>
            </Button>
          </div>
        </div>

        {count < 2 && (
          <p className="text-xs text-muted-foreground mt-2">
            Add at least 2 products to compare
          </p>
        )}
      </div>
    </div>
  );
}
