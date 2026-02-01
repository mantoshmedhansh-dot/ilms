/**
 * Service Requests API
 */

import apiClient, {PaginatedResponse} from './client';

export interface ServiceRequest {
  id: string;
  ticket_number: string;
  type: string;
  status: string;
  priority: string;
  customer_name: string;
  customer_phone: string;
  customer_email?: string;
  product_name: string;
  product_serial?: string;
  issue_description: string;
  resolution?: string;
  assigned_to?: string;
  technician_name?: string;
  scheduled_date?: string;
  completed_at?: string;
  service_address: {
    address_line1: string;
    address_line2?: string;
    city: string;
    state: string;
    pincode: string;
  };
  created_at: string;
  updated_at: string;
}

export interface ServiceRequestCreate {
  type: string;
  customer_id?: string;
  customer_name: string;
  customer_phone: string;
  customer_email?: string;
  product_id?: string;
  product_serial?: string;
  issue_description: string;
  priority?: string;
  service_address: {
    address_line1: string;
    address_line2?: string;
    city: string;
    state: string;
    pincode: string;
  };
}

export interface ServiceRequestParams {
  page?: number;
  size?: number;
  status?: string;
  type?: string;
  priority?: string;
  search?: string;
  assigned_to?: string;
}

export const serviceRequestsApi = {
  /**
   * Get service requests
   */
  async getRequests(
    params: ServiceRequestParams = {},
  ): Promise<PaginatedResponse<ServiceRequest>> {
    const response = await apiClient.get<PaginatedResponse<ServiceRequest>>(
      '/service-requests',
      {params},
    );
    return response.data;
  },

  /**
   * Get service request by ID
   */
  async getRequest(id: string): Promise<ServiceRequest> {
    const response = await apiClient.get<ServiceRequest>(
      `/service-requests/${id}`,
    );
    return response.data;
  },

  /**
   * Create service request
   */
  async createRequest(data: ServiceRequestCreate): Promise<ServiceRequest> {
    const response = await apiClient.post<ServiceRequest>(
      '/service-requests',
      data,
    );
    return response.data;
  },

  /**
   * Update service request status
   */
  async updateStatus(
    id: string,
    status: string,
    resolution?: string,
  ): Promise<ServiceRequest> {
    const response = await apiClient.patch<ServiceRequest>(
      `/service-requests/${id}/status`,
      {status, resolution},
    );
    return response.data;
  },

  /**
   * Assign technician
   */
  async assignTechnician(
    id: string,
    technicianId: string,
    scheduledDate?: string,
  ): Promise<ServiceRequest> {
    const response = await apiClient.patch<ServiceRequest>(
      `/service-requests/${id}/assign`,
      {technician_id: technicianId, scheduled_date: scheduledDate},
    );
    return response.data;
  },

  /**
   * Get service request statistics
   */
  async getStats(): Promise<{
    total: number;
    open: number;
    in_progress: number;
    resolved: number;
    closed: number;
    pending_assignment: number;
  }> {
    const response = await apiClient.get('/service-requests/stats');
    return response.data;
  },
};
