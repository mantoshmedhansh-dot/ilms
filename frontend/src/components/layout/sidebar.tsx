'use client';

import { useState } from 'react';
import Link from 'next/link';
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

// Flat badge styles (no gradients)
const badgeStyles: Record<string, string> = {
  'NEW': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400',
  'AI': 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-400',
  'pending': 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400',
  'default': 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-400',
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

  const renderBadge = (badge?: string) => {
    if (!badge) return null;
    const style = badgeStyles[badge] || badgeStyles['default'];
    return (
      <span className={cn(
        'ml-auto px-1.5 py-0.5 text-[9px] font-bold rounded-full uppercase tracking-wider',
        style
      )}>
        {badge === 'AI' ? <Sparkles className="h-2.5 w-2.5" /> : badge}
      </span>
    );
  };

  const renderNavItem = (item: NavItem, level: number = 0) => {
    if (!canAccess(item)) return null;

    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.includes(item.title);
    const active = isActive(item.href);
    const Icon = item.icon;

    if (hasChildren) {
      const filteredChildren = item.children!.filter(canAccess);
      if (filteredChildren.length === 0) return null;

      return (
        <div key={item.title}>
          <button
            onClick={() => toggleExpand(item.title)}
            className={cn(
              'group flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-medium transition-colors',
              isExpanded
                ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950/30 dark:text-indigo-400'
                : 'text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800/50'
            )}
          >
            {Icon && (
              <div className="flex h-6 w-6 items-center justify-center rounded-md">
                <Icon className="h-4 w-4" />
              </div>
            )}
            {!isCollapsed && (
              <>
                <span className="flex-1 text-left font-semibold">
                  {item.title}
                </span>
                {renderBadge(item.badge)}
                <ChevronDown
                  className={cn(
                    'h-3.5 w-3.5 transition-transform duration-200',
                    isExpanded && 'rotate-180'
                  )}
                />
              </>
            )}
          </button>
          {!isCollapsed && isExpanded && (
            <div className="ml-4 mt-0.5 space-y-0 border-l-2 border-slate-200 dark:border-slate-700 pl-3 py-0.5">
              {filteredChildren.map((child) => renderNavItem(child, level + 1))}
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
          'group flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors',
          level === 0 ? 'font-medium' : 'font-normal text-[13px]',
          active
            ? level === 0
              ? 'bg-indigo-50 text-indigo-600 border-l-2 border-indigo-600 dark:bg-indigo-950/30 dark:text-indigo-400 dark:border-indigo-400'
              : 'bg-indigo-50 text-indigo-600 font-semibold dark:bg-indigo-950/30 dark:text-indigo-400'
            : level === 0
              ? 'text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800/50'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
        )}
      >
        {Icon && (
          <div className="flex h-6 w-6 items-center justify-center rounded-md">
            <Icon className="h-4 w-4" />
          </div>
        )}
        {!isCollapsed && (
          <>
            <span>{item.title}</span>
            {renderBadge(item.badge)}
          </>
        )}
      </Link>
    );
  };

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-72'
      )}
    >
      {/* Header */}
      <div className="flex h-14 items-center justify-between border-b border-slate-200 dark:border-slate-800 px-4">
        {!isCollapsed && (
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="flex flex-col">
              <span className="font-bold text-lg text-foreground">
                ILMS.AI
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
            'rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors',
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

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-2 space-y-0.5 sidebar-scroll">
        {filteredNavigation.map((item) => renderNavItem(item))}
      </nav>

      {/* Footer */}
      {!isCollapsed && (
        <div className="border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 px-3 py-2">
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
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
