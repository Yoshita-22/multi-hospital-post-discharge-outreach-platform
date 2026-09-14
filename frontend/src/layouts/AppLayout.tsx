import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { Header } from '../components/Header';
import './AppLayout.css';

export const AppLayout: React.FC = () => {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-main">
        <Header />
        <main className="app-content p-6 animate-fade-in">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
