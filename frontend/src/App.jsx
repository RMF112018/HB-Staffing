import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';

// Components
import Dashboard from './components/Dashboard';
import StaffList from './components/StaffList';
import StaffForm from './components/StaffForm';
import ProjectList from './components/ProjectList';
import ProjectDetails from './components/ProjectDetails';
import ProjectForm from './components/ProjectForm';
import ProjectRoleRates from './components/ProjectRoleRates';
import AssignmentList from './components/AssignmentList';
import AssignmentForm from './components/AssignmentForm';
import RoleList from './components/RoleList';
import RoleForm from './components/RoleForm';
import TemplateList from './components/TemplateList';
import TemplateForm from './components/TemplateForm';
import Forecasts from './components/Forecasts';
import Reports from './components/Reports';

// Common components
import NavBar from './components/common/NavBar';
import ErrorBoundary from './components/common/ErrorBoundary';

// Context providers
import { LoadingProvider } from './contexts/LoadingContext';

function App() {
  return (
    <ErrorBoundary>
      <LoadingProvider>
        <Router>
          <div className="App">
            <NavBar />
            <main className="main-content">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/roles" element={<RoleList />} />
                <Route path="/roles/new" element={<RoleForm />} />
                <Route path="/roles/:id/edit" element={<RoleForm />} />
                <Route path="/templates" element={<TemplateList />} />
                <Route path="/templates/new" element={<TemplateForm />} />
                <Route path="/templates/:id/edit" element={<TemplateForm />} />
                <Route path="/staff" element={<StaffList />} />
                <Route path="/staff/new" element={<StaffForm />} />
                <Route path="/staff/:id/edit" element={<StaffForm />} />
                <Route path="/projects" element={<ProjectList />} />
                <Route path="/projects/new" element={<ProjectForm />} />
                <Route path="/projects/:id" element={<ProjectDetails />} />
                <Route path="/projects/:id/edit" element={<ProjectForm />} />
                <Route path="/projects/:id/rates" element={<ProjectRoleRates />} />
                <Route path="/assignments" element={<AssignmentList />} />
                <Route path="/assignments/new" element={<AssignmentForm />} />
                <Route path="/assignments/:id/edit" element={<AssignmentForm />} />
                <Route path="/forecasts" element={<Forecasts />} />
                <Route path="/reports" element={<Reports />} />
              </Routes>
            </main>
          </div>
        </Router>
      </LoadingProvider>
    </ErrorBoundary>
  );
}

export default App;
