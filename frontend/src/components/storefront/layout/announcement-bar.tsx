'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { X, Info, AlertTriangle, Tag, CheckCircle } from 'lucide-react';
import { contentApi, StorefrontAnnouncement } from '@/lib/storefront/api';
import { cn } from '@/lib/utils';

const typeIcons = {
  INFO: Info,
  WARNING: AlertTriangle,
  PROMO: Tag,
  SUCCESS: CheckCircle,
};

const typeStyles = {
  INFO: 'bg-blue-600 text-white',
  WARNING: 'bg-amber-500 text-white',
  PROMO: 'bg-purple-600 text-white',
  SUCCESS: 'bg-green-600 text-white',
};

export default function AnnouncementBar() {
  const [announcement, setAnnouncement] = useState<StorefrontAnnouncement | null>(null);
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    // Check if dismissed in this session
    const dismissed = sessionStorage.getItem('announcement_dismissed');
    if (dismissed) {
      setIsDismissed(true);
      return;
    }

    const fetchAnnouncement = async () => {
      try {
        const data = await contentApi.getActiveAnnouncement();
        setAnnouncement(data);
      } catch {
        // Silently fail - no announcement is fine
      }
    };
    fetchAnnouncement();
  }, []);

  const handleDismiss = () => {
    setIsDismissed(true);
    if (announcement?.is_dismissible) {
      sessionStorage.setItem('announcement_dismissed', announcement.id);
    }
  };

  if (!announcement || isDismissed) {
    return null;
  }

  const Icon = typeIcons[announcement.announcement_type] || Info;
  const defaultStyle = typeStyles[announcement.announcement_type] || typeStyles.INFO;

  // Use custom colors if provided, otherwise use type-based defaults
  const customStyle = announcement.background_color || announcement.text_color
    ? {
        backgroundColor: announcement.background_color || undefined,
        color: announcement.text_color || undefined,
      }
    : undefined;

  return (
    <div
      className={cn(
        'relative py-2 px-4 text-center text-sm',
        !customStyle && defaultStyle
      )}
      style={customStyle}
    >
      <div className="container mx-auto flex items-center justify-center gap-2">
        <Icon className="h-4 w-4 flex-shrink-0" />
        <span>{announcement.text}</span>
        {announcement.link_url && announcement.link_text && (
          <Link
            href={announcement.link_url}
            className="underline font-semibold hover:no-underline ml-1"
          >
            {announcement.link_text}
          </Link>
        )}
      </div>
      {announcement.is_dismissible && (
        <button
          onClick={handleDismiss}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:opacity-70 transition-opacity"
          aria-label="Dismiss announcement"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
