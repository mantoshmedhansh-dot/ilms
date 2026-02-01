'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Key, Search, Filter } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { PageHeader } from '@/components/common';
import { permissionsApi } from '@/lib/api';
import { Permission, getPermissionModuleCode } from '@/types';
import { Skeleton } from '@/components/ui/skeleton';

const moduleColors: Record<string, string> = {
  users: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  roles: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
  products: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  orders: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  inventory: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  procurement: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  finance: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300',
  service: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-300',
  default: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
};

export default function PermissionsPage() {
  const [search, setSearch] = useState('');
  const [selectedModule, setSelectedModule] = useState<string>('all');

  const { data: permissions, isLoading } = useQuery({
    queryKey: ['permissions', selectedModule],
    queryFn: () => permissionsApi.list(selectedModule !== 'all' ? { module: selectedModule } : undefined),
  });

  const { data: modules } = useQuery({
    queryKey: ['permission-modules'],
    queryFn: permissionsApi.getModules,
  });

  // Group permissions by module
  const groupedPermissions = (permissions ?? []).reduce((acc, permission) => {
    const moduleCode = getPermissionModuleCode(permission);
    if (!acc[moduleCode]) {
      acc[moduleCode] = [];
    }
    acc[moduleCode].push(permission);
    return acc;
  }, {} as Record<string, Permission[]>);

  // Filter permissions by search
  const filteredGroups = Object.entries(groupedPermissions).reduce((acc, [module, perms]) => {
    const filtered = perms.filter(
      (p) =>
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.code.toLowerCase().includes(search.toLowerCase()) ||
        (p.description?.toLowerCase().includes(search.toLowerCase()) ?? false)
    );
    if (filtered.length > 0) {
      acc[module] = filtered;
    }
    return acc;
  }, {} as Record<string, Permission[]>);

  const totalPermissions = permissions?.length ?? 0;
  const moduleCount = Object.keys(groupedPermissions).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Permissions"
        description="View all system permissions organized by module"
      />

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Permissions</CardDescription>
            <CardTitle className="text-3xl">{totalPermissions}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Modules</CardDescription>
            <CardTitle className="text-3xl">{moduleCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Actions per Module (Avg)</CardDescription>
            <CardTitle className="text-3xl">
              {moduleCount > 0 ? Math.round(totalPermissions / moduleCount) : 0}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filter Permissions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4 md:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search permissions..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={selectedModule} onValueChange={setSelectedModule}>
              <SelectTrigger className="w-full md:w-[200px]">
                <Filter className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Filter by module" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Modules</SelectItem>
                {modules?.map((module: string) => (
                  <SelectItem key={module} value={module}>
                    {module.charAt(0).toUpperCase() + module.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Permissions by Module */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {[1, 2, 3, 4].map((j) => (
                    <Skeleton key={j} className="h-12 w-full" />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : Object.keys(filteredGroups).length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center">
            <Key className="mx-auto h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-semibold">No permissions found</h3>
            <p className="text-muted-foreground">
              {search ? 'Try adjusting your search terms' : 'No permissions have been defined yet'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {Object.entries(filteredGroups).map(([module, perms]) => (
            <Card key={module}>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <Badge
                    variant="secondary"
                    className={moduleColors[module.toLowerCase()] || moduleColors.default}
                  >
                    {module.toUpperCase()}
                  </Badge>
                  <CardTitle className="text-lg">
                    {module.charAt(0).toUpperCase() + module.slice(1)} Module
                  </CardTitle>
                  <span className="text-sm text-muted-foreground">
                    ({perms.length} permissions)
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Permission Name</TableHead>
                      <TableHead>Code</TableHead>
                      <TableHead>Description</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {perms.map((permission) => (
                      <TableRow key={permission.id}>
                        <TableCell className="font-medium">{permission.name}</TableCell>
                        <TableCell>
                          <code className="rounded bg-muted px-2 py-1 text-sm">
                            {permission.code}
                          </code>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {permission.description || '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
