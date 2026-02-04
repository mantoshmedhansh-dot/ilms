import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Shopping Cart | ILMS.AI',
  description: 'Review your shopping cart and proceed to checkout. Free delivery on orders above specified amount.',
  robots: {
    index: false, // Don't index cart pages
    follow: true,
  },
};

export default function CartLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
