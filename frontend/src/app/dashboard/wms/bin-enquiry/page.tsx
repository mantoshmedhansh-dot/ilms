'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Grid3X3, Package, Layers, Warehouse, Calendar, Tag, Barcode } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatDate, formatCurrency } from '@/lib/utils';

interface BinContent {
  id: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  serial_number?: string;
  batch_number?: string;
  quantity: number;
  unit_cost: number;
  total_value: number;
  received_date: string;
  expiry_date?: string;
  status: 'AVAILABLE' | 'RESERVED' | 'DAMAGED' | 'EXPIRED';
}

interface BinDetails {
  id: string;
  code: string;
  zone_name: string;
  warehouse_name: string;
  bin_type: string;
  row: string;
  column: string;
  level: string;
  max_weight: number;
  current_weight: number;
  max_volume: number;
  current_volume: number;
  is_locked: boolean;
  is_active: boolean;
  total_items: number;
  total_value: number;
  contents: BinContent[];
}

const binEnquiryApi = {
  searchBin: async (binCode: string): Promise<BinDetails | null> => {
    try {
      const { data } = await apiClient.get(`/wms/bins/enquiry/${binCode}`);
      return data;
    } catch {
      return null;
    }
  },
  searchProduct: async (sku: string) => {
    try {
      const { data } = await apiClient.get('/wms/bins/product-location', { params: { sku } });
      return data;
    } catch {
      return { items: [] };
    }
  },
};

const statusColors: Record<string, string> = {
  AVAILABLE: 'bg-green-100 text-green-800',
  RESERVED: 'bg-yellow-100 text-yellow-800',
  DAMAGED: 'bg-red-100 text-red-800',
  EXPIRED: 'bg-gray-100 text-gray-800',
};

export default function BinEnquiryPage() {
  const [searchType, setSearchType] = useState<'bin' | 'product'>('bin');
  const [searchValue, setSearchValue] = useState('');
  const [searchTriggered, setSearchTriggered] = useState(false);

  const { data: binDetails, isLoading: binLoading, refetch: refetchBin } = useQuery({
    queryKey: ['bin-enquiry', searchValue],
    queryFn: () => binEnquiryApi.searchBin(searchValue),
    enabled: searchTriggered && searchType === 'bin' && searchValue.length > 0,
  });

  const { data: productLocations, isLoading: productLoading, refetch: refetchProduct } = useQuery({
    queryKey: ['product-location', searchValue],
    queryFn: () => binEnquiryApi.searchProduct(searchValue),
    enabled: searchTriggered && searchType === 'product' && searchValue.length > 0,
  });

  const handleSearch = () => {
    if (!searchValue.trim()) return;
    setSearchTriggered(true);
    if (searchType === 'bin') {
      refetchBin();
    } else {
      refetchProduct();
    }
  };

  const isLoading = binLoading || productLoading;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Bin Enquiry"
        description="Search and view bin contents or find product locations"
      />

      {/* Search Section */}
      <Card>
        <CardHeader>
          <CardTitle>Search</CardTitle>
          <CardDescription>Search by bin code or product SKU</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="w-[180px]">
              <Label htmlFor="searchType" className="sr-only">Search Type</Label>
              <Select value={searchType} onValueChange={(v: 'bin' | 'product') => setSearchType(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="bin">
                    <div className="flex items-center gap-2">
                      <Grid3X3 className="h-4 w-4" />
                      Bin Code
                    </div>
                  </SelectItem>
                  <SelectItem value="product">
                    <div className="flex items-center gap-2">
                      <Package className="h-4 w-4" />
                      Product SKU
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1">
              <Input
                placeholder={searchType === 'bin' ? 'Enter bin code (e.g., A-01-01-01)' : 'Enter product SKU'}
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <Button onClick={handleSearch} disabled={isLoading || !searchValue.trim()}>
              <Search className="mr-2 h-4 w-4" />
              Search
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results Section */}
      {searchTriggered && searchType === 'bin' && (
        <>
          {binLoading ? (
            <Card>
              <CardContent className="py-12">
                <div className="flex flex-col items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                  <p className="mt-4 text-muted-foreground">Searching...</p>
                </div>
              </CardContent>
            </Card>
          ) : binDetails ? (
            <div className="space-y-6">
              {/* Bin Information */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
                        <Grid3X3 className="h-6 w-6 text-muted-foreground" />
                      </div>
                      <div>
                        <CardTitle className="font-mono">{binDetails.code}</CardTitle>
                        <CardDescription>
                          {binDetails.zone_name} | {binDetails.warehouse_name}
                        </CardDescription>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        binDetails.is_locked ? 'bg-orange-100 text-orange-800' : 'bg-green-100 text-green-800'
                      }`}>
                        {binDetails.is_locked ? 'Locked' : 'Available'}
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        binDetails.bin_type === 'STANDARD' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                      }`}>
                        {binDetails.bin_type}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div className="flex items-center gap-3">
                      <Layers className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <div className="text-sm text-muted-foreground">Location</div>
                        <div className="font-medium">
                          Row {binDetails.row}, Col {binDetails.column}, Lvl {binDetails.level}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Package className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <div className="text-sm text-muted-foreground">Total Items</div>
                        <div className="font-medium">{binDetails.total_items}</div>
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Weight Capacity</div>
                      <div className="font-medium">
                        {binDetails.current_weight.toFixed(1)} / {binDetails.max_weight} kg
                      </div>
                      <div className="w-full h-2 bg-muted rounded-full mt-1 overflow-hidden">
                        <div
                          className="h-full bg-blue-500"
                          style={{ width: `${(binDetails.current_weight / binDetails.max_weight) * 100}%` }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Total Value</div>
                      <div className="font-medium text-green-600">{formatCurrency(binDetails.total_value)}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Bin Contents */}
              <Card>
                <CardHeader>
                  <CardTitle>Bin Contents</CardTitle>
                  <CardDescription>{binDetails.contents.length} items in this bin</CardDescription>
                </CardHeader>
                <CardContent>
                  {binDetails.contents.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      This bin is empty
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {binDetails.contents.map((item) => (
                        <div key={item.id} className="flex items-center justify-between p-4 border rounded-lg">
                          <div className="flex items-center gap-4">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                              <Package className="h-5 w-5 text-muted-foreground" />
                            </div>
                            <div>
                              <div className="font-medium">{item.product_name}</div>
                              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                <span className="flex items-center gap-1">
                                  <Tag className="h-3 w-3" />
                                  {item.product_sku}
                                </span>
                                {item.serial_number && (
                                  <span className="flex items-center gap-1">
                                    <Barcode className="h-3 w-3" />
                                    {item.serial_number}
                                  </span>
                                )}
                                {item.batch_number && (
                                  <span>Batch: {item.batch_number}</span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-6">
                            <div className="text-right">
                              <div className="font-mono font-bold">{item.quantity}</div>
                              <div className="text-xs text-muted-foreground">qty</div>
                            </div>
                            <div className="text-right">
                              <div className="font-mono">{formatCurrency(item.total_value)}</div>
                              <div className="text-xs text-muted-foreground">@ {formatCurrency(item.unit_cost)}</div>
                            </div>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[item.status]}`}>
                              {item.status}
                            </span>
                            <div className="text-right text-sm text-muted-foreground">
                              <div className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {formatDate(item.received_date)}
                              </div>
                              {item.expiry_date && (
                                <div className="text-red-600">Exp: {formatDate(item.expiry_date)}</div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="py-12">
                <div className="flex flex-col items-center justify-center">
                  <Grid3X3 className="h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No bin found with code &quot;{searchValue}&quot;</p>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {searchTriggered && searchType === 'product' && (
        <>
          {productLoading ? (
            <Card>
              <CardContent className="py-12">
                <div className="flex flex-col items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                  <p className="mt-4 text-muted-foreground">Searching...</p>
                </div>
              </CardContent>
            </Card>
          ) : productLocations?.items?.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Product Locations</CardTitle>
                <CardDescription>
                  Found in {productLocations.items.length} bin(s)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {productLocations.items.map((location: { bin_code: string; zone_name: string; warehouse_name: string; quantity: number; status: string }, index: number) => (
                    <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                          <Grid3X3 className="h-5 w-5 text-muted-foreground" />
                        </div>
                        <div>
                          <div className="font-mono font-medium">{location.bin_code}</div>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Layers className="h-3 w-3" />
                            {location.zone_name}
                            <span>|</span>
                            <Warehouse className="h-3 w-3" />
                            {location.warehouse_name}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <div className="font-mono font-bold">{location.quantity}</div>
                          <div className="text-xs text-muted-foreground">qty</div>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[location.status] || 'bg-gray-100'}`}>
                          {location.status}
                        </span>
                        <Button variant="outline" size="sm" onClick={() => {
                          setSearchType('bin');
                          setSearchValue(location.bin_code);
                          setSearchTriggered(true);
                        }}>
                          View Bin
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-12">
                <div className="flex flex-col items-center justify-center">
                  <Package className="h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No locations found for SKU &quot;{searchValue}&quot;</p>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
