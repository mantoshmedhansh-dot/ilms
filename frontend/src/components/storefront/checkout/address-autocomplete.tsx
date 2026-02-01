'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { MapPin, Navigation, Loader2, Search, X, QrCode } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { addressApi, AddressSuggestion, AddressDetails } from '@/lib/storefront/api';
import { ShippingAddress } from '@/types/storefront';

interface AddressAutocompleteProps {
  onAddressSelect: (address: ShippingAddress) => void;
  initialValue?: string;
  placeholder?: string;
  disabled?: boolean;
}

export default function AddressAutocomplete({
  onAddressSelect,
  initialValue = '',
  placeholder = 'Start typing your address...',
  disabled = false,
}: AddressAutocompleteProps) {
  const [query, setQuery] = useState(initialValue);
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const [digiPinDialogOpen, setDigiPinDialogOpen] = useState(false);
  const [digiPinInput, setDigiPinInput] = useState('');
  const [isLookingUpDigiPin, setIsLookingUpDigiPin] = useState(false);

  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  const sessionTokenRef = useRef<string>(generateSessionToken());

  // Generate a unique session token for billing optimization
  function generateSessionToken(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  // Debounced search
  const searchAddresses = useCallback(async (searchQuery: string) => {
    if (searchQuery.length < 3) {
      setSuggestions([]);
      return;
    }

    setIsLoading(true);
    try {
      const results = await addressApi.autocomplete(searchQuery, sessionTokenRef.current);
      setSuggestions(results);
      setIsOpen(results.length > 0);
    } catch (error) {
      console.error('Address search error:', error);
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle input change with debounce
  const handleInputChange = (value: string) => {
    setQuery(value);

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      searchAddresses(value);
    }, 300);
  };

  // Handle suggestion selection
  const handleSuggestionSelect = async (suggestion: AddressSuggestion) => {
    setIsLoading(true);
    setIsOpen(false);
    setQuery(suggestion.description);

    try {
      const details = await addressApi.getPlaceDetails(
        suggestion.place_id,
        sessionTokenRef.current
      );

      if (details) {
        const address: ShippingAddress = {
          full_name: '',
          phone: '',
          address_line1: details.address_line1 || suggestion.main_text,
          address_line2: details.address_line2 || suggestion.secondary_text,
          city: details.city,
          state: details.state,
          pincode: details.pincode,
          country: details.country || 'India',
        };

        onAddressSelect(address);

        // Show DigiPin if available
        if (details.digipin) {
          toast.success(`DigiPin: ${details.digipin}`, {
            description: 'Your digital address code',
            duration: 5000,
          });
        }

        // Generate new session token for next search
        sessionTokenRef.current = generateSessionToken();
      }
    } catch (error) {
      console.error('Error getting place details:', error);
      toast.error('Could not fetch address details');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle "Use my location" click
  const handleUseLocation = async () => {
    if (!navigator.geolocation) {
      toast.error('Geolocation is not supported by your browser');
      return;
    }

    setIsLocating(true);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude } = position.coords;
          const details = await addressApi.reverseGeocode(latitude, longitude);

          if (details) {
            const address: ShippingAddress = {
              full_name: '',
              phone: '',
              address_line1: details.address_line1,
              address_line2: details.address_line2 || '',
              city: details.city,
              state: details.state,
              pincode: details.pincode,
              country: details.country || 'India',
            };

            setQuery(details.formatted_address);
            onAddressSelect(address);

            if (details.digipin) {
              toast.success(`DigiPin: ${details.digipin}`, {
                description: 'Your digital address code',
                duration: 5000,
              });
            }
          } else {
            toast.error('Could not determine your address');
          }
        } catch (error) {
          console.error('Reverse geocode error:', error);
          toast.error('Could not determine your address');
        } finally {
          setIsLocating(false);
        }
      },
      (error) => {
        setIsLocating(false);
        switch (error.code) {
          case error.PERMISSION_DENIED:
            toast.error('Location access denied. Please enable location permissions.');
            break;
          case error.POSITION_UNAVAILABLE:
            toast.error('Location information unavailable');
            break;
          case error.TIMEOUT:
            toast.error('Location request timed out');
            break;
          default:
            toast.error('Could not get your location');
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000, // 5 minutes
      }
    );
  };

  // Handle DigiPin lookup
  const handleDigiPinLookup = async () => {
    const cleanDigiPin = digiPinInput.toUpperCase().replace(/[-\s]/g, '');

    if (cleanDigiPin.length !== 10) {
      toast.error('Please enter a valid 10-character DigiPin');
      return;
    }

    setIsLookingUpDigiPin(true);

    try {
      const info = await addressApi.lookupDigiPin(cleanDigiPin);

      if (info) {
        // Get full address from coordinates
        const details = await addressApi.reverseGeocode(info.latitude, info.longitude);

        if (details) {
          const address: ShippingAddress = {
            full_name: '',
            phone: '',
            address_line1: details.address_line1,
            address_line2: details.address_line2 || '',
            city: details.city,
            state: details.state,
            pincode: details.pincode,
            country: details.country || 'India',
          };

          setQuery(details.formatted_address);
          onAddressSelect(address);
          setDigiPinDialogOpen(false);
          setDigiPinInput('');

          toast.success('Address loaded from DigiPin');
        } else if (info.address) {
          // Use info from DigiPin response
          const address: ShippingAddress = {
            full_name: '',
            phone: '',
            address_line1: info.address,
            address_line2: '',
            city: info.city || '',
            state: info.state || '',
            pincode: info.pincode || '',
            country: 'India',
          };

          onAddressSelect(address);
          setDigiPinDialogOpen(false);
          setDigiPinInput('');

          toast.success('Address loaded from DigiPin');
        }
      } else {
        toast.error('Invalid DigiPin code');
      }
    } catch (error) {
      console.error('DigiPin lookup error:', error);
      toast.error('Could not lookup DigiPin');
    } finally {
      setIsLookingUpDigiPin(false);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  return (
    <div className="space-y-2">
      <Label htmlFor="address-search" className="flex items-center gap-2">
        <Search className="h-4 w-4" />
        Search Address
      </Label>

      <div className="flex gap-2 items-start">
        {/* Search input with label below */}
        <div className="flex-1">
          <Popover open={isOpen} onOpenChange={setIsOpen}>
            <PopoverTrigger asChild>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="address-search"
                  value={query}
                  onChange={(e) => handleInputChange(e.target.value)}
                  placeholder={placeholder}
                  className="pl-10 pr-10"
                  disabled={disabled || isLocating}
                  autoComplete="off"
                />
                {isLoading && (
                  <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
                )}
                {!isLoading && query && (
                  <button
                    type="button"
                    onClick={() => {
                      setQuery('');
                      setSuggestions([]);
                    }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            </PopoverTrigger>
            <PopoverContent
              className="w-[var(--radix-popover-trigger-width)] p-0"
              align="start"
            >
              <Command>
                <CommandList>
                  <CommandEmpty>
                    {isLoading ? 'Searching...' : 'No addresses found'}
                  </CommandEmpty>
                  <CommandGroup heading="Suggestions">
                    {suggestions.map((suggestion) => (
                      <CommandItem
                        key={suggestion.place_id}
                        value={suggestion.description}
                        onSelect={() => handleSuggestionSelect(suggestion)}
                        className="cursor-pointer"
                      >
                        <MapPin className="mr-2 h-4 w-4 text-muted-foreground" />
                        <div className="flex flex-col">
                          <span className="font-medium">{suggestion.main_text}</span>
                          <span className="text-xs text-muted-foreground">
                            {suggestion.secondary_text}
                          </span>
                        </div>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
          <p className="text-xs text-muted-foreground mt-1.5">
            Search by address, landmark, or area
          </p>
        </div>

        {/* Use my location button with label below */}
        <div className="flex flex-col items-center">
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={handleUseLocation}
            disabled={disabled || isLocating}
            title="Use my current location"
            className="h-10 w-10"
          >
            {isLocating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Navigation className="h-4 w-4" />
            )}
          </Button>
          <p className="text-xs text-muted-foreground mt-1.5 text-center whitespace-nowrap">
            Use my current location
          </p>
        </div>

        {/* DigiPin lookup button with label below */}
        <div className="flex flex-col items-center">
          <Dialog open={digiPinDialogOpen} onOpenChange={setDigiPinDialogOpen}>
            <DialogTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="icon"
                disabled={disabled}
                title="Enter DigiPin code"
                className="h-10 w-10"
              >
                <QrCode className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <QrCode className="h-5 w-5" />
                  Enter DigiPin
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <p className="text-sm text-muted-foreground">
                  DigiPin is India's digital addressing system. Enter your 10-character
                  DigiPin code to auto-fill your address.
                </p>
                <div className="space-y-2">
                  <Label htmlFor="digipin">DigiPin Code</Label>
                  <Input
                    id="digipin"
                    value={digiPinInput}
                    onChange={(e) => setDigiPinInput(e.target.value.toUpperCase())}
                    placeholder="e.g., 4H8J9K2M3P"
                    maxLength={12}
                    className="font-mono text-lg tracking-wider"
                  />
                  <p className="text-xs text-muted-foreground">
                    Find your DigiPin at{' '}
                    <a
                      href="https://digipin.gov.in"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      digipin.gov.in
                    </a>
                  </p>
                </div>
                <Button
                  onClick={handleDigiPinLookup}
                  disabled={digiPinInput.length < 10 || isLookingUpDigiPin}
                  className="w-full"
                >
                  {isLookingUpDigiPin ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Looking up...
                    </>
                  ) : (
                    <>
                      <MapPin className="mr-2 h-4 w-4" />
                      Lookup Address
                    </>
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
          <p className="text-xs text-muted-foreground mt-1.5 text-center">
            DigiPin
          </p>
        </div>
      </div>
    </div>
  );
}
