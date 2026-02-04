import { Metadata } from 'next';
import StorefrontHeader from '@/components/storefront/layout/header';
import StorefrontFooter from '@/components/storefront/layout/footer';
import AnnouncementBar from '@/components/storefront/layout/announcement-bar';
import CompareBarWrapper from '@/components/storefront/product/compare-bar-wrapper';
import WhatsAppButton from '@/components/storefront/layout/whatsapp-button';
import { ServiceabilityProvider } from '@/components/storefront/serviceability-provider';

const siteUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://www.ilms.ai';

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: 'ILMS.AI - Pure Water, Healthy Life',
    template: '%s | ILMS.AI',
  },
  description:
    "India's trusted water purifier brand. Advanced RO, UV, and UF water purification systems for homes and offices. Shop now for clean, safe drinking water solutions.",
  keywords: [
    'water purifier',
    'RO purifier',
    'UV purifier',
    'UF purifier',
    'water filter',
    'drinking water',
    'ilms',
    'water purification',
    'RO water purifier',
    'water purifier India',
  ],
  authors: [{ name: 'ILMS.AI' }],
  creator: 'ILMS.AI',
  publisher: 'ILMS.AI',
  alternates: {
    canonical: '/',
  },
  openGraph: {
    type: 'website',
    locale: 'en_IN',
    siteName: 'ILMS.AI',
    title: 'ILMS.AI - Pure Water, Healthy Life',
    description:
      "India's trusted water purifier brand. Advanced RO, UV, and UF water purification systems for homes and offices.",
    images: [
      {
        url: '/logo.png',
        width: 512,
        height: 512,
        alt: 'ILMS.AI Logo',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ILMS.AI - Pure Water, Healthy Life',
    description:
      "India's trusted water purifier brand. Advanced RO, UV, and UF water purification systems.",
    images: ['/logo.png'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
};

export default function StorefrontLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ServiceabilityProvider>
      <div className="min-h-screen flex flex-col">
        {/* Demo Site Banner */}
        <div className="bg-gray-900 text-white text-center py-2 px-4">
          <p className="text-lg font-bold tracking-wide">
            This is a Demo Site for www.ilms.ai
          </p>
        </div>
        {/* CMS Announcement Bar */}
        <AnnouncementBar />
        <StorefrontHeader />
        <main className="flex-1 pb-20">{children}</main>
        <StorefrontFooter />
        {/* Product Comparison Bar - Fixed at bottom */}
        <CompareBarWrapper />
        {/* WhatsApp Floating Button */}
        <WhatsAppButton />
      </div>
    </ServiceabilityProvider>
  );
}
