'use client';

import { useState, useMemo } from 'react';
import {
  Droplets,
  Shield,
  Award,
  Truck,
  Headphones,
  Wrench,
  Star,
  Heart,
  Clock,
  CheckCircle,
  Zap,
  Leaf,
  Sun,
  ThumbsUp,
  Gift,
  CreditCard,
  MapPin,
  Phone,
  Mail,
  Calendar,
  Users,
  Home,
  Settings,
  Package,
  ShoppingCart,
  Tag,
  Percent,
  RefreshCw,
  Lock,
  Eye,
  Globe,
  Sparkles,
  BadgeCheck,
  Fingerprint,
  Gauge,
  Rocket,
  Target,
  TrendingUp,
  ShieldCheck,
  Timer,
  Banknote,
  Wallet,
  type LucideIcon,
} from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

// Icon registry with display names
const iconRegistry: Record<string, { icon: LucideIcon; label: string; category: string }> = {
  // Features / USPs
  droplets: { icon: Droplets, label: 'Water/Droplets', category: 'Features' },
  shield: { icon: Shield, label: 'Shield', category: 'Features' },
  'shield-check': { icon: ShieldCheck, label: 'Shield Check', category: 'Features' },
  award: { icon: Award, label: 'Award', category: 'Features' },
  'badge-check': { icon: BadgeCheck, label: 'Badge Check', category: 'Features' },
  star: { icon: Star, label: 'Star', category: 'Features' },
  sparkles: { icon: Sparkles, label: 'Sparkles', category: 'Features' },
  zap: { icon: Zap, label: 'Lightning', category: 'Features' },
  rocket: { icon: Rocket, label: 'Rocket', category: 'Features' },
  target: { icon: Target, label: 'Target', category: 'Features' },
  'trending-up': { icon: TrendingUp, label: 'Trending Up', category: 'Features' },
  gauge: { icon: Gauge, label: 'Gauge', category: 'Features' },

  // Service
  truck: { icon: Truck, label: 'Delivery/Truck', category: 'Service' },
  headphones: { icon: Headphones, label: 'Support', category: 'Service' },
  wrench: { icon: Wrench, label: 'Service/Wrench', category: 'Service' },
  settings: { icon: Settings, label: 'Settings', category: 'Service' },
  'refresh-cw': { icon: RefreshCw, label: 'Refresh/Return', category: 'Service' },
  timer: { icon: Timer, label: 'Timer', category: 'Service' },

  // Trust
  lock: { icon: Lock, label: 'Lock/Security', category: 'Trust' },
  fingerprint: { icon: Fingerprint, label: 'Fingerprint', category: 'Trust' },
  eye: { icon: Eye, label: 'Eye/Visibility', category: 'Trust' },
  'check-circle': { icon: CheckCircle, label: 'Checkmark', category: 'Trust' },
  'thumbs-up': { icon: ThumbsUp, label: 'Thumbs Up', category: 'Trust' },

  // Nature
  leaf: { icon: Leaf, label: 'Eco/Leaf', category: 'Nature' },
  sun: { icon: Sun, label: 'Sun', category: 'Nature' },
  globe: { icon: Globe, label: 'Globe', category: 'Nature' },

  // Commerce
  'shopping-cart': { icon: ShoppingCart, label: 'Cart', category: 'Commerce' },
  package: { icon: Package, label: 'Package', category: 'Commerce' },
  tag: { icon: Tag, label: 'Tag', category: 'Commerce' },
  percent: { icon: Percent, label: 'Discount', category: 'Commerce' },
  gift: { icon: Gift, label: 'Gift', category: 'Commerce' },
  'credit-card': { icon: CreditCard, label: 'Credit Card', category: 'Commerce' },
  banknote: { icon: Banknote, label: 'Banknote', category: 'Commerce' },
  wallet: { icon: Wallet, label: 'Wallet', category: 'Commerce' },

  // Contact
  phone: { icon: Phone, label: 'Phone', category: 'Contact' },
  mail: { icon: Mail, label: 'Email', category: 'Contact' },
  'map-pin': { icon: MapPin, label: 'Location', category: 'Contact' },

  // General
  heart: { icon: Heart, label: 'Heart', category: 'General' },
  clock: { icon: Clock, label: 'Clock', category: 'General' },
  calendar: { icon: Calendar, label: 'Calendar', category: 'General' },
  users: { icon: Users, label: 'Users', category: 'General' },
  home: { icon: Home, label: 'Home', category: 'General' },
};

interface IconPickerProps {
  value?: string;
  onChange?: (iconName: string) => void;
  className?: string;
}

export function IconPicker({ value, onChange, className }: IconPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  const filteredIcons = useMemo(() => {
    if (!search) return Object.entries(iconRegistry);
    const term = search.toLowerCase();
    return Object.entries(iconRegistry).filter(
      ([key, { label, category }]) =>
        key.includes(term) ||
        label.toLowerCase().includes(term) ||
        category.toLowerCase().includes(term)
    );
  }, [search]);

  // Group icons by category
  const groupedIcons = useMemo(() => {
    const groups: Record<string, typeof filteredIcons> = {};
    filteredIcons.forEach(([key, data]) => {
      if (!groups[data.category]) {
        groups[data.category] = [];
      }
      groups[data.category].push([key, data]);
    });
    return groups;
  }, [filteredIcons]);

  const selectedIcon = value ? iconRegistry[value] : null;
  const SelectedIconComponent = selectedIcon?.icon;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn('w-full justify-start', className)}
        >
          {SelectedIconComponent ? (
            <>
              <SelectedIconComponent className="mr-2 h-4 w-4" />
              <span>{selectedIcon?.label}</span>
            </>
          ) : (
            <span className="text-muted-foreground">Select an icon...</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="start">
        <div className="p-2">
          <Input
            placeholder="Search icons..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8"
          />
        </div>
        <ScrollArea className="h-72">
          <div className="p-2">
            {Object.entries(groupedIcons).map(([category, icons]) => (
              <div key={category} className="mb-3">
                <div className="text-xs font-semibold text-muted-foreground mb-2 px-1">
                  {category}
                </div>
                <div className="grid grid-cols-6 gap-1">
                  {icons.map(([key, { icon: Icon, label }]) => (
                    <Button
                      key={key}
                      variant="ghost"
                      size="sm"
                      className={cn(
                        'h-8 w-8 p-0',
                        value === key && 'bg-primary text-primary-foreground'
                      )}
                      onClick={() => {
                        onChange?.(key);
                        setOpen(false);
                        setSearch('');
                      }}
                      title={label}
                    >
                      <Icon className="h-4 w-4" />
                    </Button>
                  ))}
                </div>
              </div>
            ))}
            {filteredIcons.length === 0 && (
              <div className="text-center text-sm text-muted-foreground py-4">
                No icons found
              </div>
            )}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}

// Helper function to render an icon by name
export function IconByName({
  name,
  className,
}: {
  name: string;
  className?: string;
}) {
  const iconData = iconRegistry[name];
  if (!iconData) return null;
  const Icon = iconData.icon;
  return <Icon className={className} />;
}

export default IconPicker;
