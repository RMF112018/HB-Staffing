import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './NavBar.css';

const NavBar = () => {
  const location = useLocation();

  const isActive = (path) => {
    return location.pathname === path ? 'active' : '';
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/" className="brand-link">
          HB-Staffing
        </Link>
      </div>
      <ul className="navbar-nav">
        <li className="nav-item">
          <Link to="/" className={`nav-link ${isActive('/')}`}>
            Dashboard
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/staff" className={`nav-link ${isActive('/staff')}`}>
            Staff
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/projects" className={`nav-link ${isActive('/projects')}`}>
            Projects
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/assignments" className={`nav-link ${isActive('/assignments')}`}>
            Assignments
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/forecasts" className={`nav-link ${isActive('/forecasts')}`}>
            Forecasts
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/reports" className={`nav-link ${isActive('/reports')}`}>
            Reports
          </Link>
        </li>
      </ul>
    </nav>
  );
};

export default NavBar;
