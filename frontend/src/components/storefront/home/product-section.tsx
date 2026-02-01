'use client';

import Link from 'next/link';
import { ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import ProductCard from '../product/product-card';

// Common product interface that works with both server and client products
interface BaseProduct {
  id: string;
  name: string;
  slug: string;
  mrp: number;
  selling_price?: number | null;
  is_bestseller?: boolean;
  is_new_arrival?: boolean;
  images?: Array<{
    id: string;
    image_url: string;
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

interface ProductSectionProps {
  title: string;
  subtitle?: string;
  products: BaseProduct[];
  viewAllLink?: string;
  viewAllText?: string;
}

export default function ProductSection({
  title,
  subtitle,
  products,
  viewAllLink,
  viewAllText = 'View All',
}: ProductSectionProps) {
  if (products.length === 0) {
    return null;
  }

  return (
    <section className="py-12 md:py-16">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2
              className="text-2xl md:text-3xl font-bold"
              style={{ textWrap: 'balance' } as React.CSSProperties}
            >
              {title}
            </h2>
            {subtitle && (
              <p className="text-muted-foreground mt-1 max-w-lg">{subtitle}</p>
            )}
          </div>
          {viewAllLink && (
            <Button variant="ghost" asChild>
              <Link href={viewAllLink} className="group">
                {viewAllText}
                <ChevronRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform" />
              </Link>
            </Button>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6">
          {products.slice(0, 8).map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </div>
    </section>
  );
}
