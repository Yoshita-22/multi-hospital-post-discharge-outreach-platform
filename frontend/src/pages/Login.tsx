import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { authService } from '../api/auth';
import { Stethoscope } from 'lucide-react';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('platform_admin@system.local');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { access_token, user } = await authService.login(email, password);
      login(access_token, user);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-primary" style={{ backgroundImage: 'linear-gradient(to bottom right, var(--color-bg-primary), var(--color-bg-tertiary))' }}>
      <div className="card w-full max-w-md p-8 shadow-lg">
        <div className="flex flex-col items-center mb-8">
          <div className="bg-primary-light text-primary p-4 rounded-full mb-4">
            <Stethoscope size={32} />
          </div>
          <h2 className="text-2xl font-bold">Sign In</h2>
          <p className="text-muted text-sm mt-1">Multi-Hospital Outreach Platform</p>
        </div>
        
        {error && (
          <div className="mb-4 p-3 rounded bg-danger-bg text-danger-text text-sm font-medium border border-danger">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input 
              type="email" 
              className="input" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input 
              type="password" 
              className="input" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn btn-primary mt-2" disabled={loading}>
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6 text-sm text-muted">
          <p className="font-semibold mb-2">Test Accounts:</p>
          <ul className="list-disc pl-4 space-y-1">
            <li>platform_admin@system.local</li>
            <li>hospital_admin@citygeneral.local</li>
            <li>campaign_manager@citygeneral.local</li>
            <li>clinician@citygeneral.local</li>
          </ul>
          <p className="mt-2 text-xs">(Password: admin123 or user123)</p>
        </div>
      </div>
    </div>
  );
};
