'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { usePartnerStore } from '@/lib/storefront/partner-store';
import { partnerApi, generateShareUrl, generateWhatsAppShareLink } from '@/lib/storefront/partner-api';
import { StorefrontProduct } from '@/types/storefront';
import { Card, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Share2,
  Copy,
  Check,
  MessageCircle,
  Search,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { formatCurrency } from '@/lib/utils';

export default function PartnerProductsPage() {
  const { partner } = usePartnerStore();
  const [products, setProducts] = useState<StorefrontProduct[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<StorefrontProduct | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await partnerApi.getProducts(1, 50);
        setProducts(response.items || []);
      } catch (error) {
        console.error('Failed to fetch products:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProducts();
  }, []);

  const filteredProducts = products.filter(
    (product) =>
      product.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      product.sku?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const copyLink = (product: StorefrontProduct) => {
    if (!partner?.referral_code) return;
    const link = generateShareUrl(product.slug, partner.referral_code);
    navigator.clipboard.writeText(link);
    setCopiedId(product.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const shareWhatsApp = (product: StorefrontProduct) => {
    if (!partner?.referral_code) return;
    const link = generateWhatsAppShareLink(product.slug, product.name, partner.referral_code);
    window.open(link, '_blank');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Share Products</h1>
          <p className="text-muted-foreground">
            Generate referral links and earn commission on every sale
          </p>
        </div>
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search products..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Products Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {filteredProducts.map((product) => (
          <Card key={product.id} className="overflow-hidden">
            <div className="aspect-square relative bg-gray-100">
              {product.images?.[0]?.image_url ? (
                <Image
                  src={product.images[0].image_url}
                  alt={product.name}
                  fill
                  className="object-cover"
                />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                  No image
                </div>
              )}
              {product.is_bestseller && (
                <Badge className="absolute top-2 left-2">Bestseller</Badge>
              )}
            </div>
            <CardContent className="p-4">
              <h3 className="font-medium line-clamp-2 min-h-[2.5rem]">
                {product.name}
              </h3>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-lg font-bold">
                  {formatCurrency(product.selling_price || product.mrp)}
                </span>
                {product.selling_price && product.selling_price < product.mrp && (
                  <span className="text-sm text-muted-foreground line-through">
                    {formatCurrency(product.mrp)}
                  </span>
                )}
              </div>
              <p className="text-sm text-green-600 mt-1">
                Earn ~{formatCurrency((product.selling_price || product.mrp) * 0.1)} commission
              </p>
            </CardContent>
            <CardFooter className="p-4 pt-0 gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => copyLink(product)}
              >
                {copiedId === product.id ? (
                  <Check className="h-4 w-4 mr-1" />
                ) : (
                  <Copy className="h-4 w-4 mr-1" />
                )}
                Copy Link
              </Button>
              <Button
                size="sm"
                className="flex-1 bg-green-600 hover:bg-green-700"
                onClick={() => shareWhatsApp(product)}
              >
                <MessageCircle className="h-4 w-4 mr-1" />
                WhatsApp
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSelectedProduct(product)}
              >
                <Share2 className="h-4 w-4" />
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      {filteredProducts.length === 0 && (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No products found</p>
        </div>
      )}

      {/* Share Dialog */}
      <Dialog open={!!selectedProduct} onOpenChange={() => setSelectedProduct(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Share Product</DialogTitle>
            <DialogDescription>
              Share this product with your network and earn commission
            </DialogDescription>
          </DialogHeader>

          {selectedProduct && partner && (
            <div className="space-y-4">
              <div className="flex gap-4">
                <div className="w-20 h-20 relative rounded-lg overflow-hidden bg-gray-100">
                  {selectedProduct.images?.[0]?.image_url ? (
                    <Image
                      src={selectedProduct.images[0].image_url}
                      alt={selectedProduct.name}
                      fill
                      className="object-cover"
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-xs">
                      No image
                    </div>
                  )}
                </div>
                <div>
                  <h3 className="font-medium">{selectedProduct.name}</h3>
                  <p className="text-lg font-bold">
                    {formatCurrency(selectedProduct.selling_price || selectedProduct.mrp)}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Your Referral Link</label>
                <div className="flex gap-2">
                  <Input
                    readOnly
                    value={generateShareUrl(selectedProduct.slug, partner.referral_code)}
                    className="text-sm"
                  />
                  <Button
                    variant="outline"
                    onClick={() => copyLink(selectedProduct)}
                  >
                    {copiedId === selectedProduct.id ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  className="flex-1 bg-green-600 hover:bg-green-700"
                  onClick={() => shareWhatsApp(selectedProduct)}
                >
                  <MessageCircle className="h-4 w-4 mr-2" />
                  Share on WhatsApp
                </Button>
                <Button
                  variant="outline"
                  className="flex-1"
                  asChild
                >
                  <a
                    href={`/products/${selectedProduct.slug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    View Product
                  </a>
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
