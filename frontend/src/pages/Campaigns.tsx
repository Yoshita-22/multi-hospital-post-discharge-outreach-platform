import React, { useEffect, useState } from 'react';
import { campaignService } from '../api/campaigns';
import type { Campaign } from '../types';
import { Activity, Plus, Play, Pause, AlertCircle } from 'lucide-react';

export const Campaigns: React.FC = () => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCampaigns();
  }, []);

  const loadCampaigns = async () => {
    try {
      const data = await campaignService.getCampaigns();
      setCampaigns(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'RUNNING': return 'badge-success';
      case 'PAUSED': return 'badge-warning';
      case 'FAILED': return 'badge-danger';
      case 'DRAFT': return 'badge-neutral';
      default: return 'badge-neutral';
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Activity className="text-primary" />
            Outreach Campaigns
          </h1>
          <p className="text-muted mt-1">Manage AI calling campaigns and patient queues</p>
        </div>
        <button className="btn btn-primary">
          <Plus size={18} /> New Campaign
        </button>
      </div>

      <div className="card">
        {loading ? (
          <div className="p-8 text-center text-muted">Loading campaigns...</div>
        ) : campaigns.length === 0 ? (
          <div className="p-12 flex flex-col items-center justify-center text-center text-muted border-2 border-dashed rounded-lg">
            <AlertCircle size={48} className="mb-4 text-muted opacity-50" />
            <h3 className="text-lg font-semibold text-secondary">No Campaigns Found</h3>
            <p className="mb-4 max-w-md">There are no active or drafted campaigns for this hospital. Create a new campaign to begin patient outreach.</p>
            <button className="btn btn-primary"><Plus size={18} /> Create Campaign</button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b text-sm text-muted">
                  <th className="p-4 font-semibold">Name</th>
                  <th className="p-4 font-semibold">Status</th>
                  <th className="p-4 font-semibold">Validation</th>
                  <th className="p-4 font-semibold">Capacity</th>
                  <th className="p-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map(camp => (
                  <tr key={camp.id} className="border-b last:border-0 hover:bg-bg-tertiary transition-colors">
                    <td className="p-4">
                      <div className="font-semibold">{camp.name}</div>
                      <div className="text-xs text-muted">{camp.description || 'No description'}</div>
                    </td>
                    <td className="p-4">
                      <span className={`badge ${getStatusBadge(camp.status)}`}>{camp.status}</span>
                    </td>
                    <td className="p-4">
                      <span className="text-sm font-medium">{camp.validation_status}</span>
                    </td>
                    <td className="p-4 text-sm text-secondary">
                      {camp.calling_capacity} concurrent
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex justify-end gap-2">
                        {camp.status !== 'RUNNING' && (
                          <button className="btn btn-outline py-1 px-2 text-success hover:bg-success-bg border-success">
                            <Play size={16} /> Start
                          </button>
                        )}
                        {camp.status === 'RUNNING' && (
                          <button className="btn btn-outline py-1 px-2 text-warning hover:bg-warning-bg border-warning">
                            <Pause size={16} /> Pause
                          </button>
                        )}
                        <button className="btn btn-outline py-1 px-3">View</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
