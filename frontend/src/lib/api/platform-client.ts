import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosError } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Platform admin API client — never sends X-Tenant-ID header
export const platformApiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

// Token management — uses platform_* keys to avoid conflicts with tenant auth
const getPlatformAccessToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('platform_access_token');
};

const getPlatformRefreshToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('platform_refresh_token');
};

export const setPlatformTokens = (accessToken: string, refreshToken: string): void => {
  localStorage.setItem('platform_access_token', accessToken);
  localStorage.setItem('platform_refresh_token', refreshToken);
};

export const clearPlatformTokens = (): void => {
  localStorage.removeItem('platform_access_token');
  localStorage.removeItem('platform_refresh_token');
  localStorage.removeItem('platform_tenant_id');
};

// Request interceptor — add auth token (no tenant header)
platformApiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getPlatformAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — handle 401
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

platformApiClient.interceptors.response.use(
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
            return platformApiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = getPlatformRefreshToken();
      if (refreshToken) {
        try {
          // Refresh needs tenant header
          const tenantId = localStorage.getItem('platform_tenant_id');
          const response = await axios.post(
            `${API_BASE_URL}/api/v1/auth/refresh`,
            { refresh_token: refreshToken },
            { headers: tenantId ? { 'X-Tenant-ID': tenantId } : {} }
          );

          const { access_token, refresh_token } = response.data;
          setPlatformTokens(access_token, refresh_token);
          processQueue(null, access_token);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;

          return platformApiClient(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          clearPlatformTokens();
          if (typeof window !== 'undefined') {
            window.location.href = '/platform/login';
          }
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      } else {
        clearPlatformTokens();
        if (typeof window !== 'undefined') {
          window.location.href = '/platform/login';
        }
      }
    }

    return Promise.reject(error);
  }
);

export { getPlatformAccessToken };
export default platformApiClient;
