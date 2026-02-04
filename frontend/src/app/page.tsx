import { redirect } from 'next/navigation';

/**
 * Root page - redirects to ERP login
 *
 * This is a SaaS ERP platform. The root URL redirects to the login page.
 * The D2C storefront is a separate module accessible via tenant subdomains.
 */
export default function RootPage() {
  redirect('/login');
}
