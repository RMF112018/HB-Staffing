import React from 'react';
import { Link } from 'react-router-dom';
// import './NavBar.css';

const NavBar = () => {
  return (
    <nav style={{ background: '#333', color: 'white', padding: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Link to="/" style={{ color: 'white', textDecoration: 'none', fontSize: '1.5rem', fontWeight: 'bold' }}>
          HB-Staffing
        </Link>
        <ul style={{ display: 'flex', listStyle: 'none', margin: 0, padding: 0, gap: '2rem' }}>
          <li><Link to="/" style={{ color: 'white', textDecoration: 'none' }}>Dashboard</Link></li>
          <li><Link to="/roles" style={{ color: 'white', textDecoration: 'none' }}>Roles</Link></li>
          <li><Link to="/templates" style={{ color: 'white', textDecoration: 'none' }}>Templates</Link></li>
          <li><Link to="/staff" style={{ color: 'white', textDecoration: 'none' }}>Staff</Link></li>
          <li><Link to="/projects" style={{ color: 'white', textDecoration: 'none' }}>Projects</Link></li>
          <li><Link to="/assignments" style={{ color: 'white', textDecoration: 'none' }}>Assignments</Link></li>
          <li><Link to="/forecasts" style={{ color: 'white', textDecoration: 'none' }}>Forecasts</Link></li>
          <li><Link to="/reports" style={{ color: 'white', textDecoration: 'none' }}>Reports</Link></li>
        </ul>
      </div>
    </nav>
  );
};

export default NavBar;
