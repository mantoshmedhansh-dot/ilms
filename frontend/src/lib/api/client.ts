import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Get tenant ID from localStorage (set by tenant provider from URL path)
const getTenantId = (): string => {
  if (typeof window !== 'undefined') {
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

// Token management
const getAccessToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
};

const getRefreshToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('refresh_token');
};

const setTokens = (accessToken: string, refreshToken: string): void => {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
};

const clearTokens = (): void => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
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
          if (tenant_id) {
            localStorage.setItem('tenant_id', tenant_id);
          }
          if (tenant_subdomain) {
            localStorage.setItem('tenant_subdomain', tenant_subdomain);
          }

          processQueue(null, access_token);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;

          return apiClient(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          clearTokens();

          // Redirect to tenant-specific login if tenant is known
          if (typeof window !== 'undefined') {
            const subdomain = localStorage.getItem('tenant_subdomain');
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
          const subdomain = localStorage.getItem('tenant_subdomain');
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

export { setTokens, clearTokens, getAccessToken };
export default apiClient;
