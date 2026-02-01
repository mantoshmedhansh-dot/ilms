import { Suspense } from 'react';
import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { Skeleton } from '@/components/ui/skeleton';
import CategoryPageClient from '@/components/storefront/category/category-page-client';
import {
  getCategoryBySlug,
  getProductsByCategory,
  getAllCategorySlugs,
  type ServerCategory,
  type ServerProduct,
} from '@/lib/storefront/server-api';

// ISR: Revalidate category pages every 2 minutes
export const revalidate = 120;

// Generate static params for known categories at build time
export async function generateStaticParams() {
  try {
    const slugs = await getAllCategorySlugs();
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
  const category = await getCategoryBySlug(slug);

  if (!category) {
    return {
      title: 'Category Not Found',
    };
  }

  return {
    title: `${category.name} - Water Purifiers`,
    description: category.description || `Browse ${category.name} products at AQUAPURITE`,
    openGraph: {
      title: `${category.name} - Water Purifiers`,
      description: category.description || `Browse ${category.name} products at AQUAPURITE`,
      images: category.image_url ? [category.image_url] : undefined,
      type: 'website',
    },
  };
}

// Loading component
function CategoryPageSkeleton() {
  return (
    <div className="min-h-screen bg-muted/50">
      <div className="container mx-auto px-4 py-6">
        <Skeleton className="h-6 w-64 mb-6" />
        <Skeleton className="h-10 w-48 mb-4" />
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="aspect-square rounded-lg" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-6 w-1/3" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Main Category Page (Server Component with ISR)
export default async function CategoryPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  // Fetch category and initial products with ISR caching
  const category = await getCategoryBySlug(slug);

  if (!category) {
    notFound();
  }

  // Get initial products for the category
  const initialProductsResponse = await getProductsByCategory(category.id, {
    page: 1,
    size: 12,
    sort_by: 'created_at',
    sort_order: 'desc',
  });

  return (
    <Suspense fallback={<CategoryPageSkeleton />}>
      <CategoryPageClient
        category={category}
        initialProducts={initialProductsResponse.items}
        initialTotalProducts={initialProductsResponse.total}
        slug={slug}
      />
    </Suspense>
  );
}
