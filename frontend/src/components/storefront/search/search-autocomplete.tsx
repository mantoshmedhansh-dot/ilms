'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import {
  Search,
  X,
  Clock,
  TrendingUp,
  Package,
  FolderOpen,
  Tag,
  Loader2,
  ArrowRight,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  searchApi,
  SearchSuggestionsResponse,
  SearchProductSuggestion,
  SearchCategorySuggestion,
  SearchBrandSuggestion,
} from '@/lib/storefront/api';
import {
  getRecentSearchQueries,
  addToSearchHistory,
  removeFromSearchHistory,
  clearSearchHistory,
} from '@/lib/storefront/search-history';
import { formatCurrency } from '@/lib/utils';
import { useDebounce } from '@/hooks/use-debounce';

interface SearchAutocompleteProps {
  placeholder?: string;
  className?: string;
  onSearch?: (query: string) => void;
  autoFocus?: boolean;
  showMobileOverlay?: boolean;
  onClose?: () => void;
}

export default function SearchAutocomplete({
  placeholder = 'Search for products...',
  className = '',
  onSearch,
  autoFocus = false,
  showMobileOverlay = false,
  onClose,
}: SearchAutocompleteProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<SearchSuggestionsResponse | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);

  const debouncedQuery = useDebounce(query, 300);

  // Load recent searches on mount
  useEffect(() => {
    setRecentSearches(getRecentSearchQueries());
  }, []);

  // Fetch suggestions when query changes
  useEffect(() => {
    const fetchSuggestions = async () => {
      if (debouncedQuery.length < 2) {
        setSuggestions(null);
        return;
      }

      setIsLoading(true);
      try {
        const data = await searchApi.getSuggestions(debouncedQuery);
        setSuggestions(data);
      } catch (error) {
        console.error('Failed to fetch suggestions:', error);
        setSuggestions(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSuggestions();
  }, [debouncedQuery]);

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Reset selected index when suggestions change
  useEffect(() => {
    setSelectedIndex(-1);
  }, [suggestions, recentSearches]);

  const handleSearch = useCallback(
    (searchQuery: string) => {
      if (!searchQuery.trim()) return;

      addToSearchHistory(searchQuery);
      setRecentSearches(getRecentSearchQueries());
      setIsOpen(false);
      setQuery('');

      if (onSearch) {
        onSearch(searchQuery);
      } else {
        router.push(`/products?search=${encodeURIComponent(searchQuery)}`);
      }

      if (onClose) onClose();
    },
    [router, onSearch, onClose]
  );

  const handleProductClick = (product: SearchProductSuggestion) => {
    addToSearchHistory(product.name);
    setRecentSearches(getRecentSearchQueries());
    setIsOpen(false);
    setQuery('');
    router.push(`/products/${product.slug}`);
    if (onClose) onClose();
  };

  const handleCategoryClick = (category: SearchCategorySuggestion) => {
    setIsOpen(false);
    setQuery('');
    router.push(`/products?category_id=${category.id}`);
    if (onClose) onClose();
  };

  const handleBrandClick = (brand: SearchBrandSuggestion) => {
    setIsOpen(false);
    setQuery('');
    router.push(`/products?brand_id=${brand.id}`);
    if (onClose) onClose();
  };

  const handleRemoveRecent = (searchQuery: string, e: React.MouseEvent) => {
    e.stopPropagation();
    removeFromSearchHistory(searchQuery);
    setRecentSearches(getRecentSearchQueries());
  };

  const handleClearHistory = () => {
    clearSearchHistory();
    setRecentSearches([]);
  };

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    const totalItems = getTotalItems();

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => (prev < totalItems - 1 ? prev + 1 : 0));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : totalItems - 1));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          handleSelectByIndex(selectedIndex);
        } else {
          handleSearch(query);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        inputRef.current?.blur();
        break;
    }
  };

  const getTotalItems = () => {
    if (!isOpen) return 0;

    if (suggestions && (suggestions.products.length > 0 || suggestions.categories.length > 0 || suggestions.brands.length > 0)) {
      return suggestions.products.length + suggestions.categories.length + suggestions.brands.length;
    }

    return recentSearches.length;
  };

  const handleSelectByIndex = (index: number) => {
    if (suggestions && (suggestions.products.length > 0 || suggestions.categories.length > 0 || suggestions.brands.length > 0)) {
      let currentIndex = 0;

      // Products
      if (index < suggestions.products.length) {
        handleProductClick(suggestions.products[index]);
        return;
      }
      currentIndex += suggestions.products.length;

      // Categories
      if (index < currentIndex + suggestions.categories.length) {
        handleCategoryClick(suggestions.categories[index - currentIndex]);
        return;
      }
      currentIndex += suggestions.categories.length;

      // Brands
      if (index < currentIndex + suggestions.brands.length) {
        handleBrandClick(suggestions.brands[index - currentIndex]);
        return;
      }
    } else {
      // Recent searches
      if (index < recentSearches.length) {
        handleSearch(recentSearches[index]);
      }
    }
  };

  const showSuggestions =
    suggestions &&
    (suggestions.products.length > 0 ||
      suggestions.categories.length > 0 ||
      suggestions.brands.length > 0);

  const showRecentSearches = !query && recentSearches.length > 0;

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className="pl-10 pr-10"
        />
        {query && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
            onClick={() => {
              setQuery('');
              setSuggestions(null);
              inputRef.current?.focus();
            }}
          >
            <X className="h-4 w-4" />
          </Button>
        )}
        {isLoading && (
          <div className="absolute right-10 top-1/2 -translate-y-1/2">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>

      {/* Dropdown */}
      {isOpen && (showSuggestions || showRecentSearches) && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-background border rounded-lg shadow-lg z-50 max-h-[70vh] overflow-y-auto">
          {/* Recent Searches */}
          {showRecentSearches && (
            <div className="p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  Recent Searches
                </span>
                <button
                  onClick={handleClearHistory}
                  className="text-xs text-primary hover:underline"
                >
                  Clear all
                </button>
              </div>
              <div className="space-y-1">
                {recentSearches.map((search, index) => (
                  <div
                    key={search}
                    onClick={() => handleSearch(search)}
                    className={`flex items-center justify-between px-3 py-2 rounded-md cursor-pointer transition-colors ${
                      selectedIndex === index ? 'bg-muted' : 'hover:bg-muted/50'
                    }`}
                  >
                    <span className="text-sm">{search}</span>
                    <button
                      onClick={(e) => handleRemoveRecent(search, e)}
                      className="p-1 hover:bg-muted-foreground/20 rounded"
                    >
                      <X className="h-3 w-3 text-muted-foreground" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Suggestions */}
          {showSuggestions && suggestions && (
            <>
              {/* Products */}
              {suggestions.products.length > 0 && (
                <div className="p-3 border-b">
                  <span className="text-xs font-medium text-muted-foreground flex items-center gap-1 mb-2">
                    <Package className="h-3 w-3" />
                    Products
                  </span>
                  <div className="space-y-1">
                    {suggestions.products.map((product, index) => (
                      <div
                        key={product.id}
                        onClick={() => handleProductClick(product)}
                        className={`flex items-center gap-3 p-2 rounded-md cursor-pointer transition-colors ${
                          selectedIndex === index ? 'bg-muted' : 'hover:bg-muted/50'
                        }`}
                      >
                        <div className="w-10 h-10 bg-muted rounded overflow-hidden flex-shrink-0">
                          {product.image_url ? (
                            <Image
                              src={product.image_url}
                              alt={product.name}
                              width={40}
                              height={40}
                              className="object-cover w-full h-full"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <Package className="h-4 w-4 text-muted-foreground" />
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{product.name}</p>
                          <div className="flex items-baseline gap-2">
                            <span className="text-sm text-primary font-medium">
                              {formatCurrency(product.price)}
                            </span>
                            {product.mrp > product.price && (
                              <span className="text-xs text-muted-foreground line-through">
                                {formatCurrency(product.mrp)}
                              </span>
                            )}
                          </div>
                        </div>
                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Categories */}
              {suggestions.categories.length > 0 && (
                <div className="p-3 border-b">
                  <span className="text-xs font-medium text-muted-foreground flex items-center gap-1 mb-2">
                    <FolderOpen className="h-3 w-3" />
                    Categories
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {suggestions.categories.map((category, index) => (
                      <button
                        key={category.id}
                        onClick={() => handleCategoryClick(category)}
                        className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm transition-colors ${
                          selectedIndex === suggestions.products.length + index
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted hover:bg-muted/80'
                        }`}
                      >
                        {category.name}
                        {category.product_count > 0 && (
                          <span className="text-xs opacity-70">
                            ({category.product_count})
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Brands */}
              {suggestions.brands.length > 0 && (
                <div className="p-3">
                  <span className="text-xs font-medium text-muted-foreground flex items-center gap-1 mb-2">
                    <Tag className="h-3 w-3" />
                    Brands
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {suggestions.brands.map((brand, index) => (
                      <button
                        key={brand.id}
                        onClick={() => handleBrandClick(brand)}
                        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-colors ${
                          selectedIndex ===
                          suggestions.products.length + suggestions.categories.length + index
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted hover:bg-muted/80'
                        }`}
                      >
                        {brand.logo_url && (
                          <Image
                            src={brand.logo_url}
                            alt={brand.name}
                            width={16}
                            height={16}
                            className="rounded"
                          />
                        )}
                        {brand.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* View all results */}
              {query && (
                <div className="p-3 border-t bg-muted/30">
                  <button
                    onClick={() => handleSearch(query)}
                    className="w-full flex items-center justify-center gap-2 text-sm text-primary hover:underline"
                  >
                    <Search className="h-4 w-4" />
                    View all results for &quot;{query}&quot;
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Mobile overlay close button */}
      {showMobileOverlay && onClose && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="absolute -top-12 right-0 md:hidden"
        >
          Close
        </Button>
      )}
    </div>
  );
}
