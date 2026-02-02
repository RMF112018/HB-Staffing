/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dashboard from './Dashboard';
import { staffAPI, projectAPI, assignmentAPI } from '../services/api';

// Mock the API calls
jest.mock('../services/api');
jest.mock('../contexts/LoadingContext');
jest.mock('../hooks/useApiError');

const mockStaffAPI = staffAPI;
const mockProjectAPI = projectAPI;
const mockAssignmentAPI = assignmentAPI;

describe('Dashboard Component', () => {
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();

    // Mock successful API responses
    mockStaffAPI.getAll.mockResolvedValue({
      data: [
        { id: 1, name: 'John Doe', role: 'Manager', hourly_rate: 75.0 },
        { id: 2, name: 'Jane Smith', role: 'Estimator', hourly_rate: 65.0 }
      ]
    });

    mockProjectAPI.getAll.mockResolvedValue({
      data: [
        { id: 1, name: 'Project Alpha', status: 'active', budget: 500000 },
        { id: 2, name: 'Project Beta', status: 'planning', budget: 300000 }
      ]
    });

    mockAssignmentAPI.getAll.mockResolvedValue({
      data: [
        { id: 1, staff_id: 1, project_id: 1, hours_per_week: 40 }
      ]
    });
  });

  test('renders dashboard with loading state initially', () => {
    render(<Dashboard />);

    // Should show loading skeleton or spinner
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
  });

  test('displays stats cards after data loads', async () => {
    render(<Dashboard />);

    // Wait for data to load
    await waitFor(() => {
      expect(mockStaffAPI.getAll).toHaveBeenCalled();
      expect(mockProjectAPI.getAll).toHaveBeenCalled();
      expect(mockAssignmentAPI.getAll).toHaveBeenCalled();
    });

    // Check if stats are displayed
    await waitFor(() => {
      expect(screen.getByText('Total Staff')).toBeInTheDocument();
      expect(screen.getByText('Active Projects')).toBeInTheDocument();
      expect(screen.getByText('Total Assignments')).toBeInTheDocument();
    });
  });

  test('displays correct staff count', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument(); // Total staff count
    });
  });

  test('displays correct project count', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument(); // Active projects count
    });
  });

  test('handles API errors gracefully', async () => {
    // Mock API error
    mockStaffAPI.getAll.mockRejectedValue(new Error('API Error'));

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  test('refresh button triggers data reload', async () => {
    render(<Dashboard />);

    // Wait for initial load
    await waitFor(() => {
      expect(mockStaffAPI.getAll).toHaveBeenCalledTimes(1);
    });

    // Click refresh button
    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    fireEvent.click(refreshButton);

    // Should call APIs again
    await waitFor(() => {
      expect(mockStaffAPI.getAll).toHaveBeenCalledTimes(2);
    });
  });

  test('displays upcoming deadlines', async () => {
    // Mock projects with upcoming deadlines
    mockProjectAPI.getAll.mockResolvedValue({
      data: [
        {
          id: 1,
          name: 'Urgent Project',
          status: 'active',
          end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString() // 1 week from now
        }
      ]
    });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/upcoming deadlines/i)).toBeInTheDocument();
    });
  });

  test('shows last updated timestamp', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/last updated/i)).toBeInTheDocument();
    });
  });
});
