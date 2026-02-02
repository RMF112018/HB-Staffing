import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import NavBar from './components/common/NavBar';
import Dashboard from './components/Dashboard';
import StaffList from './components/StaffList';
import StaffForm from './components/StaffForm';
import ProjectList from './components/ProjectList';
import ProjectForm from './components/ProjectForm';
import AssignmentList from './components/AssignmentList';
import AssignmentForm from './components/AssignmentForm';
import Forecasts from './components/Forecasts';
import Reports from './components/Reports';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <NavBar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/staff" element={<StaffList />} />
            <Route path="/staff/new" element={<StaffForm />} />
            <Route path="/staff/:id/edit" element={<StaffForm />} />
            <Route path="/projects" element={<ProjectList />} />
            <Route path="/projects/new" element={<ProjectForm />} />
            <Route path="/projects/:id/edit" element={<ProjectForm />} />
            <Route path="/assignments" element={<AssignmentList />} />
            <Route path="/assignments/new" element={<AssignmentForm />} />
            <Route path="/forecasts" element={<Forecasts />} />
            <Route path="/reports" element={<Reports />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
