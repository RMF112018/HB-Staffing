import React, { useState, useEffect } from 'react';
import jsPDF from 'jspdf';
import 'jspdf-autotable';
import Papa from 'papaparse';
import { staffAPI, projectAPI, assignmentAPI, forecastAPI } from '../services/api';
import Select from './common/Select';
import DatePicker from './common/DatePicker';
import LoadingSpinner from './common/LoadingSpinner';
import ErrorMessage from './common/ErrorMessage';
import './Reports.css';

const REPORT_TYPES = [
  { value: 'staffing-summary', label: 'Staffing Summary' },
  { value: 'cost-analysis', label: 'Cost Analysis' },
  { value: 'project-status', label: 'Project Status Report' },
  { value: 'staff-utilization', label: 'Staff Utilization' },
  { value: 'staffing-gaps', label: 'Staffing Gaps Analysis' }
];

const Reports = () => {
  const [reportType, setReportType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [projectFilter, setProjectFilter] = useState('');
  const [staffFilter, setStaffFilter] = useState('');
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [projects, setProjects] = useState([]);
  const [staff, setStaff] = useState([]);

  useEffect(() => {
    loadFilters();
  }, []);

  const loadFilters = async () => {
    try {
      const [projectsResponse, staffResponse] = await Promise.all([
        projectAPI.getAll(),
        staffAPI.getAll()
      ]);
      setProjects(projectsResponse.data);
      setStaff(staffResponse.data);
    } catch (err) {
      console.error('Error loading filters:', err);
    }
  };

  const generateReport = async () => {
    if (!reportType) {
      setError('Please select a report type');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setReportData(null);

      const params = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      let data;

      switch (reportType) {
        case 'staffing-summary':
          data = await generateStaffingSummary(params);
          break;
        case 'cost-analysis':
          data = await generateCostAnalysis(params);
          break;
        case 'project-status':
          data = await generateProjectStatus(params);
          break;
        case 'staff-utilization':
          data = await generateStaffUtilization(params);
          break;
        case 'staffing-gaps':
          data = await generateStaffingGaps(params);
          break;
        default:
          throw new Error('Unknown report type');
      }

      setReportData(data);
    } catch (err) {
      console.error('Error generating report:', err);
      setError('Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  const generateStaffingSummary = async (params) => {
    const [staffResponse, assignmentsResponse] = await Promise.all([
      staffAPI.getAll(),
      assignmentAPI.getAll()
    ]);

    const staff = staffResponse.data;
    const assignments = assignmentsResponse.data;

    // Group assignments by project
    const projectAssignments = assignments.reduce((acc, assignment) => {
      const projectName = assignment.project_name;
      if (!acc[projectName]) {
        acc[projectName] = [];
      }
      acc[projectName].push(assignment);
      return acc;
    }, {});

    return {
      title: 'Staffing Summary Report',
      generatedAt: new Date().toLocaleString(),
      period: params.start_date && params.end_date ?
        `${params.start_date} to ${params.end_date}` : 'All time',
      summary: {
        totalStaff: staff.length,
        totalAssignments: assignments.length,
        activeProjects: Object.keys(projectAssignments).length
      },
      data: {
        staff: staff,
        assignments: assignments,
        projectBreakdown: projectAssignments
      }
    };
  };

  const generateCostAnalysis = async (params) => {
    const projects = await projectAPI.getAll();
    const costData = [];

    for (const project of projects.data) {
      try {
        const costResponse = await projectAPI.getCost(project.id);
        costData.push({
          project: project,
          cost: costResponse.data
        });
      } catch (err) {
        console.error(`Error getting cost for project ${project.id}:`, err);
      }
    }

    const totalCost = costData.reduce((sum, item) => sum + (item.cost.total_cost || 0), 0);
    const budgetVariance = costData.reduce((sum, item) =>
      sum + (item.cost.budget_variance || 0), 0);

    return {
      title: 'Cost Analysis Report',
      generatedAt: new Date().toLocaleString(),
      period: params.start_date && params.end_date ?
        `${params.start_date} to ${params.end_date}` : 'All time',
      summary: {
        totalProjects: costData.length,
        totalCost: totalCost,
        budgetVariance: budgetVariance
      },
      data: costData
    };
  };

  const generateProjectStatus = async (params) => {
    const response = await projectAPI.getAll();
    const projects = response.data;

    const statusCounts = projects.reduce((acc, project) => {
      acc[project.status] = (acc[project.status] || 0) + 1;
      return acc;
    }, {});

    return {
      title: 'Project Status Report',
      generatedAt: new Date().toLocaleString(),
      period: params.start_date && params.end_date ?
        `${params.start_date} to ${params.end_date}` : 'Current',
      summary: statusCounts,
      data: projects.map(project => ({
        ...project,
        duration: project.start_date && project.end_date ?
          Math.round((new Date(project.end_date) - new Date(project.start_date)) / (1000 * 60 * 60 * 24)) + ' days' :
          'Not set'
      }))
    };
  };

  const generateStaffUtilization = async (params) => {
    if (!params.start_date || !params.end_date) {
      // Set default 3-month period
      const endDate = new Date();
      const startDate = new Date();
      startDate.setMonth(startDate.getMonth() - 3);
      params.start_date = startDate.toISOString().split('T')[0];
      params.end_date = endDate.toISOString().split('T')[0];
    }

    const response = await forecastAPI.getOrganization(params);
    const orgForecast = response.data;

    return {
      title: 'Staff Utilization Report',
      generatedAt: new Date().toLocaleString(),
      period: `${params.start_date} to ${params.end_date}`,
      summary: {
        totalStaff: Object.keys(orgForecast.staff_utilization || {}).length,
        averageUtilization: Object.values(orgForecast.staff_utilization || {}).length > 0 ?
          Object.values(orgForecast.staff_utilization).reduce((sum, staff) =>
            sum + (staff.utilization_rate || 0), 0) /
          Object.values(orgForecast.staff_utilization).length : 0
      },
      data: orgForecast.staff_utilization || {}
    };
  };

  const generateStaffingGaps = async (params) => {
    const response = await forecastAPI.getGaps(params);
    const gaps = response.data.gaps || [];

    return {
      title: 'Staffing Gaps Analysis',
      generatedAt: new Date().toLocaleString(),
      period: params.start_date && params.end_date ?
        `${params.start_date} to ${params.end_date}` : 'Current',
      summary: {
        totalGaps: gaps.length,
        projectsAffected: new Set(gaps.map(gap => gap.project_id)).size
      },
      data: gaps
    };
  };

  const exportToCSV = () => {
    if (!reportData || !reportData.data) return;

    let csvData = [];
    let filename = `${reportType}-report.csv`;

    switch (reportType) {
      case 'staffing-summary':
        csvData = [
          ['Staff Name', 'Role', 'Skills'],
          ...reportData.data.staff.map(staff => [
            staff.name,
            staff.role,
            (staff.skills || []).join('; ')
          ])
        ];
        break;

      case 'cost-analysis':
        csvData = [
          ['Project Name', 'Total Cost', 'Budget', 'Variance'],
          ...reportData.data.map(item => [
            item.project.name,
            item.cost.total_cost || 0,
            item.project.budget || 'N/A',
            item.cost.budget_variance || 'N/A'
          ])
        ];
        break;

      case 'project-status':
        csvData = [
          ['Project Name', 'Status', 'Start Date', 'End Date', 'Budget', 'Location'],
          ...reportData.data.map(project => [
            project.name,
            project.status,
            project.start_date || 'N/A',
            project.end_date || 'N/A',
            project.budget || 'N/A',
            project.location || 'N/A'
          ])
        ];
        break;

      case 'staff-utilization':
        csvData = [
          ['Staff Name', 'Assigned Hours', 'Available Hours', 'Utilization %', 'Status'],
          ...Object.values(reportData.data).map(staff => [
            staff.staff_name,
            staff.assigned_hours?.toFixed(1) || 0,
            staff.available_hours?.toFixed(1) || 0,
            ((staff.utilization_rate || 0) * 100).toFixed(1),
            staff.overallocated ? 'Overallocated' : 'Normal'
          ])
        ];
        break;

      case 'staffing-gaps':
        csvData = [
          ['Project', 'Week', 'Message'],
          ...reportData.data.map(gap => [
            gap.project_name || gap.project_id,
            gap.week || 'N/A',
            gap.message
          ])
        ];
        break;
    }

    const csv = Papa.unparse(csvData);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportToPDF = () => {
    if (!reportData) return;

    const doc = new jsPDF();

    // Title
    doc.setFontSize(20);
    doc.text(reportData.title, 20, 30);

    // Metadata
    doc.setFontSize(12);
    doc.text(`Generated: ${reportData.generatedAt}`, 20, 45);
    doc.text(`Period: ${reportData.period}`, 20, 55);

    // Summary
    doc.text('Summary:', 20, 70);
    let yPos = 80;
    Object.entries(reportData.summary).forEach(([key, value]) => {
      const displayValue = typeof value === 'number' ? value.toLocaleString() : value;
      doc.text(`${key}: ${displayValue}`, 30, yPos);
      yPos += 10;
    });

    // Data table
    let tableData = [];
    let tableColumns = [];

    switch (reportType) {
      case 'staffing-summary':
        tableColumns = ['Name', 'Role', 'Skills'];
        tableData = reportData.data.staff.map(staff => [
          staff.name,
          staff.role,
          (staff.skills || []).join(', ')
        ]);
        break;

      case 'cost-analysis':
        tableColumns = ['Project', 'Cost', 'Budget'];
        tableData = reportData.data.map(item => [
          item.project.name,
          `$${item.cost.total_cost?.toLocaleString() || '0'}`,
          item.project.budget ? `$${item.project.budget.toLocaleString()}` : 'N/A'
        ]);
        break;

      case 'project-status':
        tableColumns = ['Project', 'Status', 'Budget', 'Location'];
        tableData = reportData.data.map(project => [
          project.name,
          project.status,
          project.budget ? `$${project.budget.toLocaleString()}` : 'N/A',
          project.location || 'N/A'
        ]);
        break;

      case 'staff-utilization':
        tableColumns = ['Staff', 'Utilization %', 'Status'];
        tableData = Object.values(reportData.data).map(staff => [
          staff.staff_name,
          `${((staff.utilization_rate || 0) * 100).toFixed(1)}%`,
          staff.overallocated ? 'Overallocated' : 'Normal'
        ]);
        break;

      case 'staffing-gaps':
        tableColumns = ['Project', 'Issue'];
        tableData = reportData.data.map(gap => [
          gap.project_name || gap.project_id,
          gap.message
        ]);
        break;
    }

    if (tableData.length > 0) {
      doc.autoTable({
        head: [tableColumns],
        body: tableData,
        startY: yPos + 10,
        styles: { fontSize: 8 },
        headStyles: { fillColor: [52, 152, 219] }
      });
    }

    doc.save(`${reportType}-report.pdf`);
  };

  const renderReportContent = () => {
    if (!reportData) return null;

    switch (reportType) {
      case 'staffing-summary':
        return (
          <div className="report-content">
            <div className="summary-cards">
              <div className="summary-card">
                <h4>Total Staff</h4>
                <div className="summary-value">{reportData.summary.totalStaff}</div>
              </div>
              <div className="summary-card">
                <h4>Active Assignments</h4>
                <div className="summary-value">{reportData.summary.totalAssignments}</div>
              </div>
              <div className="summary-card">
                <h4>Projects</h4>
                <div className="summary-value">{reportData.summary.activeProjects}</div>
              </div>
            </div>
            <div className="report-table">
              <h4>Staff Details</h4>
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Skills</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.data.staff.map((person, index) => (
                    <tr key={index}>
                      <td>{person.name}</td>
                      <td>{person.role}</td>
                      <td>{(person.skills || []).join(', ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );

      case 'cost-analysis':
        return (
          <div className="report-content">
            <div className="summary-cards">
              <div className="summary-card">
                <h4>Total Projects</h4>
                <div className="summary-value">{reportData.summary.totalProjects}</div>
              </div>
              <div className="summary-card">
                <h4>Total Cost</h4>
                <div className="summary-value">${reportData.summary.totalCost.toLocaleString()}</div>
              </div>
              <div className="summary-card">
                <h4>Budget Variance</h4>
                <div className="summary-value">${reportData.summary.budgetVariance?.toLocaleString() || '0'}</div>
              </div>
            </div>
            <div className="report-table">
              <h4>Cost Breakdown</h4>
              <table>
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Total Cost</th>
                    <th>Budget</th>
                    <th>Variance</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.data.map((item, index) => (
                    <tr key={index}>
                      <td>{item.project.name}</td>
                      <td>${item.cost.total_cost?.toLocaleString() || '0'}</td>
                      <td>{item.project.budget ? `$${item.project.budget.toLocaleString()}` : 'N/A'}</td>
                      <td>{item.cost.budget_variance ? `$${item.cost.budget_variance.toLocaleString()}` : 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );

      case 'staffing-gaps':
        return (
          <div className="report-content">
            <div className="summary-cards">
              <div className="summary-card alert">
                <h4>Staffing Gaps Found</h4>
                <div className="summary-value">{reportData.summary.totalGaps}</div>
              </div>
              <div className="summary-card">
                <h4>Projects Affected</h4>
                <div className="summary-value">{reportData.summary.projectsAffected}</div>
              </div>
            </div>
            <div className="gaps-list">
              {reportData.data.map((gap, index) => (
                <div key={index} className="gap-item">
                  <h5>{gap.project_name || `Project ${gap.project_id}`}</h5>
                  <p>{gap.message}</p>
                  {gap.week && <span className="gap-week">Week: {gap.week}</span>}
                </div>
              ))}
            </div>
          </div>
        );

      default:
        return (
          <div className="report-content">
            <p>Report generated successfully. Use export buttons to download.</p>
          </div>
        );
    }
  };

  return (
    <div className="reports">
      <div className="reports-header">
        <h1>Reports & Analytics</h1>
      </div>

      <div className="report-controls">
        <div className="control-grid">
          <Select
            label="Report Type"
            name="reportType"
            value={reportType}
            onChange={(name, value) => setReportType(value)}
            options={REPORT_TYPES}
            placeholder="Select report type"
          />

          <DatePicker
            label="Start Date"
            name="startDate"
            value={startDate}
            onChange={(name, value) => setStartDate(value)}
          />

          <DatePicker
            label="End Date"
            name="endDate"
            value={endDate}
            onChange={(name, value) => setEndDate(value)}
          />

          <div className="control-actions">
            <button
              onClick={generateReport}
              className="generate-btn"
              disabled={!reportType || loading}
            >
              {loading ? 'Generating...' : 'Generate Report'}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <ErrorMessage
          message={error}
          onRetry={generateReport}
        />
      )}

      {loading && (
        <LoadingSpinner message="Generating report..." />
      )}

      {reportData && (
        <div className="report-results">
          <div className="report-header">
            <div className="report-info">
              <h2>{reportData.title}</h2>
              <div className="report-meta">
                <span>Generated: {reportData.generatedAt}</span>
                <span>Period: {reportData.period}</span>
              </div>
            </div>
            <div className="report-actions">
              <button onClick={exportToCSV} className="export-btn csv">
                Export CSV
              </button>
              <button onClick={exportToPDF} className="export-btn pdf">
                Export PDF
              </button>
            </div>
          </div>

          {renderReportContent()}
        </div>
      )}
    </div>
  );
};

export default Reports;
