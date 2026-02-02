import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { projectAPI, templateAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { validateProjectForm } from '../utils/validation';
import './ProjectForm.css';

const ProjectForm = () => {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const isEditing = !!id;
  const { error, handleError, clearError } = useApiError();

  // Get URL parameters for pre-filling
  const urlParentId = searchParams.get('parent');
  const urlType = searchParams.get('type');

  const [formData, setFormData] = useState({
    name: '',
    start_date: '',
    end_date: '',
    duration_value: '',
    duration_unit: 'months', // 'weeks', 'months', 'years'
    status: 'planning',
    budget: '',
    location: '',
    is_folder: urlType === 'folder',
    parent_project_id: urlParentId || ''
  });
  const [folders, setFolders] = useState([]);
  const [calculatedDuration, setCalculatedDuration] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingFolders, setIsLoadingFolders] = useState(true);
  
  // Template state
  const [useTemplate, setUseTemplate] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);

  // Duration unit options
  const durationUnitOptions = [
    { value: 'weeks', label: 'Weeks' },
    { value: 'months', label: 'Months' },
    { value: 'years', label: 'Years' }
  ];

  const statusOptions = [
    { value: 'planning', label: 'Planning' },
    { value: 'active', label: 'Active' },
    { value: 'completed', label: 'Completed' },
    { value: 'cancelled', label: 'Cancelled' },
    { value: 'on-hold', label: 'On Hold' }
  ];

  // Helper function to calculate end date from start date and duration
  const calculateEndDate = (startDate, durationValue, durationUnit) => {
    if (!startDate || !durationValue || durationValue <= 0) return null;
    
    const start = new Date(startDate);
    const duration = parseFloat(durationValue);
    
    let endDate = new Date(start);
    
    switch (durationUnit) {
      case 'weeks':
        endDate.setDate(start.getDate() + Math.round(duration * 7));
        break;
      case 'months':
        endDate.setMonth(start.getMonth() + Math.floor(duration));
        // Handle fractional months (as days)
        const fractionalDays = Math.round((duration % 1) * 30);
        endDate.setDate(endDate.getDate() + fractionalDays);
        break;
      case 'years':
        endDate.setFullYear(start.getFullYear() + Math.floor(duration));
        // Handle fractional years (as months)
        const fractionalMonths = Math.round((duration % 1) * 12);
        endDate.setMonth(endDate.getMonth() + fractionalMonths);
        break;
      default:
        return null;
    }
    
    // Format as YYYY-MM-DD for input[type="date"]
    return endDate.toISOString().split('T')[0];
  };

  // Helper function to calculate duration in months between two dates
  const calculateDurationInMonths = (startDate, endDate) => {
    if (!startDate || !endDate) return null;
    
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    if (end <= start) return null;
    
    // Calculate total months with fractional part
    const yearsDiff = end.getFullYear() - start.getFullYear();
    const monthsDiff = end.getMonth() - start.getMonth();
    const daysDiff = end.getDate() - start.getDate();
    
    // Get days in the end month for fractional calculation
    const daysInEndMonth = new Date(end.getFullYear(), end.getMonth() + 1, 0).getDate();
    
    let totalMonths = yearsDiff * 12 + monthsDiff;
    // Add fractional month based on days
    totalMonths += daysDiff / daysInEndMonth;
    
    // Round to 1 decimal place
    return Math.round(totalMonths * 10) / 10;
  };

  useEffect(() => {
    fetchFolders();
    if (isEditing) {
      fetchProject();
    }
  }, [id]);

  // Fetch templates when useTemplate is enabled
  useEffect(() => {
    if (useTemplate && templates.length === 0) {
      fetchTemplates();
    }
  }, [useTemplate]);

  // Load template details when selected
  useEffect(() => {
    if (selectedTemplateId) {
      loadTemplateDetails(selectedTemplateId);
    } else {
      setSelectedTemplate(null);
    }
  }, [selectedTemplateId]);

  const fetchTemplates = async () => {
    setIsLoadingTemplates(true);
    try {
      const response = await templateAPI.getAll({ active_only: true });
      setTemplates(response.data);
    } catch (err) {
      console.error('Failed to load templates:', err);
    } finally {
      setIsLoadingTemplates(false);
    }
  };

  const loadTemplateDetails = async (templateId) => {
    try {
      const response = await templateAPI.getById(templateId);
      setSelectedTemplate(response.data);
      
      // Auto-fill duration from template
      if (response.data.duration_months) {
        setFormData(prev => ({
          ...prev,
          duration_value: response.data.duration_months.toString(),
          duration_unit: 'months'
        }));
        
        // If start date exists, calculate end date
        if (formData.start_date) {
          const calculatedEnd = calculateEndDate(formData.start_date, response.data.duration_months, 'months');
          if (calculatedEnd) {
            setFormData(prev => ({ ...prev, end_date: calculatedEnd }));
          }
        }
      }
    } catch (err) {
      console.error('Failed to load template details:', err);
    }
  };

  const fetchFolders = async () => {
    try {
      const response = await projectAPI.getFolders();
      // Filter out the current project if editing (can't be parent of itself)
      const availableFolders = id 
        ? response.data.filter(f => f.id !== parseInt(id))
        : response.data;
      setFolders(availableFolders);
    } catch (err) {
      // Non-critical error, don't block the form
      console.error('Failed to load folders:', err);
    } finally {
      setIsLoadingFolders(false);
    }
  };

  const fetchProject = async () => {
    try {
      const response = await projectAPI.getById(id);
      const project = response.data;
      setFormData({
        name: project.name || '',
        start_date: project.start_date || '',
        end_date: project.end_date || '',
        duration_value: '',
        duration_unit: 'months',
        status: project.status || 'planning',
        budget: project.budget || '',
        location: project.location || '',
        is_folder: project.is_folder || false,
        parent_project_id: project.parent_project_id || ''
      });
      
      // Calculate initial duration if both dates exist
      if (project.start_date && project.end_date) {
        const duration = calculateDurationInMonths(project.start_date, project.end_date);
        setCalculatedDuration(duration);
      }
    } catch (err) {
      handleError(err);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : value;
    
    setFormData(prev => {
      const updated = { ...prev, [name]: newValue };
      
      // If changing to folder, clear parent_project_id
      if (name === 'is_folder' && checked) {
        updated.parent_project_id = '';
      }
      
      // Handle bidirectional date/duration calculations
      if (name === 'start_date' || name === 'duration_value' || name === 'duration_unit') {
        // When start date or duration changes, calculate end date
        const startDate = name === 'start_date' ? newValue : prev.start_date;
        const durationVal = name === 'duration_value' ? newValue : prev.duration_value;
        const durationUnit = name === 'duration_unit' ? newValue : prev.duration_unit;
        
        if (startDate && durationVal && parseFloat(durationVal) > 0) {
          const calculatedEnd = calculateEndDate(startDate, durationVal, durationUnit);
          if (calculatedEnd) {
            updated.end_date = calculatedEnd;
          }
        }
      }
      
      // When end_date is manually changed, calculate duration in months
      if (name === 'end_date') {
        // Clear duration_value to indicate manual entry
        updated.duration_value = '';
      }
      
      return updated;
    });
    
    // Update calculated duration when both dates are set
    if (name === 'end_date' || name === 'start_date') {
      setTimeout(() => {
        setFormData(current => {
          const duration = calculateDurationInMonths(current.start_date, current.end_date);
          setCalculatedDuration(duration);
          return current;
        });
      }, 0);
    }
    
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
    const errors = validateProjectForm(formData);
    
    // Additional validation for template
    if (useTemplate && !selectedTemplateId) {
      errors.template = 'Please select a template';
    }
    if (useTemplate && !formData.start_date) {
      errors.start_date = 'Start date is required when using a template';
    }
    
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }

    setIsSubmitting(true);

    try {
      let result;
      
      if (useTemplate && selectedTemplateId && !isEditing) {
        // Create project from template
        const templatePayload = {
          template_id: parseInt(selectedTemplateId),
          name: formData.name,
          start_date: formData.start_date,
          status: formData.status,
          budget: formData.budget ? parseFloat(formData.budget) : null,
          location: formData.location || null,
          parent_project_id: formData.parent_project_id ? parseInt(formData.parent_project_id) : null,
          is_folder: formData.is_folder
        };
        
        result = await templateAPI.createProjectFromTemplate(templatePayload);
        
        // Navigate to the new project's details page to see ghost staff
        navigate(`/projects/${result.data.project.id}`);
      } else {
        // Standard project creation/update
        const payload = {
          name: formData.name,
          start_date: formData.start_date || null,
          end_date: formData.end_date || null,
          status: formData.status,
          budget: formData.budget ? parseFloat(formData.budget) : null,
          location: formData.location || null,
          is_folder: formData.is_folder,
          parent_project_id: formData.parent_project_id ? parseInt(formData.parent_project_id) : null
        };

        if (isEditing) {
          await projectAPI.update(id, payload);
        } else {
          await projectAPI.create(payload);
        }
        navigate('/projects');
      }
    } catch (err) {
      handleError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getFormTitle = () => {
    if (isEditing) {
      return formData.is_folder ? 'Edit Project Folder' : 'Edit Project';
    }
    if (formData.is_folder) {
      return 'Create Project Folder';
    }
    if (formData.parent_project_id) {
      return 'Create Sub-Project';
    }
    return 'Create New Project';
  };

  return (
    <div className="project-form">
      <h1>{getFormTitle()}</h1>

      {error && (
        <div className="error-message">
          <p>{error.message}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Template Toggle (only for new projects) */}
        {!isEditing && (
          <div className="template-section">
            <div className="form-group type-toggle">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={useTemplate}
                  onChange={(e) => {
                    setUseTemplate(e.target.checked);
                    if (!e.target.checked) {
                      setSelectedTemplateId('');
                      setSelectedTemplate(null);
                    }
                  }}
                />
                <span className="checkbox-text">
                  📋 Create from Template
                </span>
              </label>
              <p className="help-text">
                Use a predefined project template with staffing requirements.
              </p>
            </div>

            {useTemplate && (
              <div className="template-selection">
                <div className="form-group">
                  <label htmlFor="template_id">Select Template *</label>
                  <select
                    id="template_id"
                    value={selectedTemplateId}
                    onChange={(e) => setSelectedTemplateId(e.target.value)}
                    disabled={isLoadingTemplates}
                    className={validationErrors.template ? 'error' : ''}
                  >
                    <option value="">-- Choose a Template --</option>
                    {templates.map(template => (
                      <option key={template.id} value={template.id}>
                        {template.name} ({template.duration_months} months, {template.role_count} roles)
                      </option>
                    ))}
                  </select>
                  {validationErrors.template && <span className="field-error">{validationErrors.template}</span>}
                </div>

                {selectedTemplate && (
                  <div className="template-preview">
                    <h4>Template: {selectedTemplate.name}</h4>
                    {selectedTemplate.description && (
                      <p className="template-description">{selectedTemplate.description}</p>
                    )}
                    <div className="template-stats">
                      <span><strong>Duration:</strong> {selectedTemplate.duration_months} months</span>
                      <span><strong>Type:</strong> {selectedTemplate.project_type || 'General'}</span>
                    </div>
                    {selectedTemplate.roles && selectedTemplate.roles.length > 0 && (
                      <div className="template-roles">
                        <strong>Staffing Requirements:</strong>
                        <ul>
                          {selectedTemplate.roles.map((role, idx) => (
                            <li key={idx}>
                              {role.count}x {role.role_name} 
                              <span className="role-timing">
                                (Month {role.start_month}{role.end_month ? `-${role.end_month}` : '+'}, {role.hours_per_week}hrs/wk)
                              </span>
                            </li>
                          ))}
                        </ul>
                        <p className="ghost-notice">
                          ⚠️ Ghost staff placeholders will be created for these roles.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Project Type Toggle */}
        <div className="form-group type-toggle">
          <label className="checkbox-label">
            <input
              type="checkbox"
              name="is_folder"
              checked={formData.is_folder}
              onChange={handleChange}
              disabled={isEditing && formData.sub_projects_count > 0}
            />
            <span className="checkbox-text">
              📁 This is a project folder (can contain sub-projects)
            </span>
          </label>
          {formData.is_folder && (
            <p className="help-text">
              Project folders organize related sub-projects and define default billable rates.
            </p>
          )}
        </div>

        {/* Parent Project Selection (only for non-folders) */}
        {!formData.is_folder && (
          <div className="form-group">
            <label htmlFor="parent_project_id">Parent Folder (Optional)</label>
            <select
              id="parent_project_id"
              name="parent_project_id"
              value={formData.parent_project_id}
              onChange={handleChange}
              disabled={isLoadingFolders}
            >
              <option value="">-- Standalone Project (No Parent) --</option>
              {folders.map(folder => (
                <option key={folder.id} value={folder.id}>
                  📁 {folder.name}
                </option>
              ))}
            </select>
            {formData.parent_project_id && (
              <p className="help-text">
                This project will inherit billable rates from the parent folder.
              </p>
            )}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="name">{formData.is_folder ? 'Folder Name' : 'Project Name'} *</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder={formData.is_folder ? 'e.g., Downtown Development' : 'e.g., Phase 1 - Foundation'}
            className={validationErrors.name ? 'error' : ''}
          />
          {validationErrors.name && <span className="field-error">{validationErrors.name}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="status">Status *</label>
          <select
            id="status"
            name="status"
            value={formData.status}
            onChange={handleChange}
            className={validationErrors.status ? 'error' : ''}
          >
            {statusOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {validationErrors.status && <span className="field-error">{validationErrors.status}</span>}
        </div>

        {/* Date and Duration Section */}
        <div className="date-duration-section">
          <div className="form-group">
            <label htmlFor="start_date">Start Date</label>
            <input
              type="date"
              id="start_date"
              name="start_date"
              value={formData.start_date}
              onChange={handleChange}
              className={validationErrors.start_date ? 'error' : ''}
            />
            {validationErrors.start_date && <span className="field-error">{validationErrors.start_date}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="duration_value">Duration</label>
            <div className="duration-row">
              <input
                type="number"
                id="duration_value"
                name="duration_value"
                value={formData.duration_value}
                onChange={handleChange}
                min="0"
                step="0.5"
                placeholder="Enter duration"
                className="duration-input"
              />
              <select
                id="duration_unit"
                name="duration_unit"
                value={formData.duration_unit}
                onChange={handleChange}
                className="duration-unit"
              >
                {durationUnitOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <p className="help-text duration-help">
              Enter duration to auto-calculate end date, or set dates manually.
            </p>
          </div>

          <div className="form-group">
            <label htmlFor="end_date">End Date</label>
            <input
              type="date"
              id="end_date"
              name="end_date"
              value={formData.end_date}
              onChange={handleChange}
              className={validationErrors.end_date ? 'error' : ''}
            />
            {validationErrors.end_date && <span className="field-error">{validationErrors.end_date}</span>}
          </div>

          {/* Calculated Duration Display */}
          {calculatedDuration !== null && formData.start_date && formData.end_date && (
            <div className="calculated-duration">
              <span className="duration-label">Project Duration:</span>
              <span className="duration-value">{calculatedDuration} months</span>
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="budget">Budget ($)</label>
          <input
            type="number"
            id="budget"
            name="budget"
            value={formData.budget}
            onChange={handleChange}
            min="0"
            step="0.01"
            placeholder="Enter budget amount"
            className={validationErrors.budget ? 'error' : ''}
          />
          {validationErrors.budget && <span className="field-error">{validationErrors.budget}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="location">Location</label>
          <input
            type="text"
            id="location"
            name="location"
            value={formData.location}
            onChange={handleChange}
            placeholder="e.g., Downtown City Center"
          />
        </div>

        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : (isEditing ? 'Update' : 'Create')}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate('/projects')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default ProjectForm;
