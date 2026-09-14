import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { AppLayout } from './layouts/AppLayout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { TriageMock } from './pages/TriageMock';
import { Campaigns } from './pages/Campaigns';
import { UserRole } from './types';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<Dashboard />} />
              
              <Route 
                path="/triage" 
                element={
                  <ProtectedRoute allowedRoles={[UserRole.PLATFORM_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.CLINICAL_REVIEWER]}>
                    <TriageMock />
                  </ProtectedRoute>
                } 
              />

              <Route 
                path="/campaigns" 
                element={
                  <ProtectedRoute allowedRoles={[UserRole.PLATFORM_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.CAMPAIGN_MANAGER]}>
                    <Campaigns />
                  </ProtectedRoute>
                } 
              />
            </Route>
          </Route>
          
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;
