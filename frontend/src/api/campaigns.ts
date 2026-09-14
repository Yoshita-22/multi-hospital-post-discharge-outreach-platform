import { apiClient } from './client';
import type { Campaign } from '../types';

export const campaignService = {
  getCampaigns: async (hospitalId?: string): Promise<Campaign[]> => {
    // If you need hospitalId, typically the backend derives it from the token context.
    const url = hospitalId ? `/hospitals/${hospitalId}/campaigns` : '/campaigns';
    const response = await apiClient.get(url);
    return response.data;
  },

  getCampaignById: async (id: string): Promise<Campaign> => {
    const response = await apiClient.get(`/campaigns/${id}`);
    return response.data;
  },

  startCampaign: async (id: string): Promise<any> => {
    const response = await apiClient.post(`/campaigns/${id}/start`);
    return response.data;
  }
};
