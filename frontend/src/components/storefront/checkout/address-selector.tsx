'use client';

import { useState, useEffect } from 'react';
import {
  MapPin,
  Plus,
  Check,
  Home,
  Building2,
  MapPinned,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { authApi } from '@/lib/storefront/api';
import { CustomerAddress } from '@/lib/storefront/auth-store';
import { ShippingAddress } from '@/types/storefront';

interface AddressSelectorProps {
  onSelectAddress: (address: ShippingAddress) => void;
  onAddNewAddress: () => void;
  selectedAddress: ShippingAddress | null;
  isAuthenticated: boolean;
}

export default function AddressSelector({
  onSelectAddress,
  onAddNewAddress,
  selectedAddress,
  isAuthenticated,
}: AddressSelectorProps) {
  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    const fetchAddresses = async () => {
      try {
        const data = await authApi.getAddresses();
        setAddresses(data);

        // Auto-select default address if no address is currently selected
        if (data.length > 0 && !selectedAddress) {
          const defaultAddress = data.find((a) => a.is_default) || data[0];
          setSelectedId(defaultAddress.id);
          onSelectAddress(mapToShippingAddress(defaultAddress));
        }
      } catch (error) {
        console.error('Failed to fetch addresses:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAddresses();
  }, [isAuthenticated]);

  const mapToShippingAddress = (addr: CustomerAddress): ShippingAddress => ({
    full_name: addr.contact_name || '',
    phone: addr.contact_phone || '',
    email: '',
    address_line1: addr.address_line1,
    address_line2: addr.address_line2 || '',
    city: addr.city,
    state: addr.state,
    pincode: addr.pincode,
    country: 'India',
  });

  const handleSelectAddress = (addressId: string) => {
    setSelectedId(addressId);
    const address = addresses.find((a) => a.id === addressId);
    if (address) {
      onSelectAddress(mapToShippingAddress(address));
    }
  };

  const getAddressTypeIcon = (type?: string) => {
    switch (type) {
      case 'HOME':
        return <Home className="h-4 w-4" />;
      case 'OFFICE':
        return <Building2 className="h-4 w-4" />;
      default:
        return <MapPinned className="h-4 w-4" />;
    }
  };

  const getAddressTypeLabel = (type?: string) => {
    switch (type) {
      case 'HOME':
        return 'Home';
      case 'OFFICE':
        return 'Office';
      default:
        return 'Other';
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (addresses.length === 0) {
    return null;
  }

  return (
    <div className="mb-6">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left mb-4"
      >
        <div className="flex items-center gap-2">
          <MapPin className="h-5 w-5 text-primary" />
          <span className="font-medium">Saved Addresses</span>
          <Badge variant="secondary" className="ml-2">
            {addresses.length}
          </Badge>
        </div>
        {expanded ? (
          <ChevronUp className="h-5 w-5 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-5 w-5 text-muted-foreground" />
        )}
      </button>

      {expanded && (
        <>
          <RadioGroup
            value={selectedId || ''}
            onValueChange={handleSelectAddress}
            className="space-y-3"
          >
            {addresses.map((address) => (
              <div key={address.id} className="relative">
                <label
                  htmlFor={`address-${address.id}`}
                  className={`block cursor-pointer rounded-lg border-2 p-4 transition-colors ${
                    selectedId === address.id
                      ? 'border-primary bg-primary/5'
                      : 'border-muted hover:border-muted-foreground/50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <RadioGroupItem
                      value={address.id}
                      id={`address-${address.id}`}
                      className="mt-1"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {address.contact_name && (
                          <span className="font-medium">{address.contact_name}</span>
                        )}
                        <Badge variant="outline" className="text-xs">
                          {getAddressTypeIcon(address.address_type)}
                          <span className="ml-1">
                            {getAddressTypeLabel(address.address_type)}
                          </span>
                        </Badge>
                        {address.is_default && (
                          <Badge className="bg-green-100 text-green-800 text-xs">
                            Default
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {address.address_line1}
                        {address.address_line2 && `, ${address.address_line2}`}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {address.city}, {address.state} - {address.pincode}
                      </p>
                      {address.contact_phone && (
                        <p className="text-sm text-muted-foreground mt-1">
                          Phone: +91 {address.contact_phone}
                        </p>
                      )}
                    </div>
                    {selectedId === address.id && (
                      <Check className="h-5 w-5 text-primary flex-shrink-0" />
                    )}
                  </div>
                </label>
              </div>
            ))}
          </RadioGroup>

          <div className="mt-4 flex items-center gap-4">
            <Separator className="flex-1" />
            <span className="text-sm text-muted-foreground">or</span>
            <Separator className="flex-1" />
          </div>

          <Button
            type="button"
            variant="outline"
            onClick={onAddNewAddress}
            className="w-full mt-4"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add New Address
          </Button>
        </>
      )}
    </div>
  );
}
