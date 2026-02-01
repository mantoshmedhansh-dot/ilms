import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'My Account | Aquapurite',
  description: 'Manage your account, view orders, track deliveries, and update your profile.',
  robots: {
    index: false, // Don't index account pages
    follow: false,
  },
};

export default function AccountLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
