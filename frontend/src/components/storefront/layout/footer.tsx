'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Droplets,
  Phone,
  Mail,
  MapPin,
  Facebook,
  Twitter,
  Instagram,
  Youtube,
  Linkedin,
  Truck,
  Shield,
  HeadphonesIcon,
  CreditCard,
  RotateCcw,
  Award,
  Zap,
  Heart,
  Star,
  LucideIcon,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { CompanyInfo } from '@/types/storefront';
import {
  companyApi,
  contentApi,
  StorefrontMenuItem,
  StorefrontFeatureBar,
  StorefrontSettings,
} from '@/lib/storefront/api';

// Icon mapping for feature bars
const iconMap: Record<string, LucideIcon> = {
  Truck: Truck,
  Shield: Shield,
  ShieldCheck: Shield,
  Headphones: HeadphonesIcon,
  HeadphonesIcon: HeadphonesIcon,
  CreditCard: CreditCard,
  RotateCcw: RotateCcw,
  Award: Award,
  Zap: Zap,
  Heart: Heart,
  Star: Star,
};

const getIconComponent = (iconName: string): LucideIcon => {
  return iconMap[iconName] || Star;
};

export default function StorefrontFooter() {
  const [company, setCompany] = useState<CompanyInfo | null>(null);
  const [featureBars, setFeatureBars] = useState<StorefrontFeatureBar[]>([]);
  const [quickLinks, setQuickLinks] = useState<StorefrontMenuItem[]>([]);
  const [serviceLinks, setServiceLinks] = useState<StorefrontMenuItem[]>([]);
  const [settings, setSettings] = useState<StorefrontSettings>({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch menu items by specific location for better caching and efficiency
        const [companyData, featureBarsData, quickLinksData, serviceLinksData, settingsData] = await Promise.all([
          companyApi.getInfo(),
          contentApi.getFeatureBars(),
          contentApi.getMenuItems('footer_quick'),
          contentApi.getMenuItems('footer_service'),
          contentApi.getSettings(),
        ]);

        setCompany(companyData);
        setFeatureBars(featureBarsData);
        setQuickLinks(quickLinksData);
        setServiceLinks(serviceLinksData);
        setSettings(settingsData);
      } catch (error) {
        console.error('Failed to fetch footer data:', error);
      }
    };
    fetchData();
  }, []);

  // Default feature bars if none from CMS
  const displayFeatureBars = featureBars.length > 0 ? featureBars : [
    { id: '1', icon: 'Truck', title: 'Free Shipping', subtitle: 'On orders above Rs.999' },
    { id: '2', icon: 'Shield', title: 'Secure Payment', subtitle: '100% secure checkout' },
    { id: '3', icon: 'Headphones', title: '24/7 Support', subtitle: 'Dedicated customer care' },
    { id: '4', icon: 'RotateCcw', title: 'Easy Returns', subtitle: '7-day return policy' },
  ];

  // Default quick links if none from CMS
  const displayQuickLinks = quickLinks.length > 0 ? quickLinks : [
    { id: '1', menu_location: 'footer_quick', title: 'About Us', url: '/about', target: '_self', children: [] },
    { id: '2', menu_location: 'footer_quick', title: 'Our Products', url: '/products', target: '_self', children: [] },
    { id: '3', menu_location: 'footer_quick', title: 'Video Guides', url: '/guides', target: '_self', children: [] },
    { id: '4', menu_location: 'footer_quick', title: 'Refer & Earn', url: '/referral', target: '_self', children: [] },
    { id: '5', menu_location: 'footer_quick', title: 'Contact Us', url: '/contact', target: '_self', children: [] },
    { id: '6', menu_location: 'footer_quick', title: 'Track Order', url: '/track', target: '_self', children: [] },
  ];

  // Default service links if none from CMS
  const displayServiceLinks = serviceLinks.length > 0 ? serviceLinks : [
    { id: '1', menu_location: 'footer_service', title: 'Shipping Policy', url: '/shipping-policy', target: '_self', children: [] },
    { id: '2', menu_location: 'footer_service', title: 'Return & Refund', url: '/return-policy', target: '_self', children: [] },
    { id: '3', menu_location: 'footer_service', title: 'Warranty Policy', url: '/warranty', target: '_self', children: [] },
    { id: '4', menu_location: 'footer_service', title: 'FAQs', url: '/faq', target: '_self', children: [] },
    { id: '5', menu_location: 'footer_service', title: 'Privacy Policy', url: '/privacy-policy', target: '_self', children: [] },
    { id: '6', menu_location: 'footer_service', title: 'Terms & Conditions', url: '/terms', target: '_self', children: [] },
  ];

  // Get social links from settings
  const socialLinks = {
    facebook: settings['social_facebook'] || '',
    twitter: settings['social_twitter'] || '',
    instagram: settings['social_instagram'] || '',
    youtube: settings['social_youtube'] || '',
    linkedin: settings['social_linkedin'] || '',
  };

  return (
    <footer className="bg-gray-900 text-gray-300">
      {/* Features Bar */}
      <div className="border-b border-gray-800">
        <div className="container mx-auto px-4 py-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {displayFeatureBars.map((feature) => {
              const IconComponent = getIconComponent(feature.icon);
              return (
                <div key={feature.id} className="flex items-center gap-3">
                  <div className="bg-primary/20 p-3 rounded-full">
                    <IconComponent className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold text-white">{feature.title}</p>
                    {feature.subtitle && <p className="text-sm">{feature.subtitle}</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Footer */}
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8">
          {/* Company Info */}
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-2 mb-4">
              {company?.logo_url ? (
                <img src={company.logo_url} alt={company.trade_name || company.name} className="h-10 w-auto" />
              ) : (
                <>
                  <div className="bg-primary rounded-full p-2">
                    <Droplets className="h-6 w-6 text-primary-foreground" />
                  </div>
                  <span className="font-bold text-xl text-white">
                    {company?.trade_name || company?.name || 'AQUAPURITE'}
                  </span>
                </>
              )}
            </Link>
            <p className="text-sm mb-6 leading-relaxed">
              {settings['footer_description'] || "India's trusted water purifier brand. We provide advanced water purification solutions for homes and offices with cutting-edge RO, UV, and UF technologies."}
            </p>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Phone className="h-4 w-4 text-primary" />
                <span>{settings['contact_phone'] || company?.phone || '1800-123-4567'} (Toll Free)</span>
              </div>
              <div className="flex items-center gap-3">
                <Mail className="h-4 w-4 text-primary" />
                <span>{settings['contact_email'] || company?.email || 'support@aquapurite.com'}</span>
              </div>
              <div className="flex items-start gap-3">
                <MapPin className="h-4 w-4 text-primary mt-1" />
                <span>
                  {settings['contact_address'] || company?.address || '123 Industrial Area, Sector 62'},
                  <br />
                  {company ? `${company.city}, ${company.state} - ${company.pincode}` : 'Noida, Uttar Pradesh - 201301'}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-white font-semibold mb-4">Quick Links</h3>
            <ul className="space-y-2">
              {displayQuickLinks.map((link) => (
                <li key={link.id}>
                  <Link
                    href={link.url}
                    target={link.target}
                    className="hover:text-primary transition-colors"
                  >
                    {link.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Customer Service */}
          <div>
            <h3 className="text-white font-semibold mb-4">Customer Service</h3>
            <ul className="space-y-2">
              {displayServiceLinks.map((link) => (
                <li key={link.id}>
                  <Link
                    href={link.url}
                    target={link.target}
                    className="hover:text-primary transition-colors"
                  >
                    {link.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Newsletter */}
          <div>
            <h3 className="text-white font-semibold mb-4">Stay Updated</h3>
            <p className="text-sm mb-4">
              {settings['newsletter_text'] || 'Subscribe to our newsletter for exclusive offers and updates.'}
            </p>
            <form className="space-y-3">
              <label htmlFor="newsletter-email" className="sr-only">Email address for newsletter</label>
              <Input
                id="newsletter-email"
                type="email"
                placeholder="Enter your email"
                className="bg-gray-800 border-gray-700 text-white placeholder:text-gray-500"
                aria-label="Email address for newsletter"
              />
              <Button type="submit" className="w-full">Subscribe</Button>
            </form>
            <div className="mt-6">
              <p className="text-sm mb-3">Follow Us</p>
              <div className="flex gap-3">
                {socialLinks.facebook && (
                  <a
                    href={socialLinks.facebook}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-gray-800 p-2 rounded-full hover:bg-primary transition-colors"
                    aria-label="Follow us on Facebook"
                  >
                    <Facebook className="h-5 w-5" />
                  </a>
                )}
                {socialLinks.twitter && (
                  <a
                    href={socialLinks.twitter}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-gray-800 p-2 rounded-full hover:bg-primary transition-colors"
                    aria-label="Follow us on Twitter"
                  >
                    <Twitter className="h-5 w-5" />
                  </a>
                )}
                {socialLinks.instagram && (
                  <a
                    href={socialLinks.instagram}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-gray-800 p-2 rounded-full hover:bg-primary transition-colors"
                    aria-label="Follow us on Instagram"
                  >
                    <Instagram className="h-5 w-5" />
                  </a>
                )}
                {socialLinks.youtube && (
                  <a
                    href={socialLinks.youtube}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-gray-800 p-2 rounded-full hover:bg-primary transition-colors"
                    aria-label="Subscribe on YouTube"
                  >
                    <Youtube className="h-5 w-5" />
                  </a>
                )}
                {socialLinks.linkedin && (
                  <a
                    href={socialLinks.linkedin}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-gray-800 p-2 rounded-full hover:bg-primary transition-colors"
                    aria-label="Connect on LinkedIn"
                  >
                    <Linkedin className="h-5 w-5" />
                  </a>
                )}
                {/* Fallback if no social links configured */}
                {!socialLinks.facebook && !socialLinks.twitter && !socialLinks.instagram && !socialLinks.youtube && (
                  <>
                    <a href="#" className="bg-gray-800 p-2 rounded-full hover:bg-primary transition-colors" aria-label="Follow us on Facebook">
                      <Facebook className="h-5 w-5" />
                    </a>
                    <a href="#" className="bg-gray-800 p-2 rounded-full hover:bg-primary transition-colors" aria-label="Follow us on Twitter">
                      <Twitter className="h-5 w-5" />
                    </a>
                    <a href="#" className="bg-gray-800 p-2 rounded-full hover:bg-primary transition-colors" aria-label="Follow us on Instagram">
                      <Instagram className="h-5 w-5" />
                    </a>
                    <a href="#" className="bg-gray-800 p-2 rounded-full hover:bg-primary transition-colors" aria-label="Subscribe on YouTube">
                      <Youtube className="h-5 w-5" />
                    </a>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="border-t border-gray-800">
        <div className="container mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm">
              {settings['footer_copyright'] || `© ${new Date().getFullYear()} ${company?.trade_name || company?.name || 'AQUAPURITE'}. All rights reserved.`}
            </p>
            <div className="flex items-center gap-4">
              <img
                src="https://razorpay.com/build/browser/static/razorpay-logo-new.svg"
                alt="Payment secured by Razorpay"
                width={80}
                height={24}
                className="h-6 w-auto opacity-50 hover:opacity-100 transition-opacity"
              />
              <img
                src="https://upload.wikimedia.org/wikipedia/commons/5/5e/Visa_Inc._logo.svg"
                alt="Visa accepted"
                width={50}
                height={16}
                className="h-4 w-auto opacity-50 hover:opacity-100 transition-opacity"
              />
              <img
                src="https://upload.wikimedia.org/wikipedia/commons/2/2a/Mastercard-logo.svg"
                alt="Mastercard accepted"
                width={40}
                height={24}
                className="h-6 w-auto opacity-50 hover:opacity-100 transition-opacity"
              />
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
