import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Order Confirmed | ILMS.AI',
  description: 'Your order has been placed successfully. Thank you for shopping with ILMS.AI.',
  robots: {
    index: false,
    follow: false,
  },
};

export default function OrderSuccessLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
