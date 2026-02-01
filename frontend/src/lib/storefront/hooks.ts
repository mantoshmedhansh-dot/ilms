'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  productsApi,
  categoriesApi,
  brandsApi,
  contentApi,
  companyApi,
  homepageApi,
} from './api';
import { ProductFilters } from '@/types/storefront';

// Query keys for storefront data
export const storefrontKeys = {
  all: ['storefront'] as const,
  products: () => [...storefrontKeys.all, 'products'] as const,
  productList: (filters: ProductFilters) => [...storefrontKeys.products(), filters] as const,
  productDetail: (slug: string) => [...storefrontKeys.products(), 'detail', slug] as const,
  categories: () => [...storefrontKeys.all, 'categories'] as const,
  categoryTree: () => [...storefrontKeys.categories(), 'tree'] as const,
  brands: () => [...storefrontKeys.all, 'brands'] as const,
  company: () => [...storefrontKeys.all, 'company'] as const,
  banners: () => [...storefrontKeys.all, 'banners'] as const,
  usps: () => [...storefrontKeys.all, 'usps'] as const,
  testimonials: () => [...storefrontKeys.all, 'testimonials'] as const,
  settings: (group?: string) => [...storefrontKeys.all, 'settings', group] as const,
  featureBars: () => [...storefrontKeys.all, 'feature-bars'] as const,
  homepage: () => [...storefrontKeys.all, 'homepage'] as const,
  megaMenu: () => [...storefrontKeys.all, 'mega-menu'] as const,
};

/**
 * Fetch paginated products list with filters
 * Cached for 2 minutes, auto-refetches when filters change
 */
export function useProducts(filters: ProductFilters) {
  return useQuery({
    queryKey: storefrontKeys.productList(filters),
    queryFn: () => productsApi.list(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (previously cacheTime)
  });
}

/**
 * Fetch single product by slug
 * Cached for 5 minutes
 */
export function useProduct(slug: string) {
  return useQuery({
    queryKey: storefrontKeys.productDetail(slug),
    queryFn: () => productsApi.getBySlug(slug),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    enabled: !!slug,
  });
}

/**
 * Fetch category tree for mega menu
 * Cached for 10 minutes (categories change rarely)
 */
export function useCategoryTree() {
  return useQuery({
    queryKey: storefrontKeys.categoryTree(),
    queryFn: () => categoriesApi.getTree(),
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  });
}

/**
 * Fetch all categories (flat list)
 * Cached for 10 minutes
 */
export function useCategories() {
  return useQuery({
    queryKey: storefrontKeys.categories(),
    queryFn: () => categoriesApi.list(),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}

/**
 * Fetch all brands
 * Cached for 10 minutes
 */
export function useBrands() {
  return useQuery({
    queryKey: storefrontKeys.brands(),
    queryFn: () => brandsApi.list(),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}

/**
 * Fetch company info
 * Cached for 1 hour (rarely changes)
 */
export function useCompanyInfo() {
  return useQuery({
    queryKey: storefrontKeys.company(),
    queryFn: () => companyApi.getInfo(),
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 2 * 60 * 60 * 1000, // 2 hours
  });
}

/**
 * Fetch hero banners
 * Cached for 5 minutes
 */
export function useBanners() {
  return useQuery({
    queryKey: storefrontKeys.banners(),
    queryFn: () => contentApi.getBanners(),
    staleTime: 5 * 60 * 1000,
    gcTime: 15 * 60 * 1000,
  });
}

/**
 * Fetch USPs/features
 * Cached for 10 minutes
 */
export function useUsps() {
  return useQuery({
    queryKey: storefrontKeys.usps(),
    queryFn: () => contentApi.getUsps(),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}

/**
 * Fetch testimonials
 * Cached for 10 minutes
 */
export function useTestimonials() {
  return useQuery({
    queryKey: storefrontKeys.testimonials(),
    queryFn: () => contentApi.getTestimonials(),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}

/**
 * Fetch site settings
 * Cached for 30 minutes
 */
export function useSettings(group?: string) {
  return useQuery({
    queryKey: storefrontKeys.settings(group),
    queryFn: () => contentApi.getSettings(group),
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });
}

/**
 * Fetch feature bars
 * Cached for 30 minutes
 */
export function useFeatureBars() {
  return useQuery({
    queryKey: storefrontKeys.featureBars(),
    queryFn: () => contentApi.getFeatureBars(),
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });
}

/**
 * Hook to prefetch product detail on hover
 */
export function usePrefetchProduct() {
  const queryClient = useQueryClient();

  return (slug: string) => {
    queryClient.prefetchQuery({
      queryKey: storefrontKeys.productDetail(slug),
      queryFn: () => productsApi.getBySlug(slug),
      staleTime: 5 * 60 * 1000,
    });
  };
}

/**
 * Combined hook for products page data (categories + brands + products)
 * Fetches filter options and products in parallel
 */
export function useProductsPageData(filters: ProductFilters) {
  const categoriesQuery = useCategories();
  const brandsQuery = useBrands();
  const productsQuery = useProducts(filters);

  return {
    categories: categoriesQuery.data ?? [],
    brands: brandsQuery.data ?? [],
    products: productsQuery.data?.items ?? [],
    totalProducts: productsQuery.data?.total ?? 0,
    totalPages: productsQuery.data?.pages ?? 0,
    isLoading: productsQuery.isLoading,
    isFiltersLoading: categoriesQuery.isLoading || brandsQuery.isLoading,
    error: productsQuery.error || categoriesQuery.error || brandsQuery.error,
  };
}

/**
 * Fetch all homepage data in a single request
 * Uses composite API endpoint for optimal performance
 * Cached for 5 minutes
 */
export function useHomepage() {
  return useQuery({
    queryKey: storefrontKeys.homepage(),
    queryFn: () => homepageApi.getData(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
  });
}

/**
 * Fetch CMS-managed mega menu items for navigation
 * This returns curated navigation structure defined by admins,
 * unlike categories which returns all categories from the database.
 * Cached for 10 minutes (navigation changes infrequently)
 */
export function useMegaMenu() {
  return useQuery({
    queryKey: storefrontKeys.megaMenu(),
    queryFn: () => contentApi.getMegaMenu(),
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  });
}
