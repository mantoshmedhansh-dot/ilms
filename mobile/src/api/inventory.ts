/**
 * Inventory API
 */

import apiClient, {PaginatedResponse} from './client';

export interface StockItem {
  id: string;
  sku: string;
  product_name: string;
  barcode?: string;
  warehouse_id: string;
  warehouse_name: string;
  quantity: number;
  reserved_quantity: number;
  available_quantity: number;
  min_stock_level: number;
  max_stock_level: number;
  reorder_point: number;
  last_movement_at?: string;
}

export interface StockMovement {
  id: string;
  sku: string;
  product_name: string;
  movement_type: string;
  quantity: number;
  from_warehouse?: string;
  to_warehouse?: string;
  reference_type: string;
  reference_number: string;
  created_at: string;
  created_by: string;
}

export interface InventoryParams {
  page?: number;
  size?: number;
  warehouse_id?: string;
  search?: string;
  low_stock?: boolean;
}

export const inventoryApi = {
  /**
   * Get stock items
   */
  async getStock(params: InventoryParams = {}): Promise<PaginatedResponse<StockItem>> {
    const response = await apiClient.get<PaginatedResponse<StockItem>>(
      '/inventory/stock',
      {params},
    );
    return response.data;
  },

  /**
   * Get stock by SKU
   */
  async getStockBySku(sku: string): Promise<StockItem[]> {
    const response = await apiClient.get<StockItem[]>(
      `/inventory/stock/sku/${sku}`,
    );
    return response.data;
  },

  /**
   * Get stock by barcode
   */
  async getStockByBarcode(barcode: string): Promise<StockItem> {
    const response = await apiClient.get<StockItem>(
      `/inventory/stock/barcode/${barcode}`,
    );
    return response.data;
  },

  /**
   * Get stock movements
   */
  async getMovements(
    params: InventoryParams = {},
  ): Promise<PaginatedResponse<StockMovement>> {
    const response = await apiClient.get<PaginatedResponse<StockMovement>>(
      '/inventory/movements',
      {params},
    );
    return response.data;
  },

  /**
   * Get low stock items
   */
  async getLowStock(warehouseId?: string): Promise<StockItem[]> {
    const response = await apiClient.get<StockItem[]>('/inventory/low-stock', {
      params: {warehouse_id: warehouseId},
    });
    return response.data;
  },

  /**
   * Get inventory summary
   */
  async getSummary(): Promise<{
    total_skus: number;
    total_quantity: number;
    total_value: number;
    low_stock_count: number;
    out_of_stock_count: number;
  }> {
    const response = await apiClient.get('/inventory/summary');
    return response.data;
  },
};
