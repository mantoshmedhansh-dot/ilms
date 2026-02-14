import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// --- Multi-tenant session support ---
// Each browser tab tracks its "active subdomain" in sessionStorage (per-tab).
// Tokens and tenant context are stored in localStorage with subdomain-scoped keys
// (e.g., access_token:mantosh, tenant_id:aquapurite) so multiple tenant sessions
// can coexist. Generic (unscoped) keys are also maintained for backward compatibility.

const getActiveSubdomain = (): string | null => {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem('active_subdomain') || null;
};

const setActiveSubdomain = (subdomain: string): void => {
  if (typeof window !== 'undefined') {
    sessionStorage.setItem('active_subdomain', subdomain);
  }
};

// Get tenant ID — scoped by active subdomain, fallback to generic
const getTenantId = (): string => {
  if (typeof window !== 'undefined') {
    const subdomain = getActiveSubdomain();
    if (subdomain) {
      const scoped = localStorage.getItem(`tenant_id:${subdomain}`);
      if (scoped) return scoped;
    }
    return localStorage.getItem('tenant_id') || '';
  }
  return '';
};

// Create axios instance - increased timeout for Render.com cold starts
export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 seconds to handle Render.com cold starts
});

// Add tenant ID header dynamically on each request
apiClient.interceptors.request.use(
  (config) => {
    const tenantId = getTenantId();
    if (tenantId) {
      config.headers['X-Tenant-ID'] = tenantId;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Log API base URL for debugging
if (typeof window !== 'undefined') {
  console.log('API Base URL:', API_BASE_URL);
}

// Token management — scoped by active subdomain
const getAccessToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  const subdomain = getActiveSubdomain();
  if (subdomain) {
    const scoped = localStorage.getItem(`access_token:${subdomain}`);
    if (scoped) return scoped;
  }
  return localStorage.getItem('access_token');
};

const getRefreshToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  const subdomain = getActiveSubdomain();
  if (subdomain) {
    const scoped = localStorage.getItem(`refresh_token:${subdomain}`);
    if (scoped) return scoped;
  }
  return localStorage.getItem('refresh_token');
};

const setTokens = (accessToken: string, refreshToken: string): void => {
  const subdomain = getActiveSubdomain();
  if (subdomain) {
    localStorage.setItem(`access_token:${subdomain}`, accessToken);
    localStorage.setItem(`refresh_token:${subdomain}`, refreshToken);
  }
  // Also write generic keys for backward compatibility
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
};

const clearTokens = (): void => {
  const subdomain = getActiveSubdomain();
  if (subdomain) {
    localStorage.removeItem(`access_token:${subdomain}`);
    localStorage.removeItem(`refresh_token:${subdomain}`);
  }
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

// Store tenant context — scoped + generic
const setTenantContext = (tenantId: string, subdomain: string): void => {
  if (typeof window === 'undefined') return;
  const active = getActiveSubdomain() || subdomain;
  if (active) {
    localStorage.setItem(`tenant_id:${active}`, tenantId);
    localStorage.setItem(`tenant_subdomain:${active}`, subdomain);
  }
  localStorage.setItem('tenant_id', tenantId);
  localStorage.setItem('tenant_subdomain', subdomain);
};

// Get the subdomain for redirect purposes (prefers sessionStorage, falls back to generic)
const getRedirectSubdomain = (): string | null => {
  if (typeof window === 'undefined') return null;
  return getActiveSubdomain() || localStorage.getItem('tenant_subdomain');
};

// Request interceptor - add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle 401, refresh token
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = getRefreshToken();
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token, tenant_id, tenant_subdomain } = response.data;
          setTokens(access_token, refresh_token);

          // Update tenant context from refresh response
          if (tenant_id && tenant_subdomain) {
            setTenantContext(tenant_id, tenant_subdomain);
          }

          processQueue(null, access_token);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;

          return apiClient(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          clearTokens();

          // Redirect to tenant-specific login if tenant is known
          if (typeof window !== 'undefined') {
            const subdomain = getRedirectSubdomain();
            if (subdomain) {
              window.location.href = `/t/${subdomain}/login`;
            } else {
              window.location.href = '/login';
            }
          }

          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      } else {
        clearTokens();
        if (typeof window !== 'undefined') {
          const subdomain = getRedirectSubdomain();
          if (subdomain) {
            window.location.href = `/t/${subdomain}/login`;
          } else {
            window.location.href = '/login';
          }
        }
      }
    }

    return Promise.reject(error);
  }
);

export {
  setTokens,
  clearTokens,
  getAccessToken,
  getActiveSubdomain,
  setActiveSubdomain,
  getTenantId,
  setTenantContext,
  getRedirectSubdomain,
};
export default apiClient;
