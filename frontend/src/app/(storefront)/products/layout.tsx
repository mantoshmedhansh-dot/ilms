import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Water Purifiers & Spare Parts | ILMS.AI',
  description: 'Browse our complete range of RO, UV, and RO+UV water purifiers along with genuine spare parts. Best prices, free delivery, and warranty on all products.',
  keywords: ['water purifier', 'RO water purifier', 'UV water purifier', 'water filter', 'spare parts', 'ILMS.AI'],
  openGraph: {
    title: 'Water Purifiers & Spare Parts | ILMS.AI',
    description: 'Browse our complete range of RO, UV, and RO+UV water purifiers along with genuine spare parts.',
    type: 'website',
  },
};

export default function ProductsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
