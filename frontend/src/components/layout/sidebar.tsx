'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { ChevronDown, ChevronLeft, Menu, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/providers';
import { navigation, NavItem } from '@/config/navigation';
import { siteConfig } from '@/config/site';

interface SidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
}

// Zoho/Freshworks-style module colors - vibrant and distinct
const moduleColors: Record<string, { bg: string; text: string; hover: string; gradient: string }> = {
  'Dashboard': {
    bg: 'bg-violet-100 dark:bg-violet-900/30',
    text: 'text-violet-600 dark:text-violet-400',
    hover: 'hover:bg-violet-50 dark:hover:bg-violet-900/20',
    gradient: 'from-violet-500 to-purple-600'
  },
  'Sales': {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-600 dark:text-blue-400',
    hover: 'hover:bg-blue-50 dark:hover:bg-blue-900/20',
    gradient: 'from-blue-500 to-cyan-600'
  },
  'CRM': {
    bg: 'bg-pink-100 dark:bg-pink-900/30',
    text: 'text-pink-600 dark:text-pink-400',
    hover: 'hover:bg-pink-50 dark:hover:bg-pink-900/20',
    gradient: 'from-pink-500 to-rose-600'
  },
  'Procurement': {
    bg: 'bg-orange-100 dark:bg-orange-900/30',
    text: 'text-orange-600 dark:text-orange-400',
    hover: 'hover:bg-orange-50 dark:hover:bg-orange-900/20',
    gradient: 'from-orange-500 to-amber-600'
  },
  'Inventory': {
    bg: 'bg-emerald-100 dark:bg-emerald-900/30',
    text: 'text-emerald-600 dark:text-emerald-400',
    hover: 'hover:bg-emerald-50 dark:hover:bg-emerald-900/20',
    gradient: 'from-emerald-500 to-teal-600'
  },
  'Warehouse (WMS)': {
    bg: 'bg-teal-100 dark:bg-teal-900/30',
    text: 'text-teal-600 dark:text-teal-400',
    hover: 'hover:bg-teal-50 dark:hover:bg-teal-900/20',
    gradient: 'from-teal-500 to-cyan-600'
  },
  'Logistics': {
    bg: 'bg-sky-100 dark:bg-sky-900/30',
    text: 'text-sky-600 dark:text-sky-400',
    hover: 'hover:bg-sky-50 dark:hover:bg-sky-900/20',
    gradient: 'from-sky-500 to-blue-600'
  },
  'Planning (S&OP)': {
    bg: 'bg-purple-100 dark:bg-purple-900/30',
    text: 'text-purple-600 dark:text-purple-400',
    hover: 'hover:bg-purple-50 dark:hover:bg-purple-900/20',
    gradient: 'from-purple-500 to-indigo-600'
  },
  'Finance': {
    bg: 'bg-amber-100 dark:bg-amber-900/30',
    text: 'text-amber-600 dark:text-amber-400',
    hover: 'hover:bg-amber-50 dark:hover:bg-amber-900/20',
    gradient: 'from-amber-500 to-yellow-600'
  },
  'Service': {
    bg: 'bg-rose-100 dark:bg-rose-900/30',
    text: 'text-rose-600 dark:text-rose-400',
    hover: 'hover:bg-rose-50 dark:hover:bg-rose-900/20',
    gradient: 'from-rose-500 to-pink-600'
  },
  'Human Resources': {
    bg: 'bg-indigo-100 dark:bg-indigo-900/30',
    text: 'text-indigo-600 dark:text-indigo-400',
    hover: 'hover:bg-indigo-50 dark:hover:bg-indigo-900/20',
    gradient: 'from-indigo-500 to-violet-600'
  },
  'Master Data': {
    bg: 'bg-cyan-100 dark:bg-cyan-900/30',
    text: 'text-cyan-600 dark:text-cyan-400',
    hover: 'hover:bg-cyan-50 dark:hover:bg-cyan-900/20',
    gradient: 'from-cyan-500 to-sky-600'
  },
  'Intelligence': {
    bg: 'bg-fuchsia-100 dark:bg-fuchsia-900/30',
    text: 'text-fuchsia-600 dark:text-fuchsia-400',
    hover: 'hover:bg-fuchsia-50 dark:hover:bg-fuchsia-900/20',
    gradient: 'from-fuchsia-500 to-pink-600'
  },
  'Administration': {
    bg: 'bg-slate-100 dark:bg-slate-800/50',
    text: 'text-slate-600 dark:text-slate-400',
    hover: 'hover:bg-slate-50 dark:hover:bg-slate-800/30',
    gradient: 'from-slate-500 to-gray-600'
  },
  'D2C Content': {
    bg: 'bg-lime-100 dark:bg-lime-900/30',
    text: 'text-lime-600 dark:text-lime-400',
    hover: 'hover:bg-lime-50 dark:hover:bg-lime-900/20',
    gradient: 'from-lime-500 to-green-600'
  },
};

// Badge colors for different badge types
const badgeStyles: Record<string, string> = {
  'NEW': 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white',
  'AI': 'bg-gradient-to-r from-fuchsia-500 to-purple-500 text-white',
  'pending': 'bg-gradient-to-r from-amber-500 to-orange-500 text-white animate-pulse',
  'default': 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white',
};

export function Sidebar({ isCollapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const { hasAnyPermission } = useAuth();
  const [expandedItems, setExpandedItems] = useState<string[]>([]);

  const toggleExpand = (title: string) => {
    setExpandedItems((prev) =>
      prev.includes(title)
        ? prev.filter((item) => item !== title)
        : [...prev, title]
    );
  };

  const isActive = (href?: string) => {
    if (!href) return false;
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const canAccess = (item: NavItem): boolean => {
    if (!item.permissions || item.permissions.length === 0) return true;
    return hasAnyPermission(item.permissions);
  };

  const filteredNavigation = navigation.filter(canAccess);

  const getModuleColor = (title: string) => {
    return moduleColors[title] || moduleColors['Administration'];
  };

  const renderBadge = (badge?: string) => {
    if (!badge) return null;
    const style = badgeStyles[badge] || badgeStyles['default'];
    return (
      <span className={cn(
        'ml-auto px-1.5 py-0.5 text-[9px] font-bold rounded-full uppercase tracking-wider shadow-sm',
        style
      )}>
        {badge === 'AI' ? <Sparkles className="h-2.5 w-2.5" /> : badge}
      </span>
    );
  };

  const renderNavItem = (item: NavItem, level: number = 0, parentColor?: typeof moduleColors[string]) => {
    if (!canAccess(item)) return null;

    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.includes(item.title);
    const active = isActive(item.href);
    const Icon = item.icon;
    const colors = level === 0 ? getModuleColor(item.title) : parentColor;

    if (hasChildren) {
      const filteredChildren = item.children!.filter(canAccess);
      if (filteredChildren.length === 0) return null;

      return (
        <div key={item.title}>
          <button
            onClick={() => toggleExpand(item.title)}
            className={cn(
              'group flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-medium transition-all duration-200',
              colors?.hover,
              isExpanded && colors?.bg,
              'hover:shadow-sm'
            )}
          >
            {Icon && (
              <div className={cn(
                'flex h-6 w-6 items-center justify-center rounded-md transition-all duration-200',
                isExpanded ? colors?.bg : 'bg-transparent group-hover:' + colors?.bg?.replace('bg-', 'bg-'),
                colors?.text
              )}>
                <Icon className="h-3.5 w-3.5" />
              </div>
            )}
            {!isCollapsed && (
              <>
                <span className={cn(
                  'flex-1 text-left font-semibold',
                  isExpanded && colors?.text
                )}>
                  {item.title}
                </span>
                {renderBadge(item.badge)}
                <ChevronDown
                  className={cn(
                    'h-3.5 w-3.5 transition-transform duration-200',
                    isExpanded && 'rotate-180',
                    colors?.text
                  )}
                />
              </>
            )}
          </button>
          {!isCollapsed && isExpanded && (
            <div className={cn(
              'ml-4 mt-0.5 space-y-0 border-l-2 pl-3 py-0.5',
              colors?.text?.replace('text-', 'border-')
            )}>
              {filteredChildren.map((child) => renderNavItem(child, level + 1, colors))}
            </div>
          )}
        </div>
      );
    }

    // Leaf item (no children)
    return (
      <Link
        key={item.title}
        href={item.href || '#'}
        className={cn(
          'group flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-all duration-200',
          level === 0 ? 'font-medium' : 'font-normal text-[13px]',
          level === 0 && colors?.hover,
          active
            ? cn(
                'shadow-md',
                level === 0
                  ? `bg-gradient-to-r ${colors?.gradient} text-white`
                  : `${colors?.bg} ${colors?.text} font-semibold`
              )
            : level > 0
              ? 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
              : ''
        )}
      >
        {Icon && (
          <div className={cn(
            'flex h-6 w-6 items-center justify-center rounded-md transition-all duration-200',
            active && level === 0
              ? 'bg-white/20'
              : level === 0
                ? cn('group-hover:' + colors?.bg?.replace('bg-', 'bg-'), colors?.text)
                : ''
          )}>
            <Icon className={cn(
              'h-3.5 w-3.5',
              active && level === 0 ? 'text-white' : ''
            )} />
          </div>
        )}
        {!isCollapsed && (
          <>
            <span className={cn(
              active && level > 0 && 'font-semibold'
            )}>
              {item.title}
            </span>
            {renderBadge(item.badge)}
          </>
        )}
      </Link>
    );
  };

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-50 flex flex-col border-r bg-gradient-to-b from-background via-background to-muted/20 transition-all duration-300 shadow-xl',
        isCollapsed ? 'w-16' : 'w-72'
      )}
    >
      {/* Header with gradient */}
      <div className={cn(
        'relative flex h-16 items-center justify-between border-b px-4',
        'bg-gradient-to-r from-primary/10 via-secondary/10 to-primary/5'
      )}>
        {!isCollapsed && (
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-primary to-secondary rounded-xl blur-sm opacity-50 group-hover:opacity-75 transition-opacity" />
              <Image
                src="/logo.png"
                alt="Aquapurite Logo"
                width={36}
                height={36}
                className="relative rounded-xl shadow-md"
              />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-sm bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                Aquapurite
              </span>
              <span className="text-[10px] text-muted-foreground font-medium">
                ERP System
              </span>
            </div>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className={cn(
            'rounded-xl hover:bg-primary/10 transition-all',
            isCollapsed && 'mx-auto'
          )}
        >
          {isCollapsed ? (
            <Menu className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Navigation - with native scrolling and visible scrollbar */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-2 space-y-0.5 sidebar-scroll">
        {filteredNavigation.map((item) => renderNavItem(item))}
      </nav>

      {/* Footer with gradient */}
      {!isCollapsed && (
        <div className={cn(
          'border-t px-3 py-2',
          'bg-gradient-to-r from-muted/50 via-background to-muted/30'
        )}>
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <p className="text-[10px] text-muted-foreground">
              System Online
            </p>
          </div>
          <p className="text-[9px] text-muted-foreground mt-0.5">
            &copy; {new Date().getFullYear()} {siteConfig.company}
          </p>
        </div>
      )}
    </aside>
  );
}
