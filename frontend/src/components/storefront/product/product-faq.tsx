'use client';

import { useState } from 'react';
import {
  ChevronDown,
  HelpCircle,
  Droplets,
  Wrench,
  ShieldCheck,
  Truck,
  CreditCard,
  RotateCcw,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface FAQItem {
  question: string;
  answer: string;
  icon?: React.ReactNode;
  category: 'general' | 'installation' | 'warranty' | 'delivery' | 'payment' | 'returns';
}

const faqs: FAQItem[] = [
  // General Product Questions
  {
    category: 'general',
    icon: <Droplets className="h-4 w-4" />,
    question: 'What type of water purifier is best for my home?',
    answer: 'The best water purifier depends on your water source. If your TDS (Total Dissolved Solids) is above 500 ppm, an RO purifier is recommended. For TDS between 200-500 ppm, RO+UV works well. For municipal water with TDS below 200 ppm, a UV purifier is sufficient. You can check your water TDS using a TDS meter or contact us for a free water quality assessment.',
  },
  {
    category: 'general',
    icon: <Droplets className="h-4 w-4" />,
    question: 'How often should I change the filters?',
    answer: 'Filter replacement frequency depends on usage and water quality. Generally, sediment filters need replacement every 3-6 months, carbon filters every 6-12 months, and RO membranes every 12-24 months. Our purifiers have filter change indicators to alert you when it\'s time for replacement.',
  },
  {
    category: 'general',
    icon: <Droplets className="h-4 w-4" />,
    question: 'What is the difference between RO, UV, and UF purification?',
    answer: 'RO (Reverse Osmosis) removes dissolved impurities, heavy metals, and reduces TDS. UV (Ultraviolet) kills bacteria and viruses without removing dissolved solids. UF (Ultrafiltration) removes bacteria and cysts but not dissolved impurities. Most advanced purifiers combine these technologies for comprehensive purification.',
  },
  {
    category: 'general',
    icon: <Droplets className="h-4 w-4" />,
    question: 'Does the purifier waste water?',
    answer: 'RO purifiers typically produce some reject water (usually 2:1 ratio). However, our advanced models feature water-saving technology that reduces wastage by up to 50%. The reject water can be used for mopping, gardening, or other household purposes.',
  },
  // Installation Questions
  {
    category: 'installation',
    icon: <Wrench className="h-4 w-4" />,
    question: 'Is installation included with the purchase?',
    answer: 'Yes! Free professional installation is included with every water purifier purchase. Our trained technician will visit your home within 24-48 hours of delivery to install the purifier. Installation includes mounting, plumbing connections, and a demonstration of how to use the purifier.',
  },
  {
    category: 'installation',
    icon: <Wrench className="h-4 w-4" />,
    question: 'What do I need to prepare before installation?',
    answer: 'Please ensure: 1) A power socket near the installation location, 2) Water inlet source accessible within 3 feet, 3) Drain outlet for reject water, 4) Wall space of at least 18" x 18" for mounting. Our technician will assess the location and suggest the best setup.',
  },
  {
    category: 'installation',
    icon: <Wrench className="h-4 w-4" />,
    question: 'Can the purifier be installed in the kitchen cabinet?',
    answer: 'Yes, under-counter installation is possible for most models. Please check the product specifications for under-counter compatibility. Additional installation charges may apply for under-counter setup due to extra plumbing work required.',
  },
  // Warranty Questions
  {
    category: 'warranty',
    icon: <ShieldCheck className="h-4 w-4" />,
    question: 'What does the warranty cover?',
    answer: 'Our warranty covers manufacturing defects in the purifier body, electrical components, and membrane (for applicable models). It includes free repair or replacement of defective parts. Consumables like sediment filters and activated carbon are not covered under warranty.',
  },
  {
    category: 'warranty',
    icon: <ShieldCheck className="h-4 w-4" />,
    question: 'How do I claim warranty service?',
    answer: 'To claim warranty: 1) Keep your purchase invoice safe, 2) Register your product on our website or app, 3) Call our helpline 1800-123-4567 or raise a service request online, 4) Our technician will visit within 24-48 hours. Warranty is void if the product is serviced by unauthorized personnel.',
  },
  {
    category: 'warranty',
    icon: <ShieldCheck className="h-4 w-4" />,
    question: 'Can I extend my warranty?',
    answer: 'Yes! You can purchase an Annual Maintenance Contract (AMC) that extends your coverage and includes free service visits, filter replacements at discounted rates, and priority support. AMC plans can be purchased within 30 days of warranty expiry.',
  },
  // Delivery Questions
  {
    category: 'delivery',
    icon: <Truck className="h-4 w-4" />,
    question: 'How long does delivery take?',
    answer: 'Standard delivery takes 3-5 business days for metro cities and 5-7 business days for other locations. Express delivery (1-2 days) is available in select cities for an additional charge. You\'ll receive tracking information via SMS and email once your order is shipped.',
  },
  {
    category: 'delivery',
    icon: <Truck className="h-4 w-4" />,
    question: 'Do you deliver to my location?',
    answer: 'We deliver across India covering 500+ cities. Enter your pincode on the product page to check serviceability. For remote areas, delivery may take slightly longer. Installation services are available in most serviceable locations.',
  },
  // Payment Questions
  {
    category: 'payment',
    icon: <CreditCard className="h-4 w-4" />,
    question: 'What payment options are available?',
    answer: 'We accept: Credit/Debit Cards (Visa, Mastercard, Rupay), Net Banking, UPI (GPay, PhonePe, Paytm), Wallets, and Cash on Delivery. EMI options are available on credit cards for orders above Rs. 5,000.',
  },
  {
    category: 'payment',
    icon: <CreditCard className="h-4 w-4" />,
    question: 'Are there any EMI options available?',
    answer: 'Yes! We offer No-Cost EMI for 3-6 months on all major credit cards for purchases above Rs. 5,000. Standard EMI options up to 12 months are also available. EMI options are displayed at checkout based on your order value.',
  },
  // Returns Questions
  {
    category: 'returns',
    icon: <RotateCcw className="h-4 w-4" />,
    question: 'What is the return policy?',
    answer: 'We offer a 7-day return policy from the date of delivery. The product must be unused, in original packaging with all accessories. For installed products, returns are subject to inspection. A nominal restocking fee may apply. Refunds are processed within 5-7 business days.',
  },
  {
    category: 'returns',
    icon: <RotateCcw className="h-4 w-4" />,
    question: 'How do I initiate a return?',
    answer: 'To return a product: 1) Login to your account and go to Orders, 2) Select the order and click "Return", 3) Choose a reason for return, 4) Our team will arrange pickup within 2-3 business days. For assistance, contact our support team.',
  },
];

const categoryLabels = {
  general: 'Product Questions',
  installation: 'Installation',
  warranty: 'Warranty & Service',
  delivery: 'Delivery',
  payment: 'Payment',
  returns: 'Returns & Refunds',
};

const categoryIcons = {
  general: <Droplets className="h-4 w-4" />,
  installation: <Wrench className="h-4 w-4" />,
  warranty: <ShieldCheck className="h-4 w-4" />,
  delivery: <Truck className="h-4 w-4" />,
  payment: <CreditCard className="h-4 w-4" />,
  returns: <RotateCcw className="h-4 w-4" />,
};

interface ProductFAQProps {
  productName?: string;
  showAll?: boolean;
  maxItems?: number;
}

export default function ProductFAQ({ productName, showAll = false, maxItems = 8 }: ProductFAQProps) {
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set([0]));
  const [activeCategory, setActiveCategory] = useState<string>('all');

  const toggleItem = (index: number) => {
    setExpandedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const filteredFaqs = activeCategory === 'all'
    ? faqs
    : faqs.filter((faq) => faq.category === activeCategory);

  const displayedFaqs = showAll ? filteredFaqs : filteredFaqs.slice(0, maxItems);

  const categories = ['all', ...new Set(faqs.map((f) => f.category))];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <HelpCircle className="h-5 w-5 text-primary" />
        <h3 className="font-semibold text-lg">Frequently Asked Questions</h3>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2">
        {categories.map((category) => (
          <button
            key={category}
            onClick={() => setActiveCategory(category)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-colors',
              activeCategory === category
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted hover:bg-muted/80 text-muted-foreground'
            )}
          >
            {category !== 'all' && categoryIcons[category as keyof typeof categoryIcons]}
            <span className="capitalize">
              {category === 'all' ? 'All' : categoryLabels[category as keyof typeof categoryLabels]}
            </span>
          </button>
        ))}
      </div>

      {/* FAQ List */}
      <div className="space-y-3">
        {displayedFaqs.map((faq, index) => (
          <div
            key={index}
            className="border rounded-lg overflow-hidden"
          >
            <button
              onClick={() => toggleItem(index)}
              className="w-full text-left p-4 hover:bg-muted/50 transition-colors flex items-start justify-between gap-4"
            >
              <div className="flex items-start gap-3">
                <span className="mt-0.5 text-primary">{faq.icon}</span>
                <span className="font-medium">{faq.question}</span>
              </div>
              <ChevronDown
                className={cn(
                  'h-5 w-5 text-muted-foreground transition-transform flex-shrink-0',
                  expandedItems.has(index) && 'rotate-180'
                )}
              />
            </button>
            {expandedItems.has(index) && (
              <div className="px-4 pb-4 pl-12">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {faq.answer}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* View All Link */}
      {!showAll && filteredFaqs.length > maxItems && (
        <div className="text-center pt-4">
          <a
            href="/faq"
            className="text-primary hover:underline text-sm font-medium"
          >
            View all FAQs ({filteredFaqs.length - maxItems} more)
          </a>
        </div>
      )}

      {/* Contact CTA */}
      <div className="bg-muted/50 rounded-lg p-4 text-center">
        <p className="text-sm text-muted-foreground mb-2">
          Didn&apos;t find what you&apos;re looking for?
        </p>
        <div className="flex flex-col sm:flex-row gap-2 justify-center">
          <a
            href="https://wa.me/919311939076?text=Hi! I have a question about ILMS.AI water purifiers."
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-[#25D366] text-white rounded-lg hover:bg-[#20BD5A] transition-colors text-sm font-medium"
          >
            Chat on WhatsApp
          </a>
          <a
            href="tel:18001234567"
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium"
          >
            Call 1800-123-4567
          </a>
        </div>
      </div>
    </div>
  );
}
