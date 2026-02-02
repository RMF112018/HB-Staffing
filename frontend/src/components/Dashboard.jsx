import React from 'react';

const Dashboard = () => {
  return (
    <div className="dashboard">
      <h1>HB-Staffing Dashboard</h1>
      <p>Dashboard is now working!</p>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Staff</h3>
          <div className="stat-number">25</div>
          <p>Active team members</p>
        </div>

        <div className="stat-card">
          <h3>Active Projects</h3>
          <div className="stat-number">8</div>
          <p>Currently running</p>
        </div>

        <div className="stat-card">
          <h3>Current Assignments</h3>
          <div className="stat-number">20</div>
          <p>Staff assigned to projects</p>
        </div>

        <div className="stat-card">
          <h3>Upcoming Forecasts</h3>
          <div className="stat-number">12</div>
          <p>Predicted staffing needs</p>
        </div>
      </div>

      <div className="dashboard-sections">
        <section className="recent-activity">
          <h2>Recent Activity</h2>
          <ul>
            <li>New staff member added: John Doe</li>
            <li>Project "Downtown Office" started</li>
            <li>Staff assignment updated for "Highway Construction"</li>
            <li>Forecast generated for next quarter</li>
          </ul>
        </section>

        <section className="quick-actions">
          <h2>Quick Actions</h2>
          <div className="action-buttons">
            <button className="btn-primary">Add New Staff</button>
            <button className="btn-secondary">Create Project</button>
            <button className="btn-secondary">Generate Forecast</button>
            <button className="btn-secondary">View Reports</button>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Dashboard;