'use client';

import { Truck, Package, FileText, MapPin } from 'lucide-react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/common';

export default function LogisticsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Logistics"
        description="Manage shipments, manifests, and transporters"
        actions={
          <Button asChild>
            <Link href="/dashboard/logistics/shipments/new">
              <Package className="mr-2 h-4 w-4" />
              Create Shipment
            </Link>
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Link href="/dashboard/logistics/shipments">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Shipments</CardTitle>
              <Package className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Track all shipments</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/logistics/manifests">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Manifests</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Manage handover manifests</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/logistics/transporters">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Transporters</CardTitle>
              <Truck className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Manage logistics partners</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/logistics/serviceability">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Serviceability</CardTitle>
              <MapPin className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Pincode coverage</p>
            </CardContent>
          </Card>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Shipments</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32 border rounded-lg bg-muted/50">
            <p className="text-muted-foreground">Recent shipments will appear here...</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
