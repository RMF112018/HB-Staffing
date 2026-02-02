import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { roleAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import './RoleForm.css';

const RoleForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = !!id;
  const { error, handleError, clearError } = useApiError();

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    hourly_cost: '',
    default_billable_rate: '',
    is_active: true
  });
  const [validationErrors, setValidationErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isEditing) {
      fetchRole();
    }
  }, [id]);

  const fetchRole = async () => {
    try {
      const response = await roleAPI.getById(id);
      const role = response.data;
      setFormData({
        name: role.name || '',
        description: role.description || '',
        hourly_cost: role.hourly_cost || '',
        default_billable_rate: role.default_billable_rate || '',
        is_active: role.is_active !== undefined ? role.is_active : true
      });
    } catch (err) {
      handleError(err);
    }
  };

  const validateForm = () => {
    const errors = {};

    if (!formData.name || formData.name.trim().length === 0) {
      errors.name = 'Role name is required';
    } else if (formData.name.trim().length > 100) {
      errors.name = 'Role name must be 100 characters or less';
    }

    if (!formData.hourly_cost || formData.hourly_cost === '') {
      errors.hourly_cost = 'Hourly cost is required';
    } else {
      const cost = parseFloat(formData.hourly_cost);
      if (isNaN(cost) || cost <= 0) {
        errors.hourly_cost = 'Hourly cost must be a positive number';
      }
    }

    // Validate default_billable_rate if provided
    if (formData.default_billable_rate && formData.default_billable_rate !== '') {
      const rate = parseFloat(formData.default_billable_rate);
      if (isNaN(rate) || rate <= 0) {
        errors.default_billable_rate = 'Default billable rate must be a positive number';
      }
    }

    return errors;
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    // Clear validation error when field changes
    if (validationErrors[name]) {
      setValidationErrors(prev => ({
        ...prev,
        [name]: null
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();

    // Validate form
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        name: formData.name.trim(),
        description: formData.description.trim() || null,
        hourly_cost: parseFloat(formData.hourly_cost),
        default_billable_rate: formData.default_billable_rate ? parseFloat(formData.default_billable_rate) : null,
        is_active: formData.is_active
      };

      if (isEditing) {
        await roleAPI.update(id, payload);
      } else {
        await roleAPI.create(payload);
      }
      navigate('/roles');
    } catch (err) {
      handleError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="role-form">
      <h1>{isEditing ? 'Edit Role' : 'Create New Role'}</h1>

      <div className="form-info">
        <p>
          Roles define position titles with associated internal hourly costs. 
          Staff members will be assigned to these roles when they are added or updated.
        </p>
      </div>

      {error && (
        <div className="error-message">
          <p>{error.message}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="name">Role Name *</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="e.g., Project Manager, Senior Estimator"
            className={validationErrors.name ? 'error' : ''}
          />
          {validationErrors.name && <span className="field-error">{validationErrors.name}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Brief description of this role's responsibilities"
            rows="3"
          />
        </div>

        <div className="form-group">
          <label htmlFor="hourly_cost">Internal Hourly Cost ($) *</label>
          <input
            type="number"
            id="hourly_cost"
            name="hourly_cost"
            value={formData.hourly_cost}
            onChange={handleChange}
            min="0"
            step="0.01"
            placeholder="e.g., 75.00"
            className={validationErrors.hourly_cost ? 'error' : ''}
          />
          <span className="field-hint">
            This is the internal company cost per hour for this role. 
            Staff billable rates may differ.
          </span>
          {validationErrors.hourly_cost && <span className="field-error">{validationErrors.hourly_cost}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="default_billable_rate">Default Billable Rate ($)</label>
          <input
            type="number"
            id="default_billable_rate"
            name="default_billable_rate"
            value={formData.default_billable_rate}
            onChange={handleChange}
            min="0"
            step="0.01"
            placeholder="e.g., 95.00"
            className={validationErrors.default_billable_rate ? 'error' : ''}
          />
          <span className="field-hint">
            Default billable rate for new projects. When a new project is created, 
            this role will be automatically added with this rate (editable per project).
          </span>
          {validationErrors.default_billable_rate && <span className="field-error">{validationErrors.default_billable_rate}</span>}
        </div>

        <div className="form-group checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              name="is_active"
              checked={formData.is_active}
              onChange={handleChange}
            />
            <span className="checkbox-text">Active Role</span>
          </label>
          <span className="field-hint">
            Inactive roles will not appear as options when creating new staff members.
          </span>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : (isEditing ? 'Update Role' : 'Create Role')}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate('/roles')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default RoleForm;

