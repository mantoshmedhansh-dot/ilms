import { NextRequest, NextResponse } from 'next/server';
import { revalidatePath, revalidateTag } from 'next/cache';

/**
 * On-demand revalidation API endpoint
 *
 * Usage:
 * POST /api/revalidate
 * Body: { "secret": "your-secret", "type": "path" | "tag", "value": "/products" | "products" }
 *
 * Types:
 * - path: Revalidates a specific URL path (e.g., "/products", "/products/ro-water-purifier")
 * - tag: Revalidates all data with a specific cache tag (e.g., "products", "homepage")
 *
 * Common tags:
 * - "homepage": Homepage data
 * - "products": Product listings
 * - "product-{slug}": Specific product
 * - "categories": Category tree
 * - "banners": CMS banners
 * - "testimonials": Testimonials
 * - "company": Company info
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { secret, type, value } = body;

    // Validate secret - MUST be set in environment
    const validSecret = process.env.REVALIDATE_SECRET;
    if (!validSecret) {
      console.error('[Revalidate] REVALIDATE_SECRET environment variable not configured');
      return NextResponse.json(
        { success: false, message: 'Server configuration error' },
        { status: 500 }
      );
    }
    if (secret !== validSecret) {
      return NextResponse.json(
        { success: false, message: 'Invalid secret' },
        { status: 401 }
      );
    }

    // Validate type
    if (!type || !['path', 'tag'].includes(type)) {
      return NextResponse.json(
        { success: false, message: 'Invalid type. Must be "path" or "tag"' },
        { status: 400 }
      );
    }

    // Validate value
    if (!value || typeof value !== 'string') {
      return NextResponse.json(
        { success: false, message: 'Invalid value. Must be a string' },
        { status: 400 }
      );
    }

    // Perform revalidation
    if (type === 'path') {
      revalidatePath(value);
      console.log(`[Revalidate] Path revalidated: ${value}`);
    } else {
      // revalidateTag requires type 'page' | 'layout' in Next.js 16
      revalidateTag(value, 'page');
      console.log(`[Revalidate] Tag revalidated: ${value}`);
    }

    return NextResponse.json({
      success: true,
      message: `Successfully revalidated ${type}: ${value}`,
      revalidated: true,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('[Revalidate] Error:', error);
    return NextResponse.json(
      { success: false, message: 'Revalidation failed', error: String(error) },
      { status: 500 }
    );
  }
}

/**
 * Batch revalidation - revalidate multiple paths/tags at once
 *
 * Usage:
 * POST /api/revalidate/batch
 * Body: {
 *   "secret": "your-secret",
 *   "items": [
 *     { "type": "path", "value": "/" },
 *     { "type": "tag", "value": "products" }
 *   ]
 * }
 */
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { secret, items } = body;

    // Validate secret - MUST be set in environment
    const validSecret = process.env.REVALIDATE_SECRET;
    if (!validSecret) {
      console.error('[Revalidate] REVALIDATE_SECRET environment variable not configured');
      return NextResponse.json(
        { success: false, message: 'Server configuration error' },
        { status: 500 }
      );
    }
    if (secret !== validSecret) {
      return NextResponse.json(
        { success: false, message: 'Invalid secret' },
        { status: 401 }
      );
    }

    // Validate items
    if (!Array.isArray(items) || items.length === 0) {
      return NextResponse.json(
        { success: false, message: 'Invalid items. Must be a non-empty array' },
        { status: 400 }
      );
    }

    const results: Array<{ type: string; value: string; success: boolean }> = [];

    for (const item of items) {
      const { type, value } = item;
      try {
        if (type === 'path') {
          revalidatePath(value);
          results.push({ type, value, success: true });
        } else if (type === 'tag') {
          revalidateTag(value, 'page');
          results.push({ type, value, success: true });
        } else {
          results.push({ type, value, success: false });
        }
      } catch {
        results.push({ type, value, success: false });
      }
    }

    console.log(`[Revalidate] Batch revalidated: ${results.filter(r => r.success).length}/${results.length}`);

    return NextResponse.json({
      success: true,
      message: `Batch revalidation completed`,
      results,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('[Revalidate] Batch error:', error);
    return NextResponse.json(
      { success: false, message: 'Batch revalidation failed', error: String(error) },
      { status: 500 }
    );
  }
}

// GET method for health check
export async function GET() {
  return NextResponse.json({
    status: 'ok',
    message: 'Revalidation API is ready',
    availableTags: [
      'homepage',
      'products',
      'categories',
      'banners',
      'testimonials',
      'company',
    ],
    usage: {
      single: 'POST /api/revalidate with body { secret, type: "path"|"tag", value }',
      batch: 'PUT /api/revalidate with body { secret, items: [{ type, value }] }',
    },
  });
}
