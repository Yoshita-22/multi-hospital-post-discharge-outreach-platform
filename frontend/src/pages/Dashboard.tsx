import React from 'react';
import { useAuth } from '../auth/AuthContext';
import { UserRole } from '../types';
import { Activity, Users, Building2, PhoneCall } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();

  const getWelcomeMessage = () => {
    switch (user?.role) {
      case UserRole.PLATFORM_ADMIN: return "System Overview";
      case UserRole.HOSPITAL_ADMIN: return "Hospital Operations Overview";
      case UserRole.CAMPAIGN_MANAGER: return "Campaign Performance";
      case UserRole.CLINICAL_REVIEWER: return "Clinical Triage Queue";
      default: return "Dashboard";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{getWelcomeMessage()}</h1>
        <div className="text-sm text-muted">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card flex items-center gap-4">
          <div className="bg-primary-light text-primary p-4 rounded-full">
            <Activity size={24} />
          </div>
          <div>
            <div className="text-sm text-muted font-medium">Active Campaigns</div>
            <div className="text-2xl font-bold">12</div>
          </div>
        </div>
        
        <div className="card flex items-center gap-4">
          <div className="bg-success-bg text-success p-4 rounded-full">
            <PhoneCall size={24} />
          </div>
          <div>
            <div className="text-sm text-muted font-medium">Calls Today</div>
            <div className="text-2xl font-bold">342</div>
          </div>
        </div>

        <div className="card flex items-center gap-4">
          <div className="bg-warning-bg text-warning p-4 rounded-full">
            <Users size={24} />
          </div>
          <div>
            <div className="text-sm text-muted font-medium">Pending Triage</div>
            <div className="text-2xl font-bold">8</div>
          </div>
        </div>

        <div className="card flex items-center gap-4">
          <div className="bg-danger-bg text-danger p-4 rounded-full">
            <Building2 size={24} />
          </div>
          <div>
            <div className="text-sm text-muted font-medium">Active Hospitals</div>
            <div className="text-2xl font-bold">4</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card lg:col-span-2">
          <h3 className="text-lg font-semibold mb-4 border-b pb-2">Recent Activity</h3>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-bg-primary rounded border">
                <div className="flex flex-col">
                  <span className="font-medium">Call completed for Patient #{1000 + i}</span>
                  <span className="text-xs text-muted">Protocol: Post-Discharge CHF</span>
                </div>
                <span className="badge badge-success">Completed</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 border-b pb-2">Quick Actions</h3>
          <div className="flex flex-col gap-3">
            <button className="btn btn-primary w-full justify-start">Create New Campaign</button>
            <button className="btn btn-outline w-full justify-start">View Triage Queue</button>
            <button className="btn btn-outline w-full justify-start">Generate Report</button>
          </div>
        </div>
      </div>
    </div>
  );
};
