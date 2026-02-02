import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { staffAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import SkeletonLoader from './common/SkeletonLoader';
import './StaffList.css';

const StaffList = () => {
  const [staff, setStaff] = useState([]);
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  useEffect(() => {
    fetchStaff();
  }, []);

  const fetchStaff = async () => {
    startLoading('staff');
    clearError();

    try {
      const response = await staffAPI.getAll();
      setStaff(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('staff');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this staff member?')) {
      return;
    }

    try {
      await staffAPI.delete(id);
      setStaff(staff.filter(member => member.id !== id));
    } catch (err) {
      const message = err.response?.data?.error?.message || 'Failed to delete staff member';
      alert(message);
    }
  };

  if (isLoading('staff')) {
    return (
      <div className="staff-list">
        <div className="header">
          <h1>Staff Management</h1>
          <SkeletonLoader />
        </div>
        <div className="staff-grid">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="staff-card">
              <SkeletonLoader />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="staff-list">
        <h1>Staff Management</h1>
        <div className="error-message">
          <p>Failed to load staff: {error.message}</p>
          <button onClick={fetchStaff}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="staff-list">
      <div className="header">
        <h1>Staff Management</h1>
        <Link to="/staff/new" className="btn-primary">Add New Staff</Link>
      </div>

      <div className="staff-grid">
        {staff.map(member => (
          <div key={member.id} className="staff-card">
            <div className="staff-info">
              <h3>{member.name}</h3>
              <p className="staff-role"><strong>Role:</strong> {member.role}</p>
              <div className="rate-info">
                <div className="rate-item internal">
                  <span className="rate-label">Internal Cost</span>
                  <span className="rate-value">${member.internal_hourly_cost?.toFixed(2)}/hr</span>
                </div>
                {member.default_billable_rate && (
                  <div className="rate-item billable">
                    <span className="rate-label">Default Billable</span>
                    <span className="rate-value">${member.default_billable_rate?.toFixed(2)}/hr</span>
                  </div>
                )}
                {member.internal_hourly_cost && member.default_billable_rate && (
                  <div className="rate-item margin">
                    <span className="rate-label">Margin</span>
                    <span className="rate-value">${(member.default_billable_rate - member.internal_hourly_cost).toFixed(2)}/hr</span>
                  </div>
                )}
              </div>
              {member.skills && member.skills.length > 0 && (
                <div className="skills-section">
                  <strong>Skills:</strong>
                  <div className="skill-tags">
                    {member.skills.map((skill, idx) => (
                      <span key={idx} className="skill-tag">{skill}</span>
                    ))}
                  </div>
                </div>
              )}
              {member.availability_start && (
                <p className="availability"><strong>Available:</strong> {member.availability_start} {member.availability_end ? `- ${member.availability_end}` : 'onwards'}</p>
              )}
            </div>
            <div className="staff-actions">
              <Link to={`/staff/${member.id}/edit`} className="btn-secondary">Edit</Link>
              <button className="btn-danger" onClick={() => handleDelete(member.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>

      {staff.length === 0 && (
        <div className="empty-state">
          <p>No staff members found. <Link to="/staff/new">Add your first staff member</Link></p>
        </div>
      )}
    </div>
  );
};

export default StaffList;
