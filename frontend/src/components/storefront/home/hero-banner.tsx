'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { ChevronLeft, ChevronRight, Pause, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { contentApi, StorefrontBanner } from '@/lib/storefront/api';

// Fallback banners for when API fails or returns empty
// High-quality water/clean living themed images from Unsplash
const fallbackBanners: StorefrontBanner[] = [
  {
    id: '1',
    title: 'Pure Water, Healthy Life',
    subtitle: 'Advanced 7-Stage RO Purification with Mineral Enrichment for Your Family',
    image_url: 'https://images.unsplash.com/photo-1564419320461-6870880221ad?q=80&w=2070&auto=format&fit=crop',
    cta_text: 'Shop Now',
    cta_link: '/products',
    text_position: 'left',
    text_color: 'white',
  },
  {
    id: '2',
    title: 'Smart Water Purifiers',
    subtitle: 'IoT-enabled purifiers with real-time water quality monitoring',
    image_url: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?q=80&w=2070&auto=format&fit=crop',
    cta_text: 'Explore New Arrivals',
    cta_link: '/products?is_new_arrival=true',
    text_position: 'left',
    text_color: 'white',
  },
  {
    id: '3',
    title: 'Free Expert Installation',
    subtitle: 'Professional setup by certified technicians within 48 hours of delivery',
    image_url: 'https://images.unsplash.com/photo-1544027993-37dbfe43562a?q=80&w=2070&auto=format&fit=crop',
    cta_text: 'Learn More',
    cta_link: '/products',
    text_position: 'left',
    text_color: 'white',
  },
  {
    id: '4',
    title: 'Bestselling Purifiers',
    subtitle: 'Trusted by 50,000+ happy families across India',
    image_url: 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?q=80&w=2070&auto=format&fit=crop',
    cta_text: 'View Bestsellers',
    cta_link: '/products?is_bestseller=true',
    text_position: 'left',
    text_color: 'white',
  },
];

export default function HeroBanner() {
  const [banners, setBanners] = useState<StorefrontBanner[]>(fallbackBanners);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const containerRef = useRef<HTMLElement>(null);

  // Fetch banners from API
  useEffect(() => {
    const fetchBanners = async () => {
      try {
        const data = await contentApi.getBanners();
        if (data && data.length > 0) {
          setBanners(data);
        }
      } catch {
        // Keep fallback banners on error
      } finally {
        setIsLoading(false);
      }
    };
    fetchBanners();
  }, []);

  // Auto-advance carousel (pause on hover or when manually paused)
  useEffect(() => {
    if (banners.length <= 1 || isPaused || isHovered) return;
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % banners.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [banners.length, isPaused, isHovered]);

  const goToSlide = useCallback((index: number) => {
    setCurrentSlide(index);
  }, []);

  const goToPrev = useCallback(() => {
    setCurrentSlide((prev) => (prev - 1 + banners.length) % banners.length);
  }, [banners.length]);

  const goToNext = useCallback(() => {
    setCurrentSlide((prev) => (prev + 1) % banners.length);
  }, [banners.length]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!containerRef.current?.contains(document.activeElement)) return;

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          goToPrev();
          break;
        case 'ArrowRight':
          e.preventDefault();
          goToNext();
          break;
        case ' ':
          e.preventDefault();
          setIsPaused((prev) => !prev);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goToPrev, goToNext]);

  const getTextAlignment = (position: string) => {
    switch (position) {
      case 'center':
        return 'items-center text-center';
      case 'right':
        return 'items-end text-right';
      default:
        return 'items-start text-left';
    }
  };

  const getTextColorClass = (color: string) => {
    return color === 'dark' ? 'text-gray-900' : 'text-white';
  };

  const getGradientClass = (position: string, color: string) => {
    const isDark = color === 'dark';
    const baseColor = isDark ? 'white' : 'black';
    switch (position) {
      case 'center':
        return `bg-gradient-to-b from-${baseColor}/60 via-${baseColor}/40 to-${baseColor}/60`;
      case 'right':
        return `bg-gradient-to-l from-${baseColor}/70 via-${baseColor}/50 to-transparent`;
      default:
        return `bg-gradient-to-r from-${baseColor}/70 via-${baseColor}/50 to-transparent`;
    }
  };

  return (
    <section
      ref={containerRef}
      className="relative w-full h-[400px] md:h-[500px] lg:h-[600px] overflow-hidden"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      role="region"
      aria-roledescription="carousel"
      aria-label="Featured promotions"
      tabIndex={0}
    >
      {/* Live region for screen readers */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        Slide {currentSlide + 1} of {banners.length}: {banners[currentSlide]?.title}
      </div>

      {/* Slides */}
      {banners.map((banner, index) => (
        <div
          key={banner.id}
          role="group"
          aria-roledescription="slide"
          aria-label={`Slide ${index + 1} of ${banners.length}: ${banner.title}`}
          aria-hidden={index !== currentSlide}
          className={`absolute inset-0 transition-opacity duration-1000 ${
            index === currentSlide ? 'opacity-100' : 'opacity-0 pointer-events-none'
          }`}
        >
          {/* Background Image - Using Next.js Image for better performance */}
          <div className="absolute inset-0">
            <Image
              src={banner.image_url}
              alt=""
              fill
              priority={index === 0}
              className="object-cover"
              sizes="100vw"
            />
            <div className={`absolute inset-0 ${
              banner.text_color === 'dark'
                ? 'bg-gradient-to-r from-white/80 via-white/60 to-transparent'
                : 'bg-gradient-to-r from-black/70 via-black/50 to-transparent'
            }`} />
          </div>

          {/* Content */}
          <div className={`relative h-full container mx-auto px-4 flex ${getTextAlignment(banner.text_position)}`}>
            <div className={`max-w-xl ${getTextColorClass(banner.text_color)} flex flex-col justify-center h-full py-12`}>
              <h2
                className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4 animate-fadeInUp"
                style={{ textWrap: 'balance', textShadow: banner.text_color === 'white' ? '0 2px 4px rgba(0,0,0,0.3)' : 'none' } as React.CSSProperties}
              >
                {banner.title}
              </h2>
              {banner.subtitle && (
                <p
                  className={`text-lg md:text-xl mb-6 animate-fadeInUp animation-delay-200 ${
                    banner.text_color === 'dark' ? 'text-gray-700' : 'text-gray-200'
                  }`}
                  style={{ textShadow: banner.text_color === 'white' ? '0 1px 2px rgba(0,0,0,0.2)' : 'none' }}
                >
                  {banner.subtitle}
                </p>
              )}
              {banner.cta_text && banner.cta_link && (
                <div>
                  <Button
                    size="lg"
                    className="animate-fadeInUp animation-delay-400 shadow-lg hover:shadow-xl transition-shadow"
                    asChild
                  >
                    <Link href={banner.cta_link}>{banner.cta_text}</Link>
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}

      {/* Navigation Arrows */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute left-4 top-1/2 -translate-y-1/2 h-12 w-12 rounded-full bg-white/20 hover:bg-white/40 text-white backdrop-blur-sm focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-transparent"
        onClick={goToPrev}
        aria-label="Previous slide"
      >
        <ChevronLeft className="h-6 w-6" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="absolute right-4 top-1/2 -translate-y-1/2 h-12 w-12 rounded-full bg-white/20 hover:bg-white/40 text-white backdrop-blur-sm focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-transparent"
        onClick={goToNext}
        aria-label="Next slide"
      >
        <ChevronRight className="h-6 w-6" />
      </Button>

      {/* Pause/Play Button */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute bottom-6 right-4 h-8 w-8 rounded-full bg-white/20 hover:bg-white/40 text-white backdrop-blur-sm focus-visible:ring-2 focus-visible:ring-white"
        onClick={() => setIsPaused((prev) => !prev)}
        aria-label={isPaused ? 'Play slideshow' : 'Pause slideshow'}
      >
        {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
      </Button>

      {/* Dots */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-2" role="tablist" aria-label="Slide navigation">
        {banners.map((banner, index) => (
          <button
            key={index}
            role="tab"
            aria-selected={index === currentSlide}
            aria-label={`Go to slide ${index + 1}: ${banner.title}`}
            className={`h-2 rounded-full transition-all focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-black/50 ${
              index === currentSlide
                ? 'w-8 bg-white'
                : 'w-2 bg-white/50 hover:bg-white/75'
            }`}
            onClick={() => goToSlide(index)}
          />
        ))}
      </div>
    </section>
  );
}
