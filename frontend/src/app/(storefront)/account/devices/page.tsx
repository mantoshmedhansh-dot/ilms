'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Cpu,
  Plus,
  ChevronRight,
  Droplets,
  Calendar,
  Shield,
  AlertTriangle,
  CheckCircle,
  Wrench,
  Package,
  Loader2,
  QrCode,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import { useAuthStore, useIsAuthenticated } from '@/lib/storefront/auth-store';
import { formatCurrency } from '@/lib/utils';
import { deviceApi, CustomerDevice } from '@/lib/storefront/api';

// Types - using API type
type Device = CustomerDevice;

export default function DevicesPage() {
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [addingDevice, setAddingDevice] = useState(false);

  const [newDevice, setNewDevice] = useState({
    serial_number: '',
    purchase_date: '',
    invoice_number: '',
  });

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/account/login?redirect=/account/devices');
      return;
    }

    // Fetch devices from API
    const fetchDevices = async () => {
      try {
        const data = await deviceApi.getMyDevices();
        setDevices(data);
      } catch (error) {
        console.error('Failed to load devices:', error);
        setDevices([]);
      } finally {
        setLoading(false);
      }
    };

    fetchDevices();
  }, [isAuthenticated, router]);

  const handleAddDevice = async () => {
    if (!newDevice.serial_number) {
      toast.error('Please enter a serial number');
      return;
    }

    setAddingDevice(true);
    try {
      const result = await deviceApi.registerDevice({
        serial_number: newDevice.serial_number,
        purchase_date: newDevice.purchase_date || undefined,
        invoice_number: newDevice.invoice_number || undefined,
      });
      toast.success(result.message || 'Device registered successfully!');
      setShowAddDialog(false);
      setNewDevice({ serial_number: '', purchase_date: '', invoice_number: '' });

      // Refresh the devices list
      const data = await deviceApi.getMyDevices();
      setDevices(data);
    } catch (error) {
      console.error('Failed to register device:', error);
      toast.error('Failed to register device. Please check the serial number and try again.');
    } finally {
      setAddingDevice(false);
    }
  };

  const getWarrantyBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-green-100 text-green-800">Warranty Active</Badge>;
      case 'expiring_soon':
        return <Badge className="bg-yellow-100 text-yellow-800">Expiring Soon</Badge>;
      case 'expired':
        return <Badge className="bg-red-100 text-red-800">Warranty Expired</Badge>;
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
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold">My Devices</h1>
          <p className="text-muted-foreground mt-1">
            Manage your registered water purifiers
          </p>
        </div>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Device
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Register a Device</DialogTitle>
              <DialogDescription>
                Enter your product details to register for warranty and service support.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="serial">Serial Number *</Label>
                <div className="flex gap-2 mt-1.5">
                  <Input
                    id="serial"
                    placeholder="Enter serial number (e.g., APFSZAIEL00000001)"
                    value={newDevice.serial_number}
                    onChange={(e) =>
                      setNewDevice({ ...newDevice, serial_number: e.target.value.toUpperCase() })
                    }
                  />
                  <Button variant="outline" size="icon" title="Scan QR Code">
                    <QrCode className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Find the serial number on the product label or invoice
                </p>
              </div>
              <div>
                <Label htmlFor="purchase_date">Purchase Date</Label>
                <Input
                  id="purchase_date"
                  type="date"
                  value={newDevice.purchase_date}
                  onChange={(e) =>
                    setNewDevice({ ...newDevice, purchase_date: e.target.value })
                  }
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="invoice">Invoice Number (Optional)</Label>
                <Input
                  id="invoice"
                  placeholder="Enter invoice number"
                  value={newDevice.invoice_number}
                  onChange={(e) =>
                    setNewDevice({ ...newDevice, invoice_number: e.target.value })
                  }
                  className="mt-1.5"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowAddDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleAddDevice} disabled={addingDevice}>
                {addingDevice ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Registering...
                  </>
                ) : (
                  'Register Device'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Devices List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : devices.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Cpu className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Devices Registered</h3>
            <p className="text-muted-foreground mb-4">
              Register your ILMS.AI water purifier to track warranty and book services.
            </p>
            <Button onClick={() => setShowAddDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Register Your First Device
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {devices.map((device) => (
            <Card key={device.id} className="overflow-hidden">
              <CardContent className="p-0">
                <div className="flex flex-col md:flex-row">
                  {/* Product Image */}
                  <div className="w-full md:w-48 h-48 md:h-auto bg-muted flex items-center justify-center">
                    {device.product_image ? (
                      <img
                        src={device.product_image}
                        alt={device.product_name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <Droplets className="h-16 w-16 text-muted-foreground" />
                    )}
                  </div>

                  {/* Device Details */}
                  <div className="flex-1 p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="font-semibold text-lg">{device.product_name}</h3>
                        <p className="text-sm text-muted-foreground">
                          Serial: {device.serial_number}
                        </p>
                      </div>
                      {getWarrantyBadge(device.warranty_status)}
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                      <div>
                        <span className="text-muted-foreground">Purchase Date</span>
                        <p className="font-medium">
                          {new Date(device.purchase_date).toLocaleDateString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Warranty Until</span>
                        <p className="font-medium">
                          {new Date(device.warranty_end_date).toLocaleDateString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Last Service</span>
                        <p className="font-medium">
                          {device.last_service_date
                            ? new Date(device.last_service_date).toLocaleDateString('en-IN', {
                                day: 'numeric',
                                month: 'short',
                                year: 'numeric',
                              })
                            : 'Not yet serviced'}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">AMC Status</span>
                        <p className="font-medium capitalize">
                          {device.amc_status === 'none' ? 'Not Enrolled' : device.amc_status}
                        </p>
                      </div>
                    </div>

                    {/* Service Reminder */}
                    {device.next_service_due && (
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                        <div className="flex items-center gap-2 text-yellow-800">
                          <AlertTriangle className="h-4 w-4" />
                          <span className="text-sm font-medium">
                            Service due on{' '}
                            {new Date(device.next_service_due).toLocaleDateString('en-IN', {
                              day: 'numeric',
                              month: 'short',
                            })}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex flex-wrap gap-2">
                      <Link href={`/account/services?device=${device.id}`}>
                        <Button size="sm">
                          <Wrench className="h-4 w-4 mr-2" />
                          Book Service
                        </Button>
                      </Link>
                      {device.amc_status === 'none' && (
                        <Link href="/account/amc">
                          <Button size="sm" variant="outline">
                            <Shield className="h-4 w-4 mr-2" />
                            Buy AMC
                          </Button>
                        </Link>
                      )}
                      <Button size="sm" variant="ghost">
                        View History
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Help Section */}
      <Card className="mt-8">
        <CardContent className="py-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-primary/10 rounded-full">
              <QrCode className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold">Can&apos;t find your serial number?</h3>
              <p className="text-sm text-muted-foreground">
                The serial number is printed on a sticker on your water purifier or on your purchase invoice.
              </p>
            </div>
            <Button variant="outline" asChild>
              <a href="https://wa.me/919311939076?text=I need help finding my serial number" target="_blank" rel="noopener noreferrer">
                Get Help
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
