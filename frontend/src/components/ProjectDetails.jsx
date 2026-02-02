import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { projectAPI, assignmentAPI, staffAPI, ghostStaffAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import SkeletonLoader from './common/SkeletonLoader';
import './ProjectDetails.css';

const ProjectDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  const [project, setProject] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [subProjects, setSubProjects] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [projectRoles, setProjectRoles] = useState([]);
  const [ghostStaff, setGhostStaff] = useState([]);
  
  // Ghost staff replace state
  const [replacingGhostId, setReplacingGhostId] = useState(null);
  const [replaceStaffId, setReplaceStaffId] = useState('');
  
  // Inline assignment form state
  const [showAssignmentForm, setShowAssignmentForm] = useState(false);
  const [assignmentForm, setAssignmentForm] = useState({
    staff_id: '',
    role_on_project: '',
    start_date: '',
    end_date: '',
    hours_per_week: '40',
    allocation_type: 'full',
    allocation_percentage: '100'
  });
  const [isSubmittingAssignment, setIsSubmittingAssignment] = useState(false);

  useEffect(() => {
    fetchProjectDetails();
  }, [id]);

  const fetchProjectDetails = async () => {
    startLoading('projectDetails');
    clearError();

    try {
      // Fetch project details
      const projectResponse = await projectAPI.getById(id, true);
      setProject(projectResponse.data);

      // Fetch assignments for this project
      const assignmentsResponse = await assignmentAPI.getAll();
      const projectAssignments = assignmentsResponse.data.filter(
        a => a.project_id === parseInt(id)
      );
      setAssignments(projectAssignments);

      // If it's a folder, fetch sub-projects
      if (projectResponse.data.is_folder) {
        const subProjectsResponse = await projectAPI.getFiltered({ parent_id: id });
        setSubProjects(subProjectsResponse.data);
      }

      // Fetch staff list for assignment form
      const staffResponse = await staffAPI.getAll();
      setStaffList(staffResponse.data);

      // Fetch project role rates
      const rolesResponse = await projectAPI.getRoleRates(id);
      setProjectRoles(rolesResponse.data.all_rates || []);

      // Fetch ghost staff for this project
      try {
        const ghostResponse = await ghostStaffAPI.getByProject(id);
        setGhostStaff(ghostResponse.data.ghost_staff || []);
      } catch (ghostErr) {
        // Ghost staff is optional, don't fail if it errors
        console.error('Failed to load ghost staff:', ghostErr);
        setGhostStaff([]);
      }

    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('projectDetails');
    }
  };

  const handleAssignmentFormChange = (e) => {
    const { name, value } = e.target;
    setAssignmentForm(prev => ({ ...prev, [name]: value }));
  };

  const handleCreateAssignment = async (e) => {
    e.preventDefault();
    setIsSubmittingAssignment(true);

    try {
      const payload = {
        staff_id: parseInt(assignmentForm.staff_id),
        project_id: parseInt(id),
        role_on_project: assignmentForm.role_on_project,
        start_date: assignmentForm.start_date,
        end_date: assignmentForm.end_date,
        hours_per_week: parseFloat(assignmentForm.hours_per_week),
        allocation_type: assignmentForm.allocation_type,
        allocation_percentage: parseFloat(assignmentForm.allocation_percentage)
      };

      await assignmentAPI.create(payload);
      
      // Reset form and refresh assignments
      setAssignmentForm({
        staff_id: '',
        role_on_project: '',
        start_date: '',
        end_date: '',
        hours_per_week: '40',
        allocation_type: 'full',
        allocation_percentage: '100'
      });
      setShowAssignmentForm(false);
      
      // Refresh assignments
      const assignmentsResponse = await assignmentAPI.getAll();
      const projectAssignments = assignmentsResponse.data.filter(
        a => a.project_id === parseInt(id)
      );
      setAssignments(projectAssignments);

    } catch (err) {
      handleError(err);
    } finally {
      setIsSubmittingAssignment(false);
    }
  };

  const handleRemoveAssignment = async (assignmentId) => {
    if (!window.confirm('Are you sure you want to remove this assignment?')) {
      return;
    }

    try {
      await assignmentAPI.delete(assignmentId);
      setAssignments(assignments.filter(a => a.id !== assignmentId));
    } catch (err) {
      const message = err.response?.data?.error?.message || 'Failed to remove assignment';
      alert(message);
    }
  };

  const handleReplaceGhost = async (ghostId) => {
    if (!replaceStaffId) {
      alert('Please select a staff member');
      return;
    }

    try {
      const response = await ghostStaffAPI.replace(ghostId, parseInt(replaceStaffId));
      
      // Update ghost staff list (mark as replaced)
      setGhostStaff(ghostStaff.filter(g => g.id !== ghostId));
      
      // Add the new assignment to the list
      if (response.data.assignment) {
        setAssignments([...assignments, response.data.assignment]);
      }
      
      // Reset replace form
      setReplacingGhostId(null);
      setReplaceStaffId('');
      
      alert(`Successfully replaced "${response.data.ghost_staff.name}" with real staff member`);
    } catch (err) {
      const message = err.response?.data?.error?.message || 'Failed to replace ghost staff';
      alert(message);
    }
  };

  const handleDeleteGhost = async (ghostId, ghostName) => {
    if (!window.confirm(`Are you sure you want to delete the placeholder "${ghostName}"?`)) {
      return;
    }

    try {
      await ghostStaffAPI.delete(ghostId);
      setGhostStaff(ghostStaff.filter(g => g.id !== ghostId));
    } catch (err) {
      const message = err.response?.data?.error?.message || 'Failed to delete ghost staff';
      alert(message);
    }
  };

  const getStatusClass = (status) => {
    const statusMap = {
      'planning': 'status-planning',
      'active': 'status-active',
      'completed': 'status-completed',
      'cancelled': 'status-cancelled',
      'on-hold': 'status-on-hold'
    };
    return statusMap[status] || 'status-default';
  };

  const getAllocationLabel = (type) => {
    const labels = {
      'full': '100%',
      'split_by_projects': 'Split',
      'percentage_total': 'Fixed %',
      'percentage_monthly': 'Monthly'
    };
    return labels[type] || type;
  };

  if (isLoading('projectDetails')) {
    return (
      <div className="project-details">
        <div className="details-header">
          <SkeletonLoader width="300px" height="40px" />
        </div>
        <div className="details-content">
          <SkeletonLoader count={5} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="project-details">
        <div className="error-message">
          <p>Failed to load project: {error.message}</p>
          <button onClick={fetchProjectDetails}>Retry</button>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="project-details">
        <p>Project not found.</p>
        <Link to="/projects">Back to Projects</Link>
      </div>
    );
  }

  return (
    <div className="project-details">
      {/* Header Section */}
      <div className="details-header">
        <div className="header-info">
          <div className="breadcrumb">
            <Link to="/projects">Projects</Link>
            {project.parent_project_name && (
              <>
                <span className="separator">/</span>
                <Link to={`/projects/${project.parent_project_id}`}>
                  {project.parent_project_name}
                </Link>
              </>
            )}
            <span className="separator">/</span>
            <span className="current">{project.name}</span>
          </div>
          <h1>
            <span className="project-icon">{project.is_folder ? '📁' : '📄'}</span>
            {project.name}
          </h1>
          <span className={`status-badge ${getStatusClass(project.status)}`}>
            {project.status}
          </span>
        </div>
        <div className="header-actions">
          <Link to={`/projects/${id}/edit`} className="btn-secondary">Edit</Link>
          <Link to={`/projects/${id}/rates`} className="btn-secondary">Manage Rates</Link>
          {project.is_folder && (
            <Link to={`/projects/new?parent=${id}`} className="btn-primary">Add Sub-Project</Link>
          )}
        </div>
      </div>

      {/* Project Info Section */}
      <div className="details-section project-info-section">
        <h2>Project Information</h2>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-label">Type</span>
            <span className="info-value">{project.is_folder ? 'Project Folder' : 'Project'}</span>
          </div>
          {project.start_date && (
            <div className="info-item">
              <span className="info-label">Start Date</span>
              <span className="info-value">{project.start_date}</span>
            </div>
          )}
          {project.end_date && (
            <div className="info-item">
              <span className="info-label">End Date</span>
              <span className="info-value">{project.end_date}</span>
            </div>
          )}
          {project.budget && (
            <div className="info-item">
              <span className="info-label">Budget</span>
              <span className="info-value">${project.budget.toLocaleString()}</span>
            </div>
          )}
          {project.location && (
            <div className="info-item">
              <span className="info-label">Location</span>
              <span className="info-value">{project.location}</span>
            </div>
          )}
        </div>
      </div>

      {/* Staff Assignments Section */}
      <div className="details-section assignments-section">
        <div className="section-header">
          <h2>Staff Assignments ({assignments.length})</h2>
          <button 
            className="btn-primary"
            onClick={() => setShowAssignmentForm(!showAssignmentForm)}
          >
            {showAssignmentForm ? 'Cancel' : 'Add Staff'}
          </button>
        </div>

        {/* Inline Assignment Form */}
        {showAssignmentForm && (
          <form className="inline-assignment-form" onSubmit={handleCreateAssignment}>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="staff_id">Staff Member *</label>
                <select
                  id="staff_id"
                  name="staff_id"
                  value={assignmentForm.staff_id}
                  onChange={handleAssignmentFormChange}
                  required
                >
                  <option value="">Select staff...</option>
                  {staffList.map(staff => (
                    <option key={staff.id} value={staff.id}>
                      {staff.name} - {staff.role}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="role_on_project">Role on Project *</label>
                <select
                  id="role_on_project"
                  name="role_on_project"
                  value={assignmentForm.role_on_project}
                  onChange={handleAssignmentFormChange}
                  required
                >
                  <option value="">Select role...</option>
                  {projectRoles.map(role => (
                    <option key={role.role_id} value={role.role_name}>
                      {role.role_name} {role.billable_rate ? `($${role.billable_rate}/hr${role.is_inherited ? ' - inherited' : ''})` : '(default rate)'}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="start_date">Start Date *</label>
                <input
                  type="date"
                  id="start_date"
                  name="start_date"
                  value={assignmentForm.start_date}
                  onChange={handleAssignmentFormChange}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="end_date">End Date *</label>
                <input
                  type="date"
                  id="end_date"
                  name="end_date"
                  value={assignmentForm.end_date}
                  onChange={handleAssignmentFormChange}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="hours_per_week">Hours/Week *</label>
                <input
                  type="number"
                  id="hours_per_week"
                  name="hours_per_week"
                  value={assignmentForm.hours_per_week}
                  onChange={handleAssignmentFormChange}
                  min="1"
                  max="80"
                  required
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="allocation_type">Allocation Type</label>
                <select
                  id="allocation_type"
                  name="allocation_type"
                  value={assignmentForm.allocation_type}
                  onChange={handleAssignmentFormChange}
                >
                  <option value="full">100% (Full)</option>
                  <option value="split_by_projects">Split by Projects</option>
                  <option value="percentage_total">Fixed Percentage</option>
                </select>
              </div>

              {assignmentForm.allocation_type === 'percentage_total' && (
                <div className="form-group">
                  <label htmlFor="allocation_percentage">Allocation %</label>
                  <input
                    type="number"
                    id="allocation_percentage"
                    name="allocation_percentage"
                    value={assignmentForm.allocation_percentage}
                    onChange={handleAssignmentFormChange}
                    min="1"
                    max="100"
                  />
                </div>
              )}
            </div>

            <div className="form-actions">
              <button type="submit" className="btn-primary" disabled={isSubmittingAssignment}>
                {isSubmittingAssignment ? 'Adding...' : 'Add Assignment'}
              </button>
              <button type="button" className="btn-secondary" onClick={() => setShowAssignmentForm(false)}>
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Assignments List */}
        {assignments.length > 0 ? (
          <div className="assignments-list">
            {assignments.map(assignment => (
              <div key={assignment.id} className="assignment-card">
                <div className="assignment-info">
                  <div className="staff-name">{assignment.staff_name}</div>
                  <div className="assignment-details">
                    <span className="role">{assignment.role_on_project || 'No role specified'}</span>
                    <span className="separator">•</span>
                    <span className="hours">{assignment.hours_per_week} hrs/week</span>
                    <span className="separator">•</span>
                    <span className="allocation">{getAllocationLabel(assignment.allocation_type)} ({assignment.effective_allocation?.toFixed(0)}%)</span>
                  </div>
                  <div className="assignment-dates">
                    {assignment.start_date} → {assignment.end_date}
                  </div>
                </div>
                <div className="assignment-costs">
                  <div className="cost-item">
                    <span className="cost-label">Billable</span>
                    <span className="cost-value">${assignment.allocated_estimated_cost?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                  </div>
                  <div className="cost-item">
                    <span className="cost-label">Rate</span>
                    <span className="cost-value">${assignment.billable_rate}/hr</span>
                  </div>
                </div>
                <div className="assignment-actions">
                  <Link to={`/assignments/${assignment.id}/edit`} className="btn-small">Edit</Link>
                  <button 
                    className="btn-small btn-danger"
                    onClick={() => handleRemoveAssignment(assignment.id)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p>No staff assigned to this project yet.</p>
            <button className="btn-primary" onClick={() => setShowAssignmentForm(true)}>
              Add First Assignment
            </button>
          </div>
        )}
      </div>

      {/* Ghost Staff Section (Staff Planning) */}
      {ghostStaff.length > 0 && (
        <div className="details-section ghost-staff-section">
          <div className="section-header">
            <h2>
              <span className="ghost-icon">👻</span>
              Staff Planning ({ghostStaff.length} placeholders)
            </h2>
          </div>
          
          <p className="section-description">
            These are placeholder positions from the project template. Replace them with real staff members when hired.
          </p>

          <div className="ghost-staff-list">
            {ghostStaff.map(ghost => (
              <div key={ghost.id} className={`ghost-card ${ghost.is_replaced ? 'replaced' : ''}`}>
                <div className="ghost-info">
                  <div className="ghost-name">
                    <span className="ghost-icon-small">👻</span>
                    {ghost.name}
                  </div>
                  <div className="ghost-details">
                    <span className="role">{ghost.role_name}</span>
                    <span className="separator">•</span>
                    <span className="hours">{ghost.hours_per_week} hrs/week</span>
                    <span className="separator">•</span>
                    <span className="duration">{ghost.duration_weeks?.toFixed(1)} weeks</span>
                  </div>
                  <div className="ghost-dates">
                    {ghost.start_date} → {ghost.end_date}
                  </div>
                </div>
                <div className="ghost-costs">
                  <div className="cost-item">
                    <span className="cost-label">Internal</span>
                    <span className="cost-value">${ghost.internal_hourly_cost}/hr</span>
                  </div>
                  <div className="cost-item">
                    <span className="cost-label">Billable</span>
                    <span className="cost-value">${ghost.billable_rate || 0}/hr</span>
                  </div>
                  <div className="cost-item">
                    <span className="cost-label">Est. Cost</span>
                    <span className="cost-value">${ghost.estimated_cost?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                  </div>
                </div>
                <div className="ghost-actions">
                  {replacingGhostId === ghost.id ? (
                    <div className="replace-form">
                      <select
                        value={replaceStaffId}
                        onChange={(e) => setReplaceStaffId(e.target.value)}
                        className="replace-select"
                      >
                        <option value="">Select staff...</option>
                        {staffList.map(staff => (
                          <option key={staff.id} value={staff.id}>
                            {staff.name} - {staff.role}
                          </option>
                        ))}
                      </select>
                      <button 
                        className="btn-small btn-primary"
                        onClick={() => handleReplaceGhost(ghost.id)}
                      >
                        Confirm
                      </button>
                      <button 
                        className="btn-small"
                        onClick={() => {
                          setReplacingGhostId(null);
                          setReplaceStaffId('');
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <>
                      <button 
                        className="btn-small btn-primary"
                        onClick={() => setReplacingGhostId(ghost.id)}
                      >
                        Replace with Staff
                      </button>
                      <button 
                        className="btn-small btn-danger"
                        onClick={() => handleDeleteGhost(ghost.id, ghost.name)}
                      >
                        Delete
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sub-Projects Section (for folders only) */}
      {project.is_folder && (
        <div className="details-section sub-projects-section">
          <div className="section-header">
            <h2>Sub-Projects ({subProjects.length})</h2>
            <Link to={`/projects/new?parent=${id}`} className="btn-primary">
              Add Sub-Project
            </Link>
          </div>

          {subProjects.length > 0 ? (
            <div className="sub-projects-list">
              {subProjects.map(subProject => (
                <div key={subProject.id} className="sub-project-card">
                  <div className="sub-project-info">
                    <span className="project-icon">📄</span>
                    <div className="sub-project-details">
                      <h4>{subProject.name}</h4>
                      <div className="sub-project-meta">
                        <span className={`status-badge small ${getStatusClass(subProject.status)}`}>
                          {subProject.status}
                        </span>
                        {subProject.start_date && (
                          <span className="date-range">
                            {subProject.start_date} → {subProject.end_date || 'TBD'}
                          </span>
                        )}
                        {subProject.budget && (
                          <span className="budget">${subProject.budget.toLocaleString()}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="sub-project-actions">
                    <Link to={`/projects/${subProject.id}`} className="btn-secondary">View</Link>
                    <Link to={`/projects/${subProject.id}/edit`} className="btn-secondary">Edit</Link>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>No sub-projects in this folder yet.</p>
              <Link to={`/projects/new?parent=${id}`} className="btn-primary">
                Create First Sub-Project
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Back Navigation */}
      <div className="details-footer">
        <button className="btn-secondary" onClick={() => navigate(-1)}>
          ← Back
        </button>
      </div>
    </div>
  );
};

export default ProjectDetails;

