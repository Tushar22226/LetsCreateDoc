import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export interface ProjectData {
    title: string;
    page_count: number;
    description: string;
    custom_index: string[];
    theme_color: string;
    include_code: boolean;
    include_flowcharts: boolean;
    include_graphs: boolean;
    include_charts: boolean;
}

export interface ProjectHistoryItem {
    id: number;
    title: string;
    description: string;
    page_count: number;
    theme_color: string;
    status: string;
    created_at: string;
}

export const documentationService = {
    generateIndex: async (data: ProjectData): Promise<string[]> => {
        const response = await axios.post(`${API_BASE_URL}/generate-index`, data);
        return response.data.index;
    },

    generateDocument: async (data: ProjectData): Promise<Blob> => {
        const response = await axios.post(`${API_BASE_URL}/documentation/generate-docx`, data, {
            responseType: 'blob',
        });
        return response.data;
    },

    getHistory: async (): Promise<ProjectHistoryItem[]> => {
        const response = await axios.get(`${API_BASE_URL}/documentation/history`);
        return response.data.projects;
    },

    downloadHistoryDocx: async (projectId: number): Promise<Blob> => {
        const response = await axios.get(`${API_BASE_URL}/documentation/download/${projectId}`, {
            responseType: 'blob',
        });
        return response.data;
    }
};
