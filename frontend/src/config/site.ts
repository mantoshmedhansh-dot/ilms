export const siteConfig = {
  name: "ILMS.AI - Enterprise Resource Planning",
  description: 'ILMS.AI Multi-Tenant ERP Management System',
  url: process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000',
  company: 'ILMS.AI',
  supportEmail: 'support@ilms.ai',
};

export const statusColors: Record<string, string> = {
  // Order statuses
  NEW: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  PENDING_PAYMENT: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  CONFIRMED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  ALLOCATED: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300',
  PICKING: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
  PACKED: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-300',
  SHIPPED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  IN_TRANSIT: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  DELIVERED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  CANCELLED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  REFUNDED: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',

  // General statuses
  ACTIVE: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  INACTIVE: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
  PENDING: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  APPROVED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  REJECTED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  DRAFT: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',

  // Service request statuses
  ASSIGNED: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300',
  SCHEDULED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  IN_PROGRESS: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
  COMPLETED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  CLOSED: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',

  // Priority
  LOW: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
  NORMAL: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  HIGH: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  URGENT: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  CRITICAL: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',

  // Payment status
  PAID: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  PARTIALLY_PAID: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  OVERDUE: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',

  // Stock status
  AVAILABLE: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  RESERVED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  DAMAGED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  QUARANTINE: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
};

export const tierColors: Record<string, string> = {
  PLATINUM: 'bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-200',
  GOLD: 'bg-yellow-200 text-yellow-800 dark:bg-yellow-700 dark:text-yellow-200',
  SILVER: 'bg-gray-200 text-gray-800 dark:bg-gray-600 dark:text-gray-200',
  BRONZE: 'bg-orange-200 text-orange-800 dark:bg-orange-700 dark:text-orange-200',
};
