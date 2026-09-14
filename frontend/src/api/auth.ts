import { apiClient } from './client';
import { type User, UserRole } from '../types';
import { jwtDecode } from 'jwt-decode';

export const authService = {
  login: async (username: string, password: string): Promise<{ access_token: string, token_type: string, user: User }> => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const response = await apiClient.post('/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });

    const token = response.data.access_token;
    const decoded: any = jwtDecode(token);
    
    // In our backend JWT, we have `sub` (usually user_id), `hospital_id`, `role`.
    const user: User = {
      id: decoded.user_id || decoded.sub,
      hospital_id: decoded.hospital_id || null,
      name: username, // Fallback since it's not in JWT
      email: username,
      role: decoded.role as UserRole,
      status: 'ACTIVE'
    };

    return { ...response.data, user };
  }
};
