'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Users, Shield, Key, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/common';
import { usersApi, rolesApi } from '@/lib/api';

export default function AccessControlPage() {
  const { data: usersData } = useQuery({
    queryKey: ['users-count'],
    queryFn: () => usersApi.list({ page: 1, size: 1, is_active: true }),
  });

  const { data: rolesData } = useQuery({
    queryKey: ['roles-count'],
    queryFn: () => rolesApi.list({ page: 1, size: 1 }),
  });

  const modules = [
    {
      title: 'Users',
      description: 'Manage user accounts, assign roles, and control access',
      icon: Users,
      href: '/access-control/users',
      count: usersData?.total ?? 0,
      countLabel: 'total users',
      color: 'text-blue-600 bg-blue-100 dark:bg-blue-900 dark:text-blue-300',
    },
    {
      title: 'Roles',
      description: 'Define roles and their associated permissions',
      icon: Shield,
      href: '/access-control/roles',
      count: rolesData?.total ?? 0,
      countLabel: 'defined roles',
      color: 'text-purple-600 bg-purple-100 dark:bg-purple-900 dark:text-purple-300',
    },
    {
      title: 'Permissions',
      description: 'View and manage system permissions matrix',
      icon: Key,
      href: '/access-control/permissions',
      count: null,
      countLabel: 'system permissions',
      color: 'text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-300',
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Access Control"
        description="Manage users, roles, and permissions for your organization"
      />

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {modules.map((module) => (
          <Card key={module.title} className="hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div className={`p-2 rounded-lg ${module.color}`}>
                <module.icon className="h-5 w-5" />
              </div>
              {module.count !== null && (
                <div className="text-right">
                  <div className="text-2xl font-bold">{module.count}</div>
                  <div className="text-xs text-muted-foreground">{module.countLabel}</div>
                </div>
              )}
            </CardHeader>
            <CardContent>
              <CardTitle className="text-lg mb-2">{module.title}</CardTitle>
              <CardDescription className="mb-4">{module.description}</CardDescription>
              <Button asChild variant="outline" className="w-full">
                <Link href={module.href}>
                  Manage {module.title}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common access control tasks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link href="/dashboard/access-control/users/new">
                <Users className="mr-2 h-4 w-4" />
                Add New User
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/dashboard/access-control/roles/new">
                <Shield className="mr-2 h-4 w-4" />
                Create Role
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
