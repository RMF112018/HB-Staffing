import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { projectAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import SkeletonLoader from './common/SkeletonLoader';
import './ProjectList.css';

const ProjectList = () => {
  const [projects, setProjects] = useState([]);
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    startLoading('projects');
    clearError();

    try {
      // Get top-level projects only (no sub-projects in main list)
      const response = await projectAPI.getTopLevel();
      setProjects(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('projects');
    }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this project?')) {
      return;
    }

    try {
      await projectAPI.delete(id);
      setProjects(prevProjects => prevProjects.filter(p => p.id !== id));
    } catch (err) {
      const message = err.response?.data?.error?.message || 'Failed to delete project';
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

  const renderProjectCard = (project) => {
    const isFolder = project.is_folder;
    const hasChildren = project.sub_projects_count > 0;
    
    return (
      <div key={project.id} className="project-tree-item">
        <div className={`project-card ${isFolder ? 'folder' : 'standalone'}`}>
          <div className="project-card-header">
            <span className="project-icon">
              {isFolder ? '📁' : '📄'}
            </span>
            <h3 className="project-name">{project.name}</h3>
            {isFolder && project.sub_projects_count > 0 && (
              <span className="sub-count">({project.sub_projects_count} sub-projects)</span>
            )}
          </div>
          
          <div className="project-card-body">
            <p>
              <strong>Status:</strong>{' '}
              <span className={`status-badge ${getStatusClass(project.status)}`}>
                {project.status}
              </span>
            </p>
            {project.start_date && <p><strong>Start:</strong> {project.start_date}</p>}
            {project.end_date && <p><strong>End:</strong> {project.end_date}</p>}
            {project.budget && <p><strong>Budget:</strong> ${project.budget.toLocaleString()}</p>}
            {project.location && <p><strong>Location:</strong> {project.location}</p>}
          </div>
          
          <div className="project-actions">
            <Link to={`/projects/${project.id}`} className="btn-primary">View</Link>
            <Link to={`/projects/${project.id}/edit`} className="btn-secondary">Edit</Link>
            <Link to={`/projects/${project.id}/rates`} className="btn-secondary">Rates</Link>
            <button 
              className="btn-danger" 
              onClick={(e) => handleDelete(project.id, e)}
              disabled={hasChildren}
              title={hasChildren ? 'Delete sub-projects first' : 'Delete project'}
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    );
  };

  if (isLoading('projects')) {
    return (
      <div className="project-list">
        <div className="header">
          <h1>Project Management</h1>
          <SkeletonLoader />
        </div>
        <div className="project-tree">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="project-card">
              <SkeletonLoader />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="project-list">
        <h1>Project Management</h1>
        <div className="error-message">
          <p>Failed to load projects: {error.message}</p>
          <button onClick={fetchProjects}>Retry</button>
        </div>
      </div>
    );
  }

  // Separate folders and standalone projects
  const folders = projects.filter(p => p.is_folder);
  const standaloneProjects = projects.filter(p => !p.is_folder);

  return (
    <div className="project-list">
      <div className="header">
        <h1>Project Management</h1>
        <div className="header-actions">
          <Link to="/projects/new?type=folder" className="btn-primary">Create Folder</Link>
          <Link to="/projects/new" className="btn-primary">Create Project</Link>
        </div>
      </div>

      {/* Project Folders Section */}
      {folders.length > 0 && (
        <div className="project-section">
          <h2 className="section-title">📁 Project Folders</h2>
          <p className="section-subtitle">Click "View" to see sub-projects and assign staff</p>
          <div className="project-tree">
            {folders.map(project => renderProjectCard(project))}
          </div>
        </div>
      )}

      {/* Standalone Projects Section */}
      {standaloneProjects.length > 0 && (
        <div className="project-section">
          <h2 className="section-title">📄 Standalone Projects</h2>
          <div className="project-tree">
            {standaloneProjects.map(project => renderProjectCard(project))}
          </div>
        </div>
      )}

      {projects.length === 0 && (
        <div className="empty-state">
          <p>No projects found.</p>
          <p>
            <Link to="/projects/new?type=folder">Create a project folder</Link> to organize your projects, or{' '}
            <Link to="/projects/new">create a standalone project</Link>.
          </p>
        </div>
      )}
    </div>
  );
};

export default ProjectList;
