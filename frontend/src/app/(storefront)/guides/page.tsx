'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Play,
  PlayCircle,
  Clock,
  Search,
  ChevronRight,
  BookOpen,
  Wrench,
  Settings,
  HelpCircle,
  Youtube,
  ThumbsUp,
  Eye,
  Star,
  Shield,
  Phone,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { guidesApi } from '@/lib/storefront/api';

interface VideoGuide {
  id: string;
  title: string;
  slug: string;
  description: string;
  category: string;
  duration_seconds?: number;
  thumbnail_url: string;
  video_url: string;
  video_type: string;
  video_id?: string;
  view_count: number;
  is_featured: boolean;
}

// Fallback data in case API fails
const fallbackGuides: VideoGuide[] = [
  {
    id: '1',
    title: 'RO Water Purifier Installation Guide',
    slug: 'ro-installation-guide',
    description: 'Step-by-step guide to install your ILMS.AI RO water purifier.',
    category: 'INSTALLATION',
    duration_seconds: 720,
    thumbnail_url: 'https://images.unsplash.com/photo-1585351650024-3a6d61c1e3f5?w=800&q=80',
    video_url: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
    video_type: 'YOUTUBE',
    video_id: 'dQw4w9WgXcQ',
    view_count: 45000,
    is_featured: true,
  },
  {
    id: '2',
    title: 'How to Change RO Membrane',
    slug: 'change-ro-membrane',
    description: 'Learn how to replace the RO membrane in your water purifier.',
    category: 'MAINTENANCE',
    duration_seconds: 510,
    thumbnail_url: 'https://images.unsplash.com/photo-1581244277943-fe4a9c777189?w=800&q=80',
    video_url: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
    video_type: 'YOUTUBE',
    video_id: 'dQw4w9WgXcQ',
    view_count: 32000,
    is_featured: true,
  },
  {
    id: '3',
    title: 'Troubleshooting Common Problems',
    slug: 'troubleshooting-guide',
    description: 'Fix common RO purifier issues: no water flow, bad taste, leakage.',
    category: 'TROUBLESHOOTING',
    duration_seconds: 920,
    thumbnail_url: 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=800&q=80',
    video_url: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
    video_type: 'YOUTUBE',
    video_id: 'dQw4w9WgXcQ',
    view_count: 67000,
    is_featured: true,
  },
];

const categoryInfo: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  INSTALLATION: {
    label: 'Installation',
    icon: Settings,
    color: 'bg-blue-100 text-blue-800',
  },
  MAINTENANCE: {
    label: 'Maintenance',
    icon: Wrench,
    color: 'bg-green-100 text-green-800',
  },
  TROUBLESHOOTING: {
    label: 'Troubleshooting',
    icon: HelpCircle,
    color: 'bg-orange-100 text-orange-800',
  },
  PRODUCT_TOUR: {
    label: 'Product Tour',
    icon: Play,
    color: 'bg-cyan-100 text-cyan-800',
  },
  HOW_TO: {
    label: 'How To',
    icon: BookOpen,
    color: 'bg-indigo-100 text-indigo-800',
  },
  TIPS: {
    label: 'Tips & Guides',
    icon: BookOpen,
    color: 'bg-purple-100 text-purple-800',
  },
};

function formatDuration(seconds?: number): string {
  if (!seconds) return '--:--';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatViews(views: number): string {
  if (views >= 1000000) {
    return `${(views / 1000000).toFixed(1)}M`;
  }
  if (views >= 1000) {
    return `${(views / 1000).toFixed(1)}K`;
  }
  return views.toString();
}

function getEmbedUrl(video: VideoGuide): string {
  if (video.video_type === 'YOUTUBE' && video.video_id) {
    return `https://www.youtube.com/embed/${video.video_id}`;
  }
  if (video.video_type === 'VIMEO' && video.video_id) {
    return `https://player.vimeo.com/video/${video.video_id}`;
  }
  return video.video_url;
}

function VideoCard({
  video,
  onPlay,
}: {
  video: VideoGuide;
  onPlay: () => void;
}) {
  const category = categoryInfo[video.category] || categoryInfo.HOW_TO;
  const CategoryIcon = category.icon;

  return (
    <Card className="overflow-hidden group cursor-pointer hover:shadow-lg transition-shadow" onClick={onPlay}>
      <div className="relative aspect-video bg-muted overflow-hidden">
        {video.thumbnail_url ? (
          <img
            src={video.thumbnail_url}
            alt={video.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-primary/5" />
        )}
        <div className="absolute inset-0 bg-black/30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="w-16 h-16 rounded-full bg-white/90 flex items-center justify-center">
            <Play className="h-8 w-8 text-primary ml-1" />
          </div>
        </div>
        <Badge className="absolute bottom-2 right-2 bg-black/80 text-white border-0">
          <Clock className="h-3 w-3 mr-1" />
          {formatDuration(video.duration_seconds)}
        </Badge>
        {video.is_featured && (
          <Badge className="absolute top-2 left-2 bg-primary border-0">
            <Star className="h-3 w-3 mr-1 fill-current" />
            Featured
          </Badge>
        )}
      </div>
      <CardContent className="p-4">
        <Badge variant="secondary" className={cn('mb-2', category.color)}>
          <CategoryIcon className="h-3 w-3 mr-1" />
          {category.label}
        </Badge>
        <h3 className="font-semibold line-clamp-2 mb-2 group-hover:text-primary transition-colors">
          {video.title}
        </h3>
        <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
          {video.description}
        </p>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Eye className="h-3.5 w-3.5" />
            {formatViews(video.view_count)} views
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function GuidesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedVideo, setSelectedVideo] = useState<VideoGuide | null>(null);
  const [guides, setGuides] = useState<VideoGuide[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);

  // Fetch guides from API
  useEffect(() => {
    const fetchGuides = async () => {
      setIsLoading(true);
      try {
        const data = await guidesApi.getGuides();
        if (data && data.length > 0) {
          // Map API response to our interface
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const mappedGuides: VideoGuide[] = data.map((item: any) => ({
            id: item.id,
            title: item.title,
            slug: item.slug || '',
            description: item.description || '',
            category: (item.category || 'HOW_TO').toUpperCase(),
            duration_seconds: item.duration_seconds,
            thumbnail_url: item.thumbnail_url || item.thumbnail || '',
            video_url: item.video_url || '',
            video_type: item.video_type || 'YOUTUBE',
            video_id: item.video_id || item.youtube_id || '',
            view_count: item.view_count || item.views || 0,
            is_featured: item.is_featured || false,
          }));
          setGuides(mappedGuides);

          // Extract unique categories
          const cats = [...new Set(mappedGuides.map(g => g.category))].filter(Boolean);
          setAvailableCategories(cats);
        } else {
          setGuides(fallbackGuides);
          setAvailableCategories(['INSTALLATION', 'MAINTENANCE', 'TROUBLESHOOTING']);
        }
      } catch {
        console.error('Failed to fetch guides, using fallback');
        setGuides(fallbackGuides);
        setAvailableCategories(['INSTALLATION', 'MAINTENANCE', 'TROUBLESHOOTING']);
      } finally {
        setIsLoading(false);
      }
    };
    fetchGuides();
  }, []);

  // Filter videos based on search and category
  const filteredVideos = guides.filter((video) => {
    const matchesSearch =
      video.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      video.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      activeCategory === 'all' || video.category === activeCategory;
    return matchesSearch && matchesCategory;
  });

  // Get featured videos
  const featuredVideos = guides.filter((v) => v.is_featured);

  // Calculate stats
  const totalViews = guides.reduce((sum, g) => sum + g.view_count, 0);

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium mb-4">
          <PlayCircle className="h-4 w-4" />
          Video Learning Center
        </div>
        <h1 className="text-3xl md:text-4xl font-bold mb-4">
          Water Purifier Guides & Tutorials
        </h1>
        <p className="text-muted-foreground max-w-2xl mx-auto mb-6">
          Learn how to install, maintain, and troubleshoot your ILMS.AI water purifier with our comprehensive video guides. From basic setup to advanced maintenance - we&apos;ve got you covered!
        </p>

        {/* Quick Stats */}
        <div className="flex flex-wrap justify-center gap-6">
          <div className="flex items-center gap-2 text-sm">
            <PlayCircle className="h-4 w-4 text-primary" />
            <span><strong>{guides.length}</strong> Video Guides</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Eye className="h-4 w-4 text-primary" />
            <span><strong>{formatViews(totalViews)}</strong> Views</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <ThumbsUp className="h-4 w-4 text-primary" />
            <span><strong>4.8★</strong> Average Rating</span>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="max-w-xl mx-auto mb-8">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search video guides..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Loading State */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading video guides...</p>
        </div>
      ) : (
        <>
          {/* Featured Videos */}
          {!searchQuery && activeCategory === 'all' && featuredVideos.length > 0 && (
            <section className="mb-12">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Play className="h-5 w-5 text-primary" />
                Featured Videos
              </h2>
              <div className="grid md:grid-cols-3 gap-6">
                {featuredVideos.slice(0, 3).map((video) => (
                  <VideoCard
                    key={video.id}
                    video={video}
                    onPlay={() => setSelectedVideo(video)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Category Tabs */}
          <Tabs value={activeCategory} onValueChange={setActiveCategory} className="mb-8">
            <TabsList className="w-full justify-start flex-wrap h-auto gap-2 bg-transparent">
              <TabsTrigger
                value="all"
                className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
              >
                All Videos
              </TabsTrigger>
              {availableCategories.map((cat) => {
                const info = categoryInfo[cat] || categoryInfo.HOW_TO;
                const Icon = info.icon;
                return (
                  <TabsTrigger
                    key={cat}
                    value={cat}
                    className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {info.label}
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </Tabs>

          {/* Video Grid */}
          {filteredVideos.length > 0 ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredVideos.map((video) => (
                <VideoCard
                  key={video.id}
                  video={video}
                  onPlay={() => setSelectedVideo(video)}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <PlayCircle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No videos found</h3>
              <p className="text-muted-foreground">
                Try adjusting your search or browse all categories.
              </p>
            </div>
          )}
        </>
      )}

      {/* Video Player Dialog */}
      <Dialog open={!!selectedVideo} onOpenChange={() => setSelectedVideo(null)}>
        <DialogContent className="sm:max-w-[800px] p-0">
          {selectedVideo && (
            <>
              <div className="aspect-video">
                <iframe
                  src={`${getEmbedUrl(selectedVideo)}?autoplay=1`}
                  title={selectedVideo.title}
                  className="w-full h-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
              <div className="p-4">
                <Badge
                  variant="secondary"
                  className={cn('mb-2', (categoryInfo[selectedVideo.category] || categoryInfo.HOW_TO).color)}
                >
                  {(categoryInfo[selectedVideo.category] || categoryInfo.HOW_TO).label}
                </Badge>
                <h3 className="text-lg font-semibold mb-2">{selectedVideo.title}</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  {selectedVideo.description}
                </p>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Eye className="h-4 w-4" />
                      {formatViews(selectedVideo.view_count)} views
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      {formatDuration(selectedVideo.duration_seconds)}
                    </span>
                  </div>
                  {selectedVideo.video_type === 'YOUTUBE' && selectedVideo.video_id && (
                    <Button variant="outline" size="sm" asChild>
                      <a
                        href={`https://www.youtube.com/watch?v=${selectedVideo.video_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Youtube className="h-4 w-4 mr-2" />
                        Watch on YouTube
                      </a>
                    </Button>
                  )}
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Maintenance Schedule Guide */}
      <Card className="mt-12">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wrench className="h-5 w-5 text-primary" />
            Recommended Maintenance Schedule
          </CardTitle>
          <CardDescription>
            Follow this schedule to keep your water purifier in optimal condition
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
              <p className="text-sm font-medium text-blue-900 mb-1">Every 3-6 Months</p>
              <p className="text-xs text-blue-700">Replace Sediment & Carbon Filters</p>
            </div>
            <div className="p-4 rounded-lg bg-green-50 border border-green-200">
              <p className="text-sm font-medium text-green-900 mb-1">Every 12 Months</p>
              <p className="text-xs text-green-700">Replace UV Lamp (if applicable)</p>
            </div>
            <div className="p-4 rounded-lg bg-orange-50 border border-orange-200">
              <p className="text-sm font-medium text-orange-900 mb-1">Every 18-24 Months</p>
              <p className="text-xs text-orange-700">Replace RO Membrane</p>
            </div>
            <div className="p-4 rounded-lg bg-purple-50 border border-purple-200">
              <p className="text-sm font-medium text-purple-900 mb-1">Monthly</p>
              <p className="text-xs text-purple-700">Clean Storage Tank</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* YouTube Channel CTA */}
      <Card className="mt-8 bg-gradient-to-r from-red-50 to-red-100 border-red-200">
        <CardContent className="py-8">
          <div className="flex flex-col md:flex-row items-center gap-6 text-center md:text-left">
            <div className="p-4 bg-red-500 rounded-full">
              <Youtube className="h-8 w-8 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-semibold text-red-900 mb-2">
                Subscribe to Our YouTube Channel
              </h3>
              <p className="text-red-700">
                Get notified about new installation guides, maintenance tips, and product reviews. Join 25,000+ subscribers!
              </p>
            </div>
            <Button className="bg-red-600 hover:bg-red-700" asChild>
              <a
                href="https://www.youtube.com/@ilms"
                target="_blank"
                rel="noopener noreferrer"
              >
                Subscribe Now
                <ChevronRight className="h-4 w-4 ml-2" />
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Quick Contact Options */}
      <div className="mt-8 grid sm:grid-cols-2 gap-4">
        {/* WhatsApp Support */}
        <Card className="bg-green-50 border-green-200">
          <CardContent className="py-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-500 rounded-full">
                <Phone className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-green-900">Need Immediate Help?</h3>
                <p className="text-sm text-green-700">Chat with our support team on WhatsApp</p>
              </div>
              <Button variant="outline" className="border-green-300 text-green-700 hover:bg-green-100" asChild>
                <a
                  href="https://wa.me/919311939076?text=I need help with my water purifier"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Chat Now
                </a>
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Book Service */}
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="py-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-primary rounded-full">
                <Shield className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold">Professional Service Needed?</h3>
                <p className="text-sm text-muted-foreground">Book a technician visit at your convenience</p>
              </div>
              <Button asChild>
                <Link href="/account/services">Book Service</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* FAQ Link */}
      <Card className="mt-8">
        <CardContent className="py-6">
          <div className="flex flex-col md:flex-row items-center gap-4 text-center md:text-left">
            <div className="p-3 bg-primary/10 rounded-full">
              <HelpCircle className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold">Have More Questions?</h3>
              <p className="text-sm text-muted-foreground">
                Browse our comprehensive FAQ section for answers to common questions about products, orders, and services.
              </p>
            </div>
            <Button variant="outline" asChild>
              <Link href="/faq">View All FAQs</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
