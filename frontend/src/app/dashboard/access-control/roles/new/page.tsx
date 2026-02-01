'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, Loader2, Check } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader } from '@/components/common';
import { rolesApi, permissionsApi } from '@/lib/api';
import { RoleLevel } from '@/types';

interface RoleForm {
  name: string;
  code: string;
  description: string;
  level: RoleLevel;
  permission_ids: string[];
}

const roleLevels = [
  { value: 'SUPER_ADMIN', label: 'Super Admin' },
  { value: 'DIRECTOR', label: 'Director' },
  { value: 'HEAD', label: 'Head' },
  { value: 'MANAGER', label: 'Manager' },
  { value: 'EXECUTIVE', label: 'Executive' },
];

export default function NewRolePage() {
  const router = useRouter();
  const [formData, setFormData] = useState<RoleForm>({
    name: '',
    code: '',
    description: '',
    level: 'EXECUTIVE',
    permission_ids: [],
  });

  const { data: permissionsData } = useQuery({
    queryKey: ['permissions-by-module'],
    queryFn: permissionsApi.getByModule,
  });

  const createMutation = useMutation({
    mutationFn: rolesApi.create,
    onSuccess: () => {
      toast.success('Role created successfully');
      router.push('/dashboard/access-control/roles');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create role');
    },
  });

  const handlePermissionToggle = (permissionId: string) => {
    setFormData((prev) => ({
      ...prev,
      permission_ids: prev.permission_ids.includes(permissionId)
        ? prev.permission_ids.filter((id) => id !== permissionId)
        : [...prev.permission_ids, permissionId],
    }));
  };

  const handleModuleSelectAll = (modulePermissions: { id: string }[]) => {
    const modulePermissionIds = modulePermissions.map((p) => p.id);
    const allSelected = modulePermissionIds.every((id) => formData.permission_ids.includes(id));

    if (allSelected) {
      setFormData((prev) => ({
        ...prev,
        permission_ids: prev.permission_ids.filter((id) => !modulePermissionIds.includes(id)),
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        permission_ids: [...new Set([...prev.permission_ids, ...modulePermissionIds])],
      }));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      toast.error('Role name is required');
      return;
    }
    if (!formData.code.trim()) {
      toast.error('Role code is required');
      return;
    }

    createMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Create Role"
        description="Create a new role with permissions"
        actions={
          <Button variant="outline" asChild>
            <Link href="/dashboard/access-control/roles">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Roles
            </Link>
          </Button>
        }
      />

      <form onSubmit={handleSubmit}>
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Basic Information */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle>Role Details</CardTitle>
              <CardDescription>Basic role information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Role Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., Sales Manager"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="code">Role Code *</Label>
                <Input
                  id="code"
                  placeholder="e.g., SALES_MANAGER"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase().replace(/\s/g, '_') })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="level">Role Level</Label>
                <Select
                  value={formData.level}
                  onValueChange={(value) => setFormData({ ...formData, level: value as RoleLevel })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select level" />
                  </SelectTrigger>
                  <SelectContent>
                    {roleLevels.map((level) => (
                      <SelectItem key={level.value} value={level.value}>
                        {level.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Describe the role responsibilities..."
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>
            </CardContent>
          </Card>

          {/* Permissions */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Permissions</CardTitle>
              <CardDescription>Select permissions for this role</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {permissionsData && Object.entries(permissionsData).map(([module, permissions]) => {
                  const modulePerms = permissions as { id: string; name: string; code: string }[];
                  const allSelected = modulePerms.every((p) => formData.permission_ids.includes(p.id));
                  const someSelected = modulePerms.some((p) => formData.permission_ids.includes(p.id));

                  return (
                    <div key={module} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium capitalize">{module.replace(/_/g, ' ')}</h4>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleModuleSelectAll(modulePerms)}
                        >
                          {allSelected ? 'Deselect All' : 'Select All'}
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                        {modulePerms.map((permission) => (
                          <label
                            key={permission.id}
                            className="flex items-center gap-2 p-2 rounded border cursor-pointer hover:bg-muted/50"
                          >
                            <Checkbox
                              checked={formData.permission_ids.includes(permission.id)}
                              onCheckedChange={() => handlePermissionToggle(permission.id)}
                            />
                            <span className="text-sm">{permission.name}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  );
                })}
                {!permissionsData && (
                  <div className="text-center py-8 text-muted-foreground">
                    Loading permissions...
                  </div>
                )}
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
            Create Role
          </Button>
        </div>
      </form>
    </div>
  );
}
