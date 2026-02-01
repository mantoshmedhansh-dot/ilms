'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  MapPin,
  Plus,
  Pencil,
  Trash2,
  Star,
  Home,
  Building2,
  ChevronLeft,
  Loader2,
  Phone,
  User,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
import { toast } from 'sonner';
import { useIsAuthenticated, CustomerAddress } from '@/lib/storefront/auth-store';
import { authApi } from '@/lib/storefront/api';

const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
  'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
  'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
  'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Delhi', 'Chandigarh', 'Puducherry', 'Ladakh', 'Jammu and Kashmir',
];

const ADDRESS_TYPES = [
  { value: 'HOME', label: 'Home', icon: Home },
  { value: 'OFFICE', label: 'Office', icon: Building2 },
  { value: 'OTHER', label: 'Other', icon: MapPin },
];

interface AddressFormData {
  address_type: string;
  contact_name: string;
  contact_phone: string;
  address_line1: string;
  address_line2: string;
  landmark: string;
  city: string;
  state: string;
  pincode: string;
  is_default: boolean;
}

const defaultFormData: AddressFormData = {
  address_type: 'HOME',
  contact_name: '',
  contact_phone: '',
  address_line1: '',
  address_line2: '',
  landmark: '',
  city: '',
  state: '',
  pincode: '',
  is_default: false,
};

export default function AddressesPage() {
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();

  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [editingAddress, setEditingAddress] = useState<CustomerAddress | null>(null);
  const [deletingAddress, setDeletingAddress] = useState<CustomerAddress | null>(null);
  const [formData, setFormData] = useState<AddressFormData>(defaultFormData);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/account/login?redirect=/account/addresses');
      return;
    }

    fetchAddresses();
  }, [isAuthenticated, router]);

  const fetchAddresses = async () => {
    try {
      setLoading(true);
      const data = await authApi.getAddresses();
      setAddresses(data);
    } catch (error) {
      console.error('Failed to fetch addresses:', error);
      toast.error('Failed to load addresses');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!formData.address_line1 || !formData.city || !formData.state || !formData.pincode) {
      toast.error('Please fill all required fields');
      return;
    }

    if (!/^\d{6}$/.test(formData.pincode)) {
      toast.error('Please enter a valid 6-digit pincode');
      return;
    }

    try {
      setSaving(true);
      await authApi.addAddress({
        address_type: formData.address_type,
        contact_name: formData.contact_name || undefined,
        contact_phone: formData.contact_phone || undefined,
        address_line1: formData.address_line1,
        address_line2: formData.address_line2 || undefined,
        landmark: formData.landmark || undefined,
        city: formData.city,
        state: formData.state,
        pincode: formData.pincode,
        country: 'India',
        is_default: formData.is_default,
      });
      toast.success('Address added successfully');
      setIsAddOpen(false);
      setFormData(defaultFormData);
      fetchAddresses();
    } catch (error) {
      console.error('Failed to add address:', error);
      toast.error('Failed to add address');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (address: CustomerAddress) => {
    setEditingAddress(address);
    setFormData({
      address_type: address.address_type,
      contact_name: address.contact_name || '',
      contact_phone: address.contact_phone || '',
      address_line1: address.address_line1,
      address_line2: address.address_line2 || '',
      landmark: address.landmark || '',
      city: address.city,
      state: address.state,
      pincode: address.pincode,
      is_default: address.is_default,
    });
    setIsEditOpen(true);
  };

  const handleUpdate = async () => {
    if (!editingAddress) return;

    if (!formData.address_line1 || !formData.city || !formData.state || !formData.pincode) {
      toast.error('Please fill all required fields');
      return;
    }

    try {
      setSaving(true);
      await authApi.updateAddress(editingAddress.id, {
        address_type: formData.address_type,
        contact_name: formData.contact_name || undefined,
        contact_phone: formData.contact_phone || undefined,
        address_line1: formData.address_line1,
        address_line2: formData.address_line2 || undefined,
        landmark: formData.landmark || undefined,
        city: formData.city,
        state: formData.state,
        pincode: formData.pincode,
        country: 'India',
        is_default: formData.is_default,
      });
      toast.success('Address updated successfully');
      setIsEditOpen(false);
      setEditingAddress(null);
      setFormData(defaultFormData);
      fetchAddresses();
    } catch (error) {
      console.error('Failed to update address:', error);
      toast.error('Failed to update address');
    } finally {
      setSaving(false);
    }
  };

  const handleSetDefault = async (address: CustomerAddress) => {
    try {
      await authApi.setDefaultAddress(address.id);
      toast.success('Default address updated');
      fetchAddresses();
    } catch (error) {
      console.error('Failed to set default:', error);
      toast.error('Failed to update default address');
    }
  };

  const handleDelete = async () => {
    if (!deletingAddress) return;

    try {
      setSaving(true);
      await authApi.deleteAddress(deletingAddress.id);
      toast.success('Address deleted');
      setIsDeleteOpen(false);
      setDeletingAddress(null);
      fetchAddresses();
    } catch (error) {
      console.error('Failed to delete address:', error);
      toast.error('Failed to delete address');
    } finally {
      setSaving(false);
    }
  };

  const getAddressTypeIcon = (type: string) => {
    const addressType = ADDRESS_TYPES.find((t) => t.value === type);
    const Icon = addressType?.icon || MapPin;
    return <Icon className="h-4 w-4" />;
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="flex items-center gap-4 mb-8">
        <Link href="/account">
          <Button variant="ghost" size="icon">
            <ChevronLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl md:text-3xl font-bold">Saved Addresses</h1>
          <p className="text-muted-foreground mt-1">Manage your delivery addresses</p>
        </div>
        <Button onClick={() => { setFormData(defaultFormData); setIsAddOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" />
          Add New
        </Button>
      </div>

      {addresses.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <MapPin className="h-16 w-16 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No Saved Addresses</h3>
            <p className="text-muted-foreground text-center mb-6">
              Add your first address for faster checkout
            </p>
            <Button onClick={() => { setFormData(defaultFormData); setIsAddOpen(true); }}>
              <Plus className="h-4 w-4 mr-2" />
              Add Address
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {addresses.map((address) => (
            <Card key={address.id} className={address.is_default ? 'border-primary' : ''}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getAddressTypeIcon(address.address_type)}
                    <CardTitle className="text-base">{address.address_type}</CardTitle>
                    {address.is_default && (
                      <Badge variant="secondary" className="ml-2">
                        <Star className="h-3 w-3 mr-1 fill-current" />
                        Default
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="icon" onClick={() => handleEdit(address)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:text-destructive"
                      onClick={() => { setDeletingAddress(address); setIsDeleteOpen(true); }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                {address.contact_name && (
                  <div className="flex items-center gap-2 text-sm mb-1">
                    <User className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>{address.contact_name}</span>
                  </div>
                )}
                {address.contact_phone && (
                  <div className="flex items-center gap-2 text-sm mb-2">
                    <Phone className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>{address.contact_phone}</span>
                  </div>
                )}
                <p className="text-sm text-muted-foreground">
                  {address.address_line1}
                  {address.address_line2 && `, ${address.address_line2}`}
                  {address.landmark && ` (Near ${address.landmark})`}
                </p>
                <p className="text-sm text-muted-foreground">
                  {address.city}, {address.state} - {address.pincode}
                </p>

                {!address.is_default && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4"
                    onClick={() => handleSetDefault(address)}
                  >
                    <Star className="h-3.5 w-3.5 mr-1" />
                    Set as Default
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add/Edit Address Dialog */}
      <Dialog open={isAddOpen || isEditOpen} onOpenChange={(open) => {
        if (!open) {
          setIsAddOpen(false);
          setIsEditOpen(false);
          setEditingAddress(null);
          setFormData(defaultFormData);
        }
      }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{isEditOpen ? 'Edit Address' : 'Add New Address'}</DialogTitle>
            <DialogDescription>
              {isEditOpen ? 'Update your address details' : 'Add a new delivery address'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Address Type */}
            <div className="space-y-2">
              <Label>Address Type</Label>
              <div className="flex gap-2">
                {ADDRESS_TYPES.map((type) => {
                  const Icon = type.icon;
                  return (
                    <Button
                      key={type.value}
                      type="button"
                      variant={formData.address_type === type.value ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setFormData({ ...formData, address_type: type.value })}
                    >
                      <Icon className="h-4 w-4 mr-1" />
                      {type.label}
                    </Button>
                  );
                })}
              </div>
            </div>

            {/* Contact Details */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="contact_name">Contact Name</Label>
                <Input
                  id="contact_name"
                  value={formData.contact_name}
                  onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                  placeholder="Full name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="contact_phone">Phone Number</Label>
                <Input
                  id="contact_phone"
                  value={formData.contact_phone}
                  onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                  placeholder="10-digit mobile"
                  maxLength={10}
                />
              </div>
            </div>

            {/* Address Lines */}
            <div className="space-y-2">
              <Label htmlFor="address_line1">Address Line 1 *</Label>
              <Input
                id="address_line1"
                value={formData.address_line1}
                onChange={(e) => setFormData({ ...formData, address_line1: e.target.value })}
                placeholder="House/Flat No., Building, Street"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="address_line2">Address Line 2</Label>
              <Input
                id="address_line2"
                value={formData.address_line2}
                onChange={(e) => setFormData({ ...formData, address_line2: e.target.value })}
                placeholder="Area, Colony"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="landmark">Landmark</Label>
              <Input
                id="landmark"
                value={formData.landmark}
                onChange={(e) => setFormData({ ...formData, landmark: e.target.value })}
                placeholder="Near temple, school, etc."
              />
            </div>

            {/* City, State, Pincode */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="city">City *</Label>
                <Input
                  id="city"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="City"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pincode">Pincode *</Label>
                <Input
                  id="pincode"
                  value={formData.pincode}
                  onChange={(e) => setFormData({ ...formData, pincode: e.target.value.replace(/\D/g, '') })}
                  placeholder="6-digit pincode"
                  maxLength={6}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="state">State *</Label>
              <Select
                value={formData.state}
                onValueChange={(value) => setFormData({ ...formData, state: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select state" />
                </SelectTrigger>
                <SelectContent>
                  {INDIAN_STATES.map((state) => (
                    <SelectItem key={state} value={state}>
                      {state}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Default Address Toggle */}
            <div className="flex items-center justify-between rounded-lg border p-4">
              <div className="space-y-0.5">
                <Label>Set as Default</Label>
                <p className="text-sm text-muted-foreground">
                  Use this address by default at checkout
                </p>
              </div>
              <Button
                type="button"
                variant={formData.is_default ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFormData({ ...formData, is_default: !formData.is_default })}
              >
                {formData.is_default ? 'Yes' : 'No'}
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsAddOpen(false);
                setIsEditOpen(false);
                setEditingAddress(null);
                setFormData(defaultFormData);
              }}
            >
              Cancel
            </Button>
            <Button onClick={isEditOpen ? handleUpdate : handleAdd} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {isEditOpen ? 'Update Address' : 'Add Address'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Address</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this address? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setIsDeleteOpen(false); setDeletingAddress(null); }}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
