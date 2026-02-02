import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { projectAPI } from '../services/api';
import { validateProjectForm } from '../utils/validation';
import Input from './common/Input';
import Select from './common/Select';
import DatePicker from './common/DatePicker';
import LoadingSpinner from './common/LoadingSpinner';
import ErrorMessage from './common/ErrorMessage';
import './ProjectForm.css';

const PROJECT_STATUSES = [
  { value: 'planning', label: 'Planning' },
  { value: 'active', label: 'Active' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'on-hold', label: 'On Hold' }
];

const ProjectForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = Boolean(id);

  const [formData, setFormData] = useState({
    name: '',
    status: 'planning',
    start_date: '',
    end_date: '',
    budget: '',
    location: ''
  });

  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isEditing) {
      loadProject();
    }
  }, [id, isEditing]);

  const loadProject = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await projectAPI.getById(id);
      const project = response.data;

      setFormData({
        name: project.name || '',
        status: project.status || 'planning',
        start_date: project.start_date || '',
        end_date: project.end_date || '',
        budget: project.budget || '',
        location: project.location || ''
      });
    } catch (err) {
      console.error('Error loading project:', err);
      setError('Failed to load project');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: null
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate form
    const validationErrors = validateProjectForm(formData);
    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    try {
      setSaving(true);
      setError(null);

      // Prepare data for API
      const submitData = {
        ...formData,
        budget: formData.budget ? parseFloat(formData.budget) : null
      };

      let response;
      if (isEditing) {
        response = await projectAPI.update(id, submitData);
      } else {
        response = await projectAPI.create(submitData);
      }

      // Navigate back to projects list
      navigate('/projects');
    } catch (err) {
      console.error('Error saving project:', err);
      setError(err.response?.data?.message || 'Failed to save project');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    navigate('/projects');
  };

  if (loading) {
    return <LoadingSpinner message="Loading project..." />;
  }

  return (
    <div className="project-form">
      <div className="form-header">
        <h1>{isEditing ? 'Edit Project' : 'Create New Project'}</h1>
        <button
          type="button"
          onClick={handleCancel}
          className="cancel-button"
          disabled={saving}
        >
          Cancel
        </button>
      </div>

      {error && (
        <ErrorMessage
          message={error}
          onRetry={isEditing ? loadProject : null}
        />
      )}

      <form onSubmit={handleSubmit} className="project-form-content">
        <div className="form-grid">
          <Input
            label="Project Name"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            error={errors.name}
            required
            placeholder="Enter project name"
            disabled={saving}
          />

          <Select
            label="Status"
            name="status"
            value={formData.status}
            onChange={handleInputChange}
            options={PROJECT_STATUSES}
            error={errors.status}
            required
            disabled={saving}
          />

          <DatePicker
            label="Start Date"
            name="start_date"
            value={formData.start_date}
            onChange={handleInputChange}
            error={errors.start_date}
            disabled={saving}
          />

          <DatePicker
            label="End Date"
            name="end_date"
            value={formData.end_date}
            onChange={handleInputChange}
            error={errors.end_date}
            disabled={saving}
          />

          <Input
            label="Budget ($)"
            name="budget"
            type="number"
            step="0.01"
            min="0"
            value={formData.budget}
            onChange={handleInputChange}
            error={errors.budget}
            placeholder="0.00"
            disabled={saving}
          />

          <Input
            label="Location"
            name="location"
            value={formData.location}
            onChange={handleInputChange}
            error={errors.location}
            placeholder="Enter project location"
            disabled={saving}
          />
        </div>

        <div className="form-actions">
          <button
            type="button"
            onClick={handleCancel}
            className="cancel-button"
            disabled={saving}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="submit-button"
            disabled={saving}
          >
            {saving ? 'Saving...' : (isEditing ? 'Update Project' : 'Create Project')}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ProjectForm;