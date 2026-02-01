'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  LayoutDashboard,
  ShoppingCart,
  Users,
  Package,
  Building2,
  FileText,
  Truck,
  Wrench,
  BarChart3,
  Settings,
  Shield,
  Boxes,
  Warehouse,
  Calculator,
  UserCircle,
  Search,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SearchResult {
  id: string;
  title: string;
  href: string;
  category: string;
  icon?: React.ElementType;
}

// Navigation items for quick access
const navigationItems: SearchResult[] = [
  // Dashboard
  { id: 'dashboard', title: 'Dashboard', href: '/dashboard', category: 'Navigation', icon: LayoutDashboard },

  // Sales & CRM
  { id: 'orders', title: 'Orders', href: '/dashboard/orders', category: 'Sales & CRM', icon: ShoppingCart },
  { id: 'customers', title: 'Customers', href: '/dashboard/customers', category: 'Sales & CRM', icon: Users },
  { id: 'leads', title: 'Leads', href: '/dashboard/leads', category: 'Sales & CRM', icon: UserCircle },
  { id: 'dealers', title: 'Dealers', href: '/dashboard/dealers', category: 'Sales & CRM', icon: Building2 },

  // Procurement
  { id: 'vendors', title: 'Vendors', href: '/dashboard/procurement/vendors', category: 'Procurement', icon: Building2 },
  { id: 'purchase-orders', title: 'Purchase Orders', href: '/dashboard/procurement/purchase-orders', category: 'Procurement', icon: FileText },

  // Inventory
  { id: 'products', title: 'Products', href: '/dashboard/products', category: 'Inventory', icon: Package },
  { id: 'stock', title: 'Stock Items', href: '/dashboard/inventory/stock', category: 'Inventory', icon: Boxes },
  { id: 'warehouses', title: 'Warehouses', href: '/dashboard/inventory/warehouses', category: 'Inventory', icon: Warehouse },

  // Logistics
  { id: 'shipments', title: 'Shipments', href: '/dashboard/logistics/shipments', category: 'Logistics', icon: Truck },

  // Service
  { id: 'service-requests', title: 'Service Requests', href: '/dashboard/service/requests', category: 'Service', icon: Wrench },
  { id: 'installations', title: 'Installations', href: '/dashboard/service/installations', category: 'Service', icon: Wrench },

  // Finance
  { id: 'invoices', title: 'Invoices', href: '/dashboard/billing/invoices', category: 'Finance', icon: FileText },
  { id: 'payments', title: 'Payments', href: '/dashboard/billing/payments', category: 'Finance', icon: Calculator },
  { id: 'chart-of-accounts', title: 'Chart of Accounts', href: '/dashboard/finance/chart-of-accounts', category: 'Finance', icon: Calculator },

  // Planning
  { id: 'snop', title: 'S&OP Dashboard', href: '/dashboard/planning/snop', category: 'Planning', icon: BarChart3 },
  { id: 'forecasts', title: 'Demand Forecasts', href: '/dashboard/planning/forecasts', category: 'Planning', icon: BarChart3 },

  // Administration
  { id: 'settings', title: 'Settings', href: '/dashboard/settings', category: 'Administration', icon: Settings },
  { id: 'users', title: 'Users', href: '/dashboard/access-control/users', category: 'Administration', icon: Users },
  { id: 'roles', title: 'Roles', href: '/dashboard/access-control/roles', category: 'Administration', icon: Shield },
];

// Group items by category
const groupedItems = navigationItems.reduce((acc, item) => {
  if (!acc[item.category]) {
    acc[item.category] = [];
  }
  acc[item.category].push(item);
  return acc;
}, {} as Record<string, SearchResult[]>);

interface GlobalSearchProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function GlobalSearch({ open: controlledOpen, onOpenChange }: GlobalSearchProps) {
  const router = useRouter();
  const [internalOpen, setInternalOpen] = useState(false);

  // Use controlled or uncontrolled state
  const open = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const setOpen = onOpenChange || setInternalOpen;

  // Handle keyboard shortcut
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen(!open);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [open, setOpen]);

  const runCommand = useCallback(
    (command: () => unknown) => {
      setOpen(false);
      command();
    },
    [setOpen]
  );

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search pages, orders, customers..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {Object.entries(groupedItems).map(([category, items], index) => (
          <div key={category}>
            {index > 0 && <CommandSeparator />}
            <CommandGroup heading={category}>
              {items.map((item) => {
                const Icon = item.icon || FileText;
                return (
                  <CommandItem
                    key={item.id}
                    value={item.title}
                    onSelect={() => runCommand(() => router.push(item.href))}
                  >
                    <Icon className="mr-2 h-4 w-4" />
                    <span>{item.title}</span>
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </div>
        ))}
      </CommandList>
    </CommandDialog>
  );
}

// Search trigger button for header
export function GlobalSearchTrigger() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        variant="outline"
        className="relative h-9 w-9 p-0 xl:h-10 xl:w-60 xl:justify-start xl:px-3 xl:py-2"
        onClick={() => setOpen(true)}
      >
        <Search className="h-4 w-4 xl:mr-2" />
        <span className="hidden xl:inline-flex">Search...</span>
        <kbd className="pointer-events-none absolute right-1.5 top-1.5 hidden h-6 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 xl:flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </Button>
      <GlobalSearch open={open} onOpenChange={setOpen} />
    </>
  );
}
