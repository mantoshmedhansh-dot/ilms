import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Domain-based routing middleware
 *
 * Domains:
 * - aquapurite.com (D2C Storefront) → Customer-facing store
 * - aquapurite.org (ERP Dashboard) → Admin panel
 *
 * Routing Rules:
 * - aquapurite.com: Serve storefront, block /dashboard access
 * - aquapurite.org: Redirect / to /dashboard, block storefront routes
 *
 * Referral Tracking:
 * - Detects ?ref=PARTNER_CODE in URL
 * - Stores partner code in cookie (7 days)
 * - Used during checkout for partner attribution
 */

// Cookie name for referral tracking
const REFERRAL_COOKIE_NAME = 'partner_ref';
const REFERRAL_COOKIE_MAX_AGE = 60 * 60 * 24 * 7; // 7 days in seconds

// Storefront routes (served on aquapurite.com)
const STOREFRONT_ROUTES = [
  '/',
  '/products',
  '/category',
  '/cart',
  '/checkout',
  '/order-success',
  '/track',
  '/about',
  '/contact',
];

// Dashboard routes (served on aquapurite.org)
const DASHBOARD_ROUTES = [
  '/dashboard',
  '/login',
  '/register',
  '/forgot-password',
  '/reset-password',
];

// Static assets and API routes to skip
const SKIP_PATHS = [
  '/_next',
  '/api',
  '/favicon.ico',
  '/logo',
  '/images',
  '/fonts',
];

export function middleware(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;
  const hostname = request.headers.get('host') || '';

  // Skip static assets and API routes
  if (SKIP_PATHS.some(path => pathname.startsWith(path))) {
    return NextResponse.next();
  }

  // Handle referral tracking
  const refCode = searchParams.get('ref');
  let response: NextResponse | null = null;

  // Helper to set referral cookie on response
  const setReferralCookie = (res: NextResponse) => {
    if (refCode) {
      res.cookies.set(REFERRAL_COOKIE_NAME, refCode, {
        maxAge: REFERRAL_COOKIE_MAX_AGE,
        path: '/',
        httpOnly: true, // Security: prevent XSS from stealing referral codes
        sameSite: 'lax',
        secure: process.env.NODE_ENV === 'production',
      });
    }
    return res;
  };

  // Determine which domain we're on
  const isStorefrontDomain =
    hostname.includes('aquapurite.com') ||
    hostname.includes('localhost:3000'); // For local development of storefront

  const isDashboardDomain =
    hostname.includes('aquapurite.org') ||
    hostname.includes('localhost:3001'); // For local development of dashboard

  // Check if path is a storefront route
  const isStorefrontRoute =
    STOREFRONT_ROUTES.some(route =>
      pathname === route || pathname.startsWith(`${route}/`)
    ) && !pathname.startsWith('/dashboard');

  // Check if path is a dashboard route
  const isDashboardRoute =
    DASHBOARD_ROUTES.some(route =>
      pathname === route || pathname.startsWith(`${route}/`)
    );

  // STOREFRONT DOMAIN (aquapurite.com)
  if (isStorefrontDomain) {
    // Block dashboard access on storefront domain
    if (isDashboardRoute) {
      // Redirect to aquapurite.org for dashboard
      const dashboardUrl = new URL(pathname, 'https://www.aquapurite.org');
      return NextResponse.redirect(dashboardUrl);
    }
    // Allow storefront routes (with referral tracking)
    response = NextResponse.next();
    return setReferralCookie(response);
  }

  // DASHBOARD DOMAIN (aquapurite.org)
  if (isDashboardDomain) {
    // Redirect root to dashboard
    if (pathname === '/') {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    // Block storefront routes on dashboard domain
    if (isStorefrontRoute && !isDashboardRoute) {
      // Redirect to aquapurite.com for storefront
      const storefrontUrl = new URL(pathname, 'https://www.aquapurite.com');
      return NextResponse.redirect(storefrontUrl);
    }

    // Allow dashboard routes
    return NextResponse.next();
  }

  // Default: allow all routes (for other domains/preview deployments)
  // With referral tracking for storefront routes
  response = NextResponse.next();
  if (isStorefrontRoute || pathname.startsWith('/products')) {
    return setReferralCookie(response);
  }
  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
