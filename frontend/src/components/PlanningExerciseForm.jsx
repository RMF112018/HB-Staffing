import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { planningAPI, roleAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import './PlanningExerciseForm.css';

const PlanningExerciseForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = !!id;
  const { error, handleError, clearError } = useApiError();

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [roles, setRoles] = useState([]);

  // Exercise data
  const [exerciseData, setExerciseData] = useState({
    name: '',
    description: '',
    status: 'draft'
  });

  // Projects within the exercise
  const [projects, setProjects] = useState([]);

  // Expanded state for project panels
  const [expandedProjects, setExpandedProjects] = useState({});

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Load roles
      const rolesResponse = await roleAPI.getAll({ active_only: true });
      setRoles(rolesResponse.data);

      // If editing, load existing exercise
      if (isEditing) {
        const exerciseResponse = await planningAPI.getById(id);
        const exercise = exerciseResponse.data;
        
        setExerciseData({
          name: exercise.name || '',
          description: exercise.description || '',
          status: exercise.status || 'draft'
        });

        if (exercise.projects && exercise.projects.length > 0) {
          setProjects(exercise.projects.map(p => ({
            id: p.id,
            name: p.name,
            start_date: p.start_date,
            duration_months: p.duration_months,
            location: p.location || '',
            budget: p.budget || '',
            roles: p.roles || []
          })));
          
          // Expand first project by default
          setExpandedProjects({ [exercise.projects[0].id || 0]: true });
        }
      }
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExerciseChange = (field, value) => {
    setExerciseData(prev => ({ ...prev, [field]: value }));
  };

  const addProject = () => {
    const newProject = {
      id: `new_${Date.now()}`,
      name: '',
      start_date: '',
      duration_months: 12,
      location: '',
      budget: '',
      roles: []
    };
    setProjects([...projects, newProject]);
    setExpandedProjects({ ...expandedProjects, [newProject.id]: true });
  };

  const removeProject = (projectId) => {
    setProjects(projects.filter(p => p.id !== projectId));
    const { [projectId]: _, ...rest } = expandedProjects;
    setExpandedProjects(rest);
  };

  const updateProject = (projectId, field, value) => {
    setProjects(projects.map(p => 
      p.id === projectId ? { ...p, [field]: value } : p
    ));
  };

  const toggleProjectExpanded = (projectId) => {
    setExpandedProjects(prev => ({
      ...prev,
      [projectId]: !prev[projectId]
    }));
  };

  const addRole = (projectId) => {
    const project = projects.find(p => p.id === projectId);
    if (!project) return;

    const newRole = {
      id: `new_${Date.now()}`,
      role_id: '',
      count: 1,
      start_month_offset: 0,
      end_month_offset: 0,
      allocation_percentage: 100,
      hours_per_week: 40,
      overlap_mode: 'efficient'
    };

    updateProject(projectId, 'roles', [...project.roles, newRole]);
  };

  const removeRole = (projectId, roleId) => {
    const project = projects.find(p => p.id === projectId);
    if (!project) return;

    updateProject(projectId, 'roles', project.roles.filter(r => r.id !== roleId));
  };

  const updateRole = (projectId, roleId, field, value) => {
    const project = projects.find(p => p.id === projectId);
    if (!project) return;

    const updatedRoles = project.roles.map(r =>
      r.id === roleId ? { ...r, [field]: value } : r
    );
    updateProject(projectId, 'roles', updatedRoles);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();

    // Basic validation
    if (!exerciseData.name.trim()) {
      alert('Please enter an exercise name');
      return;
    }

    if (projects.length === 0) {
      alert('Please add at least one project');
      return;
    }

    // Validate projects
    for (const project of projects) {
      if (!project.name.trim()) {
        alert('Please enter a name for all projects');
        return;
      }
      if (!project.start_date) {
        alert(`Please select a start date for "${project.name}"`);
        return;
      }
      if (project.roles.length === 0) {
        alert(`Please add at least one role to "${project.name}"`);
        return;
      }
      for (const role of project.roles) {
        if (!role.role_id) {
          alert(`Please select a role type for all roles in "${project.name}"`);
          return;
        }
      }
    }

    setIsSubmitting(true);

    try {
      // Prepare payload
      const payload = {
        name: exerciseData.name,
        description: exerciseData.description,
        status: exerciseData.status,
        projects: projects.map(p => ({
          id: typeof p.id === 'number' ? p.id : undefined,
          name: p.name,
          start_date: p.start_date,
          duration_months: parseInt(p.duration_months) || 12,
          location: p.location || null,
          budget: p.budget ? parseFloat(p.budget) : null,
          roles: p.roles.map(r => ({
            id: typeof r.id === 'number' ? r.id : undefined,
            role_id: parseInt(r.role_id),
            count: parseInt(r.count) || 1,
            start_month_offset: parseInt(r.start_month_offset) || 0,
            end_month_offset: parseInt(r.end_month_offset) || 0,
            allocation_percentage: parseFloat(r.allocation_percentage) || 100,
            hours_per_week: parseFloat(r.hours_per_week) || 40,
            overlap_mode: r.overlap_mode || 'efficient'
          }))
        }))
      };

      if (isEditing) {
        await planningAPI.update(id, payload);
      } else {
        await planningAPI.create(payload);
      }

      navigate('/planning');
    } catch (err) {
      handleError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getRoleName = (roleId) => {
    const role = roles.find(r => r.id === parseInt(roleId));
    return role?.name || 'Select role';
  };

  if (isLoading) {
    return (
      <div className="planning-exercise-form">
        <h1>{isEditing ? 'Edit Planning Exercise' : 'Create Planning Exercise'}</h1>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="planning-exercise-form">
      <div className="form-header">
        <h1>{isEditing ? 'Edit Planning Exercise' : 'Create Planning Exercise'}</h1>
        <button type="button" className="btn-secondary" onClick={() => navigate('/planning')}>
          Cancel
        </button>
      </div>

      {error && (
        <div className="error-message">
          <p>{error.message}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Exercise Details */}
        <div className="form-section">
          <h2>Exercise Details</h2>
          
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="name">Exercise Name *</label>
              <input
                type="text"
                id="name"
                value={exerciseData.name}
                onChange={(e) => handleExerciseChange('name', e.target.value)}
                placeholder="e.g., Q3 2026 Program Planning"
              />
            </div>
            
            <div className="form-group small">
              <label htmlFor="status">Status</label>
              <select
                id="status"
                value={exerciseData.status}
                onChange={(e) => handleExerciseChange('status', e.target.value)}
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={exerciseData.description}
              onChange={(e) => handleExerciseChange('description', e.target.value)}
              rows={3}
              placeholder="Optional description of this planning exercise..."
            />
          </div>
        </div>

        {/* Projects Section */}
        <div className="form-section projects-section">
          <div className="section-header">
            <h2>Projects ({projects.length})</h2>
            <button type="button" className="btn-add" onClick={addProject}>
              + Add Project
            </button>
          </div>

          {projects.length === 0 && (
            <div className="empty-projects">
              <p>No projects added yet. Add at least one project to continue.</p>
            </div>
          )}

          {projects.map((project, projectIndex) => (
            <div key={project.id} className="project-panel">
              <div 
                className="project-header"
                onClick={() => toggleProjectExpanded(project.id)}
              >
                <div className="project-header-left">
                  <span className="expand-icon">
                    {expandedProjects[project.id] ? '▼' : '▶'}
                  </span>
                  <span className="project-number">Project {projectIndex + 1}</span>
                  <span className="project-title">
                    {project.name || '(Untitled)'}
                  </span>
                </div>
                <div className="project-header-right">
                  <span className="role-count">{project.roles.length} role(s)</span>
                  <button
                    type="button"
                    className="btn-remove"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeProject(project.id);
                    }}
                  >
                    ✕
                  </button>
                </div>
              </div>

              {expandedProjects[project.id] && (
                <div className="project-content">
                  <div className="form-row">
                    <div className="form-group">
                      <label>Project Name *</label>
                      <input
                        type="text"
                        value={project.name}
                        onChange={(e) => updateProject(project.id, 'name', e.target.value)}
                        placeholder="e.g., Downtown Tower Phase 1"
                      />
                    </div>
                    <div className="form-group small">
                      <label>Start Date *</label>
                      <input
                        type="date"
                        value={project.start_date}
                        onChange={(e) => updateProject(project.id, 'start_date', e.target.value)}
                      />
                    </div>
                    <div className="form-group small">
                      <label>Duration (months)</label>
                      <input
                        type="number"
                        value={project.duration_months}
                        onChange={(e) => updateProject(project.id, 'duration_months', e.target.value)}
                        min="1"
                        max="120"
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Location</label>
                      <input
                        type="text"
                        value={project.location}
                        onChange={(e) => updateProject(project.id, 'location', e.target.value)}
                        placeholder="e.g., San Francisco, CA"
                      />
                    </div>
                    <div className="form-group small">
                      <label>Budget ($)</label>
                      <input
                        type="number"
                        value={project.budget}
                        onChange={(e) => updateProject(project.id, 'budget', e.target.value)}
                        min="0"
                        step="1000"
                        placeholder="Optional"
                      />
                    </div>
                  </div>

                  {/* Roles Section */}
                  <div className="roles-section">
                    <div className="roles-header">
                      <h4>Required Roles</h4>
                      <button
                        type="button"
                        className="btn-add-small"
                        onClick={() => addRole(project.id)}
                      >
                        + Add Role
                      </button>
                    </div>

                    {project.roles.length === 0 && (
                      <p className="empty-roles">Add roles to define staffing requirements.</p>
                    )}

                    {project.roles.map((role, roleIndex) => (
                      <div key={role.id} className="role-row">
                        <div className="role-number">{roleIndex + 1}</div>
                        
                        <div className="role-field">
                          <label>Role *</label>
                          <select
                            value={role.role_id}
                            onChange={(e) => updateRole(project.id, role.id, 'role_id', e.target.value)}
                          >
                            <option value="">Select role</option>
                            {roles.map(r => (
                              <option key={r.id} value={r.id}>
                                {r.name} (${r.hourly_cost}/hr)
                              </option>
                            ))}
                          </select>
                        </div>

                        <div className="role-field small">
                          <label>Count</label>
                          <input
                            type="number"
                            value={role.count}
                            onChange={(e) => updateRole(project.id, role.id, 'count', e.target.value)}
                            min="1"
                            max="50"
                          />
                        </div>

                        <div className="role-field small">
                          <label>Start Month</label>
                          <input
                            type="number"
                            value={role.start_month_offset}
                            onChange={(e) => updateRole(project.id, role.id, 'start_month_offset', e.target.value)}
                            min="-12"
                            max="120"
                            title="Negative values = before project start (pre-construction)"
                          />
                        </div>

                        <div className="role-field small">
                          <label>End Month</label>
                          <input
                            type="number"
                            value={role.end_month_offset}
                            onChange={(e) => updateRole(project.id, role.id, 'end_month_offset', e.target.value)}
                            min="-12"
                            max="24"
                            title="Relative to project end (positive = close-out)"
                          />
                        </div>

                        <div className="role-field small">
                          <label>Alloc %</label>
                          <input
                            type="number"
                            value={role.allocation_percentage}
                            onChange={(e) => updateRole(project.id, role.id, 'allocation_percentage', e.target.value)}
                            min="0"
                            max="100"
                          />
                        </div>

                        <div className="role-field">
                          <label>Overlap Mode</label>
                          <select
                            value={role.overlap_mode}
                            onChange={(e) => updateRole(project.id, role.id, 'overlap_mode', e.target.value)}
                          >
                            <option value="efficient">Efficient (share staff)</option>
                            <option value="conservative">Conservative (dedicated)</option>
                          </select>
                        </div>

                        <button
                          type="button"
                          className="btn-remove-role"
                          onClick={() => removeRole(project.id, role.id)}
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Form Actions */}
        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : (isEditing ? 'Update Exercise' : 'Create Exercise')}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate('/planning')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default PlanningExerciseForm;

