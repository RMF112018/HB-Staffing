import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { planningAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import SkeletonLoader from './common/SkeletonLoader';
import './PlanningExerciseList.css';

const PlanningExerciseList = () => {
  const navigate = useNavigate();
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  const [exercises, setExercises] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  useEffect(() => {
    fetchExercises();
  }, [statusFilter]);

  const fetchExercises = async () => {
    startLoading('exercises');
    clearError();

    try {
      const params = {};
      if (statusFilter) {
        params.status = statusFilter;
      }
      const response = await planningAPI.getAll(params);
      setExercises(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('exercises');
    }
  };

  const handleDelete = async (exerciseId) => {
    try {
      await planningAPI.delete(exerciseId);
      setExercises(exercises.filter(e => e.id !== exerciseId));
      setDeleteConfirm(null);
    } catch (err) {
      handleError(err);
    }
  };

  const handleStatusChange = async (exerciseId, newStatus) => {
    try {
      await planningAPI.update(exerciseId, { status: newStatus });
      setExercises(exercises.map(e => 
        e.id === exerciseId ? { ...e, status: newStatus } : e
      ));
    } catch (err) {
      handleError(err);
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'draft': return 'status-draft';
      case 'active': return 'status-active';
      case 'completed': return 'status-completed';
      case 'archived': return 'status-archived';
      default: return '';
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <div className="planning-exercise-list">
      <div className="page-header">
        <div className="header-content">
          <h1>Staff Planning Exercises</h1>
          <p className="subtitle">Plan and analyze staffing needs across multiple projects</p>
        </div>
        <Link to="/planning/new" className="btn-primary">
          + New Planning Exercise
        </Link>
      </div>

      {/* Filters */}
      <div className="filters-bar">
        <div className="filter-group">
          <label htmlFor="statusFilter">Status:</label>
          <select
            id="statusFilter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="archived">Archived</option>
          </select>
        </div>
        <div className="filter-results">
          {exercises.length} exercise{exercises.length !== 1 ? 's' : ''} found
        </div>
      </div>

      {error && (
        <div className="error-message">
          <p>{error.message}</p>
        </div>
      )}

      {isLoading('exercises') && <SkeletonLoader />}

      {!isLoading('exercises') && exercises.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h2>No Planning Exercises Yet</h2>
          <p>Create your first planning exercise to start analyzing staffing needs.</p>
          <Link to="/planning/new" className="btn-primary">
            Create Planning Exercise
          </Link>
        </div>
      )}

      {!isLoading('exercises') && exercises.length > 0 && (
        <div className="exercise-grid">
          {exercises.map(exercise => (
            <div key={exercise.id} className="exercise-card">
              <div className="card-header">
                <h3 className="exercise-name">{exercise.name}</h3>
                <span className={`status-badge ${getStatusBadgeClass(exercise.status)}`}>
                  {exercise.status}
                </span>
              </div>

              {exercise.description && (
                <p className="exercise-description">{exercise.description}</p>
              )}

              <div className="card-stats">
                <div className="stat">
                  <span className="stat-value">{exercise.project_count || 0}</span>
                  <span className="stat-label">Projects</span>
                </div>
                <div className="stat">
                  <span className="stat-value">{formatDate(exercise.created_at)}</span>
                  <span className="stat-label">Created</span>
                </div>
              </div>

              <div className="card-actions">
                <Link to={`/planning/${exercise.id}`} className="btn-view">
                  View Analysis
                </Link>
                <Link to={`/planning/${exercise.id}/edit`} className="btn-edit">
                  Edit
                </Link>
                <div className="dropdown-actions">
                  <select
                    value={exercise.status}
                    onChange={(e) => handleStatusChange(exercise.id, e.target.value)}
                    className="status-select"
                  >
                    <option value="draft">Draft</option>
                    <option value="active">Active</option>
                    <option value="completed">Completed</option>
                    <option value="archived">Archived</option>
                  </select>
                </div>
                <button 
                  className="btn-delete"
                  onClick={() => setDeleteConfirm(exercise.id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Delete Planning Exercise?</h3>
            <p>
              This will permanently delete the planning exercise and all associated projects and roles.
              This action cannot be undone.
            </p>
            <div className="modal-actions">
              <button 
                className="btn-danger"
                onClick={() => handleDelete(deleteConfirm)}
              >
                Delete
              </button>
              <button 
                className="btn-secondary"
                onClick={() => setDeleteConfirm(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlanningExerciseList;

