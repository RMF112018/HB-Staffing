import React, { useState, useEffect } from 'react';
import { Chart } from 'react-google-charts';
import { Bar, Line } from 'react-chartjs-2';
import { projectAPI, forecastAPI } from '../services/api';
import Select from './common/Select';
import DatePicker from './common/DatePicker';
import LoadingSpinner from './common/LoadingSpinner';
import ErrorMessage from './common/ErrorMessage';
import './Forecasts.css';

const Forecasts = () => {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [forecastData, setForecastData] = useState(null);
  const [orgForecastData, setOrgForecastData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('project'); // 'project' or 'organization'
  const [scenarioMode, setScenarioMode] = useState(false);

  useEffect(() => {
    loadProjects();
    loadOrgForecast();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await projectAPI.getAll();
      setProjects(response.data);
    } catch (err) {
      console.error('Error loading projects:', err);
    }
  };

  const loadOrgForecast = async () => {
    try {
      const today = new Date().toISOString().split('T')[0];
      const futureDate = new Date();
      futureDate.setMonth(futureDate.getMonth() + 6);
      const futureStr = futureDate.toISOString().split('T')[0];

      const response = await forecastAPI.getOrganization({
        start_date: today,
        end_date: futureStr
      });
      setOrgForecastData(response.data);
    } catch (err) {
      console.error('Error loading organization forecast:', err);
    }
  };

  const loadProjectForecast = async () => {
    if (!selectedProject) {
      setError('Please select a project');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const params = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const response = await projectAPI.getForecast(selectedProject, params);
      setForecastData(response.data);
    } catch (err) {
      console.error('Error loading forecast:', err);
      setError('Failed to load forecast data');
    } finally {
      setLoading(false);
    }
  };

  const handleProjectChange = (name, value) => {
    setSelectedProject(value);
    setForecastData(null);
  };

  const handleDateChange = (name, value) => {
    if (name === 'start_date') {
      setStartDate(value);
    } else if (name === 'end_date') {
      setEndDate(value);
    }
  };

  const generateGanttData = (forecast) => {
    if (!forecast) return null;

    const data = [
      [
        { type: 'string', label: 'Task ID' },
        { type: 'string', label: 'Task Name' },
        { type: 'date', label: 'Start Date' },
        { type: 'date', label: 'End Date' },
        { type: 'number', label: 'Duration' },
        { type: 'number', label: 'Percent Complete' },
        { type: 'string', label: 'Dependencies' },
      ],
    ];

    // Add project timeline
    const projectStart = new Date(forecast.forecast_period.start_date);
    const projectEnd = new Date(forecast.forecast_period.end_date);

    data.push([
      forecast.project_name,
      forecast.project_name,
      projectStart,
      projectEnd,
      null,
      100,
      null,
    ]);

    // Add assignments as subtasks
    forecast.assignments_count = forecast.assignments_count || 0;

    return data;
  };

  const generateCostChartData = (forecast) => {
    if (!forecast || !forecast.staff_costs) return null;

    return {
      labels: Object.keys(forecast.staff_costs),
      datasets: [{
        label: 'Cost by Staff Member',
        data: Object.values(forecast.staff_costs),
        backgroundColor: [
          '#3498db', '#e74c3c', '#27ae60', '#f39c12',
          '#9b59b6', '#1abc9c', '#34495e', '#e67e22'
        ],
        borderWidth: 1
      }]
    };
  };

  const generateWeeklyChartData = (forecast) => {
    if (!forecast || !forecast.weekly_staffing) return null;

    const weeks = Object.keys(forecast.weekly_staffing);
    const hours = Object.values(forecast.weekly_staffing);

    return {
      labels: weeks,
      datasets: [{
        label: 'Required Hours',
        data: hours,
        borderColor: '#3498db',
        backgroundColor: 'rgba(52, 152, 219, 0.1)',
        tension: 0.4,
        fill: true
      }]
    };
  };

  const exportToCSV = (data, filename) => {
    if (!data) return;

    const csvContent = [
      Object.keys(data).join(','),
      Object.values(data).join(',')
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="forecasts">
      <div className="forecasts-header">
        <h1>Staffing Forecasts</h1>
        <div className="view-toggle">
          <button
            className={`toggle-btn ${viewMode === 'project' ? 'active' : ''}`}
            onClick={() => setViewMode('project')}
          >
            Project Forecast
          </button>
          <button
            className={`toggle-btn ${viewMode === 'organization' ? 'active' : ''}`}
            onClick={() => setViewMode('organization')}
          >
            Organization Forecast
          </button>
        </div>
      </div>

      {viewMode === 'project' && (
        <div className="forecast-controls">
          <div className="control-grid">
            <Select
              label="Select Project"
              name="project"
              value={selectedProject}
              onChange={handleProjectChange}
              options={projects.map(p => ({ value: p.id, label: `${p.name} (${p.status})` }))}
              placeholder="Choose a project"
            />

            <DatePicker
              label="Start Date (Optional)"
              name="start_date"
              value={startDate}
              onChange={handleDateChange}
            />

            <DatePicker
              label="End Date (Optional)"
              name="end_date"
              value={endDate}
              onChange={handleDateChange}
            />

            <div className="control-actions">
              <button
                onClick={loadProjectForecast}
                className="generate-btn"
                disabled={!selectedProject || loading}
              >
                {loading ? 'Generating...' : 'Generate Forecast'}
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <ErrorMessage
          message={error}
          onRetry={viewMode === 'project' ? loadProjectForecast : loadOrgForecast}
        />
      )}

      {viewMode === 'project' && forecastData && (
        <div className="forecast-results">
          <div className="forecast-summary">
            <h2>{forecastData.project_name} - Forecast Summary</h2>
            <div className="summary-grid">
              <div className="summary-card">
                <h3>Total Estimated Cost</h3>
                <div className="summary-value">${forecastData.total_estimated_cost?.toLocaleString() || '0'}</div>
              </div>
              <div className="summary-card">
                <h3>Assignments</h3>
                <div className="summary-value">{forecastData.assignments_count}</div>
              </div>
              <div className="summary-card">
                <h3>Forecast Period</h3>
                <div className="summary-value">
                  {forecastData.forecast_period.start_date} to {forecastData.forecast_period.end_date}
                </div>
              </div>
            </div>

            <div className="export-actions">
              <button
                onClick={() => exportToCSV(forecastData, 'project-forecast.csv')}
                className="export-btn"
              >
                Export to CSV
              </button>
            </div>
          </div>

          <div className="forecast-charts">
            <div className="chart-section">
              <h3>Weekly Staffing Requirements</h3>
              <div className="chart-container">
                {generateWeeklyChartData(forecastData) && (
                  <Line
                    data={generateWeeklyChartData(forecastData)}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      scales: {
                        y: {
                          beginAtZero: true,
                          title: {
                            display: true,
                            text: 'Hours Required'
                          }
                        }
                      }
                    }}
                  />
                )}
              </div>
            </div>

            <div className="chart-section">
              <h3>Cost Breakdown by Staff</h3>
              <div className="chart-container">
                {generateCostChartData(forecastData) && (
                  <Bar
                    data={generateCostChartData(forecastData)}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      scales: {
                        y: {
                          beginAtZero: true,
                          title: {
                            display: true,
                            text: 'Cost ($)'
                          }
                        }
                      }
                    }}
                  />
                )}
              </div>
            </div>

            <div className="chart-section chart-full">
              <h3>Project Timeline Gantt Chart</h3>
              <div className="gantt-container">
                {generateGanttData(forecastData) && (
                  <Chart
                    chartType="Gantt"
                    width="100%"
                    height="400px"
                    data={generateGanttData(forecastData)}
                    options={{
                      height: 400,
                      gantt: {
                        trackHeight: 30,
                      },
                    }}
                  />
                )}
              </div>
            </div>
          </div>

          <div className="staff-breakdown">
            <h3>Staff Breakdown by Week</h3>
            <div className="breakdown-table">
              <table>
                <thead>
                  <tr>
                    <th>Week</th>
                    <th>Total Hours</th>
                    <th>Staff Details</th>
                  </tr>
                </thead>
                <tbody>
                  {forecastData.staff_breakdown && Object.entries(forecastData.staff_breakdown).map(([week, staff]) => (
                    <tr key={week}>
                      <td>{week}</td>
                      <td>{forecastData.weekly_staffing[week]?.toFixed(1) || '0'}</td>
                      <td>
                        {Object.entries(staff).map(([name, hours]) => (
                          <span key={name} className="staff-detail">
                            {name}: {hours.toFixed(1)}h
                          </span>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {viewMode === 'organization' && orgForecastData && (
        <div className="org-forecast">
          <h2>Organization-wide Forecast</h2>
          <div className="org-summary">
            <div className="summary-grid">
              <div className="summary-card">
                <h3>Total Projects</h3>
                <div className="summary-value">{orgForecastData.projects_count}</div>
              </div>
              <div className="summary-card">
                <h3>Total Estimated Cost</h3>
                <div className="summary-value">${orgForecastData.total_estimated_cost?.toLocaleString() || '0'}</div>
              </div>
              <div className="summary-card">
                <h3>Forecast Period</h3>
                <div className="summary-value">
                  {orgForecastData.forecast_period.start_date} to {orgForecastData.forecast_period.end_date}
                </div>
              </div>
            </div>
          </div>

          <div className="staff-utilization">
            <h3>Staff Utilization Summary</h3>
            <div className="utilization-grid">
              {orgForecastData.staff_utilization && Object.values(orgForecastData.staff_utilization).map((staff, index) => (
                <div key={index} className="utilization-card">
                  <h4>{staff.staff_name}</h4>
                  <div className="utilization-details">
                    <div className="utilization-bar">
                      <div
                        className={`utilization-fill ${staff.utilization_rate > 1 ? 'overallocated' : ''}`}
                        style={{ width: `${Math.min(staff.utilization_rate * 100, 100)}%` }}
                      ></div>
                    </div>
                    <div className="utilization-text">
                      <span>{(staff.utilization_rate * 100).toFixed(1)}% utilized</span>
                      <span>{staff.assigned_hours.toFixed(1)}h assigned</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Forecasts;
