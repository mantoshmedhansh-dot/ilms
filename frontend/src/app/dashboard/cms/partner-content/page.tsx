'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Save, Loader2, Eye, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { PageHeader } from '@/components/common';
import { toast } from 'sonner';
import { cmsApi } from '@/lib/api/cms';

interface PartnerPageContent {
  // Hero Section
  hero_title: string;
  hero_subtitle: string;
  // Benefit 1
  benefit_1_title: string;
  benefit_1_description: string;
  benefit_1_icon: string;
  // Benefit 2
  benefit_2_title: string;
  benefit_2_description: string;
  benefit_2_icon: string;
  // Benefit 3
  benefit_3_title: string;
  benefit_3_description: string;
  benefit_3_icon: string;
  // Registration Form
  form_title: string;
  form_subtitle: string;
  // Success Message
  success_title: string;
  success_message: string;
}

const defaultContent: PartnerPageContent = {
  hero_title: 'Become an ILMS.AI Partner',
  hero_subtitle: 'Join our community of partners and earn by sharing our products. Zero investment, unlimited earning potential!',
  benefit_1_title: 'Earn Commission',
  benefit_1_description: '10-15% commission on every successful sale',
  benefit_1_icon: 'Wallet',
  benefit_2_title: 'Easy Sharing',
  benefit_2_description: 'Share products via WhatsApp, social media, and more',
  benefit_2_icon: 'Share2',
  benefit_3_title: 'Grow Together',
  benefit_3_description: 'Tier upgrades with higher commission rates',
  benefit_3_icon: 'TrendingUp',
  form_title: 'Partner Registration',
  form_subtitle: 'Fill in your details to get started',
  success_title: 'Registration Successful!',
  success_message: 'Your partner application has been submitted. You can now login with your mobile number.',
};

const SETTING_KEYS = Object.keys(defaultContent).map(key => `partner_page_${key}`);

export default function PartnerContentPage() {
  const queryClient = useQueryClient();
  const [content, setContent] = useState<PartnerPageContent>(defaultContent);
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch existing settings
  const { data: settings, isLoading } = useQuery({
    queryKey: ['cms-settings-partner'],
    queryFn: async () => {
      const response = await cmsApi.settings.list({ group: 'partner_page', limit: 50 });
      return response.data?.items || [];
    },
  });

  // Initialize content from settings
  useEffect(() => {
    if (settings && settings.length > 0) {
      const newContent = { ...defaultContent };
      settings.forEach((setting: { setting_key: string; setting_value?: string }) => {
        const key = setting.setting_key.replace('partner_page_', '') as keyof PartnerPageContent;
        if (key in defaultContent && setting.setting_value) {
          newContent[key] = setting.setting_value;
        }
      });
      setContent(newContent);
    }
  }, [settings]);

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async (data: PartnerPageContent) => {
      const settingsToUpdate: Record<string, string> = {};
      Object.entries(data).forEach(([key, value]) => {
        settingsToUpdate[`partner_page_${key}`] = value;
      });

      // Use bulk update if available, otherwise update individually
      try {
        await cmsApi.settings.bulkUpdate(settingsToUpdate);
      } catch {
        // Fallback: create/update each setting individually
        for (const [key, value] of Object.entries(data)) {
          const settingKey = `partner_page_${key}`;
          try {
            await cmsApi.settings.update(settingKey, { setting_value: value });
          } catch {
            // Setting doesn't exist, create it
            await cmsApi.settings.create({
              setting_key: settingKey,
              setting_value: value,
              setting_type: key.includes('description') || key.includes('subtitle') || key.includes('message') ? 'textarea' : 'text',
              setting_group: 'partner_page',
              label: key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
            });
          }
        }
      }
    },
    onSuccess: () => {
      toast.success('Partner page content has been updated successfully.');
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['cms-settings-partner'] });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to save content');
    },
  });

  const handleChange = (key: keyof PartnerPageContent, value: string) => {
    setContent(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = () => {
    saveMutation.mutate(content);
  };

  const handleReset = () => {
    setContent(defaultContent);
    setHasChanges(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Partner Page Content"
        description="Edit the content displayed on the Become a Partner page"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <a href="https://www.ilms.ai/become-partner" target="_blank" rel="noopener noreferrer">
                <Eye className="h-4 w-4 mr-2" />
                Preview
              </a>
            </Button>
            <Button variant="outline" onClick={handleReset}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Reset to Default
            </Button>
            <Button onClick={handleSave} disabled={!hasChanges || saveMutation.isPending}>
              {saveMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Save className="h-4 w-4 mr-2" />
              )}
              Save Changes
            </Button>
          </div>
        }
      />

      {/* Hero Section */}
      <Card>
        <CardHeader>
          <CardTitle>Hero Section</CardTitle>
          <CardDescription>Main heading and subtitle shown at the top of the page</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="hero_title">Page Title</Label>
            <Input
              id="hero_title"
              value={content.hero_title}
              onChange={(e) => handleChange('hero_title', e.target.value)}
              placeholder="Become an ILMS.AI Partner"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="hero_subtitle">Subtitle</Label>
            <Textarea
              id="hero_subtitle"
              value={content.hero_subtitle}
              onChange={(e) => handleChange('hero_subtitle', e.target.value)}
              placeholder="Join our community of partners..."
              rows={3}
            />
          </div>
        </CardContent>
      </Card>

      {/* Benefits Section */}
      <Card>
        <CardHeader>
          <CardTitle>Benefits Cards</CardTitle>
          <CardDescription>Three benefit cards shown below the hero section</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-6">
            {/* Benefit 1 */}
            <div className="space-y-4 p-4 border rounded-lg">
              <h4 className="font-medium text-sm text-muted-foreground">Benefit 1 (Earn Commission)</h4>
              <div className="space-y-2">
                <Label htmlFor="benefit_1_title">Title</Label>
                <Input
                  id="benefit_1_title"
                  value={content.benefit_1_title}
                  onChange={(e) => handleChange('benefit_1_title', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="benefit_1_description">Description</Label>
                <Textarea
                  id="benefit_1_description"
                  value={content.benefit_1_description}
                  onChange={(e) => handleChange('benefit_1_description', e.target.value)}
                  rows={2}
                />
              </div>
            </div>

            {/* Benefit 2 */}
            <div className="space-y-4 p-4 border rounded-lg">
              <h4 className="font-medium text-sm text-muted-foreground">Benefit 2 (Easy Sharing)</h4>
              <div className="space-y-2">
                <Label htmlFor="benefit_2_title">Title</Label>
                <Input
                  id="benefit_2_title"
                  value={content.benefit_2_title}
                  onChange={(e) => handleChange('benefit_2_title', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="benefit_2_description">Description</Label>
                <Textarea
                  id="benefit_2_description"
                  value={content.benefit_2_description}
                  onChange={(e) => handleChange('benefit_2_description', e.target.value)}
                  rows={2}
                />
              </div>
            </div>

            {/* Benefit 3 */}
            <div className="space-y-4 p-4 border rounded-lg">
              <h4 className="font-medium text-sm text-muted-foreground">Benefit 3 (Grow Together)</h4>
              <div className="space-y-2">
                <Label htmlFor="benefit_3_title">Title</Label>
                <Input
                  id="benefit_3_title"
                  value={content.benefit_3_title}
                  onChange={(e) => handleChange('benefit_3_title', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="benefit_3_description">Description</Label>
                <Textarea
                  id="benefit_3_description"
                  value={content.benefit_3_description}
                  onChange={(e) => handleChange('benefit_3_description', e.target.value)}
                  rows={2}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Registration Form Section */}
      <Card>
        <CardHeader>
          <CardTitle>Registration Form</CardTitle>
          <CardDescription>Title and description for the registration form card</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="form_title">Form Title</Label>
              <Input
                id="form_title"
                value={content.form_title}
                onChange={(e) => handleChange('form_title', e.target.value)}
                placeholder="Partner Registration"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="form_subtitle">Form Subtitle</Label>
              <Input
                id="form_subtitle"
                value={content.form_subtitle}
                onChange={(e) => handleChange('form_subtitle', e.target.value)}
                placeholder="Fill in your details to get started"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Success Message Section */}
      <Card>
        <CardHeader>
          <CardTitle>Success Message</CardTitle>
          <CardDescription>Message shown after successful registration</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="success_title">Success Title</Label>
            <Input
              id="success_title"
              value={content.success_title}
              onChange={(e) => handleChange('success_title', e.target.value)}
              placeholder="Registration Successful!"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="success_message">Success Message</Label>
            <Textarea
              id="success_message"
              value={content.success_message}
              onChange={(e) => handleChange('success_message', e.target.value)}
              placeholder="Your partner application has been submitted..."
              rows={3}
            />
          </div>
        </CardContent>
      </Card>

      {/* Sticky Save Bar */}
      {hasChanges && (
        <div className="fixed bottom-0 left-0 right-0 bg-background border-t p-4 flex justify-end gap-2 z-50">
          <Button variant="outline" onClick={() => setContent(defaultContent)}>
            Discard Changes
          </Button>
          <Button onClick={handleSave} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Save Changes
          </Button>
        </div>
      )}
    </div>
  );
}
