'use client';

import { useEffect, useState } from 'react';
import apiClient from '@/lib/api/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
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
} from '@/components/ui/dialog';
import { Loader2, Plus, Edit, Trash2, Award } from 'lucide-react';

interface PartnerTier {
  id: string;
  code: string;
  name: string;
  level: number;
  min_monthly_sales: number;
  min_monthly_value: number;
  commission_percentage: number;
  bonus_percentage: number;
  is_active: boolean;
  created_at: string;
}

export default function PartnerTiersPage() {
  const [tiers, setTiers] = useState<PartnerTier[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingTier, setEditingTier] = useState<PartnerTier | null>(null);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    min_monthly_sales: 0,
    min_monthly_value: 0,
    commission_percentage: 10,
    bonus_percentage: 0,
    is_active: true,
  });

  useEffect(() => {
    fetchTiers();
  }, []);

  const fetchTiers = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/partners/tiers');
      setTiers(response.data || []);
    } catch (error) {
      console.error('Failed to fetch tiers:', error);
      setTiers([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingTier(null);
    setFormData({
      code: '',
      name: '',
      min_monthly_sales: 0,
      min_monthly_value: 0,
      commission_percentage: 10,
      bonus_percentage: 0,
      is_active: true,
    });
    setIsDialogOpen(true);
  };

  const handleEdit = (tier: PartnerTier) => {
    setEditingTier(tier);
    setFormData({
      code: tier.code,
      name: tier.name,
      min_monthly_sales: tier.min_monthly_sales,
      min_monthly_value: tier.min_monthly_value,
      commission_percentage: tier.commission_percentage,
      bonus_percentage: tier.bonus_percentage,
      is_active: tier.is_active,
    });
    setIsDialogOpen(true);
  };

  const handleSubmit = async () => {
    try {
      if (editingTier) {
        await apiClient.put(`/partners/tiers/${editingTier.id}`, formData);
      } else {
        await apiClient.post('/partners/tiers', formData);
      }
      setIsDialogOpen(false);
      fetchTiers();
    } catch (error) {
      console.error('Failed to save tier:', error);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const tierColors: Record<string, string> = {
    BRONZE: 'bg-amber-100 text-amber-800',
    SILVER: 'bg-gray-200 text-gray-800',
    GOLD: 'bg-yellow-100 text-yellow-800',
    PLATINUM: 'bg-slate-200 text-slate-800',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Partner Tiers</h1>
          <p className="text-muted-foreground">
            Configure commission tiers and qualification criteria
          </p>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="h-4 w-4 mr-2" />
          Add Tier
        </Button>
      </div>

      {/* Tiers Table */}
      <Card>
        <CardHeader>
          <CardTitle>Commission Tiers</CardTitle>
          <CardDescription>
            Partners progress through tiers based on performance
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : tiers.length === 0 ? (
            <div className="text-center py-12">
              <Award className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No tiers configured</p>
              <Button className="mt-4" onClick={handleCreate}>
                Create First Tier
              </Button>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tier</TableHead>
                    <TableHead>Min Monthly Sales</TableHead>
                    <TableHead>Min Monthly Value</TableHead>
                    <TableHead>Commission %</TableHead>
                    <TableHead>Bonus %</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tiers.map((tier) => (
                    <TableRow key={tier.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Badge className={tierColors[tier.code] || 'bg-gray-100'}>
                            {tier.code}
                          </Badge>
                          <span className="font-medium">{tier.name}</span>
                        </div>
                      </TableCell>
                      <TableCell>{tier.min_monthly_sales}</TableCell>
                      <TableCell>{formatCurrency(tier.min_monthly_value)}</TableCell>
                      <TableCell className="font-bold text-green-600">
                        {tier.commission_percentage}%
                      </TableCell>
                      <TableCell>{tier.bonus_percentage}%</TableCell>
                      <TableCell>
                        <Badge variant={tier.is_active ? 'default' : 'secondary'}>
                          {tier.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(tier)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingTier ? 'Edit Tier' : 'Create Tier'}</DialogTitle>
            <DialogDescription>
              {editingTier
                ? 'Update tier configuration'
                : 'Create a new commission tier'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="code">Tier Code</Label>
                <Input
                  id="code"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  placeholder="BRONZE"
                  disabled={!!editingTier}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">Tier Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Bronze Partner"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="min_monthly_sales">Min Monthly Sales</Label>
                <Input
                  id="min_monthly_sales"
                  type="number"
                  value={formData.min_monthly_sales}
                  onChange={(e) => setFormData({ ...formData, min_monthly_sales: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="min_monthly_value">Min Monthly Value (INR)</Label>
                <Input
                  id="min_monthly_value"
                  type="number"
                  value={formData.min_monthly_value}
                  onChange={(e) => setFormData({ ...formData, min_monthly_value: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="commission_percentage">Commission Rate (%)</Label>
                <Input
                  id="commission_percentage"
                  type="number"
                  step="0.5"
                  value={formData.commission_percentage}
                  onChange={(e) => setFormData({ ...formData, commission_percentage: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bonus_percentage">Bonus Rate (%)</Label>
                <Input
                  id="bonus_percentage"
                  type="number"
                  step="0.5"
                  value={formData.bonus_percentage}
                  onChange={(e) => setFormData({ ...formData, bonus_percentage: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>
              {editingTier ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
