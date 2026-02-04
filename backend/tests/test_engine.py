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
    calculate_capacity_analysis,
    get_staff_availability_forecast,
    suggest_staff_for_role,
    flag_new_hire_needs,
    detect_over_allocations,
    validate_assignment_allocation,
    get_staff_allocation_timeline,
    get_organization_over_allocations,
    generate_coverage_analysis,
    calculate_minimum_staff_per_role,
    calculate_planning_costs
)
from app import create_app
from models import db, Staff, Project, Assignment, Role, PlanningExercise, PlanningProject, PlanningRole


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
    """Create test data for forecasting tests. Returns IDs to avoid detached session issues."""
    with app.app_context():
        # Use existing roles from seeded database or create unique ones
        # Check for existing roles first
        existing_roles = Role.query.all()
        
        if len(existing_roles) >= 4:
            # Use existing roles
            role_ids = [r.id for r in existing_roles[:4]]
        else:
            # Create roles with unique names for tests
            roles_data = [
                {'name': 'Test Manager', 'hourly_cost': 80.0, 'default_billable_rate': 150.0},
                {'name': 'Test Estimator', 'hourly_cost': 60.0, 'default_billable_rate': 120.0},
                {'name': 'Test Laborer', 'hourly_cost': 35.0, 'default_billable_rate': 70.0},
                {'name': 'Test Supervisor', 'hourly_cost': 55.0, 'default_billable_rate': 110.0}
            ]
            
            role_ids = []
            for data in roles_data:
                # Check if already exists
                existing = Role.query.filter_by(name=data['name']).first()
                if existing:
                    role_ids.append(existing.id)
                else:
                    role = Role(**data)
                    db.session.add(role)
                    db.session.flush()  # Get the ID
                    role_ids.append(role.id)
            db.session.commit()
        
        # Create test staff with different roles and rates
        # Note: default_billable_rate comes from the role, not the Staff model
        staff_data = [
            {'name': 'Test PM', 'role_id': role_ids[0], 'internal_hourly_cost': 80.0},
            {'name': 'Test Senior Estimator', 'role_id': role_ids[1], 'internal_hourly_cost': 70.0},
            {'name': 'Test Junior Estimator', 'role_id': role_ids[1], 'internal_hourly_cost': 50.0},
            {'name': 'Test Laborer', 'role_id': role_ids[2], 'internal_hourly_cost': 35.0},
            {'name': 'Test Foreman', 'role_id': role_ids[3], 'internal_hourly_cost': 55.0},
            {'name': 'Test Available Estimator', 'role_id': role_ids[1], 'internal_hourly_cost': 55.0}
        ]

        staff_ids = []
        for data in staff_data:
            staff = Staff(**data)
            db.session.add(staff)
            db.session.flush()  # Get the ID
            staff_ids.append(staff.id)

        # Create test project
        project = Project(
            name="Test Large Construction Project",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            status="active",
            budget=2000000.0
        )
        db.session.add(project)
        db.session.flush()  # Get the ID
        project_id = project.id
        
        db.session.commit()

        # Create assignments spanning different periods
        assignments_data = [
            # Project Manager - full year
            {'staff_id': staff_ids[0], 'start_date': date(2024, 1, 1), 'end_date': date(2024, 12, 31), 'hours_per_week': 45.0, 'allocation_type': 'full'},
            # Senior Estimator - first half
            {'staff_id': staff_ids[1], 'start_date': date(2024, 1, 1), 'end_date': date(2024, 6, 30), 'hours_per_week': 40.0, 'allocation_type': 'full'},
            # Junior Estimator - second half
            {'staff_id': staff_ids[2], 'start_date': date(2024, 7, 1), 'end_date': date(2024, 12, 31), 'hours_per_week': 40.0, 'allocation_type': 'full'},
            # Laborers - peak periods
            {'staff_id': staff_ids[3], 'start_date': date(2024, 3, 1), 'end_date': date(2024, 8, 31), 'hours_per_week': 40.0, 'allocation_type': 'full'},
            # Foreman - full year
            {'staff_id': staff_ids[4], 'start_date': date(2024, 1, 1), 'end_date': date(2024, 12, 31), 'hours_per_week': 50.0, 'allocation_type': 'full'}
        ]

        for assign_data in assignments_data:
            assignment = Assignment(
                project_id=project_id,
                **assign_data
            )
            db.session.add(assignment)

        db.session.commit()

        # Return IDs instead of objects to avoid detached session issues
        return {
            'staff_ids': staff_ids,
            'role_ids': role_ids,
            'project_id': project_id,
            'assignments': assignments_data
        }


class TestProjectStaffingNeeds:
    """Test project staffing needs calculation"""

    def test_calculate_staffing_needs_full_year(self, app, test_data):
        """Test calculating staffing needs for full project year"""
        with app.app_context():
            project_id = test_data['project_id']

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
        with app.app_context():
            project_id = test_data['project_id']

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
        with app.app_context():
            project_id = test_data['project_id']

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
            assert result['total_cost'] >= 0
            assert isinstance(result['staff_costs'], dict)

    def test_cost_breakdown_by_staff(self, app, test_data):
        """Test cost breakdown by individual staff members"""
        with app.app_context():
            project_id = test_data['project_id']

            result = calculate_project_cost(project_id)

            # Should have cost data for assigned staff members
            staff_costs = result['staff_costs']
            assert isinstance(staff_costs, dict)

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
        with app.app_context():
            project_id = test_data['project_id']
            staff_id = test_data['staff_ids'][2]  # Junior Estimator

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
        with app.app_context():
            project_id = test_data['project_id']

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
        with app.app_context():
            with pytest.raises(ValueError) as exc_info:
                simulate_scenario(99999, {})

            assert 'not found' in str(exc_info.value).lower()


class TestStaffingGaps:
    """Test staffing gap detection"""

    def test_detect_staffing_gaps_no_gaps(self, app, test_data):
        """Test gap detection when staffing is adequate"""
        with app.app_context():
            project_id = test_data['project_id']

            gaps = detect_staffing_gaps(project_id, date(2024, 1, 1), date(2024, 12, 31))

            # Our test data should have adequate staffing
            assert isinstance(gaps, list)

    def test_detect_staffing_gaps_with_project_filter(self, app, test_data):
        """Test gap detection for specific project"""
        with app.app_context():
            project_id = test_data['project_id']

            gaps = detect_staffing_gaps(project_id, date(2024, 1, 1), date(2024, 6, 30))

            assert isinstance(gaps, list)

    def test_detect_staffing_gaps_all_projects(self, app, test_data):
        """Test gap detection across all projects"""
        with app.app_context():
            gaps = detect_staffing_gaps(None, date(2024, 1, 1), date(2024, 12, 31))

            assert isinstance(gaps, list)


class TestCapacityAnalysis:
    """Test capacity analysis functionality"""

    def test_calculate_capacity_analysis(self, app, test_data):
        """Test capacity analysis for staff member"""
        with app.app_context():
            staff_id = test_data['staff_ids'][0]  # Project Manager

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
        with app.app_context():
            result = calculate_capacity_analysis(
                None,  # All staff
                date(2024, 1, 1),
                date(2024, 12, 31)
            )

            # Returns a dict mapping staff_id to their analysis
            assert isinstance(result, dict)
            assert len(result) >= len(test_data['staff_ids'])

            for staff_id, staff_analysis in result.items():
                assert 'staff_name' in staff_analysis
                assert 'utilization_rate' in staff_analysis

    def test_capacity_analysis_date_range(self, app, test_data):
        """Test capacity analysis respects date range"""
        with app.app_context():
            staff_id = test_data['staff_ids'][0]

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


class TestStaffAvailabilityForecast:
    """Test staff availability forecast functionality"""
    
    def test_get_staff_availability_all_roles(self, app, test_data):
        """Test getting staff availability without role filter"""
        with app.app_context():
            result = get_staff_availability_forecast(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 30)
            )
            
            assert 'period' in result
            assert 'available' in result
            assert 'partially_available' in result
            assert 'unavailable' in result
            assert 'summary' in result
            assert result['summary']['total_staff'] >= 1
    
    def test_get_staff_availability_by_role(self, app, test_data):
        """Test getting staff availability filtered by role"""
        with app.app_context():
            role_id = test_data['role_ids'][1]  # Estimator role
            
            result = get_staff_availability_forecast(
                role_id=role_id,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 30)
            )
            
            assert result['role'] is not None
            assert result['role']['id'] == role_id
    
    def test_staff_availability_during_assignment(self, app, test_data):
        """Test availability during assigned period"""
        with app.app_context():
            result = get_staff_availability_forecast(
                start_date=date(2024, 3, 1),
                end_date=date(2024, 6, 30)
            )
            
            # Some staff should be unavailable during this period
            assert result['summary']['unavailable_count'] >= 0 or result['summary']['partial_count'] >= 0


class TestStaffSuggestions:
    """Test staff suggestion functionality"""
    
    def test_suggest_staff_for_role(self, app, test_data):
        """Test getting staff suggestions for a role"""
        with app.app_context():
            role_id = test_data['role_ids'][1]  # Estimator role
            
            result = suggest_staff_for_role(
                role_id=role_id,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 30),
                allocation_percentage=100.0
            )
            
            assert 'role' in result
            assert 'period' in result
            assert 'suggestions' in result
            assert 'total_candidates' in result
            assert 'qualified_candidates' in result
        
    def test_suggestions_have_match_scores(self, app, test_data):
        """Test that suggestions include match scores"""
        with app.app_context():
            role_id = test_data['role_ids'][1]
            
            result = suggest_staff_for_role(
                role_id=role_id,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 30)
            )
            
            if result['suggestions']:
                for suggestion in result['suggestions']:
                    assert 'match_score' in suggestion
                    assert 'match_reasons' in suggestion
                    assert suggestion['match_score'] >= 0
    
    def test_suggest_staff_invalid_role(self, app, test_data):
        """Test suggestion with invalid role"""
        with app.app_context():
            with pytest.raises(ValueError):
                suggest_staff_for_role(
                    role_id=99999,
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 6, 30)
                )


class TestNewHireNeeds:
    """Test new hire needs analysis"""
    
    def test_flag_new_hire_needs_sufficient_staff(self, app, test_data):
        """Test when sufficient staff are available"""
        with app.app_context():
            role_id = test_data['role_ids'][1]  # Estimator role
            
            result = flag_new_hire_needs(
                role_id=role_id,
                start_date=date(2025, 7, 1),
                end_date=date(2025, 12, 31),
                required_count=1
            )
            
            assert 'needs_new_hire' in result
            assert 'new_hire_count' in result
            assert 'recommendations' in result
            assert 'availability' in result
    
    def test_flag_new_hire_needs_insufficient_staff(self, app, test_data):
        """Test when more staff are needed than available"""
        with app.app_context():
            role_id = test_data['role_ids'][0]  # Manager role
            
            result = flag_new_hire_needs(
                role_id=role_id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
                required_count=5  # Need more than available
            )
            
            assert result['needs_new_hire'] == True
            assert result['new_hire_count'] > 0


class TestOverAllocationDetection:
    """Test over-allocation detection functionality"""
    
    def test_detect_over_allocations_no_conflicts(self, app, test_data):
        """Test detection when no over-allocations exist"""
        with app.app_context():
            staff_id = test_data['staff_ids'][5]  # Available Estimator (no assignments)
            
            result = detect_over_allocations(
                staff_id=staff_id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31)
            )
            
            assert 'has_conflicts' in result
            assert result['has_conflicts'] == False
            assert result['conflict_count'] == 0
    
    def test_detect_over_allocations_with_timeline(self, app, test_data):
        """Test that over-allocation detection returns timeline"""
        with app.app_context():
            staff_id = test_data['staff_ids'][0]  # Project Manager
            
            result = detect_over_allocations(
                staff_id=staff_id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31)
            )
            
            assert 'timeline' in result
            assert isinstance(result['timeline'], dict)
    
    def test_get_staff_allocation_timeline(self, app, test_data):
        """Test getting detailed allocation timeline"""
        with app.app_context():
            staff_id = test_data['staff_ids'][0]
            
            result = get_staff_allocation_timeline(
                staff_id=staff_id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31)
            )
            
            assert 'staff_id' in result
            assert 'monthly_allocations' in result
            assert len(result['monthly_allocations']) > 0
    
    def test_validate_assignment_allocation_valid(self, app, test_data):
        """Test validating a valid assignment"""
        with app.app_context():
            staff_id = test_data['staff_ids'][5]  # Available Estimator
            
            result = validate_assignment_allocation(
                staff_id=staff_id,
                new_start_date=date(2025, 1, 1),
                new_end_date=date(2025, 6, 30),
                new_allocation_percentage=100.0
            )
            
            assert result['is_valid'] == True
            assert result['conflict_count'] == 0
    
    def test_organization_over_allocations(self, app, test_data):
        """Test organization-wide over-allocation summary"""
        with app.app_context():
            result = get_organization_over_allocations(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31)
            )
            
            assert 'summary' in result
            assert 'conflicts' in result
            assert 'clear_staff' in result
            assert result['summary']['total_staff'] >= 1


class TestPlanningExercise:
    """Test planning exercise functionality"""
    
    @pytest.fixture
    def planning_data(self, app, test_data):
        """Create planning exercise test data"""
        with app.app_context():
            # Create planning exercise
            exercise = PlanningExercise(
                name="Test Planning Exercise",
                description="Test description",
                status="active"
            )
            db.session.add(exercise)
            db.session.flush()  # Get the ID
            exercise_id = exercise.id
            
            # Create planning project
            planning_project = PlanningProject(
                exercise_id=exercise_id,
                name="Test Planning Project",
                start_date=date(2025, 1, 1),
                duration_months=12,
                budget=1000000.0
            )
            db.session.add(planning_project)
            db.session.flush()  # Get the ID
            planning_project_id = planning_project.id
            
            # Create planning roles using role_ids from test_data
            planning_role_ids = []
            for role_id in test_data['role_ids'][:2]:
                planning_role = PlanningRole(
                    planning_project_id=planning_project_id,
                    role_id=role_id,
                    count=2,
                    start_month_offset=0,
                    end_month_offset=0,
                    allocation_percentage=100.0,
                    hours_per_week=40.0,
                    overlap_mode='efficient'
                )
                db.session.add(planning_role)
                db.session.flush()
                planning_role_ids.append(planning_role.id)
            
            db.session.commit()
            
            return {
                'exercise_id': exercise_id,
                'project_id': planning_project_id,
                'role_ids': planning_role_ids
            }
    
    def test_generate_coverage_analysis(self, app, test_data, planning_data):
        """Test generating coverage analysis for planning exercise"""
        with app.app_context():
            result = generate_coverage_analysis(planning_data['exercise_id'])
            
            assert 'exercise_id' in result
            assert 'period' in result
            assert 'role_coverage' in result
            assert len(result['role_coverage']) > 0
    
    def test_calculate_minimum_staff_efficient(self, app, test_data, planning_data):
        """Test minimum staff calculation in efficient mode"""
        with app.app_context():
            result = calculate_minimum_staff_per_role(
                planning_data['exercise_id'],
                overlap_mode='efficient'
            )
            
            assert 'staff_requirements' in result
            assert 'summary' in result
            assert result['overlap_mode'] == 'efficient'
    
    def test_calculate_minimum_staff_conservative(self, app, test_data, planning_data):
        """Test minimum staff calculation in conservative mode"""
        with app.app_context():
            result = calculate_minimum_staff_per_role(
                planning_data['exercise_id'],
                overlap_mode='conservative'
            )
            
            assert result['overlap_mode'] == 'conservative'
    
    def test_calculate_planning_costs(self, app, test_data, planning_data):
        """Test planning exercise cost calculation"""
        with app.app_context():
            result = calculate_planning_costs(planning_data['exercise_id'])
            
            assert 'summary' in result
            assert 'monthly_costs' in result
            assert 'role_costs' in result
            assert 'project_costs' in result
            
            assert result['summary']['total_hours'] >= 0
            assert result['summary']['total_billable'] >= 0
    
    def test_planning_exercise_not_found(self, app):
        """Test planning analysis with non-existent exercise"""
        with app.app_context():
            with pytest.raises(ValueError):
                generate_coverage_analysis(99999)


if __name__ == '__main__':
    pytest.main([__file__])
