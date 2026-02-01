'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, X, ShoppingCart, Package, Star, Check, Minus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useCompareStore, useCompareItems, useCompareCount } from '@/lib/storefront/compare-store';
import { useCartStore } from '@/lib/storefront/cart-store';
import { productsApi } from '@/lib/storefront/api';
import { formatCurrency } from '@/lib/utils';
import { StorefrontProduct } from '@/types/storefront';
import { toast } from 'sonner';

interface ProductSpec {
  group_name?: string;
  key: string;
  value: string;
}

export default function ComparePage() {
  const router = useRouter();
  const items = useCompareItems();
  const count = useCompareCount();
  const removeFromCompare = useCompareStore((state) => state.removeFromCompare);
  const clearCompare = useCompareStore((state) => state.clearCompare);
  const addToCart = useCartStore((state) => state.addItem);

  const [products, setProducts] = useState<StorefrontProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [allSpecs, setAllSpecs] = useState<string[]>([]);

  useEffect(() => {
    const fetchProducts = async () => {
      if (items.length === 0) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const result = await productsApi.compare(items.map((i) => i.id));
        setProducts(result.products);

        // Extract all unique specification keys
        const specs = new Set<string>();
        result.products.forEach((p) => {
          p.specifications?.forEach((spec: ProductSpec) => {
            specs.add(spec.key);
          });
        });
        setAllSpecs(Array.from(specs).sort());
      } catch (error) {
        console.error('Failed to fetch comparison data:', error);
        toast.error('Failed to load product details');
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, [items]);

  const getSpecValue = (product: StorefrontProduct, specKey: string): string | null => {
    const spec = product.specifications?.find((s: ProductSpec) => s.key === specKey);
    return spec?.value || null;
  };

  const handleAddToCart = (product: StorefrontProduct) => {
    addToCart(product as any, 1);
    toast.success(`${product.name} added to cart`);
  };

  const handleRemove = (productId: string) => {
    removeFromCompare(productId);
    setProducts((prev) => prev.filter((p) => p.id !== productId));
  };

  if (count === 0 && !loading) {
    return (
      <div className="container mx-auto px-4 py-12">
        <div className="text-center">
          <Package className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
          <h1 className="text-2xl font-bold mb-2">No Products to Compare</h1>
          <p className="text-muted-foreground mb-6">
            Add products to compare by clicking the compare icon on product cards.
          </p>
          <Button asChild>
            <Link href="/products">Browse Products</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Compare Products</h1>
            <p className="text-muted-foreground">
              Comparing {count} product{count !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={clearCompare}>
          Clear All
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {items.map((item) => (
            <Card key={item.id}>
              <CardContent className="p-4">
                <Skeleton className="aspect-square w-full mb-4" />
                <Skeleton className="h-4 w-3/4 mb-2" />
                <Skeleton className="h-6 w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            {/* Product Cards Row */}
            <thead>
              <tr>
                <th className="text-left p-4 bg-muted/50 min-w-[200px] sticky left-0 z-10">
                  <span className="font-semibold">Product</span>
                </th>
                {products.map((product) => {
                  const primaryImage =
                    product.images?.find((img) => img.is_primary) || product.images?.[0];
                  const sellingPrice = product.selling_price ?? product.mrp;
                  const discountPercent =
                    product.mrp > sellingPrice
                      ? Math.round(((product.mrp - sellingPrice) / product.mrp) * 100)
                      : 0;

                  return (
                    <th key={product.id} className="p-4 min-w-[250px] align-top">
                      <Card className="relative">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="absolute top-2 right-2 h-6 w-6 z-10"
                          onClick={() => handleRemove(product.id)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                        <CardContent className="p-4">
                          <Link href={`/products/${product.slug}`}>
                            <div className="aspect-square relative mb-4 bg-muted rounded-lg overflow-hidden">
                              {primaryImage ? (
                                <img
                                  src={primaryImage.thumbnail_url || primaryImage.image_url}
                                  alt={product.name}
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center">
                                  <Package className="h-12 w-12 text-muted-foreground/50" />
                                </div>
                              )}
                              {discountPercent > 0 && (
                                <Badge
                                  variant="destructive"
                                  className="absolute top-2 left-2"
                                >
                                  {discountPercent}% OFF
                                </Badge>
                              )}
                            </div>
                            <h3 className="font-medium text-sm line-clamp-2 mb-2 text-left">
                              {product.name}
                            </h3>
                          </Link>
                          <div className="flex items-center gap-1 mb-2">
                            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                            <span className="text-sm">4.5</span>
                            <span className="text-xs text-muted-foreground">(234)</span>
                          </div>
                          <div className="text-left mb-4">
                            <span className="text-lg font-bold text-primary">
                              {formatCurrency(sellingPrice)}
                            </span>
                            {product.mrp > sellingPrice && (
                              <span className="text-sm text-muted-foreground line-through ml-2">
                                {formatCurrency(product.mrp)}
                              </span>
                            )}
                          </div>
                          <Button
                            className="w-full"
                            size="sm"
                            onClick={() => handleAddToCart(product)}
                            disabled={product.in_stock === false}
                          >
                            <ShoppingCart className="h-4 w-4 mr-2" />
                            {product.in_stock === false ? 'Out of Stock' : 'Add to Cart'}
                          </Button>
                        </CardContent>
                      </Card>
                    </th>
                  );
                })}
              </tr>
            </thead>

            <tbody>
              {/* Basic Info */}
              <tr className="border-t">
                <td className="p-4 bg-muted/50 font-medium sticky left-0">Brand</td>
                {products.map((product) => (
                  <td key={product.id} className="p-4 text-center">
                    {product.brand?.name || '-'}
                  </td>
                ))}
              </tr>
              <tr className="border-t">
                <td className="p-4 bg-muted/50 font-medium sticky left-0">Category</td>
                {products.map((product) => (
                  <td key={product.id} className="p-4 text-center">
                    {product.category?.name || '-'}
                  </td>
                ))}
              </tr>
              <tr className="border-t">
                <td className="p-4 bg-muted/50 font-medium sticky left-0">Warranty</td>
                {products.map((product) => (
                  <td key={product.id} className="p-4 text-center">
                    {product.warranty_months
                      ? `${product.warranty_months} Months`
                      : '-'}
                  </td>
                ))}
              </tr>
              <tr className="border-t">
                <td className="p-4 bg-muted/50 font-medium sticky left-0">Availability</td>
                {products.map((product) => (
                  <td key={product.id} className="p-4 text-center">
                    {product.in_stock === false ? (
                      <Badge variant="secondary">Out of Stock</Badge>
                    ) : (
                      <Badge variant="outline" className="text-green-600 border-green-600">
                        In Stock
                      </Badge>
                    )}
                  </td>
                ))}
              </tr>

              {/* Specifications Header */}
              {allSpecs.length > 0 && (
                <tr className="border-t bg-muted">
                  <td colSpan={products.length + 1} className="p-4 font-semibold">
                    Specifications
                  </td>
                </tr>
              )}

              {/* Specifications Rows */}
              {allSpecs.map((specKey) => (
                <tr key={specKey} className="border-t">
                  <td className="p-4 bg-muted/50 font-medium sticky left-0">{specKey}</td>
                  {products.map((product) => {
                    const value = getSpecValue(product, specKey);
                    return (
                      <td key={product.id} className="p-4 text-center">
                        {value ? (
                          value.toLowerCase() === 'yes' ? (
                            <Check className="h-5 w-5 text-green-600 mx-auto" />
                          ) : value.toLowerCase() === 'no' ? (
                            <Minus className="h-5 w-5 text-muted-foreground mx-auto" />
                          ) : (
                            value
                          )
                        ) : (
                          <Minus className="h-5 w-5 text-muted-foreground mx-auto" />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Continue Shopping */}
      <div className="mt-8 text-center">
        <Button variant="outline" asChild>
          <Link href="/products">Continue Shopping</Link>
        </Button>
      </div>
    </div>
  );
}
