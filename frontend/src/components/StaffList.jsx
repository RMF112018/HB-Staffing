import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { staffAPI } from '../services/api';
import DataTable from './common/DataTable';
import LoadingSpinner from './common/LoadingSpinner';
import ErrorMessage from './common/ErrorMessage';
import './StaffList.css';

const StaffList = () => {
  const navigate = useNavigate();
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadStaff();
  }, []);

  const loadStaff = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await staffAPI.getAll();
      setStaff(response.data);
    } catch (err) {
      console.error('Error loading staff:', err);
      setError('Failed to load staff members');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (staffMember) => {
    navigate(`/staff/${staffMember.id}/edit`);
  };

  const handleDelete = async (staffMember) => {
    if (window.confirm(`Are you sure you want to delete ${staffMember.name}?`)) {
      try {
        await staffAPI.delete(staffMember.id);
        setStaff(prev => prev.filter(s => s.id !== staffMember.id));
      } catch (err) {
        console.error('Error deleting staff:', err);
        setError('Failed to delete staff member');
      }
    }
  };

  const handleCreateNew = () => {
    navigate('/staff/new');
  };

  const columns = [
    {
      key: 'name',
      label: 'Name',
      sortable: true
    },
    {
      key: 'role',
      label: 'Role',
      sortable: true
    },
    {
      key: 'hourly_rate',
      label: 'Hourly Rate',
      sortable: true,
      type: 'currency',
      align: 'right'
    },
    {
      key: 'skills',
      label: 'Skills',
      render: (skills) => skills && skills.length > 0 ? skills.join(', ') : 'None'
    },
    {
      key: 'availability_start',
      label: 'Available From',
      sortable: true,
      type: 'date'
    },
    {
      key: 'availability_end',
      label: 'Available Until',
      sortable: true,
      type: 'date'
    }
  ];

  if (loading) {
    return <LoadingSpinner message="Loading staff members..." />;
  }

  return (
    <div className="staff-list">
      <div className="list-header">
        <h1>Staff Members</h1>
        <button onClick={handleCreateNew} className="create-button">
          Add Staff Member
        </button>
      </div>

      {error && (
        <ErrorMessage
          message={error}
          onRetry={loadStaff}
        />
      )}

      <DataTable
        columns={columns}
        data={staff}
        onEdit={handleEdit}
        onDelete={handleDelete}
        loading={loading}
        emptyMessage="No staff members found"
        searchPlaceholder="Search staff members..."
        className="staff-table"
      />

      <div className="list-stats">
        <p>Total Staff: {staff.length}</p>
      </div>
    </div>
  );
};

export default StaffList;