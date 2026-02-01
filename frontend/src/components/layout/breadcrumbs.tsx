'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight, Home } from 'lucide-react';
import { cn } from '@/lib/utils';

interface BreadcrumbItem {
  label: string;
  href: string;
}

const pathLabels: Record<string, string> = {
  dashboard: 'Dashboard',
  'access-control': 'Access Control',
  users: 'Users',
  roles: 'Roles',
  permissions: 'Permissions',
  products: 'Products',
  categories: 'Categories',
  brands: 'Brands',
  orders: 'Orders',
  inventory: 'Inventory',
  warehouses: 'Warehouses',
  transfers: 'Transfers',
  procurement: 'Procurement',
  vendors: 'Vendors',
  'purchase-orders': 'Purchase Orders',
  grn: 'GRN',
  finance: 'Finance',
  'chart-of-accounts': 'Chart of Accounts',
  'journal-entries': 'Journal Entries',
  'general-ledger': 'General Ledger',
  billing: 'Billing',
  invoices: 'Invoices',
  'eway-bills': 'E-Way Bills',
  'credit-notes': 'Credit Notes',
  service: 'Service',
  requests: 'Requests',
  installations: 'Installations',
  amc: 'AMC',
  technicians: 'Technicians',
  distribution: 'Distribution',
  dealers: 'Dealers',
  'pricing-tiers': 'Pricing Tiers',
  franchisees: 'Franchisees',
  logistics: 'Logistics',
  shipments: 'Shipments',
  manifests: 'Manifests',
  transporters: 'Transporters',
  serviceability: 'Serviceability',
  crm: 'CRM',
  customers: 'Customers',
  leads: 'Leads',
  'call-center': 'Call Center',
  escalations: 'Escalations',
  marketing: 'Marketing',
  campaigns: 'Campaigns',
  promotions: 'Promotions',
  commissions: 'Commissions',
  serialization: 'Serialization',
  approvals: 'Approvals',
  'audit-logs': 'Audit Logs',
  settings: 'Settings',
  new: 'New',
  edit: 'Edit',
};

export function Breadcrumbs() {
  const pathname = usePathname();

  const generateBreadcrumbs = (): BreadcrumbItem[] => {
    const paths = pathname.split('/').filter(Boolean);
    const breadcrumbs: BreadcrumbItem[] = [];

    let currentPath = '';
    for (const segment of paths) {
      currentPath += `/${segment}`;

      // Skip UUID-like segments, show them as "Details"
      const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(segment);

      breadcrumbs.push({
        label: isUuid ? 'Details' : pathLabels[segment] || segment.charAt(0).toUpperCase() + segment.slice(1),
        href: currentPath,
      });
    }

    return breadcrumbs;
  };

  const breadcrumbs = generateBreadcrumbs();

  return (
    <nav className="flex items-center space-x-1 text-sm">
      <Link
        href="/dashboard"
        className="flex items-center text-muted-foreground hover:text-foreground transition-colors"
      >
        <Home className="h-4 w-4" />
      </Link>

      {breadcrumbs.map((item, index) => (
        <div key={item.href} className="flex items-center">
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
          <Link
            href={item.href}
            className={cn(
              'ml-1 transition-colors',
              index === breadcrumbs.length - 1
                ? 'font-medium text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {item.label}
          </Link>
        </div>
      ))}
    </nav>
  );
}
