/**
 * Orders API
 */

import apiClient, {PaginatedResponse} from './client';

export interface OrderItem {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  status: string;
}

export interface Order {
  id: string;
  order_number: string;
  status: string;
  customer_name: string;
  customer_phone: string;
  customer_email?: string;
  shipping_address: {
    address_line1: string;
    address_line2?: string;
    city: string;
    state: string;
    pincode: string;
  };
  items: OrderItem[];
  subtotal: number;
  discount: number;
  shipping_charges: number;
  tax_amount: number;
  grand_total: number;
  payment_status: string;
  payment_mode: string;
  channel_code: string;
  created_at: string;
  updated_at: string;
}

export interface OrderListParams {
  page?: number;
  size?: number;
  status?: string;
  search?: string;
  from_date?: string;
  to_date?: string;
}

export const ordersApi = {
  /**
   * Get paginated list of orders
   */
  async getOrders(params: OrderListParams = {}): Promise<PaginatedResponse<Order>> {
    const response = await apiClient.get<PaginatedResponse<Order>>('/orders', {
      params,
    });
    return response.data;
  },

  /**
   * Get order by ID
   */
  async getOrder(orderId: string): Promise<Order> {
    const response = await apiClient.get<Order>(`/orders/${orderId}`);
    return response.data;
  },

  /**
   * Get order by order number
   */
  async getOrderByNumber(orderNumber: string): Promise<Order> {
    const response = await apiClient.get<Order>(
      `/orders/by-number/${orderNumber}`,
    );
    return response.data;
  },

  /**
   * Update order status
   */
  async updateStatus(
    orderId: string,
    status: string,
    remarks?: string,
  ): Promise<Order> {
    const response = await apiClient.patch<Order>(`/orders/${orderId}/status`, {
      status,
      remarks,
    });
    return response.data;
  },

  /**
   * Get order statistics
   */
  async getStats(): Promise<{
    total_orders: number;
    pending_orders: number;
    processing_orders: number;
    shipped_orders: number;
    delivered_orders: number;
    cancelled_orders: number;
  }> {
    const response = await apiClient.get('/orders/stats');
    return response.data;
  },
};
