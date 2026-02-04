import React, { useState, useEffect, useRef } from 'react';
import { projectAPI, reportsAPI, planningAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
import Papa from 'papaparse';
import './Reports.css';

const Reports = () => {
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  // Report type state
  const [reportType, setReportType] = useState('project'); // 'project' or 'planning'

  // Project report filter state
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [includeSubProjects, setIncludeSubProjects] = useState(true);

  // Planning exercise filter state
  const [planningExercises, setPlanningExercises] = useState([]);
  const [selectedExerciseId, setSelectedExerciseId] = useState('');
  const [overlapMode, setOverlapMode] = useState('efficient');

  // Report data state
  const [reportData, setReportData] = useState(null);
  const [planningReportData, setPlanningReportData] = useState(null);
  const [costViewMode, setCostViewMode] = useState('both'); // 'internal', 'billable', 'both'
  const [isExporting, setIsExporting] = useState(false);
  
  // Refs for export
  const reportContentRef = useRef(null);
  const ganttRef = useRef(null);
  const planningGanttRef = useRef(null);

  // Load projects and planning exercises on mount
  useEffect(() => {
    fetchProjects();
    fetchPlanningExercises();
  }, []);

  // Clear report data when switching report types
  useEffect(() => {
    setReportData(null);
    setPlanningReportData(null);
    clearError();
  }, [reportType]);

  const fetchProjects = async () => {
    try {
      const response = await projectAPI.getAll();
      setProjects(response.data);
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  };

  const fetchPlanningExercises = async () => {
    try {
      const response = await planningAPI.getAll();
      setPlanningExercises(response.data);
    } catch (err) {
      console.error('Failed to load planning exercises:', err);
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

  const handleGeneratePlanningReport = async () => {
    if (!selectedExerciseId) {
      alert('Please select a planning exercise');
      return;
    }

    startLoading('report');
    clearError();

    try {
      // Fetch all three APIs in parallel
      const [analysisRes, requirementsRes, costsRes] = await Promise.all([
        planningAPI.getAnalysis(selectedExerciseId),
        planningAPI.getStaffRequirements(selectedExerciseId, overlapMode),
        planningAPI.getCosts(selectedExerciseId)
      ]);

      // Combine into unified report data
      setPlanningReportData({
        exercise: planningExercises.find(e => e.id === parseInt(selectedExerciseId)),
        analysis: analysisRes.data,
        staffRequirements: requirementsRes.data,
        costs: costsRes.data,
        overlapMode
      });
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
    }).format(value || 0);
  };

  const formatMonth = (monthStr) => {
    if (!monthStr) return '-';
    const date = new Date(monthStr + '-01');
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
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
  const selectedExercise = planningExercises.find(e => e.id === parseInt(selectedExerciseId));

  // Export to PDF - Project Report
  const handleExportPDF = async () => {
    if (!reportData || !reportContentRef.current) return;
    
    setIsExporting(true);
    
    try {
      const pdf = new jsPDF('l', 'mm', 'a4'); // Landscape for better table fit
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 15;
      let yPos = margin;
      
      // Title
      pdf.setFontSize(18);
      pdf.setFont('helvetica', 'bold');
      pdf.text(`Staff Planning Report: ${reportData.project.name}`, margin, yPos);
      yPos += 10;
      
      // Period
      pdf.setFontSize(11);
      pdf.setFont('helvetica', 'normal');
      pdf.text(`Period: ${formatMonth(reportData.period.start_date)} - ${formatMonth(reportData.period.end_date)}`, margin, yPos);
      yPos += 8;
      
      // Summary
      pdf.setFontSize(12);
      pdf.setFont('helvetica', 'bold');
      pdf.text('Summary', margin, yPos);
      yPos += 6;
      
      pdf.setFontSize(10);
      pdf.setFont('helvetica', 'normal');
      const summaryData = [
        `Total Internal Cost: ${formatCurrency(reportData.summary.total_internal_cost)}`,
        `Total Billable: ${formatCurrency(reportData.summary.total_billable)}`,
        `Total Margin: ${formatCurrency(reportData.summary.total_margin)} (${reportData.summary.margin_percentage}%)`,
        `Staff Required: ${reportData.summary.total_staff_count + reportData.summary.total_ghost_count}`,
        `Total Hours: ${reportData.summary.total_hours?.toLocaleString() || 0}`
      ];
      
      summaryData.forEach(line => {
        pdf.text(line, margin, yPos);
        yPos += 5;
      });
      yPos += 5;
      
      // Capture Gantt chart as image if available
      if (ganttRef.current) {
        try {
          const canvas = await html2canvas(ganttRef.current, {
            scale: 1.5,
            useCORS: true,
            logging: false
          });
          
          const imgData = canvas.toDataURL('image/png');
          const imgWidth = pageWidth - (margin * 2);
          const imgHeight = (canvas.height * imgWidth) / canvas.width;
          
          if (yPos + imgHeight > pageHeight - margin) {
            pdf.addPage();
            yPos = margin;
          }
          
          pdf.text('Staff Allocation Timeline', margin, yPos);
          yPos += 5;
          
          pdf.addImage(imgData, 'PNG', margin, yPos, imgWidth, Math.min(imgHeight, pageHeight - yPos - margin));
          yPos += imgHeight + 10;
        } catch (imgError) {
          console.warn('Could not capture Gantt chart:', imgError);
        }
      }
      
      // Add cost table on new page
      pdf.addPage();
      yPos = margin;
      
      pdf.setFontSize(12);
      pdf.setFont('helvetica', 'bold');
      pdf.text('Monthly Costs by Role', margin, yPos);
      yPos += 8;
      
      // Build table data
      const tableHeaders = ['Role', ...reportData.period.months.map(m => formatMonth(m)), 'Total'];
      const tableData = reportData.roles.map(role => [
        role.role_name,
        ...reportData.period.months.map(month => {
          const monthData = role.monthly_costs[month] || { internal: 0 };
          return formatCurrency(monthData.internal);
        }),
        formatCurrency(role.total_internal)
      ]);
      
      // Simple table rendering
      pdf.setFontSize(8);
      const colWidth = (pageWidth - (margin * 2)) / tableHeaders.length;
      
      // Headers
      pdf.setFont('helvetica', 'bold');
      tableHeaders.forEach((header, i) => {
        pdf.text(header.substring(0, 10), margin + (i * colWidth), yPos);
      });
      yPos += 5;
      
      // Data rows
      pdf.setFont('helvetica', 'normal');
      tableData.forEach(row => {
        if (yPos > pageHeight - margin) {
          pdf.addPage();
          yPos = margin;
        }
        row.forEach((cell, i) => {
          pdf.text(String(cell).substring(0, 12), margin + (i * colWidth), yPos);
        });
        yPos += 4;
      });
      
      // Save
      const fileName = `staff-planning-${reportData.project.name.replace(/[^a-z0-9]/gi, '-')}-${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(fileName);
      
    } catch (err) {
      console.error('PDF export failed:', err);
      alert('Failed to export PDF. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  // Export to PDF - Planning Exercise Report
  const handleExportPlanningPDF = async () => {
    if (!planningReportData) return;
    
    setIsExporting(true);
    
    try {
      const pdf = new jsPDF('l', 'mm', 'a4');
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 15;
      let yPos = margin;
      
      const { exercise, analysis, staffRequirements, costs } = planningReportData;
      
      // Title
      pdf.setFontSize(18);
      pdf.setFont('helvetica', 'bold');
      pdf.text(`Planning Exercise Report: ${exercise?.name || 'Unknown'}`, margin, yPos);
      yPos += 8;
      
      // Description
      if (exercise?.description) {
        pdf.setFontSize(10);
        pdf.setFont('helvetica', 'normal');
        const descLines = pdf.splitTextToSize(exercise.description, pageWidth - margin * 2);
        pdf.text(descLines, margin, yPos);
        yPos += descLines.length * 4 + 4;
      }
      
      // Period
      pdf.setFontSize(11);
      pdf.setFont('helvetica', 'normal');
      if (analysis?.period) {
        pdf.text(`Period: ${formatDate(analysis.period.start_date)} - ${formatDate(analysis.period.end_date)}`, margin, yPos);
        yPos += 6;
      }
      pdf.text(`Overlap Mode: ${overlapMode === 'efficient' ? 'Efficient (Share staff)' : 'Conservative (Dedicated staff)'}`, margin, yPos);
      yPos += 10;
      
      // Summary
      pdf.setFontSize(12);
      pdf.setFont('helvetica', 'bold');
      pdf.text('Summary', margin, yPos);
      yPos += 6;
      
      pdf.setFontSize(10);
      pdf.setFont('helvetica', 'normal');
      const summaryLines = [
        `Total Projects: ${exercise?.project_count || costs?.project_costs?.length || 0}`,
        `Total Hours: ${costs?.summary?.total_hours?.toLocaleString() || 0}`,
        `Total Internal Cost: ${formatCurrency(costs?.summary?.total_internal_cost)}`,
        `Total Billable: ${formatCurrency(costs?.summary?.total_billable)}`,
        `Total Margin: ${formatCurrency(costs?.summary?.total_margin)} (${costs?.summary?.margin_percentage?.toFixed(1) || 0}%)`,
        `Minimum Staff Needed: ${staffRequirements?.summary?.total_minimum_staff || 0}`,
        `New Hires Needed: ${staffRequirements?.summary?.total_new_hires_needed || 0}`
      ];
      
      summaryLines.forEach(line => {
        pdf.text(line, margin, yPos);
        yPos += 5;
      });
      yPos += 5;
      
      // Projects Overview
      if (costs?.project_costs?.length > 0) {
        pdf.setFontSize(12);
        pdf.setFont('helvetica', 'bold');
        pdf.text('Projects Overview', margin, yPos);
        yPos += 6;
        
        pdf.setFontSize(8);
        pdf.setFont('helvetica', 'bold');
        const projectHeaders = ['Project', 'Duration', 'Hours', 'Billable', 'Margin'];
        const projColWidth = (pageWidth - margin * 2) / projectHeaders.length;
        
        projectHeaders.forEach((h, i) => {
          pdf.text(h, margin + i * projColWidth, yPos);
        });
        yPos += 5;
        
        pdf.setFont('helvetica', 'normal');
        costs.project_costs.forEach(proj => {
          if (yPos > pageHeight - margin) {
            pdf.addPage();
            yPos = margin;
          }
          const row = [
            proj.project_name?.substring(0, 20) || 'Unknown',
            `${proj.duration_months || 0} mo`,
            (proj.total_hours || 0).toLocaleString(),
            formatCurrency(proj.total_billable),
            `${formatCurrency(proj.total_margin)} (${proj.margin_percentage || 0}%)`
          ];
          row.forEach((cell, i) => {
            pdf.text(String(cell), margin + i * projColWidth, yPos);
          });
          yPos += 4;
        });
        yPos += 5;
      }
      
      // Staff Requirements
      if (staffRequirements?.staff_requirements?.length > 0) {
        pdf.addPage();
        yPos = margin;
        
        pdf.setFontSize(12);
        pdf.setFont('helvetica', 'bold');
        pdf.text('Staff Requirements by Role', margin, yPos);
        yPos += 6;
        
        pdf.setFontSize(8);
        pdf.setFont('helvetica', 'bold');
        const reqHeaders = ['Role', 'Min Staff', 'Peak Month', 'Available', 'New Hires'];
        const reqColWidth = (pageWidth - margin * 2) / reqHeaders.length;
        
        reqHeaders.forEach((h, i) => {
          pdf.text(h, margin + i * reqColWidth, yPos);
        });
        yPos += 5;
        
        pdf.setFont('helvetica', 'normal');
        staffRequirements.staff_requirements.forEach(req => {
          if (yPos > pageHeight - margin) {
            pdf.addPage();
            yPos = margin;
          }
          const row = [
            req.role_name?.substring(0, 25) || 'Unknown',
            String(req.minimum_staff_needed || 0),
            req.peak_month || '-',
            String(req.available_staff_count || 0),
            String(req.new_hires_needed || 0)
          ];
          row.forEach((cell, i) => {
            pdf.text(cell, margin + i * reqColWidth, yPos);
          });
          yPos += 4;
        });
      }
      
      // Costs by Role
      if (costs?.role_costs?.length > 0) {
        pdf.addPage();
        yPos = margin;
        
        pdf.setFontSize(12);
        pdf.setFont('helvetica', 'bold');
        pdf.text('Costs by Role', margin, yPos);
        yPos += 6;
        
        pdf.setFontSize(8);
        pdf.setFont('helvetica', 'bold');
        const costHeaders = ['Role', 'Hours', 'Internal', 'Billable', 'Margin', 'Margin %'];
        const costColWidth = (pageWidth - margin * 2) / costHeaders.length;
        
        costHeaders.forEach((h, i) => {
          pdf.text(h, margin + i * costColWidth, yPos);
        });
        yPos += 5;
        
        pdf.setFont('helvetica', 'normal');
        costs.role_costs.forEach(role => {
          if (yPos > pageHeight - margin) {
            pdf.addPage();
            yPos = margin;
          }
          const row = [
            role.role_name?.substring(0, 20) || 'Unknown',
            (role.total_hours || 0).toLocaleString(),
            formatCurrency(role.total_internal_cost),
            formatCurrency(role.total_billable),
            formatCurrency(role.total_margin),
            `${role.margin_percentage || 0}%`
          ];
          row.forEach((cell, i) => {
            pdf.text(String(cell), margin + i * costColWidth, yPos);
          });
          yPos += 4;
        });
      }
      
      // Capture timeline as image if available
      if (planningGanttRef.current) {
        try {
          pdf.addPage();
          yPos = margin;
          
          const canvas = await html2canvas(planningGanttRef.current, {
            scale: 1.5,
            useCORS: true,
            logging: false
          });
          
          const imgData = canvas.toDataURL('image/png');
          const imgWidth = pageWidth - (margin * 2);
          const imgHeight = (canvas.height * imgWidth) / canvas.width;
          
          pdf.setFontSize(12);
          pdf.setFont('helvetica', 'bold');
          pdf.text('Role Coverage Timeline', margin, yPos);
          yPos += 8;
          
          pdf.addImage(imgData, 'PNG', margin, yPos, imgWidth, Math.min(imgHeight, pageHeight - yPos - margin));
        } catch (imgError) {
          console.warn('Could not capture timeline:', imgError);
        }
      }
      
      // Save
      const fileName = `planning-exercise-${exercise?.name?.replace(/[^a-z0-9]/gi, '-') || 'report'}-${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(fileName);
      
    } catch (err) {
      console.error('PDF export failed:', err);
      alert('Failed to export PDF. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  // Export to CSV - Project Report
  const handleExportCSV = () => {
    if (!reportData) return;
    
    setIsExporting(true);
    
    try {
      // Prepare cost data
      const costData = [];
      
      // Add summary rows
      costData.push({
        Section: 'Summary',
        Item: 'Total Internal Cost',
        Value: reportData.summary.total_internal_cost
      });
      costData.push({
        Section: 'Summary',
        Item: 'Total Billable',
        Value: reportData.summary.total_billable
      });
      costData.push({
        Section: 'Summary',
        Item: 'Total Margin',
        Value: reportData.summary.total_margin
      });
      costData.push({
        Section: 'Summary',
        Item: 'Margin %',
        Value: reportData.summary.margin_percentage
      });
      costData.push({
        Section: 'Summary',
        Item: 'Total Staff',
        Value: reportData.summary.total_staff_count + reportData.summary.total_ghost_count
      });
      
      // Add role costs by month
      reportData.roles.forEach(role => {
        reportData.period.months.forEach(month => {
          const monthData = role.monthly_costs[month] || { internal: 0, billable: 0, hours: 0 };
          costData.push({
            Section: 'Monthly Costs',
            Role: role.role_name,
            Month: month,
            'Internal Cost': monthData.internal,
            Billable: monthData.billable,
            Hours: monthData.hours
          });
        });
      });
      
      // Add staff entries
      reportData.staff_entries.forEach(entry => {
        costData.push({
          Section: 'Staff Entries',
          Name: entry.name,
          Type: entry.type,
          Role: entry.role_name,
          Project: entry.project_name,
          'Start Date': entry.start_date,
          'End Date': entry.end_date,
          'Hours/Week': entry.hours_per_week,
          'Allocation %': entry.allocation_percentage,
          'Internal Rate': entry.internal_hourly_cost,
          'Billable Rate': entry.billable_rate
        });
      });
      
      // Convert to CSV
      const csv = Papa.unparse(costData);
      
      // Download
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const fileName = `staff-planning-${reportData.project.name.replace(/[^a-z0-9]/gi, '-')}-${new Date().toISOString().split('T')[0]}.csv`;
      
      if (navigator.msSaveBlob) {
        navigator.msSaveBlob(blob, fileName);
      } else {
        link.href = URL.createObjectURL(blob);
        link.download = fileName;
        link.click();
        URL.revokeObjectURL(link.href);
      }
    } catch (err) {
      console.error('CSV export failed:', err);
      alert('Failed to export CSV. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  // Export to CSV - Planning Exercise Report
  const handleExportPlanningCSV = () => {
    if (!planningReportData) return;
    
    setIsExporting(true);
    
    try {
      const { exercise, analysis, staffRequirements, costs } = planningReportData;
      const csvData = [];
      
      // Summary section
      csvData.push({
        Section: 'Summary',
        Item: 'Exercise Name',
        Value: exercise?.name || ''
      });
      csvData.push({
        Section: 'Summary',
        Item: 'Description',
        Value: exercise?.description || ''
      });
      csvData.push({
        Section: 'Summary',
        Item: 'Overlap Mode',
        Value: overlapMode
      });
      csvData.push({
        Section: 'Summary',
        Item: 'Total Projects',
        Value: exercise?.project_count || costs?.project_costs?.length || 0
      });
      csvData.push({
        Section: 'Summary',
        Item: 'Total Hours',
        Value: costs?.summary?.total_hours || 0
      });
      csvData.push({
        Section: 'Summary',
        Item: 'Total Internal Cost',
        Value: costs?.summary?.total_internal_cost || 0
      });
      csvData.push({
        Section: 'Summary',
        Item: 'Total Billable',
        Value: costs?.summary?.total_billable || 0
      });
      csvData.push({
        Section: 'Summary',
        Item: 'Total Margin',
        Value: costs?.summary?.total_margin || 0
      });
      csvData.push({
        Section: 'Summary',
        Item: 'Margin %',
        Value: costs?.summary?.margin_percentage || 0
      });
      csvData.push({
        Section: 'Summary',
        Item: 'Minimum Staff Needed',
        Value: staffRequirements?.summary?.total_minimum_staff || 0
      });
      csvData.push({
        Section: 'Summary',
        Item: 'New Hires Needed',
        Value: staffRequirements?.summary?.total_new_hires_needed || 0
      });
      
      // Projects data
      costs?.project_costs?.forEach(proj => {
        csvData.push({
          Section: 'Projects',
          'Project Name': proj.project_name,
          'Start Date': proj.start_date,
          'End Date': proj.end_date,
          'Duration (Months)': proj.duration_months,
          'Total Hours': proj.total_hours,
          'Internal Cost': proj.total_internal_cost,
          Billable: proj.total_billable,
          Margin: proj.total_margin,
          'Margin %': proj.margin_percentage
        });
      });
      
      // Staff requirements
      staffRequirements?.staff_requirements?.forEach(req => {
        csvData.push({
          Section: 'Staff Requirements',
          Role: req.role_name,
          'Minimum Staff Needed': req.minimum_staff_needed,
          'Peak Month': req.peak_month,
          'Peak Allocation': req.peak_allocation,
          'Available Staff': req.available_staff_count,
          'New Hires Needed': req.new_hires_needed,
          'Average FTE': req.average_fte,
          'Suggested Staff': req.staff_suggestions?.map(s => s.name).join(', ') || ''
        });
      });
      
      // Costs by role
      costs?.role_costs?.forEach(role => {
        csvData.push({
          Section: 'Role Costs',
          Role: role.role_name,
          'Hourly Cost': role.hourly_cost,
          'Billable Rate': role.billable_rate,
          'Total Hours': role.total_hours,
          'Internal Cost': role.total_internal_cost,
          Billable: role.total_billable,
          Margin: role.total_margin,
          'Margin %': role.margin_percentage
        });
      });
      
      // Monthly costs
      const months = costs?.period?.months || [];
      months.forEach(month => {
        const monthData = costs?.monthly_costs?.[month];
        if (monthData) {
          csvData.push({
            Section: 'Monthly Costs',
            Month: month,
            Hours: monthData.hours,
            'Internal Cost': monthData.internal_cost,
            Billable: monthData.billable,
            Margin: monthData.margin
          });
        }
      });
      
      // Convert to CSV
      const csv = Papa.unparse(csvData);
      
      // Download
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const fileName = `planning-exercise-${exercise?.name?.replace(/[^a-z0-9]/gi, '-') || 'report'}-${new Date().toISOString().split('T')[0]}.csv`;
      
      if (navigator.msSaveBlob) {
        navigator.msSaveBlob(blob, fileName);
      } else {
        link.href = URL.createObjectURL(blob);
        link.download = fileName;
        link.click();
        URL.revokeObjectURL(link.href);
      }
    } catch (err) {
      console.error('CSV export failed:', err);
      alert('Failed to export CSV. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  // Render Project Report Content
  const renderProjectReport = () => {
    if (!reportData) return null;

    return (
      <div className="report-content" ref={reportContentRef}>
        {/* Export Buttons */}
        <div className="export-buttons">
          <button 
            className="btn-export pdf"
            onClick={handleExportPDF}
            disabled={isExporting}
          >
            {isExporting ? 'Exporting...' : '📄 Export PDF'}
          </button>
          <button 
            className="btn-export csv"
            onClick={handleExportCSV}
            disabled={isExporting}
          >
            {isExporting ? 'Exporting...' : '📊 Export CSV'}
          </button>
        </div>

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
          <div className="gantt-chart" ref={ganttRef}>
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
    );
  };

  // Render Planning Exercise Report Content
  const renderPlanningReport = () => {
    if (!planningReportData) return null;

    const { exercise, analysis, staffRequirements, costs } = planningReportData;

    return (
      <div className="report-content planning-report" ref={reportContentRef}>
        {/* Export Buttons */}
        <div className="export-buttons">
          <button 
            className="btn-export pdf"
            onClick={handleExportPlanningPDF}
            disabled={isExporting}
          >
            {isExporting ? 'Exporting...' : '📄 Export PDF'}
          </button>
          <button 
            className="btn-export csv"
            onClick={handleExportPlanningCSV}
            disabled={isExporting}
          >
            {isExporting ? 'Exporting...' : '📊 Export CSV'}
          </button>
        </div>

        {/* Exercise Header */}
        <div className="report-header-info">
          <h2>📋 {exercise?.name || 'Planning Exercise'}</h2>
          {exercise?.description && (
            <p className="report-description">{exercise.description}</p>
          )}
          <p className="report-period">
            {formatDate(analysis?.period?.start_date)} - {formatDate(analysis?.period?.end_date)}
            {analysis?.period?.total_months && ` (${analysis.period.total_months} months)`}
          </p>
          <p className="overlap-mode-badge">
            Mode: {overlapMode === 'efficient' ? '🔄 Efficient (Share staff)' : '🔒 Conservative (Dedicated)'}
          </p>
        </div>

        {/* Summary Cards */}
        <div className="summary-cards planning-summary">
          <div className="summary-card">
            <div className="card-label">Projects</div>
            <div className="card-value projects">{exercise?.project_count || costs?.project_costs?.length || 0}</div>
          </div>
          <div className="summary-card">
            <div className="card-label">Total Hours</div>
            <div className="card-value hours">{(costs?.summary?.total_hours || 0).toLocaleString()}</div>
          </div>
          <div className="summary-card">
            <div className="card-label">Total Billable</div>
            <div className="card-value billable">{formatCurrency(costs?.summary?.total_billable)}</div>
          </div>
          <div className="summary-card">
            <div className="card-label">Internal Cost</div>
            <div className="card-value cost">{formatCurrency(costs?.summary?.total_internal_cost)}</div>
          </div>
          <div className="summary-card">
            <div className="card-label">Total Margin</div>
            <div className="card-value margin">
              {formatCurrency(costs?.summary?.total_margin)}
              <span className="margin-percent">({costs?.summary?.margin_percentage?.toFixed(1) || 0}%)</span>
            </div>
          </div>
          <div className="summary-card highlight">
            <div className="card-label">Staff Needed</div>
            <div className="card-value staff">
              {staffRequirements?.summary?.total_minimum_staff || 0}
              {staffRequirements?.summary?.total_new_hires_needed > 0 && (
                <span className="new-hires-badge">+{staffRequirements.summary.total_new_hires_needed} new</span>
              )}
            </div>
          </div>
        </div>

        {/* Projects Overview */}
        {costs?.project_costs?.length > 0 && (
          <div className="report-section">
            <h3>Projects Overview</h3>
            <div className="projects-table-wrapper">
              <table className="planning-table">
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Start Date</th>
                    <th>End Date</th>
                    <th>Duration</th>
                    <th>Hours</th>
                    <th>Billable</th>
                    <th>Margin</th>
                  </tr>
                </thead>
                <tbody>
                  {costs.project_costs.map((project, index) => (
                    <tr key={project.project_id || index}>
                      <td className="project-name">{project.project_name}</td>
                      <td>{formatDate(project.start_date)}</td>
                      <td>{formatDate(project.end_date)}</td>
                      <td>{project.duration_months} months</td>
                      <td>{(project.total_hours || 0).toLocaleString()}</td>
                      <td>{formatCurrency(project.total_billable)}</td>
                      <td className={project.total_margin > 0 ? 'positive' : 'negative'}>
                        {formatCurrency(project.total_margin)} ({project.margin_percentage || 0}%)
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Staff Requirements by Role */}
        {staffRequirements?.staff_requirements?.length > 0 && (
          <div className="report-section">
            <h3>Staff Requirements by Role</h3>
            <div className="requirements-grid">
              {staffRequirements.staff_requirements.map((req, index) => (
                <div 
                  key={req.role_id || index} 
                  className={`requirement-card ${req.new_hires_needed > 0 ? 'needs-hire' : ''}`}
                >
                  <div className="req-header">
                    <span 
                      className="role-color-indicator" 
                      style={{ backgroundColor: getRoleColor(index) }}
                    />
                    <h4>{req.role_name}</h4>
                    {req.new_hires_needed > 0 && (
                      <span className="hire-badge">+{req.new_hires_needed} hire(s)</span>
                    )}
                  </div>
                  <div className="req-stats">
                    <div className="stat">
                      <span className="label">Min Needed:</span>
                      <span className="value">{req.minimum_staff_needed}</span>
                    </div>
                    <div className="stat">
                      <span className="label">Peak Month:</span>
                      <span className="value">{req.peak_month || '-'}</span>
                    </div>
                    <div className="stat">
                      <span className="label">Peak Alloc:</span>
                      <span className="value">{req.peak_allocation || 0}%</span>
                    </div>
                    <div className="stat">
                      <span className="label">Available:</span>
                      <span className="value">{req.available_staff_count || 0}</span>
                    </div>
                    <div className="stat">
                      <span className="label">Avg FTE:</span>
                      <span className="value">{req.average_fte || 0}</span>
                    </div>
                  </div>
                  {req.staff_suggestions?.length > 0 && (
                    <div className="suggestions">
                      <h5>Suggested Staff:</h5>
                      <ul>
                        {req.staff_suggestions.slice(0, 3).map((staff, i) => (
                          <li key={staff.staff_id || i}>
                            {staff.name} <span className="score">(Score: {staff.match_score})</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Costs by Role */}
        {costs?.role_costs?.length > 0 && (
          <div className="report-section cost-table-section">
            <div className="section-header">
              <h3>Costs by Role</h3>
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
              <table className="planning-table">
                <thead>
                  <tr>
                    <th>Role</th>
                    <th>Hourly Cost</th>
                    <th>Billable Rate</th>
                    <th>Total Hours</th>
                    <th>Internal Cost</th>
                    <th>Billable</th>
                    <th>Margin</th>
                    <th>Margin %</th>
                  </tr>
                </thead>
                <tbody>
                  {costs.role_costs.map((role, index) => (
                    <tr key={role.role_id || index}>
                      <td className="role-name">
                        <span 
                          className="role-color-indicator" 
                          style={{ backgroundColor: getRoleColor(index) }}
                        />
                        {role.role_name}
                      </td>
                      <td>{formatCurrency(role.hourly_cost)}</td>
                      <td>{formatCurrency(role.billable_rate)}</td>
                      <td>{(role.total_hours || 0).toLocaleString()}</td>
                      <td className="cost">{formatCurrency(role.total_internal_cost)}</td>
                      <td className="billable">{formatCurrency(role.total_billable)}</td>
                      <td className={role.total_margin > 0 ? 'positive' : 'negative'}>
                        {formatCurrency(role.total_margin)}
                      </td>
                      <td>{role.margin_percentage || 0}%</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan="3"><strong>Total</strong></td>
                    <td><strong>{(costs.summary?.total_hours || 0).toLocaleString()}</strong></td>
                    <td><strong>{formatCurrency(costs.summary?.total_internal_cost)}</strong></td>
                    <td><strong>{formatCurrency(costs.summary?.total_billable)}</strong></td>
                    <td><strong>{formatCurrency(costs.summary?.total_margin)}</strong></td>
                    <td><strong>{costs.summary?.margin_percentage || 0}%</strong></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}

        {/* Monthly Cost Breakdown */}
        {costs?.monthly_costs && costs?.period?.months?.length > 0 && (
          <div className="report-section">
            <h3>Monthly Cost Breakdown</h3>
            <div className="cost-table-wrapper">
              <table className="planning-table monthly-costs-table">
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Hours</th>
                    <th>Internal Cost</th>
                    <th>Billable</th>
                    <th>Margin</th>
                  </tr>
                </thead>
                <tbody>
                  {costs.period.months.map(month => {
                    const monthData = costs.monthly_costs[month] || {};
                    return (
                      <tr key={month}>
                        <td>{formatMonth(month)}</td>
                        <td>{(monthData.hours || 0).toLocaleString()}</td>
                        <td>{formatCurrency(monthData.internal_cost)}</td>
                        <td>{formatCurrency(monthData.billable)}</td>
                        <td className={monthData.margin > 0 ? 'positive' : 'negative'}>
                          {formatCurrency(monthData.margin)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Role Coverage Timeline (Gantt) */}
        {analysis?.role_coverage?.length > 0 && analysis?.period?.months?.length > 0 && (
          <div className="report-section gantt-section">
            <h3>Role Coverage Timeline</h3>
            <div className="planning-gantt" ref={planningGanttRef}>
              <div className="gantt-header">
                <div className="gantt-role-label">Role</div>
                <div className="gantt-months">
                  {analysis.period.months.map(month => (
                    <div key={month} className="gantt-month-header">
                      {month.slice(5)}
                    </div>
                  ))}
                </div>
              </div>
              <div className="gantt-body">
                {analysis.role_coverage.map((role, roleIndex) => (
                  <div key={role.role_id || roleIndex} className="gantt-row">
                    <div className="gantt-role-label">
                      <span 
                        className="role-color-indicator" 
                        style={{ backgroundColor: getRoleColor(roleIndex) }}
                      />
                      <span className="role-name">{role.role_name}</span>
                      <span className="fte-badge">{role.total_fte} FTE</span>
                    </div>
                    <div className="gantt-timeline">
                      {analysis.period.months.map(month => {
                        const monthReq = role.monthly_requirements?.[month];
                        const hasAllocation = monthReq?.allocation_total > 0;
                        const intensity = Math.min((monthReq?.allocation_total || 0) / 100, 1);
                        
                        return (
                          <div 
                            key={month} 
                            className={`gantt-cell ${hasAllocation ? 'active' : ''}`}
                            style={{ 
                              backgroundColor: hasAllocation 
                                ? `rgba(${parseInt(getRoleColor(roleIndex).slice(1, 3), 16)}, ${parseInt(getRoleColor(roleIndex).slice(3, 5), 16)}, ${parseInt(getRoleColor(roleIndex).slice(5, 7), 16)}, ${0.2 + intensity * 0.6})`
                                : 'transparent'
                            }}
                            title={`${month}: ${monthReq?.allocation_total?.toFixed(0) || 0}% allocation across ${monthReq?.projects?.length || 0} project(s)`}
                          >
                            {hasAllocation && (
                              <span className="cell-value">{monthReq?.allocation_total?.toFixed(0)}%</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="gantt-legend">
              <div className="legend-item">
                <span className="legend-bar light" />
                <span>Low Allocation</span>
              </div>
              <div className="legend-item">
                <span className="legend-bar medium" />
                <span>Medium Allocation</span>
              </div>
              <div className="legend-item">
                <span className="legend-bar high" />
                <span>High Allocation</span>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="reports">
      <h1>Staff Planning Report</h1>

      {/* Report Type Selector */}
      <div className="report-type-selector">
        <button 
          className={`type-btn ${reportType === 'project' ? 'active' : ''}`}
          onClick={() => setReportType('project')}
        >
          📄 Project Report
        </button>
        <button 
          className={`type-btn ${reportType === 'planning' ? 'active' : ''}`}
          onClick={() => setReportType('planning')}
        >
          📋 Planning Exercise Report
        </button>
      </div>

      {/* Filters Section */}
      <div className="report-filters">
        {reportType === 'project' ? (
          /* Project Filters */
          <>
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
          </>
        ) : (
          /* Planning Exercise Filters */
          <>
            <div className="filter-row">
              <div className="filter-group">
                <label htmlFor="exercise">Planning Exercise</label>
                <select
                  id="exercise"
                  value={selectedExerciseId}
                  onChange={(e) => setSelectedExerciseId(e.target.value)}
                >
                  <option value="">-- Select Planning Exercise --</option>
                  {planningExercises.map(exercise => (
                    <option key={exercise.id} value={exercise.id}>
                      📋 {exercise.name} ({exercise.project_count || 0} projects)
                    </option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label htmlFor="overlapMode">Overlap Mode</label>
                <select
                  id="overlapMode"
                  value={overlapMode}
                  onChange={(e) => setOverlapMode(e.target.value)}
                >
                  <option value="efficient">Efficient (Share staff across projects)</option>
                  <option value="conservative">Conservative (Dedicated staff per project)</option>
                </select>
              </div>
            </div>

            <div className="filter-row">
              <div className="overlap-mode-info">
                {overlapMode === 'efficient' 
                  ? '💡 Efficient mode calculates minimum staff by allowing sharing across overlapping project phases.'
                  : '🔒 Conservative mode assigns dedicated staff to each project, resulting in higher headcount.'}
              </div>

              <button 
                className="btn-primary generate-btn"
                onClick={handleGeneratePlanningReport}
                disabled={isLoading('report')}
              >
                {isLoading('report') ? 'Generating...' : 'Generate Report'}
              </button>
            </div>
          </>
        )}
      </div>

      {error && (
        <div className="error-message">
          <p>{error.message}</p>
        </div>
      )}

      {/* Report Content */}
      {reportType === 'project' && reportData && renderProjectReport()}
      {reportType === 'planning' && planningReportData && renderPlanningReport()}

      {/* Empty State */}
      {((reportType === 'project' && !reportData) || (reportType === 'planning' && !planningReportData)) && !isLoading('report') && (
        <div className="empty-state">
          <div className="empty-icon">{reportType === 'project' ? '📊' : '📋'}</div>
          <h3>Generate a {reportType === 'project' ? 'Staff Planning' : 'Planning Exercise'} Report</h3>
          <p>
            {reportType === 'project' 
              ? 'Select a project or project folder and click "Generate Report" to view detailed staff planning data including costs, allocations, and timeline.'
              : 'Select a planning exercise and click "Generate Report" to analyze staff requirements, costs, and coverage across all projects in the exercise.'}
          </p>
        </div>
      )}
    </div>
  );
};

export default Reports;
