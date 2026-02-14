import { useEffect, useState } from 'react';
import { getAccessToken, getTenantId } from '@/lib/api/client';

export interface Module {
  code: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  isEnabled: boolean;
  sections: number[];
  routes: string[];
}

export function useModules() {
  const [modules, setModules] = useState<Module[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchModules() {
      try {
        const response = await fetch('/api/v1/modules/subscriptions', {
          headers: {
            'Authorization': `Bearer ${getAccessToken() || ''}`,
            'X-Tenant-ID': getTenantId(),
          }
        });

        if (!response.ok) {
          throw new Error('Failed to load modules');
        }

        const data = await response.json();

        // Transform subscriptions to module format
        const moduleList: Module[] = data.subscriptions.map((sub: any) => ({
          code: sub.module_code,
          name: sub.module_name,
          description: '',
          icon: '',
          color: '',
          isEnabled: sub.status === 'active',
          sections: [],
          routes: []
        }));

        setModules(moduleList);
      } catch (err) {
        setError('Failed to load modules');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchModules();
  }, []);

  const isModuleEnabled = (moduleCode: string): boolean => {
    const module = modules.find(m => m.code === moduleCode);
    return module?.isEnabled || false;
  };

  const isSectionEnabled = (sectionNumber: number): boolean => {
    return modules.some(m => m.isEnabled && m.sections.includes(sectionNumber));
  };

  return {
    modules,
    loading,
    error,
    isModuleEnabled,
    isSectionEnabled
  };
}
