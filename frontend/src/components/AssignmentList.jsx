import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { assignmentAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import SkeletonLoader from './common/SkeletonLoader';
import './AssignmentList.css';

const AssignmentList = () => {
  const [assignments, setAssignments] = useState([]);
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  useEffect(() => {
    fetchAssignments();
  }, []);

  const fetchAssignments = async () => {
    startLoading('assignments');
    clearError();

    try {
      const response = await assignmentAPI.getAll();
      setAssignments(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('assignments');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to remove this assignment?')) {
      return;
    }

    try {
      await assignmentAPI.delete(id);
      setAssignments(assignments.filter(assignment => assignment.id !== id));
    } catch (err) {
      const message = err.response?.data?.error?.message || 'Failed to remove assignment';
      alert(message);
    }
  };

  const getRateSourceLabel = (source) => {
    switch (source) {
      case 'project_role_rate':
        return 'Project';
      case 'inherited_project_role_rate':
        return 'Inherited';
      case 'role_default_billable_rate':
        return 'Role Default';
      default:
        return '--';
    }
  };

  const getRateSourceClass = (source) => {
    switch (source) {
      case 'project_role_rate':
        return 'rate-source-project';
      case 'inherited_project_role_rate':
        return 'rate-source-inherited';
      case 'role_default_billable_rate':
        return 'rate-source-role-default';
      default:
        return '';
    }
  };

  const getAllocationTypeLabel = (type) => {
    switch (type) {
      case 'full':
        return '100%';
      case 'split_by_projects':
        return 'Split';
      case 'percentage_total':
        return 'Fixed %';
      case 'percentage_monthly':
        return 'Monthly';
      default:
        return type;
    }
  };

  const getAllocationTypeClass = (type) => {
    switch (type) {
      case 'full':
        return 'allocation-full';
      case 'split_by_projects':
        return 'allocation-split';
      case 'percentage_total':
        return 'allocation-percentage';
      case 'percentage_monthly':
        return 'allocation-monthly';
      default:
        return '';
    }
  };

  if (isLoading('assignments')) {
    return (
      <div className="assignment-list">
        <div className="header">
          <h1>Staff Assignments</h1>
          <SkeletonLoader />
        </div>
        <div className="assignment-table">
          <SkeletonLoader />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="assignment-list">
        <h1>Staff Assignments</h1>
        <div className="error-message">
          <p>Failed to load assignments: {error.message}</p>
          <button onClick={fetchAssignments}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="assignment-list">
      <div className="header">
        <h1>Staff Assignments</h1>
        <Link to="/assignments/new" className="btn-primary">Create Assignment</Link>
      </div>

      <div className="assignment-table-container">
        <table className="assignment-table">
          <thead>
            <tr>
              <th>Staff Member</th>
              <th>Project</th>
              <th>Role</th>
              <th>Dates</th>
              <th>Hours/Week</th>
              <th>Allocation</th>
              <th>Billable Rate</th>
              <th>Costs</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {assignments.map(assignment => (
              <tr key={assignment.id}>
                <td className="staff-name">{assignment.staff_name}</td>
                <td className="project-info">
                  <span className="project-path" title={assignment.project_hierarchy_path || assignment.project_name}>
                    {assignment.project_hierarchy_path || assignment.project_name}
                  </span>
                </td>
                <td className="role-name">{assignment.role_on_project || '-'}</td>
                <td className="dates">
                  <span className="date">{assignment.start_date}</span>
                  <span className="date-separator">→</span>
                  <span className="date">{assignment.end_date}</span>
                </td>
                <td className="hours">{assignment.hours_per_week}</td>
                <td className="allocation-info">
                  <span className={`allocation-type ${getAllocationTypeClass(assignment.allocation_type)}`}>
                    {getAllocationTypeLabel(assignment.allocation_type)}
                  </span>
                  <span className="effective-allocation">
                    {assignment.effective_allocation?.toFixed(0) || 100}%
                  </span>
                </td>
                <td className="billable-rate">
                  {assignment.billable_rate ? (
                    <>
                      <span className="rate">${assignment.billable_rate.toFixed(2)}</span>
                      <span className={`rate-source ${getRateSourceClass(assignment.billable_rate_source)}`}>
                        {getRateSourceLabel(assignment.billable_rate_source)}
                      </span>
                    </>
                  ) : (
                    <span className="no-rate">--</span>
                  )}
                </td>
                <td className="cost-info">
                  <div className="cost-row">
                    <span className="cost-label">Billable:</span>
                    <span className="cost allocated-cost">
                      ${assignment.allocated_estimated_cost?.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 }) || '--'}
                    </span>
                  </div>
                  <div className="cost-row">
                    <span className="cost-label">Internal:</span>
                    <span className="cost internal-cost">
                      ${assignment.allocated_internal_cost?.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 }) || '--'}
                    </span>
                  </div>
                  {assignment.allocated_estimated_cost && assignment.allocated_internal_cost && (
                    <div className="cost-row margin-row">
                      <span className="cost-label">Margin:</span>
                      <span className="cost margin-cost">
                        ${(assignment.allocated_estimated_cost - assignment.allocated_internal_cost).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                      </span>
                    </div>
                  )}
                </td>
                <td className="actions">
                  <Link to={`/assignments/${assignment.id}/edit`} className="btn-secondary">Edit</Link>
                  <button className="btn-danger" onClick={() => handleDelete(assignment.id)}>Remove</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {assignments.length === 0 && (
        <div className="empty-state">
          <p>No assignments found. <Link to="/assignments/new">Create your first assignment</Link></p>
        </div>
      )}
    </div>
  );
};

export default AssignmentList;
