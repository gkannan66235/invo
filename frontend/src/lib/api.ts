import axios from 'axios';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: any) => {
    const token = Cookies.get('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: any) => Promise.reject(error)
);

// Response interceptor: unwrap success envelope and handle auth errors
api.interceptors.response.use(
  (response: any) => {
    const data = response.data;
    if (data && typeof data === 'object' && data.status === 'success' && 'data' in data) {
      response.data = data.data; // unwrap
    }
    return response;
  },
  (error: any) => {
    if (error.response?.status === 401) {
      Cookies.remove('access_token');
      Cookies.remove('refresh_token');
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Types
export interface User {
  id: string; // backend returns UUID string
  username: string;
  email?: string;
  full_name?: string;
  is_active?: boolean;
  role?: string;
  created_at?: string;
  gst_preference?: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in?: number;
  user: User;
}

// Customers
export interface Customer {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  gst_number?: string;
  customer_type?: string;
  duplicate_warning?: boolean; // present on create when duplicate detected
  created_at?: string;
}

export interface CreateCustomerRequest {
  name: string;
  email?: string;
  phone?: string;
  gst_number?: string;
  customer_type?: string;
  address?: Record<string, any>;
}

// Settings
export interface SettingsResponse {
  gst_default_rate: number;
  branding?: Record<string, any> | null;
  updated_at?: string;
}

export interface UpdateSettingsRequest {
  gst_default_rate?: number;
  branding?: Record<string, any> | null;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  customer_name: string;
  customer_phone: string;
  customer_email?: string;
  service_type: string;
  service_description: string;
  amount: number;
  gst_rate: number;
  gst_amount: number;
  total_amount: number;
  status: 'draft' | 'sent' | 'paid' | 'cancelled';
  created_at: string;
  updated_at: string;
  due_date?: string;
}

export interface CreateInvoiceRequest {
  customer_name: string;
  customer_phone: string;
  customer_email?: string;
  service_type: string;
  service_description: string;
  amount: number;
  gst_rate: number;
  due_date?: string;
}

// Auth API
export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await api.post('/api/v1/auth/login', data);
    return response.data;
  },

  getProfile: async (): Promise<User> => {
    // Correct endpoint is /me in backend
    const response = await api.get('/api/v1/auth/me');
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post('/api/v1/auth/logout');
  },
};

// Invoice API
export const invoiceApi = {
  getAll: async (): Promise<Invoice[]> => {
    const response = await api.get('/api/v1/invoices');
    return response.data;
  },

  getById: async (id: number): Promise<Invoice> => {
    const response = await api.get(`/api/v1/invoices/${id}`);
    return response.data;
  },

  create: async (data: CreateInvoiceRequest): Promise<Invoice> => {
    const response = await api.post('/api/v1/invoices', data);
    return response.data;
  },

  update: async (id: number, data: Partial<CreateInvoiceRequest>): Promise<Invoice> => {
    const response = await api.put(`/api/v1/invoices/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/v1/invoices/${id}`);
  },

  updateStatus: async (id: number, status: Invoice['status']): Promise<Invoice> => {
    const response = await api.patch(`/api/v1/invoices/${id}/status`, { status });
    return response.data;
  },

  downloadPdf: async (id: string | number): Promise<Blob> => {
    const response = await api.get(`/api/v1/invoices/${id}/pdf`, { responseType: 'blob' });
    return response.data;
  },
};

// Customers API
export const customersApi = {
  list: async (): Promise<{ customers: Customer[]; pagination: any }> => {
    const response = await api.get('/api/v1/customers');
    return response.data;
  },
  create: async (data: CreateCustomerRequest): Promise<Customer & { duplicate_warning?: boolean }> => {
    const response = await api.post('/api/v1/customers', data);
    return response.data.customer || response.data; // raw mode support
  },
  get: async (id: string): Promise<Customer> => {
    const response = await api.get(`/api/v1/customers/${id}`);
    return response.data.customer || response.data;
  },
  update: async (id: string, data: Partial<CreateCustomerRequest>): Promise<Customer> => {
    const response = await api.patch(`/api/v1/customers/${id}`, data);
    return response.data.customer || response.data;
  },
};

// Inventory API (basic subset; backend may return additional fields)
export interface InventoryItem {
  id: string;
  product_code: string;
  description: string;
  gst_rate?: number;
  selling_price?: number;
  current_stock?: number;
  is_active?: boolean;
  created_at?: string;
}

export const inventoryApi = {
  list: async (): Promise<{ items: InventoryItem[] }> => {
    const response = await api.get('/api/v1/inventory');
    return response.data;
  },
  create: async (data: Partial<InventoryItem>): Promise<InventoryItem> => {
    const response = await api.post('/api/v1/inventory', data);
    return response.data.item || response.data;
  },
  update: async (id: string, data: Partial<InventoryItem>): Promise<InventoryItem> => {
    const response = await api.patch(`/api/v1/inventory/${id}`, data);
    return response.data.item || response.data;
  },
  deactivate: async (id: string): Promise<void> => {
    await api.post(`/api/v1/inventory/${id}/deactivate`, {});
  }
};

// Settings API
export const settingsApi = {
  get: async (): Promise<SettingsResponse> => {
    const response = await api.get('/api/v1/settings');
    return response.data.settings || response.data;
  },
  update: async (data: UpdateSettingsRequest): Promise<SettingsResponse> => {
    const response = await api.patch('/api/v1/settings', data);
    return response.data.settings || response.data;
  }
};

// Health check
export const healthApi = {
  check: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};