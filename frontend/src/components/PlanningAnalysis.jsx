import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { planningAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import SkeletonLoader from './common/SkeletonLoader';
import './PlanningAnalysis.css';

const PlanningAnalysis = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  const [exercise, setExercise] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [staffRequirements, setStaffRequirements] = useState(null);
  const [costs, setCosts] = useState(null);
  
  const [activeTab, setActiveTab] = useState('overview');
  const [overlapMode, setOverlapMode] = useState('efficient');
  const [isApplying, setIsApplying] = useState(false);

  useEffect(() => {
    fetchExercise();
  }, [id]);

  useEffect(() => {
    if (exercise) {
      fetchAnalysis();
    }
  }, [exercise, overlapMode]);

  const fetchExercise = async () => {
    startLoading('exercise');
    try {
      const response = await planningAPI.getById(id);
      setExercise(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('exercise');
    }
  };

  const fetchAnalysis = async () => {
    startLoading('analysis');
    clearError();

    try {
      const [analysisRes, requirementsRes, costsRes] = await Promise.all([
        planningAPI.getAnalysis(id),
        planningAPI.getStaffRequirements(id, overlapMode),
        planningAPI.getCosts(id)
      ]);

      setAnalysis(analysisRes.data);
      setStaffRequirements(requirementsRes.data);
      setCosts(costsRes.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('analysis');
    }
  };

  const handleApplyExercise = async (preview = true) => {
    setIsApplying(true);
    try {
      const response = await planningAPI.apply(id, preview);
      
      if (preview) {
        alert(`This will create:\n- ${response.data.projects_created} project(s)\n- ${response.data.ghost_staff_created} ghost staff member(s)\n\nClick "Apply for Real" to proceed.`);
      } else {
        alert('Planning exercise applied successfully! Projects and ghost staff have been created.');
        navigate('/planning');
      }
    } catch (err) {
      handleError(err);
    } finally {
      setIsApplying(false);
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

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  if (isLoading('exercise')) {
    return (
      <div className="planning-analysis">
        <h1>Loading...</h1>
        <SkeletonLoader />
      </div>
    );
  }

  if (!exercise) {
    return (
      <div className="planning-analysis">
        <h1>Exercise Not Found</h1>
        <Link to="/planning">Back to Planning Exercises</Link>
      </div>
    );
  }

  return (
    <div className="planning-analysis">
      {/* Header */}
      <div className="analysis-header">
        <div className="header-left">
          <Link to="/planning" className="back-link">← Back to Exercises</Link>
          <h1>{exercise.name}</h1>
          {exercise.description && <p className="description">{exercise.description}</p>}
        </div>
        <div className="header-actions">
          <Link to={`/planning/${id}/edit`} className="btn-secondary">Edit</Link>
          {exercise.status === 'active' && (
            <>
              <button 
                className="btn-secondary"
                onClick={() => handleApplyExercise(true)}
                disabled={isApplying}
              >
                Preview Apply
              </button>
              <button 
                className="btn-primary"
                onClick={() => handleApplyExercise(false)}
                disabled={isApplying}
              >
                {isApplying ? 'Applying...' : 'Apply for Real'}
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="error-message">
          <p>{error.message}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="analysis-tabs">
        <button 
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button 
          className={`tab ${activeTab === 'staffing' ? 'active' : ''}`}
          onClick={() => setActiveTab('staffing')}
        >
          Staff Requirements
        </button>
        <button 
          className={`tab ${activeTab === 'costs' ? 'active' : ''}`}
          onClick={() => setActiveTab('costs')}
        >
          Costs & Margins
        </button>
        <button 
          className={`tab ${activeTab === 'timeline' ? 'active' : ''}`}
          onClick={() => setActiveTab('timeline')}
        >
          Timeline
        </button>
      </div>

      {isLoading('analysis') && <SkeletonLoader />}

      {!isLoading('analysis') && (
        <div className="analysis-content">
          {/* Overview Tab */}
          {activeTab === 'overview' && costs && (
            <div className="overview-tab">
              {/* Summary Cards */}
              <div className="summary-cards">
                <div className="summary-card">
                  <div className="card-value">{exercise.project_count || 0}</div>
                  <div className="card-label">Projects</div>
                </div>
                <div className="summary-card">
                  <div className="card-value">{costs.summary?.total_hours?.toLocaleString() || 0}</div>
                  <div className="card-label">Total Hours</div>
                </div>
                <div className="summary-card primary">
                  <div className="card-value">{formatCurrency(costs.summary?.total_billable || 0)}</div>
                  <div className="card-label">Total Billable</div>
                </div>
                <div className="summary-card">
                  <div className="card-value">{formatCurrency(costs.summary?.total_internal_cost || 0)}</div>
                  <div className="card-label">Internal Cost</div>
                </div>
                <div className="summary-card success">
                  <div className="card-value">{formatCurrency(costs.summary?.total_margin || 0)}</div>
                  <div className="card-label">Total Margin</div>
                </div>
                <div className="summary-card">
                  <div className="card-value">{costs.summary?.margin_percentage?.toFixed(1) || 0}%</div>
                  <div className="card-label">Margin %</div>
                </div>
              </div>

              {/* Projects Overview */}
              <div className="section">
                <h2>Projects</h2>
                <div className="projects-table">
                  <table>
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
                      {costs.project_costs?.map(project => (
                        <tr key={project.project_id}>
                          <td className="project-name">{project.project_name}</td>
                          <td>{formatDate(project.start_date)}</td>
                          <td>{formatDate(project.end_date)}</td>
                          <td>{project.duration_months} months</td>
                          <td>{project.total_hours?.toLocaleString()}</td>
                          <td>{formatCurrency(project.total_billable)}</td>
                          <td className={project.total_margin > 0 ? 'positive' : 'negative'}>
                            {formatCurrency(project.total_margin)} ({project.margin_percentage}%)
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Staffing Tab */}
          {activeTab === 'staffing' && staffRequirements && (
            <div className="staffing-tab">
              <div className="staffing-controls">
                <div className="control-group">
                  <label>Overlap Mode:</label>
                  <select
                    value={overlapMode}
                    onChange={(e) => setOverlapMode(e.target.value)}
                  >
                    <option value="efficient">Efficient (Share staff across projects)</option>
                    <option value="conservative">Conservative (Dedicated staff per project)</option>
                  </select>
                </div>
              </div>

              {/* Summary */}
              <div className="staffing-summary">
                <div className="summary-item">
                  <span className="label">Total Roles:</span>
                  <span className="value">{staffRequirements.summary?.total_roles}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Minimum Staff Needed:</span>
                  <span className="value">{staffRequirements.summary?.total_minimum_staff}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Available Staff:</span>
                  <span className="value">{staffRequirements.summary?.total_available}</span>
                </div>
                <div className="summary-item highlight">
                  <span className="label">New Hires Needed:</span>
                  <span className="value">{staffRequirements.summary?.total_new_hires_needed}</span>
                </div>
              </div>

              {/* Staff Requirements by Role */}
              <div className="section">
                <h2>Staff Requirements by Role</h2>
                <div className="requirements-grid">
                  {staffRequirements.staff_requirements?.map(req => (
                    <div key={req.role_id} className={`requirement-card ${req.new_hires_needed > 0 ? 'needs-hire' : ''}`}>
                      <div className="req-header">
                        <h3>{req.role_name}</h3>
                        {req.new_hires_needed > 0 && (
                          <span className="hire-badge">+{req.new_hires_needed} hire(s) needed</span>
                        )}
                      </div>
                      <div className="req-stats">
                        <div className="stat">
                          <span className="label">Minimum Needed:</span>
                          <span className="value">{req.minimum_staff_needed}</span>
                        </div>
                        <div className="stat">
                          <span className="label">Peak Month:</span>
                          <span className="value">{req.peak_month}</span>
                        </div>
                        <div className="stat">
                          <span className="label">Peak Allocation:</span>
                          <span className="value">{req.peak_allocation}%</span>
                        </div>
                        <div className="stat">
                          <span className="label">Available:</span>
                          <span className="value">{req.available_staff_count}</span>
                        </div>
                        <div className="stat">
                          <span className="label">Avg FTE:</span>
                          <span className="value">{req.average_fte}</span>
                        </div>
                      </div>
                      
                      {req.staff_suggestions?.length > 0 && (
                        <div className="suggestions">
                          <h4>Available Staff:</h4>
                          <ul>
                            {req.staff_suggestions.slice(0, 3).map(staff => (
                              <li key={staff.staff_id}>
                                {staff.name} (Score: {staff.match_score})
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Costs Tab */}
          {activeTab === 'costs' && costs && (
            <div className="costs-tab">
              {/* Costs by Role */}
              <div className="section">
                <h2>Costs by Role</h2>
                <div className="costs-table">
                  <table>
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
                      {costs.role_costs?.map(role => (
                        <tr key={role.role_id}>
                          <td className="role-name">{role.role_name}</td>
                          <td>{formatCurrency(role.hourly_cost)}</td>
                          <td>{formatCurrency(role.billable_rate)}</td>
                          <td>{role.total_hours?.toLocaleString()}</td>
                          <td>{formatCurrency(role.total_internal_cost)}</td>
                          <td>{formatCurrency(role.total_billable)}</td>
                          <td className={role.total_margin > 0 ? 'positive' : 'negative'}>
                            {formatCurrency(role.total_margin)}
                          </td>
                          <td>{role.margin_percentage}%</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td colSpan="3"><strong>Total</strong></td>
                        <td><strong>{costs.summary?.total_hours?.toLocaleString()}</strong></td>
                        <td><strong>{formatCurrency(costs.summary?.total_internal_cost)}</strong></td>
                        <td><strong>{formatCurrency(costs.summary?.total_billable)}</strong></td>
                        <td><strong>{formatCurrency(costs.summary?.total_margin)}</strong></td>
                        <td><strong>{costs.summary?.margin_percentage}%</strong></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* Monthly Costs */}
              <div className="section">
                <h2>Monthly Cost Breakdown</h2>
                <div className="monthly-table">
                  <table>
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
                      {costs.period?.months?.map(month => {
                        const monthData = costs.monthly_costs?.[month];
                        return (
                          <tr key={month}>
                            <td>{month}</td>
                            <td>{monthData?.hours?.toLocaleString() || 0}</td>
                            <td>{formatCurrency(monthData?.internal_cost || 0)}</td>
                            <td>{formatCurrency(monthData?.billable || 0)}</td>
                            <td className={monthData?.margin > 0 ? 'positive' : 'negative'}>
                              {formatCurrency(monthData?.margin || 0)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Timeline Tab */}
          {activeTab === 'timeline' && analysis && (
            <div className="timeline-tab">
              <div className="section">
                <h2>Role Coverage Timeline</h2>
                <p className="timeline-info">
                  Period: {formatDate(analysis.period?.start_date)} to {formatDate(analysis.period?.end_date)} 
                  ({analysis.period?.total_months} months)
                </p>

                {/* Gantt-style timeline */}
                <div className="gantt-container">
                  <div className="gantt-header">
                    <div className="gantt-role-column">Role</div>
                    <div className="gantt-timeline">
                      {analysis.period?.months?.map(month => (
                        <div key={month} className="gantt-month-header">
                          {month.slice(5)}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="gantt-body">
                    {analysis.role_coverage?.map(role => (
                      <div key={role.role_id} className="gantt-row">
                        <div className="gantt-role-column">
                          <span className="role-name">{role.role_name}</span>
                          <span className="fte-badge">Avg: {role.total_fte} FTE</span>
                        </div>
                        <div className="gantt-timeline">
                          {analysis.period?.months?.map(month => {
                            const monthReq = role.monthly_requirements?.[month];
                            const hasAllocation = monthReq?.allocation_total > 0;
                            const intensity = Math.min(monthReq?.allocation_total / 100, 1);
                            
                            return (
                              <div 
                                key={month} 
                                className={`gantt-cell ${hasAllocation ? 'active' : ''}`}
                                style={{ 
                                  '--intensity': intensity,
                                  backgroundColor: hasAllocation ? `rgba(99, 102, 241, ${0.2 + intensity * 0.6})` : 'transparent'
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
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PlanningAnalysis;

