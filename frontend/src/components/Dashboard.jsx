import React, { useState, useEffect } from 'react';
import { staffAPI, projectAPI, assignmentAPI, forecastAPI } from '../services/api';
import './Dashboard.css';

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalStaff: 0,
    activeProjects: 0,
    totalAssignments: 0,
    upcomingDeadlines: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load data from multiple endpoints
      const [staffResponse, projectsResponse, assignmentsResponse] = await Promise.all([
        staffAPI.getAll(),
        projectAPI.getAll(),
        assignmentAPI.getAll()
      ]);

      const staff = staffResponse.data;
      const projects = projectsResponse.data;
      const assignments = assignmentsResponse.data;

      // Calculate stats
      const activeProjects = projects.filter(p => p.status === 'active' || p.status === 'planning').length;
      const upcomingDeadlines = projects
        .filter(p => p.end_date && new Date(p.end_date) > new Date())
        .sort((a, b) => new Date(a.end_date) - new Date(b.end_date))
        .slice(0, 3);

      setStats({
        totalStaff: staff.length,
        activeProjects,
        totalAssignments: assignments.length,
        upcomingDeadlines
      });

    } catch (err) {
      console.error('Error loading dashboard data:', err);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard">
        <h1>Dashboard</h1>
        <div className="loading">Loading dashboard data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard">
        <h1>Dashboard</h1>
        <div className="error">{error}</div>
        <button onClick={loadDashboardData}>Retry</button>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <h1>HB-Staffing Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Staff</h3>
          <div className="stat-value">{stats.totalStaff}</div>
        </div>

        <div className="stat-card">
          <h3>Active Projects</h3>
          <div className="stat-value">{stats.activeProjects}</div>
        </div>

        <div className="stat-card">
          <h3>Total Assignments</h3>
          <div className="stat-value">{stats.totalAssignments}</div>
        </div>
      </div>

      <div className="dashboard-section">
        <h2>Upcoming Project Deadlines</h2>
        {stats.upcomingDeadlines.length > 0 ? (
          <div className="deadlines-list">
            {stats.upcomingDeadlines.map(project => (
              <div key={project.id} className="deadline-item">
                <strong>{project.name}</strong>
                <span>Due: {new Date(project.end_date).toLocaleDateString()}</span>
                <span className={`status status-${project.status}`}>{project.status}</span>
              </div>
            ))}
          </div>
        ) : (
          <p>No upcoming deadlines</p>
        )}
      </div>

      <div className="dashboard-section">
        <h2>Quick Actions</h2>
        <div className="quick-actions">
          <a href="/staff/new" className="action-button">Add Staff</a>
          <a href="/projects/new" className="action-button">Create Project</a>
          <a href="/assignments/new" className="action-button">New Assignment</a>
          <a href="/forecasts" className="action-button">View Forecasts</a>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
