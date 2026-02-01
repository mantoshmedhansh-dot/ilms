'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Droplets,
  CheckCircle,
  AlertTriangle,
  ChevronRight,
  Loader2,
  MapPin,
  Home,
  Building,
  Factory,
  Users,
  Sparkles,
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
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/utils';

interface WaterQualityCalculatorProps {
  trigger?: React.ReactNode;
  className?: string;
}

// Water quality parameters
interface WaterProfile {
  tds: 'low' | 'medium' | 'high' | 'very_high';
  source: 'municipal' | 'borewell' | 'tanker' | 'mixed';
  usage: 'home_small' | 'home_medium' | 'home_large' | 'office' | 'commercial';
  concerns: string[];
}

// Product recommendations based on water profile
const productRecommendations: Record<string, {
  name: string;
  slug: string;
  price: number;
  image?: string;
  features: string[];
  reason: string;
  match: number;
}[]> = {
  'low_municipal_home_small': [
    {
      name: 'Aquapurite UV Basic',
      slug: 'aquapurite-uv-basic',
      price: 8999,
      features: ['UV Purification', '7L Storage', 'Low Maintenance'],
      reason: 'Municipal water with low TDS needs UV purification for microbiological safety.',
      match: 95,
    },
  ],
  'medium_borewell_home_medium': [
    {
      name: 'Aquapurite Optima RO+UV+UF',
      slug: 'aquapurite-optima-ro-uv-uf',
      price: 24999,
      features: ['7-Stage Purification', '10L Storage', 'Mineral Retention'],
      reason: 'Borewell water with moderate TDS benefits from RO+UV combination.',
      match: 92,
    },
  ],
  'high_borewell_home_large': [
    {
      name: 'Aquapurite Pro Max RO+UV+UF+TDS',
      slug: 'aquapurite-pro-max',
      price: 34999,
      features: ['9-Stage Purification', '12L Storage', 'TDS Controller', 'Copper+'],
      reason: 'High TDS borewell water requires advanced RO with TDS control.',
      match: 98,
    },
  ],
  'default': [
    {
      name: 'Aquapurite Optima RO+UV+UF',
      slug: 'aquapurite-optima-ro-uv-uf',
      price: 24999,
      features: ['7-Stage Purification', '10L Storage', 'Best Seller'],
      reason: 'Our most popular model suitable for most Indian water conditions.',
      match: 85,
    },
  ],
};

const tdsLevels = [
  { value: 'low', label: 'Below 200 TDS', description: 'Soft water (Municipal/Filtered)', icon: '💧' },
  { value: 'medium', label: '200-500 TDS', description: 'Moderate hardness', icon: '💦' },
  { value: 'high', label: '500-1000 TDS', description: 'Hard water', icon: '🌊' },
  { value: 'very_high', label: 'Above 1000 TDS', description: 'Very hard water', icon: '⚠️' },
];

const waterSources = [
  { value: 'municipal', label: 'Municipal/Corporation', description: 'Tap water from city supply', icon: Building },
  { value: 'borewell', label: 'Borewell/Tubewell', description: 'Groundwater', icon: Factory },
  { value: 'tanker', label: 'Tanker Water', description: 'External supply', icon: Droplets },
  { value: 'mixed', label: 'Mixed Sources', description: 'Multiple sources', icon: Users },
];

const usageTypes = [
  { value: 'home_small', label: '1-3 Members', description: 'Small family', liters: '10-15 L/day' },
  { value: 'home_medium', label: '4-6 Members', description: 'Medium family', liters: '15-25 L/day' },
  { value: 'home_large', label: '7+ Members', description: 'Large family/Joint', liters: '25-40 L/day' },
  { value: 'office', label: 'Small Office', description: '10-20 people', liters: '40-80 L/day' },
  { value: 'commercial', label: 'Commercial', description: 'Restaurant/Clinic', liters: '100+ L/day' },
];

const waterConcerns = [
  { id: 'taste', label: 'Bad taste or odor' },
  { id: 'hardness', label: 'Hard water / White deposits' },
  { id: 'contamination', label: 'Contamination concerns' },
  { id: 'health', label: 'Health issues from water' },
  { id: 'iron', label: 'Yellowish/Iron content' },
  { id: 'chlorine', label: 'Chlorine smell' },
];

export default function WaterQualityCalculator({
  trigger,
  className,
}: WaterQualityCalculatorProps) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<'tds' | 'source' | 'usage' | 'concerns' | 'result'>('tds');
  const [loading, setLoading] = useState(false);

  const [profile, setProfile] = useState<WaterProfile>({
    tds: 'medium',
    source: 'municipal',
    usage: 'home_medium',
    concerns: [],
  });

  const [recommendations, setRecommendations] = useState<typeof productRecommendations.default>([]);

  const toggleConcern = (concernId: string) => {
    setProfile((prev) => ({
      ...prev,
      concerns: prev.concerns.includes(concernId)
        ? prev.concerns.filter((c) => c !== concernId)
        : [...prev.concerns, concernId],
    }));
  };

  const calculateRecommendations = async () => {
    setLoading(true);

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // Get recommendations based on profile
    const key = `${profile.tds}_${profile.source}_${profile.usage}`;
    const recs = productRecommendations[key] || productRecommendations.default;

    setRecommendations(recs);
    setStep('result');
    setLoading(false);
  };

  const resetCalculator = () => {
    setStep('tds');
    setProfile({
      tds: 'medium',
      source: 'municipal',
      usage: 'home_medium',
      concerns: [],
    });
    setRecommendations([]);
  };

  const getProgress = () => {
    switch (step) {
      case 'tds': return 25;
      case 'source': return 50;
      case 'usage': return 75;
      case 'concerns': return 90;
      case 'result': return 100;
      default: return 0;
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" className={cn('gap-2', className)}>
            <Droplets className="h-4 w-4" />
            Find Your Purifier
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Droplets className="h-5 w-5 text-primary" />
            Water Quality Calculator
          </DialogTitle>
          <DialogDescription>
            Answer a few questions to find the perfect water purifier for your needs.
          </DialogDescription>
        </DialogHeader>

        {/* Progress bar */}
        {step !== 'result' && (
          <div className="mb-4">
            <Progress value={getProgress()} className="h-2" />
            <p className="text-xs text-muted-foreground mt-1 text-right">
              Step {['tds', 'source', 'usage', 'concerns'].indexOf(step) + 1} of 4
            </p>
          </div>
        )}

        {/* Step 1: TDS Level */}
        {step === 'tds' && (
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-base font-medium">What is your water TDS level?</Label>
              <p className="text-sm text-muted-foreground mt-1">
                TDS (Total Dissolved Solids) indicates water hardness. Check your water bill or use a TDS meter.
              </p>
            </div>
            <RadioGroup
              value={profile.tds}
              onValueChange={(value) => setProfile({ ...profile, tds: value as WaterProfile['tds'] })}
              className="grid gap-3"
            >
              {tdsLevels.map((level) => (
                <div key={level.value}>
                  <RadioGroupItem value={level.value} id={`tds-${level.value}`} className="peer sr-only" />
                  <Label
                    htmlFor={`tds-${level.value}`}
                    className={cn(
                      'flex items-center gap-3 p-4 border-2 rounded-lg cursor-pointer transition-colors',
                      'peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5',
                      'hover:bg-muted/50'
                    )}
                  >
                    <span className="text-2xl">{level.icon}</span>
                    <div className="flex-1">
                      <span className="font-medium">{level.label}</span>
                      <p className="text-sm text-muted-foreground">{level.description}</p>
                    </div>
                  </Label>
                </div>
              ))}
            </RadioGroup>
            <Button className="w-full" onClick={() => setStep('source')}>
              Continue
              <ChevronRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        )}

        {/* Step 2: Water Source */}
        {step === 'source' && (
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-base font-medium">What is your primary water source?</Label>
              <p className="text-sm text-muted-foreground mt-1">
                Different sources have different contamination profiles.
              </p>
            </div>
            <RadioGroup
              value={profile.source}
              onValueChange={(value) => setProfile({ ...profile, source: value as WaterProfile['source'] })}
              className="grid grid-cols-2 gap-3"
            >
              {waterSources.map((source) => {
                const Icon = source.icon;
                return (
                  <div key={source.value}>
                    <RadioGroupItem value={source.value} id={`source-${source.value}`} className="peer sr-only" />
                    <Label
                      htmlFor={`source-${source.value}`}
                      className={cn(
                        'flex flex-col items-center gap-2 p-4 border-2 rounded-lg cursor-pointer transition-colors text-center',
                        'peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5',
                        'hover:bg-muted/50'
                      )}
                    >
                      <Icon className="h-6 w-6 text-primary" />
                      <span className="font-medium text-sm">{source.label}</span>
                      <span className="text-xs text-muted-foreground">{source.description}</span>
                    </Label>
                  </div>
                );
              })}
            </RadioGroup>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep('tds')} className="flex-1">
                Back
              </Button>
              <Button className="flex-1" onClick={() => setStep('usage')}>
                Continue
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Usage */}
        {step === 'usage' && (
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-base font-medium">How many people will use this purifier?</Label>
              <p className="text-sm text-muted-foreground mt-1">
                This helps us recommend the right storage capacity.
              </p>
            </div>
            <RadioGroup
              value={profile.usage}
              onValueChange={(value) => setProfile({ ...profile, usage: value as WaterProfile['usage'] })}
              className="grid gap-3"
            >
              {usageTypes.map((usage) => (
                <div key={usage.value}>
                  <RadioGroupItem value={usage.value} id={`usage-${usage.value}`} className="peer sr-only" />
                  <Label
                    htmlFor={`usage-${usage.value}`}
                    className={cn(
                      'flex items-center justify-between p-4 border-2 rounded-lg cursor-pointer transition-colors',
                      'peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5',
                      'hover:bg-muted/50'
                    )}
                  >
                    <div>
                      <span className="font-medium">{usage.label}</span>
                      <p className="text-sm text-muted-foreground">{usage.description}</p>
                    </div>
                    <Badge variant="secondary">{usage.liters}</Badge>
                  </Label>
                </div>
              ))}
            </RadioGroup>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep('source')} className="flex-1">
                Back
              </Button>
              <Button className="flex-1" onClick={() => setStep('concerns')}>
                Continue
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 4: Concerns */}
        {step === 'concerns' && (
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-base font-medium">Any specific water concerns? (Optional)</Label>
              <p className="text-sm text-muted-foreground mt-1">
                Select all that apply to get better recommendations.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {waterConcerns.map((concern) => (
                <button
                  key={concern.id}
                  onClick={() => toggleConcern(concern.id)}
                  className={cn(
                    'p-3 border-2 rounded-lg text-left text-sm transition-colors',
                    profile.concerns.includes(concern.id)
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted/50'
                  )}
                >
                  {profile.concerns.includes(concern.id) && (
                    <CheckCircle className="h-4 w-4 text-primary inline mr-2" />
                  )}
                  {concern.label}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep('usage')} className="flex-1">
                Back
              </Button>
              <Button className="flex-1" onClick={calculateRecommendations} disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    Get Recommendations
                    <Sparkles className="h-4 w-4 ml-2" />
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* Result */}
        {step === 'result' && (
          <div className="space-y-4 py-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                <div>
                  <p className="font-medium text-green-800">Analysis Complete!</p>
                  <p className="text-sm text-green-700 mt-1">
                    Based on your water profile, we recommend the following purifiers:
                  </p>
                </div>
              </div>
            </div>

            {/* Recommendations */}
            <div className="space-y-3">
              {recommendations.map((product, index) => (
                <div
                  key={index}
                  className={cn(
                    'border rounded-lg p-4',
                    index === 0 && 'border-primary bg-primary/5'
                  )}
                >
                  {index === 0 && (
                    <Badge className="mb-2 bg-primary">Best Match</Badge>
                  )}
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="font-semibold">{product.name}</h4>
                      <p className="text-lg font-bold text-primary">
                        {formatCurrency(product.price)}
                      </p>
                    </div>
                    <div className="text-right">
                      <Badge variant="secondary" className="text-xs">
                        {product.match}% Match
                      </Badge>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">
                    {product.reason}
                  </p>
                  <div className="flex flex-wrap gap-1 mb-3">
                    {product.features.map((feature) => (
                      <Badge key={feature} variant="outline" className="text-xs">
                        {feature}
                      </Badge>
                    ))}
                  </div>
                  <Link href={`/products/${product.slug}`}>
                    <Button size="sm" className="w-full" onClick={() => setOpen(false)}>
                      View Product
                      <ChevronRight className="h-4 w-4 ml-2" />
                    </Button>
                  </Link>
                </div>
              ))}
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={resetCalculator} className="flex-1">
                Start Over
              </Button>
              <Link href="/products" className="flex-1">
                <Button variant="secondary" className="w-full" onClick={() => setOpen(false)}>
                  Browse All Products
                </Button>
              </Link>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// Banner component for homepage
export function WaterQualityBanner({ className }: { className?: string }) {
  return (
    <div className={cn('bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200 rounded-xl p-6', className)}>
      <div className="flex flex-col md:flex-row items-center gap-4 md:gap-6">
        <div className="p-4 bg-blue-100 rounded-full">
          <Droplets className="h-8 w-8 text-blue-600" />
        </div>
        <div className="flex-1 text-center md:text-left">
          <h3 className="text-lg font-semibold text-blue-900">Not sure which purifier to buy?</h3>
          <p className="text-sm text-blue-700 mt-1">
            Answer 4 quick questions and we&apos;ll recommend the perfect water purifier for your home.
          </p>
        </div>
        <WaterQualityCalculator
          trigger={
            <Button className="bg-blue-600 hover:bg-blue-700">
              Find My Purifier
              <ChevronRight className="h-4 w-4 ml-2" />
            </Button>
          }
        />
      </div>
    </div>
  );
}
