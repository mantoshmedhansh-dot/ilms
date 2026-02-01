# D2C Website Architecture - Aquapurite

## Overview

This document outlines the architecture for the D2C (Direct-to-Consumer) website for Aquapurite, integrated with the ERP backend.

## Architecture Diagram

```
                    +-------------------+
                    |   aquapurite.com  |
                    |   (Next.js App)   |
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+       +-----------v-----------+
    |   Storefront      |       |   Admin Dashboard     |
    |   /(storefront)   |       |   /(dashboard)        |
    +--------+----------+       +-----------+-----------+
              |                             |
              +-------------+---------------+
                            |
                  +---------v---------+
                  |   ERP Backend     |
                  |   (FastAPI)       |
                  +---------+---------+
                            |
              +-------------+-------------+
              |             |             |
    +---------v---+  +------v------+  +---v---------+
    |   Products  |  | Serviceability|  |   Orders   |
    |   API       |  |   + Cache    |  |   API      |
    +-------------+  +------+------+  +-------------+
                            |
                    +-------v-------+
                    |  Redis Cache  |
                    |  (Optional)   |
                    +---------------+
```

## URL Structure

| Route | Description | Auth Required |
|-------|-------------|---------------|
| `/` | Homepage with featured products | No |
| `/products` | Product catalog with filters | No |
| `/products/[slug]` | Product detail page | No |
| `/cart` | Shopping cart | No |
| `/checkout` | Checkout flow | No |
| `/track` | Order tracking | No (phone verification) |
| `/account` | User account | Yes |
| `/login` | Login page | No |

## Key Features

### 1. Fast PIN Code Serviceability

The serviceability check is optimized for speed using a two-tier caching strategy:

```
Request Flow:
1. User enters PIN code
2. Check in-memory/Redis cache (< 5ms)
3. If cache miss, query database
4. Cache result for 1 hour
5. Return response with X-Cache header

Cache Configuration:
- CACHE_ENABLED=true
- REDIS_URL=redis://localhost:6379/0 (optional)
- SERVICEABILITY_CACHE_TTL=3600 (1 hour)
```

### 2. Product Catalog

Products are fetched from the ERP backend:

```typescript
// API calls
GET /api/v1/products                    // List products
GET /api/v1/products/{slug}             // Get product by slug
GET /api/v1/products?is_featured=true   // Featured products
GET /api/v1/products?is_bestseller=true // Bestsellers
```

### 3. Order Creation (D2C)

Orders are created through a public endpoint:

```
POST /api/v1/orders/d2c

Payload:
{
  "channel": "D2C",
  "customer": {
    "name": "John Doe",
    "phone": "9876543210",
    "email": "john@example.com"
  },
  "shipping_address": {...},
  "items": [...],
  "payment_method": "cod",
  "total_amount": 15999
}

Response:
{
  "id": "uuid",
  "order_number": "ORD-20250111-0001",
  "total_amount": 15999,
  "status": "pending"
}
```

### 4. Order Tracking

```
GET /api/v1/orders/track/{order_number}?phone=9876543210
```

## Content Management Strategy

### Option A: Headless CMS (Recommended)

Use a headless CMS like **Strapi** or **Contentful** for:
- Hero banners
- Marketing content
- Blog posts
- FAQs
- Static pages (About, Contact, etc.)

Integration:
```typescript
// Fetch from CMS
const banner = await strapi.find('hero-banners', {
  filters: { active: true }
});
```

### Option B: ERP-Managed Content

Extend the ERP backend with content tables:
- `banners` - Hero banners with image URLs
- `pages` - Static page content
- `faqs` - FAQ entries
- `testimonials` - Customer reviews

### Option C: Hybrid Approach (Recommended)

1. **Product Data** → ERP Backend (single source of truth)
2. **Marketing Content** → Headless CMS or simple JSON files
3. **Static Pages** → Next.js static generation

```
/frontend
  /content
    /banners.json      # Hero banners
    /features.json     # Feature highlights
    /faqs.json         # FAQs
```

## Environment Configuration

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SITE_URL=https://www.aquapurite.com
```

### Backend (.env)
```env
# Redis Cache (optional, falls back to in-memory)
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
SERVICEABILITY_CACHE_TTL=3600
PRODUCT_CACHE_TTL=300

# CORS for D2C site
CORS_ORIGINS=["https://www.aquapurite.com","http://localhost:3000"]
```

## Deployment Architecture

### Production Setup

```
                     +------------------+
                     |   CloudFlare     |
                     |   (CDN + WAF)    |
                     +--------+---------+
                              |
              +---------------+---------------+
              |                               |
    +---------v---------+         +-----------v-----------+
    |   Vercel          |         |   Railway/Render      |
    |   Next.js App     |         |   FastAPI Backend     |
    +-------------------+         +-----------+-----------+
                                              |
                                  +-----------v-----------+
                                  |   Supabase            |
                                  |   PostgreSQL + Storage|
                                  +-----------+-----------+
                                              |
                                  +-----------v-----------+
                                  |   Redis Cloud         |
                                  |   (Cache)             |
                                  +-----------------------+
```

### Recommended Services

| Component | Service | Notes |
|-----------|---------|-------|
| Frontend | Vercel | Auto-deploys from Git |
| Backend | Railway/Render | Easy FastAPI deployment |
| Database | Supabase | PostgreSQL + Auth + Storage |
| Cache | Upstash | Serverless Redis |
| CDN | CloudFlare | Free tier sufficient |
| Images | CloudFlare R2 or Supabase Storage | Product images |

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Serviceability Check | < 100ms | ~50ms (cached) |
| Homepage Load | < 2s | - |
| Product Page | < 1.5s | - |
| Checkout | < 3s | - |

## Security Considerations

1. **Rate Limiting**: Apply rate limits to public endpoints
2. **Input Validation**: Validate all user inputs (phone, email, pincode)
3. **CORS**: Restrict to known domains
4. **Payment**: Use payment gateway webhooks for order confirmation
5. **PII**: Mask customer phone in logs

## Next Steps

1. [ ] Set up Vercel deployment for frontend
2. [ ] Configure Redis cache on production
3. [ ] Implement payment gateway integration (Razorpay/PayU)
4. [ ] Add email notifications for orders
5. [ ] Set up SMS OTP for checkout
6. [ ] Implement user authentication (optional)
7. [ ] Add Google Analytics / Meta Pixel
8. [ ] SEO optimization (meta tags, sitemap)
