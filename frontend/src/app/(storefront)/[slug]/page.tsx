import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { contentApi } from '@/lib/storefront/api';

interface PageProps {
  params: Promise<{
    slug: string;
  }>;
}

// Generate metadata for SEO
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;

  try {
    const page = await contentApi.getPage(slug);

    if (!page) {
      return {
        title: 'Page Not Found',
      };
    }

    return {
      title: page.meta_title || page.title,
      description: page.meta_description || undefined,
      openGraph: page.og_image_url
        ? {
            images: [{ url: page.og_image_url }],
          }
        : undefined,
    };
  } catch {
    return {
      title: 'Page Not Found',
    };
  }
}

export default async function DynamicPage({ params }: PageProps) {
  const { slug } = await params;

  // Reserved routes that should not be handled by this page
  const reservedRoutes = [
    'products',
    'cart',
    'checkout',
    'account',
    'order-success',
    'recover-cart',
    'track-order',
    'returns',
    'wishlist',
  ];

  if (reservedRoutes.includes(slug)) {
    notFound();
  }

  const page = await contentApi.getPage(slug);

  if (!page) {
    notFound();
  }

  return (
    <div className="container mx-auto px-4 py-12 md:py-16">
      <article className="max-w-4xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold mb-4">{page.title}</h1>
        </header>

        {page.content && (
          <div
            className="prose prose-lg max-w-none prose-headings:font-bold prose-a:text-primary prose-img:rounded-lg"
            dangerouslySetInnerHTML={{ __html: page.content }}
          />
        )}
      </article>
    </div>
  );
}
