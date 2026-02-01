import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Compare Water Purifiers | Aquapurite',
  description: 'Compare specifications, features, and prices of different water purifiers side by side to make the best choice for your home.',
  keywords: ['compare water purifiers', 'RO vs UV', 'water purifier comparison', 'best water purifier'],
  openGraph: {
    title: 'Compare Water Purifiers | Aquapurite',
    description: 'Compare specifications, features, and prices of different water purifiers side by side.',
    type: 'website',
  },
};

export default function CompareLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
