import React from 'react';
import { useAuth } from '../auth/AuthContext';
import { LogOut, User as UserIcon } from 'lucide-react';
import './Header.css';

export const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="header shadow-sm border-b glass-panel flex items-center justify-between px-6 py-4">
      <div>
        <h1 className="text-xl font-bold">Post-Discharge Outreach Platform</h1>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <div className="bg-primary-light text-primary p-2 rounded-full">
            <UserIcon size={18} />
          </div>
          <div className="flex-col">
            <span className="font-semibold text-sm">{user?.name}</span>
            <span className="text-xs text-muted">{user?.email}</span>
          </div>
        </div>
        <button onClick={logout} className="btn btn-outline" title="Logout">
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </header>
  );
};
