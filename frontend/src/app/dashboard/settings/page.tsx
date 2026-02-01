'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Building2,
  FileText,
  MapPin,
  Landmark,
  Image,
  FileCheck,
  Settings,
  Save,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/common';
import { ImageUpload } from '@/components/upload';
import { companyApi } from '@/lib/api';
import {
  Company,
  CompanyType,
  GSTRegistrationType,
  companyTypeLabels,
  gstRegistrationTypeLabels,
  indianStates,
  msmeCategories,
  MSMECategory,
} from '@/types/company';
import { BankAccountsSection } from './components/bank-accounts-section';

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<Partial<Company>>({});
  const [hasChanges, setHasChanges] = useState(false);

  const { data: company, isLoading } = useQuery({
    queryKey: ['company-primary'],
    queryFn: companyApi.getPrimary,
  });

  useEffect(() => {
    if (company) {
      setFormData(company);
      setHasChanges(false);
    }
  }, [company]);

  const updateMutation = useMutation({
    mutationFn: companyApi.updatePrimary,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-primary'] });
      toast.success('Settings saved successfully');
      setHasChanges(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to save settings');
    },
  });

  const updateField = (field: keyof Company, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setHasChanges(true);
  };

  const handleSave = () => {
    updateMutation.mutate(formData);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Manage company configuration and preferences"
        actions={
          <Button onClick={handleSave} disabled={updateMutation.isPending || !hasChanges}>
            {updateMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        }
      />

      <Tabs defaultValue="company" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4 lg:grid-cols-7">
          <TabsTrigger value="company" className="gap-2">
            <Building2 className="h-4 w-4 hidden sm:inline" />
            <span>Company</span>
          </TabsTrigger>
          <TabsTrigger value="tax" className="gap-2">
            <FileText className="h-4 w-4 hidden sm:inline" />
            <span>Tax</span>
          </TabsTrigger>
          <TabsTrigger value="address" className="gap-2">
            <MapPin className="h-4 w-4 hidden sm:inline" />
            <span>Address</span>
          </TabsTrigger>
          <TabsTrigger value="bank" className="gap-2">
            <Landmark className="h-4 w-4 hidden sm:inline" />
            <span>Bank</span>
          </TabsTrigger>
          <TabsTrigger value="branding" className="gap-2">
            <Image className="h-4 w-4 hidden sm:inline" />
            <span>Branding</span>
          </TabsTrigger>
          <TabsTrigger value="einvoice" className="gap-2">
            <FileCheck className="h-4 w-4 hidden sm:inline" />
            <span>E-Invoice</span>
          </TabsTrigger>
          <TabsTrigger value="documents" className="gap-2">
            <Settings className="h-4 w-4 hidden sm:inline" />
            <span>Documents</span>
          </TabsTrigger>
        </TabsList>

        {/* Company Information Tab */}
        <TabsContent value="company">
          <Card>
            <CardHeader>
              <CardTitle>Company Information</CardTitle>
              <CardDescription>Basic company details and registration</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="legal_name">Legal Name *</Label>
                  <Input
                    id="legal_name"
                    value={formData.legal_name || ''}
                    onChange={(e) => updateField('legal_name', e.target.value)}
                    placeholder="As per registration"
                  />
                  <p className="text-xs text-muted-foreground">Legal name as per GST/MCA registration</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="trade_name">Trade Name / Brand</Label>
                  <Input
                    id="trade_name"
                    value={formData.trade_name || ''}
                    onChange={(e) => updateField('trade_name', e.target.value)}
                    placeholder="Brand or trade name"
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="code">Company Code *</Label>
                  <Input
                    id="code"
                    value={formData.code || ''}
                    onChange={(e) => updateField('code', e.target.value.toUpperCase())}
                    placeholder="e.g., AQUA"
                    maxLength={20}
                  />
                  <p className="text-xs text-muted-foreground">Short code for internal reference</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="company_type">Company Type</Label>
                  <Select
                    value={formData.company_type || 'PRIVATE_LIMITED'}
                    onValueChange={(value) => updateField('company_type', value as CompanyType)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(companyTypeLabels).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tax & Compliance Tab */}
        <TabsContent value="tax">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>GST Registration</CardTitle>
                <CardDescription>Goods and Services Tax details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="gstin">GSTIN *</Label>
                    <Input
                      id="gstin"
                      value={formData.gstin || ''}
                      onChange={(e) => updateField('gstin', e.target.value.toUpperCase())}
                      placeholder="27AAACT1234M1Z5"
                      maxLength={15}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="gst_registration_type">Registration Type</Label>
                    <Select
                      value={formData.gst_registration_type || 'REGULAR'}
                      onValueChange={(value) => updateField('gst_registration_type', value as GSTRegistrationType)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(gstRegistrationTypeLabels).map(([value, label]) => (
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="state_code">State Code</Label>
                  <Select
                    value={formData.state_code || ''}
                    onValueChange={(value) => updateField('state_code', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select state" />
                    </SelectTrigger>
                    <SelectContent>
                      {indianStates.map((state) => (
                        <SelectItem key={state.code} value={state.code}>
                          {state.code} - {state.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Other Tax Registrations</CardTitle>
                <CardDescription>PAN, TAN, CIN and other registrations</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="pan">PAN *</Label>
                    <Input
                      id="pan"
                      value={formData.pan || ''}
                      onChange={(e) => updateField('pan', e.target.value.toUpperCase())}
                      placeholder="AAACT1234M"
                      maxLength={10}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="tan">TAN (for TDS)</Label>
                    <Input
                      id="tan"
                      value={formData.tan || ''}
                      onChange={(e) => updateField('tan', e.target.value.toUpperCase())}
                      placeholder="MUMA12345A"
                      maxLength={10}
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="cin">CIN (Company ID)</Label>
                    <Input
                      id="cin"
                      value={formData.cin || ''}
                      onChange={(e) => updateField('cin', e.target.value.toUpperCase())}
                      placeholder="U12345MH2020PTC123456"
                      maxLength={21}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="llpin">LLPIN (for LLP)</Label>
                    <Input
                      id="llpin"
                      value={formData.llpin || ''}
                      onChange={(e) => updateField('llpin', e.target.value.toUpperCase())}
                      placeholder="AAA-1234"
                      maxLength={10}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>MSME Registration</CardTitle>
                <CardDescription>Udyam registration for micro, small and medium enterprises</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>MSME Registered</Label>
                    <p className="text-sm text-muted-foreground">Is your company registered under MSME?</p>
                  </div>
                  <Switch
                    checked={formData.msme_registered || false}
                    onCheckedChange={(checked) => updateField('msme_registered', checked)}
                  />
                </div>
                {formData.msme_registered && (
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="udyam_number">Udyam Number</Label>
                      <Input
                        id="udyam_number"
                        value={formData.udyam_number || ''}
                        onChange={(e) => updateField('udyam_number', e.target.value.toUpperCase())}
                        placeholder="UDYAM-MH-01-0012345"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="msme_category">MSME Category</Label>
                      <Select
                        value={formData.msme_category || ''}
                        onValueChange={(value) => updateField('msme_category', value as MSMECategory)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select category" />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(msmeCategories).map(([value, label]) => (
                            <SelectItem key={value} value={value}>
                              {label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Address & Contact Tab */}
        <TabsContent value="address">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Registered Address</CardTitle>
                <CardDescription>Primary business address</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="address_line1">Address Line 1 *</Label>
                  <Input
                    id="address_line1"
                    value={formData.address_line1 || ''}
                    onChange={(e) => updateField('address_line1', e.target.value)}
                    placeholder="Building, Street"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="address_line2">Address Line 2</Label>
                  <Input
                    id="address_line2"
                    value={formData.address_line2 || ''}
                    onChange={(e) => updateField('address_line2', e.target.value)}
                    placeholder="Area, Landmark"
                  />
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="city">City *</Label>
                    <Input
                      id="city"
                      value={formData.city || ''}
                      onChange={(e) => updateField('city', e.target.value)}
                      placeholder="Mumbai"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="district">District</Label>
                    <Input
                      id="district"
                      value={formData.district || ''}
                      onChange={(e) => updateField('district', e.target.value)}
                      placeholder="Mumbai Suburban"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="state">State *</Label>
                    <Input
                      id="state"
                      value={formData.state || ''}
                      onChange={(e) => updateField('state', e.target.value)}
                      placeholder="Maharashtra"
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="pincode">Pincode *</Label>
                    <Input
                      id="pincode"
                      value={formData.pincode || ''}
                      onChange={(e) => updateField('pincode', e.target.value)}
                      placeholder="400001"
                      maxLength={6}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="country">Country</Label>
                    <Input
                      id="country"
                      value={formData.country || 'India'}
                      onChange={(e) => updateField('country', e.target.value)}
                      placeholder="India"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Contact Details</CardTitle>
                <CardDescription>Phone, email and website</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email *</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.email || ''}
                      onChange={(e) => updateField('email', e.target.value)}
                      placeholder="info@company.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="website">Website</Label>
                    <Input
                      id="website"
                      value={formData.website || ''}
                      onChange={(e) => updateField('website', e.target.value)}
                      placeholder="https://www.company.com"
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone *</Label>
                    <Input
                      id="phone"
                      value={formData.phone || ''}
                      onChange={(e) => updateField('phone', e.target.value)}
                      placeholder="+91 22 12345678"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="mobile">Mobile</Label>
                    <Input
                      id="mobile"
                      value={formData.mobile || ''}
                      onChange={(e) => updateField('mobile', e.target.value)}
                      placeholder="+91 98765 43210"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="fax">Fax</Label>
                    <Input
                      id="fax"
                      value={formData.fax || ''}
                      onChange={(e) => updateField('fax', e.target.value)}
                      placeholder="+91 22 12345679"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Bank Accounts Tab */}
        <TabsContent value="bank">
          {company?.id ? (
            <BankAccountsSection companyId={company.id} />
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              Loading company data...
            </div>
          )}
        </TabsContent>

        {/* Branding Tab */}
        <TabsContent value="branding">
          <Card>
            <CardHeader>
              <CardTitle>Branding & Logo</CardTitle>
              <CardDescription>Company logo and signature for documents. Upload images or enter URLs.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                <ImageUpload
                  value={formData.logo_url}
                  onChange={(url) => updateField('logo_url', url || '')}
                  category="logos"
                  label="Company Logo"
                  description="Main logo for documents and website. Recommended: 200x60 px"
                  aspectRatio="logo"
                />
                <ImageUpload
                  value={formData.logo_small_url}
                  onChange={(url) => updateField('logo_small_url', url || '')}
                  category="logos"
                  label="Small Logo / Icon"
                  description="Icon version for mobile and tabs. Recommended: 64x64 px"
                  aspectRatio="square"
                />
              </div>
              <Separator />
              <div className="grid gap-6 md:grid-cols-2">
                <ImageUpload
                  value={formData.signature_url}
                  onChange={(url) => updateField('signature_url', url || '')}
                  category="signatures"
                  label="Authorized Signature"
                  description="Digital signature for invoices and documents"
                  aspectRatio="wide"
                />
                <ImageUpload
                  value={formData.favicon_url}
                  onChange={(url) => updateField('favicon_url', url || '')}
                  category="logos"
                  label="Favicon"
                  description="Browser tab icon. Recommended: 32x32 px"
                  aspectRatio="square"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* E-Invoice & E-Way Bill Tab */}
        <TabsContent value="einvoice">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>E-Invoice Configuration</CardTitle>
                <CardDescription>GST E-Invoice settings for B2B transactions</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Enable E-Invoice</Label>
                    <p className="text-sm text-muted-foreground">Generate IRN for B2B invoices via GST portal</p>
                  </div>
                  <Switch
                    checked={formData.einvoice_enabled || false}
                    onCheckedChange={(checked) => updateField('einvoice_enabled', checked)}
                  />
                </div>
                {formData.einvoice_enabled && (
                  <>
                    <Separator />
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="einvoice_username">E-Invoice Username</Label>
                        <Input
                          id="einvoice_username"
                          value={formData.einvoice_username || ''}
                          onChange={(e) => updateField('einvoice_username', e.target.value)}
                          placeholder="GST portal username"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="einvoice_api_mode">API Mode</Label>
                        <Select
                          value={formData.einvoice_api_mode || 'SANDBOX'}
                          onValueChange={(value) => updateField('einvoice_api_mode', value)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select mode" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="SANDBOX">Sandbox (Testing)</SelectItem>
                            <SelectItem value="PRODUCTION">Production</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>E-Way Bill Configuration</CardTitle>
                <CardDescription>E-Way bill settings for goods transportation</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Enable E-Way Bill</Label>
                    <p className="text-sm text-muted-foreground">Auto-generate E-Way bills for shipments above threshold</p>
                  </div>
                  <Switch
                    checked={formData.ewb_enabled || false}
                    onCheckedChange={(checked) => updateField('ewb_enabled', checked)}
                  />
                </div>
                {formData.ewb_enabled && (
                  <>
                    <Separator />
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="ewb_username">E-Way Bill Username</Label>
                        <Input
                          id="ewb_username"
                          value={formData.ewb_username || ''}
                          onChange={(e) => updateField('ewb_username', e.target.value)}
                          placeholder="E-Way bill portal username"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="ewb_api_mode">API Mode</Label>
                        <Select
                          value={formData.ewb_api_mode || 'SANDBOX'}
                          onValueChange={(value) => updateField('ewb_api_mode', value)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select mode" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="SANDBOX">Sandbox (Testing)</SelectItem>
                            <SelectItem value="PRODUCTION">Production</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Document Settings Tab */}
        <TabsContent value="documents">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Invoice Settings</CardTitle>
                <CardDescription>Invoice numbering and default text</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="invoice_prefix">Invoice Prefix</Label>
                    <Input
                      id="invoice_prefix"
                      value={formData.invoice_prefix || ''}
                      onChange={(e) => updateField('invoice_prefix', e.target.value.toUpperCase())}
                      placeholder="INV"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="invoice_suffix">Invoice Suffix</Label>
                    <Input
                      id="invoice_suffix"
                      value={formData.invoice_suffix || ''}
                      onChange={(e) => updateField('invoice_suffix', e.target.value)}
                      placeholder="Optional"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="financial_year_start_month">FY Start Month</Label>
                    <Select
                      value={String(formData.financial_year_start_month || 4)}
                      onValueChange={(value) => updateField('financial_year_start_month', parseInt(value))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select month" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">January</SelectItem>
                        <SelectItem value="4">April (India)</SelectItem>
                        <SelectItem value="7">July</SelectItem>
                        <SelectItem value="10">October</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="invoice_terms">Invoice Terms & Conditions</Label>
                  <Textarea
                    id="invoice_terms"
                    value={formData.invoice_terms || ''}
                    onChange={(e) => updateField('invoice_terms', e.target.value)}
                    placeholder="Payment terms, warranty, etc."
                    rows={4}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="invoice_notes">Invoice Notes</Label>
                  <Textarea
                    id="invoice_notes"
                    value={formData.invoice_notes || ''}
                    onChange={(e) => updateField('invoice_notes', e.target.value)}
                    placeholder="Additional notes to appear on invoices"
                    rows={2}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="invoice_footer">Invoice Footer</Label>
                  <Input
                    id="invoice_footer"
                    value={formData.invoice_footer || ''}
                    onChange={(e) => updateField('invoice_footer', e.target.value)}
                    placeholder="Footer text (e.g., Thank you for your business!)"
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Purchase Order Settings</CardTitle>
                <CardDescription>PO numbering and default terms</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="po_prefix">PO Prefix</Label>
                  <Input
                    id="po_prefix"
                    value={formData.po_prefix || ''}
                    onChange={(e) => updateField('po_prefix', e.target.value.toUpperCase())}
                    placeholder="PO"
                    className="max-w-xs"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="po_terms">PO Terms & Conditions</Label>
                  <Textarea
                    id="po_terms"
                    value={formData.po_terms || ''}
                    onChange={(e) => updateField('po_terms', e.target.value)}
                    placeholder="Default PO terms"
                    rows={4}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Tax Defaults</CardTitle>
                <CardDescription>Default tax rates for new transactions</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="currency_code">Currency</Label>
                    <Select
                      value={formData.currency_code || 'INR'}
                      onValueChange={(value) => updateField('currency_code', value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select currency" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="INR">INR - Indian Rupee</SelectItem>
                        <SelectItem value="USD">USD - US Dollar</SelectItem>
                        <SelectItem value="EUR">EUR - Euro</SelectItem>
                        <SelectItem value="GBP">GBP - British Pound</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="currency_symbol">Currency Symbol</Label>
                    <Input
                      id="currency_symbol"
                      value={formData.currency_symbol || ''}
                      onChange={(e) => updateField('currency_symbol', e.target.value)}
                      placeholder="₹"
                      className="max-w-20"
                    />
                  </div>
                </div>
                <Separator />
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="default_cgst_rate">Default CGST %</Label>
                    <Input
                      id="default_cgst_rate"
                      type="number"
                      step="0.01"
                      value={formData.default_cgst_rate || 9}
                      onChange={(e) => updateField('default_cgst_rate', parseFloat(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="default_sgst_rate">Default SGST %</Label>
                    <Input
                      id="default_sgst_rate"
                      type="number"
                      step="0.01"
                      value={formData.default_sgst_rate || 9}
                      onChange={(e) => updateField('default_sgst_rate', parseFloat(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="default_igst_rate">Default IGST %</Label>
                    <Input
                      id="default_igst_rate"
                      type="number"
                      step="0.01"
                      value={formData.default_igst_rate || 18}
                      onChange={(e) => updateField('default_igst_rate', parseFloat(e.target.value))}
                    />
                  </div>
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>TDS Deductor</Label>
                    <p className="text-sm text-muted-foreground">Company is liable to deduct TDS</p>
                  </div>
                  <Switch
                    checked={formData.tds_deductor || false}
                    onCheckedChange={(checked) => updateField('tds_deductor', checked)}
                  />
                </div>
                {formData.tds_deductor && (
                  <div className="space-y-2">
                    <Label htmlFor="default_tds_rate">Default TDS %</Label>
                    <Input
                      id="default_tds_rate"
                      type="number"
                      step="0.01"
                      value={formData.default_tds_rate || 10}
                      onChange={(e) => updateField('default_tds_rate', parseFloat(e.target.value))}
                      className="max-w-32"
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
