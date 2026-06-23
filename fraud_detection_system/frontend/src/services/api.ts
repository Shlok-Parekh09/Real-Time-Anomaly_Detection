import type { Investigation, InvestigationFull, InvestigationStatusResponse } from '../types/api';

const BASE_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

class ApiService {
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${BASE_URL}${path}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      let errorDetail = `Error: ${response.status} ${response.statusText}`;
      try {
        const error = await response.json();
        errorDetail = error.detail || errorDetail;
      } catch (e) {
        // Fallback if not JSON
      }
      throw new Error(errorDetail);
    }

    return response.json();
  }

  async getInvestigations(): Promise<Investigation[]> {
    return this.request<Investigation[]>('/api/v1/investigations');
  }

  async getInvestigation(id: string): Promise<InvestigationFull> {
    return this.request<InvestigationFull>(`/api/v1/investigations/${id}`);
  }

  async createInvestigation(data: { context: string; title?: string }): Promise<Investigation> {
    return this.request<Investigation>('/api/v1/investigations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async uploadDocuments(id: string, files: File[]): Promise<{ uploaded: string[] }> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const url = `${BASE_URL}/api/v1/investigations/${id}/documents`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      // Note: Do NOT set Content-Type header when sending FormData, 
      // the browser will set it with the correct boundary.
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  async analyzeInvestigation(id: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/v1/investigations/${id}/analyze`, {
      method: 'POST',
    });
  }

  async getInvestigationStatus(id: string): Promise<InvestigationStatusResponse> {
    return this.request<InvestigationStatusResponse>(`/api/v1/investigations/${id}/status`);
  }

  async getInvestigationResults(id: string): Promise<InvestigationFull> {
    // Note: The backend endpoint /results returns the same full investigation data 
    // formatted by the report generator.
    return this.request<InvestigationFull>(`/api/v1/investigations/${id}/results`);
  }
}

export const api = new ApiService();
