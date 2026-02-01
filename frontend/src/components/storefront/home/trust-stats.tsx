'use client';

import {
  Users,
  MapPin,
  Clock,
  Shield,
  Award,
  Wrench,
  Star,
  CheckCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatItem {
  icon: React.ReactNode;
  value: string;
  label: string;
  sublabel?: string;
}

const stats: StatItem[] = [
  {
    icon: <Users className="h-8 w-8" />,
    value: '10,000+',
    label: 'Happy Customers',
    sublabel: 'across India',
  },
  {
    icon: <MapPin className="h-8 w-8" />,
    value: '500+',
    label: 'Cities Covered',
    sublabel: 'pan India service',
  },
  {
    icon: <Wrench className="h-8 w-8" />,
    value: '200+',
    label: 'Service Technicians',
    sublabel: 'trained professionals',
  },
  {
    icon: <Star className="h-8 w-8" />,
    value: '4.8',
    label: 'Customer Rating',
    sublabel: 'based on reviews',
  },
];

const certifications = [
  { icon: <Shield className="h-5 w-5" />, label: 'ISI Certified' },
  { icon: <Award className="h-5 w-5" />, label: 'BIS Standard' },
  { icon: <CheckCircle className="h-5 w-5" />, label: 'ISO 9001:2015' },
];

interface TrustStatsProps {
  className?: string;
  variant?: 'default' | 'compact';
}

export default function TrustStats({ className, variant = 'default' }: TrustStatsProps) {
  if (variant === 'compact') {
    return (
      <div className={cn('bg-primary/5 py-4', className)}>
        <div className="container mx-auto px-4">
          <div className="flex flex-wrap items-center justify-center gap-6 md:gap-12">
            {stats.map((stat, index) => (
              <div key={index} className="flex items-center gap-2 text-center">
                <div className="text-primary">{stat.icon}</div>
                <div>
                  <span className="font-bold text-lg text-gray-900">{stat.value}</span>
                  <span className="text-sm text-gray-600 ml-1">{stat.label}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <section className={cn('py-16 bg-gradient-to-b from-gray-50 to-white', className)}>
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Trusted by Thousands of Indian Families
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Join the growing community of health-conscious families who trust Aquapurite
            for pure, safe drinking water every day.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8 mb-12">
          {stats.map((stat, index) => (
            <div
              key={index}
              className="bg-white rounded-2xl p-6 text-center shadow-sm border border-gray-100 hover:shadow-md hover:border-primary/20 transition-all duration-300"
            >
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 text-primary mb-4">
                {stat.icon}
              </div>
              <div className="text-3xl md:text-4xl font-bold text-gray-900 mb-1">
                {stat.value}
              </div>
              <div className="text-sm font-medium text-gray-900">{stat.label}</div>
              {stat.sublabel && (
                <div className="text-xs text-gray-500 mt-1">{stat.sublabel}</div>
              )}
            </div>
          ))}
        </div>

        {/* Certifications */}
        <div className="flex flex-wrap items-center justify-center gap-4 md:gap-8 pt-8 border-t border-gray-200">
          <span className="text-sm text-gray-500 font-medium">Certified & Compliant:</span>
          {certifications.map((cert, index) => (
            <div
              key={index}
              className="flex items-center gap-2 bg-white px-4 py-2 rounded-full border border-gray-200 shadow-sm"
            >
              <span className="text-primary">{cert.icon}</span>
              <span className="text-sm font-medium text-gray-700">{cert.label}</span>
            </div>
          ))}
        </div>

        {/* Trust Message */}
        <div className="mt-12 text-center">
          <div className="inline-flex items-center gap-2 bg-green-50 text-green-700 px-6 py-3 rounded-full border border-green-200">
            <CheckCircle className="h-5 w-5" />
            <span className="font-medium">100% Genuine Products with Manufacturer Warranty</span>
          </div>
        </div>
      </div>
    </section>
  );
}
