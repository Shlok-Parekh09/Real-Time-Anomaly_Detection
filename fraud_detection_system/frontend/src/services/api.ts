import type { Investigation, InvestigationFull, InvestigationStatusResponse } from '../types/api';

const BASE_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8001';

class ApiService {
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${BASE_URL}${path}`;
    console.log(`[API Request] OUTGOING: ${options.method || 'GET'} ${url}`, options.body ? `Body: ${options.body}` : '');
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      console.log(`[API Response] INCOMING: ${response.status} ${response.statusText} from ${url}`);

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
    } catch (err) {
      console.error(`[API Error] Diagnostic failure on url ${url}:`, err);
      if (err instanceof Error) {
        if (err.message.includes('Failed to fetch') || err.message.includes('fetch')) {
          throw new Error(`Connection Refused / CORS block at API URL ${BASE_URL}. Ensure backend server is running and port matches.`);
        }
        throw err;
      }
      throw new Error(`Network failure: ${String(err)}`);
    }
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

  async approveReference(id: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/v1/investigations/${id}/approve-reference`, {
      method: 'POST',
    });
  }

  async toggleBaseline(id: string): Promise<{ status: string; is_baseline: boolean }> {
    return this.request<{ status: string; is_baseline: boolean }>(`/api/v1/investigations/${id}/toggle-baseline`, {
      method: 'POST',
    });
  }

  async deleteInvestigation(id: string): Promise<void> {
    const url = `${BASE_URL}/api/v1/investigations/${id}`;
    const response = await fetch(url, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to delete' }));
      throw new Error(error.detail || 'Failed to delete');
    }
  }

  async warmupLlm(): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>('/api/v1/system/warmup', {
      method: 'POST',
    });
  }

  async getSettings(): Promise<any> {
    return this.request<any>('/api/v1/system/settings');
  }

  async saveSettings(settings: any): Promise<any> {
    return this.request<any>('/api/v1/system/settings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(settings),
    });
  }

  async reindexReferenceLibrary(): Promise<{ status: string; message: string; indexed: number }> {
    return this.request<{ status: string; message: string; indexed: number }>('/api/v1/system/reindex-reference', {
      method: 'POST',
    });
  }

  async flushOcrCache(): Promise<{ status: string; message: string; removed: number }> {
    return this.request<{ status: string; message: string; removed: number }>('/api/v1/system/flush-ocr-cache', {
      method: 'POST',
    });
  }
}

export const api = new ApiService();
