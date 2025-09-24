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
  (config) => {
    const token = Cookies.get('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear tokens and redirect to login
      Cookies.remove('access_token');
      Cookies.remove('refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Types
export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  role: string;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
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
    const response = await api.get('/api/v1/auth/profile');
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
};

// Health check
export const healthApi = {
  check: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};