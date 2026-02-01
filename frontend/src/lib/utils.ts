import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a date string to a human-readable format
 */
export function formatDate(date: string | Date | undefined | null, options?: Intl.DateTimeFormatOptions): string {
  if (!date) return '-';

  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '-';

    return d.toLocaleDateString('en-IN', options ?? {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return '-';
  }
}

/**
 * Format a date with time
 */
export function formatDateTime(date: string | Date | undefined | null): string {
  if (!date) return '-';

  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '-';

    return d.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '-';
  }
}

/**
 * Format a number as Indian currency (INR)
 */
export function formatCurrency(amount: number | undefined | null): string {
  if (amount === undefined || amount === null) return '₹0';

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Format a number with Indian number system (lakhs, crores)
 */
export function formatNumber(num: number | undefined | null): string {
  if (num === undefined || num === null) return '0';

  return new Intl.NumberFormat('en-IN').format(num);
}

/**
 * Format a percentage
 */
export function formatPercent(value: number | undefined | null, decimals: number = 1): string {
  if (value === undefined || value === null) return '0%';

  return `${value.toFixed(decimals)}%`;
}

/**
 * Get relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: string | Date | undefined | null): string {
  if (!date) return '-';

  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '-';

    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hr ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    return formatDate(d);
  } catch {
    return '-';
  }
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string | undefined | null, length: number = 50): string {
  if (!text) return '';
  if (text.length <= length) return text;
  return text.slice(0, length) + '...';
}

/**
 * Generate initials from a name
 */
export function getInitials(name: string | undefined | null): string {
  if (!name) return '??';

  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/**
 * Capitalize first letter
 */
export function capitalize(str: string | undefined | null): string {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Convert snake_case or SCREAMING_SNAKE_CASE to Title Case
 */
export function toTitleCase(str: string | undefined | null): string {
  if (!str) return '';
  return str
    .toLowerCase()
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// ============================================
// ENUM NORMALIZATION UTILITIES
// ============================================
// These utilities handle case sensitivity issues between
// database (VARCHAR), backend (Pydantic), and frontend (TypeScript).
// All enum values should be UPPERCASE across all layers.

/**
 * Normalize an enum-like value to UPPERCASE and validate against allowed values.
 * Returns the default value if input is invalid or not in the allowed list.
 *
 * @param value - The value to normalize (may be lowercase, mixed case, or undefined)
 * @param validValues - Array of valid UPPERCASE values
 * @param defaultValue - Default value to return if input is invalid
 * @returns Normalized UPPERCASE value or default
 *
 * @example
 * normalizeEnumValue('head', ['SUPER_ADMIN', 'HEAD', 'MANAGER'], 'MANAGER') // Returns 'HEAD'
 * normalizeEnumValue('invalid', ['ACTIVE', 'INACTIVE'], 'ACTIVE') // Returns 'ACTIVE'
 */
export function normalizeEnumValue<T extends string>(
  value: string | undefined | null,
  validValues: readonly T[],
  defaultValue: T
): T {
  if (!value) return defaultValue;

  const upperValue = value.toUpperCase() as T;
  return validValues.includes(upperValue) ? upperValue : defaultValue;
}

/**
 * Create a normalizer function for a specific enum type.
 * Useful for reusable normalization across components.
 *
 * @example
 * const normalizeRoleLevel = createEnumNormalizer(
 *   ['SUPER_ADMIN', 'DIRECTOR', 'HEAD', 'MANAGER', 'EXECUTIVE'] as const,
 *   'EXECUTIVE'
 * );
 * normalizeRoleLevel('head') // Returns 'HEAD'
 */
export function createEnumNormalizer<T extends string>(
  validValues: readonly T[],
  defaultValue: T
): (value: string | undefined | null) => T {
  return (value) => normalizeEnumValue(value, validValues, defaultValue);
}

// Pre-built normalizers for common enum types
export const ROLE_LEVELS = ['SUPER_ADMIN', 'DIRECTOR', 'HEAD', 'MANAGER', 'EXECUTIVE'] as const;
export const normalizeRoleLevel = createEnumNormalizer(ROLE_LEVELS, 'EXECUTIVE');

export const ORDER_STATUSES = [
  'NEW', 'PENDING_PAYMENT', 'CONFIRMED', 'ALLOCATED', 'PICKLIST_CREATED',
  'PICKING', 'PACKED', 'READY_TO_SHIP', 'SHIPPED', 'IN_TRANSIT',
  'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED', 'RETURNED', 'REFUNDED'
] as const;
export const normalizeOrderStatus = createEnumNormalizer(ORDER_STATUSES, 'NEW');

export const PAYMENT_STATUSES = [
  'PENDING', 'AUTHORIZED', 'CAPTURED', 'PAID', 'PARTIALLY_PAID',
  'REFUNDED', 'PARTIALLY_REFUNDED', 'CANCELLED', 'FAILED'
] as const;
export const normalizePaymentStatus = createEnumNormalizer(PAYMENT_STATUSES, 'PENDING');

export const DEALER_STATUSES = [
  'PENDING_APPROVAL', 'ACTIVE', 'INACTIVE', 'SUSPENDED', 'BLACKLISTED', 'TERMINATED'
] as const;
export const normalizeDealerStatus = createEnumNormalizer(DEALER_STATUSES, 'PENDING_APPROVAL');

export const VENDOR_STATUSES = ['ACTIVE', 'INACTIVE', 'PENDING_APPROVAL', 'BLACKLISTED'] as const;
export const normalizeVendorStatus = createEnumNormalizer(VENDOR_STATUSES, 'ACTIVE');

export const COMPANY_TYPES = [
  'PRIVATE_LIMITED', 'PUBLIC_LIMITED', 'LLP', 'PARTNERSHIP',
  'PROPRIETORSHIP', 'OPC', 'TRUST', 'SOCIETY', 'HUF', 'GOVERNMENT'
] as const;
export const normalizeCompanyType = createEnumNormalizer(COMPANY_TYPES, 'PRIVATE_LIMITED');

export const GST_REGISTRATION_TYPES = [
  'REGULAR', 'COMPOSITION', 'CASUAL', 'SEZ_UNIT', 'SEZ_DEVELOPER',
  'ISD', 'TDS_DEDUCTOR', 'TCS_COLLECTOR', 'NON_RESIDENT', 'UNREGISTERED'
] as const;
export const normalizeGSTRegistrationType = createEnumNormalizer(GST_REGISTRATION_TYPES, 'REGULAR');

export const BANK_ACCOUNT_TYPES = ['CURRENT', 'SAVINGS', 'OD', 'CC'] as const;
export const normalizeBankAccountType = createEnumNormalizer(BANK_ACCOUNT_TYPES, 'CURRENT');
