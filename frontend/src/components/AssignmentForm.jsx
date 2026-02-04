import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { assignmentAPI, staffAPI, projectAPI, forecastAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { validateAssignmentForm } from '../utils/validation';
import './AssignmentForm.css';

// Allocation type options
const ALLOCATION_TYPES = [
  { value: 'full', label: '100% (Full Allocation)' },
  { value: 'split_by_projects', label: 'Split by Projects (Auto-calculated)' },
  { value: 'percentage_total', label: '% of Total (Single percentage)' },
  { value: 'percentage_monthly', label: '% by Month (Different per month)' }
];

// Helper to generate months between two dates
const generateMonthRange = (startDate, endDate) => {
  if (!startDate || !endDate) return [];
  
  const months = [];
  const start = new Date(startDate);
  const end = new Date(endDate);
  
  // Start from the first of the start month
  let current = new Date(start.getFullYear(), start.getMonth(), 1);
  const endMonth = new Date(end.getFullYear(), end.getMonth(), 1);
  
  while (current <= endMonth) {
    months.push({
      date: current.toISOString().slice(0, 10), // YYYY-MM-DD format
      label: current.toLocaleDateString('en-US', { year: 'numeric', month: 'long' }),
      allocation_percentage: 100
    });
    current = new Date(current.getFullYear(), current.getMonth() + 1, 1);
  }
  
  return months;
};

// Debounce helper
const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
};

const AssignmentForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = !!id;
  const { error, handleError, clearError } = useApiError();

  const [formData, setFormData] = useState({
    staff_id: '',
    project_id: '',
    start_date: '',
    end_date: '',
    hours_per_week: '40',
    role_on_project: '',
    allocation_type: 'full',
    allocation_percentage: '100',
    allow_over_allocation: false
  });
  const [monthlyAllocations, setMonthlyAllocations] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [projectList, setProjectList] = useState([]);
  const [projectRoles, setProjectRoles] = useState([]);
  const [selectedProjectInfo, setSelectedProjectInfo] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingRoles, setIsLoadingRoles] = useState(false);
  
  // Over-allocation state
  const [allocationValidation, setAllocationValidation] = useState(null);
  const [isCheckingAllocation, setIsCheckingAllocation] = useState(false);

  // Debounced values for allocation check
  const debouncedStaffId = useDebounce(formData.staff_id, 300);
  const debouncedStartDate = useDebounce(formData.start_date, 300);
  const debouncedEndDate = useDebounce(formData.end_date, 300);
  const debouncedAllocationPercentage = useDebounce(formData.allocation_percentage, 300);
  const debouncedAllocationType = useDebounce(formData.allocation_type, 300);

  useEffect(() => {
    loadOptions();
  }, []);

  useEffect(() => {
    if (isEditing && staffList.length > 0 && projectList.length > 0) {
      fetchAssignment();
    }
  }, [id, staffList, projectList]);

  // Load project role rates when project changes
  useEffect(() => {
    if (formData.project_id) {
      loadProjectRoles(formData.project_id);
    } else {
      setProjectRoles([]);
      setSelectedProjectInfo(null);
    }
  }, [formData.project_id]);

  // Update monthly allocations when dates change and allocation type is percentage_monthly
  useEffect(() => {
    if (formData.allocation_type === 'percentage_monthly' && formData.start_date && formData.end_date) {
      const newMonths = generateMonthRange(formData.start_date, formData.end_date);
      // Preserve existing allocation percentages where months match
      setMonthlyAllocations(prevAllocations => {
        return newMonths.map(month => {
          const existing = prevAllocations.find(ma => ma.date === month.date);
          return existing ? { ...month, allocation_percentage: existing.allocation_percentage } : month;
        });
      });
    }
  }, [formData.start_date, formData.end_date, formData.allocation_type]);

  // Check for over-allocation when relevant fields change
  useEffect(() => {
    if (debouncedStaffId && debouncedStartDate && debouncedEndDate) {
      checkAllocationConflicts();
    } else {
      setAllocationValidation(null);
    }
  }, [debouncedStaffId, debouncedStartDate, debouncedEndDate, debouncedAllocationPercentage, debouncedAllocationType]);

  const checkAllocationConflicts = async () => {
    if (!formData.staff_id || !formData.start_date || !formData.end_date) {
      return;
    }

    setIsCheckingAllocation(true);
    try {
      // Determine allocation percentage based on type
      let allocationPct = parseFloat(formData.allocation_percentage) || 100;
      if (formData.allocation_type === 'full') {
        allocationPct = 100;
      } else if (formData.allocation_type === 'split_by_projects') {
        // For split, estimate based on current setting
        allocationPct = parseFloat(formData.allocation_percentage) || 50;
      }

      const response = await forecastAPI.validateAllocation({
        staff_id: parseInt(formData.staff_id),
        start_date: formData.start_date,
        end_date: formData.end_date,
        allocation_percentage: allocationPct,
        exclude_assignment_id: isEditing ? parseInt(id) : null
      });
      
      setAllocationValidation(response.data);
    } catch (err) {
      console.error('Failed to validate allocation:', err);
      setAllocationValidation(null);
    } finally {
      setIsCheckingAllocation(false);
    }
  };

  const loadOptions = async () => {
    try {
      const [staffResponse, projectResponse] = await Promise.all([
        staffAPI.getAll(),
        projectAPI.getAll()
      ]);
      setStaffList(staffResponse.data);
      setProjectList(projectResponse.data);
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadProjectRoles = async (projectId) => {
    setIsLoadingRoles(true);
    try {
      const response = await projectAPI.getRoleRates(projectId);
      setProjectRoles(response.data.all_rates || []);
      setSelectedProjectInfo({
        name: response.data.project_name,
        is_folder: response.data.is_folder,
        parent_project_id: response.data.parent_project_id
      });
    } catch (err) {
      console.error('Failed to load project roles:', err);
      setProjectRoles([]);
    } finally {
      setIsLoadingRoles(false);
    }
  };

  const fetchAssignment = async () => {
    try {
      const response = await assignmentAPI.getById(id, true);
      const assignment = response.data;
      setFormData({
        staff_id: assignment.staff_id?.toString() || '',
        project_id: assignment.project_id?.toString() || '',
        start_date: assignment.start_date || '',
        end_date: assignment.end_date || '',
        hours_per_week: assignment.hours_per_week?.toString() || '40',
        role_on_project: assignment.role_on_project || '',
        allocation_type: assignment.allocation_type || 'full',
        allocation_percentage: assignment.allocation_percentage?.toString() || '100',
        allow_over_allocation: assignment.allow_over_allocation || false
      });
      
      // Load monthly allocations if type is percentage_monthly
      if (assignment.allocation_type === 'percentage_monthly' && assignment.monthly_allocations) {
        setMonthlyAllocations(assignment.monthly_allocations.map(ma => ({
          date: ma.month,
          label: new Date(ma.month).toLocaleDateString('en-US', { year: 'numeric', month: 'long' }),
          allocation_percentage: ma.allocation_percentage
        })));
      }
    } catch (err) {
      handleError(err);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : value;
    
    setFormData(prev => ({
      ...prev,
      [name]: newValue
    }));
    
    // Clear validation error when field changes
    if (validationErrors[name]) {
      setValidationErrors(prev => ({
        ...prev,
        [name]: null
      }));
    }
  };

  const handleMonthlyAllocationChange = (monthDate, value) => {
    const numValue = Math.min(100, Math.max(0, parseFloat(value) || 0));
    setMonthlyAllocations(prev => 
      prev.map(ma => 
        ma.date === monthDate 
          ? { ...ma, allocation_percentage: numValue }
          : ma
      )
    );
  };

  const setAllMonthlyAllocations = (value) => {
    const numValue = Math.min(100, Math.max(0, parseFloat(value) || 0));
    setMonthlyAllocations(prev => 
      prev.map(ma => ({ ...ma, allocation_percentage: numValue }))
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();

    // Validate form
    const errors = validateAssignmentForm(formData);
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }

    // Check for over-allocation warning
    if (allocationValidation && !allocationValidation.is_valid && !formData.allow_over_allocation) {
      setValidationErrors({
        ...validationErrors,
        allocation: 'Please enable over-allocation override or adjust the dates/allocation to resolve conflicts.'
      });
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        staff_id: parseInt(formData.staff_id),
        project_id: parseInt(formData.project_id),
        start_date: formData.start_date,
        end_date: formData.end_date,
        hours_per_week: parseFloat(formData.hours_per_week),
        role_on_project: formData.role_on_project || null,
        allocation_type: formData.allocation_type,
        allocation_percentage: parseFloat(formData.allocation_percentage),
        allow_over_allocation: formData.allow_over_allocation
      };

      // Include monthly allocations if type is percentage_monthly
      if (formData.allocation_type === 'percentage_monthly' && monthlyAllocations.length > 0) {
        payload.monthly_allocations = monthlyAllocations.map(ma => ({
          month: ma.date,
          allocation_percentage: ma.allocation_percentage
        }));
      }

      if (isEditing) {
        await assignmentAPI.update(id, payload);
        // Update monthly allocations separately if needed
        if (formData.allocation_type === 'percentage_monthly' && monthlyAllocations.length > 0) {
          await assignmentAPI.updateMonthlyAllocations(id, monthlyAllocations.map(ma => ({
            month: ma.date,
            allocation_percentage: ma.allocation_percentage
          })));
        }
      } else {
        await assignmentAPI.create(payload);
      }
      navigate('/assignments');
    } catch (err) {
      handleError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Build hierarchical project options
  const buildProjectOptions = () => {
    const options = [];
    const topLevel = projectList.filter(p => !p.parent_project_id);
    
    const addProject = (project, depth = 0) => {
      const prefix = depth > 0 ? '└─ '.padStart(depth * 3 + 3, '   ') : '';
      const icon = project.is_folder ? '📁' : '📄';
      options.push({
        id: project.id,
        label: `${prefix}${icon} ${project.name}`,
        status: project.status,
        is_folder: project.is_folder
      });
      
      // Add sub-projects
      const subProjects = projectList.filter(p => p.parent_project_id === project.id);
      subProjects.forEach(sub => addProject(sub, depth + 1));
    };
    
    topLevel.forEach(project => addProject(project));
    return options;
  };

  // Get billable rate for selected role
  const getSelectedRoleRate = () => {
    if (!formData.role_on_project || projectRoles.length === 0) return null;
    const role = projectRoles.find(r => r.role_name === formData.role_on_project);
    return role?.billable_rate;
  };

  // Get the selected staff member's name
  const getSelectedStaffName = () => {
    const staff = staffList.find(s => s.id.toString() === formData.staff_id);
    return staff?.name || 'staff member';
  };

  if (isLoading) {
    return (
      <div className="assignment-form">
        <h1>{isEditing ? 'Edit Assignment' : 'Create New Assignment'}</h1>
        <p>Loading...</p>
      </div>
    );
  }

  const projectOptions = buildProjectOptions();
  const selectedRoleRate = getSelectedRoleRate();

  return (
    <div className="assignment-form">
      <h1>{isEditing ? 'Edit Assignment' : 'Create New Assignment'}</h1>

      {error && (
        <div className="error-message">
          <p>{error.message}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="staff_id">Staff Member *</label>
          <select
            id="staff_id"
            name="staff_id"
            value={formData.staff_id}
            onChange={handleChange}
            className={validationErrors.staff_id ? 'error' : ''}
          >
            <option value="">Select staff member</option>
            {staffList.map(staff => (
              <option key={staff.id} value={staff.id}>
                {staff.name} - {staff.role} (${staff.internal_hourly_cost}/hr cost)
              </option>
            ))}
          </select>
          {validationErrors.staff_id && <span className="field-error">{validationErrors.staff_id}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="project_id">Project *</label>
          <select
            id="project_id"
            name="project_id"
            value={formData.project_id}
            onChange={handleChange}
            className={validationErrors.project_id ? 'error' : ''}
          >
            <option value="">Select project</option>
            {projectOptions.map(project => (
              <option key={project.id} value={project.id}>
                {project.label} ({project.status})
              </option>
            ))}
          </select>
          {validationErrors.project_id && <span className="field-error">{validationErrors.project_id}</span>}
          {selectedProjectInfo && selectedProjectInfo.is_folder && (
            <p className="help-text">
              ⚠️ Assigning to a project folder. Consider assigning to a specific sub-project instead.
            </p>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="role_on_project">Role on Project *</label>
          {isLoadingRoles ? (
            <p className="loading-text">Loading roles...</p>
          ) : projectRoles.length > 0 ? (
            <>
              <select
                id="role_on_project"
                name="role_on_project"
                value={formData.role_on_project}
                onChange={handleChange}
                className={validationErrors.role_on_project ? 'error' : ''}
              >
                <option value="">Select role</option>
                {projectRoles.filter(r => r.billable_rate !== null).map(role => (
                  <option key={role.role_id} value={role.role_name}>
                    {role.role_name} - ${role.billable_rate?.toFixed(2)}/hr
                    {role.is_inherited ? ' (inherited)' : ''}
                  </option>
                ))}
              </select>
              {selectedRoleRate && (
                <p className="rate-info">
                  <strong>Billable Rate:</strong> ${selectedRoleRate.toFixed(2)}/hr
                </p>
              )}
            </>
          ) : (
            <input
              type="text"
              id="role_on_project"
              name="role_on_project"
              value={formData.role_on_project}
              onChange={handleChange}
              placeholder="e.g., Project Manager - Level 2"
              className={validationErrors.role_on_project ? 'error' : ''}
            />
          )}
          {!formData.project_id && (
            <p className="help-text">Select a project to see available roles with rates.</p>
          )}
          {validationErrors.role_on_project && <span className="field-error">{validationErrors.role_on_project}</span>}
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="start_date">Start Date *</label>
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
            <label htmlFor="end_date">End Date *</label>
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
        </div>

        <div className="form-group">
          <label htmlFor="hours_per_week">Hours per Week *</label>
          <input
            type="number"
            id="hours_per_week"
            name="hours_per_week"
            value={formData.hours_per_week}
            onChange={handleChange}
            min="0.5"
            max="80"
            step="0.5"
            className={validationErrors.hours_per_week ? 'error' : ''}
          />
          {validationErrors.hours_per_week && <span className="field-error">{validationErrors.hours_per_week}</span>}
        </div>

        {/* Allocation Section */}
        <div className="allocation-section">
          <h3>Allocation Settings</h3>
          
          <div className="form-group">
            <label htmlFor="allocation_type">Allocation Type</label>
            <select
              id="allocation_type"
              name="allocation_type"
              value={formData.allocation_type}
              onChange={handleChange}
            >
              {ALLOCATION_TYPES.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
            <p className="help-text">
              {formData.allocation_type === 'full' && 'Staff member is 100% allocated to this assignment.'}
              {formData.allocation_type === 'split_by_projects' && 'Allocation is auto-calculated based on concurrent assignments.'}
              {formData.allocation_type === 'percentage_total' && 'Set a single percentage for the entire assignment duration.'}
              {formData.allocation_type === 'percentage_monthly' && 'Set different allocation percentages for each month.'}
            </p>
          </div>

          {/* Show percentage input for percentage_total type */}
          {formData.allocation_type === 'percentage_total' && (
            <div className="form-group">
              <label htmlFor="allocation_percentage">Allocation Percentage (%)</label>
              <input
                type="number"
                id="allocation_percentage"
                name="allocation_percentage"
                value={formData.allocation_percentage}
                onChange={handleChange}
                min="0"
                max="100"
                step="1"
              />
            </div>
          )}

          {/* Show monthly allocation table for percentage_monthly type */}
          {formData.allocation_type === 'percentage_monthly' && (
            <div className="monthly-allocations">
              <div className="monthly-allocations-header">
                <h4>Monthly Allocations</h4>
                <div className="bulk-actions">
                  <button type="button" className="btn-small" onClick={() => setAllMonthlyAllocations(100)}>
                    Set All 100%
                  </button>
                  <button type="button" className="btn-small" onClick={() => setAllMonthlyAllocations(50)}>
                    Set All 50%
                  </button>
                </div>
              </div>
              
              {monthlyAllocations.length === 0 ? (
                <p className="help-text">
                  Set start and end dates to configure monthly allocations.
                </p>
              ) : (
                <table className="monthly-allocations-table">
                  <thead>
                    <tr>
                      <th>Month</th>
                      <th>Allocation %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthlyAllocations.map(month => (
                      <tr key={month.date}>
                        <td>{month.label}</td>
                        <td>
                          <input
                            type="number"
                            value={month.allocation_percentage}
                            onChange={(e) => handleMonthlyAllocationChange(month.date, e.target.value)}
                            min="0"
                            max="100"
                            step="1"
                            className="allocation-input"
                          />
                          <span className="percent-symbol">%</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* Over-Allocation Warning */}
          {isCheckingAllocation && (
            <div className="allocation-check-loading">
              Checking allocation conflicts...
            </div>
          )}

          {allocationValidation && !allocationValidation.is_valid && !isCheckingAllocation && (
            <div className="over-allocation-warning">
              <div className="warning-header">
                <span className="warning-icon">⚠️</span>
                <h4>Over-Allocation Warning</h4>
              </div>
              <p className="warning-message">
                This assignment would cause <strong>{getSelectedStaffName()}</strong> to exceed 100% allocation 
                in <strong>{allocationValidation.conflict_count}</strong> month(s).
              </p>
              
              <div className="conflict-details">
                <h5>Conflicts:</h5>
                <ul className="conflict-list">
                  {allocationValidation.conflicts.slice(0, 5).map((conflict, idx) => (
                    <li key={idx} className="conflict-item">
                      <span className="month">{conflict.month}</span>
                      <span className="allocation">
                        {conflict.existing_allocation.toFixed(0)}% existing + {conflict.new_allocation}% new 
                        = <strong>{conflict.projected_total.toFixed(0)}%</strong>
                      </span>
                      <span className="over-by">(+{conflict.over_allocation_amount.toFixed(0)}% over)</span>
                    </li>
                  ))}
                  {allocationValidation.conflicts.length > 5 && (
                    <li className="more-conflicts">
                      ... and {allocationValidation.conflicts.length - 5} more month(s)
                    </li>
                  )}
                </ul>
              </div>

              {allocationValidation.conflicts[0]?.existing_assignments?.length > 0 && (
                <div className="existing-assignments-info">
                  <h5>Existing Assignments:</h5>
                  <ul>
                    {allocationValidation.conflicts[0].existing_assignments.map((a, idx) => (
                      <li key={idx}>
                        {a.project_name} ({a.allocation_percentage}%)
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="override-option">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="allow_over_allocation"
                    checked={formData.allow_over_allocation}
                    onChange={handleChange}
                  />
                  <span className="checkbox-text">
                    I understand and want to allow this over-allocation
                  </span>
                </label>
              </div>
            </div>
          )}

          {allocationValidation && allocationValidation.is_valid && !isCheckingAllocation && formData.staff_id && (
            <div className="allocation-ok">
              <span className="ok-icon">✅</span>
              <span>No allocation conflicts detected</span>
            </div>
          )}

          {validationErrors.allocation && (
            <span className="field-error">{validationErrors.allocation}</span>
          )}
        </div>

        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : (isEditing ? 'Update Assignment' : 'Create Assignment')}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate('/assignments')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default AssignmentForm;
