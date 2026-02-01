'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Phone,
  Mail,
  MapPin,
  MessageCircle,
  Clock,
  Globe,
  Save,
  Loader2,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { cmsApi, CMSSiteSetting } from '@/lib/api/cms';

// Contact settings configuration
const CONTACT_SETTINGS = [
  // Primary Contact
  { key: 'contact_phone', label: 'Phone Number', type: 'text', group: 'contact', icon: Phone, description: 'Primary support phone number', placeholder: '+91 93119 39076' },
  { key: 'contact_phone_toll_free', label: 'Toll-Free Number', type: 'text', group: 'contact', icon: Phone, description: 'Optional toll-free number', placeholder: '1800-123-4567' },
  { key: 'contact_whatsapp', label: 'WhatsApp Number', type: 'text', group: 'contact', icon: MessageCircle, description: 'WhatsApp support number (include country code)', placeholder: '919311939076' },
  { key: 'contact_email', label: 'Support Email', type: 'text', group: 'contact', icon: Mail, description: 'Primary support email address', placeholder: 'support@aquapurite.com' },
  { key: 'contact_email_sales', label: 'Sales Email', type: 'text', group: 'contact', icon: Mail, description: 'Sales inquiry email', placeholder: 'sales@aquapurite.com' },

  // Address
  { key: 'contact_address', label: 'Street Address', type: 'textarea', group: 'contact', icon: MapPin, description: 'Office/Corporate address', placeholder: 'Plot No. 123, Industrial Area' },
  { key: 'contact_city', label: 'City', type: 'text', group: 'contact', icon: MapPin, description: 'City name', placeholder: 'Delhi' },
  { key: 'contact_state', label: 'State', type: 'text', group: 'contact', icon: MapPin, description: 'State name', placeholder: 'Delhi' },
  { key: 'contact_pincode', label: 'Pincode', type: 'text', group: 'contact', icon: MapPin, description: 'Postal code', placeholder: '110001' },
  { key: 'contact_country', label: 'Country', type: 'text', group: 'contact', icon: MapPin, description: 'Country name', placeholder: 'India' },
  { key: 'contact_google_maps_url', label: 'Google Maps Link', type: 'url', group: 'contact', icon: Globe, description: 'Google Maps URL for directions', placeholder: 'https://maps.google.com/?q=...' },

  // Support Hours
  { key: 'support_hours_weekday', label: 'Weekday Hours', type: 'text', group: 'contact', icon: Clock, description: 'Mon-Sat support hours', placeholder: '9:00 AM - 8:00 PM IST' },
  { key: 'support_hours_weekend', label: 'Weekend Hours', type: 'text', group: 'contact', icon: Clock, description: 'Sunday support hours', placeholder: 'Emergency Only' },
  { key: 'support_response_time', label: 'Response Time', type: 'text', group: 'contact', icon: Clock, description: 'Average response time displayed', placeholder: '5 min' },
];

const SOCIAL_SETTINGS = [
  { key: 'social_facebook', label: 'Facebook URL', type: 'url', group: 'social', icon: Globe, description: 'Facebook page URL', placeholder: 'https://facebook.com/aquapurite' },
  { key: 'social_instagram', label: 'Instagram URL', type: 'url', group: 'social', icon: Globe, description: 'Instagram profile URL', placeholder: 'https://instagram.com/aquapurite' },
  { key: 'social_twitter', label: 'Twitter/X URL', type: 'url', group: 'social', icon: Globe, description: 'Twitter/X profile URL', placeholder: 'https://twitter.com/aquapurite' },
  { key: 'social_youtube', label: 'YouTube URL', type: 'url', group: 'social', icon: Globe, description: 'YouTube channel URL', placeholder: 'https://youtube.com/@aquapurite' },
  { key: 'social_linkedin', label: 'LinkedIn URL', type: 'url', group: 'social', icon: Globe, description: 'LinkedIn company page URL', placeholder: 'https://linkedin.com/company/aquapurite' },
];

export default function ContactSettingsPage() {
  const queryClient = useQueryClient();
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch existing settings
  const { data: settingsData, isLoading } = useQuery({
    queryKey: ['cms-settings'],
    queryFn: async () => {
      const response = await cmsApi.settings.list({ limit: 100 });
      return response.data;
    },
  });

  // Initialize form with existing values
  useEffect(() => {
    if (settingsData?.items) {
      const values: Record<string, string> = {};
      settingsData.items.forEach((setting: CMSSiteSetting) => {
        values[setting.setting_key] = setting.setting_value || '';
      });
      setFormValues(values);
      setHasChanges(false);
    }
  }, [settingsData]);

  // Bulk update mutation
  const updateMutation = useMutation({
    mutationFn: async (settings: Record<string, string>) => {
      // Create or update each setting
      const allSettings = [...CONTACT_SETTINGS, ...SOCIAL_SETTINGS];
      const promises = allSettings
        .filter((s) => settings[s.key] !== undefined)
        .map(async (settingConfig) => {
          const existingSetting = settingsData?.items?.find(
            (s: CMSSiteSetting) => s.setting_key === settingConfig.key
          );

          if (existingSetting) {
            // Update existing
            return cmsApi.settings.update(settingConfig.key, {
              setting_value: settings[settingConfig.key] || '',
            });
          } else if (settings[settingConfig.key]) {
            // Create new
            return cmsApi.settings.create({
              setting_key: settingConfig.key,
              setting_value: settings[settingConfig.key],
              setting_type: settingConfig.type as 'text' | 'textarea' | 'url' | 'boolean' | 'number' | 'image',
              setting_group: settingConfig.group,
              label: settingConfig.label,
              description: settingConfig.description,
            });
          }
          return Promise.resolve();
        });

      await Promise.all(promises);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-settings'] });
      toast.success('Contact settings saved successfully');
      setHasChanges(false);
    },
    onError: () => {
      toast.error('Failed to save settings');
    },
  });

  const handleChange = (key: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = () => {
    updateMutation.mutate(formValues);
  };

  const renderSettingField = (setting: typeof CONTACT_SETTINGS[0]) => {
    const Icon = setting.icon;
    const value = formValues[setting.key] || '';

    return (
      <div key={setting.key} className="space-y-2">
        <Label htmlFor={setting.key} className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {setting.label}
        </Label>
        {setting.type === 'textarea' ? (
          <Textarea
            id={setting.key}
            value={value}
            onChange={(e) => handleChange(setting.key, e.target.value)}
            placeholder={setting.placeholder}
            rows={2}
          />
        ) : (
          <Input
            id={setting.key}
            type={setting.type === 'url' ? 'url' : 'text'}
            value={value}
            onChange={(e) => handleChange(setting.key, e.target.value)}
            placeholder={setting.placeholder}
          />
        )}
        {setting.description && (
          <p className="text-xs text-muted-foreground">{setting.description}</p>
        )}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Contact Settings</h1>
          <p className="text-muted-foreground">
            Manage contact information displayed on the storefront
          </p>
        </div>
        <Button onClick={handleSave} disabled={!hasChanges || updateMutation.isPending}>
          {updateMutation.isPending ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Save Changes
        </Button>
      </div>

      {/* Info Banner */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <p className="text-sm text-blue-800">
                These settings are displayed on the Contact page, Footer, and throughout the storefront.
                Changes will be visible after a few minutes due to caching.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="contact" className="space-y-4">
        <TabsList>
          <TabsTrigger value="contact">
            <Phone className="h-4 w-4 mr-2" />
            Contact Info
          </TabsTrigger>
          <TabsTrigger value="address">
            <MapPin className="h-4 w-4 mr-2" />
            Address
          </TabsTrigger>
          <TabsTrigger value="hours">
            <Clock className="h-4 w-4 mr-2" />
            Support Hours
          </TabsTrigger>
          <TabsTrigger value="social">
            <Globe className="h-4 w-4 mr-2" />
            Social Media
          </TabsTrigger>
        </TabsList>

        <TabsContent value="contact">
          <Card>
            <CardHeader>
              <CardTitle>Contact Numbers & Email</CardTitle>
              <CardDescription>
                Primary contact methods for customer support
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                {CONTACT_SETTINGS.filter((s) =>
                  ['contact_phone', 'contact_phone_toll_free', 'contact_whatsapp', 'contact_email', 'contact_email_sales'].includes(s.key)
                ).map(renderSettingField)}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="address">
          <Card>
            <CardHeader>
              <CardTitle>Office Address</CardTitle>
              <CardDescription>
                Corporate/Office address displayed on contact page and footer
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                {CONTACT_SETTINGS.filter((s) =>
                  ['contact_address', 'contact_city', 'contact_state', 'contact_pincode', 'contact_country', 'contact_google_maps_url'].includes(s.key)
                ).map(renderSettingField)}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="hours">
          <Card>
            <CardHeader>
              <CardTitle>Support Hours</CardTitle>
              <CardDescription>
                Customer support availability times
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                {CONTACT_SETTINGS.filter((s) =>
                  ['support_hours_weekday', 'support_hours_weekend', 'support_response_time'].includes(s.key)
                ).map(renderSettingField)}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="social">
          <Card>
            <CardHeader>
              <CardTitle>Social Media Links</CardTitle>
              <CardDescription>
                Social media profile URLs displayed in footer and contact page
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                {SOCIAL_SETTINGS.map(renderSettingField)}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Preview Section */}
      <Card>
        <CardHeader>
          <CardTitle>Preview</CardTitle>
          <CardDescription>
            How your contact information will appear on the storefront
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 mb-2">
                <Phone className="h-4 w-4 text-primary" />
                <span className="font-medium text-sm">Phone</span>
              </div>
              <p className="text-sm">{formValues.contact_phone || 'Not set'}</p>
              {formValues.contact_phone_toll_free && (
                <p className="text-xs text-muted-foreground">Toll-free: {formValues.contact_phone_toll_free}</p>
              )}
            </div>
            <div className="p-4 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 mb-2">
                <MessageCircle className="h-4 w-4 text-green-600" />
                <span className="font-medium text-sm">WhatsApp</span>
              </div>
              <p className="text-sm">{formValues.contact_whatsapp ? `+${formValues.contact_whatsapp}` : 'Not set'}</p>
            </div>
            <div className="p-4 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 mb-2">
                <Mail className="h-4 w-4 text-primary" />
                <span className="font-medium text-sm">Email</span>
              </div>
              <p className="text-sm">{formValues.contact_email || 'Not set'}</p>
            </div>
            <div className="p-4 rounded-lg bg-muted/50 md:col-span-2">
              <div className="flex items-center gap-2 mb-2">
                <MapPin className="h-4 w-4 text-primary" />
                <span className="font-medium text-sm">Address</span>
              </div>
              <p className="text-sm">
                {formValues.contact_address || 'Not set'}
                {formValues.contact_city && `, ${formValues.contact_city}`}
                {formValues.contact_state && `, ${formValues.contact_state}`}
                {formValues.contact_pincode && ` - ${formValues.contact_pincode}`}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="h-4 w-4 text-primary" />
                <span className="font-medium text-sm">Hours</span>
              </div>
              <p className="text-sm">{formValues.support_hours_weekday || 'Not set'}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
