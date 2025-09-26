"use client";
import { useEffect, useState } from 'react';
import { inventoryApi, InventoryItem } from '@/lib/api';
import { toast } from 'react-hot-toast';
import { useAuth } from '@/lib/auth-context';

export default function InventoryPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ product_code: '', description: '', gst_rate: '', selling_price: '' });
  const [editingItem, setEditingItem] = useState<InventoryItem | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    try {
      const data = await inventoryApi.list();
      setItems(data.items || []);
    } catch (e:any) {
      toast.error('Failed to load inventory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const resetForm = () => {
    setForm({ product_code: '', description: '', gst_rate: '', selling_price: '' });
    setEditingItem(null);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      const payload: any = {
        product_code: form.product_code,
        description: form.description,
      };
      if (form.gst_rate) payload.gst_rate = parseFloat(form.gst_rate);
      if (form.selling_price) payload.selling_price = parseFloat(form.selling_price);

      if (editingItem) {
        const updated = await inventoryApi.update(String(editingItem.id), payload);
        toast.success('Item updated');
        setItems(prev => prev.map(i => i.id === updated.id ? updated : i));
        resetForm();
      } else {
        await inventoryApi.create(payload);
        toast.success('Item created');
        resetForm();
        load();
      }
    } catch (err:any) {
      toast.error(err.response?.data?.error?.message || 'Save failed');
    } finally {
      setSubmitting(false);
    }
  };

  const deactivate = async (id: string) => {
    if (!confirm('Deactivate this item?')) return;
    try {
      await inventoryApi.deactivate(id);
      toast.success('Item deactivated');
      load();
    } catch (e:any) {
      toast.error('Failed to deactivate');
    }
  };

  const startEdit = (item: InventoryItem) => {
    setEditingItem(item);
    setForm({
      product_code: item.product_code || '',
      description: item.description || '',
      gst_rate: item.gst_rate != null ? String(item.gst_rate) : '',
      selling_price: item.selling_price != null ? String(item.selling_price) : '',
    });
  };

  if (!user) return null;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Inventory</h1>
      <form onSubmit={onSubmit} className="space-y-4 bg-white shadow p-4 rounded max-w-md">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">{editingItem ? 'Edit Item' : 'Add Item'}</h2>
          {editingItem && (
            <button type="button" className="text-sm text-gray-500 hover:underline" onClick={resetForm}>Cancel</button>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Product Code</label>
          <input className="input" value={form.product_code} onChange={e=>setForm(f=>({...f,product_code:e.target.value}))} required />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea className="input" value={form.description} onChange={e=>setForm(f=>({...f,description:e.target.value}))} required />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">GST Rate (%)</label>
            <input className="input" value={form.gst_rate} onChange={e=>setForm(f=>({...f,gst_rate:e.target.value}))} />
          </div>
            <div>
            <label className="block text-sm font-medium mb-1">Selling Price</label>
            <input className="input" value={form.selling_price} onChange={e=>setForm(f=>({...f,selling_price:e.target.value}))} />
          </div>
        </div>
        <button className="btn btn-primary disabled:opacity-50" type="submit" disabled={submitting}>{submitting ? 'Saving...' : (editingItem ? 'Save Changes' : 'Add Item')}</button>
      </form>

      <div className="bg-white shadow rounded p-4">
        <h2 className="font-medium mb-3">Items</h2>
        {loading ? <p>Loading...</p> : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="py-2 pr-4">Code</th>
                <th className="py-2 pr-4">Description</th>
                <th className="py-2 pr-4">GST</th>
                <th className="py-2 pr-4">Price</th>
                <th className="py-2 pr-4">Active</th>
                <th className="py-2 pr-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(i => (
                <tr key={i.id} className={`border-b last:border-none ${editingItem?.id === i.id ? 'bg-blue-50' : ''}`}>
                  <td className="py-2 pr-4 font-medium">{i.product_code}</td>
                  <td className="py-2 pr-4 max-w-xs truncate">{i.description}</td>
                  <td className="py-2 pr-4">{i.gst_rate ?? '-'}</td>
                  <td className="py-2 pr-4">{i.selling_price ?? '-'}</td>
                  <td className="py-2 pr-4">{i.is_active ? 'Yes' : 'No'}</td>
                  <td className="py-2 pr-4 space-x-2">
                    {i.is_active && (
                      <button onClick={()=>deactivate(i.id)} className="text-sm text-red-600 hover:underline">Deactivate</button>
                    )}
                    <button onClick={()=>startEdit(i)} className="text-sm text-blue-600 hover:underline">Edit</button>
                  </td>
                </tr>
              ))}
              {!items.length && <tr><td colSpan={6} className="py-4 text-gray-500">No items</td></tr>}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
