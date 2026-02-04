'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ChevronRight,
  CreditCard,
  Truck,
  Package,
  ArrowLeft,
  Loader2,
  Check,
  MapPin,
  AlertCircle,
  CheckCircle2,
  Clock,
  Banknote,
  Gift,
  FileText,
  Tag,
  X,
  Percent,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { useCartStore, useCartSummary, getPartnerReferralCode, clearPartnerReferralCode } from '@/lib/storefront/cart-store';
import { ordersApi, paymentsApi, inventoryApi, couponsApi, companyApi, addressApi, CouponValidationResponse, ActiveCoupon } from '@/lib/storefront/api';
import { useAuthStore, useIsAuthenticated } from '@/lib/storefront/auth-store';
import { formatCurrency } from '@/lib/utils';
import { D2COrderRequest, ShippingAddress, CompanyInfo } from '@/types/storefront';
import AddressSelector from '@/components/storefront/checkout/address-selector';
import AddressAutocomplete from '@/components/storefront/checkout/address-autocomplete';

// Serviceability check result type
interface ServiceabilityResult {
  serviceable: boolean;
  estimate_days?: number;
  message?: string;
  cod_available?: boolean;
  shipping_cost?: number;
}

const indianStates = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
  'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
  'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
  'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Delhi', 'Jammu and Kashmir', 'Ladakh',
];

export default function CheckoutPage() {
  const router = useRouter();
  const clearCart = useCartStore((state) => state.clearCart);
  const setCheckoutStep = useCartStore((state) => state.setCheckoutStep);
  const syncToBackend = useCartStore((state) => state.syncToBackend);
  const markAsConverted = useCartStore((state) => state.markAsConverted);
  const { items, subtotal, tax, shipping, total } = useCartSummary();
  const isAuthenticated = useIsAuthenticated();

  const [step, setStep] = useState<'shipping' | 'payment' | 'review'>('shipping');
  const [loading, setLoading] = useState(false);
  const isProcessingRef = useRef(false); // Prevent double submission
  const [paymentMethod, setPaymentMethod] = useState<'RAZORPAY' | 'COD'>('RAZORPAY');
  const [useNewAddress, setUseNewAddress] = useState(false);
  const [addressFromSelector, setAddressFromSelector] = useState<ShippingAddress | null>(null);

  // Serviceability state
  const [checkingPincode, setCheckingPincode] = useState(false);
  const [serviceability, setServiceability] = useState<ServiceabilityResult | null>(null);
  const [lastCheckedPincode, setLastCheckedPincode] = useState('');

  // Coupon state
  const [couponCode, setCouponCode] = useState('');
  const [validatingCoupon, setValidatingCoupon] = useState(false);
  const [appliedCoupon, setAppliedCoupon] = useState<CouponValidationResponse | null>(null);
  const [availableCoupons, setAvailableCoupons] = useState<ActiveCoupon[]>([]);
  const [showCoupons, setShowCoupons] = useState(false);

  // Order options state
  const [orderNotes, setOrderNotes] = useState('');
  const [giftWrap, setGiftWrap] = useState(false);
  const [giftMessage, setGiftMessage] = useState('');
  const [gstInvoice, setGstInvoice] = useState(false);
  const [gstin, setGstin] = useState('');
  const [businessName, setBusinessName] = useState('');

  // Company info state
  const [company, setCompany] = useState<CompanyInfo | null>(null);

  const [formData, setFormData] = useState<ShippingAddress>({
    full_name: '',
    phone: '',
    email: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    pincode: '',
    country: 'India',
  });

  const [errors, setErrors] = useState<Partial<ShippingAddress>>({});

  // Check pincode serviceability
  const checkPincodeServiceability = useCallback(async (pincode: string) => {
    if (pincode.length !== 6 || !/^\d{6}$/.test(pincode)) {
      setServiceability(null);
      return;
    }

    // Don't recheck the same pincode
    if (pincode === lastCheckedPincode) {
      return;
    }

    setCheckingPincode(true);
    try {
      const result = await inventoryApi.checkDelivery(pincode);
      setServiceability(result);
      setLastCheckedPincode(pincode);

      // If COD is not available, default to RAZORPAY
      if (result.serviceable && !result.cod_available && paymentMethod === 'COD') {
        setPaymentMethod('RAZORPAY');
      }
    } catch (error) {
      setServiceability({
        serviceable: false,
        message: 'Unable to check delivery availability. Please try again.',
      });
    } finally {
      setCheckingPincode(false);
    }
  }, [lastCheckedPincode, paymentMethod]);

  // Auto-check pincode when it becomes valid
  useEffect(() => {
    const pincode = formData.pincode;
    if (pincode.length === 6 && /^\d{6}$/.test(pincode)) {
      checkPincodeServiceability(pincode);
    }
  }, [formData.pincode, checkPincodeServiceability]);

  // Auto-fill city/state from pincode
  useEffect(() => {
    const pincode = formData.pincode;
    if (pincode.length === 6 && /^\d{6}$/.test(pincode)) {
      // Only auto-fill if city or state is empty
      if (!formData.city || !formData.state) {
        const fetchPincodeInfo = async () => {
          try {
            const info = await addressApi.lookupPincode(pincode);
            if (info) {
              setFormData((prev) => ({
                ...prev,
                city: prev.city || info.city || '',
                state: prev.state || info.state || '',
              }));
            }
          } catch {
            // Silently fail - user can still enter manually
          }
        };
        fetchPincodeInfo();
      }
    }
  }, [formData.pincode, formData.city, formData.state]);

  // Fetch available coupons on mount
  useEffect(() => {
    const fetchCoupons = async () => {
      try {
        const coupons = await couponsApi.getActive();
        setAvailableCoupons(coupons);
      } catch (error) {
        // Silently fail - coupons are optional
      }
    };
    fetchCoupons();
  }, []);

  // Fetch company info on mount
  useEffect(() => {
    const fetchCompany = async () => {
      try {
        const data = await companyApi.getInfo();
        setCompany(data);
      } catch (error) {
        // Silently fail - will use fallback 'ILMS.AI'
      }
    };
    fetchCompany();
  }, []);

  // Track checkout initiation
  useEffect(() => {
    if (items.length > 0) {
      setCheckoutStep('SHIPPING');
      syncToBackend();
    }
  }, []); // Only on initial mount

  // Calculate discount amount
  const discountAmount = appliedCoupon?.valid ? (appliedCoupon.discount_amount || 0) : 0;
  const finalTotal = total - discountAmount;

  // Validate coupon
  const handleValidateCoupon = async (codeOverride?: string) => {
    const codeToValidate = codeOverride || couponCode.trim();
    if (!codeToValidate) {
      toast.error('Please enter a coupon code');
      return;
    }

    setValidatingCoupon(true);
    try {
      const result = await couponsApi.validate({
        code: codeToValidate,
        cart_total: subtotal,
        cart_items: items.reduce((sum, item) => sum + item.quantity, 0),
        product_ids: items.map(item => item.product.id),
        category_ids: items.map(item => item.product.category_id).filter(Boolean) as string[],
      });

      if (result.valid) {
        setAppliedCoupon(result);
        toast.success(result.message);
      } else {
        toast.error(result.message);
        setAppliedCoupon(null);
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to validate coupon');
      setAppliedCoupon(null);
    } finally {
      setValidatingCoupon(false);
    }
  };

  // Remove coupon
  const handleRemoveCoupon = () => {
    setAppliedCoupon(null);
    setCouponCode('');
    toast.info('Coupon removed');
  };

  // Apply coupon from available list
  const handleApplyCoupon = (code: string) => {
    setCouponCode(code);
    setShowCoupons(false);
    // Validate with the code directly to avoid race condition
    handleValidateCoupon(code);
  };

  // Redirect if cart is empty
  if (items.length === 0) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center px-4">
        <Package className="h-16 w-16 text-gray-400 mb-6" />
        <h2 className="text-2xl font-bold mb-2">Your cart is empty</h2>
        <p className="text-muted-foreground mb-6">
          Add some products to proceed with checkout.
        </p>
        <Button size="lg" asChild>
          <Link href="/products">Browse Products</Link>
        </Button>
      </div>
    );
  }

  const validateShipping = (): boolean => {
    const newErrors: Partial<ShippingAddress> = {};

    if (!formData.full_name.trim()) newErrors.full_name = 'Name is required';
    if (!formData.phone.trim()) newErrors.phone = 'Phone is required';
    else if (!/^[6-9]\d{9}$/.test(formData.phone))
      newErrors.phone = 'Enter valid 10-digit phone';
    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email))
      newErrors.email = 'Enter valid email';
    if (!formData.address_line1.trim())
      newErrors.address_line1 = 'Address is required';
    if (!formData.city.trim()) newErrors.city = 'City is required';
    if (!formData.state) newErrors.state = 'State is required';
    if (!formData.pincode.trim()) newErrors.pincode = 'Pincode is required';
    else if (!/^\d{6}$/.test(formData.pincode))
      newErrors.pincode = 'Enter valid 6-digit pincode';
    else if (serviceability && !serviceability.serviceable)
      newErrors.pincode = 'Delivery not available to this pincode';

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleShippingSubmit = async () => {
    // If serviceability hasn't been checked yet, check it first
    if (formData.pincode.length === 6 && !serviceability) {
      await checkPincodeServiceability(formData.pincode);
    }

    // Check if delivery is not serviceable
    if (serviceability && !serviceability.serviceable) {
      toast.error('Delivery not available to this pincode');
      return;
    }

    if (validateShipping()) {
      setStep('payment');
      // Track checkout progress and sync contact info
      setCheckoutStep('PAYMENT');
      syncToBackend({
        email: formData.email || undefined,
        phone: formData.phone,
        customer_name: formData.full_name,
        shipping_address: formData,
      });
    }
  };

  const handlePaymentSubmit = () => {
    setStep('review');
    setCheckoutStep('REVIEW');
    syncToBackend({ selected_payment_method: paymentMethod });
  };

  const handlePlaceOrder = async () => {
    // Prevent double submission
    if (isProcessingRef.current || loading) {
      return;
    }
    isProcessingRef.current = true;
    setLoading(true);

    try {
      // Get partner referral code from httpOnly cookie (set by middleware)
      // Uses API route for secure access to httpOnly cookie
      const partnerCode = await getPartnerReferralCode();

      const orderData: D2COrderRequest = {
        customer_name: formData.full_name,
        customer_phone: formData.phone,
        customer_email: formData.email || undefined,
        shipping_address: formData,
        items: items.map((item) => ({
          product_id: item.product.id,
          sku: item.variant?.sku || item.product.sku,
          name: item.product.name + (item.variant ? ` - ${item.variant.name}` : ''),
          quantity: item.quantity,
          unit_price: item.price,
          tax_rate: item.product.gst_rate || 18,
        })),
        payment_method: paymentMethod,
        subtotal,
        tax_amount: tax,
        shipping_amount: shipping,
        discount_amount: discountAmount,
        coupon_code: appliedCoupon?.valid ? appliedCoupon.code : undefined,
        total_amount: finalTotal,
        partner_code: partnerCode || undefined, // Partner referral attribution
      };

      if (paymentMethod === 'RAZORPAY') {
        // Load Razorpay script if not already loaded
        if (!(window as any).Razorpay) {
          await loadRazorpayScript();
        }

        // Step 1: Create D2C order first
        const order = await ordersApi.createD2C(orderData);

        // Step 2: Create Razorpay payment order
        const paymentOrder = await paymentsApi.createOrder({
          order_id: order.id,
          amount: finalTotal,
          customer_name: formData.full_name,
          customer_email: formData.email || undefined,
          customer_phone: formData.phone,
          notes: {
            order_number: order.order_number,
          },
        });

        // Step 3: Initialize Razorpay with razorpay_order_id
        const options = {
          key: paymentOrder.key_id || process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || 'rzp_test_xxx',
          amount: paymentOrder.amount, // Already in paise from backend
          currency: 'INR',
          name: company?.trade_name || company?.name || 'ILMS.AI',
          description: `Order #${order.order_number}`,
          order_id: paymentOrder.razorpay_order_id, // Use Razorpay order ID
          prefill: {
            name: formData.full_name,
            email: formData.email,
            contact: formData.phone,
          },
          // Enable EMI options for orders above ₹5,000
          ...(finalTotal >= 5000 && {
            config: {
              display: {
                blocks: {
                  utib: { // Axis Bank
                    name: 'Pay using Axis Bank',
                    instruments: [{ method: 'card', issuers: ['UTIB'] }, { method: 'emi', issuers: ['UTIB'] }],
                  },
                  other: {
                    name: 'Other Payment Methods',
                    instruments: [
                      { method: 'card' },
                      { method: 'emi' },
                      { method: 'netbanking' },
                      { method: 'wallet' },
                      { method: 'upi' },
                    ],
                  },
                },
                sequence: ['block.utib', 'block.other'],
                preferences: {
                  show_default_blocks: true,
                },
              },
            },
          }),
          theme: {
            color: '#0066FF',
          },
          handler: async function (response: any) {
            try {
              console.log('Payment response received:', response);
              // Step 4: Verify payment with backend
              const verification = await paymentsApi.verifyPayment({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                order_id: order.id,
              });
              console.log('Verification response:', verification);

              if (verification.verified) {
                // Payment verified - mark cart as converted (non-blocking)
                markAsConverted(order.id).catch((err) => {
                  console.warn('Failed to mark cart as converted:', err);
                });
                clearCart();
                clearPartnerReferralCode(); // Clear partner attribution cookie
                // Use window.location for more reliable redirect
                window.location.href = `/order-success?order=${order.order_number}`;
              } else {
                console.error('Verification failed:', verification.message);
                toast.error(verification.message || 'Payment verification failed. Please contact support.');
                isProcessingRef.current = false;
                setLoading(false);
              }
            } catch (error: any) {
              console.error('Payment verification error:', error);
              const errorMsg = error?.response?.data?.detail || error?.message || 'Payment verification failed';
              toast.error(errorMsg + '. Please contact support.');
              isProcessingRef.current = false;
              setLoading(false);
            }
          },
          modal: {
            ondismiss: function () {
              isProcessingRef.current = false;
              setLoading(false);
              toast.error('Payment cancelled');
            },
          },
        };

        const razorpay = new (window as any).Razorpay(options);
        razorpay.open();
      } else {
        // COD Order
        const order = await ordersApi.createD2C(orderData);
        // Mark cart as converted
        await markAsConverted(order.id);
        clearCart();
        clearPartnerReferralCode(); // Clear partner attribution cookie
        router.push(`/order-success?order=${order.order_number}`);
      }
    } catch (error: any) {
      console.error('Order error:', error);
      toast.error(error.message || 'Failed to place order. Please try again.');
      isProcessingRef.current = false;
      setLoading(false);
    }
  };

  const loadRazorpayScript = (): Promise<void> => {
    return new Promise((resolve) => {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.onload = () => resolve();
      document.body.appendChild(script);
    });
  };

  const updateFormData = (field: keyof ShippingAddress, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  // Handle address selection from saved addresses
  const handleAddressSelect = (address: ShippingAddress) => {
    setAddressFromSelector(address);
    setFormData(address);
    setUseNewAddress(false);
    setErrors({});
    // Trigger pincode check for the selected address
    if (address.pincode && address.pincode.length === 6) {
      setLastCheckedPincode(''); // Reset to force recheck
    }
  };

  // Handle switching to new address form
  const handleAddNewAddress = () => {
    setUseNewAddress(true);
    setAddressFromSelector(null);
    // Clear form for new address
    setFormData({
      full_name: '',
      phone: '',
      email: '',
      address_line1: '',
      address_line2: '',
      city: '',
      state: '',
      pincode: '',
      country: 'India',
    });
    setServiceability(null);
    setLastCheckedPincode('');
  };

  // Handle switching back to saved addresses
  const handleUseSavedAddresses = () => {
    setUseNewAddress(false);
  };

  return (
    <div className="bg-muted/50 min-h-screen py-6">
      <div className="container mx-auto px-4 max-w-5xl">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
          <Link href="/" className="hover:text-primary">
            Home
          </Link>
          <ChevronRight className="h-4 w-4" />
          <Link href="/cart" className="hover:text-primary">
            Cart
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground">Checkout</span>
        </nav>

        <h1 className="text-2xl md:text-3xl font-bold mb-6">Checkout</h1>

        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-8">
          <div className="flex items-center">
            <div
              className={`flex items-center justify-center h-10 w-10 rounded-full ${
                step === 'shipping' || step === 'payment' || step === 'review'
                  ? 'bg-primary text-white'
                  : 'bg-muted'
              }`}
            >
              {step === 'payment' || step === 'review' ? (
                <Check className="h-5 w-5" />
              ) : (
                <Truck className="h-5 w-5" />
              )}
            </div>
            <span className="ml-2 text-sm font-medium">Shipping</span>
          </div>
          <div className="w-16 h-0.5 bg-muted mx-2">
            <div
              className={`h-full bg-primary transition-all ${
                step === 'payment' || step === 'review' ? 'w-full' : 'w-0'
              }`}
            />
          </div>
          <div className="flex items-center">
            <div
              className={`flex items-center justify-center h-10 w-10 rounded-full ${
                step === 'payment' || step === 'review'
                  ? 'bg-primary text-white'
                  : 'bg-muted'
              }`}
            >
              {step === 'review' ? (
                <Check className="h-5 w-5" />
              ) : (
                <CreditCard className="h-5 w-5" />
              )}
            </div>
            <span className="ml-2 text-sm font-medium">Payment</span>
          </div>
          <div className="w-16 h-0.5 bg-muted mx-2">
            <div
              className={`h-full bg-primary transition-all ${
                step === 'review' ? 'w-full' : 'w-0'
              }`}
            />
          </div>
          <div className="flex items-center">
            <div
              className={`flex items-center justify-center h-10 w-10 rounded-full ${
                step === 'review' ? 'bg-primary text-white' : 'bg-muted'
              }`}
            >
              <Package className="h-5 w-5" />
            </div>
            <span className="ml-2 text-sm font-medium">Review</span>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2">
            {/* Shipping Form */}
            {step === 'shipping' && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Truck className="h-5 w-5" />
                    Shipping Address
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Address Selector for logged-in users */}
                  {isAuthenticated && !useNewAddress && (
                    <AddressSelector
                      onSelectAddress={handleAddressSelect}
                      onAddNewAddress={handleAddNewAddress}
                      selectedAddress={addressFromSelector}
                      isAuthenticated={isAuthenticated}
                    />
                  )}

                  {/* Show form when: not authenticated OR user chose to add new address */}
                  {(!isAuthenticated || useNewAddress || !addressFromSelector) && (
                    <>
                      {/* Back to saved addresses button */}
                      {isAuthenticated && useNewAddress && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={handleUseSavedAddresses}
                          className="mb-4"
                        >
                          <ArrowLeft className="h-4 w-4 mr-2" />
                          Back to saved addresses
                        </Button>
                      )}

                      <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="full_name">Full Name *</Label>
                      <Input
                        id="full_name"
                        value={formData.full_name}
                        onChange={(e) => updateFormData('full_name', e.target.value)}
                        className={errors.full_name ? 'border-red-500' : ''}
                      />
                      {errors.full_name && (
                        <p className="text-red-500 text-xs mt-1">{errors.full_name}</p>
                      )}
                    </div>
                    <div>
                      <Label htmlFor="phone">Phone Number *</Label>
                      <Input
                        id="phone"
                        value={formData.phone}
                        onChange={(e) =>
                          updateFormData('phone', e.target.value.replace(/\D/g, '').slice(0, 10))
                        }
                        className={errors.phone ? 'border-red-500' : ''}
                      />
                      {errors.phone && (
                        <p className="text-red-500 text-xs mt-1">{errors.phone}</p>
                      )}
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="email">Email (Optional)</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => updateFormData('email', e.target.value)}
                      className={errors.email ? 'border-red-500' : ''}
                    />
                    {errors.email && (
                      <p className="text-red-500 text-xs mt-1">{errors.email}</p>
                    )}
                  </div>

                  {/* Address Autocomplete with Google Places & DigiPin */}
                  <Separator className="my-4" />
                  <AddressAutocomplete
                    onAddressSelect={(address) => {
                      // Keep name and phone, update address fields
                      setFormData((prev) => ({
                        ...prev,
                        address_line1: address.address_line1,
                        address_line2: address.address_line2 || '',
                        city: address.city,
                        state: address.state,
                        pincode: address.pincode,
                        country: address.country || 'India',
                      }));
                      setErrors({});
                      // Trigger pincode serviceability check
                      if (address.pincode && address.pincode.length === 6) {
                        setLastCheckedPincode('');
                      }
                    }}
                    placeholder="Search address, landmark, or enter DigiPin..."
                  />
                  <Separator className="my-4" />

                  <div>
                    <Label htmlFor="address_line1">Address Line 1 *</Label>
                    <Input
                      id="address_line1"
                      value={formData.address_line1}
                      onChange={(e) => updateFormData('address_line1', e.target.value)}
                      placeholder="House/Flat No., Building Name"
                      className={errors.address_line1 ? 'border-red-500' : ''}
                    />
                    {errors.address_line1 && (
                      <p className="text-red-500 text-xs mt-1">{errors.address_line1}</p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="address_line2">Address Line 2</Label>
                    <Input
                      id="address_line2"
                      value={formData.address_line2}
                      onChange={(e) => updateFormData('address_line2', e.target.value)}
                      placeholder="Street, Area, Landmark"
                    />
                  </div>

                  <div className="grid md:grid-cols-3 gap-4">
                    <div>
                      <Label htmlFor="city">City *</Label>
                      <Input
                        id="city"
                        value={formData.city}
                        onChange={(e) => updateFormData('city', e.target.value)}
                        className={errors.city ? 'border-red-500' : ''}
                      />
                      {errors.city && (
                        <p className="text-red-500 text-xs mt-1">{errors.city}</p>
                      )}
                    </div>
                    <div>
                      <Label htmlFor="state">State *</Label>
                      <select
                        id="state"
                        value={formData.state}
                        onChange={(e) => updateFormData('state', e.target.value)}
                        className={`w-full h-10 px-3 rounded-md border ${
                          errors.state ? 'border-red-500' : 'border-input'
                        } bg-background`}
                      >
                        <option value="">Select State</option>
                        {indianStates.map((state) => (
                          <option key={state} value={state}>
                            {state}
                          </option>
                        ))}
                      </select>
                      {errors.state && (
                        <p className="text-red-500 text-xs mt-1">{errors.state}</p>
                      )}
                    </div>
                    <div>
                      <Label htmlFor="pincode">Pincode *</Label>
                      <div className="relative">
                        <Input
                          id="pincode"
                          value={formData.pincode}
                          onChange={(e) =>
                            updateFormData('pincode', e.target.value.replace(/\D/g, '').slice(0, 6))
                          }
                          className={errors.pincode ? 'border-red-500' : ''}
                          placeholder="e.g., 110001"
                        />
                        {checkingPincode && (
                          <div className="absolute right-3 top-1/2 -translate-y-1/2">
                            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                          </div>
                        )}
                      </div>
                      {errors.pincode && (
                        <p className="text-red-500 text-xs mt-1">{errors.pincode}</p>
                      )}
                    </div>
                  </div>

                  {/* Serviceability Status */}
                  {serviceability && formData.pincode.length === 6 && (
                    <div className="mt-4">
                      {serviceability.serviceable ? (
                        <Alert className="bg-green-50 border-green-200">
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                          <AlertDescription className="ml-2">
                            <div className="flex flex-col gap-1">
                              <span className="font-medium text-green-800">
                                Delivery available to {formData.pincode}
                              </span>
                              <div className="flex flex-wrap gap-4 text-sm text-green-700">
                                {serviceability.estimate_days && (
                                  <span className="flex items-center gap-1">
                                    <Clock className="h-3.5 w-3.5" />
                                    Delivery in {serviceability.estimate_days} days
                                  </span>
                                )}
                                {serviceability.cod_available !== undefined && (
                                  <span className="flex items-center gap-1">
                                    <Banknote className="h-3.5 w-3.5" />
                                    {serviceability.cod_available
                                      ? 'Cash on Delivery available'
                                      : 'COD not available'}
                                  </span>
                                )}
                              </div>
                            </div>
                          </AlertDescription>
                        </Alert>
                      ) : (
                        <Alert variant="destructive" className="bg-red-50 border-red-200">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription className="ml-2">
                            <span className="font-medium">
                              {serviceability.message || 'Delivery not available to this pincode'}
                            </span>
                            <p className="text-sm mt-1">
                              Please enter a different pincode or contact support.
                            </p>
                          </AlertDescription>
                        </Alert>
                      )}
                    </div>
                  )}

                  <div className="flex justify-between pt-4">
                    <Button variant="ghost" asChild>
                      <Link href="/cart">
                        <ArrowLeft className="h-4 w-4 mr-2" />
                        Back to Cart
                      </Link>
                    </Button>
                    <Button onClick={handleShippingSubmit}>
                      Continue to Payment
                    </Button>
                  </div>
                    </>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Payment Options */}
            {step === 'payment' && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CreditCard className="h-5 w-5" />
                    Payment Method
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <RadioGroup
                    value={paymentMethod}
                    onValueChange={(value) => setPaymentMethod(value as 'RAZORPAY' | 'COD')}
                  >
                    <div className="flex items-center space-x-3 p-4 border rounded-lg">
                      <RadioGroupItem value="RAZORPAY" id="razorpay" />
                      <Label htmlFor="razorpay" className="flex-1 cursor-pointer">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">Pay Online</span>
                          {total >= 5000 && (
                            <Badge className="bg-green-100 text-green-800 text-xs">
                              EMI Available
                            </Badge>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Credit/Debit Card, UPI, Net Banking, Wallets
                          {total >= 5000 && ' • No-cost EMI from ' + formatCurrency(Math.round(total / 6)) + '/mo'}
                        </div>
                      </Label>
                      <img
                        src="https://razorpay.com/build/browser/static/razorpay-logo-new.svg"
                        alt="Razorpay"
                        className="h-6"
                      />
                    </div>
                    <div
                      className={`flex items-center space-x-3 p-4 border rounded-lg ${
                        serviceability && !serviceability.cod_available
                          ? 'opacity-50 cursor-not-allowed'
                          : ''
                      }`}
                    >
                      <RadioGroupItem
                        value="COD"
                        id="cod"
                        disabled={serviceability !== null && !serviceability.cod_available}
                      />
                      <Label
                        htmlFor="cod"
                        className={`flex-1 ${
                          serviceability && !serviceability.cod_available
                            ? 'cursor-not-allowed'
                            : 'cursor-pointer'
                        }`}
                      >
                        <div className="font-medium">Cash on Delivery</div>
                        <div className="text-sm text-muted-foreground">
                          {serviceability && !serviceability.cod_available
                            ? 'Not available for this pincode'
                            : 'Pay when you receive your order'}
                        </div>
                      </Label>
                    </div>
                  </RadioGroup>

                  <Separator className="my-6" />

                  {/* Order Options */}
                  <div className="space-y-4">
                    <h4 className="font-medium">Additional Options</h4>

                    {/* Order Notes */}
                    <div>
                      <Label htmlFor="orderNotes" className="text-sm">
                        Order Notes (Optional)
                      </Label>
                      <textarea
                        id="orderNotes"
                        value={orderNotes}
                        onChange={(e) => setOrderNotes(e.target.value)}
                        placeholder="Special instructions for delivery, packaging, etc."
                        className="mt-1 w-full h-20 px-3 py-2 text-sm border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                        maxLength={500}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        {orderNotes.length}/500 characters
                      </p>
                    </div>

                    {/* Gift Wrap */}
                    <div className="border rounded-lg p-4">
                      <div className="flex items-start space-x-3">
                        <Checkbox
                          id="giftWrap"
                          checked={giftWrap}
                          onCheckedChange={(checked) => setGiftWrap(checked === true)}
                        />
                        <div className="flex-1">
                          <Label htmlFor="giftWrap" className="cursor-pointer">
                            <div className="font-medium flex items-center gap-2">
                              <Gift className="h-4 w-4 text-pink-500" />
                              Gift Wrap This Order
                              <Badge variant="secondary" className="text-xs">Free</Badge>
                            </div>
                            <p className="text-sm text-muted-foreground mt-1">
                              Send as a gift with special packaging
                            </p>
                          </Label>
                        </div>
                      </div>
                      {giftWrap && (
                        <div className="mt-3 ml-6">
                          <Label htmlFor="giftMessage" className="text-sm">
                            Gift Message (Optional)
                          </Label>
                          <textarea
                            id="giftMessage"
                            value={giftMessage}
                            onChange={(e) => setGiftMessage(e.target.value)}
                            placeholder="Add a personal message..."
                            className="mt-1 w-full h-16 px-3 py-2 text-sm border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                            maxLength={200}
                          />
                        </div>
                      )}
                    </div>

                    {/* GST Invoice */}
                    <div className="border rounded-lg p-4">
                      <div className="flex items-start space-x-3">
                        <Checkbox
                          id="gstInvoice"
                          checked={gstInvoice}
                          onCheckedChange={(checked) => setGstInvoice(checked === true)}
                        />
                        <div className="flex-1">
                          <Label htmlFor="gstInvoice" className="cursor-pointer">
                            <div className="font-medium flex items-center gap-2">
                              <FileText className="h-4 w-4 text-blue-500" />
                              I need a GST Invoice
                            </div>
                            <p className="text-sm text-muted-foreground mt-1">
                              For business purchases - claim GST input credit
                            </p>
                          </Label>
                        </div>
                      </div>
                      {gstInvoice && (
                        <div className="mt-3 ml-6 space-y-3">
                          <div>
                            <Label htmlFor="gstin" className="text-sm">
                              GSTIN *
                            </Label>
                            <Input
                              id="gstin"
                              value={gstin}
                              onChange={(e) => setGstin(e.target.value.toUpperCase())}
                              placeholder="22AAAAA0000A1Z5"
                              className="mt-1"
                              maxLength={15}
                            />
                            <p className="text-xs text-muted-foreground mt-1">
                              15-character GST Identification Number
                            </p>
                          </div>
                          <div>
                            <Label htmlFor="businessName" className="text-sm">
                              Business/Company Name *
                            </Label>
                            <Input
                              id="businessName"
                              value={businessName}
                              onChange={(e) => setBusinessName(e.target.value)}
                              placeholder="Your Company Pvt Ltd"
                              className="mt-1"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex justify-between pt-4">
                    <Button variant="ghost" onClick={() => setStep('shipping')}>
                      <ArrowLeft className="h-4 w-4 mr-2" />
                      Back
                    </Button>
                    <Button onClick={handlePaymentSubmit}>
                      Review Order
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Order Review */}
            {step === 'review' && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Package className="h-5 w-5" />
                    Review Your Order
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Shipping Address */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <h4 className="font-medium">Shipping Address</h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setStep('shipping')}
                      >
                        Edit
                      </Button>
                    </div>
                    <div className="bg-muted/50 p-4 rounded-lg text-sm">
                      <p className="font-medium">{formData.full_name}</p>
                      <p>{formData.address_line1}</p>
                      {formData.address_line2 && <p>{formData.address_line2}</p>}
                      <p>
                        {formData.city}, {formData.state} - {formData.pincode}
                      </p>
                      <p>Phone: {formData.phone}</p>
                      {formData.email && <p>Email: {formData.email}</p>}
                    </div>
                  </div>

                  {/* Payment Method */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <h4 className="font-medium">Payment Method</h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setStep('payment')}
                      >
                        Edit
                      </Button>
                    </div>
                    <div className="bg-muted/50 p-4 rounded-lg text-sm">
                      {paymentMethod === 'RAZORPAY'
                        ? 'Pay Online (Razorpay)'
                        : 'Cash on Delivery'}
                    </div>
                  </div>

                  {/* Applied Coupon */}
                  {appliedCoupon?.valid && (
                    <div>
                      <h4 className="font-medium mb-2">Applied Coupon</h4>
                      <div className="bg-green-50 p-4 rounded-lg flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Tag className="h-5 w-5 text-green-600" />
                          <div>
                            <p className="font-medium text-green-800">
                              {appliedCoupon.code}
                            </p>
                            <p className="text-sm text-green-700">
                              Saving {formatCurrency(discountAmount)}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Delivery Estimate */}
                  {serviceability?.serviceable && serviceability.estimate_days && (
                    <div>
                      <h4 className="font-medium mb-2">Estimated Delivery</h4>
                      <div className="bg-green-50 p-4 rounded-lg flex items-center gap-3">
                        <Truck className="h-5 w-5 text-green-600" />
                        <div>
                          <p className="font-medium text-green-800">
                            Delivery in {serviceability.estimate_days} days
                          </p>
                          <p className="text-sm text-green-700">
                            to {formData.city}, {formData.pincode}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Order Items */}
                  <div>
                    <h4 className="font-medium mb-2">Order Items</h4>
                    <div className="space-y-3">
                      {items.map((item) => (
                        <div
                          key={item.id}
                          className="flex justify-between items-center bg-muted/50 p-3 rounded-lg"
                        >
                          <div>
                            <p className="font-medium text-sm">{item.product.name}</p>
                            <p className="text-xs text-muted-foreground">
                              Qty: {item.quantity}
                            </p>
                          </div>
                          <p className="font-medium">
                            {formatCurrency(item.price * item.quantity)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex justify-between pt-4">
                    <Button variant="ghost" onClick={() => setStep('payment')}>
                      <ArrowLeft className="h-4 w-4 mr-2" />
                      Back
                    </Button>
                    <Button
                      onClick={handlePlaceOrder}
                      disabled={loading}
                      size="lg"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        `Place Order - ${formatCurrency(finalTotal)}`
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Order Summary Sidebar */}
          <div className="lg:col-span-1">
            <Card className="sticky top-24">
              <CardHeader>
                <CardTitle>Order Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Items */}
                <div className="space-y-2">
                  {items.map((item) => (
                    <div key={item.id} className="flex justify-between text-sm">
                      <span className="truncate flex-1 pr-2">
                        {item.product.name} x{item.quantity}
                      </span>
                      <span>{formatCurrency(item.price * item.quantity)}</span>
                    </div>
                  ))}
                </div>

                <Separator />

                {/* Coupon Section */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Tag className="h-4 w-4" />
                    <span>Apply Coupon</span>
                  </div>

                  {appliedCoupon?.valid ? (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                          <div>
                            <p className="font-medium text-green-800 text-sm">
                              {appliedCoupon.code}
                            </p>
                            <p className="text-xs text-green-600">
                              {appliedCoupon.message}
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleRemoveCoupon}
                          className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex gap-2">
                        <Input
                          placeholder="Enter coupon code"
                          value={couponCode}
                          onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                          className="flex-1 uppercase"
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleValidateCoupon();
                            }
                          }}
                        />
                        <Button
                          variant="secondary"
                          onClick={() => handleValidateCoupon()}
                          disabled={validatingCoupon || !couponCode.trim()}
                        >
                          {validatingCoupon ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            'Apply'
                          )}
                        </Button>
                      </div>

                      {/* Available Coupons */}
                      {availableCoupons.length > 0 && (
                        <div>
                          <button
                            type="button"
                            onClick={() => setShowCoupons(!showCoupons)}
                            className="text-xs text-primary hover:underline flex items-center gap-1"
                          >
                            <Gift className="h-3 w-3" />
                            View available coupons ({availableCoupons.length})
                          </button>

                          {showCoupons && (
                            <div className="mt-2 space-y-2 max-h-40 overflow-y-auto">
                              {availableCoupons.map((coupon) => (
                                <div
                                  key={coupon.code}
                                  className="border rounded-lg p-2 bg-muted/50 hover:bg-muted cursor-pointer transition-colors"
                                  onClick={() => handleApplyCoupon(coupon.code)}
                                >
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                      <div className="bg-primary/10 px-2 py-0.5 rounded text-xs font-mono font-medium text-primary">
                                        {coupon.code}
                                      </div>
                                      {coupon.discount_type === 'PERCENTAGE' ? (
                                        <span className="text-xs text-green-600 font-medium">
                                          {coupon.discount_value}% OFF
                                        </span>
                                      ) : coupon.discount_type === 'FIXED_AMOUNT' ? (
                                        <span className="text-xs text-green-600 font-medium">
                                          {formatCurrency(coupon.discount_value)} OFF
                                        </span>
                                      ) : (
                                        <span className="text-xs text-green-600 font-medium">
                                          FREE SHIPPING
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                  <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                                    {coupon.description || coupon.name}
                                  </p>
                                  {coupon.minimum_order_amount && (
                                    <p className="text-xs text-muted-foreground">
                                      Min. order: {formatCurrency(coupon.minimum_order_amount)}
                                    </p>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <Separator />

                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Subtotal</span>
                    <span>{formatCurrency(subtotal)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Shipping</span>
                    <span>
                      {shipping === 0 ? (
                        <span className="text-green-600">FREE</span>
                      ) : (
                        formatCurrency(shipping)
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Tax (GST)</span>
                    <span>{formatCurrency(tax)}</span>
                  </div>
                  {discountAmount > 0 && (
                    <div className="flex justify-between text-green-600">
                      <span className="flex items-center gap-1">
                        <Percent className="h-3 w-3" />
                        Discount
                      </span>
                      <span>-{formatCurrency(discountAmount)}</span>
                    </div>
                  )}
                </div>

                <Separator />

                <div className="flex justify-between text-lg font-semibold">
                  <span>Total</span>
                  <span className="text-primary">{formatCurrency(finalTotal)}</span>
                </div>
                {discountAmount > 0 && (
                  <p className="text-xs text-green-600 text-right">
                    You save {formatCurrency(discountAmount)} on this order!
                  </p>
                )}

                {/* Delivery Estimate */}
                {serviceability?.serviceable && serviceability.estimate_days && (
                  <>
                    <Separator />
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <Truck className="h-4 w-4" />
                      <span>
                        Estimated delivery in {serviceability.estimate_days} days
                      </span>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
