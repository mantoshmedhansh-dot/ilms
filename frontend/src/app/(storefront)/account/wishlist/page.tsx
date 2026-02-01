'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import {
  Heart,
  ShoppingCart,
  Trash2,
  ChevronLeft,
  Loader2,
  TrendingDown,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { useIsAuthenticated } from '@/lib/storefront/auth-store';
import { useWishlistStore, useWishlistItems } from '@/lib/storefront/wishlist-store';
import { useCartStore } from '@/lib/storefront/cart-store';
import { formatCurrency } from '@/lib/utils';

export default function WishlistPage() {
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();
  const wishlistItems = useWishlistItems();
  const fetchWishlist = useWishlistStore((state) => state.fetchWishlist);
  const removeFromWishlist = useWishlistStore((state) => state.removeFromWishlist);
  const isLoading = useWishlistStore((state) => state.isLoading);
  const addToCart = useCartStore((state) => state.addItem);

  const [removingId, setRemovingId] = useState<string | null>(null);
  const [addingToCartId, setAddingToCartId] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/account/login?redirect=/account/wishlist');
      return;
    }

    fetchWishlist();
  }, [isAuthenticated, router, fetchWishlist]);

  const handleRemove = async (productId: string) => {
    setRemovingId(productId);
    const success = await removeFromWishlist(productId);
    if (success) {
      toast.success('Removed from wishlist');
    } else {
      toast.error('Failed to remove from wishlist');
    }
    setRemovingId(null);
  };

  const handleAddToCart = async (item: typeof wishlistItems[0]) => {
    setAddingToCartId(item.productId);

    // Create a product object for the cart
    addToCart({
      id: item.productId,
      name: item.productName,
      slug: item.productSlug,
      sku: '',
      selling_price: item.productPrice,
      mrp: item.productMrp,
      is_active: true,
      images: item.productImage ? [{
        id: '1',
        image_url: item.productImage,
        is_primary: true,
        sort_order: 0,
      }] : [],
    });

    toast.success('Added to cart');
    setAddingToCartId(null);
  };

  const handleMoveToCart = async (item: typeof wishlistItems[0]) => {
    await handleAddToCart(item);
    await handleRemove(item.productId);
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="flex items-center gap-4 mb-8">
        <Link href="/account">
          <Button variant="ghost" size="icon">
            <ChevronLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2">
            <Heart className="h-7 w-7 text-red-500 fill-red-500" />
            My Wishlist
          </h1>
          <p className="text-muted-foreground mt-1">
            {wishlistItems.length} {wishlistItems.length === 1 ? 'item' : 'items'} saved
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : wishlistItems.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Heart className="h-16 w-16 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">Your Wishlist is Empty</h3>
            <p className="text-muted-foreground text-center mb-6 max-w-md">
              Save items you love by clicking the heart icon on products. They&apos;ll appear here for easy access later.
            </p>
            <Link href="/products">
              <Button>
                Browse Products
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {wishlistItems.map((item) => (
            <Card key={item.id} className="overflow-hidden">
              <CardContent className="p-0">
                <div className="flex flex-col sm:flex-row">
                  {/* Product Image */}
                  <Link href={`/products/${item.productSlug}`} className="sm:w-48 h-48 sm:h-auto relative flex-shrink-0">
                    {item.productImage ? (
                      <Image
                        src={item.productImage}
                        alt={item.productName}
                        fill
                        className="object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-muted flex items-center justify-center">
                        <Heart className="h-12 w-12 text-muted-foreground" />
                      </div>
                    )}
                    {/* Price Drop Badge */}
                    {item.priceDropped && (
                      <Badge className="absolute top-2 left-2 bg-green-500">
                        <TrendingDown className="h-3 w-3 mr-1" />
                        Price Dropped!
                      </Badge>
                    )}
                    {/* Out of Stock Badge */}
                    {!item.isInStock && (
                      <Badge variant="destructive" className="absolute top-2 left-2">
                        <AlertCircle className="h-3 w-3 mr-1" />
                        Out of Stock
                      </Badge>
                    )}
                  </Link>

                  {/* Product Info */}
                  <div className="flex-1 p-4 sm:p-6 flex flex-col">
                    <div className="flex-1">
                      <Link href={`/products/${item.productSlug}`}>
                        <h3 className="font-medium text-lg hover:text-primary transition-colors line-clamp-2">
                          {item.productName}
                        </h3>
                      </Link>

                      {/* Price */}
                      <div className="mt-2 flex items-baseline gap-2">
                        <span className="text-xl font-bold text-primary">
                          {formatCurrency(item.productPrice)}
                        </span>
                        {item.productMrp > item.productPrice && (
                          <>
                            <span className="text-sm text-muted-foreground line-through">
                              {formatCurrency(item.productMrp)}
                            </span>
                            <span className="text-sm text-green-600 font-medium">
                              {Math.round((1 - item.productPrice / item.productMrp) * 100)}% off
                            </span>
                          </>
                        )}
                      </div>

                      {/* Price when added comparison */}
                      {item.priceWhenAdded && item.priceDropped && (
                        <p className="text-sm text-green-600 mt-1">
                          Was {formatCurrency(item.priceWhenAdded)} when you saved it
                        </p>
                      )}

                      {/* Added date */}
                      <p className="text-xs text-muted-foreground mt-2">
                        Added on {new Date(item.createdAt).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </p>
                    </div>

                    {/* Actions */}
                    <Separator className="my-4" />
                    <div className="flex flex-wrap gap-2">
                      {item.isInStock ? (
                        <>
                          <Button
                            onClick={() => handleMoveToCart(item)}
                            disabled={addingToCartId === item.productId}
                            className="flex-1 sm:flex-none"
                          >
                            {addingToCartId === item.productId ? (
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                              <ShoppingCart className="h-4 w-4 mr-2" />
                            )}
                            Move to Cart
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => handleAddToCart(item)}
                            disabled={addingToCartId === item.productId}
                          >
                            Add to Cart
                          </Button>
                        </>
                      ) : (
                        <Button variant="outline" disabled>
                          Out of Stock
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive"
                        onClick={() => handleRemove(item.productId)}
                        disabled={removingId === item.productId}
                      >
                        {removingId === item.productId ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
