'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft, Package, Truck, MapPin, Clock, CheckCircle, XCircle,
  AlertTriangle, Send, Download, Upload, Camera, FileText, Printer,
  Navigation, Phone, User, Calendar, Weight, Ruler, DollarSign,
  QrCode, RotateCcw, Eye, ScrollText, Loader2
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
import { Separator } from '@/components/ui/separator';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency, formatDate } from '@/lib/utils';

interface TrackingEvent {
  id: string;
  status: string;
  event_time: string;
  location?: string;
  city?: string;
  state?: string;
  description?: string;
  source: string;
}

interface PODData {
  recipient_name?: string;
  recipient_relation?: string;
  signature_url?: string;
  photo_urls?: string[];
  latitude?: number;
  longitude?: number;
  delivery_time?: string;
  notes?: string;
}

interface Shipment {
  id: string;
  awb_number?: string;
  order_id: string;
  order_number: string;
  status: string;
  transporter_id?: string;
  transporter_name?: string;
  warehouse_id: string;
  warehouse_name: string;
  payment_mode: 'PREPAID' | 'COD';
  cod_amount?: number;
  cod_collected?: boolean;
  customer_name: string;
  customer_phone: string;
  shipping_address: {
    address_line1: string;
    address_line2?: string;
    city: string;
    state: string;
    pincode: string;
    landmark?: string;
  };
  weight_kg: number;
  volumetric_weight_kg?: number;
  chargeable_weight_kg?: number;
  length_cm?: number;
  breadth_cm?: number;
  height_cm?: number;
  packages_count: number;
  expected_delivery_date?: string;
  actual_delivery_date?: string;
  sla_status: 'ON_TRACK' | 'AT_RISK' | 'BREACHED';
  tracking_history: TrackingEvent[];
  pod_data?: PODData;
  shipping_cost?: number;
  created_at: string;
  updated_at: string;
}

const shipmentApi = {
  get: async (id: string): Promise<Shipment | null> => {
    try {
      const { data } = await apiClient.get(`/shipments/${id}`);
      return data;
    } catch {
      return null;
    }
  },
  generateAwb: async (id: string) => {
    const { data } = await apiClient.post(`/shipments/${id}/generate-awb`);
    return data;
  },
  pack: async (id: string, packData: { weight_kg: number; length_cm: number; breadth_cm: number; height_cm: number; packages_count: number }) => {
    const { data } = await apiClient.post(`/shipments/${id}/pack`, packData);
    return data;
  },
  updateTracking: async (id: string, tracking: { status: string; location?: string; city?: string; state?: string; description?: string }) => {
    const { data } = await apiClient.post(`/shipments/${id}/track`, tracking);
    return data;
  },
  markDelivered: async (id: string, podData: { recipient_name: string; recipient_relation?: string; notes?: string }) => {
    const { data } = await apiClient.post(`/shipments/${id}/deliver`, podData);
    return data;
  },
  uploadPod: async (id: string, formData: FormData) => {
    const { data } = await apiClient.post(`/shipments/${id}/pod/upload-file`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
  },
  initiateRto: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/shipments/${id}/rto`, { reason });
    return data;
  },
  cancel: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/shipments/${id}/cancel`, { reason });
    return data;
  },
  downloadLabel: async (id: string) => {
    const { data } = await apiClient.get<string>(`/shipments/${id}/label/download`);
    return data;
  },
  downloadInvoice: async (id: string) => {
    const { data } = await apiClient.get<string>(`/shipments/${id}/invoice/download`);
    return data;
  },
  generateEwayBill: async (id: string, ewayBillData: {
    transporter_id?: string;
    transporter_name?: string;
    transporter_gstin?: string;
    vehicle_number?: string;
    vehicle_type?: string;
    transport_mode?: string;
    distance_km?: number;
  }) => {
    const { data } = await apiClient.post(`/shipments/${id}/generate-eway-bill`, ewayBillData);
    return data;
  },
  getEwayBillStatus: async (id: string) => {
    const { data } = await apiClient.get(`/shipments/${id}/eway-bill-status`);
    return data;
  },
};

const statusColors: Record<string, string> = {
  CREATED: 'bg-gray-100 text-gray-800',
  PACKED: 'bg-blue-100 text-blue-800',
  READY_FOR_PICKUP: 'bg-cyan-100 text-cyan-800',
  MANIFESTED: 'bg-indigo-100 text-indigo-800',
  SHIPPED: 'bg-purple-100 text-purple-800',
  IN_TRANSIT: 'bg-blue-100 text-blue-800',
  OUT_FOR_DELIVERY: 'bg-yellow-100 text-yellow-800',
  DELIVERED: 'bg-green-100 text-green-800',
  RTO_INITIATED: 'bg-red-100 text-red-800',
  RTO_IN_TRANSIT: 'bg-red-100 text-red-800',
  RTO_DELIVERED: 'bg-orange-100 text-orange-800',
  CANCELLED: 'bg-gray-100 text-gray-600',
};

const slaColors: Record<string, string> = {
  ON_TRACK: 'bg-green-100 text-green-800',
  AT_RISK: 'bg-yellow-100 text-yellow-800',
  BREACHED: 'bg-red-100 text-red-800',
};

export default function ShipmentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const shipmentId = params.id as string;

  const [isPackDialogOpen, setIsPackDialogOpen] = useState(false);
  const [isTrackingDialogOpen, setIsTrackingDialogOpen] = useState(false);
  const [isDeliveryDialogOpen, setIsDeliveryDialogOpen] = useState(false);
  const [isPodDialogOpen, setIsPodDialogOpen] = useState(false);
  const [isRtoDialogOpen, setIsRtoDialogOpen] = useState(false);
  const [isEwayBillDialogOpen, setIsEwayBillDialogOpen] = useState(false);

  const [ewayBillForm, setEwayBillForm] = useState({
    transporter_name: '',
    transporter_gstin: '',
    vehicle_number: '',
    vehicle_type: 'REGULAR',
    transport_mode: 'ROAD',
    distance_km: 0,
  });

  const [packForm, setPackForm] = useState({
    weight_kg: 0,
    length_cm: 0,
    breadth_cm: 0,
    height_cm: 0,
    packages_count: 1,
  });

  const [trackingForm, setTrackingForm] = useState({
    status: '',
    location: '',
    city: '',
    state: '',
    description: '',
  });

  const [deliveryForm, setDeliveryForm] = useState({
    recipient_name: '',
    recipient_relation: '',
    notes: '',
  });

  const [rtoReason, setRtoReason] = useState('');

  const queryClient = useQueryClient();

  const { data: shipment, isLoading } = useQuery({
    queryKey: ['shipment', shipmentId],
    queryFn: () => shipmentApi.get(shipmentId),
    enabled: !!shipmentId,
  });

  const generateAwbMutation = useMutation({
    mutationFn: () => shipmentApi.generateAwb(shipmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shipment', shipmentId] });
      toast.success('AWB generated successfully');
    },
    onError: () => toast.error('Failed to generate AWB'),
  });

  const packMutation = useMutation({
    mutationFn: () => shipmentApi.pack(shipmentId, packForm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shipment', shipmentId] });
      toast.success('Shipment packed');
      setIsPackDialogOpen(false);
    },
    onError: () => toast.error('Failed to update pack details'),
  });

  const trackingMutation = useMutation({
    mutationFn: () => shipmentApi.updateTracking(shipmentId, trackingForm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shipment', shipmentId] });
      toast.success('Tracking updated');
      setIsTrackingDialogOpen(false);
      setTrackingForm({ status: '', location: '', city: '', state: '', description: '' });
    },
    onError: () => toast.error('Failed to update tracking'),
  });

  const deliveryMutation = useMutation({
    mutationFn: () => shipmentApi.markDelivered(shipmentId, deliveryForm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shipment', shipmentId] });
      toast.success('Shipment marked as delivered');
      setIsDeliveryDialogOpen(false);
    },
    onError: () => toast.error('Failed to mark delivered'),
  });

  const rtoMutation = useMutation({
    mutationFn: () => shipmentApi.initiateRto(shipmentId, rtoReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shipment', shipmentId] });
      toast.success('RTO initiated');
      setIsRtoDialogOpen(false);
    },
    onError: () => toast.error('Failed to initiate RTO'),
  });

  const ewayBillMutation = useMutation({
    mutationFn: () => shipmentApi.generateEwayBill(shipmentId, ewayBillForm),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['shipment', shipmentId] });
      toast.success(`E-Way Bill generated! Number: ${data.eway_bill_number || 'Pending'}`);
      setIsEwayBillDialogOpen(false);
      setEwayBillForm({
        transporter_name: '',
        transporter_gstin: '',
        vehicle_number: '',
        vehicle_type: 'REGULAR',
        transport_mode: 'ROAD',
        distance_km: 0,
      });
    },
    onError: (error: any) => toast.error(error.message || 'Failed to generate E-Way Bill'),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!shipment) {
    return (
      <div className="text-center py-12">
        <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h2 className="text-lg font-medium">Shipment not found</h2>
        <Button variant="outline" className="mt-4" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Go Back
        </Button>
      </div>
    );
  }

  const canGenerateAwb = !shipment.awb_number && shipment.status === 'CREATED';
  const canPack = shipment.status === 'CREATED' || shipment.status === 'PACKED';
  const canUpdateTracking = ['SHIPPED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY'].includes(shipment.status);
  const canDeliver = shipment.status === 'OUT_FOR_DELIVERY';
  const canInitiateRto = ['IN_TRANSIT', 'OUT_FOR_DELIVERY'].includes(shipment.status);
  const canGenerateEwayBill = ['PACKED', 'READY_FOR_PICKUP', 'MANIFESTED'].includes(shipment.status) && shipment.awb_number;

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
              <h1 className="text-2xl font-bold">
                Shipment {shipment.awb_number || '(AWB Pending)'}
              </h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[shipment.status]}`}>
                {shipment.status.replace(/_/g, ' ')}
              </span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${slaColors[shipment.sla_status]}`}>
                SLA: {shipment.sla_status.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-muted-foreground mt-1">
              Order: {shipment.order_number}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              try {
                const htmlContent = await shipmentApi.downloadLabel(shipmentId);
                const blob = new Blob([htmlContent], { type: 'text/html' });
                const url = window.URL.createObjectURL(blob);
                const printWindow = window.open(url, '_blank');
                if (printWindow) {
                  printWindow.onload = () => window.URL.revokeObjectURL(url);
                }
                toast.success('Opening label for download/print');
              } catch {
                toast.error('Failed to download label');
              }
            }}
            disabled={!shipment?.awb_number}
          >
            <Download className="mr-2 h-4 w-4" /> Label
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              try {
                const htmlContent = await shipmentApi.downloadInvoice(shipmentId);
                const blob = new Blob([htmlContent], { type: 'text/html' });
                const url = window.URL.createObjectURL(blob);
                const printWindow = window.open(url, '_blank');
                if (printWindow) {
                  printWindow.onload = () => window.URL.revokeObjectURL(url);
                }
                toast.success('Opening invoice for download/print');
              } catch {
                toast.error('Failed to download invoice');
              }
            }}
          >
            <FileText className="mr-2 h-4 w-4" /> Invoice
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.open(`/track/${shipment?.awb_number}`, '_blank')}
            disabled={!shipment?.awb_number}
          >
            <Eye className="mr-2 h-4 w-4" /> Public Tracking
          </Button>
          {canGenerateAwb && (
            <Button onClick={() => generateAwbMutation.mutate()}>
              <QrCode className="mr-2 h-4 w-4" /> Generate AWB
            </Button>
          )}
          {canPack && (
            <Button variant="outline" onClick={() => setIsPackDialogOpen(true)}>
              <Package className="mr-2 h-4 w-4" /> Update Pack
            </Button>
          )}
          {canGenerateEwayBill && (
            <Button variant="outline" onClick={() => setIsEwayBillDialogOpen(true)}>
              <ScrollText className="mr-2 h-4 w-4" /> Generate E-Way Bill
            </Button>
          )}
          {canUpdateTracking && (
            <Button onClick={() => setIsTrackingDialogOpen(true)}>
              <Navigation className="mr-2 h-4 w-4" /> Update Tracking
            </Button>
          )}
          {canDeliver && (
            <Button className="bg-green-600 hover:bg-green-700" onClick={() => setIsDeliveryDialogOpen(true)}>
              <CheckCircle className="mr-2 h-4 w-4" /> Mark Delivered
            </Button>
          )}
          {canInitiateRto && (
            <Button variant="destructive" onClick={() => setIsRtoDialogOpen(true)}>
              <RotateCcw className="mr-2 h-4 w-4" /> Initiate RTO
            </Button>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Payment Mode</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-xl font-bold ${shipment.payment_mode === 'COD' ? 'text-orange-600' : 'text-green-600'}`}>
              {shipment.payment_mode}
            </div>
            {shipment.payment_mode === 'COD' && (
              <div className="text-sm mt-1">
                {formatCurrency(shipment.cod_amount || 0)}
                {shipment.cod_collected && <span className="text-green-600 ml-2">(Collected)</span>}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Weight</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{shipment.chargeable_weight_kg || shipment.weight_kg} kg</div>
            <div className="text-xs text-muted-foreground">
              Actual: {shipment.weight_kg} kg | Vol: {shipment.volumetric_weight_kg || '-'} kg
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Packages</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{shipment.packages_count}</div>
            {shipment.length_cm && (
              <div className="text-xs text-muted-foreground">
                {shipment.length_cm} x {shipment.breadth_cm} x {shipment.height_cm} cm
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Transporter</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">{shipment.transporter_name || 'Not Assigned'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Expected Delivery</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">
              {shipment.expected_delivery_date ? formatDate(shipment.expected_delivery_date) : '-'}
            </div>
            {shipment.actual_delivery_date && (
              <div className="text-xs text-green-600">
                Delivered: {formatDate(shipment.actual_delivery_date)}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Tracking Timeline */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Navigation className="h-5 w-5" /> Tracking History
            </CardTitle>
          </CardHeader>
          <CardContent>
            {shipment.tracking_history.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Truck className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No tracking updates yet</p>
              </div>
            ) : (
              <div className="space-y-4">
                {shipment.tracking_history.map((event, index) => (
                  <div key={event.id} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className={`w-4 h-4 rounded-full ${index === 0 ? 'bg-green-500' : 'bg-muted'}`}>
                        {index === 0 && <CheckCircle className="h-4 w-4 text-white" />}
                      </div>
                      {index < shipment.tracking_history.length - 1 && (
                        <div className="w-0.5 flex-1 bg-muted mt-1" />
                      )}
                    </div>
                    <div className="flex-1 pb-4">
                      <div className="flex items-center justify-between">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColors[event.status] || 'bg-gray-100'}`}>
                          {event.status.replace(/_/g, ' ')}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatDate(event.event_time)}
                        </span>
                      </div>
                      {event.description && (
                        <p className="text-sm mt-1">{event.description}</p>
                      )}
                      {(event.location || event.city) && (
                        <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {[event.location, event.city, event.state].filter(Boolean).join(', ')}
                        </div>
                      )}
                      <div className="text-xs text-muted-foreground mt-1">
                        Source: {event.source}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Delivery Details */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" /> Customer
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="font-medium">{shipment.customer_name}</div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Phone className="h-4 w-4" />
                {shipment.customer_phone}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5" /> Delivery Address
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm space-y-1">
                <div>{shipment.shipping_address.address_line1}</div>
                {shipment.shipping_address.address_line2 && (
                  <div>{shipment.shipping_address.address_line2}</div>
                )}
                <div>
                  {shipment.shipping_address.city}, {shipment.shipping_address.state}
                </div>
                <div className="font-medium">{shipment.shipping_address.pincode}</div>
                {shipment.shipping_address.landmark && (
                  <div className="text-muted-foreground">
                    Landmark: {shipment.shipping_address.landmark}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* POD Section */}
          {shipment.pod_data && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600" /> Proof of Delivery
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="text-muted-foreground">Received By:</div>
                  <div className="font-medium">{shipment.pod_data.recipient_name}</div>
                  {shipment.pod_data.recipient_relation && (
                    <>
                      <div className="text-muted-foreground">Relation:</div>
                      <div>{shipment.pod_data.recipient_relation}</div>
                    </>
                  )}
                  {shipment.pod_data.delivery_time && (
                    <>
                      <div className="text-muted-foreground">Time:</div>
                      <div>{formatDate(shipment.pod_data.delivery_time)}</div>
                    </>
                  )}
                </div>
                {shipment.pod_data.signature_url && (
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Signature:</div>
                    <img src={shipment.pod_data.signature_url} alt="Signature" className="border rounded h-16" />
                  </div>
                )}
                {shipment.pod_data.photo_urls && shipment.pod_data.photo_urls.length > 0 && (
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Photos:</div>
                    <div className="flex gap-2">
                      {shipment.pod_data.photo_urls.map((url, i) => (
                        <img key={i} src={url} alt={`POD ${i + 1}`} className="border rounded h-16 w-16 object-cover" />
                      ))}
                    </div>
                  </div>
                )}
                {shipment.pod_data.latitude && shipment.pod_data.longitude && (
                  <div className="text-xs text-muted-foreground">
                    GPS: {shipment.pod_data.latitude.toFixed(6)}, {shipment.pod_data.longitude.toFixed(6)}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Pack Dialog */}
      <Dialog open={isPackDialogOpen} onOpenChange={setIsPackDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Pack Details</DialogTitle>
            <DialogDescription>Enter package dimensions and weight</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Weight (kg)</label>
                <Input
                  type="number"
                  step="0.1"
                  value={packForm.weight_kg}
                  onChange={(e) => setPackForm({ ...packForm, weight_kg: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Packages</label>
                <Input
                  type="number"
                  value={packForm.packages_count}
                  onChange={(e) => setPackForm({ ...packForm, packages_count: parseInt(e.target.value) || 1 })}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Length (cm)</label>
                <Input
                  type="number"
                  value={packForm.length_cm}
                  onChange={(e) => setPackForm({ ...packForm, length_cm: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Breadth (cm)</label>
                <Input
                  type="number"
                  value={packForm.breadth_cm}
                  onChange={(e) => setPackForm({ ...packForm, breadth_cm: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Height (cm)</label>
                <Input
                  type="number"
                  value={packForm.height_cm}
                  onChange={(e) => setPackForm({ ...packForm, height_cm: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>
            {packForm.length_cm > 0 && packForm.breadth_cm > 0 && packForm.height_cm > 0 && (
              <div className="p-3 bg-muted rounded-lg text-sm">
                <div className="flex justify-between">
                  <span>Volumetric Weight:</span>
                  <span className="font-medium">
                    {((packForm.length_cm * packForm.breadth_cm * packForm.height_cm) / 5000).toFixed(2)} kg
                  </span>
                </div>
                <div className="flex justify-between mt-1">
                  <span>Chargeable Weight:</span>
                  <span className="font-bold">
                    {Math.max(packForm.weight_kg, (packForm.length_cm * packForm.breadth_cm * packForm.height_cm) / 5000).toFixed(2)} kg
                  </span>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsPackDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => packMutation.mutate()}>
              <Package className="mr-2 h-4 w-4" /> Update Pack
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Tracking Dialog */}
      <Dialog open={isTrackingDialogOpen} onOpenChange={setIsTrackingDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Tracking</DialogTitle>
            <DialogDescription>Add a tracking event for this shipment</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <Select value={trackingForm.status} onValueChange={(v) => setTrackingForm({ ...trackingForm, status: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="IN_TRANSIT">In Transit</SelectItem>
                  <SelectItem value="REACHED_HUB">Reached Hub</SelectItem>
                  <SelectItem value="OUT_FOR_DELIVERY">Out for Delivery</SelectItem>
                  <SelectItem value="DELIVERY_ATTEMPTED">Delivery Attempted</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">City</label>
                <Input
                  value={trackingForm.city}
                  onChange={(e) => setTrackingForm({ ...trackingForm, city: e.target.value })}
                  placeholder="City"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">State</label>
                <Input
                  value={trackingForm.state}
                  onChange={(e) => setTrackingForm({ ...trackingForm, state: e.target.value })}
                  placeholder="State"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Location/Facility</label>
              <Input
                value={trackingForm.location}
                onChange={(e) => setTrackingForm({ ...trackingForm, location: e.target.value })}
                placeholder="Hub/Center name"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <Textarea
                value={trackingForm.description}
                onChange={(e) => setTrackingForm({ ...trackingForm, description: e.target.value })}
                placeholder="Additional details"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsTrackingDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => trackingMutation.mutate()} disabled={!trackingForm.status}>
              <Navigation className="mr-2 h-4 w-4" /> Update Tracking
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delivery Dialog */}
      <Dialog open={isDeliveryDialogOpen} onOpenChange={setIsDeliveryDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mark as Delivered</DialogTitle>
            <DialogDescription>Enter delivery confirmation details (POD)</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Received By *</label>
              <Input
                value={deliveryForm.recipient_name}
                onChange={(e) => setDeliveryForm({ ...deliveryForm, recipient_name: e.target.value })}
                placeholder="Name of person who received"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Relation to Customer</label>
              <Select
                value={deliveryForm.recipient_relation}
                onValueChange={(v) => setDeliveryForm({ ...deliveryForm, recipient_relation: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select relation" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="SELF">Self</SelectItem>
                  <SelectItem value="FAMILY">Family Member</SelectItem>
                  <SelectItem value="GUARD">Security Guard</SelectItem>
                  <SelectItem value="NEIGHBOR">Neighbor</SelectItem>
                  <SelectItem value="OFFICE">Office Staff</SelectItem>
                  <SelectItem value="OTHER">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Notes</label>
              <Textarea
                value={deliveryForm.notes}
                onChange={(e) => setDeliveryForm({ ...deliveryForm, notes: e.target.value })}
                placeholder="Any delivery notes"
              />
            </div>
            <div className="p-4 border-2 border-dashed rounded-lg text-center">
              <Camera className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">Upload signature & photos</p>
              <Button variant="outline" size="sm" className="mt-2" onClick={() => setIsPodDialogOpen(true)}>
                <Upload className="mr-2 h-4 w-4" /> Upload POD
              </Button>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeliveryDialogOpen(false)}>Cancel</Button>
            <Button
              className="bg-green-600 hover:bg-green-700"
              onClick={() => deliveryMutation.mutate()}
              disabled={!deliveryForm.recipient_name}
            >
              <CheckCircle className="mr-2 h-4 w-4" /> Confirm Delivery
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* RTO Dialog */}
      <Dialog open={isRtoDialogOpen} onOpenChange={setIsRtoDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Initiate Return to Origin (RTO)</DialogTitle>
            <DialogDescription>
              This will mark the shipment for return to warehouse
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Reason for RTO *</label>
              <Select value={rtoReason} onValueChange={setRtoReason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select reason" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CUSTOMER_REFUSED">Customer Refused</SelectItem>
                  <SelectItem value="CUSTOMER_NOT_AVAILABLE">Customer Not Available</SelectItem>
                  <SelectItem value="WRONG_ADDRESS">Wrong Address</SelectItem>
                  <SelectItem value="CUSTOMER_REQUESTED">Customer Requested Cancellation</SelectItem>
                  <SelectItem value="DELIVERY_ATTEMPTS_EXHAUSTED">Delivery Attempts Exhausted</SelectItem>
                  <SelectItem value="DAMAGED_IN_TRANSIT">Damaged in Transit</SelectItem>
                  <SelectItem value="OTHER">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRtoDialogOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={() => rtoMutation.mutate()} disabled={!rtoReason}>
              <RotateCcw className="mr-2 h-4 w-4" /> Initiate RTO
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* E-Way Bill Dialog */}
      <Dialog open={isEwayBillDialogOpen} onOpenChange={setIsEwayBillDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate E-Way Bill</DialogTitle>
            <DialogDescription>
              Generate E-Way Bill for inter-state or intra-state movement of goods above Rs. 50,000
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Transporter Name</label>
                <Input
                  value={ewayBillForm.transporter_name}
                  onChange={(e) => setEwayBillForm({ ...ewayBillForm, transporter_name: e.target.value })}
                  placeholder="Enter transporter name"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Transporter GSTIN</label>
                <Input
                  value={ewayBillForm.transporter_gstin}
                  onChange={(e) => setEwayBillForm({ ...ewayBillForm, transporter_gstin: e.target.value })}
                  placeholder="15-digit GSTIN"
                  maxLength={15}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Vehicle Number *</label>
                <Input
                  value={ewayBillForm.vehicle_number}
                  onChange={(e) => setEwayBillForm({ ...ewayBillForm, vehicle_number: e.target.value.toUpperCase() })}
                  placeholder="e.g., MH12AB1234"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Distance (km) *</label>
                <Input
                  type="number"
                  value={ewayBillForm.distance_km}
                  onChange={(e) => setEwayBillForm({ ...ewayBillForm, distance_km: parseInt(e.target.value) || 0 })}
                  placeholder="Approx. distance"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Transport Mode</label>
                <Select
                  value={ewayBillForm.transport_mode}
                  onValueChange={(v) => setEwayBillForm({ ...ewayBillForm, transport_mode: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ROAD">Road</SelectItem>
                    <SelectItem value="RAIL">Rail</SelectItem>
                    <SelectItem value="AIR">Air</SelectItem>
                    <SelectItem value="SHIP">Ship</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Vehicle Type</label>
                <Select
                  value={ewayBillForm.vehicle_type}
                  onValueChange={(v) => setEwayBillForm({ ...ewayBillForm, vehicle_type: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="REGULAR">Regular</SelectItem>
                    <SelectItem value="ODC">Over Dimensional Cargo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="p-4 bg-muted rounded-lg text-sm">
              <div className="flex items-center gap-2 text-muted-foreground">
                <ScrollText className="h-4 w-4" />
                E-Way Bill is mandatory for goods movement above Rs. 50,000
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEwayBillDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={() => ewayBillMutation.mutate()}
              disabled={ewayBillMutation.isPending || !ewayBillForm.vehicle_number || ewayBillForm.distance_km <= 0}
            >
              {ewayBillMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <ScrollText className="mr-2 h-4 w-4" />
              )}
              {ewayBillMutation.isPending ? 'Generating...' : 'Generate E-Way Bill'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
