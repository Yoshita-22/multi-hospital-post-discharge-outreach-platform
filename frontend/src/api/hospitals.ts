import { apiClient } from './client';
import type { Hospital } from '../types';

export const hospitalService = {
  getHospitals: async (): Promise<Hospital[]> => {
    const response = await apiClient.get('/hospitals');
    return response.data;
  },

  getHospitalById: async (id: string): Promise<Hospital> => {
    const response = await apiClient.get(`/hospitals/${id}`);
    return response.data;
  }
};
