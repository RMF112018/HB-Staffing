import axios from 'axios';

// Create axios instance with enhanced configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api',
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
    if (import.meta.env.DEV) {
      console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`, config);
    }

    return config;
  },
  (error) => {
    if (import.meta.env.DEV) {
      console.error('Request error:', error);
    }
    return Promise.reject(error);
  }
);

// Response interceptor with enhanced error handling and retry logic
api.interceptors.response.use(
  (response) => {
    // Calculate response time
    const duration = new Date() - response.config.metadata.startTime;

    // Log successful response in development
    if (import.meta.env.DEV) {
      console.log(`API Response: ${response.status} ${response.config.method.toUpperCase()} ${response.config.url} (${duration}ms)`, response.data);
    }

    return response;
  },
  async (error) => {
    const config = error.config;

    // Calculate error time if metadata exists
    const duration = config?.metadata ? new Date() - config.metadata.startTime : 0;

    // Log error details in development
    if (import.meta.env.DEV) {
      console.error(`API Error: ${error.response?.status || 'Network'} ${config?.method?.toUpperCase() || 'UNKNOWN'} ${config?.url || 'unknown'} (${duration}ms)`, {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        message: error.message
      });
    }

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

      if (import.meta.env.DEV) {
        console.log(`Retrying request in ${delay}ms (attempts left: ${config.retry})`);
      }

      await new Promise(resolve => setTimeout(resolve, delay));
      return api(config);
    }

    // Handle server errors (5xx) with retry for idempotent methods
    if (error.response?.status >= 500 && config?.retry > 0 && ['get', 'head', 'options'].includes(config.method)) {
      config.retry -= 1;
      config.metadata = { startTime: new Date() };

      const delay = config.retryDelay * Math.pow(2, 3 - config.retry);

      if (import.meta.env.DEV) {
        console.log(`Retrying server error in ${delay}ms (attempts left: ${config.retry})`);
      }

      await new Promise(resolve => setTimeout(resolve, delay));
      return api(config);
    }

    return Promise.reject(error);
  }
);

export default api;

// API functions
export const roleAPI = {
  getAll: (params) => api.get('/roles', { params }),
  getById: (id) => api.get(`/roles/${id}`),
  create: (data) => api.post('/roles', data),
  update: (id, data) => api.put(`/roles/${id}`, data),
  delete: (id) => api.delete(`/roles/${id}`),
};

export const staffAPI = {
  getAll: () => api.get('/staff'),
  getById: (id) => api.get(`/staff/${id}`),
  create: (data) => api.post('/staff', data),
  update: (id, data) => api.put(`/staff/${id}`, data),
  delete: (id) => api.delete(`/staff/${id}`),
};

export const projectAPI = {
  // Get all projects with optional filtering
  getAll: (params) => api.get('/projects', { params }),
  // Get projects filtered by options (status, location, parent_id, etc.)
  getFiltered: (options) => api.get('/projects', { params: options }),
  // Get top-level projects only (folders and standalone projects)
  getTopLevel: () => api.get('/projects', { params: { top_level_only: true, include_children: true } }),
  // Get sub-projects of a parent folder
  getSubProjects: (parentId) => api.get('/projects', { params: { parent_id: parentId } }),
  // Get folders only
  getFolders: () => api.get('/projects', { params: { is_folder: true } }),
  // Get a project by ID with optional children
  getById: (id, includeChildren = true) => api.get(`/projects/${id}`, { params: { include_children: includeChildren } }),
  create: (data) => api.post('/projects', data),
  update: (id, data) => api.put(`/projects/${id}`, data),
  delete: (id) => api.delete(`/projects/${id}`),
  getForecast: (id, params) => api.get(`/projects/${id}/forecast`, { params }),
  getCost: (id) => api.get(`/projects/${id}/cost`),
  // Role rates for a project
  getRoleRates: (projectId) => api.get(`/projects/${projectId}/role-rates`),
  setRoleRates: (projectId, rates) => api.post(`/projects/${projectId}/role-rates`, { rates }),
  updateRoleRate: (projectId, roleId, billableRate) => api.put(`/projects/${projectId}/role-rates/${roleId}`, { billable_rate: billableRate }),
  deleteRoleRate: (projectId, roleId) => api.delete(`/projects/${projectId}/role-rates/${roleId}`),
};

export const assignmentAPI = {
  getAll: () => api.get('/assignments'),
  getById: (id, includeMonthlyAllocations = true) => 
    api.get(`/assignments/${id}`, { params: { include_monthly_allocations: includeMonthlyAllocations } }),
  create: (data) => api.post('/assignments', data),
  update: (id, data) => api.put(`/assignments/${id}`, data),
  delete: (id) => api.delete(`/assignments/${id}`),
  // Monthly allocation endpoints
  getMonthlyAllocations: (assignmentId) => api.get(`/assignments/${assignmentId}/monthly-allocations`),
  updateMonthlyAllocations: (assignmentId, allocations) => 
    api.put(`/assignments/${assignmentId}/monthly-allocations`, { allocations }),
};

export const forecastAPI = {
  getOrganization: (params) => api.get('/forecasts/organization', { params }),
  simulate: (data) => api.post('/forecasts/simulate', data),
  getGaps: (params) => api.get('/forecasts/gaps', { params }),
  // Staff availability forecast
  getStaffAvailability: (params) => api.get('/forecasts/staff-availability', { params }),
  // Staff suggestions for a role
  getSuggestions: (params) => api.get('/forecasts/suggestions', { params }),
  // New hire needs analysis
  getNewHireNeeds: (params) => api.get('/forecasts/new-hire-needs', { params }),
  // Organization-wide over-allocations
  getOrganizationOverAllocations: (params) => api.get('/organization/over-allocations', { params }),
  // Validate assignment allocation
  validateAllocation: (data) => api.post('/assignments/validate-allocation', data),
  // Staff allocation conflicts
  getStaffAllocationConflicts: (staffId, params) => api.get(`/staff/${staffId}/allocation-conflicts`, { params }),
  // Staff allocation timeline
  getStaffAllocationTimeline: (staffId, params) => api.get(`/staff/${staffId}/allocation-timeline`, { params }),
};

export const capacityAPI = {
  getAnalysis: (params) => api.get('/capacity/analysis', { params }),
};

export const templateAPI = {
  getAll: (params) => api.get('/templates', { params }),
  getById: (id) => api.get(`/templates/${id}`),
  create: (data) => api.post('/templates', data),
  update: (id, data) => api.put(`/templates/${id}`, data),
  delete: (id) => api.delete(`/templates/${id}`),
  // Create a project from a template
  createProjectFromTemplate: (data) => api.post('/projects/from-template', data),
};

export const ghostStaffAPI = {
  // Get ghost staff for a project
  getByProject: (projectId, includeReplaced = false) => 
    api.get(`/projects/${projectId}/ghost-staff`, { params: { include_replaced: includeReplaced } }),
  // Get a specific ghost staff member
  getById: (ghostId) => api.get(`/ghost-staff/${ghostId}`),
  // Replace a ghost with a real staff member
  replace: (ghostId, staffId) => api.put(`/ghost-staff/${ghostId}/replace`, { staff_id: staffId }),
  // Delete a ghost staff member
  delete: (ghostId) => api.delete(`/ghost-staff/${ghostId}`),
};

export const reportsAPI = {
  // Get staff planning report for a project or project folder
  getStaffPlanningReport: (params) => api.get('/reports/staff-planning', { params }),
};

export const planningAPI = {
  // Planning Exercise CRUD
  getAll: (params) => api.get('/planning-exercises', { params }),
  getById: (id) => api.get(`/planning-exercises/${id}`),
  create: (data) => api.post('/planning-exercises', data),
  update: (id, data) => api.put(`/planning-exercises/${id}`, data),
  delete: (id) => api.delete(`/planning-exercises/${id}`),
  
  // Planning Projects
  addProject: (exerciseId, data) => api.post(`/planning-exercises/${exerciseId}/projects`, data),
  updateProject: (projectId, data) => api.put(`/planning-projects/${projectId}`, data),
  deleteProject: (projectId) => api.delete(`/planning-projects/${projectId}`),
  
  // Planning Roles
  addRole: (projectId, data) => api.post(`/planning-projects/${projectId}/roles`, data),
  updateRole: (roleId, data) => api.put(`/planning-roles/${roleId}`, data),
  deleteRole: (roleId) => api.delete(`/planning-roles/${roleId}`),
  
  // Analysis endpoints
  getAnalysis: (exerciseId) => api.get(`/planning-exercises/${exerciseId}/analysis`),
  getStaffRequirements: (exerciseId, overlapMode = 'efficient') => 
    api.get(`/planning-exercises/${exerciseId}/staff-requirements`, { params: { overlap_mode: overlapMode } }),
  getCosts: (exerciseId) => api.get(`/planning-exercises/${exerciseId}/costs`),
  
  // Apply exercise to create real projects
  apply: (exerciseId, preview = false) => 
    api.post(`/planning-exercises/${exerciseId}/apply`, { preview }),
};
