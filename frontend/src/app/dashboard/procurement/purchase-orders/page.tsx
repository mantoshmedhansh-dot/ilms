'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Plus, Eye, FileText, Send, CheckCircle, X, Loader2, Trash2, Download, Printer, Package, Barcode, Lock, FileSpreadsheet, Pencil, Shield } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/providers/auth-provider';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import { purchaseOrdersApi, purchaseRequisitionsApi, PurchaseRequisition, vendorsApi, warehousesApi, productsApi, serializationApi, companyApi, Company, ModelCodeReference, SupplierCode as SupplierCodeType, POSerialsResponse } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';

interface POItem {
  id?: string;
  po_id?: string;
  product_id: string;
  product_name?: string;
  sku?: string;
  quantity?: number;
  quantity_ordered?: number;
  quantity_received?: number;
  unit_price: number;
  gst_rate: number;
  total?: number;
  monthly_quantities?: Record<string, number>;
  uom?: string;
}

interface MonthQuantity {
  month: string;
  quantity: number;
}

interface PurchaseOrder {
  id: string;
  po_number: string;
  vendor_id: string;
  vendor?: { id: string; name: string; code?: string; vendor_code?: string };
  delivery_warehouse_id?: string;
  warehouse_id?: string;
  warehouse?: { id: string; name: string };
  status: string;
  po_date?: string;
  expected_delivery_date?: string;
  credit_days?: number;
  subtotal?: number;
  gst_amount: number;
  grand_total: number;
  notes?: string;
  payment_terms?: string;
  advance_required?: number;
  advance_paid?: number;
  freight_charges?: number;
  packing_charges?: number;
  other_charges?: number;
  terms_and_conditions?: string;
  special_instructions?: string;
  internal_notes?: string;
  items?: POItem[];
  created_at: string;
}

interface Vendor {
  id: string;
  name: string;
  code?: string;
  vendor_code?: string;
}

interface Warehouse {
  id: string;
  name: string;
  code: string;
}

interface Product {
  id: string;
  name: string;
  sku: string;
  mrp: number;
}

export default function PurchaseOrdersPage() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { permissions } = useAuth();
  const isSuperAdmin = permissions?.is_super_admin ?? false;
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [isSubmitOpen, setIsSubmitOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isSuccessDialogOpen, setIsSuccessDialogOpen] = useState(false);
  const [createdPO, setCreatedPO] = useState<PurchaseOrder | null>(null);
  const [selectedPO, setSelectedPO] = useState<PurchaseOrder | null>(null);
  const [urlPrId, setUrlPrId] = useState<string | null>(null);

  const [isMultiDelivery, setIsMultiDelivery] = useState(false);
  const [deliveryMonths, setDeliveryMonths] = useState<string[]>([]);
  const [nextPONumber, setNextPONumber] = useState<string>('');
  const [isLoadingPONumber, setIsLoadingPONumber] = useState(false);

  // Multi-lot payment dialog state
  const [isPaymentDialogOpen, setIsPaymentDialogOpen] = useState(false);
  const [paymentLot, setPaymentLot] = useState<any>(null);
  const [paymentType, setPaymentType] = useState<'ADVANCE' | 'BALANCE'>('ADVANCE');
  const [paymentAmount, setPaymentAmount] = useState<number>(0);
  const [paymentReference, setPaymentReference] = useState<string>('');
  const [paymentDate, setPaymentDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [isRecordingPayment, setIsRecordingPayment] = useState(false);

  // Edit PO state - comprehensive editing of all fields
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editPOData, setEditPOData] = useState<{
    vendor_id: string;
    expected_delivery_date: string;
    credit_days: number;
    payment_terms: string;
    advance_required: number;
    advance_paid: number;
    freight_charges: number;
    packing_charges: number;
    other_charges: number;
    terms_and_conditions: string;
    special_instructions: string;
    internal_notes: string;
    items: POItem[];
  }>({
    vendor_id: '',
    expected_delivery_date: '',
    credit_days: 30,
    payment_terms: '',
    advance_required: 0,
    advance_paid: 0,
    freight_charges: 0,
    packing_charges: 0,
    other_charges: 0,
    terms_and_conditions: '',
    special_instructions: '',
    internal_notes: '',
    items: [],
  });
  const [editNewItem, setEditNewItem] = useState({
    product_id: '',
    quantity: 1,
    unit_price: 0,
    gst_rate: 18,
  });

  // Admin status edit state (Super Admin only)
  const [isEditStatusDialogOpen, setIsEditStatusDialogOpen] = useState(false);
  const [editStatusData, setEditStatusData] = useState<{ new_status: string; reason: string }>({
    new_status: '',
    reason: '',
  });

  const [formData, setFormData] = useState({
    requisition_id: '',  // Required - PO must be linked to an approved PR
    vendor_id: '',
    expected_delivery_date: '',
    credit_days: 30,
    advance_required: 0,  // Advance payment amount required
    advance_paid: 0,  // Advance payment already paid
    bill_to: null as any,  // Bill To address (from warehouse)
    ship_to: null as any,  // Ship To address (warehouse or manual)
    terms_and_conditions: '',  // Terms & Conditions (previously notes)
    items: [] as POItem[],
  });

  // Selected PR object for reference
  const [selectedPR, setSelectedPR] = useState<PurchaseRequisition | null>(null);

  const [newItem, setNewItem] = useState({
    product_id: '',
    quantity: 1,
    unit_price: 0,
    gst_rate: 18,
    monthlyQtys: {} as Record<string, number>,
  });

  // Ship To type selection
  const [shipToType, setShipToType] = useState<'warehouse' | 'other' | ''>('');
  const [manualShipTo, setManualShipTo] = useState({
    name: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    pincode: '',
  });

  // Generate next 6 months for multi-delivery selection
  const getAvailableMonths = () => {
    const months = [];
    const today = new Date();
    for (let i = 0; i < 6; i++) {
      const d = new Date(today.getFullYear(), today.getMonth() + i, 1);
      const monthCode = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      const monthName = d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
      months.push({ code: monthCode, name: monthName });
    }
    return months;
  };

  const availableMonths = getAvailableMonths();

  // Queries
  const { data, isLoading } = useQuery({
    queryKey: ['purchase-orders', page, pageSize, statusFilter],
    queryFn: () => purchaseOrdersApi.list({
      page: page + 1,
      size: pageSize,
      status: statusFilter === 'all' ? undefined : statusFilter
    }),
  });

  const { data: vendorsData } = useQuery({
    queryKey: ['vendors-dropdown-active'],
    queryFn: () => vendorsApi.list({ size: 100, status: 'ACTIVE' }),
  });

  const { data: warehousesData } = useQuery({
    queryKey: ['warehouses-dropdown'],
    queryFn: () => warehousesApi.list({ size: 100 }),
  });

  const { data: productsData } = useQuery({
    queryKey: ['products-dropdown'],
    queryFn: () => productsApi.list({ size: 100 }),
  });

  // Open Purchase Requisitions query (for PR dropdown)
  const { data: openPRsData } = useQuery({
    queryKey: ['open-purchase-requisitions'],
    queryFn: () => purchaseRequisitionsApi.getOpenForPO(),
  });

  // Serialization queries - only fetch linked model codes for barcode generation
  const { data: modelCodesData } = useQuery({
    queryKey: ['model-codes-linked'],
    queryFn: () => serializationApi.getModelCodes(true, undefined, true), // activeOnly=true, itemType=undefined, linkedOnly=true
  });

  const { data: supplierCodesData } = useQuery({
    queryKey: ['supplier-codes'],
    queryFn: () => serializationApi.getSupplierCodes(true),
  });

  // Company data for Bill To address
  const { data: companyData } = useQuery({
    queryKey: ['company-primary'],
    queryFn: () => companyApi.getPrimary(),
  });

  // State for serial number preview in PO view
  const [poSerials, setPOSerials] = useState<POSerialsResponse | null>(null);
  const [loadingSerials, setLoadingSerials] = useState(false);

  // Handle URL parameters for Convert to PO navigation or direct create
  useEffect(() => {
    const createParam = searchParams.get('create');
    const prIdParam = searchParams.get('pr_id');

    if (createParam === 'true') {
      if (prIdParam) {
        setUrlPrId(prIdParam);
      }
      setIsCreateOpen(true);
      // Clear URL params after handling
      router.replace('/dashboard/procurement/purchase-orders', { scroll: false });
    }
  }, [searchParams, router]);

  // Fetch next PO number when dialog opens
  useEffect(() => {
    if (isCreateOpen) {
      const fetchNextPONumber = async () => {
        setIsLoadingPONumber(true);
        try {
          const result = await purchaseOrdersApi.getNextNumber();
          setNextPONumber(result.next_number);
        } catch (error) {
          console.error('Failed to fetch next PO number:', error);
        } finally {
          setIsLoadingPONumber(false);
        }
      };
      fetchNextPONumber();
    }
  }, [isCreateOpen]);

  // Auto-select PR when openPRsData loads and urlPrId is set
  useEffect(() => {
    if (urlPrId && openPRsData && openPRsData.length > 0 && isCreateOpen) {
      const pr = openPRsData.find((p: PurchaseRequisition) => p.id === urlPrId);
      if (pr) {
        handlePRSelect(urlPrId);
        setUrlPrId(null); // Clear after selection
      }
    }
  }, [urlPrId, openPRsData, isCreateOpen]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: purchaseOrdersApi.create,
    onSuccess: (data: PurchaseOrder) => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      toast.success('Purchase order created successfully');
      setCreatedPO(data);
      setIsSuccessDialogOpen(true);
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create PO'),
  });

  const submitMutation = useMutation({
    mutationFn: purchaseOrdersApi.submit,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      toast.success('PO submitted for approval');
      setIsSubmitOpen(false);
      setSelectedPO(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to submit PO'),
  });

  const approveMutation = useMutation({
    mutationFn: purchaseOrdersApi.approve,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      toast.success('PO approved successfully');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to approve PO'),
  });

  const deleteMutation = useMutation({
    mutationFn: purchaseOrdersApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      toast.success('PO deleted successfully');
      setIsDeleteOpen(false);
      setSelectedPO(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete PO'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      purchaseOrdersApi.update(id, data as Parameters<typeof purchaseOrdersApi.update>[1]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      toast.success('PO updated successfully');
      setIsEditDialogOpen(false);
      setSelectedPO(null);
      setEditPOData({
        vendor_id: '',
        expected_delivery_date: '',
        credit_days: 30,
        payment_terms: '',
        advance_required: 0,
        advance_paid: 0,
        freight_charges: 0,
        packing_charges: 0,
        other_charges: 0,
        terms_and_conditions: '',
        special_instructions: '',
        internal_notes: '',
        items: [],
      });
      setEditNewItem({ product_id: '', quantity: 1, unit_price: 0, gst_rate: 18 });
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update PO'),
  });

  // Admin status update mutation (Super Admin only)
  const adminUpdateStatusMutation = useMutation({
    mutationFn: ({ id, newStatus, reason }: { id: string; newStatus: string; reason?: string }) =>
      purchaseOrdersApi.adminUpdateStatus(id, newStatus, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      toast.success('PO status updated successfully');
      setIsEditStatusDialogOpen(false);
      setSelectedPO(null);
      setEditStatusData({ new_status: '', reason: '' });
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update PO status'),
  });

  // Handle Edit PO - Fetch full details including items
  const handleEditPO = async (po: PurchaseOrder) => {
    setSelectedPO(po);
    try {
      // Fetch full PO details with items
      const fullDetails = await purchaseOrdersApi.getById(po.id);
      setEditPOData({
        vendor_id: fullDetails.vendor_id || po.vendor_id || '',
        expected_delivery_date: fullDetails.expected_delivery_date || po.expected_delivery_date || '',
        credit_days: fullDetails.credit_days ?? 30,
        payment_terms: fullDetails.payment_terms || '',
        advance_required: Number(fullDetails.advance_required) || 0,
        advance_paid: Number(fullDetails.advance_paid) || 0,
        freight_charges: Number(fullDetails.freight_charges) || 0,
        packing_charges: Number(fullDetails.packing_charges) || 0,
        other_charges: Number(fullDetails.other_charges) || 0,
        terms_and_conditions: fullDetails.terms_and_conditions || '',
        special_instructions: fullDetails.special_instructions || '',
        internal_notes: fullDetails.internal_notes || '',
        items: (fullDetails.items || []).map((item: any) => ({
          id: item.id,
          product_id: item.product_id || '',
          product_name: item.product_name || '',
          sku: item.sku || '',
          quantity: item.quantity_ordered || item.quantity || 0,
          quantity_ordered: item.quantity_ordered || item.quantity || 0,
          unit_price: Number(item.unit_price) || 0,
          gst_rate: Number(item.gst_rate) || 18,
          uom: item.uom || 'PCS',
        })),
      });
    } catch {
      // Fallback to basic data if fetch fails
      setEditPOData({
        vendor_id: po.vendor_id || '',
        expected_delivery_date: po.expected_delivery_date || '',
        credit_days: 30,
        payment_terms: '',
        advance_required: 0,
        advance_paid: 0,
        freight_charges: 0,
        packing_charges: 0,
        other_charges: 0,
        terms_and_conditions: '',
        special_instructions: '',
        internal_notes: '',
        items: [],
      });
    }
    setIsEditDialogOpen(true);
  };

  // Helper functions for editing items in Edit modal
  const handleEditAddItem = () => {
    if (!editNewItem.product_id) {
      toast.error('Please select a product');
      return;
    }
    const product = products.find((p: Product) => p.id === editNewItem.product_id);
    if (!product) return;

    const newItem: POItem = {
      product_id: product.id,
      product_name: product.name,
      sku: product.sku,
      quantity: editNewItem.quantity,
      quantity_ordered: editNewItem.quantity,
      unit_price: editNewItem.unit_price,
      gst_rate: editNewItem.gst_rate,
      uom: 'PCS',
    };

    setEditPOData({
      ...editPOData,
      items: [...editPOData.items, newItem],
    });
    setEditNewItem({ product_id: '', quantity: 1, unit_price: 0, gst_rate: 18 });
  };

  const handleEditRemoveItem = (index: number) => {
    setEditPOData({
      ...editPOData,
      items: editPOData.items.filter((_, i) => i !== index),
    });
  };

  const handleEditUpdateItem = (index: number, field: string, value: any) => {
    const updatedItems = [...editPOData.items];
    updatedItems[index] = { ...updatedItems[index], [field]: value };
    setEditPOData({ ...editPOData, items: updatedItems });
  };

  // Calculate totals for Edit modal
  const calculateEditTotals = () => {
    const subtotal = editPOData.items.reduce((sum, item) => {
      const qty = Number(item.quantity_ordered) || Number(item.quantity) || 0;
      const price = Number(item.unit_price) || 0;
      return sum + (qty * price);
    }, 0);
    const gst = editPOData.items.reduce((sum, item) => {
      const qty = Number(item.quantity_ordered) || Number(item.quantity) || 0;
      const price = Number(item.unit_price) || 0;
      const rate = Number(item.gst_rate) || 0;
      return sum + (qty * price * (rate / 100));
    }, 0);
    // Ensure all charges are valid numbers, default to 0 if NaN
    const freight = Number(editPOData.freight_charges) || 0;
    const packing = Number(editPOData.packing_charges) || 0;
    const other = Number(editPOData.other_charges) || 0;
    const charges = freight + packing + other;
    return { subtotal, gst, charges, total: subtotal + gst + charges };
  };

  const handleUpdatePO = () => {
    if (!selectedPO) return;
    if (editPOData.items.length === 0) {
      toast.error('Please add at least one item');
      return;
    }
    updateMutation.mutate({
      id: selectedPO.id,
      data: {
        vendor_id: editPOData.vendor_id || undefined,
        expected_delivery_date: editPOData.expected_delivery_date || undefined,
        credit_days: editPOData.credit_days ?? undefined,
        payment_terms: editPOData.payment_terms || undefined,
        advance_required: editPOData.advance_required ?? undefined,
        advance_paid: editPOData.advance_paid ?? undefined,
        freight_charges: editPOData.freight_charges ?? undefined,
        packing_charges: editPOData.packing_charges ?? undefined,
        other_charges: editPOData.other_charges ?? undefined,
        terms_and_conditions: editPOData.terms_and_conditions || undefined,
        special_instructions: editPOData.special_instructions || undefined,
        internal_notes: editPOData.internal_notes || undefined,
        items: editPOData.items.map(item => ({
          product_id: item.product_id,
          product_name: item.product_name || '',
          sku: item.sku || '',
          quantity_ordered: Number(item.quantity_ordered) || Number(item.quantity) || 0,
          unit_price: Number(item.unit_price) || 0,
          gst_rate: Number(item.gst_rate) || 18,
          uom: item.uom || 'PCS',
          discount_percentage: 0,
          hsn_code: '',
        })),
      },
    });
  };

  // Handle Edit Status (Super Admin only)
  const handleEditStatus = (po: PurchaseOrder) => {
    setSelectedPO(po);
    setEditStatusData({ new_status: po.status, reason: '' });
    setIsEditStatusDialogOpen(true);
  };

  const handleUpdateStatus = () => {
    if (!selectedPO || !editStatusData.new_status) return;
    adminUpdateStatusMutation.mutate({
      id: selectedPO.id,
      newStatus: editStatusData.new_status,
      reason: editStatusData.reason || undefined,
    });
  };

  // Handle lot payment recording
  const handleRecordPayment = async () => {
    if (!selectedPO || !paymentLot) return;

    setIsRecordingPayment(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/purchase/orders/${selectedPO.id}/delivery-schedules/${paymentLot.id}/payment`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
          body: JSON.stringify({
            payment_type: paymentType,
            amount: paymentAmount,
            payment_date: paymentDate,
            payment_reference: paymentReference,
          }),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to record payment');
      }

      toast.success(`${paymentType === 'ADVANCE' ? 'Advance' : 'Balance'} payment recorded successfully`);
      setIsPaymentDialogOpen(false);
      setPaymentLot(null);
      setPaymentReference('');

      // Refresh PO details
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });

      // Refresh the selected PO to update delivery schedules
      if (selectedPO) {
        const updatedPO = await purchaseOrdersApi.getById(selectedPO.id);
        setSelectedPO(updatedPO);
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to record payment');
    } finally {
      setIsRecordingPayment(false);
    }
  };

  const handleDownload = async (po: PurchaseOrder) => {
    try {
      // Fetch HTML with auth token, then open in new tab
      const htmlContent = await purchaseOrdersApi.download(po.id);
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => window.URL.revokeObjectURL(url);
      }
      toast.success('Opening PO for download/print');
    } catch {
      toast.error('Failed to download PO');
    }
  };

  const handlePrint = async (po: PurchaseOrder) => {
    try {
      // Fetch HTML with auth token, then open in new tab for printing
      const htmlContent = await purchaseOrdersApi.download(po.id);
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => {
          window.URL.revokeObjectURL(url);
          printWindow.print();
        };
      }
    } catch {
      toast.error('Failed to print PO');
    }
  };

  const handleDownloadBarcodesCSV = async (po: PurchaseOrder) => {
    try {
      // Try to get actual serials first (if already generated)
      const serials = await serializationApi.getByPO(po.id);

      if (serials.serials && serials.serials.length > 0) {
        // Export actual generated serials
        const csv = await serializationApi.exportPOSerials(po.id, 'csv');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `barcodes_${po.po_number}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        toast.success('Barcodes CSV downloaded');
      } else {
        // Generate preview barcodes based on PO items
        const vendor = vendors.find((v: Vendor) => v.id === po.vendor_id);
        const supplierCode = vendor ? getSupplierCodeForVendor(vendor.id) : undefined;

        if (!supplierCode) {
          toast.error('Supplier code not mapped. Please configure in Serialization settings.');
          return;
        }

        // Generate preview barcodes
        const getYearCode = (year: number) => 'ZABCDEFGHIJ'[(year - 2025) % 11] || 'Z';
        const getMonthCode = (month: number) => 'ABCDEFGHIJKL'[(month - 1) % 12] || 'A';
        const now = new Date();
        const yearCode = getYearCode(now.getFullYear());
        const monthCode = getMonthCode(now.getMonth() + 1);

        const csvRows = ['Barcode,Product,SKU,Model Code,Serial Number'];
        let globalSerial = 1;

        po.items?.forEach(item => {
          const modelCode = getModelCodeForProduct(item.product_id, item.sku);
          if (modelCode) {
            const prefix = `AP${supplierCode.code}${yearCode}${monthCode}${modelCode.model_code}`;
            for (let i = 0; i < (item.quantity || item.quantity_ordered || 0); i++) {
              const serial = String(globalSerial).padStart(6, '0');
              csvRows.push(`${prefix}${serial},${item.product_name || ''},${item.sku || ''},${modelCode.model_code},${globalSerial}`);
              globalSerial++;
            }
          }
        });

        if (csvRows.length === 1) {
          toast.error('No model codes mapped for products. Please configure in Serialization settings.');
          return;
        }

        const csv = csvRows.join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `barcodes_preview_${po.po_number}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        toast.success('Barcodes preview CSV downloaded (final serials will be assigned on approval)');
      }
    } catch {
      toast.error('Failed to download barcodes CSV');
    }
  };

  const resetForm = () => {
    setFormData({
      requisition_id: '',
      vendor_id: '',
      expected_delivery_date: '',
      credit_days: 30,
      advance_required: 0,
      advance_paid: 0,
      bill_to: null,
      ship_to: null,
      terms_and_conditions: '',
      items: [],
    });
    setSelectedPR(null);
    setNewItem({ product_id: '', quantity: 1, unit_price: 0, gst_rate: 18, monthlyQtys: {} });
    setIsMultiDelivery(false);
    setDeliveryMonths([]);
    setNextPONumber('');
    setShipToType('');
    setManualShipTo({ name: '', address_line1: '', address_line2: '', city: '', state: '', pincode: '' });
    setIsCreateOpen(false);
  };

  const handleAddItem = () => {
    if (!selectedPR) {
      toast.error('Please select a Purchase Requisition first');
      return;
    }

    if (!newItem.product_id) {
      toast.error('Please select a product from the PR');
      return;
    }

    if (newItem.unit_price <= 0) {
      toast.error('Please enter a valid unit price');
      return;
    }

    // Get month-wise quantities (filter out zero values)
    const monthQtys = Object.entries(newItem.monthlyQtys).reduce((acc, [month, qty]) => {
      if (qty && qty > 0) acc[month] = qty;
      return acc;
    }, {} as Record<string, number>);

    if (Object.keys(monthQtys).length === 0) {
      toast.error('Please enter quantities for at least one delivery month');
      return;
    }

    const totalQty = Object.values(monthQtys).reduce((sum, q) => sum + q, 0);

    // Get product info from PR item
    const prItem = selectedPR.items.find(item => item.product_id === newItem.product_id);
    if (!prItem) {
      toast.error('Product not found in selected PR');
      return;
    }

    // Update delivery months for the PO
    const allMonths = new Set([...deliveryMonths, ...Object.keys(monthQtys)]);
    setDeliveryMonths(Array.from(allMonths).sort());

    // Enable multi-delivery mode since we're using month-wise quantities
    if (Object.keys(monthQtys).length > 0) {
      setIsMultiDelivery(true);
    }

    setFormData({
      ...formData,
      items: [...formData.items, {
        product_id: newItem.product_id,
        product_name: prItem.product_name,
        sku: prItem.sku,
        quantity: totalQty,
        unit_price: newItem.unit_price,
        gst_rate: newItem.gst_rate,
        uom: prItem.uom || 'Nos',
        monthly_quantities: monthQtys,
      }],
    });
    setNewItem({ product_id: '', quantity: 1, unit_price: 0, gst_rate: 18, monthlyQtys: {} });
  };

  const handleRemoveItem = (index: number) => {
    setFormData({
      ...formData,
      items: formData.items.filter((_, i) => i !== index),
    });
  };

  const handleCreatePO = () => {
    // Validate: PR selection is mandatory
    if (!formData.requisition_id) {
      toast.error('Please select an approved Purchase Requisition first');
      return;
    }
    if (!formData.vendor_id || formData.items.length === 0) {
      toast.error('Please select vendor and add at least one item');
      return;
    }
    if (!formData.bill_to) {
      toast.error('Please select a Bill To address');
      return;
    }
    if (!formData.ship_to) {
      toast.error('Please select or enter a Ship To address');
      return;
    }

    // Validate: PO quantity cannot exceed PR quantity for any item
    const overLimitItems = formData.items.filter(item => {
      const prItem = selectedPR?.items.find(pi => pi.product_id === item.product_id);
      return (item.quantity ?? 0) > (prItem?.quantity_requested || 0);
    });
    if (overLimitItems.length > 0) {
      toast.error('PO quantity cannot exceed PR quantity. Please adjust quantities.');
      return;
    }

    // Get delivery_warehouse_id from ship_to if it's a warehouse, otherwise use bill_to warehouse
    const deliveryWarehouseId = formData.ship_to?.warehouse_id || formData.bill_to?.warehouse_id;

    if (!deliveryWarehouseId) {
      toast.error('Please select a valid warehouse for Bill To or Ship To address');
      return;
    }

    const poPayload = {
      requisition_id: formData.requisition_id,  // Link PO to PR
      vendor_id: formData.vendor_id,
      delivery_warehouse_id: deliveryWarehouseId,
      expected_delivery_date: formData.expected_delivery_date || undefined,
      credit_days: formData.credit_days,
      advance_required: formData.advance_required || 0,  // Advance payment required
      advance_paid: formData.advance_paid || 0,  // Advance payment already paid
      bill_to: formData.bill_to || undefined,  // Bill To address
      ship_to: formData.ship_to || undefined,  // Ship To address
      terms_and_conditions: formData.terms_and_conditions || undefined,  // Terms & Conditions
      items: formData.items.map(item => ({
        product_id: item.product_id || undefined,
        product_name: item.product_name || 'Unknown Product',
        sku: item.sku || 'N/A',
        quantity_ordered: item.quantity || 1,
        unit_price: item.unit_price || 0,
        discount_percentage: 0,
        gst_rate: item.gst_rate ?? 18,
        monthly_quantities: item.monthly_quantities || undefined,
      })),
    };

    console.log('Creating PO with payload:', JSON.stringify(poPayload, null, 2));
    createMutation.mutate(poPayload as any);
  };

  const handleViewDetails = async (po: PurchaseOrder) => {
    try {
      const detail = await purchaseOrdersApi.getById(po.id);
      setSelectedPO(detail);
      setIsViewOpen(true);

      // Fetch serial numbers for the PO
      setLoadingSerials(true);
      try {
        const serials = await serializationApi.getByPO(po.id);
        setPOSerials(serials);
      } catch {
        setPOSerials(null);
      } finally {
        setLoadingSerials(false);
      }
    } catch {
      setSelectedPO(po);
      setIsViewOpen(true);
      setPOSerials(null);
    }
  };

  const calculateTotals = () => {
    const subtotal = formData.items.reduce((sum, item) => sum + ((item.quantity ?? 0) * item.unit_price), 0);
    const gst = formData.items.reduce((sum, item) => sum + ((item.quantity ?? 0) * item.unit_price * (item.gst_rate ?? 0) / 100), 0);
    return { subtotal, gst, total: subtotal + gst };
  };

  const vendors = Array.isArray(vendorsData?.items) ? vendorsData.items : [];
  const warehouses = Array.isArray(warehousesData?.items) ? warehousesData.items : [];
  const products = Array.isArray(productsData?.items) ? productsData.items : [];
  const openPRs = Array.isArray(openPRsData) ? openPRsData : [];
  const modelCodes = Array.isArray(modelCodesData) ? modelCodesData : [];
  const supplierCodes = Array.isArray(supplierCodesData) ? supplierCodesData : [];
  const totals = calculateTotals();

  // Helper to get model code for a product - prioritize product_id match over SKU match
  const getModelCodeForProduct = (productId: string, productSku?: string): ModelCodeReference | undefined => {
    // First try exact product_id match (most reliable)
    const byProductId = modelCodes.find(mc => mc.product_id === productId);
    if (byProductId) return byProductId;
    // Fall back to SKU match
    return modelCodes.find(mc => mc.product_sku === productSku);
  };

  // Helper to get supplier code for a vendor
  const getSupplierCodeForVendor = (vendorId: string): SupplierCodeType | undefined => {
    return supplierCodes.find(sc => sc.vendor_id === vendorId);
  };

  // Handle PR selection - auto-populate ALL data from PR including items with monthly quantities
  const handlePRSelect = (prId: string) => {
    const pr = openPRs.find(p => p.id === prId);
    setSelectedPR(pr || null);

    if (pr) {
      // Get preferred vendor from first item that has one
      const preferredVendorId = pr.items.find(item => item.preferred_vendor_id)?.preferred_vendor_id || '';

      // Convert PR items to PO items - inherit monthly quantities from PR
      const poItems: POItem[] = pr.items.map(item => ({
        product_id: item.product_id,
        product_name: item.product_name,
        sku: item.sku,
        quantity: item.quantity_requested,
        unit_price: item.estimated_unit_price || 0,
        gst_rate: 18, // Default GST rate
        uom: item.uom || 'Nos',
        monthly_quantities: item.monthly_quantities, // Inherit from PR
      }));

      // Check if multi-delivery and collect delivery months
      const allMonths = new Set<string>();
      pr.items.forEach(item => {
        if (item.monthly_quantities) {
          Object.keys(item.monthly_quantities).forEach(m => allMonths.add(m));
        }
      });
      const hasMonthlyBreakdown = allMonths.size > 0;

      setIsMultiDelivery(hasMonthlyBreakdown);
      setDeliveryMonths(Array.from(allMonths).sort());

      setFormData({
        ...formData,
        requisition_id: prId,
        vendor_id: preferredVendorId,
        expected_delivery_date: pr.required_by_date || '',
        terms_and_conditions: pr.reason || '',
        items: poItems, // Auto-populate items from PR
      });
    } else {
      // Clear form if no PR selected
      setFormData({
        ...formData,
        requisition_id: '',
        vendor_id: '',
        expected_delivery_date: '',
        terms_and_conditions: '',
        items: [],
      });
      setIsMultiDelivery(false);
      setDeliveryMonths([]);
    }
  };

  const columns: ColumnDef<PurchaseOrder>[] = [
    {
      accessorKey: 'po_number',
      header: 'PO Number',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium font-mono">{row.original.po_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'vendor',
      header: 'Vendor',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.vendor?.name || 'N/A'}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.original.vendor?.code}</div>
        </div>
      ),
    },
    {
      accessorKey: 'warehouse',
      header: 'Warehouse',
      cell: ({ row }) => (
        <span className="text-sm">{row.original.warehouse?.name || 'N/A'}</span>
      ),
    },
    {
      accessorKey: 'grand_total',
      header: 'Amount',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{formatCurrency(row.original.grand_total)}</div>
          <div className="text-xs text-muted-foreground">
            GST: {formatCurrency(row.original.gst_amount)}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'expected_delivery_date',
      header: 'Expected Delivery',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {row.original.expected_delivery_date
            ? formatDate(row.original.expected_delivery_date)
            : '-'}
        </span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => handleViewDetails(row.original)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            {/* Edit PO - Only for DRAFT and PENDING_APPROVAL */}
            {(row.original.status === 'DRAFT' || row.original.status === 'PENDING_APPROVAL') && (
              <DropdownMenuItem onClick={() => handleEditPO(row.original)}>
                <Pencil className="mr-2 h-4 w-4" />
                Edit PO
              </DropdownMenuItem>
            )}
            {/* Edit Status - Super Admin only */}
            {isSuperAdmin && (
              <DropdownMenuItem onClick={() => handleEditStatus(row.original)}>
                <Shield className="mr-2 h-4 w-4" />
                Edit Status
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={() => handleDownload(row.original)}>
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handlePrint(row.original)}>
              <Printer className="mr-2 h-4 w-4" />
              Print PO
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleDownloadBarcodesCSV(row.original)}>
              <FileSpreadsheet className="mr-2 h-4 w-4" />
              Download Barcodes CSV
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {row.original.status === 'DRAFT' && (
              <DropdownMenuItem onClick={() => { setSelectedPO(row.original); setIsSubmitOpen(true); }}>
                <Send className="mr-2 h-4 w-4" />
                Submit for Approval
              </DropdownMenuItem>
            )}
            {row.original.status === 'PENDING_APPROVAL' && (
              <DropdownMenuItem onClick={() => approveMutation.mutate(row.original.id)}>
                <CheckCircle className="mr-2 h-4 w-4" />
                Approve
              </DropdownMenuItem>
            )}
            {row.original.status === 'APPROVED' && (
              <DropdownMenuItem>
                <Send className="mr-2 h-4 w-4" />
                Send to Vendor
              </DropdownMenuItem>
            )}
            {['SENT_TO_VENDOR', 'CONFIRMED', 'PARTIALLY_RECEIVED'].includes(row.original.status) && (
              <DropdownMenuItem onClick={() => router.push(`/procurement/grn?create=true&po_id=${row.original.id}`)}>
                <Package className="mr-2 h-4 w-4" />
                Create GRN
              </DropdownMenuItem>
            )}
            {isSuperAdmin && row.original.status === 'DRAFT' && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => { setSelectedPO(row.original); setIsDeleteOpen(true); }}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete PO
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Purchase Orders"
        description="Manage purchase orders and vendor procurement"
        actions={
          <div className="flex items-center gap-2">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="DRAFT">Draft</SelectItem>
                <SelectItem value="PENDING_APPROVAL">Pending Approval</SelectItem>
                <SelectItem value="APPROVED">Approved</SelectItem>
                <SelectItem value="SENT_TO_VENDOR">Sent to Vendor</SelectItem>
                <SelectItem value="CONFIRMED">Confirmed</SelectItem>
                <SelectItem value="PARTIALLY_RECEIVED">Partially Received</SelectItem>
                <SelectItem value="RECEIVED">Received</SelectItem>
                <SelectItem value="CLOSED">Closed</SelectItem>
              </SelectContent>
            </Select>
            <Dialog open={isCreateOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsCreateOpen(true); }}>
              <DialogTrigger asChild>
                <Button onClick={() => setIsCreateOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Create PO
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>Create Purchase Order</DialogTitle>
                  <DialogDescription>Create a new purchase order for vendor procurement</DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  {/* PO Number - Auto-generated, Read-only */}
                  <div className="space-y-2">
                    <Label htmlFor="po_number">PO Number (Auto-generated)</Label>
                    <div className="relative">
                      <Input
                        id="po_number"
                        placeholder={isLoadingPONumber ? "Loading..." : "PO/APL/YY-YY/0001"}
                        value={nextPONumber}
                        readOnly
                        disabled
                        className="bg-muted pr-8 font-mono"
                      />
                      <Lock className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>

                  {/* Purchase Requisition Selection - MANDATORY */}
                  <div className="space-y-2 p-3 border rounded-lg bg-blue-50/50">
                    <Label className="text-base font-semibold flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Purchase Requisition *
                      <span className="text-xs font-normal text-muted-foreground">(Required)</span>
                    </Label>
                    <Select
                      value={formData.requisition_id || 'select'}
                      onValueChange={(value) => handlePRSelect(value === 'select' ? '' : value)}
                    >
                      <SelectTrigger className={!formData.requisition_id ? 'border-amber-400' : ''}>
                        <SelectValue placeholder="Select an approved Purchase Requisition" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="select" disabled>Select an approved PR</SelectItem>
                        {openPRs.length === 0 ? (
                          <SelectItem value="none" disabled>No open PRs available</SelectItem>
                        ) : (
                          openPRs.map((pr) => (
                            <SelectItem key={pr.id} value={pr.id}>
                              {pr.requisition_number} - {pr.reason || 'No description'} ({formatCurrency(pr.estimated_total || 0)})
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                    {selectedPR && (
                      <div className="text-xs text-muted-foreground mt-1 space-y-1">
                        <p><strong>Department:</strong> {selectedPR.requesting_department || 'N/A'}</p>
                        <p><strong>Items:</strong> {selectedPR.items.length} | <strong>Total:</strong> {formatCurrency(selectedPR.estimated_total || 0)}</p>
                        {selectedPR.required_by_date && <p><strong>Required By:</strong> {formatDate(selectedPR.required_by_date)}</p>}
                      </div>
                    )}
                    {!formData.requisition_id && openPRs.length === 0 && (
                      <p className="text-xs text-amber-600">
                        No approved Purchase Requisitions available. Create and approve a PR first.
                      </p>
                    )}
                  </div>

                  <Separator />

                  <div className="space-y-2">
                    <Label>Vendor *</Label>
                    <Select
                      value={formData.vendor_id || 'select'}
                      onValueChange={(value) => setFormData({ ...formData, vendor_id: value === 'select' ? '' : value })}
                      disabled={!formData.requisition_id}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select vendor" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="select" disabled>Select vendor</SelectItem>
                        {vendors.filter((v: Vendor) => v.id && v.name).map((v: Vendor) => (
                          <SelectItem key={v.id} value={v.id}>{v.name} ({v.vendor_code || v.code || 'N/A'})</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {/* Bill To & Ship To Section */}
                  <div className="space-y-4 p-4 border rounded-lg bg-blue-50/30">
                    <Label className="text-base font-semibold">Billing & Shipping Addresses</Label>

                    <div className="grid grid-cols-2 gap-4">
                      {/* Bill To - Warehouse Selection */}
                      <div className="space-y-2">
                        <Label>Bill To (Invoice Address) *</Label>
                        <Select
                          value={formData.bill_to?.warehouse_id || 'select'}
                          onValueChange={(value) => {
                            if (value === 'select') {
                              setFormData({ ...formData, bill_to: null });
                              return;
                            }
                            const selectedWarehouse = warehouses.find((w: Warehouse) => w.id === value);
                            if (selectedWarehouse) {
                              setFormData({
                                ...formData,
                                bill_to: {
                                  warehouse_id: selectedWarehouse.id,
                                  name: selectedWarehouse.name,
                                  address_line1: (selectedWarehouse as any).address_line1 || '',
                                  address_line2: (selectedWarehouse as any).address_line2 || '',
                                  city: (selectedWarehouse as any).city || '',
                                  state: (selectedWarehouse as any).state || '',
                                  pincode: (selectedWarehouse as any).pincode || '',
                                  gstin: companyData?.gstin || '',
                                  state_code: companyData?.state_code || '',
                                }
                              });
                            }
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select warehouse" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="select" disabled>Select warehouse</SelectItem>
                            {warehouses.filter((w: Warehouse) => w.id && w.name).map((w: Warehouse) => (
                              <SelectItem key={w.id} value={w.id}>
                                {w.name} {(w as any).city ? `- ${(w as any).city}` : ''}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {formData.bill_to && (
                          <div className="text-xs text-muted-foreground p-2 bg-white rounded border">
                            <strong>{formData.bill_to.name}</strong><br />
                            {formData.bill_to.address_line1}<br />
                            {formData.bill_to.city}, {formData.bill_to.state} - {formData.bill_to.pincode}<br />
                            {formData.bill_to.gstin && <>GSTIN: {formData.bill_to.gstin}</>}
                          </div>
                        )}
                      </div>

                      {/* Ship To - Warehouse or Other */}
                      <div className="space-y-2">
                        <Label>Ship To (Delivery Address) *</Label>
                        <Select
                          value={shipToType || 'select'}
                          onValueChange={(value) => {
                            if (value === 'select') {
                              setShipToType('');
                              setFormData({ ...formData, ship_to: null });
                              return;
                            }
                            setShipToType(value as 'warehouse' | 'other');
                            if (value === 'other') {
                              // Clear ship_to, will be filled from manual form
                              setFormData({ ...formData, ship_to: null });
                            }
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select address type" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="select" disabled>Select address type</SelectItem>
                            <SelectItem value="warehouse">Warehouse Address</SelectItem>
                            <SelectItem value="other">Other (Manual Entry)</SelectItem>
                          </SelectContent>
                        </Select>

                        {/* Warehouse Selection */}
                        {shipToType === 'warehouse' && (
                          <Select
                            value={formData.ship_to?.warehouse_id || 'select'}
                            onValueChange={(value) => {
                              if (value === 'select') {
                                setFormData({ ...formData, ship_to: null });
                                return;
                              }
                              const selectedWarehouse = warehouses.find((w: Warehouse) => w.id === value);
                              if (selectedWarehouse) {
                                setFormData({
                                  ...formData,
                                  ship_to: {
                                    type: 'warehouse',
                                    warehouse_id: selectedWarehouse.id,
                                    name: selectedWarehouse.name,
                                    address_line1: (selectedWarehouse as any).address_line1 || '',
                                    address_line2: (selectedWarehouse as any).address_line2 || '',
                                    city: (selectedWarehouse as any).city || '',
                                    state: (selectedWarehouse as any).state || '',
                                    pincode: (selectedWarehouse as any).pincode || '',
                                  }
                                });
                              }
                            }}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select warehouse" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="select" disabled>Select warehouse</SelectItem>
                              {warehouses.filter((w: Warehouse) => w.id && w.name).map((w: Warehouse) => (
                                <SelectItem key={w.id} value={w.id}>
                                  {w.name} {(w as any).city ? `- ${(w as any).city}` : ''}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}

                        {/* Manual Address Entry */}
                        {shipToType === 'other' && (
                          <div className="space-y-2 p-2 border rounded bg-white">
                            <Input
                              placeholder="Name / Company"
                              value={manualShipTo.name}
                              onChange={(e) => {
                                const updated = { ...manualShipTo, name: e.target.value };
                                setManualShipTo(updated);
                                setFormData({
                                  ...formData,
                                  ship_to: { type: 'other', ...updated }
                                });
                              }}
                            />
                            <Input
                              placeholder="Address Line 1"
                              value={manualShipTo.address_line1}
                              onChange={(e) => {
                                const updated = { ...manualShipTo, address_line1: e.target.value };
                                setManualShipTo(updated);
                                setFormData({
                                  ...formData,
                                  ship_to: { type: 'other', ...updated }
                                });
                              }}
                            />
                            <Input
                              placeholder="Address Line 2 (Optional)"
                              value={manualShipTo.address_line2}
                              onChange={(e) => {
                                const updated = { ...manualShipTo, address_line2: e.target.value };
                                setManualShipTo(updated);
                                setFormData({
                                  ...formData,
                                  ship_to: { type: 'other', ...updated }
                                });
                              }}
                            />
                            <div className="grid grid-cols-3 gap-2">
                              <Input
                                placeholder="City"
                                value={manualShipTo.city}
                                onChange={(e) => {
                                  const updated = { ...manualShipTo, city: e.target.value };
                                  setManualShipTo(updated);
                                  setFormData({
                                    ...formData,
                                    ship_to: { type: 'other', ...updated }
                                  });
                                }}
                              />
                              <Input
                                placeholder="State"
                                value={manualShipTo.state}
                                onChange={(e) => {
                                  const updated = { ...manualShipTo, state: e.target.value };
                                  setManualShipTo(updated);
                                  setFormData({
                                    ...formData,
                                    ship_to: { type: 'other', ...updated }
                                  });
                                }}
                              />
                              <Input
                                placeholder="Pincode"
                                value={manualShipTo.pincode}
                                onChange={(e) => {
                                  const updated = { ...manualShipTo, pincode: e.target.value };
                                  setManualShipTo(updated);
                                  setFormData({
                                    ...formData,
                                    ship_to: { type: 'other', ...updated }
                                  });
                                }}
                              />
                            </div>
                          </div>
                        )}

                        {formData.ship_to && shipToType === 'warehouse' && (
                          <div className="text-xs text-muted-foreground p-2 bg-white rounded border">
                            <strong>{formData.ship_to.name}</strong><br />
                            {formData.ship_to.address_line1}<br />
                            {formData.ship_to.city}, {formData.ship_to.state} - {formData.ship_to.pincode}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Expected Delivery Date</Label>
                      <Input
                        type="date"
                        value={formData.expected_delivery_date}
                        onChange={(e) => setFormData({ ...formData, expected_delivery_date: e.target.value })}
                        disabled={isMultiDelivery || !formData.requisition_id}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Credit Days</Label>
                      <Input
                        type="number"
                        min="0"
                        value={formData.credit_days}
                        onChange={(e) => setFormData({ ...formData, credit_days: parseInt(e.target.value) || 0 })}
                      />
                    </div>
                  </div>

                  {/* Advance Payment Section */}
                  <div className="space-y-2 p-3 border rounded-lg bg-green-50/50">
                    <Label className="text-base font-semibold">Advance Payment</Label>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="advance_required">Advance Required (₹)</Label>
                        <Input
                          id="advance_required"
                          type="number"
                          min="0"
                          step="0.01"
                          placeholder="Enter advance payment amount"
                          value={formData.advance_required || ''}
                          onChange={(e) => setFormData({ ...formData, advance_required: parseFloat(e.target.value) || 0 })}
                        />
                        <p className="text-xs text-muted-foreground">
                          Amount to be paid in advance before delivery
                        </p>
                        {/* Quick percentage buttons */}
                        <div className="flex gap-1 mt-1">
                          {[10, 25, 50].map((pct) => (
                            <Button
                              key={pct}
                              type="button"
                              variant="outline"
                              size="sm"
                              className="text-xs h-6 px-2"
                              onClick={() => setFormData({ ...formData, advance_required: Math.round((totals.total * pct / 100) * 100) / 100 })}
                            >
                              {pct}%
                            </Button>
                          ))}
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="advance_paid">Advance Already Paid (₹)</Label>
                        <Input
                          id="advance_paid"
                          type="number"
                          min="0"
                          step="0.01"
                          placeholder="Enter amount already paid"
                          value={formData.advance_paid || ''}
                          onChange={(e) => setFormData({ ...formData, advance_paid: parseFloat(e.target.value) || 0 })}
                          className={formData.advance_paid > 0 ? "border-green-500 bg-green-50" : ""}
                        />
                        <p className="text-xs text-muted-foreground">
                          Amount already paid to vendor
                        </p>
                        {formData.advance_required > 0 && (
                          <div className="text-xs">
                            <span className="text-muted-foreground">Balance: </span>
                            <span className={formData.advance_paid >= formData.advance_required ? "text-green-600 font-medium" : "text-orange-600 font-medium"}>
                              {formatCurrency(Math.max(0, formData.advance_required - formData.advance_paid))}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Items from PR - Auto-populated */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <Label className="text-base font-semibold">Items from Purchase Requisition</Label>
                      {selectedPR && formData.items.length > 0 && (
                        <Badge variant="secondary">{formData.items.length} item(s)</Badge>
                      )}
                    </div>

                    {!selectedPR ? (
                      <p className="text-sm text-muted-foreground italic p-4 border rounded-lg bg-muted/20">
                        Please select a Purchase Requisition first - items will be auto-populated
                      </p>
                    ) : formData.items.length === 0 ? (
                      <p className="text-sm text-amber-600 p-4 border rounded-lg bg-amber-50">
                        Selected PR has no items. Please select a different PR.
                      </p>
                    ) : (
                      <div className="p-3 border rounded-lg bg-green-50/30 space-y-2">
                        <p className="text-xs text-muted-foreground">
                          Items inherited from PR. You can redistribute month-wise quantities (total cannot exceed PR qty) and adjust prices.
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Month Selection for PO (can differ from PR) */}
                  {selectedPR && formData.items.length > 0 && isMultiDelivery && (
                    <div className="space-y-2 border rounded-lg p-3 bg-blue-50/50">
                      <Label className="text-sm font-medium">PO Delivery Months</Label>
                      <p className="text-xs text-muted-foreground mb-2">
                        You can redistribute quantities across different months. Select the months for this PO.
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {availableMonths.map((month) => (
                          <Button
                            key={month.code}
                            type="button"
                            size="sm"
                            variant={deliveryMonths.includes(month.code) ? 'default' : 'outline'}
                            onClick={() => {
                              if (deliveryMonths.includes(month.code)) {
                                setDeliveryMonths(deliveryMonths.filter(m => m !== month.code));
                              } else {
                                setDeliveryMonths([...deliveryMonths, month.code].sort());
                              }
                            }}
                          >
                            {month.name}
                          </Button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Items List - Editable Prices and Monthly Quantities */}
                  {formData.items.length > 0 && (
                    <div className="space-y-2">
                      <Label className="text-base font-semibold">Order Items</Label>
                      <div className="border rounded-md overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-muted">
                            <tr>
                              <th className="px-3 py-2 text-left">Product</th>
                              <th className="px-3 py-2 text-center text-xs">PR Max</th>
                              {isMultiDelivery && deliveryMonths.map(month => (
                                <th key={month} className="px-2 py-2 text-center text-xs">
                                  {availableMonths.find(m => m.code === month)?.name || month}
                                </th>
                              ))}
                              <th className="px-3 py-2 text-right">PO Qty</th>
                              <th className="px-3 py-2 text-right">Unit Price</th>
                              <th className="px-3 py-2 text-right">GST %</th>
                              <th className="px-3 py-2 text-right">Total</th>
                            </tr>
                          </thead>
                          <tbody>
                            {formData.items.map((item, index) => {
                              // Get PR item to know max quantity
                              const prItem = selectedPR?.items.find(pi => pi.product_id === item.product_id);
                              const prMaxQty = prItem?.quantity_requested || 0;
                              const currentTotal = item.quantity ?? 0;
                              const isOverLimit = currentTotal > prMaxQty;

                              return (
                                <tr key={index} className={`border-t ${isOverLimit ? 'bg-red-50' : ''}`}>
                                  <td className="px-3 py-2">
                                    <div className="font-medium">{item.product_name}</div>
                                    <div className="text-xs text-muted-foreground">{item.sku}</div>
                                  </td>
                                  <td className="px-3 py-2 text-center">
                                    <Badge variant="outline" className="text-xs">
                                      {prMaxQty}
                                    </Badge>
                                  </td>
                                  {isMultiDelivery && deliveryMonths.map(month => (
                                    <td key={month} className="px-2 py-2">
                                      <Input
                                        type="number"
                                        min="0"
                                        className="w-16 h-8 text-center"
                                        value={item.monthly_quantities?.[month] || ''}
                                        onChange={(e) => {
                                          const qty = parseInt(e.target.value) || 0;
                                          const newItems = [...formData.items];
                                          const newMonthlyQtys = { ...newItems[index].monthly_quantities, [month]: qty };
                                          // Remove zero values
                                          Object.keys(newMonthlyQtys).forEach(k => {
                                            if (!newMonthlyQtys[k]) delete newMonthlyQtys[k];
                                          });
                                          // Calculate new total
                                          const newTotal = Object.values(newMonthlyQtys).reduce((sum, q) => sum + (q || 0), 0);
                                          newItems[index] = {
                                            ...newItems[index],
                                            monthly_quantities: newMonthlyQtys,
                                            quantity: newTotal,
                                          };
                                          setFormData({ ...formData, items: newItems });
                                        }}
                                      />
                                    </td>
                                  ))}
                                  <td className="px-3 py-2 text-right">
                                    {isMultiDelivery ? (
                                      <span className={`font-medium ${isOverLimit ? 'text-red-600' : ''}`}>
                                        {currentTotal}
                                        {isOverLimit && <span className="text-xs ml-1">!</span>}
                                      </span>
                                    ) : (
                                      <Input
                                        type="number"
                                        min="1"
                                        max={prMaxQty}
                                        className={`w-20 h-8 text-right ${isOverLimit ? 'border-red-500' : ''}`}
                                        value={item.quantity || ''}
                                        onChange={(e) => {
                                          const qty = parseInt(e.target.value) || 0;
                                          const newItems = [...formData.items];
                                          newItems[index] = { ...newItems[index], quantity: qty };
                                          setFormData({ ...formData, items: newItems });
                                        }}
                                      />
                                    )}
                                  </td>
                                  <td className="px-3 py-2">
                                    <Input
                                      type="number"
                                      min="0"
                                      step="0.01"
                                      className="w-24 h-8 text-right ml-auto"
                                      value={item.unit_price || ''}
                                      onChange={(e) => {
                                        const newItems = [...formData.items];
                                        newItems[index] = { ...newItems[index], unit_price: parseFloat(e.target.value) || 0 };
                                        setFormData({ ...formData, items: newItems });
                                      }}
                                    />
                                  </td>
                                  <td className="px-3 py-2">
                                    <Input
                                      type="number"
                                      min="0"
                                      max="28"
                                      className="w-16 h-8 text-right ml-auto"
                                      value={item.gst_rate ?? 18}
                                      onChange={(e) => {
                                        const newItems = [...formData.items];
                                        newItems[index] = { ...newItems[index], gst_rate: parseFloat(e.target.value) || 0 };
                                        setFormData({ ...formData, items: newItems });
                                      }}
                                    />
                                  </td>
                                  <td className="px-3 py-2 text-right font-medium">
                                    {formatCurrency((item.quantity ?? 0) * item.unit_price * (1 + (item.gst_rate ?? 0) / 100))}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                          <tfoot className="bg-muted/50">
                            <tr className="border-t">
                              <td colSpan={isMultiDelivery ? deliveryMonths.length + 5 : 5} className="px-3 py-2 text-right">Subtotal:</td>
                              <td className="px-3 py-2 text-right font-medium">{formatCurrency(totals.subtotal)}</td>
                            </tr>
                            <tr>
                              <td colSpan={isMultiDelivery ? deliveryMonths.length + 5 : 5} className="px-3 py-2 text-right">GST:</td>
                              <td className="px-3 py-2 text-right font-medium">{formatCurrency(totals.gst)}</td>
                            </tr>
                            <tr className="border-t">
                              <td colSpan={isMultiDelivery ? deliveryMonths.length + 5 : 5} className="px-3 py-2 text-right font-semibold">Grand Total:</td>
                              <td className="px-3 py-2 text-right font-bold text-lg">{formatCurrency(totals.total)}</td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                      {/* Validation Warning */}
                      {formData.items.some((item, idx) => {
                        const prItem = selectedPR?.items.find(pi => pi.product_id === item.product_id);
                        return (item.quantity ?? 0) > (prItem?.quantity_requested || 0);
                      }) && (
                        <p className="text-sm text-red-600 p-2 bg-red-50 rounded">
                          Warning: Some items exceed PR quantity. PO quantity cannot be more than PR quantity.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Barcode Range Preview Section */}
                  {formData.items.length > 0 && formData.vendor_id && (
                    <div className="space-y-2 p-4 border rounded-lg bg-purple-50/50">
                      <Label className="text-base font-semibold flex items-center gap-2">
                        <Barcode className="h-4 w-4" />
                        Barcode Range Preview
                      </Label>
                      <p className="text-xs text-muted-foreground mb-2">
                        <strong>System Generated:</strong> Barcodes will be auto-assigned when PO is created and sent to vendor for printing
                      </p>
                      {(() => {
                        // Get supplier code for vendor
                        const selectedVendor = vendors.find((v: Vendor) => v.id === formData.vendor_id);
                        const supplierCode = selectedVendor ? getSupplierCodeForVendor(selectedVendor.id) : undefined;

                        // Year and month codes for barcode
                        const getYearCode = (year: number) => {
                          const codes = 'ZABCDEFGHIJ'; // Z=2025, A=2026, B=2027, etc.
                          return codes[(year - 2025) % 11] || 'Z';
                        };
                        const getMonthCode = (month: number) => {
                          const codes = 'ABCDEFGHIJKL'; // A=Jan, B=Feb, etc.
                          return codes[(month - 1) % 12] || 'A';
                        };

                        if (!supplierCode) {
                          return (
                            <div className="p-3 bg-amber-50 border border-amber-200 rounded-md">
                              <p className="text-sm text-amber-700">
                                <strong>Note:</strong> Supplier code not mapped for {selectedVendor?.name || 'selected vendor'}.
                                Please setup in <strong>Serialization → Supplier Codes</strong> to generate barcodes.
                              </p>
                            </div>
                          );
                        }

                        return (
                          <div className="border rounded-md bg-background">
                            <table className="w-full text-sm">
                              <thead className="bg-muted">
                                <tr>
                                  <th className="px-3 py-2 text-left">Product</th>
                                  <th className="px-3 py-2 text-center">Model Code</th>
                                  <th className="px-3 py-2 text-right">Qty</th>
                                  <th className="px-3 py-2 text-left">Barcode Range (Preview)</th>
                                </tr>
                              </thead>
                              <tbody>
                                {formData.items.map((item, idx) => {
                                  const modelCode = getModelCodeForProduct(item.product_id, item.sku);
                                  const qty = item.quantity || 0;

                                  // Generate preview barcode format
                                  // Format: AP{supplier}{year}{month}{model}{serial}
                                  const now = new Date();
                                  const yearCode = getYearCode(now.getFullYear());
                                  const monthCode = getMonthCode(now.getMonth() + 1);

                                  if (!modelCode) {
                                    return (
                                      <tr key={idx} className="border-t">
                                        <td className="px-3 py-2">
                                          <div className="font-medium text-xs">{item.product_name}</div>
                                          <div className="text-xs text-muted-foreground">{item.sku}</div>
                                        </td>
                                        <td className="px-3 py-2 text-center">
                                          <span className="text-xs text-amber-600">Not mapped</span>
                                        </td>
                                        <td className="px-3 py-2 text-right">{qty}</td>
                                        <td className="px-3 py-2">
                                          <span className="text-xs text-amber-600">Setup model code first</span>
                                        </td>
                                      </tr>
                                    );
                                  }

                                  const barcodePrefix = `AP${supplierCode.code}${yearCode}${monthCode}${modelCode.model_code}`;

                                  return (
                                    <tr key={idx} className="border-t">
                                      <td className="px-3 py-2">
                                        <div className="font-medium text-xs">{item.product_name}</div>
                                        <div className="text-xs text-muted-foreground">{item.sku}</div>
                                      </td>
                                      <td className="px-3 py-2 text-center">
                                        <Badge variant="secondary" className="font-mono text-xs">
                                          {modelCode.model_code}
                                        </Badge>
                                      </td>
                                      <td className="px-3 py-2 text-right font-medium">{qty}</td>
                                      <td className="px-3 py-2">
                                        <div className="font-mono text-xs space-y-1">
                                          <div className="text-green-700">
                                            {barcodePrefix}<span className="text-muted-foreground">000001</span>
                                          </div>
                                          <div className="text-muted-foreground">to</div>
                                          <div className="text-green-700">
                                            {barcodePrefix}<span className="text-muted-foreground">{String(qty).padStart(6, '0')}</span>
                                          </div>
                                        </div>
                                      </td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                              <tfoot className="bg-muted/50">
                                <tr className="border-t font-medium">
                                  <td className="px-3 py-2">Total Units</td>
                                  <td className="px-3 py-2"></td>
                                  <td className="px-3 py-2 text-right">
                                    {formData.items.reduce((sum, item) => sum + (item.quantity || 0), 0)}
                                  </td>
                                  <td className="px-3 py-2 text-xs text-muted-foreground">
                                    Barcodes will be allocated from last used serial
                                  </td>
                                </tr>
                              </tfoot>
                            </table>
                          </div>
                        );
                      })()}
                      <p className="text-xs text-muted-foreground italic">
                        Barcode Format: AP + Supplier({(() => {
                          const sc = getSupplierCodeForVendor(formData.vendor_id);
                          return sc?.code || 'XX';
                        })()}) + Year + Month + Model + Serial(6 digits)
                      </p>
                    </div>
                  )}

                  {/* Terms & Conditions Section */}
                  <div className="space-y-2 p-4 border rounded-lg bg-amber-50/30">
                    <Label className="text-base font-semibold">Terms & Conditions</Label>
                    <p className="text-xs text-muted-foreground mb-2">
                      Enter the terms and conditions for this Purchase Order. These will appear on the printed PO.
                    </p>
                    <Textarea
                      placeholder="Enter terms and conditions for this PO...&#10;&#10;Example:&#10;1. Delivery must be as per schedule mentioned above.&#10;2. All goods must be in original packing with serial numbers as specified.&#10;3. Payment will be released as per lot-wise schedule.&#10;4. Quality check will be done before acceptance."
                      value={formData.terms_and_conditions}
                      onChange={(e) => setFormData({ ...formData, terms_and_conditions: e.target.value })}
                      rows={6}
                      className="font-mono text-sm"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={resetForm}>Cancel</Button>
                  <Button onClick={handleCreatePO} disabled={createMutation.isPending}>
                    {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Create Purchase Order
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="po_number"
        searchPlaceholder="Search PO number..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      {/* Submit Confirmation Dialog */}
      <AlertDialog open={isSubmitOpen} onOpenChange={setIsSubmitOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Submit for Approval</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to submit PO {selectedPO?.po_number} for approval?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => selectedPO && submitMutation.mutate(selectedPO.id)}
              disabled={submitMutation.isPending}
            >
              {submitMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Submit
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* View Details Sheet */}
      <Sheet open={isViewOpen} onOpenChange={setIsViewOpen}>
        <SheetContent className="w-[600px] sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Purchase Order Details</SheetTitle>
            <SheetDescription>{selectedPO?.po_number}</SheetDescription>
          </SheetHeader>
          {selectedPO && (
            <div className="mt-6 space-y-6">
              <div className="flex items-center justify-between">
                <StatusBadge status={selectedPO.status} />
                <span className="text-sm text-muted-foreground">
                  {formatDate(selectedPO.created_at)}
                </span>
              </div>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Vendor</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="font-medium">{selectedPO.vendor?.name}</div>
                  <div className="text-sm text-muted-foreground font-mono">{selectedPO.vendor?.code}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Delivery Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Warehouse:</span>
                    <span>{selectedPO.warehouse?.name || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Expected Date:</span>
                    <span>{selectedPO.expected_delivery_date ? formatDate(selectedPO.expected_delivery_date) : '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Credit Days:</span>
                    <span>{selectedPO.credit_days} days</span>
                  </div>
                </CardContent>
              </Card>

              {selectedPO.items && selectedPO.items.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Package className="h-4 w-4" />
                      Items ({selectedPO.items.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {selectedPO.items.map((item, index) => (
                        <div key={index} className="flex justify-between items-center py-2 border-b last:border-0">
                          <div>
                            <div className="font-medium">{item.product_name || 'Product'}</div>
                            <div className="text-xs text-muted-foreground">
                              {item.quantity ?? item.quantity_ordered ?? 0} x {formatCurrency(item.unit_price)}
                            </div>
                          </div>
                          <div className="text-right font-medium">
                            {formatCurrency((item.quantity ?? item.quantity_ordered ?? 0) * item.unit_price)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Delivery Schedule & Lot-wise Payment Plan */}
              {(selectedPO as any).delivery_schedules && (selectedPO as any).delivery_schedules.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Delivery Schedule & Lot-wise Payment Plan
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="border rounded-md overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-muted">
                          <tr>
                            <th className="px-3 py-2 text-left">Lot</th>
                            <th className="px-3 py-2 text-right">Qty</th>
                            <th className="px-3 py-2 text-center">Serial Range</th>
                            <th className="px-3 py-2 text-right">Value</th>
                            <th className="px-3 py-2 text-right">Advance</th>
                            <th className="px-3 py-2 text-right">Balance</th>
                            <th className="px-3 py-2 text-center">Delivery</th>
                            <th className="px-3 py-2 text-center">Status</th>
                            <th className="px-3 py-2 text-center">Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(selectedPO as any).delivery_schedules.map((schedule: any) => {
                            const advancePaid = parseFloat(schedule.advance_paid || 0);
                            const advanceAmount = parseFloat(schedule.advance_amount || 0);
                            const balancePaid = parseFloat(schedule.balance_paid || 0);
                            const balanceAmount = parseFloat(schedule.balance_amount || 0);
                            const isAdvancePending = advancePaid < advanceAmount && ['pending', 'advance_pending'].includes(schedule.status);
                            const isBalancePending = balancePaid < balanceAmount && ['delivered', 'payment_pending'].includes(schedule.status);

                            return (
                              <tr key={schedule.id} className="border-t">
                                <td className="px-3 py-2 font-medium">{schedule.lot_name}</td>
                                <td className="px-3 py-2 text-right">{schedule.total_quantity}</td>
                                <td className="px-3 py-2 text-center font-mono">
                                  {schedule.serial_number_start && schedule.serial_number_end ? (
                                    <Badge variant="outline" className="font-mono text-xs">
                                      {schedule.serial_number_start} - {schedule.serial_number_end}
                                    </Badge>
                                  ) : (
                                    <span className="text-muted-foreground text-xs">-</span>
                                  )}
                                </td>
                                <td className="px-3 py-2 text-right">{formatCurrency(schedule.lot_total)}</td>
                                <td className="px-3 py-2 text-right">
                                  <div className="space-y-0.5">
                                    <div className="text-xs">{formatCurrency(advanceAmount)}</div>
                                    {advancePaid > 0 && (
                                      <div className="text-xs text-green-600">Paid: {formatCurrency(advancePaid)}</div>
                                    )}
                                  </div>
                                </td>
                                <td className="px-3 py-2 text-right">
                                  <div className="space-y-0.5">
                                    <div className="text-xs">{formatCurrency(balanceAmount)}</div>
                                    {balancePaid > 0 && (
                                      <div className="text-xs text-green-600">Paid: {formatCurrency(balancePaid)}</div>
                                    )}
                                  </div>
                                </td>
                                <td className="px-3 py-2 text-center text-xs">
                                  {formatDate(schedule.expected_delivery_date)}
                                </td>
                                <td className="px-3 py-2 text-center">
                                  <StatusBadge status={schedule.status} />
                                </td>
                                <td className="px-3 py-2 text-center">
                                  {isAdvancePending && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="h-7 text-xs bg-green-50 border-green-300 text-green-700 hover:bg-green-100"
                                      onClick={() => {
                                        setPaymentLot(schedule);
                                        setPaymentType('ADVANCE');
                                        setPaymentAmount(advanceAmount - advancePaid);
                                        setIsPaymentDialogOpen(true);
                                      }}
                                    >
                                      Pay Advance
                                    </Button>
                                  )}
                                  {isBalancePending && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="h-7 text-xs bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100"
                                      onClick={() => {
                                        setPaymentLot(schedule);
                                        setPaymentType('BALANCE');
                                        setPaymentAmount(balanceAmount - balancePaid);
                                        setIsPaymentDialogOpen(true);
                                      }}
                                    >
                                      Pay Balance
                                    </Button>
                                  )}
                                  {schedule.status === 'completed' && (
                                    <span className="text-xs text-green-600">✓ Paid</span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                        <tfoot className="bg-muted/50">
                          <tr className="border-t font-medium">
                            <td className="px-3 py-2">Total</td>
                            <td className="px-3 py-2 text-right">
                              {(selectedPO as any).delivery_schedules.reduce((sum: number, s: any) => sum + s.total_quantity, 0)}
                            </td>
                            <td className="px-3 py-2 text-center font-mono text-xs">
                              {(() => {
                                const schedules = (selectedPO as any).delivery_schedules;
                                const first = schedules[0]?.serial_number_start;
                                const last = schedules[schedules.length - 1]?.serial_number_end;
                                return first && last ? `${first} - ${last}` : '-';
                              })()}
                            </td>
                            <td className="px-3 py-2 text-right">
                              {formatCurrency((selectedPO as any).delivery_schedules.reduce((sum: number, s: any) => sum + parseFloat(s.lot_total || 0), 0))}
                            </td>
                            <td className="px-3 py-2 text-right text-xs">
                              {formatCurrency((selectedPO as any).delivery_schedules.reduce((sum: number, s: any) => sum + parseFloat(s.advance_amount || 0), 0))}
                            </td>
                            <td className="px-3 py-2 text-right text-xs">
                              {formatCurrency((selectedPO as any).delivery_schedules.reduce((sum: number, s: any) => sum + parseFloat(s.balance_amount || 0), 0))}
                            </td>
                            <td colSpan={3}></td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Serial Numbers Section */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Barcode className="h-4 w-4" />
                    Serial Numbers
                    {poSerials && poSerials.total > 0 && (
                      <Badge variant="secondary" className="ml-2">{poSerials.total}</Badge>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {loadingSerials ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                      <span className="ml-2 text-sm text-muted-foreground">Loading serials...</span>
                    </div>
                  ) : poSerials && poSerials.total > 0 ? (
                    <div className="space-y-3">
                      {/* Status Summary */}
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(poSerials.by_status).map(([status, count]) => (
                          status !== 'total' && (
                            <Badge key={status} variant={status === 'received' ? 'default' : 'secondary'}>
                              {status}: {count}
                            </Badge>
                          )
                        ))}
                      </div>

                      {/* Serial Numbers by Model */}
                      <div className="border rounded-md max-h-48 overflow-y-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-muted sticky top-0">
                            <tr>
                              <th className="px-3 py-2 text-left">Model</th>
                              <th className="px-3 py-2 text-left">Barcode Range</th>
                              <th className="px-3 py-2 text-right">Count</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(() => {
                              // Group serials by model_code
                              const byModel: Record<string, { barcodes: string[]; count: number }> = {};
                              poSerials.serials.forEach(s => {
                                if (!byModel[s.model_code]) {
                                  byModel[s.model_code] = { barcodes: [], count: 0 };
                                }
                                byModel[s.model_code].barcodes.push(s.barcode);
                                byModel[s.model_code].count++;
                              });

                              return Object.entries(byModel).map(([model, data]) => (
                                <tr key={model} className="border-t">
                                  <td className="px-3 py-2 font-mono font-medium">{model}</td>
                                  <td className="px-3 py-2">
                                    <span className="font-mono text-xs">
                                      {data.barcodes[0]}
                                      {data.barcodes.length > 1 && (
                                        <> ... {data.barcodes[data.barcodes.length - 1]}</>
                                      )}
                                    </span>
                                  </td>
                                  <td className="px-3 py-2 text-right">{data.count}</td>
                                </tr>
                              ));
                            })()}
                          </tbody>
                        </table>
                      </div>

                      {/* Export Button */}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          try {
                            const csv = await serializationApi.exportPOSerials(selectedPO.id, 'csv');
                            const blob = new Blob([csv], { type: 'text/csv' });
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `serials_${selectedPO.po_number}.csv`;
                            a.click();
                            window.URL.revokeObjectURL(url);
                            toast.success('Serial numbers exported');
                          } catch {
                            toast.error('Failed to export serials');
                          }
                        }}
                      >
                        <Download className="h-4 w-4 mr-2" />
                        Export Serials (CSV)
                      </Button>
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <p className="text-sm text-muted-foreground">
                        No serial numbers generated yet.
                      </p>
                      {selectedPO.status === 'APPROVED' && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Serials will be generated when PO is sent to vendor.
                        </p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="bg-muted/50">
                <CardContent className="pt-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Subtotal:</span>
                    <span>{formatCurrency(selectedPO.subtotal)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">GST:</span>
                    <span>{formatCurrency(selectedPO.gst_amount)}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between font-bold text-lg">
                    <span>Grand Total:</span>
                    <span>{formatCurrency(selectedPO.grand_total)}</span>
                  </div>
                </CardContent>
              </Card>

              {selectedPO.notes && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Notes</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{selectedPO.notes}</p>
                  </CardContent>
                </Card>
              )}

              {/* Action Buttons in Details View */}
              <div className="flex flex-wrap gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => handleDownload(selectedPO)}>
                  <Download className="mr-2 h-4 w-4" />
                  Download PDF
                </Button>
                <Button variant="outline" onClick={() => handlePrint(selectedPO)}>
                  <Printer className="mr-2 h-4 w-4" />
                  Print
                </Button>
                <Button variant="outline" onClick={() => handleDownloadBarcodesCSV(selectedPO)}>
                  <FileSpreadsheet className="mr-2 h-4 w-4" />
                  Download Barcodes CSV
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Purchase Order</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete PO <strong>{selectedPO?.po_number}</strong>?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => selectedPO && deleteMutation.mutate(selectedPO.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Edit PO Dialog - Comprehensive editing */}
      <Dialog open={isEditDialogOpen} onOpenChange={(open) => {
        if (!open) {
          setIsEditDialogOpen(false);
          setSelectedPO(null);
          setEditPOData({
            vendor_id: '',
            expected_delivery_date: '',
            credit_days: 30,
            payment_terms: '',
            advance_required: 0,
            advance_paid: 0,
            freight_charges: 0,
            packing_charges: 0,
            other_charges: 0,
            terms_and_conditions: '',
            special_instructions: '',
            internal_notes: '',
            items: [],
          });
          setEditNewItem({ product_id: '', quantity: 1, unit_price: 0, gst_rate: 18 });
        }
      }}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Purchase Order</DialogTitle>
            <DialogDescription>
              Update PO {selectedPO?.po_number} - Edit vendor, items, prices, and all details
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-6 py-4">
            {/* Row 1: Vendor & Dates */}
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Vendor <span className="text-red-500">*</span></Label>
                <Select
                  value={editPOData.vendor_id}
                  onValueChange={(value) => setEditPOData({ ...editPOData, vendor_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select vendor" />
                  </SelectTrigger>
                  <SelectContent>
                    {vendors.filter((v: Vendor) => v.id && v.name).map((vendor: Vendor) => (
                      <SelectItem key={vendor.id} value={vendor.id}>
                        {vendor.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Expected Delivery</Label>
                <Input
                  type="date"
                  value={editPOData.expected_delivery_date}
                  onChange={(e) => setEditPOData({ ...editPOData, expected_delivery_date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Payment Terms</Label>
                <Input
                  value={editPOData.payment_terms}
                  onChange={(e) => setEditPOData({ ...editPOData, payment_terms: e.target.value })}
                  placeholder="e.g., Net 30, 50% Advance"
                />
              </div>
            </div>

            {/* Row 2: Credit & Advance */}
            <div className="grid grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label>Credit Days</Label>
                <Input
                  type="number"
                  min="0"
                  value={editPOData.credit_days}
                  onChange={(e) => setEditPOData({ ...editPOData, credit_days: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label>Advance Required</Label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={editPOData.advance_required}
                  onChange={(e) => setEditPOData({ ...editPOData, advance_required: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label>Advance Paid</Label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={editPOData.advance_paid}
                  onChange={(e) => setEditPOData({ ...editPOData, advance_paid: parseFloat(e.target.value) || 0 })}
                  className={editPOData.advance_paid > 0 ? "border-green-500 bg-green-50" : ""}
                />
              </div>
              <div className="space-y-2">
                <Label>Advance Balance</Label>
                <div className={`h-9 px-3 py-2 border rounded-md text-sm ${editPOData.advance_paid >= editPOData.advance_required ? "bg-green-50 text-green-700" : "bg-orange-50 text-orange-700"}`}>
                  {formatCurrency(Math.max(0, editPOData.advance_required - editPOData.advance_paid))}
                </div>
              </div>
            </div>

            <Separator />

            {/* Line Items Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label className="text-base font-semibold">Line Items</Label>
                <Badge variant="secondary">{editPOData.items.length} item(s)</Badge>
              </div>

              {/* Existing Items Table */}
              {editPOData.items.length > 0 && (
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-muted">
                      <tr>
                        <th className="text-left p-2 font-medium">Product</th>
                        <th className="text-left p-2 font-medium w-20">Qty</th>
                        <th className="text-left p-2 font-medium w-28">Unit Price</th>
                        <th className="text-left p-2 font-medium w-20">GST %</th>
                        <th className="text-right p-2 font-medium w-28">Total</th>
                        <th className="w-10"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {editPOData.items.map((item, index) => {
                        const qty = item.quantity_ordered || item.quantity || 0;
                        const total = qty * (item.unit_price || 0);
                        const gstAmt = total * ((item.gst_rate || 0) / 100);
                        return (
                          <tr key={index} className="border-t">
                            <td className="p-2">
                              <div className="font-medium">{item.product_name || 'Unknown'}</div>
                              <div className="text-xs text-muted-foreground">{item.sku}</div>
                            </td>
                            <td className="p-2">
                              <Input
                                type="number"
                                min="1"
                                className="w-20 h-8"
                                value={qty}
                                onChange={(e) => handleEditUpdateItem(index, 'quantity_ordered', parseInt(e.target.value) || 1)}
                              />
                            </td>
                            <td className="p-2">
                              <Input
                                type="number"
                                min="0"
                                step="0.01"
                                className="w-28 h-8"
                                value={item.unit_price || 0}
                                onChange={(e) => handleEditUpdateItem(index, 'unit_price', parseFloat(e.target.value) || 0)}
                              />
                            </td>
                            <td className="p-2">
                              <Input
                                type="number"
                                min="0"
                                max="100"
                                className="w-20 h-8"
                                value={item.gst_rate || 0}
                                onChange={(e) => handleEditUpdateItem(index, 'gst_rate', parseFloat(e.target.value) || 0)}
                              />
                            </td>
                            <td className="p-2 text-right">
                              <div>{formatCurrency(total + gstAmt)}</div>
                              <div className="text-xs text-muted-foreground">GST: {formatCurrency(gstAmt)}</div>
                            </td>
                            <td className="p-2">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-red-500 hover:text-red-700"
                                onClick={() => handleEditRemoveItem(index)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Add New Item */}
              <div className="border rounded-lg p-4 bg-muted/50">
                <Label className="text-sm font-medium mb-3 block">Add New Item</Label>
                <div className="flex gap-3 items-end">
                  <div className="flex-1">
                    <Label className="text-xs">Product</Label>
                    <Select
                      value={editNewItem.product_id}
                      onValueChange={(value) => {
                        const product = products.find((p: Product) => p.id === value);
                        setEditNewItem({
                          ...editNewItem,
                          product_id: value,
                          unit_price: product?.mrp || 0,
                        });
                      }}
                    >
                      <SelectTrigger className="h-9">
                        <SelectValue placeholder="Select product" />
                      </SelectTrigger>
                      <SelectContent>
                        {products.map((product: Product) => (
                          <SelectItem key={product.id} value={product.id}>
                            {product.name} ({product.sku})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="w-20">
                    <Label className="text-xs">Qty</Label>
                    <Input
                      type="number"
                      min="1"
                      className="h-9"
                      value={editNewItem.quantity}
                      onChange={(e) => setEditNewItem({ ...editNewItem, quantity: parseInt(e.target.value) || 1 })}
                    />
                  </div>
                  <div className="w-28">
                    <Label className="text-xs">Unit Price</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      className="h-9"
                      value={editNewItem.unit_price}
                      onChange={(e) => setEditNewItem({ ...editNewItem, unit_price: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <div className="w-20">
                    <Label className="text-xs">GST %</Label>
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      className="h-9"
                      value={editNewItem.gst_rate}
                      onChange={(e) => setEditNewItem({ ...editNewItem, gst_rate: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <Button onClick={handleEditAddItem} size="sm" className="h-9">
                    <Plus className="h-4 w-4 mr-1" /> Add
                  </Button>
                </div>
              </div>
            </div>

            <Separator />

            {/* Charges & Totals */}
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-4">
                <Label className="text-base font-semibold">Additional Charges</Label>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">Freight</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={editPOData.freight_charges}
                      onChange={(e) => setEditPOData({ ...editPOData, freight_charges: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Packing</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={editPOData.packing_charges}
                      onChange={(e) => setEditPOData({ ...editPOData, packing_charges: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Other</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={editPOData.other_charges}
                      onChange={(e) => setEditPOData({ ...editPOData, other_charges: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-base font-semibold">Order Summary</Label>
                <Card className="bg-muted/50">
                  <CardContent className="p-4 space-y-2 text-sm">
                    {(() => {
                      const totals = calculateEditTotals();
                      return (
                        <>
                          <div className="flex justify-between">
                            <span>Subtotal:</span>
                            <span>{formatCurrency(totals.subtotal)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>GST:</span>
                            <span>{formatCurrency(totals.gst)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Charges:</span>
                            <span>{formatCurrency(totals.charges)}</span>
                          </div>
                          <Separator />
                          <div className="flex justify-between font-bold text-base">
                            <span>Grand Total:</span>
                            <span>{formatCurrency(totals.total)}</span>
                          </div>
                        </>
                      );
                    })()}
                  </CardContent>
                </Card>
              </div>
            </div>

            <Separator />

            {/* Notes Section */}
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Terms & Conditions</Label>
                <Textarea
                  value={editPOData.terms_and_conditions}
                  onChange={(e) => setEditPOData({ ...editPOData, terms_and_conditions: e.target.value })}
                  placeholder="Enter terms"
                  rows={3}
                />
              </div>
              <div className="space-y-2">
                <Label>Special Instructions</Label>
                <Textarea
                  value={editPOData.special_instructions}
                  onChange={(e) => setEditPOData({ ...editPOData, special_instructions: e.target.value })}
                  placeholder="Instructions for vendor"
                  rows={3}
                />
              </div>
              <div className="space-y-2">
                <Label>Internal Notes</Label>
                <Textarea
                  value={editPOData.internal_notes}
                  onChange={(e) => setEditPOData({ ...editPOData, internal_notes: e.target.value })}
                  placeholder="Not visible to vendor"
                  rows={3}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsEditDialogOpen(false);
                setSelectedPO(null);
                setEditPOData({
                  vendor_id: '',
                  expected_delivery_date: '',
                  credit_days: 30,
                  payment_terms: '',
                  advance_required: 0,
                  advance_paid: 0,
                  freight_charges: 0,
                  packing_charges: 0,
                  other_charges: 0,
                  terms_and_conditions: '',
                  special_instructions: '',
                  internal_notes: '',
                  items: [],
                });
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleUpdatePO}
              disabled={updateMutation.isPending || editPOData.items.length === 0}
            >
              {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Update PO
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Status Dialog (Super Admin only) */}
      <Dialog open={isEditStatusDialogOpen} onOpenChange={(open) => {
        if (!open) {
          setIsEditStatusDialogOpen(false);
          setSelectedPO(null);
          setEditStatusData({ new_status: '', reason: '' });
        }
      }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-orange-500" />
              Edit PO Status (Admin)
            </DialogTitle>
            <DialogDescription>
              Change status for {selectedPO?.po_number}. This is an admin override.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Current Status</Label>
              <Badge variant="outline">{selectedPO?.status}</Badge>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-status-new">New Status *</Label>
              <Select
                value={editStatusData.new_status}
                onValueChange={(value) => setEditStatusData({ ...editStatusData, new_status: value })}
              >
                <SelectTrigger id="edit-status-new">
                  <SelectValue placeholder="Select new status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="DRAFT">DRAFT</SelectItem>
                  <SelectItem value="PENDING_APPROVAL">PENDING_APPROVAL</SelectItem>
                  <SelectItem value="APPROVED">APPROVED</SelectItem>
                  <SelectItem value="SENT_TO_VENDOR">SENT_TO_VENDOR</SelectItem>
                  <SelectItem value="CONFIRMED">CONFIRMED</SelectItem>
                  <SelectItem value="PARTIALLY_RECEIVED">PARTIALLY_RECEIVED</SelectItem>
                  <SelectItem value="COMPLETED">COMPLETED</SelectItem>
                  <SelectItem value="CANCELLED">CANCELLED</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-status-reason">Reason for Change</Label>
              <Textarea
                id="edit-status-reason"
                value={editStatusData.reason}
                onChange={(e) => setEditStatusData({ ...editStatusData, reason: e.target.value })}
                placeholder="Enter reason for status change (for audit purposes)"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsEditStatusDialogOpen(false);
                setSelectedPO(null);
                setEditStatusData({ new_status: '', reason: '' });
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleUpdateStatus}
              disabled={adminUpdateStatusMutation.isPending || !editStatusData.new_status || editStatusData.new_status === selectedPO?.status}
            >
              {adminUpdateStatusMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Update Status
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* PO Created Success Dialog */}
      <Dialog open={isSuccessDialogOpen} onOpenChange={setIsSuccessDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" />
              Purchase Order Created
            </DialogTitle>
            <DialogDescription>
              PO <strong>{createdPO?.po_number}</strong> has been created successfully.
              What would you like to do next?
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3 py-4">
            <Button
              variant="outline"
              className="justify-start"
              onClick={() => {
                if (createdPO) handleDownload(createdPO);
              }}
            >
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </Button>
            <Button
              variant="outline"
              className="justify-start"
              onClick={() => {
                if (createdPO) handlePrint(createdPO);
              }}
            >
              <Printer className="mr-2 h-4 w-4" />
              Print PO
            </Button>
            <Button
              variant="outline"
              className="justify-start"
              onClick={() => {
                if (createdPO) handleDownloadBarcodesCSV(createdPO);
              }}
            >
              <FileSpreadsheet className="mr-2 h-4 w-4" />
              Download Barcodes CSV
              <span className="ml-auto text-xs text-muted-foreground">For manufacturer</span>
            </Button>
          </div>
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button
              variant="default"
              onClick={() => {
                setIsSuccessDialogOpen(false);
                if (createdPO) {
                  setSelectedPO(createdPO);
                  setIsViewOpen(true);
                }
              }}
            >
              <Eye className="mr-2 h-4 w-4" />
              View PO Details
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setIsSuccessDialogOpen(false);
                setCreatedPO(null);
              }}
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Multi-Lot Payment Recording Dialog */}
      <Dialog open={isPaymentDialogOpen} onOpenChange={setIsPaymentDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {paymentType === 'ADVANCE' ? (
                <span className="text-green-600">Record Advance Payment</span>
              ) : (
                <span className="text-blue-600">Record Balance Payment</span>
              )}
            </DialogTitle>
            <DialogDescription>
              {paymentLot && (
                <span>
                  Recording {paymentType.toLowerCase()} payment for <strong>{paymentLot.lot_name}</strong>
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Lot Details Summary */}
            {paymentLot && (
              <div className="bg-muted p-3 rounded-md space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Lot Value:</span>
                  <span className="font-medium">{formatCurrency(paymentLot.lot_total)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    {paymentType === 'ADVANCE' ? 'Advance Amount:' : 'Balance Amount:'}
                  </span>
                  <span className="font-medium">
                    {formatCurrency(paymentType === 'ADVANCE' ? paymentLot.advance_amount : paymentLot.balance_amount)}
                  </span>
                </div>
                {paymentType === 'ADVANCE' && parseFloat(paymentLot.advance_paid || 0) > 0 && (
                  <div className="flex justify-between text-green-600">
                    <span>Already Paid:</span>
                    <span className="font-medium">{formatCurrency(paymentLot.advance_paid)}</span>
                  </div>
                )}
                {paymentType === 'BALANCE' && parseFloat(paymentLot.balance_paid || 0) > 0 && (
                  <div className="flex justify-between text-green-600">
                    <span>Already Paid:</span>
                    <span className="font-medium">{formatCurrency(paymentLot.balance_paid)}</span>
                  </div>
                )}
              </div>
            )}

            {/* Payment Amount */}
            <div className="space-y-2">
              <Label htmlFor="payment-amount">Payment Amount (Rs.)</Label>
              <Input
                id="payment-amount"
                type="number"
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(parseFloat(e.target.value) || 0)}
                placeholder="Enter amount"
              />
            </div>

            {/* Payment Date */}
            <div className="space-y-2">
              <Label htmlFor="payment-date">Payment Date</Label>
              <Input
                id="payment-date"
                type="date"
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
              />
            </div>

            {/* Payment Reference */}
            <div className="space-y-2">
              <Label htmlFor="payment-reference">Transaction Reference (UTR/NEFT/RTGS)</Label>
              <Input
                id="payment-reference"
                value={paymentReference}
                onChange={(e) => setPaymentReference(e.target.value)}
                placeholder="e.g., UTR123456789"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsPaymentDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleRecordPayment}
              disabled={isRecordingPayment || !paymentAmount || !paymentReference}
              className={paymentType === 'ADVANCE' ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'}
            >
              {isRecordingPayment && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Record Payment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
