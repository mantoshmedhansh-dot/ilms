'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Shield,
  Check,
  ChevronRight,
  Calendar,
  Wrench,
  Package,
  Loader2,
  Star,
  AlertCircle,
  CheckCircle,
  Phone,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { useIsAuthenticated } from '@/lib/storefront/auth-store';
import { formatCurrency } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { amcApi, deviceApi, AMCPlan as APIPlan, AMCContract } from '@/lib/storefront/api';

// Types
interface AMCPlan {
  id: string;
  name: string;
  duration_months: number;
  price: number;
  original_price?: number;
  features: string[];
  is_popular?: boolean;
  service_visits: number;
  filter_discount: number;
  priority_support: boolean;
}

interface ActiveAMC {
  id: string;
  plan_name: string;
  device_name: string;
  device_serial: string;
  start_date: string;
  end_date: string;
  status: 'active' | 'expired' | 'expiring_soon';
  visits_used: number;
  visits_total: number;
  next_service_date?: string;
}

// Default AMC Plans (fallback if API doesn't return plans)
const defaultPlans: AMCPlan[] = [
  {
    id: 'basic',
    name: 'Basic Care',
    duration_months: 12,
    price: 1999,
    original_price: 2499,
    service_visits: 2,
    filter_discount: 10,
    priority_support: false,
    features: [
      '2 preventive maintenance visits',
      '10% discount on spare parts',
      'Phone support during business hours',
      'Standard response time (48 hours)',
    ],
  },
  {
    id: 'standard',
    name: 'Standard Care',
    duration_months: 12,
    price: 2999,
    original_price: 3999,
    service_visits: 4,
    filter_discount: 15,
    priority_support: true,
    is_popular: true,
    features: [
      '4 preventive maintenance visits',
      '15% discount on spare parts',
      'Priority phone & WhatsApp support',
      '24-hour response time',
      'Free labor charges',
      'Annual water quality check',
    ],
  },
  {
    id: 'premium',
    name: 'Premium Care',
    duration_months: 12,
    price: 4999,
    original_price: 6499,
    service_visits: 6,
    filter_discount: 25,
    priority_support: true,
    features: [
      'Unlimited service visits',
      '25% discount on spare parts',
      '24/7 priority support',
      'Same-day response',
      'Free labor charges',
      'Bi-annual water quality check',
      '1 free filter replacement',
      'Extended warranty coverage',
    ],
  },
];

export default function AMCPage() {
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();
  const [activeAMCs, setActiveAMCs] = useState<ActiveAMC[]>([]);
  const [amcPlans, setAmcPlans] = useState<AMCPlan[]>(defaultPlans);
  const [devices, setDevices] = useState<{ id: string; name: string; serial: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [showBuyDialog, setShowBuyDialog] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<AMCPlan | null>(null);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [purchasing, setPurchasing] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/account/login?redirect=/account/amc');
      return;
    }

    const fetchData = async () => {
      try {
        // Fetch AMC plans, active contracts, and devices in parallel
        const [plansData, contractsData, devicesData] = await Promise.all([
          amcApi.getPlans().catch(() => []),
          amcApi.getMyContracts().catch(() => []),
          deviceApi.getMyDevices().catch(() => []),
        ]);

        // Transform plans from API
        if (plansData && plansData.length > 0) {
          const transformedPlans: AMCPlan[] = plansData.map((plan: APIPlan, index: number) => ({
            id: plan.id,
            name: plan.name,
            duration_months: plan.duration_months,
            price: plan.base_price,
            original_price: plan.base_price * 1.25, // Assume 20% discount
            service_visits: plan.services_included,
            filter_discount: plan.discount_on_parts,
            priority_support: plan.priority_support,
            is_popular: index === 1, // Mark middle plan as popular
            features: generateFeatures(plan),
          }));
          setAmcPlans(transformedPlans);
        }

        // Transform contracts to active AMCs
        const transformedAMCs: ActiveAMC[] = contractsData.map((contract: AMCContract) => {
          const endDate = new Date(contract.end_date);
          const now = new Date();
          const daysRemaining = Math.floor((endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

          let status: ActiveAMC['status'] = 'active';
          if (daysRemaining < 0) status = 'expired';
          else if (daysRemaining <= 30) status = 'expiring_soon';

          return {
            id: contract.id,
            plan_name: contract.plan_name,
            device_name: contract.product_name,
            device_serial: contract.serial_number,
            start_date: contract.start_date,
            end_date: contract.end_date,
            status,
            visits_used: contract.services_used,
            visits_total: contract.total_services,
            next_service_date: contract.next_service_due,
          };
        });
        setActiveAMCs(transformedAMCs);

        // Transform devices for selection
        const deviceOptions = devicesData.map((device) => ({
          id: device.serial_number,
          name: device.product_name,
          serial: device.serial_number,
        }));
        setDevices(deviceOptions);
      } catch (error) {
        console.error('Failed to load AMC data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [isAuthenticated, router]);

  // Helper to generate features from plan
  function generateFeatures(plan: APIPlan): string[] {
    const features: string[] = [];
    features.push(`${plan.services_included === 99 ? 'Unlimited' : plan.services_included} preventive maintenance visits`);
    if (plan.discount_on_parts > 0) features.push(`${plan.discount_on_parts}% discount on spare parts`);
    if (plan.priority_support) features.push('Priority phone & WhatsApp support');
    if (plan.emergency_support) features.push('24/7 emergency support');
    if (plan.labor_covered) features.push('Free labor charges');
    if (plan.parts_covered) features.push('Parts covered under plan');
    if (plan.description) features.push(plan.description);
    return features;
  }

  const handleBuyPlan = (plan: AMCPlan) => {
    setSelectedPlan(plan);
    setShowBuyDialog(true);
  };

  const handlePurchase = async () => {
    if (!selectedDevice || !selectedPlan) {
      toast.error('Please select a device');
      return;
    }

    setPurchasing(true);
    try {
      const result = await amcApi.purchasePlan(selectedPlan.id, selectedDevice);
      toast.success(result.message || 'AMC plan purchased successfully!');
      setShowBuyDialog(false);
      setSelectedPlan(null);
      setSelectedDevice('');

      // Refresh the active AMCs list
      const contractsData = await amcApi.getMyContracts();
      const transformedAMCs: ActiveAMC[] = contractsData.map((contract: AMCContract) => {
        const endDate = new Date(contract.end_date);
        const now = new Date();
        const daysRemaining = Math.floor((endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

        let status: ActiveAMC['status'] = 'active';
        if (daysRemaining < 0) status = 'expired';
        else if (daysRemaining <= 30) status = 'expiring_soon';

        return {
          id: contract.id,
          plan_name: contract.plan_name,
          device_name: contract.product_name,
          device_serial: contract.serial_number,
          start_date: contract.start_date,
          end_date: contract.end_date,
          status,
          visits_used: contract.services_used,
          visits_total: contract.total_services,
          next_service_date: contract.next_service_due,
        };
      });
      setActiveAMCs(transformedAMCs);
    } catch (error) {
      console.error('Failed to purchase plan:', error);
      toast.error('Failed to purchase plan. Please try again.');
    } finally {
      setPurchasing(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-green-100 text-green-800">Active</Badge>;
      case 'expiring_soon':
        return <Badge className="bg-yellow-100 text-yellow-800">Expiring Soon</Badge>;
      case 'expired':
        return <Badge className="bg-red-100 text-red-800">Expired</Badge>;
      default:
        return null;
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-2xl md:text-3xl font-bold">Annual Maintenance Contracts</h1>
        <p className="text-muted-foreground mt-2 max-w-2xl mx-auto">
          Keep your water purifier running at peak performance with our comprehensive maintenance plans.
        </p>
      </div>

      {/* Active AMCs */}
      {activeAMCs.length > 0 && (
        <div className="mb-12">
          <h2 className="text-xl font-semibold mb-4">Your Active Plans</h2>
          <div className="space-y-4">
            {activeAMCs.map((amc) => (
              <Card key={amc.id}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Shield className="h-5 w-5 text-primary" />
                        <span className="font-semibold">{amc.plan_name}</span>
                        {getStatusBadge(amc.status)}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {amc.device_name} ({amc.device_serial})
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">Valid Until</p>
                      <p className="font-medium">
                        {new Date(amc.end_date).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-6 text-sm">
                    <div>
                      <span className="text-muted-foreground">Visits Used:</span>
                      <span className="ml-2 font-medium">
                        {amc.visits_used}/{amc.visits_total}
                      </span>
                    </div>
                    {amc.next_service_date && (
                      <div>
                        <span className="text-muted-foreground">Next Service:</span>
                        <span className="ml-2 font-medium">
                          {new Date(amc.next_service_date).toLocaleDateString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                          })}
                        </span>
                      </div>
                    )}
                  </div>

                  {amc.status === 'expiring_soon' && (
                    <div className="mt-4 pt-4 border-t">
                      <Button size="sm">Renew Now</Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* AMC Plans */}
      <div>
        <h2 className="text-xl font-semibold mb-4 text-center">Choose Your Plan</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {amcPlans.map((plan) => (
            <Card
              key={plan.id}
              className={cn(
                'relative overflow-hidden',
                plan.is_popular && 'border-primary shadow-lg'
              )}
            >
              {plan.is_popular && (
                <div className="absolute top-0 right-0 bg-primary text-primary-foreground text-xs px-3 py-1 rounded-bl-lg font-medium">
                  Most Popular
                </div>
              )}
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  {plan.name}
                </CardTitle>
                <CardDescription>
                  {plan.duration_months} months coverage
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Price */}
                <div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold">{formatCurrency(plan.price)}</span>
                    {plan.original_price && (
                      <span className="text-muted-foreground line-through text-sm">
                        {formatCurrency(plan.original_price)}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {formatCurrency(Math.round(plan.price / 12))}/month
                  </p>
                </div>

                {/* Highlights */}
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <Wrench className="h-4 w-4 text-primary" />
                    <span>
                      {plan.service_visits === 99 ? 'Unlimited' : plan.service_visits} visits
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Package className="h-4 w-4 text-primary" />
                    <span>{plan.filter_discount}% off parts</span>
                  </div>
                </div>

                <Separator />

                {/* Features */}
                <ul className="space-y-2">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm">
                      <Check className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
              <CardFooter>
                <Button
                  className="w-full"
                  variant={plan.is_popular ? 'default' : 'outline'}
                  onClick={() => handleBuyPlan(plan)}
                >
                  Choose {plan.name}
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>

      {/* Why AMC */}
      <Card className="mt-12">
        <CardContent className="py-8">
          <h3 className="text-xl font-semibold text-center mb-6">Why Choose an AMC?</h3>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              {
                icon: <Wrench className="h-6 w-6" />,
                title: 'Regular Maintenance',
                description: 'Scheduled visits keep your purifier in top condition',
              },
              {
                icon: <Package className="h-6 w-6" />,
                title: 'Parts Discount',
                description: 'Save up to 25% on filter and spare parts',
              },
              {
                icon: <Star className="h-6 w-6" />,
                title: 'Priority Support',
                description: 'Get faster response and dedicated support',
              },
              {
                icon: <CheckCircle className="h-6 w-6" />,
                title: 'Peace of Mind',
                description: 'No surprise repair bills during coverage',
              },
            ].map((item, index) => (
              <div key={index} className="text-center">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3 text-primary">
                  {item.icon}
                </div>
                <h4 className="font-medium mb-1">{item.title}</h4>
                <p className="text-sm text-muted-foreground">{item.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Buy Dialog */}
      <Dialog open={showBuyDialog} onOpenChange={setShowBuyDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Purchase AMC Plan</DialogTitle>
            <DialogDescription>
              {selectedPlan?.name} - {formatCurrency(selectedPlan?.price || 0)}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Select Device</Label>
              <Select value={selectedDevice} onValueChange={setSelectedDevice}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue placeholder="Choose a device" />
                </SelectTrigger>
                <SelectContent>
                  {devices.length > 0 ? (
                    devices.map((device) => (
                      <SelectItem key={device.id} value={device.serial}>
                        {device.name} ({device.serial})
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="no-devices" disabled>
                      No devices registered
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground mt-1">
                Don&apos;t see your device?{' '}
                <Link href="/account/devices" className="text-primary hover:underline">
                  Register it first
                </Link>
              </p>
            </div>

            {selectedPlan && (
              <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span>{selectedPlan.name}</span>
                  <span>{formatCurrency(selectedPlan.price)}</span>
                </div>
                <div className="flex justify-between text-sm text-green-600">
                  <span>Savings</span>
                  <span>
                    -{formatCurrency((selectedPlan.original_price || selectedPlan.price) - selectedPlan.price)}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between font-semibold">
                  <span>Total</span>
                  <span>{formatCurrency(selectedPlan.price)}</span>
                </div>
              </div>
            )}

            <div className="flex items-start gap-2 text-sm text-muted-foreground">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <p>
                AMC will be activated within 24 hours of purchase. You&apos;ll receive a confirmation call from our team.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBuyDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handlePurchase} disabled={purchasing || !selectedDevice}>
              {purchasing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                `Pay ${formatCurrency(selectedPlan?.price || 0)}`
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Help */}
      <Card className="mt-8">
        <CardContent className="py-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-primary/10 rounded-full">
              <Phone className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold">Need help choosing a plan?</h3>
              <p className="text-sm text-muted-foreground">
                Our experts can help you find the right AMC for your needs.
              </p>
            </div>
            <Button variant="outline" asChild>
              <a href="https://wa.me/919311939076?text=I need help choosing an AMC plan" target="_blank" rel="noopener noreferrer">
                Chat with Us
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
