import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL;

const api = axios.create({ baseURL: API_URL });

// Attach JWT token to every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('alethian_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Auto-purge stale/expired JWT tokens on 401 and redirect to login
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            localStorage.removeItem('alethian_token');
            localStorage.removeItem('alethian_user');
            if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
                window.location.href = '/login?expired=true';
            }
        }
        return Promise.reject(error);
    }
);

const Client = {
    auth: {
        login: async (username, password) => {
            const response = await api.post('/auth/login', { username, password });
            return response.data;
        }
    },

    documents: {
        list: async (params = {}) => {
            const response = await api.get('/documents', { params });
            return response.data;
        },
        get: async (id) => {
            const response = await api.get(`/documents/${id}`);
            return response.data;
        },
        upload: async (file, courseId = null, scope = null) => {
            const formData = new FormData();
            formData.append('file', file);
            if (courseId) formData.append('course_id', courseId);
            if (scope) {
                formData.append('check_ai', String(scope.check_ai ?? true));
                formData.append('check_web', String(scope.check_web ?? true));
                formData.append('check_internal', String(scope.check_internal ?? true));
            }
            const response = await api.post('/documents/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            return response.data;
        }
    },

    reports: {
        get: async (documentId) => {
            const response = await api.get(`/reports/${documentId}`);
            return response.data;
        },
        getHeatmap: async (documentId) => {
            const response = await api.get(`/reports/${documentId}/heatmap`);
            return response.data;
        },
        excludeMatch: async (documentId, matchId, data) => {
            const response = await api.patch(`/reports/${documentId}/matches/${matchId}`, data);
            return response.data;
        },
        commentMatch: async (documentId, matchId, comment) => {
            const response = await api.post(`/reports/${documentId}/matches/${matchId}/comment`, { comment });
            return response.data;
        },
        review: async (documentId, data) => {
            const response = await api.post(`/reports/${documentId}/review`, data);
            return response.data;
        },
        exportPdf: async (documentId, mode = 'bundle') => {
            try {
                const response = await api.get(`/reports/${documentId}/export-pdf`, { 
                    params: { mode },
                    responseType: 'blob' 
                });
                return response.data; // returns Blob — caller handles download
            } catch (err) {
                if (err.response && err.response.status === 404) {
                    const fallback = await api.get(`/reports/${documentId}/export/pdf`, { 
                        params: { mode },
                        responseType: 'blob' 
                    });
                    return fallback.data;
                }
                throw err;
            }
        },
        exportJson: async (documentId) => {
            const response = await api.get(`/reports/${documentId}/export/json`);
            return response.data;
        },
        getAIDetection: async (reportId) => {
            const response = await api.get(`/reports/${reportId}/ai-detection`);
            return response.data;
        }
    },

    admin: {
        getConfig: async () => {
            const response = await api.get('/admin/config');
            return response.data;
        },
        updateConfig: async (data) => {
            const response = await api.patch('/admin/config', data);
            return response.data;
        }
    },

    system: {
        getHealth: async () => {
            const response = await api.get('/health');
            return response.data;
        }
    }
};

export default Client;
