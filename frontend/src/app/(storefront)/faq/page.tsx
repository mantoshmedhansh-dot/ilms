'use client';

import { useState, useMemo, useEffect } from 'react';
import Link from 'next/link';
import { ChevronDown, HelpCircle, Package, Truck, CreditCard, RotateCcw, Shield, Phone, Search, Wrench, Award, ChevronUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { contentApi, StorefrontFaqCategory, StorefrontFaqItem } from '@/lib/storefront/api';

// Icon map for rendering icons from API
const iconMap: Record<string, React.ReactNode> = {
  Package: <Package className="h-5 w-5" />,
  Truck: <Truck className="h-5 w-5" />,
  CreditCard: <CreditCard className="h-5 w-5" />,
  RotateCcw: <RotateCcw className="h-5 w-5" />,
  Wrench: <Wrench className="h-5 w-5" />,
  Award: <Award className="h-5 w-5" />,
  Phone: <Phone className="h-5 w-5" />,
  Shield: <Shield className="h-5 w-5" />,
  HelpCircle: <HelpCircle className="h-5 w-5" />,
};

function FAQAccordion({ item, isOpen, onToggle }: { item: StorefrontFaqItem; isOpen: boolean; onToggle: () => void }) {
  return (
    <div className="border-b last:border-b-0">
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full py-4 text-left hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded"
        aria-expanded={isOpen}
      >
        <span className="font-medium pr-4">{item.question}</span>
        <ChevronDown
          className={cn(
            'h-5 w-5 text-muted-foreground shrink-0 transition-transform duration-200',
            isOpen && 'rotate-180'
          )}
          aria-hidden="true"
        />
      </button>
      <div
        className={cn(
          'overflow-hidden transition-all duration-200',
          isOpen ? 'max-h-[500px] pb-4' : 'max-h-0'
        )}
        role="region"
        aria-hidden={!isOpen}
      >
        <p className="text-muted-foreground leading-relaxed">{item.answer}</p>
      </div>
    </div>
  );
}

// Fallback data for when API is empty or fails
const fallbackCategories: StorefrontFaqCategory[] = [
  {
    id: '1',
    name: 'Orders & Shopping',
    slug: 'orders-shopping',
    icon: 'Package',
    items: [
      {
        id: '1',
        question: 'How do I place an order on Aquapurite?',
        answer: 'Placing an order is simple: Browse our water purifiers and spare parts, add items to your cart, and proceed to checkout. You can pay using UPI, Credit/Debit cards, Net Banking, EMI options, or Cash on Delivery (COD) in select areas.',
        keywords: ['order', 'buy', 'purchase'],
      },
    ],
  },
  {
    id: '2',
    name: 'Shipping & Delivery',
    slug: 'shipping-delivery',
    icon: 'Truck',
    items: [
      {
        id: '2',
        question: 'What are the delivery charges?',
        answer: 'We offer FREE delivery on all water purifier orders across India. For spare parts, delivery is free on orders above Rs. 499.',
        keywords: ['delivery', 'shipping'],
      },
    ],
  },
];

export default function FAQPage() {
  const [categories, setCategories] = useState<StorefrontFaqCategory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [openItems, setOpenItems] = useState<Record<string, boolean>>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [expandAll, setExpandAll] = useState(false);

  // Fetch FAQ data from API
  useEffect(() => {
    const fetchFaq = async () => {
      try {
        const data = await contentApi.getFaq();
        if (data.categories && data.categories.length > 0) {
          setCategories(data.categories);
        } else {
          // Use fallback if no data from API
          setCategories(fallbackCategories);
        }
      } catch {
        // Use fallback on error
        setCategories(fallbackCategories);
      } finally {
        setIsLoading(false);
      }
    };
    fetchFaq();
  }, []);

  const toggleItem = (categoryIndex: number, itemIndex: number) => {
    const key = `${categoryIndex}-${itemIndex}`;
    setOpenItems((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleExpandAll = () => {
    if (expandAll) {
      setOpenItems({});
    } else {
      const allOpen: Record<string, boolean> = {};
      categories.forEach((cat, catIndex) => {
        cat.items.forEach((_, itemIndex) => {
          allOpen[`${catIndex}-${itemIndex}`] = true;
        });
      });
      setOpenItems(allOpen);
    }
    setExpandAll(!expandAll);
  };

  // Filter FAQs based on search query
  const filteredCategories = useMemo(() => {
    if (!searchQuery.trim()) return categories;

    const query = searchQuery.toLowerCase();
    return categories
      .map((category) => ({
        ...category,
        items: category.items.filter(
          (item) =>
            item.question.toLowerCase().includes(query) ||
            item.answer.toLowerCase().includes(query) ||
            item.keywords?.some((kw) => kw.toLowerCase().includes(query))
        ),
      }))
      .filter((category) => category.items.length > 0);
  }, [searchQuery, categories]);

  const totalFAQs = categories.reduce((sum, cat) => sum + cat.items.length, 0);
  const filteredFAQs = filteredCategories.reduce((sum, cat) => sum + cat.items.length, 0);

  const getIconForCategory = (iconName: string) => {
    return iconMap[iconName] || <HelpCircle className="h-5 w-5" />;
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-full mb-4 animate-pulse">
            <HelpCircle className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-2xl font-bold mb-2">Loading FAQs...</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-full mb-4">
          <HelpCircle className="h-8 w-8 text-primary" />
        </div>
        <h1 className="text-3xl md:text-4xl font-bold mb-4" style={{ textWrap: 'balance' } as React.CSSProperties}>
          Frequently Asked Questions
        </h1>
        <p className="text-muted-foreground max-w-2xl mx-auto mb-6">
          Find instant answers to common questions about Aquapurite water purifiers, orders, installation, warranty, and more.
          Can&apos;t find what you&apos;re looking for?{' '}
          <Link href="/contact" className="text-primary hover:underline font-medium">
            Contact our support team
          </Link>
        </p>

        {/* Search Bar */}
        <div className="max-w-xl mx-auto relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search FAQs... (e.g., 'warranty', 'installation', 'EMI')"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-12 text-base"
            aria-label="Search frequently asked questions"
          />
        </div>

        {/* Search Results Info & Expand/Collapse */}
        <div className="flex items-center justify-center gap-4 mt-4">
          {searchQuery && (
            <p className="text-sm text-muted-foreground">
              Showing {filteredFAQs} of {totalFAQs} questions
            </p>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleExpandAll}
            className="text-sm"
          >
            {expandAll ? (
              <>
                <ChevronUp className="h-4 w-4 mr-1" />
                Collapse All
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4 mr-1" />
                Expand All
              </>
            )}
          </Button>
        </div>
      </div>

      {/* FAQ Categories */}
      {filteredCategories.length > 0 ? (
        <div className="grid gap-6 md:grid-cols-2 max-w-5xl mx-auto">
          {filteredCategories.map((category, categoryIndex) => {
            const originalCategoryIndex = categories.findIndex(c => c.id === category.id);
            return (
              <Card key={category.id} className="overflow-hidden">
                <CardHeader className="bg-muted/30">
                  <CardTitle className="flex items-center gap-2">
                    <span className="p-2 bg-primary/10 rounded-lg text-primary">
                      {getIconForCategory(category.icon)}
                    </span>
                    {category.name}
                    <span className="ml-auto text-sm font-normal text-muted-foreground">
                      {category.items.length} {category.items.length === 1 ? 'question' : 'questions'}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                  <div className="divide-y">
                    {category.items.map((item, itemIndex) => {
                      const originalItemIndex = categories[originalCategoryIndex]?.items.findIndex(
                        i => i.id === item.id
                      ) ?? itemIndex;
                      return (
                        <FAQAccordion
                          key={item.id}
                          item={item}
                          isOpen={openItems[`${originalCategoryIndex}-${originalItemIndex}`] || false}
                          onToggle={() => toggleItem(originalCategoryIndex, originalItemIndex)}
                        />
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-lg text-muted-foreground mb-4">
            No FAQs found for &quot;{searchQuery}&quot;
          </p>
          <p className="text-sm text-muted-foreground mb-6">
            Try different keywords or browse all categories
          </p>
          <Button variant="outline" onClick={() => setSearchQuery('')}>
            Clear Search
          </Button>
        </div>
      )}

      {/* Contact CTA */}
      <div className="text-center mt-12 p-8 bg-gradient-to-br from-primary/5 to-primary/10 rounded-2xl max-w-2xl mx-auto border border-primary/10">
        <h2 className="text-xl font-semibold mb-2">Still have questions?</h2>
        <p className="text-muted-foreground mb-6">
          Our expert support team is ready to help you with any questions about water purifiers, orders, or service.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/contact"
            className="inline-flex items-center justify-center px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium shadow-sm"
          >
            Contact Support
          </Link>
          <a
            href="tel:18001234567"
            className="inline-flex items-center justify-center px-6 py-3 border-2 border-primary/20 rounded-lg hover:bg-primary/5 transition-colors font-medium"
          >
            <Phone className="h-4 w-4 mr-2" />
            1800-123-4567
          </a>
        </div>
        <p className="text-xs text-muted-foreground mt-4">
          Available Mon-Sat, 9 AM - 7 PM IST | Sunday 10 AM - 4 PM
        </p>
      </div>
    </div>
  );
}
