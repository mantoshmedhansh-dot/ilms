'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ChevronRight,
  Package,
  Loader2,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Camera,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from 'sonner';
import { authApi, returnsApi, ReturnRequest, ReturnItemRequest } from '@/lib/storefront/api';
import { useAuthStore } from '@/lib/storefront/auth-store';
import { formatCurrency } from '@/lib/utils';

const returnReasons = [
  { value: 'DAMAGED', label: 'Product is damaged' },
  { value: 'DEFECTIVE', label: 'Product is defective / not working' },
  { value: 'WRONG_ITEM', label: 'Wrong item delivered' },
  { value: 'NOT_AS_DESCRIBED', label: 'Product not as described' },
  { value: 'CHANGED_MIND', label: 'Changed my mind' },
  { value: 'QUALITY_ISSUE', label: 'Quality not satisfactory' },
  { value: 'OTHER', label: 'Other reason' },
] as const;

const itemConditions = [
  { value: 'UNOPENED', label: 'Unopened / Sealed' },
  { value: 'OPENED_UNUSED', label: 'Opened but unused' },
  { value: 'USED', label: 'Used' },
  { value: 'DAMAGED', label: 'Damaged' },
  { value: 'DEFECTIVE', label: 'Defective' },
] as const;

interface OrderItem {
  id: string;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

interface OrderData {
  order_number: string;
  status: string;
  shipping_address: {
    full_name: string;
    phone: string;
    address_line1: string;
    address_line2?: string;
    city: string;
    state: string;
    pincode: string;
  };
  items: OrderItem[];
}

interface SelectedItem {
  order_item_id: string;
  quantity_returned: number;
  condition: string;
  condition_notes: string;
}

export default function ReturnRequestPage({ params }: { params: Promise<{ orderNumber: string }> }) {
  const resolvedParams = use(params);
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, customer } = useAuthStore();

  const [order, setOrder] = useState<OrderData | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [rmaNumber, setRmaNumber] = useState('');

  // Form state
  const [selectedItems, setSelectedItems] = useState<Record<string, SelectedItem>>({});
  const [returnReason, setReturnReason] = useState<string>('');
  const [returnReasonDetails, setReturnReasonDetails] = useState('');
  const [useOrderAddress, setUseOrderAddress] = useState(true);
  const [pickupAddress, setPickupAddress] = useState({
    full_name: '',
    phone: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    pincode: '',
  });

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push(`/account/login?redirect=/account/orders/${resolvedParams.orderNumber}/return`);
    }
  }, [isAuthenticated, authLoading, router, resolvedParams.orderNumber]);

  useEffect(() => {
    const fetchOrder = async () => {
      if (!isAuthenticated) return;

      try {
        const data = await authApi.getOrderByNumber(resolvedParams.orderNumber);

        // Check if order is eligible for return
        if (!['DELIVERED', 'PARTIALLY_DELIVERED'].includes(data.status)) {
          toast.error('This order is not eligible for return');
          router.push(`/account/orders/${resolvedParams.orderNumber}`);
          return;
        }

        setOrder({
          order_number: data.order_number,
          status: data.status,
          shipping_address: data.shipping_address,
          items: data.items,
        });

        // Pre-fill pickup address from order
        setPickupAddress({
          full_name: data.shipping_address.full_name,
          phone: data.shipping_address.phone,
          address_line1: data.shipping_address.address_line1,
          address_line2: data.shipping_address.address_line2 || '',
          city: data.shipping_address.city,
          state: data.shipping_address.state,
          pincode: data.shipping_address.pincode,
        });
      } catch (error) {
        toast.error('Failed to load order details');
        router.push('/account/orders');
      } finally {
        setLoading(false);
      }
    };

    fetchOrder();
  }, [isAuthenticated, resolvedParams.orderNumber, router]);

  const toggleItem = (itemId: string, item: OrderItem) => {
    setSelectedItems(prev => {
      if (prev[itemId]) {
        const newItems = { ...prev };
        delete newItems[itemId];
        return newItems;
      }
      return {
        ...prev,
        [itemId]: {
          order_item_id: itemId,
          quantity_returned: item.quantity,
          condition: 'UNOPENED',
          condition_notes: '',
        },
      };
    });
  };

  const updateItemField = (itemId: string, field: keyof SelectedItem, value: string | number) => {
    setSelectedItems(prev => ({
      ...prev,
      [itemId]: {
        ...prev[itemId],
        [field]: value,
      },
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    const selectedItemsList = Object.values(selectedItems);
    if (selectedItemsList.length === 0) {
      toast.error('Please select at least one item to return');
      return;
    }

    if (!returnReason) {
      toast.error('Please select a return reason');
      return;
    }

    if (!order || !customer?.phone) {
      toast.error('Unable to submit return request');
      return;
    }

    setSubmitting(true);
    try {
      const request: ReturnRequest = {
        order_number: order.order_number,
        phone: customer.phone,
        return_reason: returnReason as ReturnRequest['return_reason'],
        return_reason_details: returnReasonDetails || undefined,
        items: selectedItemsList.map(item => ({
          order_item_id: item.order_item_id,
          quantity_returned: item.quantity_returned,
          condition: item.condition as ReturnItemRequest['condition'],
          condition_notes: item.condition_notes || undefined,
        })),
        pickup_address: useOrderAddress ? undefined : {
          ...pickupAddress,
          country: 'India',
        },
      };

      const result = await returnsApi.requestReturn(request);
      setRmaNumber(result.rma_number);
      setSuccess(true);
      toast.success('Return request submitted successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to submit return request');
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated || !order) {
    return null;
  }

  if (success) {
    return (
      <div className="bg-muted/50 min-h-screen py-6">
        <div className="container mx-auto px-4 max-w-2xl">
          <Card>
            <CardContent className="pt-12 pb-8 text-center">
              <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold mb-2">Return Request Submitted</h2>
              <p className="text-muted-foreground mb-4">
                Your return request has been submitted successfully.
              </p>
              <div className="bg-muted p-4 rounded-lg mb-6 inline-block">
                <p className="text-sm text-muted-foreground">RMA Number</p>
                <p className="text-2xl font-mono font-bold text-primary">{rmaNumber}</p>
              </div>
              <p className="text-sm text-muted-foreground mb-6">
                We&apos;ll review your request and send you an update within 24-48 hours.
                You can track your return status using the RMA number above.
              </p>
              <div className="flex gap-3 justify-center">
                <Button variant="outline" asChild>
                  <Link href="/account/orders">Back to Orders</Link>
                </Button>
                <Button asChild>
                  <Link href={`/account/returns/${rmaNumber}`}>Track Return</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const selectedCount = Object.keys(selectedItems).length;
  const totalRefund = Object.values(selectedItems).reduce((sum, item) => {
    const orderItem = order.items.find(oi => oi.id === item.order_item_id);
    if (orderItem) {
      return sum + (orderItem.unit_price * item.quantity_returned);
    }
    return sum;
  }, 0);

  return (
    <div className="bg-muted/50 min-h-screen py-6">
      <div className="container mx-auto px-4 max-w-3xl">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
          <Link href="/" className="hover:text-primary">Home</Link>
          <ChevronRight className="h-4 w-4" />
          <Link href="/account" className="hover:text-primary">Account</Link>
          <ChevronRight className="h-4 w-4" />
          <Link href="/account/orders" className="hover:text-primary">Orders</Link>
          <ChevronRight className="h-4 w-4" />
          <Link href={`/account/orders/${order.order_number}`} className="hover:text-primary">
            {order.order_number}
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground">Return</span>
        </nav>

        <div className="flex items-center gap-4 mb-6">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/account/orders/${order.order_number}`}>
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Request Return</h1>
            <p className="text-muted-foreground">Order {order.order_number}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Select Items */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Select Items to Return</CardTitle>
              <CardDescription>
                Choose the items you want to return and specify the quantity and condition.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {order.items.map((item) => {
                const isSelected = !!selectedItems[item.id];
                const selectedItem = selectedItems[item.id];

                return (
                  <div
                    key={item.id}
                    className={`p-4 rounded-lg border-2 transition-colors ${
                      isSelected ? 'border-primary bg-primary/5' : 'border-muted'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <Checkbox
                        id={`item-${item.id}`}
                        checked={isSelected}
                        onCheckedChange={() => toggleItem(item.id, item)}
                      />
                      <div className="flex-1">
                        <label
                          htmlFor={`item-${item.id}`}
                          className="font-medium cursor-pointer"
                        >
                          {item.product_name}
                        </label>
                        <p className="text-sm text-muted-foreground">
                          SKU: {item.sku} | Qty: {item.quantity} | {formatCurrency(item.unit_price)} each
                        </p>
                      </div>
                      <p className="font-medium">{formatCurrency(item.total_price)}</p>
                    </div>

                    {isSelected && (
                      <div className="mt-4 pl-8 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label>Quantity to Return</Label>
                            <Input
                              type="number"
                              min={1}
                              max={item.quantity}
                              value={selectedItem.quantity_returned}
                              onChange={(e) => updateItemField(
                                item.id,
                                'quantity_returned',
                                Math.min(item.quantity, Math.max(1, parseInt(e.target.value) || 1))
                              )}
                            />
                          </div>
                          <div>
                            <Label>Item Condition</Label>
                            <select
                              value={selectedItem.condition}
                              onChange={(e) => updateItemField(item.id, 'condition', e.target.value)}
                              className="w-full h-10 px-3 rounded-md border border-input bg-background"
                            >
                              {itemConditions.map((cond) => (
                                <option key={cond.value} value={cond.value}>
                                  {cond.label}
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>
                        <div>
                          <Label>Notes (Optional)</Label>
                          <Textarea
                            placeholder="Describe any issues with the item..."
                            value={selectedItem.condition_notes}
                            onChange={(e) => updateItemField(item.id, 'condition_notes', e.target.value)}
                            rows={2}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Return Reason */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Return Reason</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <RadioGroup value={returnReason} onValueChange={setReturnReason}>
                {returnReasons.map((reason) => (
                  <div key={reason.value} className="flex items-center space-x-3">
                    <RadioGroupItem value={reason.value} id={reason.value} />
                    <Label htmlFor={reason.value} className="cursor-pointer">
                      {reason.label}
                    </Label>
                  </div>
                ))}
              </RadioGroup>

              <div>
                <Label>Additional Details (Optional)</Label>
                <Textarea
                  placeholder="Provide more details about your return reason..."
                  value={returnReasonDetails}
                  onChange={(e) => setReturnReasonDetails(e.target.value)}
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>

          {/* Pickup Address */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Pickup Address</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-2 mb-4">
                <Checkbox
                  id="use-order-address"
                  checked={useOrderAddress}
                  onCheckedChange={(checked) => setUseOrderAddress(!!checked)}
                />
                <Label htmlFor="use-order-address" className="cursor-pointer">
                  Use order shipping address for pickup
                </Label>
              </div>

              {useOrderAddress ? (
                <div className="bg-muted/50 p-4 rounded-lg text-sm">
                  <p className="font-medium">{order.shipping_address.full_name}</p>
                  <p>{order.shipping_address.address_line1}</p>
                  {order.shipping_address.address_line2 && (
                    <p>{order.shipping_address.address_line2}</p>
                  )}
                  <p>
                    {order.shipping_address.city}, {order.shipping_address.state} -{' '}
                    {order.shipping_address.pincode}
                  </p>
                  <p>Phone: {order.shipping_address.phone}</p>
                </div>
              ) : (
                <div className="grid gap-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Full Name</Label>
                      <Input
                        value={pickupAddress.full_name}
                        onChange={(e) => setPickupAddress(p => ({ ...p, full_name: e.target.value }))}
                        required={!useOrderAddress}
                      />
                    </div>
                    <div>
                      <Label>Phone</Label>
                      <Input
                        value={pickupAddress.phone}
                        onChange={(e) => setPickupAddress(p => ({ ...p, phone: e.target.value }))}
                        required={!useOrderAddress}
                      />
                    </div>
                  </div>
                  <div>
                    <Label>Address Line 1</Label>
                    <Input
                      value={pickupAddress.address_line1}
                      onChange={(e) => setPickupAddress(p => ({ ...p, address_line1: e.target.value }))}
                      required={!useOrderAddress}
                    />
                  </div>
                  <div>
                    <Label>Address Line 2</Label>
                    <Input
                      value={pickupAddress.address_line2}
                      onChange={(e) => setPickupAddress(p => ({ ...p, address_line2: e.target.value }))}
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label>City</Label>
                      <Input
                        value={pickupAddress.city}
                        onChange={(e) => setPickupAddress(p => ({ ...p, city: e.target.value }))}
                        required={!useOrderAddress}
                      />
                    </div>
                    <div>
                      <Label>State</Label>
                      <Input
                        value={pickupAddress.state}
                        onChange={(e) => setPickupAddress(p => ({ ...p, state: e.target.value }))}
                        required={!useOrderAddress}
                      />
                    </div>
                    <div>
                      <Label>Pincode</Label>
                      <Input
                        value={pickupAddress.pincode}
                        onChange={(e) => setPickupAddress(p => ({ ...p, pincode: e.target.value }))}
                        required={!useOrderAddress}
                      />
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Summary & Submit */}
          <Card>
            <CardContent className="pt-6">
              {selectedCount > 0 ? (
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-sm text-muted-foreground">
                      {selectedCount} item{selectedCount > 1 ? 's' : ''} selected
                    </p>
                    <p className="text-lg font-bold">
                      Estimated Refund: {formatCurrency(totalRefund)}
                    </p>
                  </div>
                  <Button type="submit" size="lg" disabled={submitting || !returnReason}>
                    {submitting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Submitting...
                      </>
                    ) : (
                      'Submit Return Request'
                    )}
                  </Button>
                </div>
              ) : (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Please select at least one item to return.
                  </AlertDescription>
                </Alert>
              )}

              <p className="text-xs text-muted-foreground">
                By submitting this return request, you agree to our return policy.
                Refund amount may vary based on item inspection.
              </p>
            </CardContent>
          </Card>
        </form>
      </div>
    </div>
  );
}
