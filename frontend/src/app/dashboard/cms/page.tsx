'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
  Menu,
  LayoutGrid,
  Star,
  Image,
  Award,
  MessageSquare,
  Bell,
  FileText,
  Search,
  Settings,
  ExternalLink,
  Plus,
  Eye,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/common';
import { cmsApi } from '@/lib/api/cms';

interface CMSSection {
  title: string;
  description: string;
  href: string;
  icon: React.ElementType;
  color: string;
  queryKey: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  fetchFn: () => Promise<any>;
}

const cmsSections: CMSSection[] = [
  {
    title: 'Header Navigation',
    description: 'Manage header and footer navigation links',
    href: '/dashboard/cms/navigation',
    icon: Menu,
    color: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30',
    queryKey: 'cms-menu-items',
    fetchFn: () => cmsApi.menuItems.list(),
  },
  {
    title: 'Mega Menu',
    description: 'Configure product category mega menu',
    href: '/dashboard/cms/mega-menu',
    icon: LayoutGrid,
    color: 'text-purple-600 bg-purple-100 dark:bg-purple-900/30',
    queryKey: 'cms-mega-menu',
    fetchFn: () => cmsApi.megaMenuItems.list(),
  },
  {
    title: 'Feature Bars',
    description: 'Trust badges below the header',
    href: '/dashboard/cms/feature-bars',
    icon: Star,
    color: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30',
    queryKey: 'cms-feature-bars',
    fetchFn: () => cmsApi.featureBars.list(),
  },
  {
    title: 'Hero Banners',
    description: 'Homepage carousel banners',
    href: '/dashboard/cms/banners',
    icon: Image,
    color: 'text-pink-600 bg-pink-100 dark:bg-pink-900/30',
    queryKey: 'cms-banners',
    fetchFn: () => cmsApi.banners.list(),
  },
  {
    title: 'USPs/Features',
    description: 'Why choose us section highlights',
    href: '/dashboard/cms/usps',
    icon: Award,
    color: 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30',
    queryKey: 'cms-usps',
    fetchFn: () => cmsApi.usps.list(),
  },
  {
    title: 'Testimonials',
    description: 'Customer reviews and testimonials',
    href: '/dashboard/cms/testimonials',
    icon: MessageSquare,
    color: 'text-cyan-600 bg-cyan-100 dark:bg-cyan-900/30',
    queryKey: 'cms-testimonials',
    fetchFn: () => cmsApi.testimonials.list(),
  },
  {
    title: 'Announcements',
    description: 'Site-wide notification banners',
    href: '/dashboard/cms/announcements',
    icon: Bell,
    color: 'text-orange-600 bg-orange-100 dark:bg-orange-900/30',
    queryKey: 'cms-announcements',
    fetchFn: () => cmsApi.announcements.list(),
  },
  {
    title: 'Static Pages',
    description: 'About, Contact, Terms, Privacy pages',
    href: '/dashboard/cms/pages',
    icon: FileText,
    color: 'text-indigo-600 bg-indigo-100 dark:bg-indigo-900/30',
    queryKey: 'cms-pages',
    fetchFn: () => cmsApi.pages.list(),
  },
  {
    title: 'SEO Settings',
    description: 'Page-level meta tags and SEO',
    href: '/dashboard/cms/seo',
    icon: Search,
    color: 'text-green-600 bg-green-100 dark:bg-green-900/30',
    queryKey: 'cms-seo',
    fetchFn: () => cmsApi.seo.list(),
  },
  {
    title: 'Site Settings',
    description: 'Global site configuration',
    href: '/dashboard/cms/settings',
    icon: Settings,
    color: 'text-slate-600 bg-slate-100 dark:bg-slate-800/50',
    queryKey: 'cms-settings',
    fetchFn: () => cmsApi.settings.list(),
  },
];

function CMSSectionCard({ section }: { section: CMSSection }) {
  const { data, isLoading } = useQuery({
    queryKey: [section.queryKey],
    queryFn: section.fetchFn,
    staleTime: 60000,
  });

  const items = (data?.data?.items || data?.items || []) as Array<{ is_active?: boolean }>;
  const activeCount = items.filter((item) => item.is_active !== false).length;
  const inactiveCount = items.length - activeCount;

  const Icon = section.icon;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className={`p-2 rounded-lg ${section.color}`}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="flex gap-1">
            <Button variant="ghost" size="icon" asChild>
              <Link href={section.href}>
                <Settings className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
        <CardTitle className="text-base mt-3">{section.title}</CardTitle>
        <CardDescription className="text-xs">{section.description}</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="text-sm text-muted-foreground">Loading...</div>
        ) : (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span className="text-sm font-medium">{activeCount}</span>
              <span className="text-xs text-muted-foreground">active</span>
            </div>
            {inactiveCount > 0 && (
              <div className="flex items-center gap-1.5">
                <XCircle className="h-4 w-4 text-gray-400" />
                <span className="text-sm font-medium">{inactiveCount}</span>
                <span className="text-xs text-muted-foreground">inactive</span>
              </div>
            )}
          </div>
        )}
        <div className="mt-3 flex gap-2">
          <Button size="sm" variant="outline" className="flex-1" asChild>
            <Link href={section.href}>
              <Eye className="h-3.5 w-3.5 mr-1.5" />
              Manage
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function CMSOverviewPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="D2C Content Management"
        description="Manage your storefront content, navigation, and settings"
        actions={
          <Button variant="outline" asChild>
            <a href="https://www.aquapurite.com" target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4 mr-2" />
              View Live Site
            </a>
          </Button>
        }
      />

      {/* Quick Actions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" asChild>
              <Link href="/dashboard/cms/navigation">
                <Plus className="h-4 w-4 mr-1.5" />
                Add Nav Link
              </Link>
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href="/dashboard/cms/banners">
                <Plus className="h-4 w-4 mr-1.5" />
                Add Banner
              </Link>
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href="/dashboard/cms/pages/new">
                <Plus className="h-4 w-4 mr-1.5" />
                New Page
              </Link>
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href="/dashboard/cms/announcements">
                <Plus className="h-4 w-4 mr-1.5" />
                Add Announcement
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Layout & Navigation */}
      <div>
        <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wider">
          Layout & Navigation
        </h3>
        <div className="grid gap-4 md:grid-cols-3">
          {cmsSections.slice(0, 3).map((section) => (
            <CMSSectionCard key={section.queryKey} section={section} />
          ))}
        </div>
      </div>

      {/* Homepage Content */}
      <div>
        <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wider">
          Homepage Content
        </h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {cmsSections.slice(3, 7).map((section) => (
            <CMSSectionCard key={section.queryKey} section={section} />
          ))}
        </div>
      </div>

      {/* Pages & SEO */}
      <div>
        <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wider">
          Pages & SEO
        </h3>
        <div className="grid gap-4 md:grid-cols-3">
          {cmsSections.slice(7, 10).map((section) => (
            <CMSSectionCard key={section.queryKey} section={section} />
          ))}
        </div>
      </div>
    </div>
  );
}
