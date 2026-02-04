import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Contact Us | ILMS.AI',
  description: 'Get in touch with ILMS.AI for product inquiries, service requests, or general questions. We are here to help you with all your water purifier needs.',
  keywords: ['contact ILMS.AI', 'water purifier support', 'customer service', 'service request'],
  openGraph: {
    title: 'Contact Us | ILMS.AI',
    description: 'Get in touch with ILMS.AI for product inquiries, service requests, or general questions.',
    type: 'website',
  },
};

export default function ContactLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
