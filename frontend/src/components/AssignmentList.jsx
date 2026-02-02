import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { assignmentAPI } from '../services/api';
import DataTable from './common/DataTable';
import LoadingSpinner from './common/LoadingSpinner';
import ErrorMessage from './common/ErrorMessage';
import './AssignmentList.css';

const AssignmentList = () => {
  const navigate = useNavigate();
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAssignments();
  }, []);

  const loadAssignments = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await assignmentAPI.getAll();
      setAssignments(response.data);
    } catch (err) {
      console.error('Error loading assignments:', err);
      setError('Failed to load assignments');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (assignment) => {
    navigate(`/assignments/${assignment.id}/edit`);
  };

  const handleDelete = async (assignment) => {
    if (window.confirm(`Are you sure you want to delete this assignment?`)) {
      try {
        await assignmentAPI.delete(assignment.id);
        setAssignments(prev => prev.filter(a => a.id !== assignment.id));
      } catch (err) {
        console.error('Error deleting assignment:', err);
        setError('Failed to delete assignment');
      }
    }
  };

  const handleCreateNew = () => {
    navigate('/assignments/new');
  };

  const formatDateRange = (startDate, endDate) => {
    if (!startDate || !endDate) return 'N/A';
    const start = new Date(startDate).toLocaleDateString();
    const end = new Date(endDate).toLocaleDateString();
    return `${start} - ${end}`;
  };

  const getDurationWeeks = (startDate, endDate) => {
    if (!startDate || !endDate) return 'N/A';
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end - start);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    const weeks = Math.ceil(diffDays / 7);
    return `${weeks} week${weeks !== 1 ? 's' : ''}`;
  };

  const columns = [
    {
      key: 'staff_name',
      label: 'Staff Member',
      sortable: true
    },
    {
      key: 'project_name',
      label: 'Project',
      sortable: true
    },
    {
      key: 'role_on_project',
      label: 'Role',
      sortable: true,
      render: (role) => role || 'Not specified'
    },
    {
      key: 'start_date',
      label: 'Date Range',
      sortable: true,
      render: (startDate, assignment) => formatDateRange(startDate, assignment.end_date)
    },
    {
      key: 'hours_per_week',
      label: 'Hours/Week',
      sortable: true,
      align: 'center'
    },
    {
      key: 'start_date',
      label: 'Duration',
      render: (startDate, assignment) => getDurationWeeks(startDate, assignment.end_date)
    }
  ];

  // Group assignments by project for summary
  const assignmentsByProject = assignments.reduce((acc, assignment) => {
    const projectName = assignment.project_name || 'Unknown Project';
    if (!acc[projectName]) {
      acc[projectName] = [];
    }
    acc[projectName].push(assignment);
    return acc;
  }, {});

  if (loading) {
    return <LoadingSpinner message="Loading assignments..." />;
  }

  return (
    <div className="assignment-list">
      <div className="list-header">
        <h1>Staff Assignments</h1>
        <button onClick={handleCreateNew} className="create-button">
          Create Assignment
        </button>
      </div>

      {error && (
        <ErrorMessage
          message={error}
          onRetry={loadAssignments}
        />
      )}

      <div className="assignment-summary">
        <div className="summary-card">
          <h3>Total Assignments</h3>
          <div className="summary-value">{assignments.length}</div>
        </div>
        <div className="summary-card">
          <h3>Active Projects</h3>
          <div className="summary-value">{Object.keys(assignmentsByProject).length}</div>
        </div>
        <div className="summary-card">
          <h3>Total Hours/Week</h3>
          <div className="summary-value">
            {assignments.reduce((total, assignment) => total + assignment.hours_per_week, 0)}
          </div>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={assignments}
        onEdit={handleEdit}
        onDelete={handleDelete}
        loading={loading}
        emptyMessage="No assignments found"
        searchPlaceholder="Search assignments..."
        className="assignment-table"
      />

      {Object.keys(assignmentsByProject).length > 0 && (
        <div className="assignment-breakdown">
          <h2>Assignments by Project</h2>
          <div className="project-breakdown">
            {Object.entries(assignmentsByProject).map(([projectName, projectAssignments]) => (
              <div key={projectName} className="project-card">
                <h4>{projectName}</h4>
                <p>{projectAssignments.length} assignment{projectAssignments.length !== 1 ? 's' : ''}</p>
                <p>Total Hours: {projectAssignments.reduce((total, assignment) => total + assignment.hours_per_week, 0)}/week</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AssignmentList;