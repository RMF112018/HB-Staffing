import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { templateAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import SkeletonLoader from './common/SkeletonLoader';
import './TemplateList.css';

const TemplateList = () => {
  const [templates, setTemplates] = useState([]);
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    startLoading('templates');
    clearError();

    try {
      const response = await templateAPI.getAll();
      setTemplates(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('templates');
    }
  };

  const handleDelete = async (id, templateName) => {
    if (!window.confirm(`Are you sure you want to delete the template "${templateName}"?`)) {
      return;
    }

    try {
      await templateAPI.delete(id);
      setTemplates(templates.filter(t => t.id !== id));
    } catch (err) {
      const message = err.response?.data?.error?.message || 'Failed to delete template';
      alert(message);
    }
  };

  const getProjectTypeClass = (type) => {
    if (!type) return 'type-default';
    const typeMap = {
      'Commercial': 'type-commercial',
      'Residential': 'type-residential',
      'Healthcare': 'type-healthcare',
      'Industrial': 'type-industrial',
      'Educational': 'type-educational'
    };
    return typeMap[type] || 'type-default';
  };

  if (isLoading('templates')) {
    return (
      <div className="template-list">
        <div className="header">
          <h1>Project Templates</h1>
          <SkeletonLoader />
        </div>
        <div className="template-grid">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="template-card">
              <SkeletonLoader />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="template-list">
        <h1>Project Templates</h1>
        <div className="error-message">
          <p>Failed to load templates: {error.message}</p>
          <button onClick={fetchTemplates}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="template-list">
      <div className="header">
        <div className="header-content">
          <h1>Project Templates</h1>
          <p className="header-description">
            Create reusable project structures with predefined roles, durations, and staffing requirements.
          </p>
        </div>
        <Link to="/templates/new" className="btn-primary">Create Template</Link>
      </div>

      <div className="template-grid">
        {templates.map(template => (
          <div key={template.id} className={`template-card ${!template.is_active ? 'inactive' : ''}`}>
            <div className="template-header">
              <div className="template-title">
                <h3>{template.name}</h3>
                {!template.is_active && <span className="inactive-badge">Inactive</span>}
              </div>
              {template.project_type && (
                <span className={`project-type-badge ${getProjectTypeClass(template.project_type)}`}>
                  {template.project_type}
                </span>
              )}
            </div>

            {template.description && (
              <p className="template-description">{template.description}</p>
            )}

            <div className="template-stats">
              <div className="stat">
                <span className="stat-value">{template.duration_months}</span>
                <span className="stat-label">Months</span>
              </div>
              <div className="stat">
                <span className="stat-value">{template.role_count || 0}</span>
                <span className="stat-label">Roles</span>
              </div>
              <div className="stat">
                <span className="stat-value">
                  {template.roles?.reduce((sum, r) => sum + r.count, 0) || 0}
                </span>
                <span className="stat-label">Staff Needed</span>
              </div>
            </div>

            {template.roles && template.roles.length > 0 && (
              <div className="template-roles-preview">
                <h4>Roles:</h4>
                <ul>
                  {template.roles.slice(0, 4).map((role, idx) => (
                    <li key={idx}>
                      {role.count}x {role.role_name}
                      <span className="role-timing">
                        (M{role.start_month}{role.end_month ? `-${role.end_month}` : '+'})
                      </span>
                    </li>
                  ))}
                  {template.roles.length > 4 && (
                    <li className="more-roles">+{template.roles.length - 4} more...</li>
                  )}
                </ul>
              </div>
            )}

            <div className="template-actions">
              <Link to={`/templates/${template.id}/edit`} className="btn-secondary">Edit</Link>
              <button 
                className="btn-danger" 
                onClick={() => handleDelete(template.id, template.name)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {templates.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h3>No Templates Yet</h3>
          <p>Create your first project template to streamline project setup.</p>
          <Link to="/templates/new" className="btn-primary">Create Template</Link>
        </div>
      )}
    </div>
  );
};

export default TemplateList;

