import { LayoutDashboard, Users, Settings, LucideIcon } from 'lucide-react';

export interface PlatformNavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
}

export const platformNavigation: PlatformNavItem[] = [
  {
    title: 'Overview',
    href: '/platform/dashboard',
    icon: LayoutDashboard,
  },
  {
    title: 'Clients',
    href: '/platform/clients',
    icon: Users,
  },
  {
    title: 'Settings',
    href: '/platform/settings',
    icon: Settings,
  },
];
