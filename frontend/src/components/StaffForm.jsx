import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { staffAPI } from '../services/api';
import { validateStaffForm } from '../utils/validation';
import Input from './common/Input';
import DatePicker from './common/DatePicker';
import LoadingSpinner from './common/LoadingSpinner';
import ErrorMessage from './common/ErrorMessage';
import './StaffForm.css';

const StaffForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = Boolean(id);

  const [formData, setFormData] = useState({
    name: '',
    role: '',
    hourly_rate: '',
    availability_start: '',
    availability_end: '',
    skills: []
  });

  const [skillInput, setSkillInput] = useState('');
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isEditing) {
      loadStaff();
    }
  }, [id, isEditing]);

  const loadStaff = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await staffAPI.getById(id);
      const staff = response.data;

      setFormData({
        name: staff.name || '',
        role: staff.role || '',
        hourly_rate: staff.hourly_rate || '',
        availability_start: staff.availability_start || '',
        availability_end: staff.availability_end || '',
        skills: staff.skills || []
      });
    } catch (err) {
      console.error('Error loading staff:', err);
      setError('Failed to load staff member');
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

  const handleAddSkill = () => {
    if (skillInput.trim() && !formData.skills.includes(skillInput.trim())) {
      setFormData(prev => ({
        ...prev,
        skills: [...prev.skills, skillInput.trim()]
      }));
      setSkillInput('');
    }
  };

  const handleRemoveSkill = (skillToRemove) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.filter(skill => skill !== skillToRemove)
    }));
  };

  const handleSkillInputKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddSkill();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate form
    const validationErrors = validateStaffForm(formData);
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
        hourly_rate: parseFloat(formData.hourly_rate)
      };

      let response;
      if (isEditing) {
        response = await staffAPI.update(id, submitData);
      } else {
        response = await staffAPI.create(submitData);
      }

      // Navigate back to staff list
      navigate('/staff');
    } catch (err) {
      console.error('Error saving staff:', err);
      setError(err.response?.data?.message || 'Failed to save staff member');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    navigate('/staff');
  };

  if (loading) {
    return <LoadingSpinner message="Loading staff member..." />;
  }

  return (
    <div className="staff-form">
      <div className="form-header">
        <h1>{isEditing ? 'Edit Staff Member' : 'Add New Staff Member'}</h1>
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
          onRetry={isEditing ? loadStaff : null}
        />
      )}

      <form onSubmit={handleSubmit} className="staff-form-content">
        <div className="form-grid">
          <Input
            label="Name"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            error={errors.name}
            required
            placeholder="Enter full name"
            disabled={saving}
          />

          <Input
            label="Role"
            name="role"
            value={formData.role}
            onChange={handleInputChange}
            error={errors.role}
            required
            placeholder="e.g., Project Manager, Estimator"
            disabled={saving}
          />

          <Input
            label="Hourly Rate ($)"
            name="hourly_rate"
            type="number"
            step="0.01"
            min="0"
            value={formData.hourly_rate}
            onChange={handleInputChange}
            error={errors.hourly_rate}
            required
            placeholder="0.00"
            disabled={saving}
          />

          <DatePicker
            label="Availability Start Date"
            name="availability_start"
            value={formData.availability_start}
            onChange={handleInputChange}
            error={errors.availability_start}
            disabled={saving}
          />

          <DatePicker
            label="Availability End Date"
            name="availability_end"
            value={formData.availability_end}
            onChange={handleInputChange}
            error={errors.availability_end}
            disabled={saving}
          />
        </div>

        <div className="skills-section">
          <label className="skills-label">Skills *</label>

          <div className="skills-input-group">
            <Input
              name="skillInput"
              value={skillInput}
              onChange={(name, value) => setSkillInput(value)}
              placeholder="Add a skill"
              disabled={saving}
              onKeyPress={handleSkillInputKeyPress}
            />
            <button
              type="button"
              onClick={handleAddSkill}
              className="add-skill-button"
              disabled={!skillInput.trim() || saving}
            >
              Add Skill
            </button>
          </div>

          {formData.skills.length > 0 && (
            <div className="skills-list">
              {formData.skills.map((skill, index) => (
                <span key={index} className="skill-tag">
                  {skill}
                  <button
                    type="button"
                    onClick={() => handleRemoveSkill(skill)}
                    className="remove-skill-button"
                    disabled={saving}
                    aria-label={`Remove ${skill} skill`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}

          {errors.skills && (
            <span className="skills-error">{errors.skills}</span>
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
            {saving ? 'Saving...' : (isEditing ? 'Update Staff' : 'Create Staff')}
          </button>
        </div>
      </form>
    </div>
  );
};

export default StaffForm;