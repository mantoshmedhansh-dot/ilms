'use client';

import { useState, useEffect } from 'react';
import { Star, Quote } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { contentApi, StorefrontTestimonial } from '@/lib/storefront/api';

// Fallback testimonials for when API fails or returns empty
const fallbackTestimonials: StorefrontTestimonial[] = [
  {
    id: '1',
    customer_name: 'Rajesh Kumar',
    customer_location: 'Delhi',
    rating: 5,
    content:
      'Excellent water purifier! The water tastes so pure and fresh. Installation was quick and the service team was very professional.',
    product_name: 'Aqua Pro 7-Stage RO',
  },
  {
    id: '2',
    customer_name: 'Priya Sharma',
    customer_location: 'Mumbai',
    rating: 5,
    content:
      "Best investment for my family's health. The mineral enrichment feature makes the water taste great. Highly recommended!",
    product_name: 'Aqua Elite UV+RO',
  },
  {
    id: '3',
    customer_name: 'Amit Patel',
    customer_location: 'Ahmedabad',
    rating: 4,
    content:
      'Great product with excellent after-sales service. The AMC plan is worth it for hassle-free maintenance.',
    product_name: 'Aqua Smart RO',
  },
  {
    id: '4',
    customer_name: 'Sunita Verma',
    customer_location: 'Bangalore',
    rating: 5,
    content:
      'Very happy with my purchase. The smart features like filter change indicator are very useful. Delivery was on time.',
    product_name: 'Aqua Pro Max',
  },
];

export default function Testimonials() {
  const [testimonials, setTestimonials] = useState<StorefrontTestimonial[]>(fallbackTestimonials);

  useEffect(() => {
    const fetchTestimonials = async () => {
      try {
        const data = await contentApi.getTestimonials();
        if (data && data.length > 0) {
          setTestimonials(data);
        }
      } catch {
        // Keep fallback testimonials on error
      }
    };
    fetchTestimonials();
  }, []);
  return (
    <section className="py-12 md:py-16 bg-muted/50">
      <div className="container mx-auto px-4">
        <div className="text-center mb-10">
          <h2 className="text-2xl md:text-3xl font-bold mb-2">
            What Our Customers Say
          </h2>
          <p className="text-muted-foreground">
            Join thousands of happy families across India
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {testimonials.map((testimonial) => (
            <Card key={testimonial.id} className="relative">
              <CardContent className="p-6">
                <Quote className="h-8 w-8 text-primary/20 absolute top-4 right-4" />

                {/* Rating */}
                <div className="flex items-center gap-1 mb-4">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star
                      key={i}
                      className={`h-4 w-4 ${
                        i < testimonial.rating
                          ? 'text-yellow-500 fill-yellow-500'
                          : 'text-gray-300'
                      }`}
                    />
                  ))}
                </div>

                {/* Title */}
                {testimonial.title && (
                  <p className="font-semibold text-sm mb-2">{testimonial.title}</p>
                )}

                {/* Content */}
                <p className="text-sm text-muted-foreground mb-4 line-clamp-4">
                  &ldquo;{testimonial.content}&rdquo;
                </p>

                {/* Product */}
                {testimonial.product_name && (
                  <p className="text-xs text-primary font-medium mb-4">
                    {testimonial.product_name}
                  </p>
                )}

                {/* Author */}
                <div className="flex items-center gap-3">
                  <Avatar className="h-10 w-10">
                    <AvatarImage src={testimonial.customer_avatar_url || undefined} />
                    <AvatarFallback className="bg-primary/10 text-primary">
                      {testimonial.customer_name
                        .split(' ')
                        .map((n) => n[0])
                        .join('')}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="font-medium text-sm">{testimonial.customer_name}</p>
                    {(testimonial.customer_designation || testimonial.customer_location) && (
                      <p className="text-xs text-muted-foreground">
                        {testimonial.customer_designation}
                        {testimonial.customer_designation && testimonial.customer_location && ', '}
                        {testimonial.customer_location}
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
