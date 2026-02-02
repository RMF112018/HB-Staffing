import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { staffAPI, roleAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { validateStaffForm } from '../utils/validation';
import './StaffForm.css';

const StaffForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = !!id;
  const { error, handleError, clearError } = useApiError();

  const [formData, setFormData] = useState({
    name: '',
    role_id: '',
    internal_hourly_cost: '',
    availability_start: '',
    availability_end: '',
    skills: []
  });
  const [roles, setRoles] = useState([]);
  const [selectedRole, setSelectedRole] = useState(null);
  const [skillInput, setSkillInput] = useState('');
  const [validationErrors, setValidationErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingRoles, setIsLoadingRoles] = useState(true);

  useEffect(() => {
    fetchRoles();
    if (isEditing) {
      fetchStaff();
    }
  }, [id]);

  const fetchRoles = async () => {
    try {
      const response = await roleAPI.getAll({ active_only: true });
      setRoles(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoadingRoles(false);
    }
  };

  const fetchStaff = async () => {
    try {
      const response = await staffAPI.getById(id);
      const staff = response.data;
      setFormData({
        name: staff.name || '',
        role_id: staff.role_id || '',
        internal_hourly_cost: staff.internal_hourly_cost || '',
        availability_start: staff.availability_start || '',
        availability_end: staff.availability_end || '',
        skills: staff.skills || []
      });
      // Find and set the selected role
      if (staff.role_id) {
        const role = roles.find(r => r.id === staff.role_id);
        setSelectedRole(role || null);
      }
    } catch (err) {
      handleError(err);
    }
  };

  // Update selected role when role_id changes
  useEffect(() => {
    if (formData.role_id && roles.length > 0) {
      const role = roles.find(r => r.id === parseInt(formData.role_id));
      setSelectedRole(role || null);
    }
  }, [formData.role_id, roles]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear validation error when field changes
    if (validationErrors[name]) {
      setValidationErrors(prev => ({
        ...prev,
        [name]: null
      }));
    }
  };

  const handleAddSkill = () => {
    const skill = skillInput.trim();
    if (skill && !formData.skills.includes(skill)) {
      setFormData(prev => ({
        ...prev,
        skills: [...prev.skills, skill]
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

  const handleSkillKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddSkill();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();

    // Validate form
    const errors = validateStaffForm(formData);
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        name: formData.name,
        role_id: parseInt(formData.role_id),
        internal_hourly_cost: parseFloat(formData.internal_hourly_cost),
        availability_start: formData.availability_start || null,
        availability_end: formData.availability_end || null,
        skills: formData.skills
      };

      if (isEditing) {
        await staffAPI.update(id, payload);
      } else {
        await staffAPI.create(payload);
      }
      navigate('/staff');
    } catch (err) {
      handleError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="staff-form">
      <h1>{isEditing ? 'Edit Staff Member' : 'Add New Staff Member'}</h1>

      {error && (
        <div className="error-message">
          <p>{error.message}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="name">Full Name *</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            className={validationErrors.name ? 'error' : ''}
          />
          {validationErrors.name && <span className="field-error">{validationErrors.name}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="role_id">Role *</label>
          <select
            id="role_id"
            name="role_id"
            value={formData.role_id}
            onChange={handleChange}
            className={validationErrors.role_id ? 'error' : ''}
            disabled={isLoadingRoles}
          >
            <option value="">Select a role...</option>
            {roles.map(role => (
              <option key={role.id} value={role.id}>
                {role.name} (${role.hourly_cost?.toFixed(2)}/hr)
              </option>
            ))}
          </select>
          {selectedRole && (
            <span className="field-hint">
              Role cost: ${selectedRole.hourly_cost?.toFixed(2)}/hr
              {selectedRole.default_billable_rate && ` | Default billable: $${selectedRole.default_billable_rate?.toFixed(2)}/hr`}
              {selectedRole.description && ` - ${selectedRole.description}`}
            </span>
          )}
          {validationErrors.role_id && <span className="field-error">{validationErrors.role_id}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="internal_hourly_cost">Internal Hourly Cost ($) *</label>
          <input
            type="number"
            id="internal_hourly_cost"
            name="internal_hourly_cost"
            value={formData.internal_hourly_cost}
            onChange={handleChange}
            min="0"
            step="0.01"
            placeholder="e.g., 75.00"
            className={validationErrors.internal_hourly_cost ? 'error' : ''}
          />
          <span className="field-hint">
            This is what you pay this staff member per hour. The billable rate comes from the role's default or project-specific rate.
          </span>
          {validationErrors.internal_hourly_cost && <span className="field-error">{validationErrors.internal_hourly_cost}</span>}
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="availability_start">Availability Start Date</label>
            <input
              type="date"
              id="availability_start"
              name="availability_start"
              value={formData.availability_start}
              onChange={handleChange}
              className={validationErrors.availability_start ? 'error' : ''}
            />
            {validationErrors.availability_start && <span className="field-error">{validationErrors.availability_start}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="availability_end">Availability End Date</label>
            <input
              type="date"
              id="availability_end"
              name="availability_end"
              value={formData.availability_end}
              onChange={handleChange}
              className={validationErrors.availability_end ? 'error' : ''}
            />
            {validationErrors.availability_end && <span className="field-error">{validationErrors.availability_end}</span>}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="skills">Skills</label>
          <div className="skills-input">
            <input
              type="text"
              id="skills"
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyPress={handleSkillKeyPress}
              placeholder="Type a skill and press Enter"
            />
            <button type="button" onClick={handleAddSkill} className="btn-secondary">Add</button>
          </div>
          {formData.skills.length > 0 && (
            <div className="skills-list">
              {formData.skills.map((skill, index) => (
                <span key={index} className="skill-tag">
                  {skill}
                  <button type="button" onClick={() => handleRemoveSkill(skill)}>&times;</button>
                </span>
              ))}
            </div>
          )}
          {validationErrors.skills && <span className="field-error">{validationErrors.skills}</span>}
        </div>

        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : (isEditing ? 'Update Staff Member' : 'Add Staff Member')}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate('/staff')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default StaffForm;
