import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Become a Partner | ILMS.AI',
  description: 'Join our community partner program and earn commissions by referring customers. Easy registration, no investment required, earn up to 15% commission.',
  keywords: ['partner program', 'affiliate', 'earn commission', 'water purifier partner', 'ILMS.AI partner'],
  openGraph: {
    title: 'Become a Partner | ILMS.AI',
    description: 'Join our community partner program and earn commissions by referring customers.',
    type: 'website',
  },
};

export default function BecomePartnerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
