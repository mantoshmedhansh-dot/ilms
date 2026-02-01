'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Loader2, Save, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
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
import { normalizeRoleLevel } from '@/lib/utils';

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

export default function EditRolePage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const roleId = params.id as string;

  const [formData, setFormData] = useState<RoleForm>({
    name: '',
    code: '',
    description: '',
    level: 'EXECUTIVE',
    permission_ids: [],
  });

  const { data: role, isLoading: roleLoading, isError, error } = useQuery({
    queryKey: ['role', roleId],
    queryFn: () => rolesApi.getById(roleId),
    enabled: !!roleId,
    retry: 1,
  });

  const { data: permissionsData } = useQuery({
    queryKey: ['permissions-by-module'],
    queryFn: permissionsApi.getByModule,
  });

  useEffect(() => {
    if (role) {
      setFormData({
        name: role.name || '',
        code: role.code || '',
        description: role.description || '',
        level: normalizeRoleLevel(role.level) as RoleLevel,
        permission_ids: role.permissions?.map((p: { id: string }) => p.id) || [],
      });
    }
  }, [role]);

  const updateMutation = useMutation({
    mutationFn: async (data: RoleForm) => {
      // Update role details
      await rolesApi.update(roleId, {
        name: data.name,
        description: data.description,
        level: data.level,
      });
      // Update permissions separately
      await rolesApi.assignPermissions(roleId, data.permission_ids);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      queryClient.invalidateQueries({ queryKey: ['role', roleId] });
      toast.success('Role updated successfully');
      router.push('/dashboard/access-control/roles');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update role');
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

    updateMutation.mutate(formData);
  };

  if (roleLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-64" />
          <Skeleton className="h-96 lg:col-span-2" />
        </div>
      </div>
    );
  }

  // Handle error state
  if (isError) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to load role';
    return (
      <div className="space-y-6">
        <PageHeader
          title="Edit Role"
          description="Error loading role"
          actions={
            <Button variant="outline" asChild>
              <Link href="/dashboard/access-control/roles">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Roles
              </Link>
            </Button>
          }
        />
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {errorMessage}. Please try again or contact support if the issue persists.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Handle not found state
  if (!role) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Edit Role"
          description="Role not found"
          actions={
            <Button variant="outline" asChild>
              <Link href="/dashboard/access-control/roles">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Roles
              </Link>
            </Button>
          }
        />
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Not Found</AlertTitle>
          <AlertDescription>
            The role you are looking for does not exist or you do not have permission to view it.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Edit Role: ${role?.name || ''}`}
        description="Modify role details and permissions"
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
                <Label htmlFor="code">Role Code</Label>
                <Input
                  id="code"
                  value={formData.code}
                  disabled
                  className="bg-muted"
                />
                <p className="text-xs text-muted-foreground">Code cannot be changed</p>
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
              <CardDescription>
                {formData.permission_ids.length} permissions selected
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6 max-h-[600px] overflow-y-auto">
                {permissionsData && Object.entries(permissionsData).map(([module, permissions]) => {
                  const modulePerms = permissions as { id: string; name: string; code: string }[];
                  const allSelected = modulePerms.every((p) => formData.permission_ids.includes(p.id));

                  return (
                    <div key={module} className="space-y-2">
                      <div className="flex items-center justify-between sticky top-0 bg-background py-1">
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
          <Button type="submit" disabled={updateMutation.isPending}>
            {updateMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save Changes
          </Button>
        </div>
      </form>
    </div>
  );
}
