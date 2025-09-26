"use client";

import { useEffect, useState } from 'react';
import { customersApi, Customer } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { toast } from 'react-hot-toast';

export default function CustomersPage() {
  const { user } = useAuth();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: '', phone: '', email: '', address: '', city: '' });
  const [duplicateWarning, setDuplicateWarning] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState('');
  const [searching, setSearching] = useState(false);

  const load = async (q?: string) => {
    try {
      const data = await customersApi.list(q);
      setCustomers(data.customers || []);
    } catch (e:any) {
      toast.error('Failed to load customers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const resetForm = () => {
    setForm({ name: '', phone: '', email: '', address: '', city: '' });
    setEditingCustomer(null);
    setDuplicateWarning(false);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setDuplicateWarning(false);
    try {
      if (!form.phone && !form.email) {
        toast.error('Provide at least a phone or an email');
        return;
      }
      const payload: any = {
        name: form.name,
        phone: form.phone || undefined,
        email: form.email || undefined,
      };
      if (form.address || form.city) {
        payload.address = { street: form.address || null, city: form.city || null };
      }
      if (editingCustomer) {
        const updated = await customersApi.update(String(editingCustomer.id), payload);
        toast.success('Customer updated');
        setCustomers(prev => prev.map(c => c.id === updated.id ? updated : c));
        resetForm();
      } else {
        const created = await customersApi.create(payload);
        if ((created as any).duplicate_warning) {
          setDuplicateWarning(true);
          toast.success('Customer created (duplicate mobile)');
        } else {
          toast.success('Customer created');
        }
        setForm({ name: '', phone: '', email: '', address: '', city: '' });
        load();
      }
    } catch (err:any) {
      toast.error(err.response?.data?.error?.message || 'Save failed');
    } finally {
      setSubmitting(false);
    }
  };

  const startEdit = (customer: Customer) => {
    setEditingCustomer(customer);
    setForm({
      name: customer.name || '',
      phone: customer.phone || '',
      email: customer.email || '',
      address: (customer.address && (customer.address.street || customer.address.address_line)) || '',
      city: (customer.address && customer.address.city) || customer.city || ''
    });
    setDuplicateWarning(false);
  };

  if (!user) return null;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Customers</h1>
      <div className="flex items-center gap-2 max-w-md">
        <input
          className="input flex-1"
          placeholder="Search by name or phone"
          value={search}
          onChange={(e)=> setSearch(e.target.value)}
        />
        <button
          className="btn btn-secondary"
          disabled={searching}
          onClick={async ()=>{ setSearching(true); await load(search.trim()||undefined); setSearching(false); }}
        >{searching? '...' : 'Search'}</button>
        {search && (
          <button
            className="text-sm text-gray-500 hover:underline"
            onClick={()=>{ setSearch(''); load(); }}
          >Clear</button>
        )}
      </div>
      <form onSubmit={onSubmit} className="space-y-4 bg-white shadow p-4 rounded max-w-md">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">{editingCustomer ? 'Edit Customer' : 'Add Customer'}</h2>
          {editingCustomer && (
            <button
              type="button"
              className="text-sm text-gray-500 hover:underline"
              onClick={resetForm}
            >Cancel</button>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Name</label>
          <input className="input" value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))} required />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Phone</label>
          <input className="input" value={form.phone} onChange={e=>setForm(f=>({...f,phone:e.target.value}))} />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Email</label>
          <input className="input" type="email" value={form.email} onChange={e=>setForm(f=>({...f,email:e.target.value}))} />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Address</label>
          <input className="input" value={form.address} onChange={e=>setForm(f=>({...f,address:e.target.value}))} placeholder="Street / Line" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">City</label>
          <input className="input" value={form.city} onChange={e=>setForm(f=>({...f,city:e.target.value}))} />
        </div>
        <button className="btn btn-primary disabled:opacity-50" type="submit" disabled={submitting}>{submitting ? 'Saving...' : (editingCustomer ? 'Save Changes' : 'Add Customer')}</button>
        {duplicateWarning && <p className="text-yellow-600 text-sm">Duplicate warning: mobile already exists.</p>}
      </form>

      <div className="bg-white shadow rounded p-4">
        <h2 className="font-medium mb-3">Customer List</h2>
        {loading ? <p>Loading...</p> : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Phone</th>
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">City</th>
                <th className="py-2 pr-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {customers.map(c => (
                <tr key={c.id} className={`border-b last:border-none ${editingCustomer?.id === c.id ? 'bg-blue-50' : ''}`}>
                  <td className="py-2 pr-4">{c.name}</td>
                  <td className="py-2 pr-4">{c.phone || '-'}</td>
                  <td className="py-2 pr-4">{c.email || '-'}</td>
                  <td className="py-2 pr-4">{c.city || c.address?.city || '-'}</td>
                  <td className="py-2 pr-4 space-x-2">
                    <button onClick={()=>startEdit(c)} className="text-sm text-blue-600 hover:underline">Edit</button>
                  </td>
                </tr>
              ))}
              {!customers.length && <tr><td colSpan={5} className="py-4 text-gray-500">No customers</td></tr>}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
