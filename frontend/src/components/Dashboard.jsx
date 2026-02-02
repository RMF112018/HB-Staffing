import React, { useState, useEffect, useCallback } from 'react';
import { Bar, Pie, Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
} from 'chart.js';
import { staffAPI, projectAPI, assignmentAPI, forecastAPI } from '../services/api';
import LoadingSpinner from './common/LoadingSpinner';
import ErrorMessage from './common/ErrorMessage';
import SkeletonLoader from './common/SkeletonLoader';
import { useLoading } from '../contexts/LoadingContext';
import { useApiError } from '../hooks/useApiError';
import './Dashboard.css';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement
);

const Dashboard = () => {
  const { withLoading, isLoading } = useLoading();
  const { error, handleApiError, clearError, retryOperation } = useApiError();

  const [stats, setStats] = useState({
    totalStaff: 0,
    activeProjects: 0,
    totalAssignments: 0,
    upcomingDeadlines: [],
    projectsByStatus: {},
    staffByRole: {},
    projectTimeline: [],
    totalBudget: 0,
    utilizedBudget: 0
  });
  const [chartData, setChartData] = useState({
    projectsByStatus: null,
    staffByRole: null,
    projectTimeline: null
  });
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    withLoading('dashboard_initial', loadDashboardData);
  }, [loadDashboardData, withLoading]);

  const loadDashboardData = useCallback(async () => {
    try {
      clearError();


      // Load data from multiple endpoints with individual error handling
      const [staffRes, projectsRes, assignmentsRes] = await Promise.allSettled([
        staffAPI.getAll(),
        projectAPI.getAll(),
        assignmentAPI.getAll()
      ]);

      const staff = staffRes.status === 'fulfilled' ? staffRes.value.data : [];
      const projects = projectsRes.status === 'fulfilled' ? projectsRes.value.data : [];
      const assignments = assignmentsRes.status === 'fulfilled' ? assignmentsRes.value.data : [];

      // Check for failed requests and log warnings
      const failedRequests = [staffRes, projectsRes, assignmentsRes]
        .map((res, index) => ({ res, index }))
        .filter(({ res }) => res.status === 'rejected');

      if (failedRequests.length > 0) {
        console.warn('Some dashboard data requests failed:', failedRequests[0].res.reason);
      }

      // Calculate comprehensive stats
      const activeProjects = projects.filter(p => p.status === 'active' || p.status === 'planning').length;
      const upcomingDeadlines = projects
        .filter(p => p.end_date && new Date(p.end_date) > new Date())
        .sort((a, b) => new Date(a.end_date) - new Date(b.end_date))
        .slice(0, 3);

      // Group projects by status
      const projectsByStatus = projects.reduce((acc, project) => {
        acc[project.status] = (acc[project.status] || 0) + 1;
        return acc;
      }, {});

      // Group staff by role
      const staffByRole = staff.reduce((acc, person) => {
        acc[person.role] = (acc[person.role] || 0) + 1;
        return acc;
      }, {});

      // Calculate project timeline data (projects by month)
      const projectTimeline = projects.reduce((acc, project) => {
        if (project.start_date) {
          const month = new Date(project.start_date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short'
          });
          acc[month] = (acc[month] || 0) + 1;
        }
        return acc;
      }, {});

      // Calculate budget utilization
      const totalBudget = projects.reduce((sum, project) => sum + (project.budget || 0), 0);

      setStats({
        totalStaff: staff.length,
        activeProjects,
        totalAssignments: assignments.length,
        upcomingDeadlines,
        projectsByStatus,
        staffByRole,
        projectTimeline: Object.entries(projectTimeline).map(([month, count]) => ({ month, count })),
        totalBudget,
        utilizedBudget: totalBudget * 0.75 // Simplified calculation
      });

      // Prepare chart data
      setChartData({
        projectsByStatus: {
          labels: Object.keys(projectsByStatus),
          datasets: [{
            label: 'Projects by Status',
            data: Object.values(projectsByStatus),
            backgroundColor: [
              '#3498db', // planning
              '#27ae60', // active
              '#f39c12', // on-hold
              '#e74c3c', // cancelled
              '#95a5a6'  // completed
            ],
            borderWidth: 1
          }]
        },
        staffByRole: {
          labels: Object.keys(staffByRole),
          datasets: [{
            label: 'Staff Distribution',
            data: Object.values(staffByRole),
            backgroundColor: [
              '#3498db',
              '#e74c3c',
              '#27ae60',
              '#f39c12',
              '#9b59b6',
              '#1abc9c'
            ],
            borderWidth: 1
          }]
        },
        projectTimeline: {
          labels: Object.keys(projectTimeline),
          datasets: [{
            label: 'Projects Starting',
            data: Object.values(projectTimeline),
            borderColor: '#3498db',
            backgroundColor: 'rgba(52, 152, 219, 0.1)',
            tension: 0.4,
            fill: true
          }]
        }
      });

      setLastUpdated(new Date());

    } catch (err) {
      handleApiError(err, 'load_dashboard_data');
    }
  }, [clearError, handleApiError]);

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
        <ErrorMessage
          message={error.message}
          type={error.type}
          onRetry={() => retryOperation(loadDashboardData)}
          action={
            <button onClick={() => window.location.reload()}>
              Reload Page
            </button>
          }
        />
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>HB-Staffing Dashboard</h1>
        <div className="dashboard-controls">
          <button
            onClick={() => withLoading('dashboard_refresh', loadDashboardData)}
            className="refresh-button"
            disabled={isLoading('dashboard_refresh')}
          >
            {isLoading('dashboard_refresh') ? 'Refreshing...' : 'Refresh Data'}
          </button>
          {lastUpdated && (
            <span className="last-updated">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Staff</h3>
          {isLoading('dashboard_initial') ? (
            <SkeletonLoader type="text" width="60px" height="2rem" />
          ) : (
            <>
              <div className="stat-value">{stats.totalStaff}</div>
              <div className="stat-subtitle">
                {Object.keys(stats.staffByRole).length} different roles
              </div>
            </>
          )}
        </div>

        <div className="stat-card">
          <h3>Active Projects</h3>
          {isLoading('dashboard_initial') ? (
            <SkeletonLoader type="text" width="60px" height="2rem" />
          ) : (
            <>
              <div className="stat-value">{stats.activeProjects}</div>
              <div className="stat-subtitle">
                of {stats.totalStaff + stats.activeProjects + stats.totalAssignments} total records
              </div>
            </>
          )}
        </div>

        <div className="stat-card">
          <h3>Total Assignments</h3>
          {isLoading('dashboard_initial') ? (
            <SkeletonLoader type="text" width="60px" height="2rem" />
          ) : (
            <>
              <div className="stat-value">{stats.totalAssignments}</div>
              <div className="stat-subtitle">
                {stats.totalAssignments > 0 ? Math.round(stats.totalAssignments / stats.activeProjects) : 0} per project avg
              </div>
            </>
          )}
        </div>

        <div className="stat-card">
          <h3>Total Budget</h3>
          {isLoading('dashboard_initial') ? (
            <SkeletonLoader type="text" width="80px" height="2rem" />
          ) : (
            <>
              <div className="stat-value">${stats.totalBudget?.toLocaleString() || '0'}</div>
              <div className="stat-subtitle">
                ${stats.utilizedBudget?.toLocaleString() || '0'} utilized
              </div>
            </>
          )}
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Projects by Status</h3>
          <div className="chart-container">
            {chartData.projectsByStatus && (
              <Pie
                data={chartData.projectsByStatus}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      position: 'bottom',
                      labels: {
                        boxWidth: 12,
                        font: {
                          size: 11
                        }
                      }
                    }
                  }
                }}
              />
            )}
          </div>
        </div>

        <div className="chart-card">
          <h3>Staff Distribution by Role</h3>
          <div className="chart-container">
            {chartData.staffByRole && (
              <Bar
                data={chartData.staffByRole}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  scales: {
                    y: {
                      beginAtZero: true,
                      ticks: {
                        stepSize: 1
                      }
                    }
                  },
                  plugins: {
                    legend: {
                      display: false
                    }
                  }
                }}
              />
            )}
          </div>
        </div>

        <div className="chart-card chart-card-full">
          <h3>Project Timeline Overview</h3>
          <div className="chart-container chart-container-large">
            {chartData.projectTimeline && (
              <Line
                data={chartData.projectTimeline}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  scales: {
                    y: {
                      beginAtZero: true,
                      ticks: {
                        stepSize: 1
                      }
                    }
                  },
                  plugins: {
                    legend: {
                      display: false
                    }
                  }
                }}
              />
            )}
          </div>
        </div>
      </div>

      <div className="dashboard-section">
        <h2>Upcoming Project Deadlines</h2>
        {stats.upcomingDeadlines.length > 0 ? (
          <div className="deadlines-list">
            {stats.upcomingDeadlines.map(project => (
              <div key={project.id} className="deadline-item">
                <div className="deadline-info">
                  <strong>{project.name}</strong>
                  <span className="deadline-date">
                    Due: {new Date(project.end_date).toLocaleDateString()}
                  </span>
                </div>
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
          <a href="/staff/new" className="action-button">Add Staff Member</a>
          <a href="/projects/new" className="action-button">Create Project</a>
          <a href="/assignments/new" className="action-button">New Assignment</a>
          <a href="/forecasts" className="action-button primary">View Forecasts</a>
          <a href="/reports" className="action-button">Generate Reports</a>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
