'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Save,
  RefreshCw,
  Globe,
  Phone,
  Mail,
  MapPin,
  Facebook,
  Instagram,
  Youtube,
  Twitter,
  Linkedin,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/common';
import { cmsApi, CMSSiteSetting } from '@/lib/api/cms';

const socialIcons: Record<string, React.ReactNode> = {
  facebook: <Facebook className="h-4 w-4" />,
  instagram: <Instagram className="h-4 w-4" />,
  youtube: <Youtube className="h-4 w-4" />,
  twitter: <Twitter className="h-4 w-4" />,
  linkedin: <Linkedin className="h-4 w-4" />,
};

export default function SiteSettingsPage() {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['cms-settings'],
    queryFn: () => cmsApi.settings.list(),
  });

  const bulkUpdateMutation = useMutation({
    mutationFn: (settings: Record<string, string>) => cmsApi.settings.bulkUpdate(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-settings'] });
      toast.success('Settings saved successfully');
      setHasChanges(false);
    },
    onError: () => toast.error('Failed to save settings'),
  });

  const settings = data?.data?.items || [];

  // Group settings by category
  const groupedSettings = settings.reduce((acc: Record<string, CMSSiteSetting[]>, setting) => {
    const group = setting.setting_group;
    if (!acc[group]) acc[group] = [];
    acc[group].push(setting);
    return acc;
  }, {});

  // Sort settings within each group
  Object.keys(groupedSettings).forEach((group) => {
    groupedSettings[group].sort((a, b) => a.sort_order - b.sort_order);
  });

  const handleChange = (key: string, value: string) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const getValue = (setting: CMSSiteSetting): string => {
    if (formData[setting.setting_key] !== undefined) {
      return formData[setting.setting_key];
    }
    return setting.setting_value || '';
  };

  const handleSave = () => {
    if (Object.keys(formData).length === 0) {
      toast.info('No changes to save');
      return;
    }
    bulkUpdateMutation.mutate(formData);
  };

  const handleReset = () => {
    setFormData({});
    setHasChanges(false);
    refetch();
  };

  const renderSettingInput = (setting: CMSSiteSetting) => {
    const value = getValue(setting);

    switch (setting.setting_type) {
      case 'boolean':
        return (
          <Switch
            id={setting.setting_key}
            checked={value === 'true'}
            onCheckedChange={(checked) => handleChange(setting.setting_key, checked ? 'true' : 'false')}
          />
        );

      case 'textarea':
        return (
          <Textarea
            id={setting.setting_key}
            value={value}
            onChange={(e) => handleChange(setting.setting_key, e.target.value)}
            rows={3}
            placeholder={setting.description || ''}
          />
        );

      case 'url':
        return (
          <Input
            id={setting.setting_key}
            type="url"
            value={value}
            onChange={(e) => handleChange(setting.setting_key, e.target.value)}
            placeholder="https://..."
          />
        );

      case 'number':
        return (
          <Input
            id={setting.setting_key}
            type="number"
            value={value}
            onChange={(e) => handleChange(setting.setting_key, e.target.value)}
          />
        );

      default:
        return (
          <Input
            id={setting.setting_key}
            value={value}
            onChange={(e) => handleChange(setting.setting_key, e.target.value)}
            placeholder={setting.description || ''}
          />
        );
    }
  };

  const getGroupIcon = (group: string) => {
    switch (group) {
      case 'social':
        return <Globe className="h-5 w-5" />;
      case 'contact':
        return <Phone className="h-5 w-5" />;
      case 'footer':
        return <Mail className="h-5 w-5" />;
      default:
        return <Globe className="h-5 w-5" />;
    }
  };

  const getGroupTitle = (group: string) => {
    switch (group) {
      case 'social':
        return 'Social Media Links';
      case 'contact':
        return 'Contact Information';
      case 'footer':
        return 'Footer Settings';
      case 'newsletter':
        return 'Newsletter Settings';
      default:
        return group.charAt(0).toUpperCase() + group.slice(1);
    }
  };

  const getGroupDescription = (group: string) => {
    switch (group) {
      case 'social':
        return 'Configure your social media profile links shown in the footer';
      case 'contact':
        return 'Contact details displayed on the storefront';
      case 'footer':
        return 'Footer text and copyright information';
      case 'newsletter':
        return 'Newsletter subscription settings';
      default:
        return '';
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Site Settings"
        description="Manage global settings for your D2C storefront"
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleReset}
              disabled={!hasChanges}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Reset
            </Button>
            <Button
              onClick={handleSave}
              disabled={!hasChanges || bulkUpdateMutation.isPending}
            >
              <Save className="h-4 w-4 mr-2" />
              {bulkUpdateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        }
      />

      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Loading settings...</div>
      ) : (
        <Tabs defaultValue="social" className="space-y-4">
          <TabsList>
            {Object.keys(groupedSettings).map((group) => (
              <TabsTrigger key={group} value={group} className="capitalize">
                {getGroupTitle(group)}
              </TabsTrigger>
            ))}
          </TabsList>

          {Object.entries(groupedSettings).map(([group, groupSettings]) => (
            <TabsContent key={group} value={group}>
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    {getGroupIcon(group)}
                    <CardTitle>{getGroupTitle(group)}</CardTitle>
                  </div>
                  <CardDescription>{getGroupDescription(group)}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {groupSettings.map((setting) => (
                    <div key={setting.id} className="space-y-2">
                      <div className="flex items-center gap-2">
                        {setting.setting_key.includes('facebook') && socialIcons.facebook}
                        {setting.setting_key.includes('instagram') && socialIcons.instagram}
                        {setting.setting_key.includes('youtube') && socialIcons.youtube}
                        {setting.setting_key.includes('twitter') && socialIcons.twitter}
                        {setting.setting_key.includes('linkedin') && socialIcons.linkedin}
                        <Label htmlFor={setting.setting_key}>
                          {setting.label || setting.setting_key}
                        </Label>
                      </div>
                      {renderSettingInput(setting)}
                      {setting.description && setting.setting_type !== 'boolean' && (
                        <p className="text-xs text-muted-foreground">{setting.description}</p>
                      )}
                    </div>
                  ))}

                  {groupSettings.length === 0 && (
                    <p className="text-center py-4 text-muted-foreground">
                      No settings in this category
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          ))}
        </Tabs>
      )}

      {hasChanges && (
        <div className="fixed bottom-4 right-4 bg-background border rounded-lg shadow-lg p-4 flex items-center gap-4">
          <span className="text-sm text-muted-foreground">You have unsaved changes</span>
          <Button variant="outline" size="sm" onClick={handleReset}>
            Discard
          </Button>
          <Button size="sm" onClick={handleSave} disabled={bulkUpdateMutation.isPending}>
            Save Changes
          </Button>
        </div>
      )}
    </div>
  );
}
