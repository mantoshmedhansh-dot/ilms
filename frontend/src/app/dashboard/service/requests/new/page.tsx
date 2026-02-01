'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';

interface ServiceRequestForm {
  customer_id: string;
  customer_phone: string;
  type: string;
  priority: string;
  subject: string;
  description: string;
  product_id?: string;
  serial_number?: string;
}

const serviceTypes = [
  { value: 'INSTALLATION', label: 'Installation' },
  { value: 'WARRANTY_REPAIR', label: 'Warranty Repair' },
  { value: 'PAID_REPAIR', label: 'Paid Repair' },
  { value: 'AMC_SERVICE', label: 'AMC Service' },
  { value: 'DEMO', label: 'Demo' },
  { value: 'PREVENTIVE_MAINTENANCE', label: 'Preventive Maintenance' },
  { value: 'COMPLAINT', label: 'Complaint' },
  { value: 'FILTER_CHANGE', label: 'Filter Change' },
  { value: 'INSPECTION', label: 'Inspection' },
  { value: 'UNINSTALLATION', label: 'Uninstallation' },
];

const priorities = [
  { value: 'LOW', label: 'Low' },
  { value: 'NORMAL', label: 'Normal' },
  { value: 'HIGH', label: 'High' },
  { value: 'URGENT', label: 'Urgent' },
  { value: 'CRITICAL', label: 'Critical' },
];

const serviceRequestsApi = {
  create: async (data: Partial<ServiceRequestForm>) => {
    const response = await apiClient.post('/service-requests', data);
    return response.data;
  },
  lookupCustomer: async (phone: string) => {
    try {
      const { data } = await apiClient.get(`/customers/phone/${phone}`);
      return data;
    } catch {
      return null;
    }
  },
};

export default function NewServiceRequestPage() {
  const router = useRouter();
  const [formData, setFormData] = useState<ServiceRequestForm>({
    customer_id: '',
    customer_phone: '',
    type: '',
    priority: 'NORMAL',
    subject: '',
    description: '',
    product_id: '',
    serial_number: '',
  });
  const [customerLookup, setCustomerLookup] = useState<{ name: string; id: string } | null>(null);

  const createMutation = useMutation({
    mutationFn: serviceRequestsApi.create,
    onSuccess: (data) => {
      toast.success('Service request created successfully');
      router.push(`/dashboard/service/requests/${data.id}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create service request');
    },
  });

  const handlePhoneLookup = async () => {
    if (formData.customer_phone.length >= 10) {
      const customer = await serviceRequestsApi.lookupCustomer(formData.customer_phone);
      if (customer) {
        setCustomerLookup({ name: customer.name, id: customer.id });
        setFormData({ ...formData, customer_id: customer.id });
      } else {
        setCustomerLookup(null);
        toast.info('Customer not found. A new customer will be created.');
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.customer_phone) {
      toast.error('Customer phone is required');
      return;
    }
    if (!formData.type) {
      toast.error('Service type is required');
      return;
    }
    if (!formData.subject) {
      toast.error('Subject is required');
      return;
    }

    createMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Create Service Request"
        description="Create a new service request for a customer"
        actions={
          <Button variant="outline" asChild>
            <Link href="/dashboard/service">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Service
            </Link>
          </Button>
        }
      />

      <form onSubmit={handleSubmit}>
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Customer Information */}
          <Card>
            <CardHeader>
              <CardTitle>Customer Information</CardTitle>
              <CardDescription>Enter customer details or search by phone</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="phone">Customer Phone *</Label>
                <div className="flex gap-2">
                  <Input
                    id="phone"
                    placeholder="+91 98765 43210"
                    value={formData.customer_phone}
                    onChange={(e) => setFormData({ ...formData, customer_phone: e.target.value })}
                  />
                  <Button type="button" variant="outline" onClick={handlePhoneLookup}>
                    Lookup
                  </Button>
                </div>
                {customerLookup && (
                  <p className="text-sm text-green-600">
                    Found: {customerLookup.name}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="serial">Serial Number (Optional)</Label>
                <Input
                  id="serial"
                  placeholder="Product serial number"
                  value={formData.serial_number}
                  onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
                />
              </div>
            </CardContent>
          </Card>

          {/* Request Details */}
          <Card>
            <CardHeader>
              <CardTitle>Request Details</CardTitle>
              <CardDescription>Specify the type and priority of the request</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="type">Service Type *</Label>
                  <Select
                    value={formData.type}
                    onValueChange={(value) => setFormData({ ...formData, type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      {serviceTypes.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="priority">Priority</Label>
                  <Select
                    value={formData.priority}
                    onValueChange={(value) => setFormData({ ...formData, priority: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select priority" />
                    </SelectTrigger>
                    <SelectContent>
                      {priorities.map((priority) => (
                        <SelectItem key={priority.value} value={priority.value}>
                          {priority.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="subject">Subject *</Label>
                <Input
                  id="subject"
                  placeholder="Brief description of the issue"
                  value={formData.subject}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Detailed description of the issue..."
                  rows={4}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-end gap-4 mt-6">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Create Request
          </Button>
        </div>
      </form>
    </div>
  );
}
