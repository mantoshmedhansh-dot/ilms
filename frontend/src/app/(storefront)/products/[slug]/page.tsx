import { Suspense } from 'react';
import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ChevronRight, Package } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import ProductDetailClient from '@/components/storefront/product/product-detail-client';
import RecentlyViewedWrapper from '@/components/storefront/product/recently-viewed-wrapper';
import {
  getProductBySlug,
  getRelatedProducts,
  getAllProductSlugs,
} from '@/lib/storefront/server-api';

// ISR: Revalidate product pages every 5 minutes
export const revalidate = 300;

// Generate static params for known products at build time
export async function generateStaticParams() {
  try {
    const slugs = await getAllProductSlugs();
    return slugs.map((slug) => ({ slug }));
  } catch {
    return [];
  }
}

// Generate metadata for SEO
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const product = await getProductBySlug(slug);

  if (!product) {
    return {
      title: 'Product Not Found',
    };
  }

  const primaryImage = product.images?.find((img) => img.is_primary) || product.images?.[0];

  return {
    title: product.name,
    description: product.short_description || product.description?.substring(0, 160),
    openGraph: {
      title: product.name,
      description: product.short_description || product.description?.substring(0, 160),
      images: primaryImage?.image_url ? [primaryImage.image_url] : undefined,
      type: 'website',
    },
  };
}

// Loading skeleton
function ProductDetailSkeleton() {
  return (
    <div className="container mx-auto px-4 py-6">
      <Skeleton className="h-6 w-64 mb-6" />
      <div className="grid lg:grid-cols-2 gap-8">
        <Skeleton className="aspect-square rounded-lg" />
        <div className="space-y-4">
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-6 w-1/2" />
          <Skeleton className="h-10 w-1/3" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      </div>
    </div>
  );
}

// Related Products Section (Server Component)
async function RelatedProductsSection({
  productId,
  categoryId,
}: {
  productId: string;
  categoryId?: string;
}) {
  const relatedProducts = await getRelatedProducts(productId, categoryId, 4);

  if (relatedProducts.length === 0) return null;

  // Dynamic import for client component
  const ProductCard = (await import('@/components/storefront/product/product-card')).default;

  return (
    <div className="bg-card rounded-lg shadow-sm p-6">
      <h2 className="text-xl font-bold mb-6">Related Products</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {relatedProducts.slice(0, 4).map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
}

// Main Product Detail Page (Server Component with ISR)
export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  // Fetch product data with ISR caching
  const product = await getProductBySlug(slug);

  if (!product) {
    notFound();
  }

  return (
    <div className="bg-muted/50 min-h-screen">
      <div className="container mx-auto px-4 py-6">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
          <Link href="/" className="hover:text-primary">
            Home
          </Link>
          <ChevronRight className="h-4 w-4" />
          <Link href="/products" className="hover:text-primary">
            Products
          </Link>
          {product.category && (
            <>
              <ChevronRight className="h-4 w-4" />
              <Link
                href={`/category/${product.category.slug}`}
                className="hover:text-primary"
              >
                {product.category.name}
              </Link>
            </>
          )}
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground truncate max-w-[200px]">
            {product.name}
          </span>
        </nav>

        {/* Product Detail Section (Client Component for interactivity) */}
        <ProductDetailClient product={product} />

        {/* Related Products */}
        <Suspense fallback={<Skeleton className="h-64 w-full rounded-lg mt-8" />}>
          <div className="mt-8">
            <RelatedProductsSection
              productId={product.id}
              categoryId={product.category_id}
            />
          </div>
        </Suspense>

        {/* Recently Viewed Products */}
        <div className="bg-card rounded-lg shadow-sm p-6 mt-8">
          <Suspense fallback={<Skeleton className="h-48 w-full" />}>
            <RecentlyViewedWrapper excludeProductId={product.id} maxItems={6} />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
