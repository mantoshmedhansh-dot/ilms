import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Order Confirmed | Aquapurite',
  description: 'Your order has been placed successfully. Thank you for shopping with Aquapurite.',
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
