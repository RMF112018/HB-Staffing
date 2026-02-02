"""
Unit tests for HB-Staffing forecasting engine
"""

import pytest
from datetime import date, datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import (
    calculate_project_staffing_needs,
    calculate_project_cost,
    calculate_organization_forecast,
    simulate_scenario,
    detect_staffing_gaps,
    calculate_capacity_analysis
)
from app import create_app
from models import db, Staff, Project, Assignment


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_data(app):
    """Create test data for forecasting tests."""
    with app.app_context():
        # Create test staff with different roles and rates
        staff_data = [
            {'name': 'Project Manager', 'role': 'Manager', 'hourly_rate': 80.0},
            {'name': 'Senior Estimator', 'role': 'Estimator', 'hourly_rate': 70.0},
            {'name': 'Junior Estimator', 'role': 'Estimator', 'hourly_rate': 50.0},
            {'name': 'General Laborer', 'role': 'Laborer', 'hourly_rate': 35.0},
            {'name': 'Foreman', 'role': 'Supervisor', 'hourly_rate': 55.0}
        ]

        staff_members = []
        for data in staff_data:
            staff = Staff(**data)
            staff_members.append(staff)
            db.session.add(staff)

        # Create test project
        project = Project(
            name="Large Construction Project",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            status="active",
            budget=2000000.0
        )
        db.session.add(project)
        db.session.commit()

        # Create assignments spanning different periods
        assignments_data = [
            # Project Manager - full year
            {'staff_id': 1, 'start_date': date(2024, 1, 1), 'end_date': date(2024, 12, 31), 'hours_per_week': 45.0},
            # Senior Estimator - first half
            {'staff_id': 2, 'start_date': date(2024, 1, 1), 'end_date': date(2024, 6, 30), 'hours_per_week': 40.0},
            # Junior Estimator - second half
            {'staff_id': 3, 'start_date': date(2024, 7, 1), 'end_date': date(2024, 12, 31), 'hours_per_week': 40.0},
            # Laborers - peak periods
            {'staff_id': 4, 'start_date': date(2024, 3, 1), 'end_date': date(2024, 8, 31), 'hours_per_week': 40.0},
            {'staff_id': 4, 'start_date': date(2024, 9, 1), 'end_date': date(2024, 12, 31), 'hours_per_week': 35.0},
            # Foreman - full year
            {'staff_id': 5, 'start_date': date(2024, 1, 1), 'end_date': date(2024, 12, 31), 'hours_per_week': 50.0}
        ]

        for assign_data in assignments_data:
            assignment = Assignment(
                project_id=project.id,
                **assign_data
            )
            db.session.add(assignment)

        db.session.commit()

        return {
            'staff': staff_members,
            'project': project,
            'assignments': assignments_data
        }


class TestProjectStaffingNeeds:
    """Test project staffing needs calculation"""

    def test_calculate_staffing_needs_full_year(self, app, test_data):
        """Test calculating staffing needs for full project year"""
        project_id = test_data['project'].id

        result = calculate_project_staffing_needs(
            project_id,
            date(2024, 1, 1),
            date(2024, 12, 31)
        )

        # Check expected keys in result
        assert 'project_id' in result
        assert 'project_name' in result
        assert 'forecast_period' in result
        assert 'weekly_staffing' in result
        assert 'staff_breakdown' in result
        assert 'total_estimated_cost' in result
        assert 'assignments_count' in result

        # Check that we have staffing data
        assert len(result['weekly_staffing']) > 0
        assert result['assignments_count'] > 0

    def test_calculate_staffing_needs_partial_period(self, app, test_data):
        """Test calculating staffing needs for partial period"""
        project_id = test_data['project'].id

        result = calculate_project_staffing_needs(
            project_id,
            date(2024, 1, 1),
            date(2024, 6, 30)
        )

        # Half year should have roughly 26 weeks of data
        assert len(result['weekly_staffing']) <= 30  # Allow some margin for week alignment

    def test_calculate_staffing_needs_no_assignments(self, app):
        """Test calculating staffing needs for project with no assignments"""
        with app.app_context():
            # Create project with dates but no assignments
            project = Project(
                name="Empty Project",
                status="planning",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31)
            )
            db.session.add(project)
            db.session.commit()

            result = calculate_project_staffing_needs(project.id)

            assert result['assignments_count'] == 0
            assert result['total_estimated_cost'] == 0


class TestProjectCost:
    """Test project cost calculation"""

    def test_calculate_project_cost(self, app, test_data):
        """Test calculating total project cost"""
        project_id = test_data['project'].id

        result = calculate_project_cost(project_id)

        # Check expected keys
        assert 'project_id' in result
        assert 'project_name' in result
        assert 'total_cost' in result
        assert 'staff_costs' in result
        assert 'assignments_count' in result
        assert 'budget' in result
        assert 'budget_variance' in result

        # Check that costs are calculated
        assert result['total_cost'] > 0
        assert len(result['staff_costs']) > 0

    def test_cost_breakdown_by_staff(self, app, test_data):
        """Test cost breakdown by individual staff members"""
        project_id = test_data['project'].id

        result = calculate_project_cost(project_id)

        # Should have cost data for each assigned staff member
        staff_costs = result['staff_costs']
        assert len(staff_costs) >= 4  # At least 4 unique staff members

    def test_project_with_no_assignments_cost(self, app):
        """Test cost calculation for project with no assignments"""
        with app.app_context():
            project = Project(name="Costless Project", status="planning")
            db.session.add(project)
            db.session.commit()

            result = calculate_project_cost(project.id)

            assert result['total_cost'] == 0
            assert len(result['staff_costs']) == 0


class TestOrganizationForecast:
    """Test organization-wide forecasting"""

    def test_calculate_organization_forecast(self, app, test_data):
        """Test calculating organization-wide forecast"""
        result = calculate_organization_forecast(
            date(2024, 1, 1),
            date(2024, 12, 31)
        )

        # Check expected keys
        assert 'forecast_period' in result
        assert 'weekly_forecast' in result
        assert 'project_forecasts' in result
        assert 'staff_utilization' in result
        assert 'total_estimated_cost' in result
        assert 'projects_count' in result

        # Should include our test project
        assert result['projects_count'] >= 1
        assert len(result['project_forecasts']) >= 1

    def test_organization_forecast_date_range(self, app, test_data):
        """Test organization forecast respects date range"""
        # Test with shorter date range
        result = calculate_organization_forecast(
            date(2024, 1, 1),
            date(2024, 6, 30)
        )

        # Should have staff utilization data
        assert len(result['staff_utilization']) >= 1


class TestScenarioSimulation:
    """Test what-if scenario simulation"""

    def test_simulate_scenario_add_assignment(self, app, test_data):
        """Test simulating addition of assignment"""
        project_id = test_data['project'].id
        staff_id = test_data['staff'][2].id  # Junior Estimator

        changes = {
            'add_assignments': [
                {
                    'staff_id': staff_id,
                    'start_date': '2024-01-01',
                    'end_date': '2024-06-30',
                    'hours_per_week': 20.0,
                    'role_on_project': 'Additional Support'
                }
            ]
        }

        result = simulate_scenario(project_id, changes)

        assert 'current_forecast' in result
        assert 'simulated_forecast' in result
        assert 'changes_applied' in result
        assert 'impact_analysis' in result

        # Simulated forecast should have more assignments
        assert result['simulated_forecast']['assignments_count'] > result['current_forecast']['assignments_count']

    def test_simulate_scenario_extend_dates(self, app, test_data):
        """Test simulating project extension"""
        project_id = test_data['project'].id

        changes = {
            'extend_dates': {'end_date': '2025-06-30'}  # Extend by 6 months
        }

        result = simulate_scenario(project_id, changes)

        # Extended project should have longer duration
        orig_end = result['current_forecast']['forecast_period']['end_date']
        sim_end = result['simulated_forecast']['forecast_period']['end_date']
        assert sim_end > orig_end

    def test_simulate_scenario_invalid_project(self, app):
        """Test simulation with invalid project ID"""
        with pytest.raises(ValueError) as exc_info:
            simulate_scenario(99999, {})

        assert 'not found' in str(exc_info.value).lower()


class TestStaffingGaps:
    """Test staffing gap detection"""

    def test_detect_staffing_gaps_no_gaps(self, app, test_data):
        """Test gap detection when staffing is adequate"""
        project_id = test_data['project'].id

        gaps = detect_staffing_gaps(project_id, date(2024, 1, 1), date(2024, 12, 31))

        # Our test data should have adequate staffing
        assert isinstance(gaps, list)

    def test_detect_staffing_gaps_with_project_filter(self, app, test_data):
        """Test gap detection for specific project"""
        project_id = test_data['project'].id

        gaps = detect_staffing_gaps(project_id, date(2024, 1, 1), date(2024, 6, 30))

        assert isinstance(gaps, list)

    def test_detect_staffing_gaps_all_projects(self, app, test_data):
        """Test gap detection across all projects"""
        gaps = detect_staffing_gaps(None, date(2024, 1, 1), date(2024, 12, 31))

        assert isinstance(gaps, list)


class TestCapacityAnalysis:
    """Test capacity analysis functionality"""

    def test_calculate_capacity_analysis(self, app, test_data):
        """Test capacity analysis for staff member"""
        staff_id = test_data['staff'][0].id  # Project Manager

        result = calculate_capacity_analysis(
            staff_id,
            date(2024, 1, 1),
            date(2024, 12, 31)
        )

        # Check expected keys
        assert 'staff_id' in result
        assert 'staff_name' in result
        assert 'role' in result
        assert 'assigned_hours' in result
        assert 'available_hours' in result
        assert 'utilization_rate' in result
        assert 'overallocated' in result

        # Utilization should be between 0 and a reasonable max (could be > 1 if overallocated)
        assert result['utilization_rate'] >= 0

    def test_capacity_analysis_all_staff(self, app, test_data):
        """Test capacity analysis for all staff"""
        result = calculate_capacity_analysis(
            None,  # All staff
            date(2024, 1, 1),
            date(2024, 12, 31)
        )

        # Returns a dict mapping staff_id to their analysis
        assert isinstance(result, dict)
        assert len(result) >= len(test_data['staff'])

        for staff_id, staff_analysis in result.items():
            assert 'staff_name' in staff_analysis
            assert 'utilization_rate' in staff_analysis

    def test_capacity_analysis_date_range(self, app, test_data):
        """Test capacity analysis respects date range"""
        staff_id = test_data['staff'][0].id

        # Test with shorter date range
        result_short = calculate_capacity_analysis(
            staff_id,
            date(2024, 1, 1),
            date(2024, 6, 30)
        )

        result_long = calculate_capacity_analysis(
            staff_id,
            date(2024, 1, 1),
            date(2024, 12, 31)
        )

        # Longer period should have more available hours
        assert result_long['available_hours'] > result_short['available_hours']


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_forecast_with_missing_project_dates(self, app):
        """Test forecasting when project has no dates set"""
        with app.app_context():
            project = Project(name="No Dates Project", status="planning")
            db.session.add(project)
            db.session.commit()

            # Should raise ValueError since dates are required
            with pytest.raises(ValueError):
                calculate_project_staffing_needs(project.id, None, None)

    def test_cost_calculation_project_not_found(self, app):
        """Test cost calculation for non-existent project"""
        with pytest.raises(ValueError) as exc_info:
            calculate_project_cost(99999)

        assert 'not found' in str(exc_info.value).lower()


if __name__ == '__main__':
    pytest.main([__file__])
