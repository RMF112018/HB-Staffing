import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectAPI } from '../services/api';
import DataTable from './common/DataTable';
import LoadingSpinner from './common/LoadingSpinner';
import ErrorMessage from './common/ErrorMessage';
import './ProjectList.css';

const ProjectList = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await projectAPI.getAll();
      setProjects(response.data);
    } catch (err) {
      console.error('Error loading projects:', err);
      setError('Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (project) => {
    navigate(`/projects/${project.id}/edit`);
  };

  const handleDelete = async (project) => {
    if (window.confirm(`Are you sure you want to delete "${project.name}"?`)) {
      try {
        await projectAPI.delete(project.id);
        setProjects(prev => prev.filter(p => p.id !== project.id));
      } catch (err) {
        console.error('Error deleting project:', err);
        setError('Failed to delete project');
      }
    }
  };

  const handleViewForecast = (project) => {
    navigate(`/forecasts?project=${project.id}`);
  };

  const handleCreateNew = () => {
    navigate('/projects/new');
  };

  const getStatusBadge = (status) => {
    const statusClasses = {
      planning: 'status-planning',
      active: 'status-active',
      completed: 'status-completed',
      cancelled: 'status-cancelled',
      'on-hold': 'status-on-hold'
    };

    return (
      <span className={`status-badge ${statusClasses[status] || 'status-default'}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const columns = [
    {
      key: 'name',
      label: 'Project Name',
      sortable: true
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (status) => getStatusBadge(status)
    },
    {
      key: 'location',
      label: 'Location',
      sortable: true
    },
    {
      key: 'start_date',
      label: 'Start Date',
      sortable: true,
      type: 'date'
    },
    {
      key: 'end_date',
      label: 'End Date',
      sortable: true,
      type: 'date'
    },
    {
      key: 'budget',
      label: 'Budget',
      sortable: true,
      type: 'currency',
      align: 'right'
    }
  ];

  const activeProjects = projects.filter(p => p.status === 'active' || p.status === 'planning');
  const completedProjects = projects.filter(p => p.status === 'completed');

  if (loading) {
    return <LoadingSpinner message="Loading projects..." />;
  }

  return (
    <div className="project-list">
      <div className="list-header">
        <h1>Projects</h1>
        <button onClick={handleCreateNew} className="create-button">
          Create Project
        </button>
      </div>

      {error && (
        <ErrorMessage
          message={error}
          onRetry={loadProjects}
        />
      )}

      <div className="project-stats">
        <div className="stat-card">
          <h3>Total Projects</h3>
          <div className="stat-value">{projects.length}</div>
        </div>
        <div className="stat-card">
          <h3>Active Projects</h3>
          <div className="stat-value">{activeProjects.length}</div>
        </div>
        <div className="stat-card">
          <h3>Completed Projects</h3>
          <div className="stat-value">{completedProjects.length}</div>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={projects}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onView={handleViewForecast}
        loading={loading}
        emptyMessage="No projects found"
        searchPlaceholder="Search projects..."
        className="project-table"
      />

      <div className="project-actions">
        <button onClick={() => navigate('/forecasts')} className="forecast-button">
          View All Forecasts
        </button>
      </div>
    </div>
  );
};

export default ProjectList;