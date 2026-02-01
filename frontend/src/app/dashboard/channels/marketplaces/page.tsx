'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Store,
  ShoppingBag,
  Package,
  Truck,
  Plus,
  Settings,
  RefreshCcw,
  CheckCircle2,
  XCircle,
  Loader2,
  MoreHorizontal,
  Wifi,
  WifiOff,
  AlertTriangle,
  Clock,
  ChevronRight,
  ArrowUpDown,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { PageHeader } from '@/components/common';
import { marketplacesApi } from '@/lib/api';

interface MarketplaceIntegration {
  id: string;
  marketplace_type: string;
  client_id: string;
  seller_id: string | null;
  is_sandbox: boolean;
  is_active: boolean;
  last_sync_at: string | null;
  created_at: string;
}

interface MarketplaceCredentials {
  marketplace_type: string;
  client_id: string;
  client_secret: string;
  refresh_token?: string;
  api_key?: string;
  seller_id?: string;
  is_sandbox: boolean;
}

const SUPPORTED_MARKETPLACES = [
  {
    type: 'AMAZON',
    name: 'Amazon',
    icon: Store,
    color: 'orange',
    bgColor: 'bg-orange-100',
    textColor: 'text-orange-600',
    description: 'Amazon Seller Central / SP-API',
    requiredFields: ['client_id', 'client_secret', 'refresh_token'],
  },
  {
    type: 'FLIPKART',
    name: 'Flipkart',
    icon: ShoppingBag,
    color: 'blue',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-600',
    description: 'Flipkart Seller Hub API',
    requiredFields: ['client_id', 'client_secret'],
  },
  {
    type: 'MEESHO',
    name: 'Meesho',
    icon: Package,
    color: 'pink',
    bgColor: 'bg-pink-100',
    textColor: 'text-pink-600',
    description: 'Meesho Supplier API',
    requiredFields: ['api_key'],
  },
  {
    type: 'SNAPDEAL',
    name: 'Snapdeal',
    icon: Store,
    color: 'red',
    bgColor: 'bg-red-100',
    textColor: 'text-red-600',
    description: 'Snapdeal Seller API',
    requiredFields: ['client_id', 'client_secret'],
  },
];

export default function MarketplacesPage() {
  const queryClient = useQueryClient();
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isSyncDialogOpen, setIsSyncDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedMarketplace, setSelectedMarketplace] = useState<string | null>(null);
  const [syncType, setSyncType] = useState<'orders' | 'inventory'>('orders');
  const [testingConnection, setTestingConnection] = useState<string | null>(null);

  const [credentials, setCredentials] = useState<MarketplaceCredentials>({
    marketplace_type: '',
    client_id: '',
    client_secret: '',
    refresh_token: '',
    api_key: '',
    seller_id: '',
    is_sandbox: true,
  });

  // Fetch integrations
  const { data: integrations, isLoading, refetch } = useQuery({
    queryKey: ['marketplace-integrations'],
    queryFn: () => marketplacesApi.listIntegrations(),
  });

  // Create integration mutation
  const createMutation = useMutation({
    mutationFn: (creds: MarketplaceCredentials) => marketplacesApi.createIntegration(creds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplace-integrations'] });
      toast.success('Marketplace integration created successfully');
      setIsAddDialogOpen(false);
      resetCredentials();
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to create integration'),
  });

  // Delete integration mutation
  const deleteMutation = useMutation({
    mutationFn: (marketplaceType: string) => marketplacesApi.deleteIntegration(marketplaceType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplace-integrations'] });
      toast.success('Integration deleted successfully');
      setIsDeleteDialogOpen(false);
      setSelectedMarketplace(null);
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete integration'),
  });

  // Toggle integration mutation
  const toggleMutation = useMutation({
    mutationFn: ({ marketplaceType, isActive }: { marketplaceType: string; isActive: boolean }) =>
      marketplacesApi.toggleIntegration(marketplaceType, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplace-integrations'] });
      toast.success('Integration status updated');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to update status'),
  });

  // Test connection mutation
  const testConnectionMutation = useMutation({
    mutationFn: (marketplaceType: string) => marketplacesApi.testConnection(marketplaceType),
    onSuccess: (result, marketplaceType) => {
      if (result.success) {
        toast.success(`${marketplaceType} connection successful`);
      } else {
        toast.error(result.message || 'Connection test failed');
      }
      setTestingConnection(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Connection test failed');
      setTestingConnection(null);
    },
  });

  // Sync orders mutation
  const syncOrdersMutation = useMutation({
    mutationFn: ({ marketplaceType, fromDate }: { marketplaceType: string; fromDate?: string }) =>
      marketplacesApi.syncOrders(marketplaceType, { from_date: fromDate }),
    onSuccess: (result) => {
      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
      queryClient.invalidateQueries({ queryKey: ['marketplace-integrations'] });
      setIsSyncDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message || 'Order sync failed'),
  });

  const resetCredentials = () => {
    setCredentials({
      marketplace_type: '',
      client_id: '',
      client_secret: '',
      refresh_token: '',
      api_key: '',
      seller_id: '',
      is_sandbox: true,
    });
  };

  const handleTestConnection = (marketplaceType: string) => {
    setTestingConnection(marketplaceType);
    testConnectionMutation.mutate(marketplaceType);
  };

  const getMarketplaceConfig = (type: string) => {
    return SUPPORTED_MARKETPLACES.find(m => m.type === type);
  };

  const formatLastSync = (dateStr: string | null) => {
    if (!dateStr) return 'Never synced';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`;
    return date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  const integrationsList = integrations || [];
  const connectedTypes = integrationsList.map((i: MarketplaceIntegration) => i.marketplace_type);
  const availableMarketplaces = SUPPORTED_MARKETPLACES.filter(m => !connectedTypes.includes(m.type));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Marketplace Integrations"
        description="Connect and manage your marketplace selling channels"
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCcw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
              <DialogTrigger asChild>
                <Button disabled={availableMarketplaces.length === 0}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Marketplace
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle>Add Marketplace Integration</DialogTitle>
                  <DialogDescription>
                    Connect a new marketplace to sync orders and inventory
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="space-y-2">
                    <Label>Select Marketplace</Label>
                    <Select
                      value={credentials.marketplace_type}
                      onValueChange={(value) => setCredentials({ ...credentials, marketplace_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Choose marketplace" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableMarketplaces.map((mp) => (
                          <SelectItem key={mp.type} value={mp.type}>
                            <div className="flex items-center gap-2">
                              <mp.icon className={`h-4 w-4 ${mp.textColor}`} />
                              {mp.name}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {credentials.marketplace_type && (
                    <>
                      <div className="space-y-2">
                        <Label>Client ID / App ID</Label>
                        <Input
                          placeholder="Enter client ID"
                          value={credentials.client_id}
                          onChange={(e) => setCredentials({ ...credentials, client_id: e.target.value })}
                        />
                      </div>

                      {credentials.marketplace_type !== 'MEESHO' && (
                        <div className="space-y-2">
                          <Label>Client Secret / App Secret</Label>
                          <Input
                            type="password"
                            placeholder="Enter client secret"
                            value={credentials.client_secret}
                            onChange={(e) => setCredentials({ ...credentials, client_secret: e.target.value })}
                          />
                        </div>
                      )}

                      {credentials.marketplace_type === 'AMAZON' && (
                        <div className="space-y-2">
                          <Label>Refresh Token</Label>
                          <Input
                            type="password"
                            placeholder="Enter refresh token"
                            value={credentials.refresh_token}
                            onChange={(e) => setCredentials({ ...credentials, refresh_token: e.target.value })}
                          />
                        </div>
                      )}

                      {credentials.marketplace_type === 'MEESHO' && (
                        <div className="space-y-2">
                          <Label>API Key</Label>
                          <Input
                            type="password"
                            placeholder="Enter API key"
                            value={credentials.api_key}
                            onChange={(e) => setCredentials({ ...credentials, api_key: e.target.value })}
                          />
                        </div>
                      )}

                      <div className="space-y-2">
                        <Label>Seller ID (Optional)</Label>
                        <Input
                          placeholder="Enter seller ID"
                          value={credentials.seller_id}
                          onChange={(e) => setCredentials({ ...credentials, seller_id: e.target.value })}
                        />
                      </div>

                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label>Sandbox Mode</Label>
                          <p className="text-xs text-muted-foreground">
                            Use test environment for development
                          </p>
                        </div>
                        <Switch
                          checked={credentials.is_sandbox}
                          onCheckedChange={(checked) => setCredentials({ ...credentials, is_sandbox: checked })}
                        />
                      </div>
                    </>
                  )}
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => {
                    setIsAddDialogOpen(false);
                    resetCredentials();
                  }}>
                    Cancel
                  </Button>
                  <Button
                    onClick={() => createMutation.mutate(credentials)}
                    disabled={!credentials.marketplace_type || !credentials.client_id || createMutation.isPending}
                  >
                    {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Connect Marketplace
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Connected</CardTitle>
            <Store className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{integrationsList.length}</div>
            <p className="text-xs text-muted-foreground">
              Marketplace integrations
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {integrationsList.filter((i: MarketplaceIntegration) => i.is_active).length}
            </div>
            <p className="text-xs text-muted-foreground">
              Syncing enabled
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Available</CardTitle>
            <Plus className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{availableMarketplaces.length}</div>
            <p className="text-xs text-muted-foreground">
              Marketplaces to connect
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sandbox</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {integrationsList.filter((i: MarketplaceIntegration) => i.is_sandbox).length}
            </div>
            <p className="text-xs text-muted-foreground">
              In test mode
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Connected Marketplaces */}
      <Card>
        <CardHeader>
          <CardTitle>Connected Marketplaces</CardTitle>
          <CardDescription>
            Manage your marketplace integrations and sync settings
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : integrationsList.length === 0 ? (
            <div className="text-center py-8">
              <Store className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-lg font-medium">No Marketplaces Connected</p>
              <p className="text-sm text-muted-foreground mb-4">
                Connect your first marketplace to start syncing orders and inventory
              </p>
              <Button onClick={() => setIsAddDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add Marketplace
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {integrationsList.map((integration: MarketplaceIntegration) => {
                const config = getMarketplaceConfig(integration.marketplace_type);
                if (!config) return null;

                return (
                  <div
                    key={integration.id}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className={`p-3 rounded-lg ${config.bgColor}`}>
                        <config.icon className={`h-6 w-6 ${config.textColor}`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold">{config.name}</h3>
                          {integration.is_sandbox && (
                            <Badge variant="outline" className="text-xs">Sandbox</Badge>
                          )}
                          {integration.is_active ? (
                            <Badge className="bg-green-100 text-green-700 text-xs">
                              <Wifi className="mr-1 h-3 w-3" /> Active
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-xs">
                              <WifiOff className="mr-1 h-3 w-3" /> Inactive
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          Client ID: {integration.client_id}
                          {integration.seller_id && ` | Seller: ${integration.seller_id}`}
                        </p>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                          <Clock className="h-3 w-3" />
                          Last sync: {formatLastSync(integration.last_sync_at)}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTestConnection(integration.marketplace_type)}
                        disabled={testingConnection === integration.marketplace_type}
                      >
                        {testingConnection === integration.marketplace_type ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <>
                            <Wifi className="mr-2 h-4 w-4" />
                            Test
                          </>
                        )}
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedMarketplace(integration.marketplace_type);
                          setIsSyncDialogOpen(true);
                        }}
                        disabled={!integration.is_active}
                      >
                        <ArrowUpDown className="mr-2 h-4 w-4" />
                        Sync
                      </Button>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => toggleMutation.mutate({
                              marketplaceType: integration.marketplace_type,
                              isActive: !integration.is_active
                            })}
                          >
                            {integration.is_active ? (
                              <>
                                <WifiOff className="mr-2 h-4 w-4" />
                                Disable
                              </>
                            ) : (
                              <>
                                <Wifi className="mr-2 h-4 w-4" />
                                Enable
                              </>
                            )}
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Settings className="mr-2 h-4 w-4" />
                            Settings
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-red-600"
                            onClick={() => {
                              setSelectedMarketplace(integration.marketplace_type);
                              setIsDeleteDialogOpen(true);
                            }}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Available Marketplaces */}
      {availableMarketplaces.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Available Marketplaces</CardTitle>
            <CardDescription>
              Connect more marketplaces to expand your selling channels
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {availableMarketplaces.map((mp) => (
                <div
                  key={mp.type}
                  className="p-4 border rounded-lg hover:border-primary cursor-pointer transition-colors"
                  onClick={() => {
                    setCredentials({ ...credentials, marketplace_type: mp.type });
                    setIsAddDialogOpen(true);
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${mp.bgColor}`}>
                      <mp.icon className={`h-5 w-5 ${mp.textColor}`} />
                    </div>
                    <div>
                      <h4 className="font-medium">{mp.name}</h4>
                      <p className="text-xs text-muted-foreground">{mp.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sync Dialog */}
      <Dialog open={isSyncDialogOpen} onOpenChange={setIsSyncDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Sync {selectedMarketplace}</DialogTitle>
            <DialogDescription>
              Choose what to sync from this marketplace
            </DialogDescription>
          </DialogHeader>
          <Tabs value={syncType} onValueChange={(v) => setSyncType(v as 'orders' | 'inventory')}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="orders">Orders</TabsTrigger>
              <TabsTrigger value="inventory">Inventory</TabsTrigger>
            </TabsList>
            <TabsContent value="orders" className="space-y-4 pt-4">
              <p className="text-sm text-muted-foreground">
                Import new orders from {selectedMarketplace} into your order management system.
              </p>
              <Button
                className="w-full"
                onClick={() => selectedMarketplace && syncOrdersMutation.mutate({
                  marketplaceType: selectedMarketplace
                })}
                disabled={syncOrdersMutation.isPending}
              >
                {syncOrdersMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Package className="mr-2 h-4 w-4" />
                )}
                Sync Orders
              </Button>
            </TabsContent>
            <TabsContent value="inventory" className="space-y-4 pt-4">
              <p className="text-sm text-muted-foreground">
                Push your current inventory levels to {selectedMarketplace}.
              </p>
              <Button className="w-full" disabled>
                <ArrowUpDown className="mr-2 h-4 w-4" />
                Sync Inventory (Coming Soon)
              </Button>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Integration</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the {selectedMarketplace} integration?
              This will stop all syncing and remove stored credentials.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => selectedMarketplace && deleteMutation.mutate(selectedMarketplace)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
