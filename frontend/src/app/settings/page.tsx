"use client";
import { useEffect, useState } from 'react';
import { settingsApi, SettingsResponse } from '@/lib/api';
import { toast } from 'react-hot-toast';
import { useAuth } from '@/lib/auth-context';

export default function SettingsPage() {
  const { user } = useAuth();
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [gstRate, setGstRate] = useState('');
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const s = await settingsApi.get();
      setSettings(s);
      setGstRate(String(s.gst_default_rate ?? ''));
    } catch (e:any) {
      toast.error('Failed to load settings');
    }
  };

  useEffect(() => { load(); }, []);

  const update = async (e: React.FormEvent) => {
    e.preventDefault();
    if (user?.role && user.role !== 'admin') {
      toast.error('Only admin can modify settings');
      return;
    }
    setSaving(true);
    try {
      const updated = await settingsApi.update({ gst_default_rate: parseFloat(gstRate) });
      setSettings(updated);
      toast.success('Settings updated');
    } catch (e:any) {
      toast.error('Update failed');
    } finally {
      setSaving(false);
    }
  };

  if (!user) return null;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <form onSubmit={update} className="space-y-4 bg-white shadow p-4 rounded max-w-md">
        <div>
          <label className="block text-sm font-medium mb-1">Default GST Rate (%)</label>
          <input className="input" value={gstRate} onChange={e=>setGstRate(e.target.value)} required />
        </div>
        <button type="submit" className="btn btn-primary disabled:opacity-50" disabled={saving || (user && user.role !== 'admin')}>
          {saving ? 'Saving...' : (user && user.role !== 'admin' ? 'Read Only' : 'Save')}
        </button>
      </form>
      {settings && (
        <div className="text-sm text-gray-600">
          <p>Last updated: {settings.updated_at || '—'}</p>
        </div>
      )}
    </div>
  );
}
