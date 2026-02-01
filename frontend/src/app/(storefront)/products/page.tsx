'use client';

import { useState, useEffect, Suspense, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import {
  ChevronRight,
  ChevronDown,
  ChevronUp,
  SlidersHorizontal,
  X,
  Package,
  Grid3X3,
  List,
  Star,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent } from '@/components/ui/card';
import ProductCard from '@/components/storefront/product/product-card';
import {
  StorefrontProduct,
  StorefrontCategory,
  StorefrontBrand,
  ProductFilters,
} from '@/types/storefront';
import { useProductsPageData, usePrefetchProduct } from '@/lib/storefront/hooks';
import { useDebounce } from '@/hooks/use-debounce';
import { formatCurrency } from '@/lib/utils';

// View mode storage key
const VIEW_MODE_KEY = 'd2c-products-view-mode';

// Get saved view mode from localStorage
function getSavedViewMode(): 'grid' | 'list' {
  if (typeof window === 'undefined') return 'grid';
  const saved = localStorage.getItem(VIEW_MODE_KEY);
  return saved === 'list' ? 'list' : 'grid';
}

// Save view mode to localStorage
function saveViewMode(mode: 'grid' | 'list') {
  if (typeof window === 'undefined') return;
  localStorage.setItem(VIEW_MODE_KEY, mode);
}

// Product List Item for List View
function ProductListItem({ product }: { product: StorefrontProduct }) {
  const primaryImage = product.images?.find((img) => img.is_primary) || product.images?.[0];
  const discount = product.mrp && product.selling_price
    ? Math.round((1 - product.selling_price / product.mrp) * 100)
    : 0;

  return (
    <Link href={`/products/${product.slug}`}>
      <Card className="overflow-hidden hover:shadow-md transition-shadow">
        <CardContent className="flex gap-4 p-4">
          {/* Image */}
          <div className="relative w-32 h-32 sm:w-40 sm:h-40 bg-muted rounded-lg overflow-hidden flex-shrink-0">
            {primaryImage?.image_url ? (
              <Image
                src={primaryImage.image_url}
                alt={product.name}
                fill
                className="object-cover"
                sizes="160px"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                <Package className="h-8 w-8" />
              </div>
            )}
            {discount > 0 && (
              <Badge className="absolute top-2 left-2 bg-red-500">
                {discount}% OFF
              </Badge>
            )}
          </div>

          {/* Details */}
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-base sm:text-lg line-clamp-2 hover:text-primary transition-colors">
              {product.name}
            </h3>

            {product.short_description && (
              <p className="text-sm text-muted-foreground mt-1 line-clamp-2 hidden sm:block">
                {product.short_description}
              </p>
            )}

            <div className="flex items-center gap-2 mt-2">
              {product.is_bestseller && (
                <Badge variant="secondary" className="text-xs">
                  <Star className="h-3 w-3 mr-1 fill-yellow-500 text-yellow-500" />
                  Bestseller
                </Badge>
              )}
              {product.is_new_arrival && (
                <Badge variant="outline" className="text-xs">
                  New
                </Badge>
              )}
            </div>

            {/* Price */}
            <div className="flex items-baseline gap-2 mt-3">
              <span className="text-lg sm:text-xl font-bold text-primary">
                {formatCurrency(product.selling_price || product.mrp)}
              </span>
              {product.selling_price && product.mrp > product.selling_price && (
                <>
                  <span className="text-sm text-muted-foreground line-through">
                    {formatCurrency(product.mrp)}
                  </span>
                  <span className="text-sm text-green-600 font-medium">
                    {discount}% off
                  </span>
                </>
              )}
            </div>

            {/* Category & Brand */}
            <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
              {product.category?.name && <span>{product.category.name}</span>}
              {product.category?.name && product.brand?.name && <span>|</span>}
              {product.brand?.name && <span>{product.brand.name}</span>}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

function ProductsContent() {
  const searchParams = useSearchParams();
  const prefetchProduct = usePrefetchProduct();

  const [currentPage, setCurrentPage] = useState(1);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Collapsible filter sections state
  const [openSections, setOpenSections] = useState({
    categories: true,
    brands: true,
    price: true,
    discount: false,
    productType: false,
  });

  // Initialize view mode from localStorage
  useEffect(() => {
    setViewMode(getSavedViewMode());
  }, []);

  const handleViewModeChange = (mode: 'grid' | 'list') => {
    setViewMode(mode);
    saveViewMode(mode);
  };

  const toggleSection = (section: keyof typeof openSections) => {
    setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  // Filters from URL - immediate state for UI
  const [filters, setFilters] = useState<ProductFilters>({
    category_id: searchParams.get('category') || undefined,
    brand_id: searchParams.get('brand') || undefined,
    min_price: searchParams.get('min_price')
      ? Number(searchParams.get('min_price'))
      : undefined,
    max_price: searchParams.get('max_price')
      ? Number(searchParams.get('max_price'))
      : undefined,
    is_bestseller: searchParams.get('is_bestseller') === 'true',
    is_new_arrival: searchParams.get('is_new_arrival') === 'true',
    search: searchParams.get('search') || undefined,
    sort_by: (searchParams.get('sort_by') as ProductFilters['sort_by']) || 'created_at',
    sort_order: (searchParams.get('sort_order') as ProductFilters['sort_order']) || 'desc',
    page: 1,
    size: 12,
  });

  // Debounce filters for API calls (300ms delay for price inputs)
  const debouncedFilters = useDebounce(filters, 300);

  // Combine debounced filters with current page
  const queryFilters = useMemo(() => ({
    ...debouncedFilters,
    page: currentPage,
  }), [debouncedFilters, currentPage]);

  // React Query hooks for data fetching with caching
  const {
    categories,
    brands,
    products,
    totalProducts,
    totalPages,
    isLoading: loading,
  } = useProductsPageData(queryFilters);

  const updateFilter = (key: keyof ProductFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setCurrentPage(1);
  };

  const clearFilters = () => {
    setFilters({
      sort_by: 'created_at',
      sort_order: 'desc',
      page: 1,
      size: 12,
    });
    setCurrentPage(1);
  };

  const hasActiveFilters =
    filters.category_id ||
    filters.brand_id ||
    filters.min_price ||
    filters.max_price ||
    filters.is_bestseller ||
    filters.is_new_arrival ||
    filters.search;

  // Prefetch product on hover for faster navigation
  const handleProductHover = (slug: string) => {
    prefetchProduct(slug);
  };

  // Filter sidebar content
  const FilterContent = () => (
    <div className="space-y-4">
      {/* Categories */}
      <Collapsible open={openSections.categories} onOpenChange={() => toggleSection('categories')}>
        <CollapsibleTrigger className="flex items-center justify-between w-full py-2 border-b">
          <span className="text-sm font-semibold">Categories</span>
          <div className="flex items-center gap-2">
            {filters.category_id && (
              <Badge variant="secondary" className="text-xs">1</Badge>
            )}
            {openSections.categories ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-3">
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {categories.map((category) => (
              <div key={category.id} className="flex items-center space-x-2">
                <Checkbox
                  id={`cat-${category.id}`}
                  checked={filters.category_id === category.id}
                  onCheckedChange={(checked) =>
                    updateFilter('category_id', checked ? category.id : undefined)
                  }
                />
                <label
                  htmlFor={`cat-${category.id}`}
                  className="text-sm cursor-pointer flex-1"
                >
                  {category.name}
                </label>
              </div>
            ))}
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Brands */}
      <Collapsible open={openSections.brands} onOpenChange={() => toggleSection('brands')}>
        <CollapsibleTrigger className="flex items-center justify-between w-full py-2 border-b">
          <span className="text-sm font-semibold">Brands</span>
          <div className="flex items-center gap-2">
            {filters.brand_id && (
              <Badge variant="secondary" className="text-xs">1</Badge>
            )}
            {openSections.brands ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-3">
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {brands.map((brand) => (
              <div key={brand.id} className="flex items-center space-x-2">
                <Checkbox
                  id={`brand-${brand.id}`}
                  checked={filters.brand_id === brand.id}
                  onCheckedChange={(checked) =>
                    updateFilter('brand_id', checked ? brand.id : undefined)
                  }
                />
                <label
                  htmlFor={`brand-${brand.id}`}
                  className="text-sm cursor-pointer flex-1"
                >
                  {brand.name}
                </label>
              </div>
            ))}
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Price Range */}
      <Collapsible open={openSections.price} onOpenChange={() => toggleSection('price')}>
        <CollapsibleTrigger className="flex items-center justify-between w-full py-2 border-b">
          <span className="text-sm font-semibold">Price Range</span>
          <div className="flex items-center gap-2">
            {(filters.min_price || filters.max_price) && (
              <Badge variant="secondary" className="text-xs">
                {filters.min_price && filters.max_price
                  ? `${formatCurrency(filters.min_price)} - ${formatCurrency(filters.max_price)}`
                  : filters.min_price
                  ? `Min: ${formatCurrency(filters.min_price)}`
                  : `Max: ${formatCurrency(filters.max_price!)}`}
              </Badge>
            )}
            {openSections.price ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-3">
          <div className="space-y-3">
            {/* Quick price filters */}
            <div className="flex flex-wrap gap-2">
              {[
                { label: 'Under 5K', max: 5000 },
                { label: '5K - 10K', min: 5000, max: 10000 },
                { label: '10K - 20K', min: 10000, max: 20000 },
                { label: '20K+', min: 20000 },
              ].map((range) => (
                <Button
                  key={range.label}
                  variant={
                    filters.min_price === range.min && filters.max_price === range.max
                      ? 'default'
                      : 'outline'
                  }
                  size="sm"
                  className="text-xs"
                  onClick={() => {
                    updateFilter('min_price', range.min);
                    updateFilter('max_price', range.max);
                  }}
                >
                  {range.label}
                </Button>
              ))}
            </div>
            {/* Custom range inputs */}
            <div className="flex items-center gap-2">
              <Input
                type="number"
                placeholder="Min"
                value={filters.min_price || ''}
                onChange={(e) =>
                  updateFilter(
                    'min_price',
                    e.target.value ? Number(e.target.value) : undefined
                  )
                }
                className="h-9"
              />
              <span className="text-muted-foreground">to</span>
              <Input
                type="number"
                placeholder="Max"
                value={filters.max_price || ''}
                onChange={(e) =>
                  updateFilter(
                    'max_price',
                    e.target.value ? Number(e.target.value) : undefined
                  )
                }
                className="h-9"
              />
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Product Type */}
      <Collapsible open={openSections.productType} onOpenChange={() => toggleSection('productType')}>
        <CollapsibleTrigger className="flex items-center justify-between w-full py-2 border-b">
          <span className="text-sm font-semibold">Product Type</span>
          <div className="flex items-center gap-2">
            {(filters.is_bestseller || filters.is_new_arrival) && (
              <Badge variant="secondary" className="text-xs">
                {(filters.is_bestseller ? 1 : 0) + (filters.is_new_arrival ? 1 : 0)}
              </Badge>
            )}
            {openSections.productType ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-3">
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="bestseller"
                checked={filters.is_bestseller || false}
                onCheckedChange={(checked) =>
                  updateFilter('is_bestseller', checked || undefined)
                }
              />
              <label htmlFor="bestseller" className="text-sm cursor-pointer flex items-center gap-1">
                <Star className="h-3.5 w-3.5 text-yellow-500 fill-yellow-500" />
                Bestsellers
              </label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="new-arrival"
                checked={filters.is_new_arrival || false}
                onCheckedChange={(checked) =>
                  updateFilter('is_new_arrival', checked || undefined)
                }
              />
              <label htmlFor="new-arrival" className="text-sm cursor-pointer">
                New Arrivals
              </label>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Clear Filters */}
      {hasActiveFilters && (
        <Button
          variant="outline"
          className="w-full mt-4"
          onClick={clearFilters}
        >
          <X className="h-4 w-4 mr-2" />
          Clear All Filters
        </Button>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-muted/50">
      <div className="container mx-auto px-4 py-6">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
          <Link href="/" className="hover:text-primary">
            Home
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground">Products</span>
        </nav>

        <div className="flex gap-8">
          {/* Sidebar - Desktop */}
          <aside className="hidden lg:block w-64 flex-shrink-0">
            <div className="sticky top-24 bg-card rounded-lg p-6 shadow-sm">
              <h3 className="font-semibold mb-4">Filters</h3>
              <FilterContent />
            </div>
          </aside>

          {/* Main Content */}
          <div className="flex-1">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold">
                  {filters.search
                    ? `Search: "${filters.search}"`
                    : 'All Products'}
                </h1>
                <p className="text-muted-foreground">
                  {totalProducts} products found
                </p>
              </div>

              <div className="flex items-center gap-2 md:gap-3">
                {/* Mobile Filters */}
                <Sheet
                  open={mobileFiltersOpen}
                  onOpenChange={setMobileFiltersOpen}
                >
                  <SheetTrigger asChild>
                    <Button variant="outline" size="sm" className="lg:hidden">
                      <SlidersHorizontal className="h-4 w-4 mr-2" />
                      Filters
                      {hasActiveFilters && (
                        <Badge variant="secondary" className="ml-1 h-5 w-5 p-0 flex items-center justify-center text-xs">
                          {[
                            filters.category_id,
                            filters.brand_id,
                            filters.min_price || filters.max_price,
                            filters.is_bestseller,
                            filters.is_new_arrival,
                          ].filter(Boolean).length}
                        </Badge>
                      )}
                    </Button>
                  </SheetTrigger>
                  <SheetContent side="left">
                    <SheetHeader>
                      <SheetTitle>Filters</SheetTitle>
                    </SheetHeader>
                    <div className="mt-6 overflow-y-auto max-h-[calc(100vh-120px)]">
                      <FilterContent />
                    </div>
                  </SheetContent>
                </Sheet>

                {/* View Toggle */}
                <div className="hidden md:flex items-center border rounded-lg">
                  <Button
                    variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="rounded-r-none"
                    onClick={() => handleViewModeChange('grid')}
                  >
                    <Grid3X3 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="rounded-l-none"
                    onClick={() => handleViewModeChange('list')}
                  >
                    <List className="h-4 w-4" />
                  </Button>
                </div>

                {/* Sort */}
                <Select
                  value={`${filters.sort_by}-${filters.sort_order}`}
                  onValueChange={(value) => {
                    const [sortBy, sortOrder] = value.split('-');
                    updateFilter('sort_by', sortBy);
                    updateFilter('sort_order', sortOrder);
                  }}
                >
                  <SelectTrigger className="w-[140px] md:w-[180px]">
                    <SelectValue placeholder="Sort by" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="created_at-desc">Newest First</SelectItem>
                    <SelectItem value="created_at-asc">Oldest First</SelectItem>
                    <SelectItem value="selling_price-asc">Price: Low to High</SelectItem>
                    <SelectItem value="selling_price-desc">Price: High to Low</SelectItem>
                    <SelectItem value="name-asc">Name: A to Z</SelectItem>
                    <SelectItem value="name-desc">Name: Z to A</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Active Filters */}
            {hasActiveFilters && (
              <div className="flex flex-wrap gap-2 mb-4">
                {filters.search && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => updateFilter('search', undefined)}
                  >
                    Search: {filters.search}
                    <X className="h-3 w-3 ml-1" />
                  </Button>
                )}
                {filters.category_id && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => updateFilter('category_id', undefined)}
                  >
                    Category
                    <X className="h-3 w-3 ml-1" />
                  </Button>
                )}
                {filters.brand_id && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => updateFilter('brand_id', undefined)}
                  >
                    Brand
                    <X className="h-3 w-3 ml-1" />
                  </Button>
                )}
              </div>
            )}

            {/* Products Grid/List */}
            {loading ? (
              <div className={viewMode === 'grid'
                ? "grid grid-cols-2 md:grid-cols-3 gap-4 md:gap-6"
                : "space-y-4"
              }>
                {Array.from({ length: 6 }).map((_, i) => (
                  viewMode === 'grid' ? (
                    <div key={i} className="space-y-3">
                      <Skeleton className="aspect-square rounded-lg" />
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-4 w-1/2" />
                      <Skeleton className="h-6 w-1/3" />
                    </div>
                  ) : (
                    <Card key={i}>
                      <CardContent className="flex gap-4 p-4">
                        <Skeleton className="w-32 h-32 rounded-lg" />
                        <div className="flex-1 space-y-2">
                          <Skeleton className="h-5 w-3/4" />
                          <Skeleton className="h-4 w-full" />
                          <Skeleton className="h-6 w-1/4" />
                        </div>
                      </CardContent>
                    </Card>
                  )
                ))}
              </div>
            ) : products.length === 0 ? (
              <div className="text-center py-16">
                <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No products found</h3>
                <p className="text-muted-foreground mb-4">
                  Try adjusting your filters or search terms
                </p>
                <Button onClick={clearFilters}>Clear Filters</Button>
              </div>
            ) : (
              <>
                {viewMode === 'grid' ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 md:gap-6">
                    {products.map((product) => (
                      <div key={product.id} onMouseEnter={() => handleProductHover(product.slug)}>
                        <ProductCard product={product} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {products.map((product) => (
                      <div key={product.id} onMouseEnter={() => handleProductHover(product.slug)}>
                        <ProductListItem product={product} />
                      </div>
                    ))}
                  </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex justify-center gap-2 mt-8">
                    <Button
                      variant="outline"
                      disabled={currentPage === 1}
                      onClick={() => setCurrentPage((p) => p - 1)}
                    >
                      Previous
                    </Button>
                    <div className="flex items-center gap-1">
                      {Array.from({ length: Math.min(5, totalPages) }).map(
                        (_, i) => {
                          const page = i + 1;
                          return (
                            <Button
                              key={page}
                              variant={
                                currentPage === page ? 'default' : 'outline'
                              }
                              size="icon"
                              onClick={() => setCurrentPage(page)}
                            >
                              {page}
                            </Button>
                          );
                        }
                      )}
                    </div>
                    <Button
                      variant="outline"
                      disabled={currentPage === totalPages}
                      onClick={() => setCurrentPage((p) => p + 1)}
                    >
                      Next
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ProductsPage() {
  return (
    <Suspense
      fallback={
        <div className="container mx-auto px-4 py-6">
          <Skeleton className="h-8 w-48 mb-6" />
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
      }
    >
      <ProductsContent />
    </Suspense>
  );
}
