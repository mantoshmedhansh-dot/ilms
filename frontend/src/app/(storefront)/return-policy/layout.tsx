import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Return & Refund Policy | Aquapurite',
  description: 'Learn about Aquapurite return and refund policy. Easy 7-day returns on eligible products with hassle-free refund process.',
  keywords: ['return policy', 'refund policy', 'returns', 'refund', 'aquapurite returns', 'water purifier returns'],
  openGraph: {
    title: 'Return & Refund Policy | Aquapurite',
    description: 'Learn about Aquapurite return and refund policy. Easy 7-day returns on eligible products with hassle-free refund process.',
    type: 'website',
  },
};

export default function ReturnPolicyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
