import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { projectAPI, roleAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import SkeletonLoader from './common/SkeletonLoader';
import './ProjectRoleRates.css';

const ProjectRoleRates = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  const [project, setProject] = useState(null);
  const [allRates, setAllRates] = useState([]);
  const [roles, setRoles] = useState([]);
  const [editingRoleId, setEditingRoleId] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    startLoading('project-rates');
    clearError();

    try {
      const [projectRes, ratesRes, rolesRes] = await Promise.all([
        projectAPI.getById(id),
        projectAPI.getRoleRates(id),
        roleAPI.getAll({ active_only: true })
      ]);

      setProject(projectRes.data);
      setAllRates(ratesRes.data.all_rates || []);
      setRoles(rolesRes.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('project-rates');
    }
  };

  const handleEditStart = (roleId, currentRate) => {
    setEditingRoleId(roleId);
    setEditValue(currentRate !== null ? currentRate.toString() : '');
  };

  const handleEditCancel = () => {
    setEditingRoleId(null);
    setEditValue('');
  };

  const handleEditSave = async (roleId) => {
    if (!editValue || parseFloat(editValue) <= 0) {
      alert('Please enter a valid billable rate greater than 0');
      return;
    }

    setIsSaving(true);
    try {
      await projectAPI.updateRoleRate(id, roleId, parseFloat(editValue));
      await fetchData(); // Refresh data
      setEditingRoleId(null);
      setEditValue('');
    } catch (err) {
      handleError(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleRevertToParent = async (roleId) => {
    if (!window.confirm('Are you sure you want to remove this rate override and use the parent rate?')) {
      return;
    }

    setIsSaving(true);
    try {
      await projectAPI.deleteRoleRate(id, roleId);
      await fetchData(); // Refresh data
    } catch (err) {
      handleError(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleBulkSave = async (rates) => {
    setIsSaving(true);
    try {
      const ratesArray = Object.entries(rates)
        .filter(([_, rate]) => rate !== null && rate !== '')
        .map(([roleId, rate]) => ({
          role_id: parseInt(roleId),
          billable_rate: parseFloat(rate)
        }));

      if (ratesArray.length > 0) {
        await projectAPI.setRoleRates(id, ratesArray);
        await fetchData();
      }
    } catch (err) {
      handleError(err);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading('project-rates')) {
    return (
      <div className="project-role-rates">
        <div className="header">
          <h1>Project Role Rates</h1>
          <SkeletonLoader />
        </div>
        <div className="rates-table">
          <SkeletonLoader />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="project-role-rates">
        <h1>Project Role Rates</h1>
        <div className="error-message">
          <p>Failed to load data: {error.message}</p>
          <button onClick={fetchData}>Retry</button>
        </div>
      </div>
    );
  }

  if (!project) {
    return null;
  }

  return (
    <div className="project-role-rates">
      <div className="header">
        <div className="header-info">
          <h1>
            <span className="project-icon">{project.is_folder ? '📁' : '📄'}</span>
            {project.name} - Role Rates
          </h1>
          {project.parent_project_name && (
            <p className="parent-info">
              Parent: <Link to={`/projects/${project.parent_project_id}/rates`}>{project.parent_project_name}</Link>
            </p>
          )}
        </div>
        <div className="header-actions">
          <Link to={`/projects/${id}/edit`} className="btn-secondary">Edit Project</Link>
          <button className="btn-secondary" onClick={() => navigate('/projects')}>Back to Projects</button>
        </div>
      </div>

      {project.is_folder && (
        <div className="folder-notice">
          <p>
            <strong>📁 This is a project folder.</strong> Rates set here will be inherited by all sub-projects 
            unless they define their own rates.
          </p>
        </div>
      )}

      {!project.is_folder && project.parent_project_id && (
        <div className="inheritance-notice">
          <p>
            Rates marked as "Inherited" come from the parent folder. 
            You can override any rate by clicking Edit, or revert to the parent rate.
          </p>
        </div>
      )}

      <div className="rates-table-container">
        <table className="rates-table">
          <thead>
            <tr>
              <th>Role</th>
              <th>Billable Rate ($/hr)</th>
              <th>Source</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {allRates.map(rate => (
              <tr 
                key={rate.role_id} 
                className={rate.is_inherited ? 'inherited' : rate.billable_rate ? 'explicit' : 'unset'}
              >
                <td className="role-name">{rate.role_name}</td>
                <td className="rate-value">
                  {editingRoleId === rate.role_id ? (
                    <input
                      type="number"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      min="0"
                      step="0.01"
                      autoFocus
                      className="rate-input"
                    />
                  ) : (
                    rate.billable_rate !== null ? (
                      <span className="rate">${rate.billable_rate.toFixed(2)}</span>
                    ) : (
                      <span className="no-rate">Not set</span>
                    )
                  )}
                </td>
                <td className="rate-source">
                  {rate.is_inherited ? (
                    <span className="source-inherited">Inherited</span>
                  ) : rate.billable_rate !== null ? (
                    <span className="source-explicit">This Project</span>
                  ) : (
                    <span className="source-none">--</span>
                  )}
                </td>
                <td className="rate-actions">
                  {editingRoleId === rate.role_id ? (
                    <>
                      <button 
                        className="btn-save"
                        onClick={() => handleEditSave(rate.role_id)}
                        disabled={isSaving}
                      >
                        Save
                      </button>
                      <button 
                        className="btn-cancel"
                        onClick={handleEditCancel}
                        disabled={isSaving}
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button 
                        className="btn-edit"
                        onClick={() => handleEditStart(rate.role_id, rate.billable_rate)}
                      >
                        {rate.billable_rate !== null ? 'Edit' : 'Set Rate'}
                      </button>
                      {rate.billable_rate !== null && !rate.is_inherited && project.parent_project_id && (
                        <button 
                          className="btn-revert"
                          onClick={() => handleRevertToParent(rate.role_id)}
                          title="Revert to parent rate"
                        >
                          Revert
                        </button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {allRates.length === 0 && (
        <div className="empty-state">
          <p>No roles found. <Link to="/roles">Manage roles</Link> to add billable rates.</p>
        </div>
      )}
    </div>
  );
};

export default ProjectRoleRates;

