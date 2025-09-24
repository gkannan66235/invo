'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { invoiceApi, CreateInvoiceRequest } from '@/lib/api';
import { X } from 'lucide-react';
import { toast } from 'react-hot-toast';

interface InvoiceFormProps {
  invoice?: any;
  onClose: () => void;
  onSuccess: () => void;
}

export default function InvoiceForm({ invoice, onClose, onSuccess }: InvoiceFormProps) {
  const [isLoading, setIsLoading] = useState(false);
  const isEditing = !!invoice;

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
  } = useForm<CreateInvoiceRequest>({
    defaultValues: invoice ? {
      customer_name: invoice.customer_name,
      customer_phone: invoice.customer_phone,
      customer_email: invoice.customer_email || '',
      service_type: invoice.service_type,
      service_description: invoice.service_description,
      amount: invoice.amount,
      gst_rate: invoice.gst_rate,
      due_date: invoice.due_date ? new Date(invoice.due_date).toISOString().split('T')[0] : '',
    } : {
      gst_rate: 18, // Default GST rate
    }
  });

  // Coerce form values to numbers to avoid string concatenation issues (e.g. 500 + 60 => 50060)
  const rawAmount = watch('amount');
  const rawGstRate = watch('gst_rate');
  const amount = typeof rawAmount === 'string' ? parseFloat(rawAmount) || 0 : (rawAmount || 0);
  const gstRate = typeof rawGstRate === 'string' ? parseFloat(rawGstRate) || 0 : (rawGstRate || 0);
  const gstAmount = Number(((amount * gstRate) / 100).toFixed(2));
  const totalAmount = Number((amount + gstAmount).toFixed(2));

  useEffect(() => {
    // Auto-calculate GST when amount or rate changes
    setValue('amount', amount);
  }, [amount, gstRate, setValue]);

  const onSubmit = async (data: CreateInvoiceRequest) => {
    setIsLoading(true);
    try {
      if (isEditing) {
        await invoiceApi.update(invoice.id, data);
        toast.success('Invoice updated successfully');
      } else {
        await invoiceApi.create(data);
        toast.success('Invoice created successfully');
      }
      onSuccess();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to save invoice');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center p-6 border-b">
          <h2 className="text-xl font-semibold">
            {isEditing ? 'Edit Invoice' : 'Create New Invoice'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
          {/* Customer Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">Customer Information</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Customer Name *
                </label>
                <input
                  {...register('customer_name', { required: 'Customer name is required' })}
                  type="text"
                  className="input"
                  placeholder="Enter customer name"
                />
                {errors.customer_name && (
                  <p className="mt-1 text-sm text-red-600">{errors.customer_name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Phone Number *
                </label>
                <input
                  {...register('customer_phone', { 
                    required: 'Phone number is required',
                    pattern: {
                      value: /^[0-9]{10}$/,
                      message: 'Please enter a valid 10-digit phone number'
                    }
                  })}
                  type="tel"
                  className="input"
                  placeholder="Enter phone number"
                />
                {errors.customer_phone && (
                  <p className="mt-1 text-sm text-red-600">{errors.customer_phone.message}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <input
                {...register('customer_email', {
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: 'Please enter a valid email address'
                  }
                })}
                type="email"
                className="input"
                placeholder="Enter email address (optional)"
              />
              {errors.customer_email && (
                <p className="mt-1 text-sm text-red-600">{errors.customer_email.message}</p>
              )}
            </div>
          </div>

          {/* Service Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">Service Information</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Service Type *
              </label>
              <select
                {...register('service_type', { required: 'Service type is required' })}
                className="input"
              >
                <option value="">Select service type</option>
                <option value="Mobile Repair">Mobile Repair</option>
                <option value="Laptop Repair">Laptop Repair</option>
                <option value="Computer Repair">Computer Repair</option>
                <option value="Software Installation">Software Installation</option>
                <option value="Data Recovery">Data Recovery</option>
                <option value="Virus Removal">Virus Removal</option>
                <option value="Hardware Upgrade">Hardware Upgrade</option>
                <option value="Other">Other</option>
              </select>
              {errors.service_type && (
                <p className="mt-1 text-sm text-red-600">{errors.service_type.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Service Description *
              </label>
              <textarea
                {...register('service_description', { required: 'Service description is required' })}
                rows={3}
                className="input"
                placeholder="Describe the service provided..."
              />
              {errors.service_description && (
                <p className="mt-1 text-sm text-red-600">{errors.service_description.message}</p>
              )}
            </div>
          </div>

          {/* Billing Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">Billing Information</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Service Amount (₹) *
                </label>
                <input
                  {...register('amount', { 
                    required: 'Amount is required',
                    min: {
                      value: 1,
                      message: 'Amount must be greater than 0'
                    }
                  })}
                  type="number"
                  step="0.01"
                  className="input"
                  placeholder="Enter service amount"
                />
                {errors.amount && (
                  <p className="mt-1 text-sm text-red-600">{errors.amount.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  GST Rate (%) *
                </label>
                <select
                  {...register('gst_rate', { required: 'GST rate is required' })}
                  className="input"
                >
                  <option value="0">0%</option>
                  <option value="5">5%</option>
                  <option value="12">12%</option>
                  <option value="18">18%</option>
                  <option value="28">28%</option>
                </select>
                {errors.gst_rate && (
                  <p className="mt-1 text-sm text-red-600">{errors.gst_rate.message}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Due Date
              </label>
              <input
                {...register('due_date')}
                type="date"
                className="input"
                min={new Date().toISOString().split('T')[0]}
              />
            </div>

            {/* Amount Summary */}
            <div className="bg-gray-50 p-4 rounded-lg space-y-2">
              <div className="flex justify-between text-sm">
                <span>Service Amount:</span>
                <span>₹{amount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>GST ({gstRate}%):</span>
                <span>₹{gstAmount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-lg font-semibold border-t pt-2">
                <span>Total Amount:</span>
                <span>₹{totalAmount.toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex justify-end space-x-4 pt-6 border-t">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {isEditing ? 'Updating...' : 'Creating...'}
                </div>
              ) : (
                isEditing ? 'Update Invoice' : 'Create Invoice'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}