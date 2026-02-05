'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import { GraduationCap, Plus, Video, FileText, CheckCircle, Clock, Award, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/data-table/data-table';
import { PageHeader, StatusBadge } from '@/components/common';
import apiClient from '@/lib/api/client';

interface TrainingModule {
  id: string;
  module_code: string;
  title: string;
  description?: string;
  training_type: 'VIDEO' | 'DOCUMENT' | 'QUIZ' | 'WEBINAR';
  duration_minutes: number;
  is_mandatory: boolean;
  passing_score?: number;
  enrolled_count: number;
  completed_count: number;
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
  created_at: string;
}

interface TrainingStats {
  total_modules: number;
  total_enrollments: number;
  completion_rate: number;
  active_learners: number;
}

const trainingApi = {
  list: async (params?: { page?: number; size?: number }) => {
    try {
      const { data } = await apiClient.get('/partners/training', { params });
      return data;
    } catch {
      return { items: [], total: 0, pages: 0 };
    }
  },
  getStats: async (): Promise<TrainingStats> => {
    try {
      const { data } = await apiClient.get('/partners/training/stats');
      return data;
    } catch {
      return { total_modules: 0, total_enrollments: 0, completion_rate: 0, active_learners: 0 };
    }
  },
};

const typeColors: Record<string, string> = {
  VIDEO: 'bg-purple-100 text-purple-800',
  DOCUMENT: 'bg-blue-100 text-blue-800',
  QUIZ: 'bg-green-100 text-green-800',
  WEBINAR: 'bg-orange-100 text-orange-800',
};

const typeIcons: Record<string, React.ReactNode> = {
  VIDEO: <Video className="h-4 w-4" />,
  DOCUMENT: <FileText className="h-4 w-4" />,
  QUIZ: <CheckCircle className="h-4 w-4" />,
  WEBINAR: <Users className="h-4 w-4" />,
};

const columns: ColumnDef<TrainingModule>[] = [
  {
    accessorKey: 'title',
    header: 'Module',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <GraduationCap className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="font-medium">{row.original.title}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.original.module_code}</div>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'training_type',
    header: 'Type',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${typeColors[row.original.training_type]}`}>
          {typeIcons[row.original.training_type]}
          {row.original.training_type}
        </span>
      </div>
    ),
  },
  {
    accessorKey: 'duration_minutes',
    header: 'Duration',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span>{row.original.duration_minutes} min</span>
      </div>
    ),
  },
  {
    accessorKey: 'is_mandatory',
    header: 'Mandatory',
    cell: ({ row }) => (
      <span className={`text-xs px-2 py-1 rounded ${row.original.is_mandatory ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}`}>
        {row.original.is_mandatory ? 'Required' : 'Optional'}
      </span>
    ),
  },
  {
    accessorKey: 'completion',
    header: 'Completion',
    cell: ({ row }) => {
      const rate = row.original.enrolled_count > 0
        ? (row.original.completed_count / row.original.enrolled_count) * 100
        : 0;
      return (
        <div className="space-y-1">
          <div className="text-sm">{row.original.completed_count} / {row.original.enrolled_count}</div>
          <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-green-500" style={{ width: `${rate}%` }} />
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
];

export default function PartnerTrainingPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['partner-training', page, pageSize],
    queryFn: () => trainingApi.list({ page: page + 1, size: pageSize }),
  });

  const { data: stats } = useQuery({
    queryKey: ['partner-training-stats'],
    queryFn: trainingApi.getStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Partner Training"
        description="Manage training modules and certifications for community partners"
        actions={
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create Module
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Modules</CardTitle>
            <GraduationCap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_modules || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Enrollments</CardTitle>
            <Users className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.total_enrollments || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completion Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.completion_rate || 0}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Learners</CardTitle>
            <Award className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats?.active_learners || 0}</div>
          </CardContent>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        searchKey="title"
        searchPlaceholder="Search modules..."
        isLoading={isLoading}
        manualPagination
        pageCount={data?.pages ?? 0}
        pageIndex={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />
    </div>
  );
}
