'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  Wrench,
  Plus,
  ChevronRight,
  Calendar,
  Clock,
  CheckCircle,
  AlertCircle,
  Phone,
  MapPin,
  Loader2,
  Filter,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { useIsAuthenticated } from '@/lib/storefront/auth-store';
import { portalApi, ServiceRequest as APIServiceRequest } from '@/lib/storefront/api';

// Types - extended from API type
interface ServiceRequest {
  id: string;
  ticket_number: string;
  device_name: string;
  device_serial: string;
  service_type: 'installation' | 'repair' | 'maintenance' | 'filter_change' | 'complaint';
  status: 'pending' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled';
  scheduled_date?: string;
  scheduled_time?: string;
  technician_name?: string;
  technician_phone?: string;
  description: string;
  address: string;
  created_at: string;
  completed_at?: string;
  rating?: number;
}

const serviceTypes = [
  { value: 'installation', label: 'Installation', description: 'New product installation' },
  { value: 'repair', label: 'Repair', description: 'Fix a problem with your purifier' },
  { value: 'maintenance', label: 'Maintenance', description: 'Regular servicing' },
  { value: 'filter_change', label: 'Filter Change', description: 'Replace filters' },
  { value: 'complaint', label: 'Complaint', description: 'Report an issue' },
];

function ServicesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isAuthenticated = useIsAuthenticated();
  const [services, setServices] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [showBookDialog, setShowBookDialog] = useState(false);
  const [bookingService, setBookingService] = useState(false);
  const [activeTab, setActiveTab] = useState('all');

  const [newService, setNewService] = useState({
    device_id: searchParams.get('device') || '',
    service_type: '',
    preferred_date: '',
    preferred_time: '',
    description: '',
    address: '',
  });

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/account/login?redirect=/account/services');
      return;
    }

    const fetchServices = async () => {
      try {
        const data = await portalApi.getServiceRequests({ limit: 50 });
        // Transform API data to local format
        const transformedServices: ServiceRequest[] = (data.items || []).map((req: APIServiceRequest) => ({
          id: req.id,
          ticket_number: req.ticket_number || `SR-${req.id.slice(0, 8)}`,
          device_name: req.product_name || 'Water Purifier',
          device_serial: req.product_id || '',
          service_type: (req.request_type?.toLowerCase() || 'maintenance') as ServiceRequest['service_type'],
          status: (req.status?.toLowerCase() || 'pending') as ServiceRequest['status'],
          scheduled_date: req.scheduled_date,
          scheduled_time: req.scheduled_time,
          technician_name: req.technician_name,
          technician_phone: req.technician_phone,
          description: req.description || req.subject || '',
          address: req.address || '',
          created_at: req.created_at,
          completed_at: req.completed_at,
          rating: req.rating,
        }));
        setServices(transformedServices);
      } catch (error) {
        console.error('Failed to load service requests:', error);
        setServices([]);
      } finally {
        setLoading(false);
      }
    };

    fetchServices();
  }, [isAuthenticated, router]);

  const handleBookService = async () => {
    if (!newService.service_type || !newService.preferred_date) {
      toast.error('Please fill in required fields');
      return;
    }

    setBookingService(true);
    try {
      // Map local service type to API request type
      const requestTypeMap: Record<string, string> = {
        'installation': 'INSTALLATION',
        'repair': 'REPAIR',
        'maintenance': 'MAINTENANCE',
        'filter_change': 'REPAIR',
        'complaint': 'COMPLAINT',
      };

      await portalApi.createServiceRequest({
        request_type: requestTypeMap[newService.service_type] as any || 'GENERAL',
        subject: `${serviceTypes.find(t => t.value === newService.service_type)?.label || 'Service'} Request`,
        description: newService.description || `Service type: ${newService.service_type}`,
        preferred_date: newService.preferred_date,
        preferred_time: newService.preferred_time,
        address: newService.address,
      });

      toast.success('Service request submitted! We\'ll call you to confirm.');
      setShowBookDialog(false);
      setNewService({
        device_id: '',
        service_type: '',
        preferred_date: '',
        preferred_time: '',
        description: '',
        address: '',
      });

      // Refresh the service list
      const data = await portalApi.getServiceRequests({ limit: 50 });
      const transformedServices: ServiceRequest[] = (data.items || []).map((req: APIServiceRequest) => ({
        id: req.id,
        ticket_number: req.ticket_number || `SR-${req.id.slice(0, 8)}`,
        device_name: req.product_name || 'Water Purifier',
        device_serial: req.product_id || '',
        service_type: (req.request_type?.toLowerCase() || 'maintenance') as ServiceRequest['service_type'],
        status: (req.status?.toLowerCase() || 'pending') as ServiceRequest['status'],
        scheduled_date: req.scheduled_date,
        scheduled_time: req.scheduled_time,
        technician_name: req.technician_name,
        technician_phone: req.technician_phone,
        description: req.description || req.subject || '',
        address: req.address || '',
        created_at: req.created_at,
        completed_at: req.completed_at,
        rating: req.rating,
      }));
      setServices(transformedServices);
    } catch (error) {
      console.error('Failed to submit service request:', error);
      toast.error('Failed to submit service request. Please try again.');
    } finally {
      setBookingService(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <Badge variant="secondary">Pending</Badge>;
      case 'confirmed':
        return <Badge className="bg-blue-100 text-blue-800">Confirmed</Badge>;
      case 'in_progress':
        return <Badge className="bg-yellow-100 text-yellow-800">In Progress</Badge>;
      case 'completed':
        return <Badge className="bg-green-100 text-green-800">Completed</Badge>;
      case 'cancelled':
        return <Badge className="bg-red-100 text-red-800">Cancelled</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getServiceTypeLabel = (type: string) => {
    return serviceTypes.find((t) => t.value === type)?.label || type;
  };

  const filteredServices = activeTab === 'all'
    ? services
    : services.filter((s) =>
        activeTab === 'active'
          ? ['pending', 'confirmed', 'in_progress'].includes(s.status)
          : s.status === 'completed'
      );

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
          <h1 className="text-2xl md:text-3xl font-bold">Service Requests</h1>
          <p className="text-muted-foreground mt-1">
            Book and track your service appointments
          </p>
        </div>
        <Dialog open={showBookDialog} onOpenChange={setShowBookDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Book Service
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Book a Service</DialogTitle>
              <DialogDescription>
                Schedule a service visit for your water purifier.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {/* Service Type */}
              <div>
                <Label>Service Type *</Label>
                <Select
                  value={newService.service_type}
                  onValueChange={(value) =>
                    setNewService({ ...newService, service_type: value })
                  }
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue placeholder="Select service type" />
                  </SelectTrigger>
                  <SelectContent>
                    {serviceTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        <div>
                          <span className="font-medium">{type.label}</span>
                          <span className="text-muted-foreground ml-2">- {type.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Preferred Date */}
              <div>
                <Label>Preferred Date *</Label>
                <Input
                  type="date"
                  min={new Date().toISOString().split('T')[0]}
                  value={newService.preferred_date}
                  onChange={(e) =>
                    setNewService({ ...newService, preferred_date: e.target.value })
                  }
                  className="mt-1.5"
                />
              </div>

              {/* Preferred Time */}
              <div>
                <Label>Preferred Time Slot</Label>
                <Select
                  value={newService.preferred_time}
                  onValueChange={(value) =>
                    setNewService({ ...newService, preferred_time: value })
                  }
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue placeholder="Select time slot" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="9-12">9:00 AM - 12:00 PM</SelectItem>
                    <SelectItem value="12-3">12:00 PM - 3:00 PM</SelectItem>
                    <SelectItem value="3-6">3:00 PM - 6:00 PM</SelectItem>
                    <SelectItem value="6-9">6:00 PM - 9:00 PM</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Description */}
              <div>
                <Label>Problem Description</Label>
                <Textarea
                  placeholder="Describe the issue or service required..."
                  value={newService.description}
                  onChange={(e) =>
                    setNewService({ ...newService, description: e.target.value })
                  }
                  className="mt-1.5"
                  rows={3}
                />
              </div>

              {/* Address */}
              <div>
                <Label>Service Address</Label>
                <Textarea
                  placeholder="Enter complete address for service visit..."
                  value={newService.address}
                  onChange={(e) =>
                    setNewService({ ...newService, address: e.target.value })
                  }
                  className="mt-1.5"
                  rows={2}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowBookDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleBookService} disabled={bookingService}>
                {bookingService ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  'Submit Request'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-6">
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Service Requests List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : filteredServices.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Wrench className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Service Requests</h3>
            <p className="text-muted-foreground mb-4">
              {activeTab === 'all'
                ? 'You haven\'t booked any services yet.'
                : activeTab === 'active'
                ? 'No active service requests.'
                : 'No completed services.'}
            </p>
            <Button onClick={() => setShowBookDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Book Your First Service
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredServices.map((service) => (
            <Card key={service.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold">#{service.ticket_number}</span>
                      {getStatusBadge(service.status)}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {service.device_name} ({service.device_serial})
                    </p>
                  </div>
                  <Badge variant="outline">{getServiceTypeLabel(service.service_type)}</Badge>
                </div>

                <p className="text-sm mb-4">{service.description}</p>

                <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                  {service.scheduled_date && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      <span>
                        {new Date(service.scheduled_date).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </span>
                    </div>
                  )}
                  {service.scheduled_time && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Clock className="h-4 w-4" />
                      <span>{service.scheduled_time}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-muted-foreground col-span-2">
                    <MapPin className="h-4 w-4" />
                    <span>{service.address}</span>
                  </div>
                </div>

                {/* Technician Info */}
                {service.technician_name && service.status !== 'completed' && (
                  <div className="bg-muted/50 rounded-lg p-3 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">Technician: {service.technician_name}</p>
                      {service.technician_phone && (
                        <p className="text-xs text-muted-foreground">
                          Contact: {service.technician_phone}
                        </p>
                      )}
                    </div>
                    {service.technician_phone && (
                      <Button size="sm" variant="outline" asChild>
                        <a href={`tel:${service.technician_phone}`}>
                          <Phone className="h-4 w-4 mr-2" />
                          Call
                        </a>
                      </Button>
                    )}
                  </div>
                )}

                {/* Rating for completed services */}
                {service.status === 'completed' && service.rating && (
                  <div className="flex items-center gap-2 mt-4 pt-4 border-t">
                    <span className="text-sm text-muted-foreground">Your Rating:</span>
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <span
                          key={star}
                          className={`text-lg ${
                            star <= service.rating! ? 'text-yellow-500' : 'text-gray-300'
                          }`}
                        >
                          ★
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Quick Help */}
      <Card className="mt-8">
        <CardContent className="py-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-primary/10 rounded-full">
              <Phone className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold">Need Urgent Help?</h3>
              <p className="text-sm text-muted-foreground">
                Call our 24/7 helpline for immediate assistance.
              </p>
            </div>
            <Button asChild>
              <a href="tel:18001234567">Call 1800-123-4567</a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function ServicesPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[60vh] flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <ServicesPageContent />
    </Suspense>
  );
}
