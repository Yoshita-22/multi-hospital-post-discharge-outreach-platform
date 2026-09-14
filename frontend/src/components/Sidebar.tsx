import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { UserRole } from '../types';
import { LayoutDashboard, Building2, Users, Activity, Settings, Stethoscope, PhoneCall, ScrollText } from 'lucide-react';
import './Sidebar.css';

interface NavItem {
  name: string;
  path: string;
  icon: React.ElementType;
  roles: UserRole[];
}

const NAV_ITEMS: NavItem[] = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard, roles: [UserRole.PLATFORM_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.CAMPAIGN_MANAGER, UserRole.CLINICAL_REVIEWER] },
  { name: 'Hospitals', path: '/admin/hospitals', icon: Building2, roles: [UserRole.PLATFORM_ADMIN] },
  { name: 'Users', path: '/admin/users', icon: Users, roles: [UserRole.PLATFORM_ADMIN, UserRole.HOSPITAL_ADMIN] },
  { name: 'Campaigns', path: '/campaigns', icon: Activity, roles: [UserRole.PLATFORM_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.CAMPAIGN_MANAGER] },
  { name: 'Protocols', path: '/protocols', icon: ScrollText, roles: [UserRole.PLATFORM_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.CAMPAIGN_MANAGER] },
  { name: 'Triage & Review', path: '/triage', icon: Stethoscope, roles: [UserRole.PLATFORM_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.CLINICAL_REVIEWER] },
  { name: 'Live Calls', path: '/calls', icon: PhoneCall, roles: [UserRole.PLATFORM_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.CAMPAIGN_MANAGER] },
  { name: 'Settings', path: '/settings', icon: Settings, roles: [UserRole.PLATFORM_ADMIN, UserRole.HOSPITAL_ADMIN] },
];

export const Sidebar: React.FC = () => {
  const { user } = useAuth();

  if (!user) return null;

  const allowedItems = NAV_ITEMS.filter(item => item.roles.includes(user.role));

  return (
    <aside className="sidebar shadow-md glass-panel">
      <div className="sidebar-header p-6 border-b border">
        <h2 className="text-xl font-bold text-primary flex items-center gap-2">
          <Stethoscope className="text-primary" />
          Multi-Hospital AI
        </h2>
        <div className="mt-2 text-sm text-secondary font-medium">
          Role: <span className="badge badge-neutral">{user.role.replace('_', ' ')}</span>
        </div>
      </div>
      <nav className="sidebar-nav p-4 flex-col gap-2">
        {allowedItems.map((item) => (
          <NavLink 
            key={item.path} 
            to={item.path}
            className={({ isActive }) => 
              `sidebar-link flex items-center gap-4 px-4 py-3 rounded-lg font-medium transition-all ${isActive ? 'active bg-primary text-white' : 'text-secondary hover:bg-secondary'}`
            }
          >
            <item.icon size={20} />
            {item.name}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
};
