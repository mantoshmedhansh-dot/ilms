'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { format } from 'date-fns';
import {
  Building2,
  Package,
  TrendingDown,
  ArrowRightLeft,
  Wrench,
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  RefreshCw,
  AlertTriangle,
  Shield,
  Calendar,
  DollarSign,
  CheckCircle,
  Clock,
  XCircle,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
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
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';

import {
  fixedAssetsApi,
  Asset,
  AssetCategory,
  DepreciationEntry,
  AssetTransfer,
  AssetMaintenance,
  FixedAssetsDashboard,
  DepreciationMethod,
  AssetStatus,
  TransferStatus,
  MaintenanceStatus,
  warehousesApi,
  hrApi,
} from '@/lib/api';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
};

const getStatusBadge = (status: AssetStatus) => {
  const variants: Record<AssetStatus, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
    ACTIVE: { variant: 'default', label: 'Active' },
    UNDER_MAINTENANCE: { variant: 'secondary', label: 'Under Maintenance' },
    DISPOSED: { variant: 'destructive', label: 'Disposed' },
    SOLD: { variant: 'outline', label: 'Sold' },
    WRITTEN_OFF: { variant: 'destructive', label: 'Written Off' },
  };
  const { variant, label } = variants[status] || { variant: 'default', label: status };
  return <Badge variant={variant}>{label}</Badge>;
};

const getTransferStatusBadge = (status: TransferStatus) => {
  const variants: Record<TransferStatus, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
    PENDING: { variant: 'secondary', label: 'Pending' },
    APPROVED: { variant: 'default', label: 'Approved' },
    COMPLETED: { variant: 'outline', label: 'Completed' },
    CANCELLED: { variant: 'destructive', label: 'Cancelled' },
  };
  const { variant, label } = variants[status] || { variant: 'default', label: status };
  return <Badge variant={variant}>{label}</Badge>;
};

const getMaintenanceStatusBadge = (status: MaintenanceStatus) => {
  const variants: Record<MaintenanceStatus, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
    SCHEDULED: { variant: 'secondary', label: 'Scheduled' },
    IN_PROGRESS: { variant: 'default', label: 'In Progress' },
    COMPLETED: { variant: 'outline', label: 'Completed' },
    CANCELLED: { variant: 'destructive', label: 'Cancelled' },
  };
  const { variant, label } = variants[status] || { variant: 'default', label: status };
  return <Badge variant={variant}>{label}</Badge>;
};

export default function FixedAssetsPage() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  // Dialog states
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [assetDialogOpen, setAssetDialogOpen] = useState(false);
  const [depreciationDialogOpen, setDepreciationDialogOpen] = useState(false);
  const [transferDialogOpen, setTransferDialogOpen] = useState(false);
  const [maintenanceDialogOpen, setMaintenanceDialogOpen] = useState(false);
  const [disposeDialogOpen, setDisposeDialogOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);

  const queryClient = useQueryClient();

  // Queries
  const { data: dashboard, isLoading: dashboardLoading } = useQuery({
    queryKey: ['fixed-assets-dashboard'],
    queryFn: fixedAssetsApi.getDashboard,
  });

  const { data: assets, isLoading: assetsLoading } = useQuery({
    queryKey: ['fixed-assets', searchTerm, statusFilter, categoryFilter],
    queryFn: () => fixedAssetsApi.assets.list({
      search: searchTerm || undefined,
      status: statusFilter !== 'all' ? statusFilter as AssetStatus : undefined,
      category_id: categoryFilter !== 'all' ? categoryFilter : undefined,
    }),
  });

  const { data: categories, isLoading: categoriesLoading } = useQuery({
    queryKey: ['asset-categories'],
    queryFn: () => fixedAssetsApi.categories.list(),
  });

  const { data: categoriesDropdown } = useQuery({
    queryKey: ['asset-categories-dropdown'],
    queryFn: fixedAssetsApi.categories.dropdown,
  });

  const { data: depreciation, isLoading: depreciationLoading } = useQuery({
    queryKey: ['depreciation-entries'],
    queryFn: () => fixedAssetsApi.depreciation.list(),
  });

  const { data: transfers, isLoading: transfersLoading } = useQuery({
    queryKey: ['asset-transfers'],
    queryFn: () => fixedAssetsApi.transfers.list(),
  });

  const { data: maintenance, isLoading: maintenanceLoading } = useQuery({
    queryKey: ['asset-maintenance'],
    queryFn: () => fixedAssetsApi.maintenance.list(),
  });

  const { data: warehouses } = useQuery({
    queryKey: ['warehouses-dropdown'],
    queryFn: warehousesApi.dropdown,
  });

  const { data: departments } = useQuery({
    queryKey: ['departments-dropdown'],
    queryFn: hrApi.departments.dropdown,
  });

  const { data: employees } = useQuery({
    queryKey: ['employees-dropdown'],
    queryFn: () => hrApi.employees.dropdown(),
  });

  // Mutations
  const createCategoryMutation = useMutation({
    mutationFn: fixedAssetsApi.categories.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-categories'] });
      queryClient.invalidateQueries({ queryKey: ['asset-categories-dropdown'] });
      setCategoryDialogOpen(false);
      toast.success('Asset category created successfully');
    },
    onError: () => {
      toast.error('Failed to create category');
    },
  });

  const createAssetMutation = useMutation({
    mutationFn: fixedAssetsApi.assets.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fixed-assets'] });
      queryClient.invalidateQueries({ queryKey: ['fixed-assets-dashboard'] });
      setAssetDialogOpen(false);
      toast.success('Asset created successfully');
    },
    onError: () => {
      toast.error('Failed to create asset');
    },
  });

  const runDepreciationMutation = useMutation({
    mutationFn: fixedAssetsApi.depreciation.run,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['depreciation-entries'] });
      queryClient.invalidateQueries({ queryKey: ['fixed-assets'] });
      queryClient.invalidateQueries({ queryKey: ['fixed-assets-dashboard'] });
      setDepreciationDialogOpen(false);
      toast.success(`Depreciation run completed. ${data.entries_created} entries created, total: ${formatCurrency(data.total_depreciation)}`);
    },
    onError: () => {
      toast.error('Failed to run depreciation');
    },
  });

  const createTransferMutation = useMutation({
    mutationFn: fixedAssetsApi.transfers.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-transfers'] });
      setTransferDialogOpen(false);
      toast.success('Transfer request created successfully');
    },
    onError: () => {
      toast.error('Failed to create transfer request');
    },
  });

  const createMaintenanceMutation = useMutation({
    mutationFn: fixedAssetsApi.maintenance.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-maintenance'] });
      setMaintenanceDialogOpen(false);
      toast.success('Maintenance scheduled successfully');
    },
    onError: () => {
      toast.error('Failed to schedule maintenance');
    },
  });

  const disposeAssetMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { disposal_date: string; disposal_price: number; disposal_reason: string } }) =>
      fixedAssetsApi.assets.dispose(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fixed-assets'] });
      queryClient.invalidateQueries({ queryKey: ['fixed-assets-dashboard'] });
      setDisposeDialogOpen(false);
      setSelectedAsset(null);
      toast.success('Asset disposed successfully');
    },
    onError: () => {
      toast.error('Failed to dispose asset');
    },
  });

  const approveTransferMutation = useMutation({
    mutationFn: fixedAssetsApi.transfers.approve,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-transfers'] });
      toast.success('Transfer approved');
    },
    onError: () => {
      toast.error('Failed to approve transfer');
    },
  });

  const completeTransferMutation = useMutation({
    mutationFn: fixedAssetsApi.transfers.complete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-transfers'] });
      queryClient.invalidateQueries({ queryKey: ['fixed-assets'] });
      toast.success('Transfer completed');
    },
    onError: () => {
      toast.error('Failed to complete transfer');
    },
  });

  // Form handlers
  const handleCreateCategory = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createCategoryMutation.mutate({
      code: formData.get('code') as string,
      name: formData.get('name') as string,
      description: formData.get('description') as string || undefined,
      depreciation_method: formData.get('depreciation_method') as DepreciationMethod,
      depreciation_rate: parseFloat(formData.get('depreciation_rate') as string),
      useful_life_years: parseInt(formData.get('useful_life_years') as string),
    });
  };

  const handleCreateAsset = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createAssetMutation.mutate({
      name: formData.get('name') as string,
      description: formData.get('description') as string || undefined,
      category_id: formData.get('category_id') as string,
      serial_number: formData.get('serial_number') as string || undefined,
      manufacturer: formData.get('manufacturer') as string || undefined,
      warehouse_id: formData.get('warehouse_id') as string || undefined,
      department_id: formData.get('department_id') as string || undefined,
      purchase_date: formData.get('purchase_date') as string,
      purchase_price: parseFloat(formData.get('purchase_price') as string),
      capitalization_date: formData.get('capitalization_date') as string,
      salvage_value: parseFloat(formData.get('salvage_value') as string) || 0,
    });
  };

  const handleRunDepreciation = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    runDepreciationMutation.mutate({
      period_date: formData.get('period_date') as string,
      financial_year: formData.get('financial_year') as string,
    });
  };

  const handleCreateTransfer = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createTransferMutation.mutate({
      asset_id: formData.get('asset_id') as string,
      to_warehouse_id: formData.get('to_warehouse_id') as string || undefined,
      to_department_id: formData.get('to_department_id') as string || undefined,
      to_custodian_id: formData.get('to_custodian_id') as string || undefined,
      transfer_date: formData.get('transfer_date') as string,
      reason: formData.get('reason') as string || undefined,
    });
  };

  const handleCreateMaintenance = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createMaintenanceMutation.mutate({
      asset_id: formData.get('asset_id') as string,
      maintenance_type: formData.get('maintenance_type') as string,
      description: formData.get('description') as string,
      scheduled_date: formData.get('scheduled_date') as string,
      estimated_cost: parseFloat(formData.get('estimated_cost') as string) || 0,
    });
  };

  const handleDisposeAsset = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedAsset) return;
    const formData = new FormData(e.currentTarget);
    disposeAssetMutation.mutate({
      id: selectedAsset.id,
      data: {
        disposal_date: formData.get('disposal_date') as string,
        disposal_price: parseFloat(formData.get('disposal_price') as string) || 0,
        disposal_reason: formData.get('disposal_reason') as string,
      },
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Fixed Assets</h1>
          <p className="text-muted-foreground">
            Manage fixed assets, depreciation, transfers, and maintenance
          </p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="dashboard" className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Dashboard
          </TabsTrigger>
          <TabsTrigger value="assets" className="flex items-center gap-2">
            <Package className="h-4 w-4" />
            Assets
          </TabsTrigger>
          <TabsTrigger value="categories" className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Categories
          </TabsTrigger>
          <TabsTrigger value="depreciation" className="flex items-center gap-2">
            <TrendingDown className="h-4 w-4" />
            Depreciation
          </TabsTrigger>
          <TabsTrigger value="transfers" className="flex items-center gap-2">
            <ArrowRightLeft className="h-4 w-4" />
            Transfers
          </TabsTrigger>
          <TabsTrigger value="maintenance" className="flex items-center gap-2">
            <Wrench className="h-4 w-4" />
            Maintenance
          </TabsTrigger>
        </TabsList>

        {/* Dashboard Tab */}
        <TabsContent value="dashboard" className="space-y-6">
          {dashboardLoading ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {[...Array(8)].map((_, i) => (
                <Skeleton key={i} className="h-32" />
              ))}
            </div>
          ) : dashboard ? (
            <>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">Total Assets</CardTitle>
                    <Package className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{dashboard.total_assets}</div>
                    <p className="text-xs text-muted-foreground">
                      {dashboard.active_assets} active, {dashboard.disposed_assets} disposed
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">Capitalized Value</CardTitle>
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatCurrency(dashboard.total_capitalized_value)}</div>
                    <p className="text-xs text-muted-foreground">
                      Total investment in assets
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">Book Value</CardTitle>
                    <TrendingDown className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatCurrency(dashboard.total_current_book_value)}</div>
                    <p className="text-xs text-muted-foreground">
                      Acc. Dep: {formatCurrency(dashboard.total_accumulated_depreciation)}
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">YTD Depreciation</CardTitle>
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatCurrency(dashboard.ytd_depreciation)}</div>
                    <p className="text-xs text-muted-foreground">
                      Monthly: {formatCurrency(dashboard.monthly_depreciation)}
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">Under Maintenance</CardTitle>
                    <Wrench className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{dashboard.under_maintenance}</div>
                    <p className="text-xs text-muted-foreground">
                      {dashboard.pending_maintenance} pending
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">Pending Transfers</CardTitle>
                    <ArrowRightLeft className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{dashboard.pending_transfers}</div>
                    <p className="text-xs text-muted-foreground">
                      Awaiting approval
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">Warranty Expiring</CardTitle>
                    <AlertTriangle className="h-4 w-4 text-orange-500" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{dashboard.warranty_expiring_soon}</div>
                    <p className="text-xs text-muted-foreground">
                      Within next 30 days
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">Insurance Expiring</CardTitle>
                    <Shield className="h-4 w-4 text-orange-500" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{dashboard.insurance_expiring_soon}</div>
                    <p className="text-xs text-muted-foreground">
                      Within next 30 days
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Category-wise breakdown */}
              <Card>
                <CardHeader>
                  <CardTitle>Assets by Category</CardTitle>
                  <CardDescription>Distribution of assets across categories</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Category</TableHead>
                        <TableHead className="text-right">Count</TableHead>
                        <TableHead className="text-right">Book Value</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dashboard.category_wise.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={3} className="text-center text-muted-foreground">
                            No assets found
                          </TableCell>
                        </TableRow>
                      ) : (
                        dashboard.category_wise.map((cat, i) => (
                          <TableRow key={i}>
                            <TableCell className="font-medium">{cat.category_name}</TableCell>
                            <TableCell className="text-right">{cat.count}</TableCell>
                            <TableCell className="text-right">{formatCurrency(cat.book_value)}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          ) : null}
        </TabsContent>

        {/* Assets Tab */}
        <TabsContent value="assets" className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search assets..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-64 pl-9"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="ACTIVE">Active</SelectItem>
                  <SelectItem value="UNDER_MAINTENANCE">Under Maintenance</SelectItem>
                  <SelectItem value="DISPOSED">Disposed</SelectItem>
                  <SelectItem value="SOLD">Sold</SelectItem>
                  <SelectItem value="WRITTEN_OFF">Written Off</SelectItem>
                </SelectContent>
              </Select>
              <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {categoriesDropdown?.map((cat) => (
                    <SelectItem key={cat.id} value={cat.id}>{cat.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Dialog open={assetDialogOpen} onOpenChange={setAssetDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Asset
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Add New Asset</DialogTitle>
                  <DialogDescription>Enter the asset details</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateAsset}>
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="name">Asset Name *</Label>
                        <Input id="name" name="name" required />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="category_id">Category *</Label>
                        <Select name="category_id" required>
                          <SelectTrigger>
                            <SelectValue placeholder="Select category" />
                          </SelectTrigger>
                          <SelectContent>
                            {categoriesDropdown?.map((cat) => (
                              <SelectItem key={cat.id} value={cat.id}>
                                {cat.name} ({cat.depreciation_method} @ {cat.depreciation_rate}%)
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="serial_number">Serial Number</Label>
                        <Input id="serial_number" name="serial_number" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="manufacturer">Manufacturer</Label>
                        <Input id="manufacturer" name="manufacturer" />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="warehouse_id">Warehouse</Label>
                        <Select name="warehouse_id">
                          <SelectTrigger>
                            <SelectValue placeholder="Select warehouse" />
                          </SelectTrigger>
                          <SelectContent>
                            {warehouses?.map((wh) => (
                              <SelectItem key={wh.id} value={wh.id}>{wh.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="department_id">Department</Label>
                        <Select name="department_id">
                          <SelectTrigger>
                            <SelectValue placeholder="Select department" />
                          </SelectTrigger>
                          <SelectContent>
                            {departments?.map((dept) => (
                              <SelectItem key={dept.id} value={dept.id}>{dept.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="purchase_date">Purchase Date *</Label>
                        <Input id="purchase_date" name="purchase_date" type="date" required />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="purchase_price">Purchase Price *</Label>
                        <Input id="purchase_price" name="purchase_price" type="number" step="0.01" required />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="salvage_value">Salvage Value</Label>
                        <Input id="salvage_value" name="salvage_value" type="number" step="0.01" defaultValue="0" />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="capitalization_date">Capitalization Date *</Label>
                      <Input id="capitalization_date" name="capitalization_date" type="date" required />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="description">Description</Label>
                      <Textarea id="description" name="description" rows={2} />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setAssetDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={createAssetMutation.isPending}>
                      {createAssetMutation.isPending ? 'Creating...' : 'Create Asset'}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Asset Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead className="text-right">Purchase Price</TableHead>
                    <TableHead className="text-right">Book Value</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-10"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {assetsLoading ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8">
                        <RefreshCw className="h-6 w-6 animate-spin mx-auto" />
                      </TableCell>
                    </TableRow>
                  ) : assets?.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                        No assets found
                      </TableCell>
                    </TableRow>
                  ) : (
                    assets?.items.map((asset) => (
                      <TableRow key={asset.id}>
                        <TableCell className="font-mono">{asset.asset_code}</TableCell>
                        <TableCell className="font-medium">{asset.name}</TableCell>
                        <TableCell>{asset.category_name}</TableCell>
                        <TableCell>{asset.warehouse_name || asset.department_name || '-'}</TableCell>
                        <TableCell className="text-right">{formatCurrency(asset.purchase_price)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(asset.current_book_value)}</TableCell>
                        <TableCell>{getStatusBadge(asset.status)}</TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                onClick={() => {
                                  setSelectedAsset(asset);
                                  setTransferDialogOpen(true);
                                }}
                              >
                                <ArrowRightLeft className="mr-2 h-4 w-4" />
                                Transfer
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => {
                                  setSelectedAsset(asset);
                                  setMaintenanceDialogOpen(true);
                                }}
                              >
                                <Wrench className="mr-2 h-4 w-4" />
                                Schedule Maintenance
                              </DropdownMenuItem>
                              {asset.status === 'ACTIVE' && (
                                <DropdownMenuItem
                                  onClick={() => {
                                    setSelectedAsset(asset);
                                    setDisposeDialogOpen(true);
                                  }}
                                  className="text-destructive"
                                >
                                  <XCircle className="mr-2 h-4 w-4" />
                                  Dispose
                                </DropdownMenuItem>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Categories Tab */}
        <TabsContent value="categories" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Asset Categories</h2>
            <Dialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Category
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Asset Category</DialogTitle>
                  <DialogDescription>Define a new asset category with depreciation settings</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateCategory}>
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="code">Category Code *</Label>
                        <Input id="code" name="code" placeholder="e.g., COMP" required />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="cat_name">Category Name *</Label>
                        <Input id="cat_name" name="name" placeholder="e.g., Computers" required />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="description">Description</Label>
                      <Textarea id="description" name="description" rows={2} />
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="depreciation_method">Depreciation Method *</Label>
                        <Select name="depreciation_method" defaultValue="SLM">
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="SLM">Straight Line (SLM)</SelectItem>
                            <SelectItem value="WDV">Written Down Value (WDV)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="depreciation_rate">Rate (%) *</Label>
                        <Input id="depreciation_rate" name="depreciation_rate" type="number" step="0.01" min="0" max="100" required />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="useful_life_years">Useful Life (Years) *</Label>
                        <Input id="useful_life_years" name="useful_life_years" type="number" min="1" required />
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setCategoryDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={createCategoryMutation.isPending}>
                      {createCategoryMutation.isPending ? 'Creating...' : 'Create Category'}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Method</TableHead>
                    <TableHead className="text-right">Rate (%)</TableHead>
                    <TableHead className="text-right">Useful Life</TableHead>
                    <TableHead className="text-right">Asset Count</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {categoriesLoading ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8">
                        <RefreshCw className="h-6 w-6 animate-spin mx-auto" />
                      </TableCell>
                    </TableRow>
                  ) : categories?.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                        No categories found
                      </TableCell>
                    </TableRow>
                  ) : (
                    categories?.items.map((cat) => (
                      <TableRow key={cat.id}>
                        <TableCell className="font-mono">{cat.code}</TableCell>
                        <TableCell className="font-medium">{cat.name}</TableCell>
                        <TableCell className="text-muted-foreground">{cat.description || '-'}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{cat.depreciation_method}</Badge>
                        </TableCell>
                        <TableCell className="text-right">{cat.depreciation_rate}%</TableCell>
                        <TableCell className="text-right">{cat.useful_life_years} years</TableCell>
                        <TableCell className="text-right">{cat.asset_count}</TableCell>
                        <TableCell>
                          <Badge variant={cat.is_active ? 'default' : 'secondary'}>
                            {cat.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Depreciation Tab */}
        <TabsContent value="depreciation" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Depreciation Entries</h2>
            <Dialog open={depreciationDialogOpen} onOpenChange={setDepreciationDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <TrendingDown className="mr-2 h-4 w-4" />
                  Run Depreciation
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Run Depreciation</DialogTitle>
                  <DialogDescription>Calculate depreciation for all active assets</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleRunDepreciation}>
                  <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="period_date">Period Date *</Label>
                      <Input id="period_date" name="period_date" type="date" required />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="financial_year">Financial Year *</Label>
                      <Input id="financial_year" name="financial_year" placeholder="e.g., 2025-26" required />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setDepreciationDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={runDepreciationMutation.isPending}>
                      {runDepreciationMutation.isPending ? 'Processing...' : 'Run Depreciation'}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Period</TableHead>
                    <TableHead>Asset</TableHead>
                    <TableHead>Method</TableHead>
                    <TableHead className="text-right">Opening Value</TableHead>
                    <TableHead className="text-right">Depreciation</TableHead>
                    <TableHead className="text-right">Closing Value</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {depreciationLoading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        <RefreshCw className="h-6 w-6 animate-spin mx-auto" />
                      </TableCell>
                    </TableRow>
                  ) : depreciation?.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                        No depreciation entries found
                      </TableCell>
                    </TableRow>
                  ) : (
                    depreciation?.items.map((entry) => (
                      <TableRow key={entry.id}>
                        <TableCell>{format(new Date(entry.period_date), 'MMM yyyy')}</TableCell>
                        <TableCell>
                          <div className="font-medium">{entry.asset_name}</div>
                          <div className="text-xs text-muted-foreground">{entry.asset_code}</div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{entry.depreciation_method}</Badge>
                          <span className="ml-2 text-muted-foreground">{entry.depreciation_rate}%</span>
                        </TableCell>
                        <TableCell className="text-right">{formatCurrency(entry.opening_book_value)}</TableCell>
                        <TableCell className="text-right text-destructive">-{formatCurrency(entry.depreciation_amount)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(entry.closing_book_value)}</TableCell>
                        <TableCell>
                          <Badge variant={entry.is_posted ? 'default' : 'secondary'}>
                            {entry.is_posted ? 'Posted' : 'Draft'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Transfers Tab */}
        <TabsContent value="transfers" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Asset Transfers</h2>
            <Dialog open={transferDialogOpen} onOpenChange={setTransferDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  New Transfer
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Asset Transfer</DialogTitle>
                  <DialogDescription>Transfer an asset to a new location</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateTransfer}>
                  <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="asset_id">Asset *</Label>
                      <Select name="asset_id" defaultValue={selectedAsset?.id}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select asset" />
                        </SelectTrigger>
                        <SelectContent>
                          {assets?.items.filter(a => a.status === 'ACTIVE').map((asset) => (
                            <SelectItem key={asset.id} value={asset.id}>
                              {asset.asset_code} - {asset.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="to_warehouse_id">To Warehouse</Label>
                      <Select name="to_warehouse_id">
                        <SelectTrigger>
                          <SelectValue placeholder="Select warehouse" />
                        </SelectTrigger>
                        <SelectContent>
                          {warehouses?.map((wh) => (
                            <SelectItem key={wh.id} value={wh.id}>{wh.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="to_department_id">To Department</Label>
                      <Select name="to_department_id">
                        <SelectTrigger>
                          <SelectValue placeholder="Select department" />
                        </SelectTrigger>
                        <SelectContent>
                          {departments?.map((dept) => (
                            <SelectItem key={dept.id} value={dept.id}>{dept.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="to_custodian_id">To Custodian</Label>
                      <Select name="to_custodian_id">
                        <SelectTrigger>
                          <SelectValue placeholder="Select custodian" />
                        </SelectTrigger>
                        <SelectContent>
                          {employees?.map((emp) => (
                            <SelectItem key={emp.id} value={emp.id}>{emp.full_name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="transfer_date">Transfer Date *</Label>
                      <Input id="transfer_date" name="transfer_date" type="date" required />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="reason">Reason</Label>
                      <Textarea id="reason" name="reason" rows={2} />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => { setTransferDialogOpen(false); setSelectedAsset(null); }}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={createTransferMutation.isPending}>
                      {createTransferMutation.isPending ? 'Creating...' : 'Create Transfer'}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Transfer #</TableHead>
                    <TableHead>Asset</TableHead>
                    <TableHead>From</TableHead>
                    <TableHead>To</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-10"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transfersLoading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        <RefreshCw className="h-6 w-6 animate-spin mx-auto" />
                      </TableCell>
                    </TableRow>
                  ) : transfers?.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                        No transfers found
                      </TableCell>
                    </TableRow>
                  ) : (
                    transfers?.items.map((transfer) => (
                      <TableRow key={transfer.id}>
                        <TableCell className="font-mono">{transfer.transfer_number}</TableCell>
                        <TableCell>
                          <div className="font-medium">{transfer.asset_name}</div>
                          <div className="text-xs text-muted-foreground">{transfer.asset_code}</div>
                        </TableCell>
                        <TableCell>
                          {transfer.from_warehouse_name || transfer.from_department_name || '-'}
                        </TableCell>
                        <TableCell>
                          {transfer.to_warehouse_name || transfer.to_department_name || '-'}
                        </TableCell>
                        <TableCell>{format(new Date(transfer.transfer_date), 'dd MMM yyyy')}</TableCell>
                        <TableCell>{getTransferStatusBadge(transfer.status)}</TableCell>
                        <TableCell>
                          {transfer.status === 'PENDING' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => approveTransferMutation.mutate(transfer.id)}
                              disabled={approveTransferMutation.isPending}
                            >
                              <CheckCircle className="h-4 w-4" />
                            </Button>
                          )}
                          {transfer.status === 'APPROVED' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => completeTransferMutation.mutate(transfer.id)}
                              disabled={completeTransferMutation.isPending}
                            >
                              <CheckCircle className="h-4 w-4 text-green-600" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Maintenance Tab */}
        <TabsContent value="maintenance" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Asset Maintenance</h2>
            <Dialog open={maintenanceDialogOpen} onOpenChange={setMaintenanceDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Schedule Maintenance
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Schedule Maintenance</DialogTitle>
                  <DialogDescription>Create a maintenance schedule for an asset</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateMaintenance}>
                  <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="maint_asset_id">Asset *</Label>
                      <Select name="asset_id" defaultValue={selectedAsset?.id}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select asset" />
                        </SelectTrigger>
                        <SelectContent>
                          {assets?.items.filter(a => a.status === 'ACTIVE').map((asset) => (
                            <SelectItem key={asset.id} value={asset.id}>
                              {asset.asset_code} - {asset.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="maintenance_type">Maintenance Type *</Label>
                      <Select name="maintenance_type" required>
                        <SelectTrigger>
                          <SelectValue placeholder="Select type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="PREVENTIVE">Preventive</SelectItem>
                          <SelectItem value="CORRECTIVE">Corrective</SelectItem>
                          <SelectItem value="INSPECTION">Inspection</SelectItem>
                          <SelectItem value="CALIBRATION">Calibration</SelectItem>
                          <SelectItem value="UPGRADE">Upgrade</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="maint_description">Description *</Label>
                      <Textarea id="maint_description" name="description" rows={3} required />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="scheduled_date">Scheduled Date *</Label>
                        <Input id="scheduled_date" name="scheduled_date" type="date" required />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="estimated_cost">Estimated Cost</Label>
                        <Input id="estimated_cost" name="estimated_cost" type="number" step="0.01" />
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => { setMaintenanceDialogOpen(false); setSelectedAsset(null); }}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={createMaintenanceMutation.isPending}>
                      {createMaintenanceMutation.isPending ? 'Creating...' : 'Schedule'}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Maintenance #</TableHead>
                    <TableHead>Asset</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Scheduled</TableHead>
                    <TableHead className="text-right">Est. Cost</TableHead>
                    <TableHead className="text-right">Actual Cost</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {maintenanceLoading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        <RefreshCw className="h-6 w-6 animate-spin mx-auto" />
                      </TableCell>
                    </TableRow>
                  ) : maintenance?.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                        No maintenance records found
                      </TableCell>
                    </TableRow>
                  ) : (
                    maintenance?.items.map((maint) => (
                      <TableRow key={maint.id}>
                        <TableCell className="font-mono">{maint.maintenance_number}</TableCell>
                        <TableCell>
                          <div className="font-medium">{maint.asset_name}</div>
                          <div className="text-xs text-muted-foreground">{maint.asset_code}</div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{maint.maintenance_type}</Badge>
                        </TableCell>
                        <TableCell>{format(new Date(maint.scheduled_date), 'dd MMM yyyy')}</TableCell>
                        <TableCell className="text-right">{formatCurrency(maint.estimated_cost)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(maint.actual_cost)}</TableCell>
                        <TableCell>{getMaintenanceStatusBadge(maint.status)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Dispose Asset Dialog */}
      <Dialog open={disposeDialogOpen} onOpenChange={(open) => { setDisposeDialogOpen(open); if (!open) setSelectedAsset(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Dispose Asset</DialogTitle>
            <DialogDescription>
              {selectedAsset && `Disposing: ${selectedAsset.asset_code} - ${selectedAsset.name}`}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleDisposeAsset}>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="disposal_date">Disposal Date *</Label>
                <Input id="disposal_date" name="disposal_date" type="date" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="disposal_price">Sale/Disposal Price</Label>
                <Input id="disposal_price" name="disposal_price" type="number" step="0.01" defaultValue="0" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="disposal_reason">Reason for Disposal *</Label>
                <Textarea id="disposal_reason" name="disposal_reason" rows={3} required />
              </div>
              {selectedAsset && (
                <div className="rounded-lg bg-muted p-3 text-sm">
                  <div className="flex justify-between">
                    <span>Current Book Value:</span>
                    <span className="font-medium">{formatCurrency(selectedAsset.current_book_value)}</span>
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setDisposeDialogOpen(false); setSelectedAsset(null); }}>
                Cancel
              </Button>
              <Button type="submit" variant="destructive" disabled={disposeAssetMutation.isPending}>
                {disposeAssetMutation.isPending ? 'Processing...' : 'Dispose Asset'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
