import axios from 'axios';

// Create axios instance with enhanced configuration
const api = axios.create({
  baseURL: '/api',
  timeout: 15000, // Increased timeout
  headers: {
    'Content-Type': 'application/json',
  },
  // Retry configuration
  retry: 3,
  retryDelay: 1000,
});

// Request interceptor for logging and auth
api.interceptors.request.use(
  (config) => {
    // Add timestamp for request tracking
    config.metadata = { startTime: new Date() };

    // Add auth token if available
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Log request in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`, config);
    }

    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor with enhanced error handling and retry logic
api.interceptors.response.use(
  (response) => {
    // Calculate response time
    const duration = new Date() - response.config.metadata.startTime;

    // Log successful response in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`API Response: ${response.status} ${response.config.method.toUpperCase()} ${response.config.url} (${duration}ms)`, response.data);
    }

    return response;
  },
  async (error) => {
    const config = error.config;

    // Calculate error time if metadata exists
    const duration = config?.metadata ? new Date() - config.metadata.startTime : 0;

    // Log error details
    console.error(`API Error: ${error.response?.status || 'Network'} ${config?.method?.toUpperCase() || 'UNKNOWN'} ${config?.url || 'unknown'} (${duration}ms)`, {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message
    });

    // Handle unauthorized access
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken');
      // Only redirect if not already on login page
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }

    // Handle network errors with retry logic
    if (!error.response && config?.retry > 0) {
      config.retry -= 1;
      config.metadata = { startTime: new Date() };

      // Exponential backoff
      const delay = config.retryDelay * Math.pow(2, 3 - config.retry);

      console.log(`Retrying request in ${delay}ms (attempts left: ${config.retry})`);

      await new Promise(resolve => setTimeout(resolve, delay));
      return api(config);
    }

    // Handle server errors (5xx) with retry for idempotent methods
    if (error.response?.status >= 500 && config?.retry > 0 && ['get', 'head', 'options'].includes(config.method)) {
      config.retry -= 1;
      config.metadata = { startTime: new Date() };

      const delay = config.retryDelay * Math.pow(2, 3 - config.retry);

      console.log(`Retrying server error in ${delay}ms (attempts left: ${config.retry})`);

      await new Promise(resolve => setTimeout(resolve, delay));
      return api(config);
    }

    return Promise.reject(error);
  }
);

export default api;

// API functions
export const staffAPI = {
  getAll: () => api.get('/staff'),
  getById: (id) => api.get(`/staff/${id}`),
  create: (data) => api.post('/staff', data),
  update: (id, data) => api.put(`/staff/${id}`, data),
  delete: (id) => api.delete(`/staff/${id}`),
};

export const projectAPI = {
  getAll: () => api.get('/projects'),
  getById: (id) => api.get(`/projects/${id}`),
  create: (data) => api.post('/projects', data),
  update: (id, data) => api.put(`/projects/${id}`, data),
  delete: (id) => api.delete(`/projects/${id}`),
  getForecast: (id, params) => api.get(`/projects/${id}/forecast`, { params }),
  getCost: (id) => api.get(`/projects/${id}/cost`),
};

export const assignmentAPI = {
  getAll: () => api.get('/assignments'),
  getById: (id) => api.get(`/assignments/${id}`),
  create: (data) => api.post('/assignments', data),
  update: (id, data) => api.put(`/assignments/${id}`, data),
  delete: (id) => api.delete(`/assignments/${id}`),
};

export const forecastAPI = {
  getOrganization: (params) => api.get('/forecasts/organization', { params }),
  simulate: (data) => api.post('/forecasts/simulate', data),
  getGaps: (params) => api.get('/forecasts/gaps', { params }),
};

export const capacityAPI = {
  getAnalysis: (params) => api.get('/capacity/analysis', { params }),
};
