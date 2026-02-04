'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Star,
  Minus,
  Plus,
  ShoppingCart,
  Heart,
  Truck,
  Shield,
  RotateCcw,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import PinCodeChecker from '@/components/storefront/product/pincode-checker';
import { ProductReviews } from '@/components/storefront/reviews';
import ProductQA from '@/components/storefront/reviews/product-qa';
import ProductFAQ from '@/components/storefront/product/product-faq';
import ImageGallery from '@/components/storefront/product/image-gallery';
import StockStatus from '@/components/storefront/product/stock-status';
import ShareButton from '@/components/storefront/product/share-button';
import DemoBooking from '@/components/storefront/booking/demo-booking';
import { ExchangeBanner } from '@/components/storefront/exchange/exchange-calculator';
import { useCartStore } from '@/lib/storefront/cart-store';
import { addToRecentlyViewed } from '@/lib/storefront/recently-viewed';
import { reviewsApi } from '@/lib/storefront/api';
import { formatCurrency } from '@/lib/utils';
import type { ServerProduct } from '@/lib/storefront/server-api';

interface ProductDetailClientProps {
  product: ServerProduct;
}

interface ProductVariant {
  id: string;
  name: string;
  sku: string;
  mrp: number;
  selling_price?: number;
  in_stock: boolean;
  stock_quantity?: number;
  attributes?: Record<string, string>;
}

export default function ProductDetailClient({ product }: ProductDetailClientProps) {
  const [selectedVariant, setSelectedVariant] = useState<ProductVariant | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [reviewSummary, setReviewSummary] = useState<{
    average_rating: number;
    total_reviews: number;
  } | null>(null);

  const addItem = useCartStore((state) => state.addItem);

  // Set default variant and track recently viewed
  useEffect(() => {
    // Set default variant if exists
    if (product.variants && product.variants.length > 0) {
      setSelectedVariant(product.variants[0]);
    }

    // Track this product as recently viewed
    const primaryImg = product.images?.find((img) => img.is_primary) || product.images?.[0];
    addToRecentlyViewed({
      id: product.id,
      slug: product.slug,
      name: product.name,
      imageUrl: primaryImg?.image_url,
      price: product.selling_price || product.mrp,
      mrp: product.mrp,
    });

    // Fetch review summary
    reviewsApi.getReviewSummary(product.id)
      .then((summary) => setReviewSummary(summary))
      .catch(() => null);
  }, [product]);

  const handleQuantityChange = (delta: number) => {
    setQuantity((prev) => Math.max(1, Math.min(10, prev + delta)));
  };

  const handleAddToCart = () => {
    // Convert server product to cart-compatible format
    const cartProduct = {
      ...product,
      selling_price: product.selling_price || product.mrp,
    };
    addItem(cartProduct as any, quantity, (selectedVariant || undefined) as any);
    toast.success('Added to cart!');
  };

  const handleBuyNow = () => {
    handleAddToCart();
    window.location.href = '/checkout';
  };

  const images = product.images || [];
  const currentPrice = selectedVariant?.selling_price || product.selling_price || product.mrp;
  const currentMrp = selectedVariant?.mrp || product.mrp;
  const discountPercentage =
    currentMrp > currentPrice
      ? Math.round(((currentMrp - currentPrice) / currentMrp) * 100)
      : 0;

  // Check if product is out of stock
  const isOutOfStock = product.in_stock === false || product.stock_quantity === 0;

  // Group specifications by group_name
  const specGroups = (product.specifications || []).reduce((acc, spec) => {
    const group = spec.group_name || 'General';
    if (!acc[group]) acc[group] = [];
    acc[group].push(spec);
    return acc;
  }, {} as Record<string, typeof product.specifications>);

  return (
    <>
      {/* Product Section */}
      <div className="bg-card rounded-lg shadow-sm p-6 mb-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Image Gallery with Zoom & Lightbox */}
          <ImageGallery
            images={images.map((img) => ({
              id: img.id,
              image_url: img.image_url,
              thumbnail_url: img.thumbnail_url,
              alt_text: img.alt_text,
              is_primary: img.is_primary,
            }))}
            productName={product.name}
          />

          {/* Product Info */}
          <div className="space-y-6">
            {/* Badges */}
            <div className="flex flex-wrap gap-2">
              {product.is_bestseller && (
                <Badge className="bg-orange-500">Bestseller</Badge>
              )}
              {product.is_new_arrival && (
                <Badge className="bg-green-500">New Arrival</Badge>
              )}
              {discountPercentage > 0 && (
                <Badge variant="destructive">{discountPercentage}% OFF</Badge>
              )}
            </div>

            {/* Brand & Category */}
            <div className="text-sm text-muted-foreground">
              {product.brand?.name && (
                <span className="font-medium text-primary">
                  {product.brand.name}
                </span>
              )}
              {product.category?.name && (
                <>
                  {product.brand?.name && ' • '}
                  {product.category.name}
                </>
              )}
            </div>

            {/* Title */}
            <h1 className="text-2xl md:text-3xl font-bold">{product.name}</h1>

            {/* Rating */}
            {reviewSummary && reviewSummary.total_reviews > 0 ? (
              <div className="flex items-center gap-2" role="group" aria-label="Product rating">
                <div
                  className="flex items-center bg-green-600 text-white px-2 py-0.5 rounded text-sm"
                  role="img"
                  aria-label={`Rated ${reviewSummary.average_rating.toFixed(1)} out of 5 stars`}
                >
                  <Star className="h-3 w-3 fill-current mr-1" aria-hidden="true" />
                  {reviewSummary.average_rating.toFixed(1)}
                </div>
                <span className="text-muted-foreground text-sm">
                  {reviewSummary.total_reviews} Review{reviewSummary.total_reviews !== 1 ? 's' : ''}
                </span>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">
                No reviews yet - Be the first to review!
              </div>
            )}

            {/* Price */}
            <div className="space-y-1">
              <div className="flex items-baseline gap-3">
                <span className="text-3xl font-bold text-primary">
                  {formatCurrency(currentPrice)}
                </span>
                {currentMrp > currentPrice && (
                  <>
                    <span className="text-xl text-muted-foreground line-through">
                      {formatCurrency(currentMrp)}
                    </span>
                    <span className="text-green-600 font-medium">
                      Save {formatCurrency(currentMrp - currentPrice)}
                    </span>
                  </>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                Inclusive of all taxes
              </p>
              {/* EMI Option */}
              {currentPrice >= 5000 && (
                <div className="flex items-center gap-2 mt-2 p-2 bg-green-50 rounded-lg border border-green-200">
                  <span className="text-green-700 font-medium text-sm">
                    No-cost EMI from {formatCurrency(Math.round(currentPrice / 6))}/month
                  </span>
                  <Badge variant="secondary" className="bg-green-100 text-green-800 text-xs">
                    6 months
                  </Badge>
                </div>
              )}
            </div>

            {/* Exchange Offer */}
            <ExchangeBanner
              newProductPrice={currentPrice}
              newProductName={product.name}
            />

            {/* Stock Status */}
            <StockStatus
              productId={product.id}
              variantId={selectedVariant?.id}
              inStock={product.in_stock}
              stockQuantity={product.stock_quantity}
            />

            {/* Variants */}
            {product.variants && product.variants.length > 0 && (
              <div>
                <label className="text-sm font-semibold mb-2 block">
                  Select Variant
                </label>
                <div className="flex flex-wrap gap-2">
                  {product.variants.map((variant) => (
                    <Button
                      key={variant.id}
                      variant={
                        selectedVariant?.id === variant.id
                          ? 'default'
                          : 'outline'
                      }
                      size="sm"
                      onClick={() => setSelectedVariant(variant)}
                    >
                      {variant.name}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {/* Quantity */}
            <div>
              <label className="text-sm font-semibold mb-2 block">
                Quantity
              </label>
              <div className="flex items-center gap-3">
                <div className="flex items-center border rounded-lg" role="group" aria-label="Select quantity">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-10 w-10"
                    onClick={() => handleQuantityChange(-1)}
                    disabled={quantity <= 1}
                    aria-label="Decrease quantity"
                  >
                    <Minus className="h-4 w-4" aria-hidden="true" />
                  </Button>
                  <span className="w-12 text-center font-medium" aria-live="polite" aria-label={`Quantity: ${quantity}`}>
                    {quantity}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-10 w-10"
                    onClick={() => handleQuantityChange(1)}
                    disabled={quantity >= 10}
                    aria-label="Increase quantity"
                  >
                    <Plus className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Delivery Check */}
            <PinCodeChecker productPrice={currentPrice} />

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button
                size="lg"
                className="flex-1"
                onClick={handleAddToCart}
                disabled={isOutOfStock}
              >
                <ShoppingCart className="h-5 w-5 mr-2" />
                {isOutOfStock ? 'Out of Stock' : 'Add to Cart'}
              </Button>
              <Button
                size="lg"
                variant="secondary"
                className="flex-1"
                onClick={handleBuyNow}
                disabled={isOutOfStock}
              >
                {isOutOfStock ? 'Coming Soon' : 'Buy Now'}
              </Button>
              <Button size="lg" variant="outline" className="px-4">
                <Heart className="h-5 w-5" />
              </Button>
              <ShareButton
                title={product.name}
                text={`Check out ${product.name} on ILMS.AI - ${formatCurrency(currentPrice)}`}
              />
            </div>

            {/* Demo Booking */}
            <DemoBooking productName={product.name} />

            {/* Features */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t">
              <div className="text-center">
                <Truck className="h-6 w-6 mx-auto text-primary mb-1" />
                <p className="text-xs">Free Shipping</p>
              </div>
              <div className="text-center">
                <Shield className="h-6 w-6 mx-auto text-primary mb-1" />
                <p className="text-xs">{product.warranty_months || 12}M Warranty</p>
              </div>
              <div className="text-center">
                <RotateCcw className="h-6 w-6 mx-auto text-primary mb-1" />
                <p className="text-xs">7 Day Returns</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Product Details Tabs */}
      <div className="bg-card rounded-lg shadow-sm p-6 mb-8">
        <Tabs defaultValue="description">
          <TabsList className="mb-4">
            <TabsTrigger value="description">Description</TabsTrigger>
            <TabsTrigger value="specifications">Specifications</TabsTrigger>
            <TabsTrigger value="reviews">Reviews</TabsTrigger>
            <TabsTrigger value="qa">Q&A</TabsTrigger>
            <TabsTrigger value="faq">FAQs</TabsTrigger>
          </TabsList>

          <TabsContent value="description" className="space-y-4">
            <h3 className="font-semibold text-lg">Product Description</h3>
            {product.description ? (
              <div
                className="prose max-w-none text-muted-foreground"
                dangerouslySetInnerHTML={{ __html: product.description }}
              />
            ) : (
              <p className="text-muted-foreground">
                {product.short_description || 'No description available.'}
              </p>
            )}

            {product.features && (
              <div className="mt-6">
                <h4 className="font-semibold mb-3">Key Features</h4>
                <ul className="space-y-2">
                  {product.features.split('\n').map((feature, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <Check className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </TabsContent>

          <TabsContent value="specifications">
            <h3 className="font-semibold text-lg mb-4">Specifications</h3>
            {Object.keys(specGroups).length > 0 ? (
              <div className="space-y-6">
                {Object.entries(specGroups).map(([group, specs]) => (
                  <div key={group}>
                    <h4 className="font-medium text-primary mb-2">{group}</h4>
                    <div className="border rounded-lg overflow-hidden">
                      {specs?.map((spec, i) => (
                        <div
                          key={spec.id}
                          className={`flex ${
                            i % 2 === 0 ? 'bg-muted/50' : 'bg-card'
                          }`}
                        >
                          <div className="w-1/3 p-3 font-medium border-r">
                            {spec.key}
                          </div>
                          <div className="w-2/3 p-3">{spec.value}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground">
                No specifications available.
              </p>
            )}
          </TabsContent>

          <TabsContent value="reviews">
            <ProductReviews productId={product.id} productName={product.name} />
          </TabsContent>

          <TabsContent value="qa">
            <ProductQA productId={product.id} productName={product.name} />
          </TabsContent>

          <TabsContent value="faq">
            <ProductFAQ productName={product.name} />
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
