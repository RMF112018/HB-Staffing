import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { assignmentAPI, staffAPI, projectAPI } from '../services/api';
import { validateAssignmentForm } from '../utils/validation';
import Select from './common/Select';
import DatePicker from './common/DatePicker';
import Input from './common/Input';
import LoadingSpinner from './common/LoadingSpinner';
import ErrorMessage from './common/ErrorMessage';
import './AssignmentForm.css';

const AssignmentForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = Boolean(id);

  const [formData, setFormData] = useState({
    staff_id: '',
    project_id: '',
    start_date: '',
    end_date: '',
    hours_per_week: '40',
    role_on_project: ''
  });

  const [staffOptions, setStaffOptions] = useState([]);
  const [projectOptions, setProjectOptions] = useState([]);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [loadingOptions, setLoadingOptions] = useState(true);

  useEffect(() => {
    loadOptions();
    if (isEditing) {
      loadAssignment();
    }
  }, [id, isEditing]);

  const loadOptions = async () => {
    try {
      setLoadingOptions(true);
      const [staffResponse, projectsResponse] = await Promise.all([
        staffAPI.getAll(),
        projectAPI.getAll()
      ]);

      // Format staff options
      const staffOpts = staffResponse.data.map(staff => ({
        value: staff.id,
        label: `${staff.name} (${staff.role})`
      }));
      setStaffOptions(staffOpts);

      // Format project options
      const projectOpts = projectsResponse.data.map(project => ({
        value: project.id,
        label: `${project.name} (${project.status})`
      }));
      setProjectOptions(projectOpts);
    } catch (err) {
      console.error('Error loading options:', err);
      setError('Failed to load form options');
    } finally {
      setLoadingOptions(false);
    }
  };

  const loadAssignment = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await assignmentAPI.getById(id);
      const assignment = response.data;

      setFormData({
        staff_id: assignment.staff_id || '',
        project_id: assignment.project_id || '',
        start_date: assignment.start_date || '',
        end_date: assignment.end_date || '',
        hours_per_week: assignment.hours_per_week || '40',
        role_on_project: assignment.role_on_project || ''
      });
    } catch (err) {
      console.error('Error loading assignment:', err);
      setError('Failed to load assignment');
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
    const validationErrors = validateAssignmentForm(formData);
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
        hours_per_week: parseFloat(formData.hours_per_week)
      };

      let response;
      if (isEditing) {
        response = await assignmentAPI.update(id, submitData);
      } else {
        response = await assignmentAPI.create(submitData);
      }

      // Navigate back to assignments list
      navigate('/assignments');
    } catch (err) {
      console.error('Error saving assignment:', err);
      setError(err.response?.data?.message || 'Failed to save assignment');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    navigate('/assignments');
  };

  if (loading || loadingOptions) {
    return <LoadingSpinner message={loading ? "Loading assignment..." : "Loading form options..."} />;
  }

  return (
    <div className="assignment-form">
      <div className="form-header">
        <h1>{isEditing ? 'Edit Assignment' : 'Create New Assignment'}</h1>
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
          onRetry={isEditing ? loadAssignment : loadOptions}
        />
      )}

      <form onSubmit={handleSubmit} className="assignment-form-content">
        <div className="form-grid">
          <Select
            label="Staff Member"
            name="staff_id"
            value={formData.staff_id}
            onChange={handleInputChange}
            options={staffOptions}
            error={errors.staff_id}
            required
            disabled={saving}
            placeholder="Select a staff member"
          />

          <Select
            label="Project"
            name="project_id"
            value={formData.project_id}
            onChange={handleInputChange}
            options={projectOptions}
            error={errors.project_id}
            required
            disabled={saving}
            placeholder="Select a project"
          />

          <DatePicker
            label="Start Date"
            name="start_date"
            value={formData.start_date}
            onChange={handleInputChange}
            error={errors.start_date}
            required
            disabled={saving}
          />

          <DatePicker
            label="End Date"
            name="end_date"
            value={formData.end_date}
            onChange={handleInputChange}
            error={errors.end_date}
            required
            disabled={saving}
          />

          <Input
            label="Hours per Week"
            name="hours_per_week"
            type="number"
            step="0.5"
            min="0.5"
            max="80"
            value={formData.hours_per_week}
            onChange={handleInputChange}
            error={errors.hours_per_week}
            required
            placeholder="40"
            disabled={saving}
          />

          <Input
            label="Role on Project"
            name="role_on_project"
            value={formData.role_on_project}
            onChange={handleInputChange}
            error={errors.role_on_project}
            placeholder="e.g., Lead Estimator, Project Manager"
            disabled={saving}
          />
        </div>

        <div className="assignment-preview">
          <h3>Assignment Preview</h3>
          {formData.staff_id && formData.project_id && (
            <div className="preview-content">
              <p>
                <strong>Staff:</strong> {staffOptions.find(s => s.value === parseInt(formData.staff_id))?.label || 'Unknown'}
              </p>
              <p>
                <strong>Project:</strong> {projectOptions.find(p => p.value === parseInt(formData.project_id))?.label || 'Unknown'}
              </p>
              {formData.start_date && formData.end_date && (
                <p>
                  <strong>Duration:</strong> {formData.start_date} to {formData.end_date}
                </p>
              )}
              <p>
                <strong>Hours per Week:</strong> {formData.hours_per_week}
              </p>
              {formData.role_on_project && (
                <p>
                  <strong>Role:</strong> {formData.role_on_project}
                </p>
              )}
            </div>
          )}
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
            {saving ? 'Saving...' : (isEditing ? 'Update Assignment' : 'Create Assignment')}
          </button>
        </div>
      </form>
    </div>
  );
};

export default AssignmentForm;