import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Checkout | ILMS.AI',
  description: 'Complete your purchase securely. Multiple payment options available including COD, UPI, and cards.',
  robots: {
    index: false, // Don't index checkout pages
    follow: false,
  },
};

export default function CheckoutLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
