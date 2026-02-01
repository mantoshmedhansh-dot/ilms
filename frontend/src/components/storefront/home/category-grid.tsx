'use client';

import Link from 'next/link';
import { Droplet, Filter, Cog, Wrench, Package, Zap, ThermometerSun, Shield } from 'lucide-react';

// Common category interface that works with both server and client categories
interface BaseCategory {
  id: string;
  name: string;
  slug: string;
  icon?: string;
  image_url?: string;
  children?: BaseCategory[];
}

interface CategoryGridProps {
  categories: BaseCategory[];
}

// Default categories if API returns empty - Water Purifiers and Spare Parts prominently displayed
const defaultCategories: Array<{ id: string; name: string; slug: string; icon: string; image_url?: string }> = [
  { id: '1', name: 'Water Purifiers', slug: 'water-purifiers', icon: 'droplet' },
  { id: '2', name: 'Spare Parts', slug: 'spare-parts', icon: 'cog' },
];

const iconMap: Record<string, React.ElementType> = {
  droplet: Droplet,
  filter: Filter,
  cog: Cog,
  wrench: Wrench,
  package: Package,
  zap: Zap,
  thermometer: ThermometerSun,
  shield: Shield,
  ro: Droplet,
  uv: Zap,
  'ro-uv': Shield,
  'hot-cold': ThermometerSun,
  'water-purifiers': Droplet,
  'spare-parts': Cog,
};

export default function CategoryGrid({ categories }: CategoryGridProps) {
  // Use provided categories or default to Water Purifiers and Spare Parts
  const displayCategories = categories.length > 0
    ? categories.slice(0, 6).map((cat) => ({
        id: cat.id,
        name: cat.name,
        slug: cat.slug,
        icon: cat.icon || cat.slug || 'droplet',
        image_url: cat.image_url,
      }))
    : defaultCategories;

  // Determine grid classes based on number of categories for proper centering
  const getGridClasses = () => {
    const count = displayCategories.length;
    if (count <= 2) {
      return 'flex flex-wrap justify-center gap-8 md:gap-16';
    } else if (count <= 3) {
      return 'flex flex-wrap justify-center gap-6 md:gap-12';
    } else if (count <= 4) {
      return 'grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-8 max-w-3xl mx-auto';
    }
    return 'grid grid-cols-3 md:grid-cols-6 gap-4 md:gap-8';
  };

  return (
    <section className="py-12 md:py-16">
      <div className="container mx-auto px-4">
        <div className="text-center mb-10">
          <h2
            className="text-2xl md:text-3xl font-bold mb-2"
            style={{ textWrap: 'balance' } as React.CSSProperties}
          >
            Shop by Category
          </h2>
          <p className="text-muted-foreground max-w-md mx-auto">
            Find the perfect water purification solution for your home or office
          </p>
        </div>

        {/* Categories - Centered layout */}
        <div className={getGridClasses()}>
          {displayCategories.map((category) => {
            const Icon = iconMap[category.icon] || iconMap[category.slug] || Droplet;

            return (
              <Link
                key={category.id}
                href={`/category/${category.slug}`}
                className="group flex flex-col items-center text-center"
              >
                {/* Icon Container */}
                <div className="w-24 h-24 md:w-28 md:h-28 rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center mb-3 group-hover:from-primary group-hover:to-primary/90 group-hover:scale-105 transition-all duration-300 shadow-sm group-hover:shadow-lg border border-primary/10 group-hover:border-primary/20">
                  {category.image_url ? (
                    <img
                      src={category.image_url}
                      alt=""
                      width={64}
                      height={64}
                      className="w-14 h-14 md:w-16 md:h-16 object-contain"
                      loading="lazy"
                    />
                  ) : (
                    <Icon className="w-12 h-12 md:w-14 md:h-14 text-primary group-hover:text-primary-foreground transition-colors drop-shadow-sm" />
                  )}
                </div>
                {/* Category Name */}
                <span className="text-sm md:text-base font-semibold text-foreground group-hover:text-primary transition-colors">
                  {category.name}
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
