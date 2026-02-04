/**
 * Server-side API utilities for ISR (Incremental Static Regeneration)
 * These functions use native fetch with Next.js caching options
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const STOREFRONT_PATH = '/api/v1/storefront';

// Cache revalidation times (in seconds)
export const REVALIDATE_TIMES = {
  HOMEPAGE: 60,           // 1 minute - frequently updated content
  PRODUCTS_LIST: 60,      // 1 minute - product list changes often
  PRODUCT_DETAIL: 300,    // 5 minutes - individual product details
  CATEGORIES: 600,        // 10 minutes - categories rarely change
  CATEGORY_PRODUCTS: 120, // 2 minutes - category products
  COMPANY_INFO: 3600,     // 1 hour - company info rarely changes
  MEGA_MENU: 600,         // 10 minutes - navigation structure
  BANNERS: 300,           // 5 minutes - promotional banners
  TESTIMONIALS: 1800,     // 30 minutes - testimonials
};

/**
 * Generic server-side fetch with ISR caching
 */
async function serverFetch<T>(
  endpoint: string,
  options?: {
    revalidate?: number;
    tags?: string[];
  }
): Promise<T | null> {
  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      next: {
        revalidate: options?.revalidate ?? 60,
        tags: options?.tags,
      },
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.error(`Server fetch error: ${response.status} for ${endpoint}`);
      return null;
    }

    return response.json();
  } catch (error) {
    console.error(`Server fetch failed for ${endpoint}:`, error);
    return null;
  }
}

// Types (matching the client-side types)
export interface ServerProduct {
  id: string;
  name: string;
  slug: string;
  sku: string;
  short_description?: string;
  description?: string;
  mrp: number;
  selling_price?: number;
  cost_price?: number;
  hsn_code?: string;
  gst_rate?: number;
  is_active: boolean;
  is_featured: boolean;
  is_bestseller: boolean;
  is_new_arrival: boolean;
  in_stock: boolean;
  stock_quantity?: number;
  warranty_months?: number;
  features?: string;
  category_id?: string;
  brand_id?: string;
  category?: {
    id: string;
    name: string;
    slug: string;
  };
  brand?: {
    id: string;
    name: string;
    slug: string;
    logo_url?: string;
  };
  images?: Array<{
    id: string;
    image_url: string;
    thumbnail_url?: string;
    alt_text?: string;
    is_primary: boolean;
  }>;
  specifications?: Array<{
    id: string;
    key: string;
    value: string;
    group_name?: string;
    display_order?: number;
  }>;
  variants?: Array<{
    id: string;
    name: string;
    sku: string;
    mrp: number;
    selling_price?: number;
    in_stock: boolean;
    stock_quantity?: number;
    attributes?: Record<string, string>;
  }>;
}

export interface ServerCategory {
  id: string;
  name: string;
  slug: string;
  description?: string;
  image_url?: string;
  is_active: boolean;
  parent_id?: string;
  children?: ServerCategory[];
  product_count?: number;
}

export interface ServerBrand {
  id: string;
  name: string;
  slug: string;
  logo_url?: string;
  description?: string;
  is_active: boolean;
}

export interface ServerBanner {
  id: string;
  title: string;
  subtitle?: string;
  image_url: string;
  mobile_image_url?: string;
  cta_text?: string;
  cta_link?: string;
  text_position: 'left' | 'center' | 'right';
  text_color: 'white' | 'dark';
}

export interface ServerTestimonial {
  id: string;
  customer_name: string;
  customer_location?: string;
  customer_avatar_url?: string;
  rating: number;
  content: string;
  title?: string;
  product_name?: string;
}

export interface ServerUsp {
  id: string;
  title: string;
  description?: string;
  icon: string;
  icon_color?: string;
}

export interface ServerHomepageData {
  categories: ServerCategory[];
  featured_products: ServerProduct[];
  bestseller_products: ServerProduct[];
  new_arrivals: ServerProduct[];
  banners: ServerBanner[];
  brands: ServerBrand[];
  usps: ServerUsp[];
  testimonials: ServerTestimonial[];
}

export interface ServerCompanyInfo {
  name: string;
  trade_name?: string;
  email?: string;
  phone?: string;
  website?: string;
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  logo_url?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Server-side API functions with ISR

/**
 * Get homepage data with ISR caching
 */
export async function getHomepageData(): Promise<ServerHomepageData> {
  const data = await serverFetch<ServerHomepageData>(
    `${STOREFRONT_PATH}/homepage`,
    {
      revalidate: REVALIDATE_TIMES.HOMEPAGE,
      tags: ['homepage'],
    }
  );

  return data || {
    categories: [],
    featured_products: [],
    bestseller_products: [],
    new_arrivals: [],
    banners: [],
    brands: [],
    usps: [],
    testimonials: [],
  };
}

/**
 * Get all categories with ISR caching
 */
export async function getCategories(): Promise<ServerCategory[]> {
  const data = await serverFetch<ServerCategory[]>(
    `${STOREFRONT_PATH}/categories`,
    {
      revalidate: REVALIDATE_TIMES.CATEGORIES,
      tags: ['categories'],
    }
  );

  return data || [];
}

/**
 * Get category by slug with ISR caching
 */
export async function getCategoryBySlug(slug: string): Promise<ServerCategory | null> {
  const categories = await getCategories();

  const findCategory = (cats: ServerCategory[]): ServerCategory | null => {
    for (const cat of cats) {
      if (cat.slug === slug) return cat;
      if (cat.children) {
        const found = findCategory(cat.children);
        if (found) return found;
      }
    }
    return null;
  };

  return findCategory(categories);
}

/**
 * Get all category slugs for static generation
 */
export async function getAllCategorySlugs(): Promise<string[]> {
  const categories = await getCategories();

  const collectSlugs = (cats: ServerCategory[]): string[] => {
    const slugs: string[] = [];
    for (const cat of cats) {
      if (cat.slug) slugs.push(cat.slug);
      if (cat.children) {
        slugs.push(...collectSlugs(cat.children));
      }
    }
    return slugs;
  };

  return collectSlugs(categories);
}

/**
 * Get product by slug with ISR caching
 */
export async function getProductBySlug(slug: string): Promise<ServerProduct | null> {
  return serverFetch<ServerProduct>(
    `${STOREFRONT_PATH}/products/${slug}`,
    {
      revalidate: REVALIDATE_TIMES.PRODUCT_DETAIL,
      tags: ['products', `product-${slug}`],
    }
  );
}

/**
 * Get products list with filters and ISR caching
 */
export async function getProducts(params?: {
  category_id?: string;
  brand_id?: string;
  is_featured?: boolean;
  is_bestseller?: boolean;
  is_new_arrival?: boolean;
  search?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  size?: number;
}): Promise<PaginatedResponse<ServerProduct>> {
  const searchParams = new URLSearchParams();

  if (params) {
    if (params.category_id) searchParams.append('category_id', params.category_id);
    if (params.brand_id) searchParams.append('brand_id', params.brand_id);
    if (params.is_featured) searchParams.append('is_featured', 'true');
    if (params.is_bestseller) searchParams.append('is_bestseller', 'true');
    if (params.is_new_arrival) searchParams.append('is_new_arrival', 'true');
    if (params.search) searchParams.append('search', params.search);
    if (params.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params.sort_order) searchParams.append('sort_order', params.sort_order);
    if (params.page) searchParams.append('page', params.page.toString());
    if (params.size) searchParams.append('size', params.size.toString());
  }

  const queryString = searchParams.toString();
  const endpoint = `${STOREFRONT_PATH}/products${queryString ? `?${queryString}` : ''}`;

  const data = await serverFetch<PaginatedResponse<ServerProduct>>(
    endpoint,
    {
      revalidate: REVALIDATE_TIMES.PRODUCTS_LIST,
      tags: ['products'],
    }
  );

  return data || { items: [], total: 0, page: 1, size: 12, pages: 0 };
}

/**
 * Get all product slugs for static generation
 */
export async function getAllProductSlugs(): Promise<string[]> {
  // Fetch all products (might need pagination for large catalogs)
  const response = await getProducts({ size: 1000 });
  return response.items.map(p => p.slug).filter(Boolean);
}

/**
 * Get related products with ISR caching
 */
export async function getRelatedProducts(
  productId: string,
  categoryId?: string,
  limit = 4
): Promise<ServerProduct[]> {
  const params = new URLSearchParams();
  params.append('size', limit.toString());
  if (categoryId) params.append('category_id', categoryId);

  const data = await serverFetch<PaginatedResponse<ServerProduct>>(
    `${STOREFRONT_PATH}/products?${params.toString()}`,
    {
      revalidate: REVALIDATE_TIMES.PRODUCTS_LIST,
      tags: ['products'],
    }
  );

  // Filter out the current product
  return (data?.items || []).filter(p => p.id !== productId).slice(0, limit);
}

/**
 * Get company info with ISR caching
 */
export async function getCompanyInfo(): Promise<ServerCompanyInfo> {
  const data = await serverFetch<ServerCompanyInfo>(
    `${STOREFRONT_PATH}/company`,
    {
      revalidate: REVALIDATE_TIMES.COMPANY_INFO,
      tags: ['company'],
    }
  );

  return data || {
    name: 'ILMS.AI',
    trade_name: 'ILMS.AI',
    email: 'support@ilms.ai',
    phone: '1800-123-4567',
  };
}

/**
 * Get bestsellers with ISR caching
 */
export async function getBestsellers(limit = 8): Promise<ServerProduct[]> {
  const response = await getProducts({ is_bestseller: true, size: limit });
  return response.items;
}

/**
 * Get new arrivals with ISR caching
 */
export async function getNewArrivals(limit = 8): Promise<ServerProduct[]> {
  const response = await getProducts({
    is_new_arrival: true,
    size: limit,
    sort_by: 'created_at',
    sort_order: 'desc',
  });
  return response.items;
}

/**
 * Get featured products with ISR caching
 */
export async function getFeaturedProducts(limit = 8): Promise<ServerProduct[]> {
  const response = await getProducts({ is_featured: true, size: limit });
  return response.items;
}

/**
 * Get banners with ISR caching
 */
export async function getBanners(): Promise<ServerBanner[]> {
  const data = await serverFetch<ServerBanner[]>(
    `${STOREFRONT_PATH}/banners`,
    {
      revalidate: REVALIDATE_TIMES.BANNERS,
      tags: ['banners'],
    }
  );

  return data || [];
}

/**
 * Get testimonials with ISR caching
 */
export async function getTestimonials(): Promise<ServerTestimonial[]> {
  const data = await serverFetch<ServerTestimonial[]>(
    `${STOREFRONT_PATH}/testimonials`,
    {
      revalidate: REVALIDATE_TIMES.TESTIMONIALS,
      tags: ['testimonials'],
    }
  );

  return data || [];
}

/**
 * Get products by category with ISR caching
 */
export async function getProductsByCategory(
  categoryId: string,
  options?: {
    page?: number;
    size?: number;
    sort_by?: string;
    sort_order?: string;
  }
): Promise<PaginatedResponse<ServerProduct>> {
  return getProducts({
    category_id: categoryId,
    ...options,
  });
}
