import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://www.aquapurite.com'

  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          '/dashboard/',
          '/dashboard',
          '/account/',
          '/account',
          '/cart',
          '/checkout',
          '/checkout/',
          '/order-success',
          '/order-success/',
          '/api/',
          '/portal/',
          '/partner/login',
          '/partner/earnings',
          '/partner/kyc',
          '/partner/payouts',
          '/login',
          '/forgot-password',
          '/reset-password',
          '/recover-cart',
          '/_next/',
          '/static/',
        ],
      },
      {
        userAgent: 'Googlebot',
        allow: '/',
        disallow: [
          '/dashboard/',
          '/account/',
          '/cart',
          '/checkout/',
          '/order-success/',
          '/api/',
          '/portal/',
          '/login',
          '/forgot-password',
          '/reset-password',
        ],
      },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
  }
}
