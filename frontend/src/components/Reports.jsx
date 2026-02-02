import React, { useState, useEffect } from 'react';
import { projectAPI, reportsAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import './Reports.css';

const Reports = () => {
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  // Filter state
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [includeSubProjects, setIncludeSubProjects] = useState(true);

  // Report data state
  const [reportData, setReportData] = useState(null);
  const [costViewMode, setCostViewMode] = useState('both'); // 'internal', 'billable', 'both'

  // Load projects on mount
  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await projectAPI.getAll();
      setProjects(response.data);
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  };

  const handleGenerateReport = async () => {
    if (!selectedProjectId) {
      alert('Please select a project or project folder');
      return;
    }

    startLoading('report');
    clearError();

    try {
      const params = {
        project_id: selectedProjectId,
        include_sub_projects: includeSubProjects
      };
      
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const response = await reportsAPI.getStaffPlanningReport(params);
      setReportData(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('report');
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatMonth = (monthStr) => {
    const date = new Date(monthStr + '-01');
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  // Get role color for Gantt chart
  const getRoleColor = (roleIndex) => {
    const colors = [
      '#3498db', '#e74c3c', '#2ecc71', '#9b59b6', '#f39c12',
      '#1abc9c', '#e67e22', '#34495e', '#16a085', '#c0392b'
    ];
    return colors[roleIndex % colors.length];
  };

  // Calculate bar position for Gantt chart
  const getBarStyle = (entry, months) => {
    const startMonth = entry.start_date.substring(0, 7);
    const endMonth = entry.end_date.substring(0, 7);
    
    const startIndex = months.indexOf(startMonth);
    const endIndex = months.indexOf(endMonth);
    
    // Handle cases where dates are outside the report period
    const effectiveStart = Math.max(0, startIndex === -1 ? 0 : startIndex);
    const effectiveEnd = Math.min(months.length - 1, endIndex === -1 ? months.length - 1 : endIndex);
    
    const startPercent = (effectiveStart / months.length) * 100;
    const widthPercent = ((effectiveEnd - effectiveStart + 1) / months.length) * 100;
    
    return {
      left: `${startPercent}%`,
      width: `${Math.max(widthPercent, 2)}%`
    };
  };

  // Group staff entries by role for Gantt chart
  const getEntriesByRole = () => {
    if (!reportData?.staff_entries) return {};
    
    const byRole = {};
    reportData.staff_entries.forEach(entry => {
      if (!byRole[entry.role_name]) {
        byRole[entry.role_name] = {
          role_id: entry.role_id,
          entries: []
        };
      }
      byRole[entry.role_name].entries.push(entry);
    });
    return byRole;
  };

  const selectedProject = projects.find(p => p.id === parseInt(selectedProjectId));

  return (
    <div className="reports">
      <h1>Staff Planning Report</h1>

      {/* Filters Section */}
      <div className="report-filters">
        <div className="filter-row">
          <div className="filter-group">
            <label htmlFor="project">Project / Project Folder</label>
            <select
              id="project"
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
            >
              <option value="">-- Select Project --</option>
              {projects.map(project => (
                <option key={project.id} value={project.id}>
                  {project.is_folder ? '📁 ' : '📄 '}{project.name}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="startDate">Start Date</label>
            <input
              type="date"
              id="startDate"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          <div className="filter-group">
            <label htmlFor="endDate">End Date</label>
            <input
              type="date"
              id="endDate"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>

        <div className="filter-row">
          {selectedProject?.is_folder && (
            <div className="filter-group checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={includeSubProjects}
                  onChange={(e) => setIncludeSubProjects(e.target.checked)}
                />
                Include Sub-Projects
              </label>
            </div>
          )}

          <button 
            className="btn-primary generate-btn"
            onClick={handleGenerateReport}
            disabled={isLoading('report')}
          >
            {isLoading('report') ? 'Generating...' : 'Generate Report'}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">
          <p>{error.message}</p>
        </div>
      )}

      {/* Report Content */}
      {reportData && (
        <div className="report-content">
          {/* Project Info */}
          <div className="report-header-info">
            <h2>
              {reportData.project.is_folder ? '📁' : '📄'} {reportData.project.name}
            </h2>
            <p className="report-period">
              {formatMonth(reportData.period.start_date)} - {formatMonth(reportData.period.end_date)}
            </p>
            {reportData.sub_projects.length > 0 && (
              <p className="sub-projects-count">
                Includes {reportData.sub_projects.length} sub-project(s)
              </p>
            )}
          </div>

          {/* Summary Cards */}
          <div className="summary-cards">
            <div className="summary-card">
              <div className="card-label">Total Internal Cost</div>
              <div className="card-value cost">{formatCurrency(reportData.summary.total_internal_cost)}</div>
            </div>
            <div className="summary-card">
              <div className="card-label">Total Billable</div>
              <div className="card-value billable">{formatCurrency(reportData.summary.total_billable)}</div>
            </div>
            <div className="summary-card">
              <div className="card-label">Total Margin</div>
              <div className="card-value margin">
                {formatCurrency(reportData.summary.total_margin)}
                <span className="margin-percent">({reportData.summary.margin_percentage}%)</span>
              </div>
            </div>
            <div className="summary-card">
              <div className="card-label">Staff Required</div>
              <div className="card-value staff">
                {reportData.summary.total_staff_count + reportData.summary.total_ghost_count}
                <span className="staff-breakdown">
                  ({reportData.summary.total_staff_count} real, {reportData.summary.total_ghost_count} planned)
                </span>
              </div>
            </div>
          </div>

          {/* Gantt Chart Section */}
          <div className="report-section gantt-section">
            <h3>Staff Allocation Timeline</h3>
            <div className="gantt-chart">
              {/* Month Headers */}
              <div className="gantt-header">
                <div className="gantt-role-label">Role / Staff</div>
                <div className="gantt-months">
                  {reportData.period.months.map(month => (
                    <div key={month} className="gantt-month-header">
                      {formatMonth(month)}
                    </div>
                  ))}
                </div>
              </div>

              {/* Role Rows */}
              <div className="gantt-body">
                {Object.entries(getEntriesByRole()).map(([roleName, roleData], roleIndex) => (
                  <div key={roleName} className="gantt-role-group">
                    <div className="gantt-role-row">
                      <div className="gantt-role-label">
                        <span 
                          className="role-color-indicator" 
                          style={{ backgroundColor: getRoleColor(roleIndex) }}
                        />
                        {roleName}
                      </div>
                      <div className="gantt-months-bg">
                        {reportData.period.months.map(month => (
                          <div key={month} className="gantt-month-cell" />
                        ))}
                      </div>
                    </div>
                    
                    {/* Staff entries for this role */}
                    {roleData.entries.map((entry, entryIndex) => (
                      <div key={`${entry.type}-${entry.id}`} className="gantt-staff-row">
                        <div className="gantt-staff-label">
                          <span className={`staff-type-icon ${entry.type}`}>
                            {entry.type === 'ghost' ? '👻' : '👤'}
                          </span>
                          {entry.name}
                        </div>
                        <div className="gantt-bar-container">
                          <div 
                            className={`gantt-bar ${entry.type}`}
                            style={{
                              ...getBarStyle(entry, reportData.period.months),
                              backgroundColor: getRoleColor(roleIndex)
                            }}
                            title={`${entry.name}\n${entry.hours_per_week} hrs/week\nInternal: $${entry.internal_hourly_cost}/hr\nBillable: $${entry.billable_rate}/hr`}
                          >
                            <span className="bar-label">{entry.name}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>

            {/* Legend */}
            <div className="gantt-legend">
              <div className="legend-item">
                <span className="legend-bar real" />
                <span>Real Staff</span>
              </div>
              <div className="legend-item">
                <span className="legend-bar ghost" />
                <span>Planned (Ghost Staff)</span>
              </div>
            </div>
          </div>

          {/* Cost Table by Role */}
          <div className="report-section cost-table-section">
            <div className="section-header">
              <h3>Monthly Costs by Role</h3>
              <div className="cost-view-toggle">
                <button 
                  className={costViewMode === 'internal' ? 'active' : ''}
                  onClick={() => setCostViewMode('internal')}
                >
                  Internal
                </button>
                <button 
                  className={costViewMode === 'billable' ? 'active' : ''}
                  onClick={() => setCostViewMode('billable')}
                >
                  Billable
                </button>
                <button 
                  className={costViewMode === 'both' ? 'active' : ''}
                  onClick={() => setCostViewMode('both')}
                >
                  Both
                </button>
              </div>
            </div>

            <div className="cost-table-wrapper">
              <table className="cost-table">
                <thead>
                  <tr>
                    <th className="role-column">Role</th>
                    {reportData.period.months.map(month => (
                      <th key={month}>{formatMonth(month)}</th>
                    ))}
                    <th className="total-column">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.roles.map((role, index) => (
                    <tr key={role.role_id || index}>
                      <td className="role-column">
                        <span 
                          className="role-color-indicator" 
                          style={{ backgroundColor: getRoleColor(index) }}
                        />
                        {role.role_name}
                      </td>
                      {reportData.period.months.map(month => {
                        const monthData = role.monthly_costs[month] || { internal: 0, billable: 0 };
                        return (
                          <td key={month} className={monthData.internal === 0 ? 'zero-value' : ''}>
                            {costViewMode === 'internal' && formatCurrency(monthData.internal)}
                            {costViewMode === 'billable' && formatCurrency(monthData.billable)}
                            {costViewMode === 'both' && (
                              <div className="dual-cost">
                                <span className="internal">{formatCurrency(monthData.internal)}</span>
                                <span className="billable">{formatCurrency(monthData.billable)}</span>
                              </div>
                            )}
                          </td>
                        );
                      })}
                      <td className="total-column">
                        {costViewMode === 'internal' && formatCurrency(role.total_internal)}
                        {costViewMode === 'billable' && formatCurrency(role.total_billable)}
                        {costViewMode === 'both' && (
                          <div className="dual-cost">
                            <span className="internal">{formatCurrency(role.total_internal)}</span>
                            <span className="billable">{formatCurrency(role.total_billable)}</span>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="totals-row">
                    <td className="role-column"><strong>Monthly Totals</strong></td>
                    {reportData.period.months.map(month => {
                      const monthData = reportData.monthly_breakdown[month] || { internal_cost: 0, billable: 0 };
                      return (
                        <td key={month}>
                          {costViewMode === 'internal' && formatCurrency(monthData.internal_cost)}
                          {costViewMode === 'billable' && formatCurrency(monthData.billable)}
                          {costViewMode === 'both' && (
                            <div className="dual-cost">
                              <span className="internal">{formatCurrency(monthData.internal_cost)}</span>
                              <span className="billable">{formatCurrency(monthData.billable)}</span>
                            </div>
                          )}
                        </td>
                      );
                    })}
                    <td className="total-column">
                      {costViewMode === 'internal' && formatCurrency(reportData.summary.total_internal_cost)}
                      {costViewMode === 'billable' && formatCurrency(reportData.summary.total_billable)}
                      {costViewMode === 'both' && (
                        <div className="dual-cost">
                          <span className="internal">{formatCurrency(reportData.summary.total_internal_cost)}</span>
                          <span className="billable">{formatCurrency(reportData.summary.total_billable)}</span>
                        </div>
                      )}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* Staff Distribution List */}
          <div className="report-section staff-list-section">
            <h3>Staff Distribution</h3>
            <div className="staff-list">
              {reportData.staff_entries.map((entry, index) => (
                <div key={`${entry.type}-${entry.id}`} className={`staff-entry ${entry.type}`}>
                  <div className="staff-entry-header">
                    <span className={`type-badge ${entry.type}`}>
                      {entry.type === 'ghost' ? '👻 Planned' : '👤 Staff'}
                    </span>
                    <h4>{entry.name}</h4>
                    <span className="role-badge">{entry.role_name}</span>
                  </div>
                  <div className="staff-entry-details">
                    <div className="detail-item">
                      <span className="label">Project:</span>
                      <span className="value">{entry.project_name}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">Period:</span>
                      <span className="value">{entry.start_date} to {entry.end_date}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">Hours/Week:</span>
                      <span className="value">{entry.hours_per_week}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">Allocation:</span>
                      <span className="value">{entry.allocation_percentage}%</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">Internal Rate:</span>
                      <span className="value">${entry.internal_hourly_cost}/hr</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">Billable Rate:</span>
                      <span className="value">${entry.billable_rate}/hr</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!reportData && !isLoading('report') && (
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <h3>Generate a Staff Planning Report</h3>
          <p>Select a project or project folder and click "Generate Report" to view detailed staff planning data including costs, allocations, and timeline.</p>
        </div>
      )}
    </div>
  );
};

export default Reports;
