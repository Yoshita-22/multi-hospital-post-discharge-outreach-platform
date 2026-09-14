import { apiClient } from './client';
import type { TriageDetail } from '../types';

export interface MockTriageRequest {
  call_id?: string;
  scenario: 'routine' | 'attention' | 'urgent';
}

export const triageService = {
  runMockTriage: async (payload: MockTriageRequest): Promise<TriageDetail> => {
    const response = await apiClient.post('/triage/mock-run', payload);
    return response.data;
  }
};
