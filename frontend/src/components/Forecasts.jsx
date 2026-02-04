import React, { useState, useEffect } from 'react';
import { roleAPI, forecastAPI } from '../services/api';
import { useApiError } from '../hooks/useApiError';
import { useLoading } from '../contexts/LoadingContext';
import SkeletonLoader from './common/SkeletonLoader';
import './Forecasts.css';

const Forecasts = () => {
  const { error, handleError, clearError } = useApiError();
  const { startLoading, stopLoading, isLoading } = useLoading();

  // Filter state
  const [roles, setRoles] = useState([]);
  const [selectedRoleId, setSelectedRoleId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [requiredCount, setRequiredCount] = useState(1);
  const [allocationPercentage, setAllocationPercentage] = useState(100);

  // Data state
  const [availabilityData, setAvailabilityData] = useState(null);
  const [suggestionsData, setSuggestionsData] = useState(null);
  const [newHireData, setNewHireData] = useState(null);
  const [overAllocations, setOverAllocations] = useState(null);

  // View state
  const [activeTab, setActiveTab] = useState('availability');

  // Set default dates
  useEffect(() => {
    const today = new Date();
    const start = today.toISOString().split('T')[0];
    const end = new Date(today.getTime() + 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    setStartDate(start);
    setEndDate(end);
    
    fetchRoles();
  }, []);

  const fetchRoles = async () => {
    try {
      const response = await roleAPI.getAll({ active_only: true });
      setRoles(response.data);
    } catch (err) {
      console.error('Failed to load roles:', err);
    }
  };

  const handleFetchAvailability = async () => {
    if (!startDate || !endDate) {
      alert('Please select start and end dates');
      return;
    }

    startLoading('availability');
    clearError();

    try {
      const params = {
        start_date: startDate,
        end_date: endDate
      };
      if (selectedRoleId) {
        params.role_id = selectedRoleId;
      }

      const response = await forecastAPI.getStaffAvailability(params);
      setAvailabilityData(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('availability');
    }
  };

  const handleFetchSuggestions = async () => {
    if (!selectedRoleId || !startDate || !endDate) {
      alert('Please select a role and date range');
      return;
    }

    startLoading('suggestions');
    clearError();

    try {
      const response = await forecastAPI.getSuggestions({
        role_id: selectedRoleId,
        start_date: startDate,
        end_date: endDate,
        allocation_percentage: allocationPercentage
      });
      setSuggestionsData(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('suggestions');
    }
  };

  const handleFetchNewHireNeeds = async () => {
    if (!selectedRoleId || !startDate || !endDate) {
      alert('Please select a role and date range');
      return;
    }

    startLoading('newHire');
    clearError();

    try {
      const response = await forecastAPI.getNewHireNeeds({
        role_id: selectedRoleId,
        start_date: startDate,
        end_date: endDate,
        required_count: requiredCount,
        allocation_percentage: allocationPercentage
      });
      setNewHireData(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('newHire');
    }
  };

  const handleFetchOverAllocations = async () => {
    if (!startDate || !endDate) {
      alert('Please select start and end dates');
      return;
    }

    startLoading('overAllocations');
    clearError();

    try {
      const response = await forecastAPI.getOrganizationOverAllocations({
        start_date: startDate,
        end_date: endDate
      });
      setOverAllocations(response.data);
    } catch (err) {
      handleError(err);
    } finally {
      stopLoading('overAllocations');
    }
  };

  const getAvailabilityStatusClass = (status) => {
    switch (status) {
      case 'available': return 'status-available';
      case 'partial': return 'status-partial';
      case 'unavailable': return 'status-unavailable';
      default: return '';
    }
  };

  const getSeverityClass = (severity) => {
    switch (severity) {
      case 'critical': return 'severity-critical';
      case 'high': return 'severity-high';
      case 'moderate': return 'severity-moderate';
      default: return '';
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    });
  };

  return (
    <div className="forecasts">
      <h1>Staffing Forecasts</h1>

      {/* Filters */}
      <div className="forecast-filters">
        <div className="filter-row">
          <div className="filter-group">
            <label htmlFor="role">Role (Optional)</label>
            <select
              id="role"
              value={selectedRoleId}
              onChange={(e) => setSelectedRoleId(e.target.value)}
            >
              <option value="">All Roles</option>
              {roles.map(role => (
                <option key={role.id} value={role.id}>{role.name}</option>
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
          <div className="filter-group small">
            <label htmlFor="requiredCount">Required Count</label>
            <input
              type="number"
              id="requiredCount"
              value={requiredCount}
              onChange={(e) => setRequiredCount(parseInt(e.target.value) || 1)}
              min="1"
              max="50"
            />
          </div>

          <div className="filter-group small">
            <label htmlFor="allocation">Allocation %</label>
            <input
              type="number"
              id="allocation"
              value={allocationPercentage}
              onChange={(e) => setAllocationPercentage(parseFloat(e.target.value) || 100)}
              min="0"
              max="100"
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="forecast-tabs">
        <button 
          className={`tab ${activeTab === 'availability' ? 'active' : ''}`}
          onClick={() => setActiveTab('availability')}
        >
          Staff Availability
        </button>
        <button 
          className={`tab ${activeTab === 'suggestions' ? 'active' : ''}`}
          onClick={() => setActiveTab('suggestions')}
        >
          Staff Suggestions
        </button>
        <button 
          className={`tab ${activeTab === 'newHire' ? 'active' : ''}`}
          onClick={() => setActiveTab('newHire')}
        >
          New Hire Needs
        </button>
        <button 
          className={`tab ${activeTab === 'overAllocations' ? 'active' : ''}`}
          onClick={() => setActiveTab('overAllocations')}
        >
          Over-Allocations
        </button>
      </div>

      {error && (
        <div className="error-message">
          <p>{error.message}</p>
        </div>
      )}

      {/* Tab Content */}
      <div className="forecast-content">
        {/* Availability Tab */}
        {activeTab === 'availability' && (
          <div className="availability-section">
            <div className="section-header">
              <h2>Staff Availability Forecast</h2>
              <button 
                className="btn-primary"
                onClick={handleFetchAvailability}
                disabled={isLoading('availability')}
              >
                {isLoading('availability') ? 'Loading...' : 'Check Availability'}
              </button>
            </div>

            {isLoading('availability') && <SkeletonLoader />}

            {availabilityData && !isLoading('availability') && (
              <div className="availability-results">
                <div className="availability-summary">
                  <div className="summary-card available">
                    <div className="card-value">{availabilityData.summary.available_count}</div>
                    <div className="card-label">Fully Available</div>
                  </div>
                  <div className="summary-card partial">
                    <div className="card-value">{availabilityData.summary.partial_count}</div>
                    <div className="card-label">Partially Available</div>
                  </div>
                  <div className="summary-card unavailable">
                    <div className="card-value">{availabilityData.summary.unavailable_count}</div>
                    <div className="card-label">Unavailable</div>
                  </div>
                </div>

                {availabilityData.role && (
                  <div className="role-info">
                    Showing availability for: <strong>{availabilityData.role.name}</strong>
                  </div>
                )}

                {/* Available Staff */}
                {availabilityData.available.length > 0 && (
                  <div className="staff-group">
                    <h3>✅ Available Staff ({availabilityData.available.length})</h3>
                    <div className="staff-cards">
                      {availabilityData.available.map(staff => (
                        <div key={staff.staff_id} className="staff-card available">
                          <div className="staff-name">{staff.name}</div>
                          <div className="staff-role">{staff.role_name}</div>
                          <div className="staff-allocation">
                            <span className="allocation-badge">{staff.available_allocation}% available</span>
                          </div>
                          <div className="staff-rate">${staff.internal_hourly_cost}/hr internal</div>
                          {staff.skills?.length > 0 && (
                            <div className="staff-skills">
                              {staff.skills.slice(0, 3).map((skill, i) => (
                                <span key={i} className="skill-tag">{skill}</span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Partially Available Staff */}
                {availabilityData.partially_available.length > 0 && (
                  <div className="staff-group">
                    <h3>⚠️ Partially Available Staff ({availabilityData.partially_available.length})</h3>
                    <div className="staff-cards">
                      {availabilityData.partially_available.map(staff => (
                        <div key={staff.staff_id} className="staff-card partial">
                          <div className="staff-name">{staff.name}</div>
                          <div className="staff-role">{staff.role_name}</div>
                          <div className="staff-allocation">
                            <span className="allocation-badge partial">{staff.available_allocation.toFixed(0)}% available</span>
                            <span className="current-allocation">({staff.current_allocation.toFixed(0)}% allocated)</span>
                          </div>
                          {staff.current_assignments?.length > 0 && (
                            <div className="current-assignments">
                              {staff.current_assignments.slice(0, 2).map((a, i) => (
                                <div key={i} className="assignment-mini">
                                  {a.project_name} ({a.allocation_percentage}%)
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Unavailable Staff */}
                {availabilityData.unavailable.length > 0 && (
                  <div className="staff-group collapsed">
                    <h3>❌ Unavailable Staff ({availabilityData.unavailable.length})</h3>
                    <div className="staff-list-compact">
                      {availabilityData.unavailable.map(staff => (
                        <div key={staff.staff_id} className="staff-item unavailable">
                          <span className="name">{staff.name}</span>
                          <span className="role">{staff.role_name}</span>
                          <span className="reason">{staff.reason}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Suggestions Tab */}
        {activeTab === 'suggestions' && (
          <div className="suggestions-section">
            <div className="section-header">
              <h2>Staff Suggestions</h2>
              <button 
                className="btn-primary"
                onClick={handleFetchSuggestions}
                disabled={isLoading('suggestions') || !selectedRoleId}
              >
                {isLoading('suggestions') ? 'Loading...' : 'Get Suggestions'}
              </button>
            </div>

            {!selectedRoleId && (
              <div className="info-message">Please select a role to get staff suggestions.</div>
            )}

            {isLoading('suggestions') && <SkeletonLoader />}

            {suggestionsData && !isLoading('suggestions') && (
              <div className="suggestions-results">
                <div className="suggestions-info">
                  <p>
                    Suggesting staff for <strong>{suggestionsData.role.name}</strong> 
                    from {formatDate(suggestionsData.period.start_date)} to {formatDate(suggestionsData.period.end_date)}
                  </p>
                  <p className="stats">
                    {suggestionsData.qualified_candidates} of {suggestionsData.total_candidates} staff members qualify
                  </p>
                </div>

                {suggestionsData.suggestions.length === 0 ? (
                  <div className="no-suggestions">
                    <div className="alert-icon">🚨</div>
                    <h3>No Staff Available</h3>
                    <p>No staff members with the {suggestionsData.role.name} role are available during this period.</p>
                    <p>Consider hiring new staff or adjusting dates.</p>
                  </div>
                ) : (
                  <div className="suggestion-cards">
                    {suggestionsData.suggestions.map((suggestion, index) => (
                      <div key={suggestion.staff_id} className={`suggestion-card ${index === 0 ? 'top-match' : ''}`}>
                        {index === 0 && <div className="top-badge">Best Match</div>}
                        <div className="suggestion-header">
                          <div className="staff-name">{suggestion.name}</div>
                          <div className="match-score">
                            <span className="score">{suggestion.match_score}</span>
                            <span className="label">match score</span>
                          </div>
                        </div>
                        <div className="suggestion-body">
                          <div className="match-reasons">
                            {suggestion.match_reasons.map((reason, i) => (
                              <div key={i} className="reason">✓ {reason}</div>
                            ))}
                          </div>
                          <div className="staff-details">
                            <div className="detail">
                              <span className="label">Available:</span>
                              <span className="value">{suggestion.available_allocation}%</span>
                            </div>
                            <div className="detail">
                              <span className="label">Rate:</span>
                              <span className="value">${suggestion.internal_hourly_cost}/hr</span>
                            </div>
                          </div>
                          {suggestion.current_assignments?.length > 0 && (
                            <div className="current-work">
                              <div className="label">Current Assignments:</div>
                              {suggestion.current_assignments.map((a, i) => (
                                <div key={i} className="assignment-line">
                                  {a.project_name} - ends {a.end_date}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* New Hire Needs Tab */}
        {activeTab === 'newHire' && (
          <div className="new-hire-section">
            <div className="section-header">
              <h2>New Hire Needs Analysis</h2>
              <button 
                className="btn-primary"
                onClick={handleFetchNewHireNeeds}
                disabled={isLoading('newHire') || !selectedRoleId}
              >
                {isLoading('newHire') ? 'Loading...' : 'Analyze Needs'}
              </button>
            </div>

            {!selectedRoleId && (
              <div className="info-message">Please select a role to analyze new hire needs.</div>
            )}

            {isLoading('newHire') && <SkeletonLoader />}

            {newHireData && !isLoading('newHire') && (
              <div className="new-hire-results">
                <div className={`hire-status-banner ${newHireData.needs_new_hire ? 'needs-hire' : 'no-hire'}`}>
                  {newHireData.needs_new_hire ? (
                    <>
                      <div className="banner-icon">🚨</div>
                      <div className="banner-content">
                        <h3>New Hires Needed</h3>
                        <p>
                          You need <strong>{newHireData.new_hire_count}</strong> new {newHireData.role.name}(s) 
                          to meet the requirement of {newHireData.requirement.required_count} staff at {newHireData.requirement.allocation_percentage}% allocation.
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="banner-icon">✅</div>
                      <div className="banner-content">
                        <h3>Sufficient Staff Available</h3>
                        <p>
                          You have enough {newHireData.role.name} staff to meet the requirement.
                        </p>
                      </div>
                    </>
                  )}
                </div>

                <div className="hire-details">
                  <div className="detail-section">
                    <h4>Requirement</h4>
                    <div className="detail-grid">
                      <div className="detail-item">
                        <span className="label">Role</span>
                        <span className="value">{newHireData.role.name}</span>
                      </div>
                      <div className="detail-item">
                        <span className="label">Count Needed</span>
                        <span className="value">{newHireData.requirement.required_count}</span>
                      </div>
                      <div className="detail-item">
                        <span className="label">Period</span>
                        <span className="value">
                          {formatDate(newHireData.period.start_date)} - {formatDate(newHireData.period.end_date)}
                        </span>
                      </div>
                      <div className="detail-item">
                        <span className="label">Duration</span>
                        <span className="value">{newHireData.period.duration_weeks} weeks</span>
                      </div>
                    </div>
                  </div>

                  <div className="detail-section">
                    <h4>Availability</h4>
                    <div className="detail-grid">
                      <div className="detail-item">
                        <span className="label">Total Staff with Role</span>
                        <span className="value">{newHireData.availability.total_staff_with_role}</span>
                      </div>
                      <div className="detail-item">
                        <span className="label">Qualified & Available</span>
                        <span className="value">{newHireData.availability.qualified_available}</span>
                      </div>
                      <div className="detail-item">
                        <span className="label">Gap</span>
                        <span className={`value ${newHireData.availability.gap > 0 ? 'negative' : 'positive'}`}>
                          {newHireData.availability.gap > 0 ? `-${newHireData.availability.gap}` : '0'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {newHireData.needs_new_hire && (
                    <div className="detail-section">
                      <h4>Estimated Cost Impact</h4>
                      <div className="detail-grid">
                        <div className="detail-item">
                          <span className="label">Hours per Person</span>
                          <span className="value">{newHireData.estimated_impact.hours_per_person} hrs</span>
                        </div>
                        <div className="detail-item">
                          <span className="label">Internal Cost (Gap)</span>
                          <span className="value">${newHireData.estimated_impact.internal_cost_for_gap.toLocaleString()}</span>
                        </div>
                        <div className="detail-item">
                          <span className="label">Billable (Gap)</span>
                          <span className="value">${newHireData.estimated_impact.billable_for_gap.toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {newHireData.recommendations?.length > 0 && (
                    <div className="recommendations-section">
                      <h4>Recommendations</h4>
                      <div className="recommendations-list">
                        {newHireData.recommendations.map((rec, index) => (
                          <div key={index} className={`recommendation ${rec.priority}`}>
                            <div className="rec-type">{rec.type.replace('_', ' ')}</div>
                            <div className="rec-message">{rec.message}</div>
                            <div className="rec-details">{rec.details}</div>
                            <span className={`priority-badge ${rec.priority}`}>{rec.priority}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {newHireData.existing_suggestions?.length > 0 && (
                    <div className="existing-staff-section">
                      <h4>Available Staff Suggestions</h4>
                      <div className="staff-list">
                        {newHireData.existing_suggestions.map(staff => (
                          <div key={staff.staff_id} className="staff-suggestion-item">
                            <span className="name">{staff.name}</span>
                            <span className="availability">{staff.available_allocation}% available</span>
                            <span className="score">Score: {staff.match_score}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Over-Allocations Tab */}
        {activeTab === 'overAllocations' && (
          <div className="over-allocations-section">
            <div className="section-header">
              <h2>Over-Allocation Conflicts</h2>
              <button 
                className="btn-primary"
                onClick={handleFetchOverAllocations}
                disabled={isLoading('overAllocations')}
              >
                {isLoading('overAllocations') ? 'Loading...' : 'Check Conflicts'}
              </button>
            </div>

            {isLoading('overAllocations') && <SkeletonLoader />}

            {overAllocations && !isLoading('overAllocations') && (
              <div className="over-allocation-results">
                <div className="allocation-summary">
                  <div className="summary-card total">
                    <div className="card-value">{overAllocations.summary.total_staff}</div>
                    <div className="card-label">Total Staff</div>
                  </div>
                  <div className="summary-card clear">
                    <div className="card-value">{overAllocations.summary.staff_without_conflicts}</div>
                    <div className="card-label">No Conflicts</div>
                  </div>
                  <div className="summary-card critical">
                    <div className="card-value">{overAllocations.summary.critical_count}</div>
                    <div className="card-label">Critical</div>
                  </div>
                  <div className="summary-card high">
                    <div className="card-value">{overAllocations.summary.high_count}</div>
                    <div className="card-label">High</div>
                  </div>
                  <div className="summary-card moderate">
                    <div className="card-value">{overAllocations.summary.moderate_count}</div>
                    <div className="card-label">Moderate</div>
                  </div>
                </div>

                {overAllocations.conflicts.length === 0 ? (
                  <div className="no-conflicts">
                    <div className="success-icon">✅</div>
                    <h3>No Over-Allocation Conflicts</h3>
                    <p>All staff members are within their allocation limits for this period.</p>
                  </div>
                ) : (
                  <div className="conflicts-list">
                    <h3>Staff with Conflicts ({overAllocations.conflicts.length})</h3>
                    {overAllocations.conflicts.map(staff => (
                      <div key={staff.staff_id} className={`conflict-card ${getSeverityClass(staff.severity)}`}>
                        <div className="conflict-header">
                          <div className="staff-info">
                            <span className="staff-name">{staff.staff_name}</span>
                            <span className="staff-role">{staff.role}</span>
                          </div>
                          <span className={`severity-badge ${staff.severity}`}>{staff.severity}</span>
                        </div>
                        <div className="conflict-details">
                          <div className="conflict-count">{staff.conflict_count} month(s) with conflicts</div>
                          <div className="conflict-periods">
                            {staff.over_allocated_periods.map((period, i) => (
                              <div key={i} className="period-item">
                                <span className="month">{period.month}</span>
                                <span className="allocation">{period.total_allocation.toFixed(0)}% allocated</span>
                                <span className="over-by">+{period.over_allocation_amount.toFixed(0)}% over</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Forecasts;
