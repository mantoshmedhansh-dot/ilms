'use client';

import { useState } from 'react';
import {
  ArrowRightLeft,
  CheckCircle,
  IndianRupee,
  Droplets,
  Calendar,
  AlertCircle,
  ChevronRight,
  X,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/utils';
import { exchangeApi } from '@/lib/storefront/api';

interface ExchangeCalculatorProps {
  newProductPrice?: number;
  newProductName?: string;
  onExchangeValueCalculated?: (value: number) => void;
  trigger?: React.ReactNode;
  className?: string;
}

// Exchange value calculation based on brand and age
const brandValues: Record<string, number> = {
  'aquaguard': 2000,
  'kent': 1800,
  'pureit': 1500,
  'livpure': 1400,
  'eureka_forbes': 1800,
  'blue_star': 1600,
  'ao_smith': 1700,
  'aquapurite': 2000,
  'other': 1000,
};

const conditionMultipliers: Record<string, number> = {
  'excellent': 1.0,
  'good': 0.8,
  'fair': 0.6,
  'poor': 0.4,
};

const ageMultipliers: Record<string, number> = {
  '0-1': 1.0,
  '1-2': 0.85,
  '2-3': 0.7,
  '3-5': 0.5,
  '5+': 0.3,
};

export default function ExchangeCalculator({
  newProductPrice,
  newProductName,
  onExchangeValueCalculated,
  trigger,
  className,
}: ExchangeCalculatorProps) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<'details' | 'result'>('details');
  const [loading, setLoading] = useState(false);

  const [brand, setBrand] = useState('');
  const [age, setAge] = useState('');
  const [condition, setCondition] = useState('');
  const [purifierType, setPurifierType] = useState('');

  const [exchangeValue, setExchangeValue] = useState(0);

  // Helper to convert age range to years for API
  const parseAgeToYears = (ageRange: string): number => {
    switch (ageRange) {
      case '0-1': return 0.5;
      case '1-2': return 1.5;
      case '2-3': return 2.5;
      case '3-5': return 4;
      case '5+': return 6;
      default: return 3;
    }
  };

  const calculateExchangeValue = async () => {
    if (!brand || !age || !condition) return;

    setLoading(true);
    try {
      // Call the exchange API
      const result = await exchangeApi.calculateValue({
        brand,
        age_years: parseAgeToYears(age),
        condition: condition as 'excellent' | 'good' | 'fair' | 'poor',
        purifier_type: purifierType || undefined,
      });

      setExchangeValue(result.estimated_value);
      onExchangeValueCalculated?.(result.estimated_value);
      setStep('result');
    } catch (error) {
      console.error('Failed to calculate exchange value:', error);
      // Fallback to client-side calculation if API fails
      const baseValue = brandValues[brand] || 1000;
      const ageMultiplier = ageMultipliers[age] || 0.5;
      const conditionMultiplier = conditionMultipliers[condition] || 0.5;

      let value = Math.round(baseValue * ageMultiplier * conditionMultiplier);
      value = Math.max(value, 500);
      value = Math.min(value, 2000);

      setExchangeValue(value);
      onExchangeValueCalculated?.(value);
      setStep('result');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setStep('details');
    setLoading(false);
    setBrand('');
    setAge('');
    setCondition('');
    setPurifierType('');
    setExchangeValue(0);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" className={cn('gap-2', className)}>
            <ArrowRightLeft className="h-4 w-4" />
            Exchange Old Purifier
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowRightLeft className="h-5 w-5 text-primary" />
            Exchange Your Old Purifier
          </DialogTitle>
          <DialogDescription>
            Get up to ₹2,000 off when you exchange your old water purifier.
          </DialogDescription>
        </DialogHeader>

        {/* Details Step */}
        {step === 'details' && (
          <div className="space-y-5 py-4">
            {/* Benefits Banner */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                <div>
                  <p className="font-medium text-green-800">Exchange Benefits</p>
                  <ul className="text-sm text-green-700 mt-1 space-y-1">
                    <li>• Up to ₹2,000 exchange value</li>
                    <li>• Free pickup of old purifier</li>
                    <li>• Instant discount on new purchase</li>
                    <li>• Any brand accepted</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Form */}
            <div className="space-y-4">
              {/* Brand */}
              <div>
                <Label>Brand of your old purifier *</Label>
                <Select value={brand} onValueChange={setBrand}>
                  <SelectTrigger className="mt-1.5">
                    <SelectValue placeholder="Select brand" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="aquaguard">Aquaguard</SelectItem>
                    <SelectItem value="kent">Kent</SelectItem>
                    <SelectItem value="pureit">Pureit (HUL)</SelectItem>
                    <SelectItem value="livpure">Livpure</SelectItem>
                    <SelectItem value="eureka_forbes">Eureka Forbes</SelectItem>
                    <SelectItem value="blue_star">Blue Star</SelectItem>
                    <SelectItem value="ao_smith">A.O. Smith</SelectItem>
                    <SelectItem value="aquapurite">Aquapurite</SelectItem>
                    <SelectItem value="other">Other Brand</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Type */}
              <div>
                <Label>Type of purifier</Label>
                <Select value={purifierType} onValueChange={setPurifierType}>
                  <SelectTrigger className="mt-1.5">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ro">RO</SelectItem>
                    <SelectItem value="ro_uv">RO + UV</SelectItem>
                    <SelectItem value="ro_uv_uf">RO + UV + UF</SelectItem>
                    <SelectItem value="uv">UV Only</SelectItem>
                    <SelectItem value="gravity">Gravity Based</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Age */}
              <div>
                <Label>Age of purifier *</Label>
                <RadioGroup value={age} onValueChange={setAge} className="mt-2">
                  <div className="grid grid-cols-5 gap-2">
                    {[
                      { value: '0-1', label: '<1 yr' },
                      { value: '1-2', label: '1-2 yrs' },
                      { value: '2-3', label: '2-3 yrs' },
                      { value: '3-5', label: '3-5 yrs' },
                      { value: '5+', label: '5+ yrs' },
                    ].map((option) => (
                      <div key={option.value}>
                        <RadioGroupItem
                          value={option.value}
                          id={`age-${option.value}`}
                          className="peer sr-only"
                        />
                        <Label
                          htmlFor={`age-${option.value}`}
                          className={cn(
                            'flex items-center justify-center p-2 border rounded-lg cursor-pointer text-sm transition-colors',
                            'peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/10'
                          )}
                        >
                          {option.label}
                        </Label>
                      </div>
                    ))}
                  </div>
                </RadioGroup>
              </div>

              {/* Condition */}
              <div>
                <Label>Working condition *</Label>
                <RadioGroup value={condition} onValueChange={setCondition} className="mt-2">
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { value: 'excellent', label: 'Excellent', desc: 'Working perfectly' },
                      { value: 'good', label: 'Good', desc: 'Minor issues' },
                      { value: 'fair', label: 'Fair', desc: 'Needs repair' },
                      { value: 'poor', label: 'Poor', desc: 'Not working' },
                    ].map((option) => (
                      <div key={option.value}>
                        <RadioGroupItem
                          value={option.value}
                          id={`condition-${option.value}`}
                          className="peer sr-only"
                        />
                        <Label
                          htmlFor={`condition-${option.value}`}
                          className={cn(
                            'flex flex-col p-3 border rounded-lg cursor-pointer transition-colors',
                            'peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/10'
                          )}
                        >
                          <span className="font-medium">{option.label}</span>
                          <span className="text-xs text-muted-foreground">{option.desc}</span>
                        </Label>
                      </div>
                    ))}
                  </div>
                </RadioGroup>
              </div>
            </div>

            <Button
              className="w-full"
              onClick={calculateExchangeValue}
              disabled={loading || !brand || !age || !condition}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Calculating...
                </>
              ) : (
                <>
                  Calculate Exchange Value
                  <ChevronRight className="h-4 w-4 ml-2" />
                </>
              )}
            </Button>
          </div>
        )}

        {/* Result Step */}
        {step === 'result' && (
          <div className="space-y-5 py-4">
            {/* Exchange Value Card */}
            <div className="bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 rounded-xl p-6 text-center">
              <p className="text-sm text-muted-foreground mb-2">Your Exchange Value</p>
              <div className="text-4xl font-bold text-primary mb-2">
                {formatCurrency(exchangeValue)}
              </div>
              <Badge className="bg-green-100 text-green-800">
                Instant discount on checkout
              </Badge>
            </div>

            {/* Summary */}
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Brand</span>
                <span className="font-medium capitalize">{brand.replace('_', ' ')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Age</span>
                <span className="font-medium">{age} years</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Condition</span>
                <span className="font-medium capitalize">{condition}</span>
              </div>
            </div>

            {/* New Product Price */}
            {newProductPrice && (
              <>
                <Separator />
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{newProductName || 'New Purifier'}</span>
                    <span>{formatCurrency(newProductPrice)}</span>
                  </div>
                  <div className="flex justify-between text-sm text-green-600">
                    <span>Exchange Discount</span>
                    <span>-{formatCurrency(exchangeValue)}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between font-semibold">
                    <span>You Pay</span>
                    <span className="text-primary text-lg">
                      {formatCurrency(newProductPrice - exchangeValue)}
                    </span>
                  </div>
                </div>
              </>
            )}

            {/* Terms */}
            <div className="bg-muted/50 rounded-lg p-3 text-xs text-muted-foreground">
              <p className="font-medium text-foreground mb-1">Exchange Terms:</p>
              <ul className="space-y-1">
                <li>• Old purifier will be picked up at the time of new purifier installation</li>
                <li>• Exchange value is subject to physical verification</li>
                <li>• Exchange offer cannot be combined with other discounts</li>
              </ul>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={resetForm} className="flex-1">
                Recalculate
              </Button>
              <Button onClick={() => setOpen(false)} className="flex-1">
                Apply Exchange
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// Compact inline version for product pages
interface ExchangeBannerProps {
  className?: string;
  newProductPrice?: number;
  newProductName?: string;
}

export function ExchangeBanner({ className, newProductPrice, newProductName }: ExchangeBannerProps) {
  return (
    <div className={cn('bg-amber-50 border border-amber-200 rounded-lg p-4', className)}>
      <div className="flex items-center gap-3">
        <div className="p-2 bg-amber-100 rounded-full">
          <ArrowRightLeft className="h-5 w-5 text-amber-700" />
        </div>
        <div className="flex-1">
          <p className="font-medium text-amber-900">Exchange & Save up to ₹2,000</p>
          <p className="text-sm text-amber-700">Trade in your old purifier for instant discount</p>
        </div>
        <ExchangeCalculator
          newProductPrice={newProductPrice}
          newProductName={newProductName}
          trigger={
            <Button size="sm" variant="outline" className="border-amber-300 text-amber-800 hover:bg-amber-100">
              Calculate
            </Button>
          }
        />
      </div>
    </div>
  );
}
