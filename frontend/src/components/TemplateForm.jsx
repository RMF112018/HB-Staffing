import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { templateAPI, roleAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import './TemplateForm.css';

const TemplateForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = !!id;
  const { error, handleError, clearError } = useApiError();

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    project_type: '',
    duration_months: 12,
    is_active: true
  });

  const [templateRoles, setTemplateRoles] = useState([]);
  const [availableRoles, setAvailableRoles] = useState([]);
  const [validationErrors, setValidationErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const projectTypes = [
    'Commercial',
    'Residential',
    'Healthcare',
    'Industrial',
    'Educational',
    'Mixed-Use',
    'Renovation',
    'Infrastructure'
  ];

  useEffect(() => {
    loadInitialData();
  }, [id]);

  const loadInitialData = async () => {
    try {
      // Load available roles
      const rolesResponse = await roleAPI.getAll({ active_only: true });
      setAvailableRoles(rolesResponse.data);

      // Load template if editing
      if (isEditing) {
        const templateResponse = await templateAPI.getById(id);
        const template = templateResponse.data;
        setFormData({
          name: template.name || '',
          description: template.description || '',
          project_type: template.project_type || '',
          duration_months: template.duration_months || 12,
          is_active: template.is_active !== undefined ? template.is_active : true
        });
        setTemplateRoles(template.roles || []);
      }
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : (name === 'duration_months' ? parseInt(value) || 1 : value)
    }));

    // Clear validation error when field changes
    if (validationErrors[name]) {
      setValidationErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  const handleAddRole = () => {
    const newRole = {
      role_id: '',
      role_name: '',
      count: 1,
      start_month: 1,
      end_month: formData.duration_months,
      hours_per_week: 40
    };
    setTemplateRoles([...templateRoles, newRole]);
  };

  const handleRoleChange = (index, field, value) => {
    const updated = [...templateRoles];
    
    if (field === 'role_id') {
      const role = availableRoles.find(r => r.id === parseInt(value));
      updated[index] = {
        ...updated[index],
        role_id: parseInt(value),
        role_name: role?.name || '',
        role_hourly_cost: role?.hourly_cost,
        role_default_billable_rate: role?.default_billable_rate
      };
    } else if (['count', 'start_month', 'end_month', 'hours_per_week'].includes(field)) {
      updated[index] = {
        ...updated[index],
        [field]: field === 'hours_per_week' ? parseFloat(value) || 0 : parseInt(value) || 0
      };
    } else {
      updated[index] = { ...updated[index], [field]: value };
    }
    
    setTemplateRoles(updated);
  };

  const handleRemoveRole = (index) => {
    setTemplateRoles(templateRoles.filter((_, i) => i !== index));
  };

  const validateForm = () => {
    const errors = {};
    
    if (!formData.name.trim()) {
      errors.name = 'Template name is required';
    }
    
    if (formData.duration_months < 1) {
      errors.duration_months = 'Duration must be at least 1 month';
    }

    // Validate roles
    templateRoles.forEach((role, index) => {
      if (!role.role_id) {
        errors[`role_${index}_role_id`] = 'Please select a role';
      }
      if (role.count < 1) {
        errors[`role_${index}_count`] = 'Count must be at least 1';
      }
      if (role.start_month < 1 || role.start_month > formData.duration_months) {
        errors[`role_${index}_start_month`] = `Start month must be between 1 and ${formData.duration_months}`;
      }
      if (role.end_month && (role.end_month < role.start_month || role.end_month > formData.duration_months)) {
        errors[`role_${index}_end_month`] = `End month must be between ${role.start_month} and ${formData.duration_months}`;
      }
      if (role.hours_per_week < 1 || role.hours_per_week > 80) {
        errors[`role_${index}_hours_per_week`] = 'Hours must be between 1 and 80';
      }
    });

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        name: formData.name.trim(),
        description: formData.description.trim() || null,
        project_type: formData.project_type || null,
        duration_months: formData.duration_months,
        is_active: formData.is_active,
        roles: templateRoles.map(role => ({
          role_id: role.role_id,
          count: role.count,
          start_month: role.start_month,
          end_month: role.end_month || null,
          hours_per_week: role.hours_per_week
        }))
      };

      if (isEditing) {
        await templateAPI.update(id, payload);
      } else {
        await templateAPI.create(payload);
      }
      
      navigate('/templates');
    } catch (err) {
      handleError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const calculateTotalStaff = () => {
    return templateRoles.reduce((sum, role) => sum + (role.count || 0), 0);
  };

  const calculateEstimatedCost = () => {
    let totalCost = 0;
    templateRoles.forEach(role => {
      const rate = role.role_default_billable_rate || role.role_hourly_cost || 0;
      const duration = (role.end_month || formData.duration_months) - role.start_month + 1;
      const weeksInDuration = duration * 4.33; // Approximate weeks per month
      const totalHours = weeksInDuration * role.hours_per_week * role.count;
      totalCost += totalHours * rate;
    });
    return totalCost;
  };

  if (isLoading) {
    return (
      <div className="template-form">
        <h1>{isEditing ? 'Edit Template' : 'Create Template'}</h1>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="template-form">
      <h1>{isEditing ? 'Edit Template' : 'Create New Template'}</h1>

      <div className="form-info">
        <p>
          Define a reusable project structure with predefined roles and durations. 
          When you create a project from this template, ghost staff placeholders will be automatically generated.
        </p>
      </div>

      {error && (
        <div className="error-message">
          <p>{error.message}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-section">
          <h2>Template Details</h2>
          
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="name">Template Name *</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g., Medium Commercial Project"
                className={validationErrors.name ? 'error' : ''}
              />
              {validationErrors.name && <span className="field-error">{validationErrors.name}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="project_type">Project Type</label>
              <select
                id="project_type"
                name="project_type"
                value={formData.project_type}
                onChange={handleChange}
              >
                <option value="">Select type...</option>
                {projectTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              placeholder="Describe when this template should be used..."
              rows="3"
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="duration_months">Duration (Months) *</label>
              <input
                type="number"
                id="duration_months"
                name="duration_months"
                value={formData.duration_months}
                onChange={handleChange}
                min="1"
                max="120"
                className={validationErrors.duration_months ? 'error' : ''}
              />
              {validationErrors.duration_months && <span className="field-error">{validationErrors.duration_months}</span>}
            </div>

            <div className="form-group checkbox-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="is_active"
                  checked={formData.is_active}
                  onChange={handleChange}
                />
                <span className="checkbox-text">Active Template</span>
              </label>
              <span className="field-hint">Inactive templates won't appear in the template selection.</span>
            </div>
          </div>
        </div>

        <div className="form-section">
          <div className="section-header">
            <h2>Required Roles</h2>
            <button type="button" className="btn-secondary" onClick={handleAddRole}>
              + Add Role
            </button>
          </div>

          {templateRoles.length === 0 ? (
            <div className="empty-roles">
              <p>No roles defined yet. Add roles to specify staffing requirements.</p>
              <button type="button" className="btn-primary" onClick={handleAddRole}>
                Add First Role
              </button>
            </div>
          ) : (
            <div className="roles-list">
              {templateRoles.map((role, index) => (
                <div key={index} className="role-item">
                  <div className="role-header">
                    <span className="role-number">Role {index + 1}</span>
                    <button 
                      type="button" 
                      className="btn-remove"
                      onClick={() => handleRemoveRole(index)}
                    >
                      ×
                    </button>
                  </div>

                  <div className="role-fields">
                    <div className="form-group">
                      <label>Role *</label>
                      <select
                        value={role.role_id || ''}
                        onChange={(e) => handleRoleChange(index, 'role_id', e.target.value)}
                        className={validationErrors[`role_${index}_role_id`] ? 'error' : ''}
                      >
                        <option value="">Select role...</option>
                        {availableRoles.map(r => (
                          <option key={r.id} value={r.id}>
                            {r.name} (${r.hourly_cost}/hr)
                          </option>
                        ))}
                      </select>
                      {validationErrors[`role_${index}_role_id`] && (
                        <span className="field-error">{validationErrors[`role_${index}_role_id`]}</span>
                      )}
                    </div>

                    <div className="form-group small">
                      <label>Count *</label>
                      <input
                        type="number"
                        value={role.count}
                        onChange={(e) => handleRoleChange(index, 'count', e.target.value)}
                        min="1"
                        max="50"
                        className={validationErrors[`role_${index}_count`] ? 'error' : ''}
                      />
                      {validationErrors[`role_${index}_count`] && (
                        <span className="field-error">{validationErrors[`role_${index}_count`]}</span>
                      )}
                    </div>

                    <div className="form-group small">
                      <label>Start Month *</label>
                      <input
                        type="number"
                        value={role.start_month}
                        onChange={(e) => handleRoleChange(index, 'start_month', e.target.value)}
                        min="1"
                        max={formData.duration_months}
                        className={validationErrors[`role_${index}_start_month`] ? 'error' : ''}
                      />
                      {validationErrors[`role_${index}_start_month`] && (
                        <span className="field-error">{validationErrors[`role_${index}_start_month`]}</span>
                      )}
                    </div>

                    <div className="form-group small">
                      <label>End Month</label>
                      <input
                        type="number"
                        value={role.end_month || ''}
                        onChange={(e) => handleRoleChange(index, 'end_month', e.target.value)}
                        min={role.start_month}
                        max={formData.duration_months}
                        placeholder="End"
                        className={validationErrors[`role_${index}_end_month`] ? 'error' : ''}
                      />
                      {validationErrors[`role_${index}_end_month`] && (
                        <span className="field-error">{validationErrors[`role_${index}_end_month`]}</span>
                      )}
                    </div>

                    <div className="form-group small">
                      <label>Hrs/Week</label>
                      <input
                        type="number"
                        value={role.hours_per_week}
                        onChange={(e) => handleRoleChange(index, 'hours_per_week', e.target.value)}
                        min="1"
                        max="80"
                        className={validationErrors[`role_${index}_hours_per_week`] ? 'error' : ''}
                      />
                      {validationErrors[`role_${index}_hours_per_week`] && (
                        <span className="field-error">{validationErrors[`role_${index}_hours_per_week`]}</span>
                      )}
                    </div>
                  </div>

                  {role.role_id && (
                    <div className="role-summary">
                      <span>Duration: {(role.end_month || formData.duration_months) - role.start_month + 1} months</span>
                      {role.role_default_billable_rate && (
                        <span>Billable: ${role.role_default_billable_rate}/hr</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {templateRoles.length > 0 && (
          <div className="template-summary">
            <h3>Template Summary</h3>
            <div className="summary-stats">
              <div className="summary-stat">
                <span className="stat-value">{formData.duration_months}</span>
                <span className="stat-label">Months</span>
              </div>
              <div className="summary-stat">
                <span className="stat-value">{templateRoles.length}</span>
                <span className="stat-label">Roles</span>
              </div>
              <div className="summary-stat">
                <span className="stat-value">{calculateTotalStaff()}</span>
                <span className="stat-label">Staff Needed</span>
              </div>
              <div className="summary-stat">
                <span className="stat-value">${calculateEstimatedCost().toLocaleString()}</span>
                <span className="stat-label">Est. Cost</span>
              </div>
            </div>
          </div>
        )}

        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : (isEditing ? 'Update Template' : 'Create Template')}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate('/templates')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default TemplateForm;

