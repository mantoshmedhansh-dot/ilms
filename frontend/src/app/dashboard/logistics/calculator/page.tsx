'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Calculator, Package, Truck, ArrowRight, Loader2,
  MapPin, Scale, Ruler, CreditCard, Tag, TrendingUp
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { PageHeader } from '@/components/common';
import { rateCardsApi } from '@/lib/api';
import { formatCurrency, cn } from '@/lib/utils';

interface CarrierQuote {
  transporter_id: string;
  transporter_code: string;
  transporter_name: string;
  rate_card_id: string;
  rate_card_code: string;
  segment: string;
  service_type: string;
  cost_breakdown: {
    base_rate: number;
    additional_weight_charge: number;
    fuel_surcharge: number;
    cod_charge: number;
    oda_charge: number;
    handling_charge: number;
    insurance: number;
    rto_risk_charge: number;
    gst: number;
    other_charges: number;
    total: number;
  };
  total_cost: number;
  estimated_delivery: {
    min_days: number;
    max_days: number;
  };
  zone: string;
  chargeable_weight_kg: number;
  performance_score: number | null;
  allocation_score: number;
  is_cod_available: boolean;
  is_serviceable: boolean;
  remarks?: string;
}

interface CalculationResult {
  segment: string;
  zone: string;
  chargeable_weight: number;
  quotes: CarrierQuote[];
  recommended: CarrierQuote | null;
  alternatives: CarrierQuote[];
  message?: string;
}

const strategies = [
  { value: 'BALANCED', label: 'Balanced (Cost + Speed + Performance)' },
  { value: 'CHEAPEST_FIRST', label: 'Cheapest First' },
  { value: 'FASTEST_FIRST', label: 'Fastest First' },
  { value: 'BEST_SLA', label: 'Best SLA Performance' },
];

export default function RateCalculatorPage() {
  const [formData, setFormData] = useState({
    origin_pincode: '',
    destination_pincode: '',
    weight_kg: 1,
    length_cm: 0,
    width_cm: 0,
    height_cm: 0,
    payment_mode: 'PREPAID' as 'PREPAID' | 'COD',
    order_value: 0,
    channel: 'D2C',
    is_fragile: false,
    num_packages: 1,
  });

  const [strategy, setStrategy] = useState('BALANCED');
  const [result, setResult] = useState<CalculationResult | null>(null);
  const [showDimensions, setShowDimensions] = useState(false);

  const calculateMutation = useMutation({
    mutationFn: async () => {
      const params: Parameters<typeof rateCardsApi.pricing.calculateRate>[0] = {
        origin_pincode: formData.origin_pincode,
        destination_pincode: formData.destination_pincode,
        weight_kg: formData.weight_kg,
        payment_mode: formData.payment_mode,
        order_value: formData.order_value,
        channel: formData.channel,
        is_fragile: formData.is_fragile,
        num_packages: formData.num_packages,
      };

      if (showDimensions && formData.length_cm && formData.width_cm && formData.height_cm) {
        params.length_cm = formData.length_cm;
        params.width_cm = formData.width_cm;
        params.height_cm = formData.height_cm;
      }

      return rateCardsApi.pricing.calculateRate(params);
    },
    onSuccess: (data) => {
      setResult(data);
      if (data.quotes?.length === 0) {
        toast.warning('No carriers available for this route');
      } else {
        toast.success(`Found ${data.quotes?.length || 0} carrier options`);
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to calculate rates');
    },
  });

  const handleCalculate = () => {
    if (!formData.origin_pincode || !formData.destination_pincode) {
      toast.error('Please enter origin and destination pincodes');
      return;
    }
    if (formData.weight_kg <= 0) {
      toast.error('Weight must be greater than 0');
      return;
    }
    calculateMutation.mutate();
  };

  const getSegmentColor = (segment: string) => {
    switch (segment) {
      case 'D2C': return 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200';
      case 'B2B': return 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200';
      case 'FTL': return 'bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-200';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getZoneColor = (zone: string) => {
    const colors: Record<string, string> = {
      'A': 'bg-green-100 text-green-800',
      'B': 'bg-emerald-100 text-emerald-800',
      'C': 'bg-yellow-100 text-yellow-800',
      'D': 'bg-orange-100 text-orange-800',
      'E': 'bg-red-100 text-red-800',
      'F': 'bg-rose-100 text-rose-800',
    };
    return colors[zone] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Rate Calculator"
        description="Calculate shipping rates and compare carriers for your shipments"
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Input Form */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calculator className="h-5 w-5" />
              Shipment Details
            </CardTitle>
            <CardDescription>
              Enter shipment details to calculate rates
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Origin & Destination */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Origin Pincode *</Label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    className="pl-9"
                    placeholder="400001"
                    maxLength={6}
                    value={formData.origin_pincode}
                    onChange={(e) => setFormData({ ...formData, origin_pincode: e.target.value })}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Destination Pincode *</Label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    className="pl-9"
                    placeholder="110001"
                    maxLength={6}
                    value={formData.destination_pincode}
                    onChange={(e) => setFormData({ ...formData, destination_pincode: e.target.value })}
                  />
                </div>
              </div>
            </div>

            {/* Weight */}
            <div className="space-y-2">
              <Label>Weight (kg) *</Label>
              <div className="relative">
                <Scale className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={formData.weight_kg}
                  onChange={(e) => setFormData({ ...formData, weight_kg: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>

            {/* Dimensions Toggle */}
            <div className="flex items-center justify-between">
              <Label>Include Dimensions</Label>
              <Switch
                checked={showDimensions}
                onCheckedChange={setShowDimensions}
              />
            </div>

            {showDimensions && (
              <div className="grid grid-cols-3 gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">Length (cm)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.length_cm || ''}
                    onChange={(e) => setFormData({ ...formData, length_cm: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Width (cm)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.width_cm || ''}
                    onChange={(e) => setFormData({ ...formData, width_cm: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Height (cm)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.height_cm || ''}
                    onChange={(e) => setFormData({ ...formData, height_cm: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>
            )}

            <Separator />

            {/* Payment Mode */}
            <div className="space-y-2">
              <Label>Payment Mode</Label>
              <Select
                value={formData.payment_mode}
                onValueChange={(value: 'PREPAID' | 'COD') => setFormData({ ...formData, payment_mode: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PREPAID">Prepaid</SelectItem>
                  <SelectItem value="COD">Cash on Delivery (COD)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Order Value */}
            <div className="space-y-2">
              <Label>Order Value (for COD/Insurance)</Label>
              <div className="relative">
                <CreditCard className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  type="number"
                  min="0"
                  value={formData.order_value || ''}
                  onChange={(e) => setFormData({ ...formData, order_value: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>

            {/* Number of Packages */}
            <div className="space-y-2">
              <Label>Number of Packages</Label>
              <Input
                type="number"
                min="1"
                value={formData.num_packages}
                onChange={(e) => setFormData({ ...formData, num_packages: parseInt(e.target.value) || 1 })}
              />
            </div>

            {/* Allocation Strategy */}
            <div className="space-y-2">
              <Label>Allocation Strategy</Label>
              <Select value={strategy} onValueChange={setStrategy}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {strategies.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              className="w-full"
              onClick={handleCalculate}
              disabled={calculateMutation.isPending}
            >
              {calculateMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Calculating...
                </>
              ) : (
                <>
                  <Calculator className="mr-2 h-4 w-4" />
                  Calculate Rates
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results */}
        <div className="lg:col-span-2 space-y-6">
          {result && (
            <>
              {/* Summary Card */}
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle>Shipment Analysis</CardTitle>
                    <div className="flex gap-2">
                      <Badge className={getSegmentColor(result.segment)}>
                        {result.segment}
                      </Badge>
                      {result.zone && (
                        <Badge className={getZoneColor(result.zone)}>
                          Zone {result.zone}
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1">
                      <MapPin className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{formData.origin_pincode}</span>
                      <ArrowRight className="h-4 w-4 text-muted-foreground mx-1" />
                      <span className="font-medium">{formData.destination_pincode}</span>
                    </div>
                    <Separator orientation="vertical" className="h-4" />
                    <div className="flex items-center gap-1">
                      <Scale className="h-4 w-4 text-muted-foreground" />
                      <span>Chargeable: <strong>{result.chargeable_weight} kg</strong></span>
                    </div>
                    <Separator orientation="vertical" className="h-4" />
                    <div>
                      <span className="text-muted-foreground">{result.quotes?.length || 0} carriers available</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Recommended Carrier */}
              {result.recommended && (
                <Card className="border-green-200 bg-green-50/50 dark:border-green-900 dark:bg-green-950/20">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2 text-green-700 dark:text-green-400">
                        <TrendingUp className="h-5 w-5" />
                        Recommended Carrier
                      </CardTitle>
                      <Badge variant="outline" className="text-green-700 border-green-300">
                        Score: {result.recommended.allocation_score}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900">
                          <Truck className="h-6 w-6 text-green-600" />
                        </div>
                        <div>
                          <h3 className="font-semibold">{result.recommended.transporter_name}</h3>
                          <p className="text-sm text-muted-foreground">
                            {result.recommended.rate_card_code} - {result.recommended.service_type}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-green-700 dark:text-green-400">
                          {formatCurrency(result.recommended.total_cost)}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {result.recommended.estimated_delivery.min_days}-{result.recommended.estimated_delivery.max_days} days
                        </p>
                      </div>
                    </div>

                    {/* Cost Breakdown */}
                    <Separator className="my-4" />
                    <div className="grid grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Base Rate</p>
                        <p className="font-medium">{formatCurrency(result.recommended.cost_breakdown.base_rate)}</p>
                      </div>
                      {result.recommended.cost_breakdown.fuel_surcharge > 0 && (
                        <div>
                          <p className="text-muted-foreground">Fuel Surcharge</p>
                          <p className="font-medium">{formatCurrency(result.recommended.cost_breakdown.fuel_surcharge)}</p>
                        </div>
                      )}
                      {result.recommended.cost_breakdown.cod_charge > 0 && (
                        <div>
                          <p className="text-muted-foreground">COD Charge</p>
                          <p className="font-medium">{formatCurrency(result.recommended.cost_breakdown.cod_charge)}</p>
                        </div>
                      )}
                      <div>
                        <p className="text-muted-foreground">GST (18%)</p>
                        <p className="font-medium">{formatCurrency(result.recommended.cost_breakdown.gst)}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* All Carriers */}
              {result.quotes && result.quotes.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>All Available Carriers</CardTitle>
                    <CardDescription>
                      Compare all carrier options sorted by {strategies.find(s => s.value === strategy)?.label}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {result.quotes.map((quote, index) => (
                        <div
                          key={`${quote.transporter_id}-${quote.rate_card_id}`}
                          className={cn(
                            "flex items-center justify-between p-4 rounded-lg border",
                            index === 0 && "border-green-200 bg-green-50/30 dark:border-green-900 dark:bg-green-950/10"
                          )}
                        >
                          <div className="flex items-center gap-4">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                              <Truck className="h-5 w-5 text-muted-foreground" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="font-medium">{quote.transporter_name}</h4>
                                {index === 0 && (
                                  <Badge variant="secondary" className="text-xs">Best Match</Badge>
                                )}
                              </div>
                              <p className="text-sm text-muted-foreground">
                                {quote.rate_card_code} - {quote.service_type}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-6">
                            <div className="text-center">
                              <p className="text-sm text-muted-foreground">Delivery</p>
                              <p className="font-medium">
                                {quote.estimated_delivery.min_days}-{quote.estimated_delivery.max_days} days
                              </p>
                            </div>
                            {quote.performance_score && (
                              <div className="text-center">
                                <p className="text-sm text-muted-foreground">Performance</p>
                                <p className="font-medium">{quote.performance_score.toFixed(1)}%</p>
                              </div>
                            )}
                            <div className="text-center">
                              <p className="text-sm text-muted-foreground">Score</p>
                              <p className="font-medium">{quote.allocation_score}</p>
                            </div>
                            <div className="text-right min-w-[100px]">
                              <p className="text-lg font-bold">{formatCurrency(quote.total_cost)}</p>
                              <p className="text-xs text-muted-foreground">incl. GST</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* No Results */}
              {(!result.quotes || result.quotes.length === 0) && (
                <Card>
                  <CardContent className="py-12 text-center">
                    <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <h3 className="text-lg font-medium">No Carriers Available</h3>
                    <p className="text-muted-foreground mt-2">
                      {result.message || 'No carriers found for this route. Please check your pincodes or try different parameters.'}
                    </p>
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {/* Initial State */}
          {!result && !calculateMutation.isPending && (
            <Card>
              <CardContent className="py-16 text-center">
                <Calculator className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-xl font-medium">Rate Calculator</h3>
                <p className="text-muted-foreground mt-2 max-w-md mx-auto">
                  Enter your shipment details to calculate shipping rates and compare carriers.
                  The system will automatically determine the segment (D2C, B2B, or FTL) based on weight.
                </p>
                <div className="mt-6 grid grid-cols-3 gap-4 max-w-md mx-auto text-sm">
                  <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950">
                    <p className="font-medium text-blue-700 dark:text-blue-300">D2C</p>
                    <p className="text-blue-600 dark:text-blue-400 text-xs">&lt; 30 kg</p>
                  </div>
                  <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-950">
                    <p className="font-medium text-purple-700 dark:text-purple-300">B2B (LTL)</p>
                    <p className="text-purple-600 dark:text-purple-400 text-xs">30 - 3000 kg</p>
                  </div>
                  <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-950">
                    <p className="font-medium text-orange-700 dark:text-orange-300">FTL</p>
                    <p className="text-orange-600 dark:text-orange-400 text-xs">&gt; 3000 kg</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
