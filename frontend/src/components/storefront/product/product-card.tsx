'use client';

import Link from 'next/link';
import { ShoppingCart, Heart, Star, Package, GitCompareArrows, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { useCartStore } from '@/lib/storefront/cart-store';
import { useCompareStore, useIsInCompare, useCanAddToCompare } from '@/lib/storefront/compare-store';
import { useWishlistStore, useIsInWishlist } from '@/lib/storefront/wishlist-store';
import { useAuthStore } from '@/lib/storefront/auth-store';
import { usePrefetchProduct } from '@/lib/storefront/hooks';
import { formatCurrency } from '@/lib/utils';
import { toast } from 'sonner';

// Common product interface that works with both server and client products
interface BaseProduct {
  id: string;
  name: string;
  slug: string;
  mrp: number;
  selling_price?: number | null;
  is_bestseller?: boolean;
  is_new_arrival?: boolean;
  in_stock?: boolean;
  stock_quantity?: number | null;
  warranty_months?: number | null;
  images?: Array<{
    id: string;
    image_url: string;
    thumbnail_url?: string;
    alt_text?: string;
    is_primary?: boolean;
  }>;
  category?: {
    id: string;
    name: string;
    slug: string;
  };
  brand?: {
    id: string;
    name: string;
    slug: string;
  };
}

interface ProductCardProps {
  product: BaseProduct;
  showAddToCart?: boolean;
}

export default function ProductCard({
  product,
  showAddToCart = true,
}: ProductCardProps) {
  const addItem = useCartStore((state) => state.addItem);
  const addToCompare = useCompareStore((state) => state.addToCompare);
  const removeFromCompare = useCompareStore((state) => state.removeFromCompare);
  const isInCompare = useIsInCompare(product.id);
  const canAddMore = useCanAddToCompare();
  const prefetchProduct = usePrefetchProduct();

  // Wishlist
  const addToWishlist = useWishlistStore((state) => state.addToWishlist);
  const removeFromWishlist = useWishlistStore((state) => state.removeFromWishlist);
  const isInWishlist = useIsInWishlist(product.id);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  // Prefetch product detail on hover for faster navigation
  const handleMouseEnter = () => {
    prefetchProduct(product.slug);
  };

  const primaryImage =
    product.images?.find((img) => img.is_primary) || product.images?.[0];

  const sellingPrice = product.selling_price ?? product.mrp;
  const discountPercentage = product.mrp > sellingPrice
    ? Math.round(((product.mrp - sellingPrice) / product.mrp) * 100)
    : 0;

  // Check stock status
  const isOutOfStock = product.in_stock === false || product.stock_quantity === 0;

  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isOutOfStock) {
      // Convert to cart-compatible product format
      addItem(product as any, 1);
    }
  };

  const handleCompare = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (isInCompare) {
      removeFromCompare(product.id);
      toast.success('Removed from compare');
    } else {
      if (!canAddMore) {
        toast.error('Maximum 4 products can be compared');
        return;
      }
      const added = addToCompare({
        id: product.id,
        name: product.name,
        slug: product.slug,
        image: primaryImage?.thumbnail_url || primaryImage?.image_url,
        price: sellingPrice,
        mrp: product.mrp,
        category: product.category?.name,
        brand: product.brand?.name,
      });
      if (added) {
        toast.success('Added to compare');
      }
    }
  };

  const handleWishlist = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!isAuthenticated) {
      toast.error('Please login to add items to wishlist');
      return;
    }

    if (isInWishlist) {
      const removed = await removeFromWishlist(product.id);
      if (removed) {
        toast.success('Removed from wishlist');
      } else {
        toast.error('Failed to remove from wishlist');
      }
    } else {
      const added = await addToWishlist(product.id);
      if (added) {
        toast.success('Added to wishlist');
      } else {
        toast.error('Failed to add to wishlist');
      }
    }
  };

  return (
    <Card
      className="group overflow-hidden hover:shadow-lg transition-shadow"
      onMouseEnter={handleMouseEnter}
    >
      <Link href={`/products/${product.slug}`}>
        <div className="relative aspect-square overflow-hidden bg-muted">
          {primaryImage ? (
            <img
              src={primaryImage.thumbnail_url || primaryImage.image_url}
              alt={primaryImage.alt_text || product.name}
              width={400}
              height={400}
              className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
              loading="lazy"
            />
          ) : (
            <div className="h-full w-full flex items-center justify-center">
              <Package className="h-16 w-16 text-gray-300" />
            </div>
          )}

          {/* Badges */}
          <div className="absolute top-2 left-2 flex flex-col gap-1">
            {isOutOfStock && (
              <Badge variant="secondary" className="bg-gray-800 text-white text-xs">
                Out of Stock - Coming Soon
              </Badge>
            )}
            {!isOutOfStock && discountPercentage > 0 && (
              <Badge variant="destructive" className="text-xs">
                {discountPercentage}% OFF
              </Badge>
            )}
            {product.is_new_arrival && (
              <Badge className="bg-green-500 text-xs">New</Badge>
            )}
            {product.is_bestseller && (
              <Badge className="bg-orange-500 text-xs">Bestseller</Badge>
            )}
          </div>

          {/* Action Buttons */}
          <div className="absolute top-2 right-2 flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {/* Wishlist Button */}
            <Button
              variant="ghost"
              size="icon"
              className={`h-8 w-8 bg-background/80 hover:bg-background ${isInWishlist ? 'text-red-500' : ''}`}
              onClick={handleWishlist}
              aria-label={isInWishlist ? `Remove ${product.name} from wishlist` : `Add ${product.name} to wishlist`}
              title={isInWishlist ? 'Remove from wishlist' : 'Add to wishlist'}
            >
              <Heart className={`h-4 w-4 ${isInWishlist ? 'fill-current' : ''}`} />
            </Button>

            {/* Compare Button */}
            <Button
              variant="ghost"
              size="icon"
              className={`h-8 w-8 bg-background/80 hover:bg-background ${isInCompare ? 'text-primary' : ''}`}
              onClick={handleCompare}
              aria-label={isInCompare ? `Remove ${product.name} from compare` : `Add ${product.name} to compare`}
              title={isInCompare ? 'Remove from compare' : 'Add to compare'}
            >
              {isInCompare ? (
                <Check className="h-4 w-4" />
              ) : (
                <GitCompareArrows className="h-4 w-4" />
              )}
            </Button>
          </div>

          {/* Quick Add to Cart */}
          {showAddToCart && !isOutOfStock && (
            <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                className="w-full"
                size="sm"
                onClick={handleAddToCart}
              >
                <ShoppingCart className="h-4 w-4 mr-2" />
                Add to Cart
              </Button>
            </div>
          )}
        </div>

        <CardContent className="p-4">
          {/* Category & Brand */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
            {product.category?.name && (
              <span>{product.category.name}</span>
            )}
            {product.brand?.name && (
              <>
                <span>•</span>
                <span>{product.brand.name}</span>
              </>
            )}
          </div>

          {/* Product Name */}
          <h3 className="font-medium line-clamp-2 group-hover:text-primary transition-colors">
            {product.name}
          </h3>

          {/* Rating */}
          <div className="flex items-center gap-1 mt-2">
            <div className="flex items-center text-yellow-500">
              <Star className="h-3.5 w-3.5 fill-current" />
              <span className="text-xs ml-1 text-foreground">4.5</span>
            </div>
            <span className="text-xs text-muted-foreground">(234)</span>
          </div>

          {/* Price */}
          <div className="flex items-center gap-2 mt-2">
            <span className="text-lg font-bold text-primary tabular-nums">
              {formatCurrency(sellingPrice)}
            </span>
            {product.mrp > sellingPrice && (
              <span className="text-sm text-muted-foreground line-through tabular-nums">
                {formatCurrency(product.mrp)}
              </span>
            )}
          </div>

          {/* EMI Option - Show for products above ₹5,000 */}
          {sellingPrice >= 5000 && (
            <p className="text-xs text-green-600 font-medium mt-1 tabular-nums">
              No-cost EMI from {formatCurrency(Math.round(sellingPrice / 6))}/mo
            </p>
          )}

          {/* Warranty */}
          {product.warranty_months && (
            <p className="text-xs text-muted-foreground mt-2">
              {product.warranty_months} Months Warranty
            </p>
          )}
        </CardContent>
      </Link>
    </Card>
  );
}
