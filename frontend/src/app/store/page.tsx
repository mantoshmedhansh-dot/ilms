import { Suspense } from 'react';
import { Metadata } from 'next';
import HeroBanner from '@/components/storefront/home/hero-banner';
import CategoryGrid from '@/components/storefront/home/category-grid';
import ProductSection from '@/components/storefront/home/product-section';
import WhyChooseUs from '@/components/storefront/home/why-choose-us';
import TrustStats from '@/components/storefront/home/trust-stats';
import Testimonials from '@/components/storefront/home/testimonials';
import RecentlyViewedWrapper from '@/components/storefront/product/recently-viewed-wrapper';
import { WaterQualityBanner } from '@/components/storefront/tools/water-quality-calculator';
import { Skeleton } from '@/components/ui/skeleton';
import {
  getHomepageData,
  getCompanyInfo,
} from '@/lib/storefront/server-api';

// ISR: Revalidate homepage every 60 seconds
export const revalidate = 60;

// Generate metadata
export async function generateMetadata(): Promise<Metadata> {
  const company = await getCompanyInfo();

  return {
    title: `${company.name} - Pure Water, Healthy Life`,
    description:
      "India's trusted water purifier brand. Advanced RO, UV, and UF water purification systems for homes and offices.",
    openGraph: {
      title: `${company.name} - Pure Water, Healthy Life`,
      description:
        "India's trusted water purifier brand. Advanced RO, UV, and UF water purification systems for homes and offices.",
      type: 'website',
    },
  };
}

// Loading skeleton for product sections
function ProductSectionSkeleton({ title }: { title: string }) {
  return (
    <section className="py-12 md:py-16">
      <div className="container mx-auto px-4">
        <div className="mb-8">
          <h2 className="text-2xl md:text-3xl font-bold">{title}</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="aspect-square rounded-lg" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-6 w-1/3" />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// CTA Section Component
async function CTASection() {
  const company = await getCompanyInfo();

  return (
    <section className="py-16 bg-gradient-to-r from-primary to-primary/80 text-white">
      <div className="container mx-auto px-4 text-center">
        <h2 className="text-2xl md:text-3xl font-bold mb-4">
          Need Help Choosing the Right Purifier?
        </h2>
        <p className="text-lg text-white/80 mb-6 max-w-2xl mx-auto">
          Our experts are here to help you find the perfect water purification
          solution for your home or office.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <a
            href={`tel:${company.phone?.replace(/[^0-9+]/g, '') || '18001234567'}`}
            className="inline-flex items-center justify-center px-6 py-3 bg-background text-primary font-semibold rounded-lg hover:bg-muted transition-colors"
          >
            Call {company.phone || '1800-123-4567'}
          </a>
          <a
            href="/contact"
            className="inline-flex items-center justify-center px-6 py-3 border-2 border-white text-white font-semibold rounded-lg hover:bg-white/10 transition-colors"
          >
            Contact Us
          </a>
        </div>
      </div>
    </section>
  );
}

// Main Homepage Component (Server Component with ISR)
export default async function HomePage() {
  // Fetch all homepage data with ISR caching
  const homepageData = await getHomepageData();

  const {
    categories,
    bestseller_products: bestsellers,
    new_arrivals: newArrivals,
    featured_products: featured,
  } = homepageData;

  return (
    <>
      {/* Hero Banner */}
      <HeroBanner />

      {/* Categories */}
      <CategoryGrid categories={categories} />

      {/* Bestsellers */}
      {bestsellers.length > 0 && (
        <ProductSection
          title="Bestsellers"
          subtitle="Our most popular products loved by customers"
          products={bestsellers}
          viewAllLink="/products?is_bestseller=true"
        />
      )}

      {/* Water Quality Calculator Banner */}
      <section className="py-8">
        <div className="container mx-auto px-4">
          <WaterQualityBanner />
        </div>
      </section>

      {/* Why Choose Us */}
      <WhyChooseUs />

      {/* New Arrivals */}
      {newArrivals.length > 0 && (
        <ProductSection
          title="New Arrivals"
          subtitle="Discover our latest water purification solutions"
          products={newArrivals}
          viewAllLink="/products?is_new_arrival=true"
        />
      )}

      {/* Featured Products */}
      {featured.length > 0 && (
        <div className="bg-muted/50">
          <ProductSection
            title="Featured Products"
            subtitle="Handpicked products for you"
            products={featured}
            viewAllLink="/products?is_featured=true"
          />
        </div>
      )}

      {/* Recently Viewed Products (Client Component) */}
      <Suspense fallback={<ProductSectionSkeleton title="Recently Viewed" />}>
        <RecentlyViewedWrapper maxItems={8} />
      </Suspense>

      {/* Trust Stats */}
      <TrustStats />

      {/* Testimonials */}
      <Testimonials />

      {/* CTA Section */}
      <CTASection />
    </>
  );
}
