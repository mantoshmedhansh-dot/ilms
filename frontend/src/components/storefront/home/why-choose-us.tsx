'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
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
import { Card, CardContent } from '@/components/ui/card';
import { contentApi, StorefrontUsp } from '@/lib/storefront/api';

// Icon registry for dynamic rendering
const iconRegistry: Record<string, LucideIcon> = {
  droplets: Droplets,
  shield: Shield,
  'shield-check': ShieldCheck,
  award: Award,
  'badge-check': BadgeCheck,
  star: Star,
  sparkles: Sparkles,
  zap: Zap,
  rocket: Rocket,
  target: Target,
  'trending-up': TrendingUp,
  gauge: Gauge,
  truck: Truck,
  headphones: Headphones,
  wrench: Wrench,
  settings: Settings,
  'refresh-cw': RefreshCw,
  timer: Timer,
  lock: Lock,
  fingerprint: Fingerprint,
  eye: Eye,
  'check-circle': CheckCircle,
  'thumbs-up': ThumbsUp,
  leaf: Leaf,
  sun: Sun,
  globe: Globe,
  'shopping-cart': ShoppingCart,
  package: Package,
  tag: Tag,
  percent: Percent,
  gift: Gift,
  'credit-card': CreditCard,
  banknote: Banknote,
  wallet: Wallet,
  phone: Phone,
  mail: Mail,
  'map-pin': MapPin,
  heart: Heart,
  clock: Clock,
  calendar: Calendar,
  users: Users,
  home: Home,
};

// Fallback USPs for when API fails or returns empty
const fallbackUsps: StorefrontUsp[] = [
  {
    id: '1',
    icon: 'droplets',
    title: '7-Stage Purification',
    description: 'Advanced RO+UV+UF technology for 100% pure drinking water',
  },
  {
    id: '2',
    icon: 'shield',
    title: '1 Year Warranty',
    description: 'Comprehensive warranty coverage on all products',
  },
  {
    id: '3',
    icon: 'award',
    title: 'ISI Certified',
    description: 'All products meet Indian quality standards',
  },
  {
    id: '4',
    icon: 'truck',
    title: 'Free Installation',
    description: 'Professional installation by trained technicians',
  },
  {
    id: '5',
    icon: 'headphones',
    title: '24/7 Support',
    description: 'Round-the-clock customer service support',
  },
  {
    id: '6',
    icon: 'wrench',
    title: 'AMC Plans',
    description: 'Annual maintenance contracts for hassle-free service',
  },
];

function IconByName({ name, className }: { name: string; className?: string }) {
  const Icon = iconRegistry[name] || Star;
  return <Icon className={className} />;
}

export default function WhyChooseUs() {
  const [usps, setUsps] = useState<StorefrontUsp[]>(fallbackUsps);

  useEffect(() => {
    const fetchUsps = async () => {
      try {
        const data = await contentApi.getUsps();
        if (data && data.length > 0) {
          setUsps(data);
        }
      } catch {
        // Keep fallback USPs on error
      }
    };
    fetchUsps();
  }, []);
  return (
    <section className="py-12 md:py-16 bg-primary text-primary-foreground">
      <div className="container mx-auto px-4">
        <div className="text-center mb-10">
          <h2 className="text-2xl md:text-3xl font-bold mb-2">
            Why Choose ILMS.AI?
          </h2>
          <p className="text-primary-foreground/80">
            India's most trusted water purification brand
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 md:gap-6">
          {usps.map((usp) => {
            const content = (
              <Card
                className="bg-white/10 border-white/20 hover:bg-white/20 transition-colors h-full"
              >
                <CardContent className="p-4 md:p-6 text-center">
                  <div className={`inline-flex items-center justify-center h-12 w-12 rounded-full bg-white/20 mb-4 ${usp.icon_color || ''}`}>
                    <IconByName name={usp.icon} className="h-6 w-6" />
                  </div>
                  <h3 className="font-semibold mb-1 text-sm md:text-base">
                    {usp.title}
                  </h3>
                  {usp.description && (
                    <p className="text-xs md:text-sm text-primary-foreground/70">
                      {usp.description}
                    </p>
                  )}
                  {usp.link_text && (
                    <p className="text-xs text-primary-foreground/90 mt-2 underline">
                      {usp.link_text}
                    </p>
                  )}
                </CardContent>
              </Card>
            );

            if (usp.link_url) {
              return (
                <Link key={usp.id} href={usp.link_url}>
                  {content}
                </Link>
              );
            }

            return <div key={usp.id}>{content}</div>;
          })}
        </div>
      </div>
    </section>
  );
}
