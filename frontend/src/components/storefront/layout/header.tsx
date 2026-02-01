'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Search,
  ShoppingCart,
  User,
  Menu,
  X,
  Phone,
  ChevronDown,
  Droplets,
  Moon,
  Sun,
} from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useCartStore } from '@/lib/storefront/cart-store';
import { useAuthStore, useIsAuthenticated, useCustomer } from '@/lib/storefront/auth-store';
import { StorefrontCategory, CompanyInfo } from '@/types/storefront';
import { categoriesApi, companyApi, authApi, contentApi, StorefrontMenuItem, StorefrontMegaMenuItem } from '@/lib/storefront/api';
import CartDrawer from '../cart/cart-drawer';
import SearchAutocomplete from '../search/search-autocomplete';
import MegaMenu, { CMSMegaMenu } from './mega-menu';

export default function StorefrontHeader() {
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const [categories, setCategories] = useState<StorefrontCategory[]>([]);
  const [company, setCompany] = useState<CompanyInfo | null>(null);
  const [headerMenuItems, setHeaderMenuItems] = useState<StorefrontMenuItem[]>([]);
  const [megaMenuItems, setMegaMenuItems] = useState<StorefrontMegaMenuItem[]>([]);

  const cartItemCount = useCartStore((state) => state.getItemCount());
  const openCart = useCartStore((state) => state.openCart);

  // Auth state
  const isAuthenticated = useIsAuthenticated();
  const customer = useCustomer();
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = async () => {
    await authApi.logout();
    logout();
    router.push('/');
  };

  // Prevent hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [categoriesData, companyData, menuItems, megaMenu] = await Promise.all([
          categoriesApi.getTree(),
          companyApi.getInfo(),
          contentApi.getMenuItems('header'),
          contentApi.getMegaMenu(),
        ]);
        setCategories(categoriesData);
        setCompany(companyData);
        setHeaderMenuItems(menuItems);
        setMegaMenuItems(megaMenu);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      }
    };
    fetchData();
  }, []);

  return (
    <>
      {/* Top Bar */}
      <div className="bg-secondary text-secondary-foreground text-sm py-2 hidden md:block">
        <div className="container mx-auto px-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <Phone className="h-3 w-3" />
              {company?.phone || '1800-123-4567'} (Toll Free)
            </span>
            <span>Free Shipping on orders above ₹999</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/track" className="hover:underline">
              Track Order
            </Link>
            <Link href="/guides" className="hover:underline">
              Video Guides
            </Link>
            <Link href="/referral" className="hover:underline">
              Refer & Earn
            </Link>
            <Link href="/support" className="hover:underline">
              Support
            </Link>
          </div>
        </div>
      </div>

      {/* Main Header */}
      <header
        className={`sticky top-0 z-50 bg-background transition-shadow ${
          isScrolled ? 'shadow-md' : 'shadow-sm'
        }`}
      >
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16 md:h-20">
            {/* Mobile Menu Button */}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open navigation menu"
            >
              <Menu className="h-6 w-6" />
            </Button>

            {/* Logo */}
            <Link href="/" className="flex items-center gap-2">
              {company?.logo_url ? (
                <img
                  src={company.logo_url}
                  alt={company.trade_name || company.name}
                  className="h-10 w-auto"
                />
              ) : (
                <>
                  <div className="bg-primary rounded-full p-2">
                    <Droplets className="h-6 w-6 text-primary-foreground" />
                  </div>
                  <span className="font-bold text-xl hidden sm:block">
                    {company?.trade_name || company?.name || 'AQUAPURITE'}
                  </span>
                </>
              )}
            </Link>

            {/* Search Bar - Desktop */}
            <div className="hidden md:flex flex-1 max-w-xl mx-8">
              <SearchAutocomplete
                placeholder="Search for products..."
                className="w-full"
              />
            </div>

            {/* Right Actions */}
            <div className="flex items-center gap-2 md:gap-4">
              {/* Search - Mobile */}
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                onClick={() => setMobileSearchOpen(true)}
                aria-label="Open search"
              >
                <Search className="h-5 w-5" />
              </Button>

              {/* Dark Mode Toggle */}
              {mounted && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                  aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                  title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                >
                  {theme === 'dark' ? (
                    <Sun className="h-5 w-5" />
                  ) : (
                    <Moon className="h-5 w-5" />
                  )}
                </Button>
              )}

              {/* Account */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="hidden md:flex" aria-label="Account menu">
                    <User className="h-5 w-5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  {isAuthenticated && customer ? (
                    <>
                      <div className="px-2 py-1.5 text-sm font-medium border-b mb-1">
                        Hi, {customer.first_name}
                      </div>
                      <DropdownMenuItem asChild>
                        <Link href="/account">My Account</Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href="/account/orders">My Orders</Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href="/account/addresses">Saved Addresses</Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={handleLogout}
                        className="text-red-600 focus:text-red-600"
                      >
                        Logout
                      </DropdownMenuItem>
                    </>
                  ) : (
                    <>
                      <DropdownMenuItem asChild>
                        <Link href="/account/login">Login / Sign Up</Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href="/track">Track Order</Link>
                      </DropdownMenuItem>
                    </>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Cart */}
              <Button
                variant="ghost"
                size="icon"
                className="relative"
                onClick={openCart}
                aria-label={`Shopping cart${cartItemCount > 0 ? ` with ${cartItemCount} items` : ''}`}
              >
                <ShoppingCart className="h-5 w-5" />
                {cartItemCount > 0 && (
                  <Badge
                    variant="destructive"
                    className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs"
                  >
                    {cartItemCount}
                  </Badge>
                )}
              </Button>
            </div>
          </div>

          {/* Category Navigation - Desktop with Mega Menu */}
          <nav className="hidden md:flex items-center gap-2 py-3 border-t">
            {/* CMS Mega Menu (admin-curated) takes priority, otherwise fall back to all categories */}
            {megaMenuItems.length > 0 ? (
              <CMSMegaMenu items={megaMenuItems} />
            ) : categories.length > 0 ? (
              <MegaMenu categories={categories} />
            ) : null}

            {/* Divider if navigation exists and menu items exist */}
            {(megaMenuItems.length > 0 || categories.length > 0) && headerMenuItems.length > 0 && (
              <div className="h-4 w-px bg-border mx-2" />
            )}

            {/* CMS Menu Items - falls back to defaults if empty */}
            {headerMenuItems.length > 0 ? (
              headerMenuItems.map((item) => (
                <Link
                  key={item.id}
                  href={item.url}
                  target={item.target}
                  className="px-3 py-2 text-sm font-medium hover:text-primary transition-colors"
                >
                  {item.title}
                </Link>
              ))
            ) : (
              <>
                <Link
                  href="/products?is_bestseller=true"
                  className="px-3 py-2 text-sm font-medium hover:text-primary transition-colors"
                >
                  Bestsellers
                </Link>
                <Link
                  href="/products?is_new_arrival=true"
                  className="px-3 py-2 text-sm font-medium hover:text-primary transition-colors"
                >
                  New Arrivals
                </Link>
                <Link
                  href="/products"
                  className="px-3 py-2 text-sm font-medium hover:text-primary transition-colors"
                >
                  All Products
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Mobile Menu */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-80">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Droplets className="h-5 w-5 text-primary" />
              {company?.trade_name || company?.name || 'AQUAPURITE'}
            </SheetTitle>
          </SheetHeader>
          <nav className="mt-8 flex flex-col gap-4">
            <Link
              href="/"
              className="text-lg font-medium"
              onClick={() => setMobileMenuOpen(false)}
            >
              Home
            </Link>
            <Link
              href="/products"
              className="text-lg font-medium"
              onClick={() => setMobileMenuOpen(false)}
            >
              All Products
            </Link>
            <div className="border-t pt-4">
              <p className="text-sm text-muted-foreground mb-2">Categories</p>
              {/* Use CMS mega menu if available, otherwise fall back to categories */}
              {megaMenuItems.length > 0 ? (
                megaMenuItems.map((item) => (
                  <div key={item.id} className="mb-1">
                    <Link
                      href={item.menu_type === 'CATEGORY' ? `/category/${item.category_slug}` : item.url || '#'}
                      target={item.target}
                      className="block py-2 text-base font-medium"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      {item.title}
                      {item.is_highlighted && (
                        <Badge variant="default" className="ml-2 text-[10px] px-1.5 py-0 bg-amber-500">
                          {item.highlight_text || 'New'}
                        </Badge>
                      )}
                    </Link>
                    {/* Subcategories for category type */}
                    {item.menu_type === 'CATEGORY' && item.subcategories && item.subcategories.length > 0 && (
                      <div className="ml-4 border-l pl-3">
                        {item.subcategories.map((sub) => (
                          <Link
                            key={sub.id}
                            href={`/category/${sub.slug}`}
                            className="block py-1.5 text-sm text-muted-foreground hover:text-foreground"
                            onClick={() => setMobileMenuOpen(false)}
                          >
                            {sub.name}
                            {sub.product_count > 0 && (
                              <span className="ml-1 text-xs">({sub.product_count})</span>
                            )}
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                categories.filter(c => !c.parent_id).map((category) => (
                  <div key={category.id} className="mb-1">
                    <Link
                      href={`/category/${category.slug}`}
                      className="block py-2 text-base font-medium"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      {category.name}
                      {category.product_count !== undefined && category.product_count > 0 && (
                        <span className="ml-2 text-xs text-muted-foreground">
                          ({category.product_count})
                        </span>
                      )}
                    </Link>
                    {/* Subcategories */}
                    {category.children && category.children.length > 0 && (
                      <div className="ml-4 border-l pl-3">
                        {category.children.map((child) => (
                          <Link
                            key={child.id}
                            href={`/category/${child.slug}`}
                            className="block py-1.5 text-sm text-muted-foreground hover:text-foreground"
                            onClick={() => setMobileMenuOpen(false)}
                          >
                            {child.name}
                            {child.product_count !== undefined && child.product_count > 0 && (
                              <span className="ml-1 text-xs">({child.product_count})</span>
                            )}
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
            <div className="border-t pt-4">
              {isAuthenticated && customer ? (
                <>
                  <p className="text-sm text-muted-foreground mb-2">
                    Hi, {customer.first_name}
                  </p>
                  <Link
                    href="/account"
                    className="block py-2 text-base"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    My Account
                  </Link>
                  <Link
                    href="/account/orders"
                    className="block py-2 text-base"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    My Orders
                  </Link>
                  <Link
                    href="/account/addresses"
                    className="block py-2 text-base"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Saved Addresses
                  </Link>
                  <button
                    onClick={() => {
                      handleLogout();
                      setMobileMenuOpen(false);
                    }}
                    className="block py-2 text-base text-red-600 w-full text-left"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link
                    href="/account/login"
                    className="block py-2 text-base font-medium text-primary"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Login / Sign Up
                  </Link>
                  <Link
                    href="/track"
                    className="block py-2 text-base"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Track Order
                  </Link>
                </>
              )}
            </div>
            <div className="border-t pt-4">
              {/* CMS Menu Items for mobile */}
              {headerMenuItems.length > 0 ? (
                headerMenuItems.map((item) => (
                  <Link
                    key={item.id}
                    href={item.url}
                    target={item.target}
                    className="block py-2 text-base"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    {item.title}
                  </Link>
                ))
              ) : (
                <>
                  <Link
                    href="/guides"
                    className="block py-2 text-base"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Video Guides
                  </Link>
                  <Link
                    href="/referral"
                    className="block py-2 text-base font-medium text-primary"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Refer & Earn ₹500
                  </Link>
                  <Link
                    href="/about"
                    className="block py-2 text-base"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    About Us
                  </Link>
                  <Link
                    href="/contact"
                    className="block py-2 text-base"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Contact Us
                  </Link>
                  <Link
                    href="/support"
                    className="block py-2 text-base"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Support
                  </Link>
                </>
              )}
            </div>
          </nav>
        </SheetContent>
      </Sheet>

      {/* Cart Drawer */}
      <CartDrawer />

      {/* Mobile Search Overlay */}
      <Sheet open={mobileSearchOpen} onOpenChange={setMobileSearchOpen}>
        <SheetContent side="top" className="h-auto pb-8">
          <SheetHeader className="mb-4">
            <SheetTitle>Search Products</SheetTitle>
          </SheetHeader>
          <SearchAutocomplete
            placeholder="Search for products..."
            autoFocus
            onClose={() => setMobileSearchOpen(false)}
          />
        </SheetContent>
      </Sheet>
    </>
  );
}
