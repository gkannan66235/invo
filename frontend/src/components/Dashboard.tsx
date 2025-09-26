'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useQuery } from 'react-query';
import { invoiceApi, healthApi } from '@/lib/api';
import { 
  Building2, 
  FileText, 
  Users, 
  DollarSign, 
  LogOut,
  Plus,
  Search,
  Filter,
  Edit,
  Trash2,
  Printer,
  Download,
  Package,
  Settings as SettingsIcon
} from 'lucide-react';
import InvoiceForm from './InvoiceForm';
import { toast } from 'react-hot-toast';
import { format } from 'date-fns';
import Link from 'next/link';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [showInvoiceForm, setShowInvoiceForm] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Fetch data
  const { data: invoices = [], refetch: refetchInvoices } = useQuery(
    'invoices',
    invoiceApi.getAll,
    {
      onError: (error: any) => {
        toast.error('Failed to load invoices');
      }
    }
  );

  const { data: healthData } = useQuery('health', healthApi.check, {
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Filter invoices
  const filteredInvoices = invoices.filter((invoice: any) => {
    const matchesSearch = 
      invoice.invoice_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      invoice.customer_name.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || invoice.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  // Stats calculations
  const stats = {
    totalInvoices: invoices.length,
    totalAmount: invoices.reduce((sum: number, inv: any) => sum + inv.total_amount, 0),
    paidInvoices: invoices.filter((inv: any) => inv.status === 'paid').length,
    pendingInvoices: invoices.filter((inv: any) => inv.status === 'sent').length,
  };

  const handleCreateInvoice = () => {
    setSelectedInvoice(null);
    setShowInvoiceForm(true);
  };

  const handleEditInvoice = (invoice: any) => {
    setSelectedInvoice(invoice);
    setShowInvoiceForm(true);
  };

  const handleDeleteInvoice = async (invoiceId: number) => {
    if (!confirm('Are you sure you want to delete this invoice?')) return;
    
    try {
      await invoiceApi.delete(invoiceId);
      toast.success('Invoice deleted successfully');
      refetchInvoices();
    } catch (error) {
      toast.error('Failed to delete invoice');
    }
  };

  const handleStatusChange = async (invoiceId: number, newStatus: string) => {
    try {
      await invoiceApi.updateStatus(invoiceId, newStatus as any);
      toast.success('Invoice status updated');
      refetchInvoices();
    } catch (error) {
      toast.error('Failed to update invoice status');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid': return 'bg-green-100 text-green-800';
      case 'sent': return 'bg-blue-100 text-blue-800';
      case 'draft': return 'bg-gray-100 text-gray-800';
      case 'cancelled': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-8">
              <div className="flex items-center">
                <Building2 className="h-8 w-8 text-blue-600 mr-3" />
                <h1 className="text-xl font-semibold text-gray-900">
                  GST Service Center
                </h1>
              </div>
              <nav className="hidden md:flex items-center space-x-6 text-sm">
                <Link href="/" className="text-gray-600 hover:text-gray-900 flex items-center space-x-1">
                  <FileText className="h-4 w-4" /><span>Invoices</span>
                </Link>
                <Link href="/customers" className="text-gray-600 hover:text-gray-900 flex items-center space-x-1">
                  <Users className="h-4 w-4" /><span>Customers</span>
                </Link>
                <Link href="/inventory" className="text-gray-600 hover:text-gray-900 flex items-center space-x-1">
                  <Package className="h-4 w-4" /><span>Inventory</span>
                </Link>
                <Link href="/settings" className="text-gray-600 hover:text-gray-900 flex items-center space-x-1">
                  <SettingsIcon className="h-4 w-4" /><span>Settings</span>
                </Link>
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                Welcome, <span className="font-medium">{user?.full_name || user?.username}</span>
              </div>
              <button
                onClick={logout}
                className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
              >
                <LogOut className="h-4 w-4 mr-1" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="card">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-blue-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600">Total Invoices</p>
                <p className="text-2xl font-bold text-gray-900">{stats.totalInvoices}</p>
              </div>
            </div>
          </div>
          
          <div className="card">
            <div className="flex items-center">
              <DollarSign className="h-8 w-8 text-green-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600">Total Amount</p>
                <p className="text-2xl font-bold text-gray-900">₹{stats.totalAmount.toLocaleString()}</p>
              </div>
            </div>
          </div>
          
          <div className="card">
            <div className="flex items-center">
              <Users className="h-8 w-8 text-green-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600">Paid Invoices</p>
                <p className="text-2xl font-bold text-gray-900">{stats.paidInvoices}</p>
              </div>
            </div>
          </div>
          
          <div className="card">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-yellow-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600">Pending</p>
                <p className="text-2xl font-bold text-gray-900">{stats.pendingInvoices}</p>
              </div>
            </div>
          </div>
        </div>

        {/* System Health */}
        {healthData && (
          <div className="card mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">System Status</h2>
            <div className="flex items-center space-x-6">
              <div className="flex items-center">
                <div className={`w-3 h-3 rounded-full mr-2 ${
                  healthData.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                }`}></div>
                <span className="text-sm text-gray-600">
                  Backend: {healthData.status === 'healthy' ? 'Online' : 'Offline'}
                </span>
              </div>
              <div className="flex items-center">
                <div className={`w-3 h-3 rounded-full mr-2 ${
                  healthData.database?.connection ? 'bg-green-500' : 'bg-red-500'
                }`}></div>
                <span className="text-sm text-gray-600">
                  Database: {healthData.database?.connection ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Invoice Management */}
        <div className="card">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Invoice Management</h2>
            <button
              onClick={handleCreateInvoice}
              className="btn btn-primary"
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Invoice
            </button>
          </div>

          {/* Search and Filter */}
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search invoices..."
                className="input pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <select
                className="input pl-10 pr-8"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="all">All Status</option>
                <option value="draft">Draft</option>
                <option value="sent">Sent</option>
                <option value="paid">Paid</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>

          {/* Invoice Table */}
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Invoice #</th>
                  <th>Customer</th>
                  <th>Service</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredInvoices.map((invoice: any) => (
                  <tr key={invoice.id}>
                    <td className="font-medium text-blue-600">
                      {invoice.invoice_number}
                    </td>
                    <td>
                      <div>
                        <div className="font-medium">{invoice.customer_name}</div>
                        <div className="text-sm text-gray-500">{invoice.customer_phone}</div>
                      </div>
                    </td>
                    <td>
                      <div>
                        <div className="font-medium">{invoice.service_type}</div>
                        <div className="text-sm text-gray-500 truncate max-w-xs">
                          {invoice.service_description}
                        </div>
                      </div>
                    </td>
                    <td className="font-medium">₹{invoice.total_amount.toLocaleString()}</td>
                    <td>
                      <select
                        value={invoice.status}
                        onChange={(e) => handleStatusChange(invoice.id, e.target.value)}
                        className={`text-xs px-2 py-1 rounded-full border-0 ${getStatusColor(invoice.status)}`}
                      >
                        <option value="draft">Draft</option>
                        <option value="sent">Sent</option>
                        <option value="paid">Paid</option>
                        <option value="cancelled">Cancelled</option>
                      </select>
                    </td>
                    <td className="text-sm text-gray-500">
                      {format(new Date(invoice.created_at), 'MMM dd, yyyy')}
                    </td>
                    <td>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleEditInvoice(invoice)}
                          className="text-blue-600 hover:text-blue-900"
                          title="Edit"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteInvoice(invoice.id)}
                          className="text-red-600 hover:text-red-900"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                        <Link
                          href={`/invoices/${invoice.id}/print`}
                          className="text-gray-600 hover:text-gray-900"
                          title="Print / PDF"
                        >
                          <Printer className="h-4 w-4" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            
            {filteredInvoices.length === 0 && (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">No invoices found</p>
                <button
                  onClick={handleCreateInvoice}
                  className="btn btn-primary mt-4"
                >
                  Create Your First Invoice
                </button>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Invoice Form Modal */}
      {showInvoiceForm && (
        <InvoiceForm
          invoice={selectedInvoice}
          onClose={() => setShowInvoiceForm(false)}
          onSuccess={() => {
            setShowInvoiceForm(false);
            refetchInvoices();
          }}
        />
      )}
    </div>
  );
}