/**
 * CMS API Client
 * Handles all CMS-related API calls for the dashboard
 */

import { apiClient } from './client';

// ==================== Types ====================

export interface CMSBanner {
  id: string;
  title: string;
  subtitle?: string;
  image_url: string;
  thumbnail_url?: string;
  mobile_image_url?: string;
  cta_text?: string;
  cta_link?: string;
  text_position: 'left' | 'center' | 'right';
  text_color: 'white' | 'dark';
  sort_order: number;
  is_active: boolean;
  starts_at?: string;
  ends_at?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface CMSBannerCreate {
  title: string;
  subtitle?: string;
  image_url: string;
  thumbnail_url?: string;
  mobile_image_url?: string;
  cta_text?: string;
  cta_link?: string;
  text_position?: 'left' | 'center' | 'right';
  text_color?: 'white' | 'dark';
  sort_order?: number;
  is_active?: boolean;
  starts_at?: string;
  ends_at?: string;
}

export interface CMSUsp {
  id: string;
  title: string;
  description?: string;
  icon: string;
  icon_color?: string;
  link_url?: string;
  link_text?: string;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface CMSUspCreate {
  title: string;
  description?: string;
  icon: string;
  icon_color?: string;
  link_url?: string;
  link_text?: string;
  sort_order?: number;
  is_active?: boolean;
}

export interface CMSTestimonial {
  id: string;
  customer_name: string;
  customer_location?: string;
  customer_avatar_url?: string;
  customer_designation?: string;
  rating: number;
  content: string;
  title?: string;
  product_name?: string;
  product_id?: string;
  sort_order: number;
  is_featured: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface CMSTestimonialCreate {
  customer_name: string;
  customer_location?: string;
  customer_avatar_url?: string;
  customer_designation?: string;
  rating: number;
  content: string;
  title?: string;
  product_name?: string;
  product_id?: string;
  sort_order?: number;
  is_featured?: boolean;
  is_active?: boolean;
}

export interface CMSAnnouncement {
  id: string;
  text: string;
  link_url?: string;
  link_text?: string;
  announcement_type: 'INFO' | 'WARNING' | 'PROMO' | 'SUCCESS';
  background_color?: string;
  text_color?: string;
  starts_at?: string;
  ends_at?: string;
  sort_order: number;
  is_dismissible: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface CMSAnnouncementCreate {
  text: string;
  link_url?: string;
  link_text?: string;
  announcement_type?: 'INFO' | 'WARNING' | 'PROMO' | 'SUCCESS';
  background_color?: string;
  text_color?: string;
  starts_at?: string;
  ends_at?: string;
  sort_order?: number;
  is_dismissible?: boolean;
  is_active?: boolean;
}

export interface CMSPageVersion {
  id: string;
  page_id: string;
  version_number: number;
  title: string;
  content?: string;
  meta_title?: string;
  meta_description?: string;
  change_summary?: string;
  created_at: string;
  created_by?: string;
}

export interface CMSPage {
  id: string;
  title: string;
  slug: string;
  content?: string;
  excerpt?: string;
  meta_title?: string;
  meta_description?: string;
  meta_keywords?: string;
  og_image_url?: string;
  canonical_url?: string;
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
  published_at?: string;
  template: 'default' | 'full-width' | 'landing';
  show_in_footer: boolean;
  show_in_header: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  versions: CMSPageVersion[];
}

export interface CMSPageBrief {
  id: string;
  title: string;
  slug: string;
  status: string;
  published_at?: string;
  updated_at: string;
}

export interface CMSPageCreate {
  title: string;
  slug: string;
  content?: string;
  excerpt?: string;
  meta_title?: string;
  meta_description?: string;
  meta_keywords?: string;
  og_image_url?: string;
  canonical_url?: string;
  status?: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
  template?: 'default' | 'full-width' | 'landing';
  show_in_footer?: boolean;
  show_in_header?: boolean;
  sort_order?: number;
}

export interface CMSSeo {
  id: string;
  url_path: string;
  meta_title?: string;
  meta_description?: string;
  meta_keywords?: string;
  og_title?: string;
  og_description?: string;
  og_image_url?: string;
  og_type: string;
  canonical_url?: string;
  robots_index: boolean;
  robots_follow: boolean;
  structured_data?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface CMSSeoCreate {
  url_path: string;
  meta_title?: string;
  meta_description?: string;
  meta_keywords?: string;
  og_title?: string;
  og_description?: string;
  og_image_url?: string;
  og_type?: string;
  canonical_url?: string;
  robots_index?: boolean;
  robots_follow?: boolean;
  structured_data?: Record<string, unknown>;
}

// Site Settings
export interface CMSSiteSetting {
  id: string;
  setting_key: string;
  setting_value?: string;
  setting_type: 'text' | 'textarea' | 'url' | 'boolean' | 'number' | 'image';
  setting_group: string;
  label?: string;
  description?: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface CMSSiteSettingCreate {
  setting_key: string;
  setting_value?: string;
  setting_type: 'text' | 'textarea' | 'url' | 'boolean' | 'number' | 'image';
  setting_group: string;
  label?: string;
  description?: string;
  sort_order?: number;
}

// Menu Items
export interface CMSMenuItem {
  id: string;
  menu_location: 'header' | 'footer_quick' | 'footer_service';
  title: string;
  url: string;
  icon?: string;
  target: '_self' | '_blank';
  parent_id?: string;
  sort_order: number;
  is_active: boolean;
  show_on_mobile: boolean;
  css_class?: string;
  created_at: string;
  updated_at: string;
  children?: CMSMenuItem[];
}

export interface CMSMenuItemCreate {
  menu_location: 'header' | 'footer_quick' | 'footer_service';
  title: string;
  url: string;
  icon?: string;
  target?: '_self' | '_blank';
  parent_id?: string;
  sort_order?: number;
  is_active?: boolean;
  show_on_mobile?: boolean;
  css_class?: string;
}

// Feature Bars
export interface CMSFeatureBar {
  id: string;
  icon: string;
  title: string;
  subtitle?: string;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CMSFeatureBarCreate {
  icon: string;
  title: string;
  subtitle?: string;
  sort_order?: number;
  is_active?: boolean;
}

// Mega Menu Items
export interface CMSMegaMenuItem {
  id: string;
  title: string;
  icon?: string;
  image_url?: string;
  menu_type: 'CATEGORY' | 'CUSTOM_LINK';
  category_id?: string;
  url?: string;
  target: '_self' | '_blank';
  show_subcategories: boolean;
  subcategory_ids?: string[];
  sort_order: number;
  is_active: boolean;
  is_highlighted: boolean;
  highlight_text?: string;
  company_id?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  // Resolved from category
  category_name?: string;
  category_slug?: string;
}

export interface CMSMegaMenuItemCreate {
  title: string;
  icon?: string;
  image_url?: string;
  menu_type: 'CATEGORY' | 'CUSTOM_LINK';
  category_id?: string;
  url?: string;
  target?: '_self' | '_blank';
  show_subcategories?: boolean;
  subcategory_ids?: string[];
  sort_order?: number;
  is_active?: boolean;
  is_highlighted?: boolean;
  highlight_text?: string;
}

// FAQ Categories
export interface CMSFaqCategory {
  id: string;
  name: string;
  slug: string;
  description?: string;
  icon: string;
  icon_color?: string;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
  items_count: number;
}

export interface CMSFaqCategoryCreate {
  name: string;
  slug: string;
  description?: string;
  icon?: string;
  icon_color?: string;
  sort_order?: number;
  is_active?: boolean;
}

// FAQ Items
export interface CMSFaqItem {
  id: string;
  category_id: string;
  question: string;
  answer: string;
  keywords: string[];
  sort_order: number;
  is_featured: boolean;
  is_active: boolean;
  view_count: number;
  helpful_count: number;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface CMSFaqItemCreate {
  category_id: string;
  question: string;
  answer: string;
  keywords?: string[];
  sort_order?: number;
  is_featured?: boolean;
  is_active?: boolean;
}

// Video Guides
export interface CMSVideoGuide {
  id: string;
  title: string;
  slug: string;
  description?: string;
  thumbnail_url: string;
  video_url: string;
  video_type: 'YOUTUBE' | 'VIMEO' | 'DIRECT';
  video_id?: string;
  duration_seconds?: number;
  category: 'INSTALLATION' | 'MAINTENANCE' | 'TROUBLESHOOTING' | 'PRODUCT_TOUR' | 'HOW_TO' | 'TIPS';
  tags?: string[];
  product_id?: string;
  product_category_id?: string;
  sort_order: number;
  is_featured: boolean;
  is_active: boolean;
  view_count: number;
  like_count: number;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface CMSVideoGuideCreate {
  title: string;
  slug: string;
  description?: string;
  thumbnail_url: string;
  video_url: string;
  video_type?: 'YOUTUBE' | 'VIMEO' | 'DIRECT';
  video_id?: string;
  duration_seconds?: number;
  category?: string;
  tags?: string[];
  product_id?: string;
  product_category_id?: string;
  sort_order?: number;
  is_featured?: boolean;
  is_active?: boolean;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
}

// ==================== API Functions ====================

export const cmsApi = {
  // Banners
  banners: {
    list: (params?: { is_active?: boolean; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSBanner>>('/cms/banners', { params }),

    get: (id: string) =>
      apiClient.get<CMSBanner>(`/cms/banners/${id}`),

    create: (data: CMSBannerCreate) =>
      apiClient.post<CMSBanner>('/cms/banners', data),

    update: (id: string, data: Partial<CMSBannerCreate>) =>
      apiClient.put<CMSBanner>(`/cms/banners/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/banners/${id}`),

    reorder: (ids: string[]) =>
      apiClient.put<CMSBanner[]>('/cms/banners/reorder', { ids }),
  },

  // USPs
  usps: {
    list: (params?: { is_active?: boolean; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSUsp>>('/cms/usps', { params }),

    get: (id: string) =>
      apiClient.get<CMSUsp>(`/cms/usps/${id}`),

    create: (data: CMSUspCreate) =>
      apiClient.post<CMSUsp>('/cms/usps', data),

    update: (id: string, data: Partial<CMSUspCreate>) =>
      apiClient.put<CMSUsp>(`/cms/usps/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/usps/${id}`),

    reorder: (ids: string[]) =>
      apiClient.put<CMSUsp[]>('/cms/usps/reorder', { ids }),
  },

  // Testimonials
  testimonials: {
    list: (params?: { is_active?: boolean; is_featured?: boolean; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSTestimonial>>('/cms/testimonials', { params }),

    get: (id: string) =>
      apiClient.get<CMSTestimonial>(`/cms/testimonials/${id}`),

    create: (data: CMSTestimonialCreate) =>
      apiClient.post<CMSTestimonial>('/cms/testimonials', data),

    update: (id: string, data: Partial<CMSTestimonialCreate>) =>
      apiClient.put<CMSTestimonial>(`/cms/testimonials/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/testimonials/${id}`),
  },

  // Announcements
  announcements: {
    list: (params?: { is_active?: boolean; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSAnnouncement>>('/cms/announcements', { params }),

    get: (id: string) =>
      apiClient.get<CMSAnnouncement>(`/cms/announcements/${id}`),

    create: (data: CMSAnnouncementCreate) =>
      apiClient.post<CMSAnnouncement>('/cms/announcements', data),

    update: (id: string, data: Partial<CMSAnnouncementCreate>) =>
      apiClient.put<CMSAnnouncement>(`/cms/announcements/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/announcements/${id}`),
  },

  // Pages
  pages: {
    list: (params?: { status?: string; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSPageBrief>>('/cms/pages', { params }),

    get: (id: string) =>
      apiClient.get<CMSPage>(`/cms/pages/${id}`),

    create: (data: CMSPageCreate) =>
      apiClient.post<CMSPage>('/cms/pages', data),

    update: (id: string, data: Partial<CMSPageCreate>) =>
      apiClient.put<CMSPage>(`/cms/pages/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/pages/${id}`),

    publish: (id: string) =>
      apiClient.post<CMSPage>(`/cms/pages/${id}/publish`),

    getVersions: (id: string) =>
      apiClient.get<CMSPageVersion[]>(`/cms/pages/${id}/versions`),

    revertToVersion: (id: string, versionNumber: number) =>
      apiClient.post<CMSPage>(`/cms/pages/${id}/revert/${versionNumber}`),
  },

  // SEO
  seo: {
    list: (params?: { skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSSeo>>('/cms/seo', { params }),

    get: (id: string) =>
      apiClient.get<CMSSeo>(`/cms/seo/${id}`),

    create: (data: CMSSeoCreate) =>
      apiClient.post<CMSSeo>('/cms/seo', data),

    update: (id: string, data: Partial<CMSSeoCreate>) =>
      apiClient.put<CMSSeo>(`/cms/seo/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/seo/${id}`),
  },

  // Site Settings
  settings: {
    list: (params?: { group?: string; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSSiteSetting>>('/cms/settings', { params }),

    get: (key: string) =>
      apiClient.get<CMSSiteSetting>(`/cms/settings/${key}`),

    create: (data: CMSSiteSettingCreate) =>
      apiClient.post<CMSSiteSetting>('/cms/settings', data),

    update: (key: string, data: Partial<CMSSiteSettingCreate>) =>
      apiClient.put<CMSSiteSetting>(`/cms/settings/${key}`, data),

    bulkUpdate: (settings: Record<string, string>) =>
      apiClient.put<CMSSiteSetting[]>('/cms/settings-bulk', { settings }),

    delete: (key: string) =>
      apiClient.delete(`/cms/settings/${key}`),
  },

  // Menu Items
  menuItems: {
    list: (params?: { location?: string; is_active?: boolean; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSMenuItem>>('/cms/menu-items', { params }),

    get: (id: string) =>
      apiClient.get<CMSMenuItem>(`/cms/menu-items/${id}`),

    create: (data: CMSMenuItemCreate) =>
      apiClient.post<CMSMenuItem>('/cms/menu-items', data),

    update: (id: string, data: Partial<CMSMenuItemCreate>) =>
      apiClient.put<CMSMenuItem>(`/cms/menu-items/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/menu-items/${id}`),

    reorder: (ids: string[]) =>
      apiClient.put<CMSMenuItem[]>('/cms/menu-items/reorder', { ids }),
  },

  // Feature Bars
  featureBars: {
    list: (params?: { is_active?: boolean; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSFeatureBar>>('/cms/feature-bars', { params }),

    get: (id: string) =>
      apiClient.get<CMSFeatureBar>(`/cms/feature-bars/${id}`),

    create: (data: CMSFeatureBarCreate) =>
      apiClient.post<CMSFeatureBar>('/cms/feature-bars', data),

    update: (id: string, data: Partial<CMSFeatureBarCreate>) =>
      apiClient.put<CMSFeatureBar>(`/cms/feature-bars/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/feature-bars/${id}`),

    reorder: (ids: string[]) =>
      apiClient.put<CMSFeatureBar[]>('/cms/feature-bars/reorder', { ids }),
  },

  // Mega Menu Items
  megaMenuItems: {
    list: (params?: { is_active?: boolean; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSMegaMenuItem>>('/cms/mega-menu-items', { params }),

    get: (id: string) =>
      apiClient.get<CMSMegaMenuItem>(`/cms/mega-menu-items/${id}`),

    create: (data: CMSMegaMenuItemCreate) =>
      apiClient.post<CMSMegaMenuItem>('/cms/mega-menu-items', data),

    update: (id: string, data: Partial<CMSMegaMenuItemCreate>) =>
      apiClient.put<CMSMegaMenuItem>(`/cms/mega-menu-items/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/mega-menu-items/${id}`),

    reorder: (ids: string[]) =>
      apiClient.put<CMSMegaMenuItem[]>('/cms/mega-menu-items/reorder', { ids }),
  },

  // FAQ Categories
  faqCategories: {
    list: (params?: { is_active?: boolean; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSFaqCategory>>('/cms/faq-categories', { params }),

    get: (id: string) =>
      apiClient.get<CMSFaqCategory>(`/cms/faq-categories/${id}`),

    create: (data: CMSFaqCategoryCreate) =>
      apiClient.post<CMSFaqCategory>('/cms/faq-categories', data),

    update: (id: string, data: Partial<CMSFaqCategoryCreate>) =>
      apiClient.put<CMSFaqCategory>(`/cms/faq-categories/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/faq-categories/${id}`),

    reorder: (ids: string[]) =>
      apiClient.put('/cms/faq-categories/reorder', { ids }),
  },

  // FAQ Items
  faqItems: {
    list: (params?: { category_id?: string; is_active?: boolean; is_featured?: boolean; search?: string; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSFaqItem>>('/cms/faq-items', { params }),

    get: (id: string) =>
      apiClient.get<CMSFaqItem>(`/cms/faq-items/${id}`),

    create: (data: CMSFaqItemCreate) =>
      apiClient.post<CMSFaqItem>('/cms/faq-items', data),

    update: (id: string, data: Partial<CMSFaqItemCreate>) =>
      apiClient.put<CMSFaqItem>(`/cms/faq-items/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/faq-items/${id}`),

    reorder: (ids: string[]) =>
      apiClient.put('/cms/faq-items/reorder', { ids }),
  },

  // Video Guides
  videoGuides: {
    list: (params?: { category?: string; is_active?: boolean; is_featured?: boolean; search?: string; skip?: number; limit?: number }) =>
      apiClient.get<ListResponse<CMSVideoGuide>>('/cms/video-guides', { params }),

    get: (id: string) =>
      apiClient.get<CMSVideoGuide>(`/cms/video-guides/${id}`),

    create: (data: CMSVideoGuideCreate) =>
      apiClient.post<CMSVideoGuide>('/cms/video-guides', data),

    update: (id: string, data: Partial<CMSVideoGuideCreate>) =>
      apiClient.put<CMSVideoGuide>(`/cms/video-guides/${id}`, data),

    delete: (id: string) =>
      apiClient.delete(`/cms/video-guides/${id}`),

    reorder: (ids: string[]) =>
      apiClient.put('/cms/video-guides/reorder', { ids }),
  },
};

export default cmsApi;
