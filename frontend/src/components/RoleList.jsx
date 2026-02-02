import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { roleAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import SkeletonLoader from './common/SkeletonLoader';
import './RoleList.css';

const RoleList = () => {
  const [roles, setRoles] = useState([]);
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  useEffect(() => {
    fetchRoles();
  }, []);

  const fetchRoles = async () => {
    startLoading('roles');
    clearError();

    try {
      const response = await roleAPI.getAll();
      setRoles(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('roles');
    }
  };

  const handleDelete = async (id, roleName, staffCount) => {
    if (staffCount > 0) {
      alert(`Cannot delete role "${roleName}" - ${staffCount} staff member(s) are assigned to it.`);
      return;
    }

    if (!window.confirm(`Are you sure you want to delete the role "${roleName}"?`)) {
      return;
    }

    try {
      await roleAPI.delete(id);
      setRoles(roles.filter(role => role.id !== id));
    } catch (err) {
      const message = err.response?.data?.error?.message || 'Failed to delete role';
      alert(message);
    }
  };

  if (isLoading('roles')) {
    return (
      <div className="role-list">
        <div className="header">
          <h1>Role Management</h1>
          <SkeletonLoader />
        </div>
        <div className="role-grid">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="role-card">
              <SkeletonLoader />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="role-list">
        <h1>Role Management</h1>
        <div className="error-message">
          <p>Failed to load roles: {error.message}</p>
          <button onClick={fetchRoles}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="role-list">
      <div className="header">
        <h1>Role Management</h1>
        <Link to="/roles/new" className="btn-primary">Add New Role</Link>
      </div>

      <div className="role-info-banner">
        <p>
          Roles define position titles with associated internal hourly costs. 
          When a new project is created, roles with a default billable rate are automatically added to the project's rate sheet.
          Rates can be customized per project.
        </p>
      </div>

      <div className="role-grid">
        {roles.map(role => (
          <div key={role.id} className={`role-card ${!role.is_active ? 'inactive' : ''}`}>
            <div className="role-header">
              <h3>{role.name}</h3>
              {!role.is_active && <span className="inactive-badge">Inactive</span>}
            </div>
            <div className="role-info">
              {role.description && (
                <p className="role-description">{role.description}</p>
              )}
              <div className="role-stats">
                <div className="stat">
                  <span className="stat-label">Hourly Cost</span>
                  <span className="stat-value cost">${role.hourly_cost?.toFixed(2)}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Default Billable</span>
                  <span className="stat-value billable">
                    {role.default_billable_rate ? `$${role.default_billable_rate.toFixed(2)}` : '—'}
                  </span>
                </div>
                <div className="stat">
                  <span className="stat-label">Staff Assigned</span>
                  <span className="stat-value">{role.staff_count || 0}</span>
                </div>
              </div>
            </div>
            <div className="role-actions">
              <Link to={`/roles/${role.id}/edit`} className="btn-secondary">Edit</Link>
              <button 
                className="btn-danger" 
                onClick={() => handleDelete(role.id, role.name, role.staff_count)}
                disabled={role.staff_count > 0}
                title={role.staff_count > 0 ? 'Cannot delete role with assigned staff' : ''}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {roles.length === 0 && (
        <div className="empty-state">
          <p>No roles found. <Link to="/roles/new">Create your first role</Link></p>
        </div>
      )}
    </div>
  );
};

export default RoleList;

