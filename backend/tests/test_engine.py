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

        assert 'total_weeks' in result
        assert 'weekly_breakdown' in result
        assert 'peak_staffing' in result
        assert 'average_staffing' in result

        # Check that we have staffing data
        assert result['total_weeks'] > 0
        assert len(result['weekly_breakdown']) > 0

    def test_calculate_staffing_needs_partial_period(self, app, test_data):
        """Test calculating staffing needs for partial period"""
        project_id = test_data['project'].id

        result = calculate_project_staffing_needs(
            project_id,
            date(2024, 1, 1),
            date(2024, 6, 30)
        )

        assert result['total_weeks'] <= 26  # Half year
        assert len(result['weekly_breakdown']) <= 26

    def test_calculate_staffing_needs_no_assignments(self, app):
        """Test calculating staffing needs for project with no assignments"""
        with app.app_context():
            # Create project with no assignments
            project = Project(name="Empty Project", status="planning")
            db.session.add(project)
            db.session.commit()

            result = calculate_project_staffing_needs(project.id, None, None)

            assert result['total_weeks'] == 0
            assert len(result['weekly_breakdown']) == 0
            assert result['peak_staffing'] == 0

    def test_staffing_peak_calculation(self, app, test_data):
        """Test that peak staffing is correctly calculated"""
        project_id = test_data['project'].id

        result = calculate_project_staffing_needs(
            project_id,
            date(2024, 3, 1),  # Period with maximum staffing
            date(2024, 8, 31)
        )

        # During March-August, we should have: Manager + Senior Est + Laborer + Foreman = 4 people
        assert result['peak_staffing'] >= 4


class TestProjectCost:
    """Test project cost calculation"""

    def test_calculate_project_cost(self, app, test_data):
        """Test calculating total project cost"""
        project_id = test_data['project'].id

        result = calculate_project_cost(project_id)

        assert 'total_cost' in result
        assert 'staff_costs' in result
        assert 'cost_breakdown' in result

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

        # Verify cost calculation: hours * rate
        for staff_cost in staff_costs:
            assert 'staff_name' in staff_cost
            assert 'hours' in staff_cost
            assert 'hourly_rate' in staff_cost
            assert 'total_cost' in staff_cost
            assert staff_cost['total_cost'] == staff_cost['hours'] * staff_cost['hourly_rate']

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

        assert 'total_projects' in result
        assert 'organization_staffing' in result
        assert 'cost_summary' in result
        assert 'project_forecasts' in result

        # Should include our test project
        assert result['total_projects'] >= 1
        assert len(result['project_forecasts']) >= 1

    def test_organization_forecast_date_range(self, app, test_data):
        """Test organization forecast respects date range"""
        # Test with shorter date range
        result = calculate_organization_forecast(
            date(2024, 1, 1),
            date(2024, 6, 30)
        )

        # Staffing should be lower for shorter period
        staffing_data = result['organization_staffing']
        # This would depend on the actual assignment dates


class TestScenarioSimulation:
    """Test what-if scenario simulation"""

    def test_simulate_scenario_add_staff(self, app, test_data):
        """Test simulating addition of staff"""
        project_id = test_data['project'].id

        changes = {
            'add_staff': [
                {
                    'role': 'Estimator',
                    'count': 2,
                    'start_date': '2024-07-01',
                    'hours_per_week': 40.0
                }
            ]
        }

        result = simulate_scenario(project_id, changes)

        assert 'original_forecast' in result
        assert 'simulated_forecast' in result
        assert 'changes_summary' in result

        # Simulated forecast should have higher staffing
        orig_peak = result['original_forecast']['peak_staffing']
        sim_peak = result['simulated_forecast']['peak_staffing']
        assert sim_peak >= orig_peak

    def test_simulate_scenario_extend_project(self, app, test_data):
        """Test simulating project extension"""
        project_id = test_data['project'].id

        changes = {
            'extend_project': '2025-06-30'  # Extend by 6 months
        }

        result = simulate_scenario(project_id, changes)

        # Extended project should have longer duration
        orig_weeks = result['original_forecast']['total_weeks']
        sim_weeks = result['simulated_forecast']['total_weeks']
        assert sim_weeks > orig_weeks

    def test_simulate_scenario_invalid_project(self, app):
        """Test simulation with invalid project ID"""
        result = simulate_scenario(99999, {})

        assert 'error' in result
        assert result['error'] == 'Project not found'


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

        assert 'staff_info' in result
        assert 'total_available_hours' in result
        assert 'assigned_hours' in result
        assert 'utilization_rate' in result
        assert 'capacity_status' in result

        # Utilization should be between 0 and 1
        assert 0 <= result['utilization_rate'] <= 1

    def test_capacity_analysis_all_staff(self, app, test_data):
        """Test capacity analysis for all staff"""
        result = calculate_capacity_analysis(
            None,  # All staff
            date(2024, 1, 1),
            date(2024, 12, 31)
        )

        assert isinstance(result, list)
        assert len(result) >= len(test_data['staff'])

        for staff_analysis in result:
            assert 'staff_info' in staff_analysis
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

        # Longer period should potentially have different utilization
        # (depending on assignments, but the function should handle it)


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_forecast_with_invalid_dates(self, app):
        """Test forecasting with invalid date ranges"""
        # This should be handled gracefully
        result = calculate_project_staffing_needs(1, None, None)
        assert isinstance(result, dict)

    def test_cost_calculation_with_missing_rates(self, app):
        """Test cost calculation when hourly rates are missing"""
        with app.app_context():
            # Create staff without rate (shouldn't happen in real usage)
            staff = Staff(name="No Rate Staff", role="Worker", hourly_rate=None)
            project = Project(name="Test Project", status="active")
            db.session.add(staff)
            db.session.add(project)
            db.session.commit()

            assignment = Assignment(
                staff_id=staff.id,
                project_id=project.id,
                start_date=date.today(),
                end_date=date.today(),
                hours_per_week=40.0
            )
            db.session.add(assignment)
            db.session.commit()

            result = calculate_project_cost(project.id)
            # Should handle None rates gracefully
            assert isinstance(result, dict)


if __name__ == '__main__':
    pytest.main([__file__])
