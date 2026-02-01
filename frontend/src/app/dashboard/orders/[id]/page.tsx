'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft, Package, Truck, User, MapPin, CreditCard, FileText,
  CheckCircle, XCircle, Clock, AlertTriangle, Send, Download,
  Plus, RefreshCw, Ban, RotateCcw, Printer, History, DollarSign
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Separator } from '@/components/ui/separator';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency, formatDate } from '@/lib/utils';

interface OrderItem {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  discount: number;
  tax_amount: number;
  total: number;
  serial_numbers?: string[];
}

interface Payment {
  id: string;
  amount: number;
  payment_method: 'CASH' | 'CARD' | 'UPI' | 'NET_BANKING' | 'CHEQUE' | 'WALLET';
  transaction_id?: string;
  payment_date: string;
  status: 'PENDING' | 'AUTHORIZED' | 'CAPTURED' | 'PAID' | 'FAILED' | 'REFUNDED';
  gateway?: string;
  notes?: string;
}

interface StatusHistory {
  id: string;
  status: string;
  changed_by: string;
  changed_at: string;
  notes?: string;
}

interface Invoice {
  id: string;
  invoice_number: string;
  invoice_date: string;
  total_amount: number;
  irn?: string;
  status: string;
}

interface Order {
  id: string;
  order_number: string;
  status: string;
  payment_status: string;
  source: string;
  channel?: string;
  customer: {
    id: string;
    name: string;
    phone: string;
    email?: string;
  };
  shipping_address: {
    address_line1: string;
    address_line2?: string;
    city: string;
    state: string;
    pincode: string;
    landmark?: string;
  };
  billing_address?: {
    address_line1: string;
    city: string;
    state: string;
    pincode: string;
  };
  items: OrderItem[];
  payments: Payment[];
  status_history: StatusHistory[];
  invoices: Invoice[];
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  shipping_amount: number;
  grand_total: number;
  amount_paid: number;
  balance_due: number;
  expected_delivery_date?: string;
  customer_notes?: string;
  internal_notes?: string;
  created_at: string;
  updated_at: string;
}

const orderApi = {
  get: async (id: string): Promise<Order | null> => {
    try {
      const { data } = await apiClient.get(`/orders/${id}`);
      return data;
    } catch {
      return null;
    }
  },
  updateStatus: async (id: string, status: string, notes?: string) => {
    const { data } = await apiClient.put(`/orders/${id}/status`, { status, notes });
    return data;
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post(`/orders/${id}/approve`);
    return data;
  },
  cancel: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/orders/${id}/cancel`, { reason });
    return data;
  },
  addPayment: async (id: string, payment: { amount: number; payment_method: string; transaction_id?: string; notes?: string }) => {
    const { data } = await apiClient.post(`/orders/${id}/payments`, payment);
    return data;
  },
  generateInvoice: async (id: string) => {
    const { data } = await apiClient.post(`/orders/${id}/invoice`);
    return data;
  },
  downloadInvoice: async (invoiceId: string) => {
    const { data } = await apiClient.get<string>(`/invoices/${invoiceId}/download`);
    return data;
  },
};

const statusColors: Record<string, string> = {
  NEW: 'bg-blue-100 text-blue-800',
  PENDING_PAYMENT: 'bg-yellow-100 text-yellow-800',
  CONFIRMED: 'bg-green-100 text-green-800',
  ALLOCATED: 'bg-purple-100 text-purple-800',
  PICKLIST_CREATED: 'bg-indigo-100 text-indigo-800',
  PICKING: 'bg-indigo-100 text-indigo-800',
  PICKED: 'bg-indigo-100 text-indigo-800',
  PACKING: 'bg-orange-100 text-orange-800',
  PACKED: 'bg-orange-100 text-orange-800',
  MANIFESTED: 'bg-cyan-100 text-cyan-800',
  READY_TO_SHIP: 'bg-cyan-100 text-cyan-800',
  SHIPPED: 'bg-blue-100 text-blue-800',
  IN_TRANSIT: 'bg-blue-100 text-blue-800',
  OUT_FOR_DELIVERY: 'bg-green-100 text-green-800',
  DELIVERED: 'bg-green-100 text-green-800',
  RTO_INITIATED: 'bg-red-100 text-red-800',
  RTO_IN_TRANSIT: 'bg-red-100 text-red-800',
  RTO_DELIVERED: 'bg-red-100 text-red-800',
  CANCELLED: 'bg-gray-100 text-gray-800',
  REFUNDED: 'bg-gray-100 text-gray-800',
  ON_HOLD: 'bg-yellow-100 text-yellow-800',
};

const paymentStatusColors: Record<string, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  AUTHORIZED: 'bg-blue-100 text-blue-800',
  CAPTURED: 'bg-green-100 text-green-800',
  PAID: 'bg-green-100 text-green-800',
  FAILED: 'bg-red-100 text-red-800',
  REFUNDED: 'bg-gray-100 text-gray-800',
};

// Order status workflow - what actions are available for each status
const statusActions: Record<string, { next: string; label: string; icon: React.ReactNode }[]> = {
  NEW: [{ next: 'CONFIRMED', label: 'Confirm Order', icon: <CheckCircle className="h-4 w-4" /> }],
  PENDING_PAYMENT: [{ next: 'CONFIRMED', label: 'Confirm Order', icon: <CheckCircle className="h-4 w-4" /> }],
  CONFIRMED: [{ next: 'ALLOCATED', label: 'Allocate Stock', icon: <Package className="h-4 w-4" /> }],
  ALLOCATED: [{ next: 'PICKLIST_CREATED', label: 'Create Picklist', icon: <FileText className="h-4 w-4" /> }],
  PICKLIST_CREATED: [{ next: 'PICKING', label: 'Start Picking', icon: <RefreshCw className="h-4 w-4" /> }],
  PICKING: [{ next: 'PICKED', label: 'Complete Picking', icon: <CheckCircle className="h-4 w-4" /> }],
  PICKED: [{ next: 'PACKING', label: 'Start Packing', icon: <Package className="h-4 w-4" /> }],
  PACKING: [{ next: 'PACKED', label: 'Complete Packing', icon: <CheckCircle className="h-4 w-4" /> }],
  PACKED: [{ next: 'MANIFESTED', label: 'Add to Manifest', icon: <FileText className="h-4 w-4" /> }],
  MANIFESTED: [{ next: 'READY_TO_SHIP', label: 'Ready to Ship', icon: <Truck className="h-4 w-4" /> }],
  READY_TO_SHIP: [{ next: 'SHIPPED', label: 'Mark Shipped', icon: <Send className="h-4 w-4" /> }],
  SHIPPED: [{ next: 'IN_TRANSIT', label: 'In Transit', icon: <Truck className="h-4 w-4" /> }],
  IN_TRANSIT: [{ next: 'OUT_FOR_DELIVERY', label: 'Out for Delivery', icon: <Truck className="h-4 w-4" /> }],
  OUT_FOR_DELIVERY: [{ next: 'DELIVERED', label: 'Mark Delivered', icon: <CheckCircle className="h-4 w-4" /> }],
};

export default function OrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params.id as string;

  const [isPaymentDialogOpen, setIsPaymentDialogOpen] = useState(false);
  const [isCancelDialogOpen, setIsCancelDialogOpen] = useState(false);
  const [paymentForm, setPaymentForm] = useState({
    amount: 0,
    payment_method: 'CASH',
    transaction_id: '',
    notes: '',
  });
  const [cancelReason, setCancelReason] = useState('');

  const queryClient = useQueryClient();

  const { data: order, isLoading } = useQuery({
    queryKey: ['order', orderId],
    queryFn: () => orderApi.get(orderId),
    enabled: !!orderId,
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ status, notes }: { status: string; notes?: string }) =>
      orderApi.updateStatus(orderId, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      toast.success('Order status updated');
    },
    onError: () => toast.error('Failed to update status'),
  });

  const approveMutation = useMutation({
    mutationFn: () => orderApi.approve(orderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      toast.success('Order approved');
    },
    onError: () => toast.error('Failed to approve order'),
  });

  const cancelMutation = useMutation({
    mutationFn: (reason: string) => orderApi.cancel(orderId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      toast.success('Order cancelled');
      setIsCancelDialogOpen(false);
    },
    onError: () => toast.error('Failed to cancel order'),
  });

  const addPaymentMutation = useMutation({
    mutationFn: () => orderApi.addPayment(orderId, paymentForm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      toast.success('Payment recorded');
      setIsPaymentDialogOpen(false);
      setPaymentForm({ amount: 0, payment_method: 'CASH', transaction_id: '', notes: '' });
    },
    onError: () => toast.error('Failed to record payment'),
  });

  const generateInvoiceMutation = useMutation({
    mutationFn: () => orderApi.generateInvoice(orderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      toast.success('Invoice generated');
    },
    onError: () => toast.error('Failed to generate invoice'),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="text-center py-12">
        <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h2 className="text-lg font-medium">Order not found</h2>
        <Button variant="outline" className="mt-4" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Go Back
        </Button>
      </div>
    );
  }

  const availableActions = statusActions[order.status] || [];
  const canCancel = !['DELIVERED', 'CANCELLED', 'REFUNDED', 'RTO_DELIVERED'].includes(order.status);
  const canAddPayment = order.balance_due > 0;
  const canGenerateInvoice = order.status === 'CONFIRMED' && order.invoices.length === 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">Order {order.order_number}</h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[order.status]}`}>
                {order.status.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-muted-foreground">
              Created on {formatDate(order.created_at)} | Source: {order.source}{order.channel ? ` | Channel: ${order.channel}` : ''}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {canCancel && (
            <Button variant="outline" onClick={() => setIsCancelDialogOpen(true)}>
              <Ban className="mr-2 h-4 w-4" /> Cancel
            </Button>
          )}
          {canAddPayment && (
            <Button variant="outline" onClick={() => {
              setPaymentForm({ ...paymentForm, amount: order.balance_due });
              setIsPaymentDialogOpen(true);
            }}>
              <CreditCard className="mr-2 h-4 w-4" /> Record Payment
            </Button>
          )}
          {canGenerateInvoice && (
            <Button variant="outline" onClick={() => generateInvoiceMutation.mutate()}>
              <FileText className="mr-2 h-4 w-4" /> Generate Invoice
            </Button>
          )}
          {availableActions.map((action) => (
            <Button key={action.next} onClick={() => updateStatusMutation.mutate({ status: action.next })}>
              {action.icon}
              <span className="ml-2">{action.label}</span>
            </Button>
          ))}
        </div>
      </div>

      {/* Order Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Order Total</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(order.grand_total)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {order.items.length} items
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Amount Paid</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{formatCurrency(order.amount_paid)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {order.payments.length} payment(s)
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Balance Due</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${order.balance_due > 0 ? 'text-red-600' : 'text-green-600'}`}>
              {formatCurrency(order.balance_due)}
            </div>
            <span className={`text-xs px-2 py-0.5 rounded ${paymentStatusColors[order.payment_status]}`}>
              {order.payment_status}
            </span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Expected Delivery</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {order.expected_delivery_date ? formatDate(order.expected_delivery_date) : '-'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="items" className="space-y-4">
        <TabsList>
          <TabsTrigger value="items">Items ({order.items.length})</TabsTrigger>
          <TabsTrigger value="payments">Payments ({order.payments.length})</TabsTrigger>
          <TabsTrigger value="invoices">Invoices ({order.invoices.length})</TabsTrigger>
          <TabsTrigger value="history">Status History</TabsTrigger>
          <TabsTrigger value="details">Details</TabsTrigger>
        </TabsList>

        {/* Items Tab */}
        <TabsContent value="items">
          <Card>
            <CardHeader>
              <CardTitle>Order Items</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Product</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                    <TableHead className="text-right">Unit Price</TableHead>
                    <TableHead className="text-right">Discount</TableHead>
                    <TableHead className="text-right">Tax</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {order.items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{item.product_name}</div>
                          <div className="text-sm text-muted-foreground">{item.sku}</div>
                          {item.serial_numbers && item.serial_numbers.length > 0 && (
                            <div className="text-xs text-blue-600 mt-1">
                              S/N: {item.serial_numbers.join(', ')}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">{item.quantity}</TableCell>
                      <TableCell className="text-right">{formatCurrency(item.unit_price)}</TableCell>
                      <TableCell className="text-right text-red-600">
                        {item.discount > 0 ? `-${formatCurrency(item.discount)}` : '-'}
                      </TableCell>
                      <TableCell className="text-right">{formatCurrency(item.tax_amount)}</TableCell>
                      <TableCell className="text-right font-medium">{formatCurrency(item.total)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Separator className="my-4" />
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span>{formatCurrency(order.subtotal)}</span>
                </div>
                {order.discount_amount > 0 && (
                  <div className="flex justify-between text-red-600">
                    <span>Discount</span>
                    <span>-{formatCurrency(order.discount_amount)}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Tax</span>
                  <span>{formatCurrency(order.tax_amount)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Shipping</span>
                  <span>{formatCurrency(order.shipping_amount)}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-lg font-bold">
                  <span>Grand Total</span>
                  <span>{formatCurrency(order.grand_total)}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Payments Tab */}
        <TabsContent value="payments">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Payment History</CardTitle>
                <CardDescription>All payments received for this order</CardDescription>
              </div>
              {canAddPayment && (
                <Button size="sm" onClick={() => {
                  setPaymentForm({ ...paymentForm, amount: order.balance_due });
                  setIsPaymentDialogOpen(true);
                }}>
                  <Plus className="mr-2 h-4 w-4" /> Add Payment
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {order.payments.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <CreditCard className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No payments recorded</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Method</TableHead>
                      <TableHead>Transaction ID</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {order.payments.map((payment) => (
                      <TableRow key={payment.id}>
                        <TableCell>{formatDate(payment.payment_date)}</TableCell>
                        <TableCell>{payment.payment_method}</TableCell>
                        <TableCell className="font-mono">{payment.transaction_id || '-'}</TableCell>
                        <TableCell className="text-right font-medium">{formatCurrency(payment.amount)}</TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${paymentStatusColors[payment.status]}`}>
                            {payment.status}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Invoices Tab */}
        <TabsContent value="invoices">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Invoices</CardTitle>
                <CardDescription>Tax invoices generated for this order</CardDescription>
              </div>
              {canGenerateInvoice && (
                <Button size="sm" onClick={() => generateInvoiceMutation.mutate()}>
                  <FileText className="mr-2 h-4 w-4" /> Generate Invoice
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {order.invoices.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No invoices generated</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Invoice Number</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>IRN</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {order.invoices.map((invoice) => (
                      <TableRow key={invoice.id}>
                        <TableCell className="font-mono font-medium">{invoice.invoice_number}</TableCell>
                        <TableCell>{formatDate(invoice.invoice_date)}</TableCell>
                        <TableCell className="font-mono text-xs">{invoice.irn || '-'}</TableCell>
                        <TableCell className="text-right font-medium">{formatCurrency(invoice.total_amount)}</TableCell>
                        <TableCell>
                          <span className="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                            {invoice.status}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Printer className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Status History Tab */}
        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" /> Status History
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {order.status_history.map((history, index) => (
                  <div key={history.id} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className={`w-3 h-3 rounded-full ${index === 0 ? 'bg-green-500' : 'bg-muted'}`} />
                      {index < order.status_history.length - 1 && (
                        <div className="w-0.5 h-full bg-muted" />
                      )}
                    </div>
                    <div className="flex-1 pb-4">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColors[history.status]}`}>
                          {history.status.replace(/_/g, ' ')}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          by {history.changed_by}
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {formatDate(history.changed_at)}
                      </div>
                      {history.notes && (
                        <div className="text-sm mt-2 p-2 bg-muted rounded">
                          {history.notes}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Details Tab */}
        <TabsContent value="details">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" /> Customer
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div>
                  <div className="font-medium">{order.customer.name}</div>
                  <div className="text-sm text-muted-foreground">{order.customer.phone}</div>
                  {order.customer.email && (
                    <div className="text-sm text-muted-foreground">{order.customer.email}</div>
                  )}
                </div>
                <Button variant="outline" size="sm" className="mt-2">
                  View Customer 360
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="h-5 w-5" /> Shipping Address
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm">
                  <div>{order.shipping_address.address_line1}</div>
                  {order.shipping_address.address_line2 && (
                    <div>{order.shipping_address.address_line2}</div>
                  )}
                  <div>
                    {order.shipping_address.city}, {order.shipping_address.state} - {order.shipping_address.pincode}
                  </div>
                  {order.shipping_address.landmark && (
                    <div className="text-muted-foreground">Landmark: {order.shipping_address.landmark}</div>
                  )}
                </div>
              </CardContent>
            </Card>

            {order.customer_notes && (
              <Card>
                <CardHeader>
                  <CardTitle>Customer Notes</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">{order.customer_notes}</p>
                </CardContent>
              </Card>
            )}

            {order.internal_notes && (
              <Card>
                <CardHeader>
                  <CardTitle>Internal Notes</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">{order.internal_notes}</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Add Payment Dialog */}
      <Dialog open={isPaymentDialogOpen} onOpenChange={setIsPaymentDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record Payment</DialogTitle>
            <DialogDescription>
              Balance due: {formatCurrency(order.balance_due)}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Amount</label>
              <Input
                type="number"
                value={paymentForm.amount}
                onChange={(e) => setPaymentForm({ ...paymentForm, amount: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Payment Method</label>
              <Select
                value={paymentForm.payment_method}
                onValueChange={(value) => setPaymentForm({ ...paymentForm, payment_method: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CASH">Cash</SelectItem>
                  <SelectItem value="CARD">Card</SelectItem>
                  <SelectItem value="UPI">UPI</SelectItem>
                  <SelectItem value="NET_BANKING">Net Banking</SelectItem>
                  <SelectItem value="CHEQUE">Cheque</SelectItem>
                  <SelectItem value="WALLET">Wallet</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Transaction ID (Optional)</label>
              <Input
                value={paymentForm.transaction_id}
                onChange={(e) => setPaymentForm({ ...paymentForm, transaction_id: e.target.value })}
                placeholder="Enter transaction reference"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Notes (Optional)</label>
              <Textarea
                value={paymentForm.notes}
                onChange={(e) => setPaymentForm({ ...paymentForm, notes: e.target.value })}
                placeholder="Any additional notes"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsPaymentDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => addPaymentMutation.mutate()}>
              <DollarSign className="mr-2 h-4 w-4" /> Record Payment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Cancel Order Dialog */}
      <Dialog open={isCancelDialogOpen} onOpenChange={setIsCancelDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Order</DialogTitle>
            <DialogDescription>
              Are you sure you want to cancel this order? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Cancellation Reason</label>
              <Textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="Enter reason for cancellation"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCancelDialogOpen(false)}>Keep Order</Button>
            <Button variant="destructive" onClick={() => cancelMutation.mutate(cancelReason)} disabled={!cancelReason}>
              <XCircle className="mr-2 h-4 w-4" /> Cancel Order
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
