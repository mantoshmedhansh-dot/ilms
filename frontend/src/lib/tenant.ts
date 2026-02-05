/**
 * Tenant Context Utilities
 *
 * Provides tenant detection from URL path and localStorage.
 * URL format: /t/{tenant_subdomain}/...
 */

// Get tenant subdomain from URL path
export function getTenantFromPath(pathname: string): string | null {
  // Match /t/{tenant}/... pattern
  const match = pathname.match(/^\/t\/([^/]+)/);
  return match ? match[1] : null;
}

// Get tenant ID from subdomain via API
export async function getTenantIdBySubdomain(
  subdomain: string,
  apiBaseUrl: string
): Promise<string | null> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/onboarding/tenant-lookup?subdomain=${subdomain}`);
    if (response.ok) {
      const data = await response.json();
      return data.tenant_id || null;
    }
    return null;
  } catch {
    return null;
  }
}

// Store tenant info in localStorage
export function setTenantContext(subdomain: string, tenantId: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('tenant_subdomain', subdomain);
    localStorage.setItem('tenant_id', tenantId);
  }
}

// Get stored tenant ID
export function getStoredTenantId(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('tenant_id');
  }
  return null;
}

// Get stored tenant subdomain
export function getStoredTenantSubdomain(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('tenant_subdomain');
  }
  return null;
}

// Clear tenant context
export function clearTenantContext(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('tenant_subdomain');
    localStorage.removeItem('tenant_id');
  }
}

// Build tenant URL
export function buildTenantUrl(subdomain: string, path: string = ''): string {
  return `/t/${subdomain}${path.startsWith('/') ? path : `/${path}`}`;
}

// Check if current path is a tenant path
export function isTenantPath(pathname: string): boolean {
  return pathname.startsWith('/t/');
}
