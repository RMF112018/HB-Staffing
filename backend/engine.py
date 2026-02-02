from datetime import datetime, date, timedelta
from collections import defaultdict
import json

def get_models():
    """Import models - call this inside engine functions"""
    from models import Staff, Project, Assignment
    return Staff, Project, Assignment

def calculate_date_range_overlap(start1, end1, start2, end2):
    """
    Calculate the number of overlapping days between two date ranges.

    Args:
        start1, end1: First date range
        start2, end2: Second date range

    Returns:
        int: Number of overlapping days
    """
    if not all([start1, end1, start2, end2]):
        return 0

    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)

    if overlap_start <= overlap_end:
        return (overlap_end - overlap_start).days + 1  # +1 to include end date
    return 0

def calculate_assignment_hours_in_period(assignment, period_start, period_end):
    """
    Calculate how many hours an assignment contributes in a given period.

    Args:
        assignment: Assignment object
        period_start, period_end: Date range to calculate for

    Returns:
        float: Total hours in the period
    """
    # Find overlap between assignment and period
    overlap_days = calculate_date_range_overlap(
        assignment.start_date, assignment.end_date,
        period_start, period_end
    )

    if overlap_days <= 0:
        return 0

    # Calculate weeks in the period
    weeks_in_period = overlap_days / 7.0

    # Return hours for this period
    return weeks_in_period * assignment.hours_per_week

def calculate_staff_capacity_in_period(staff_id, period_start, period_end):
    """
    Calculate a staff member's total assigned hours in a given period.

    Args:
        staff_id: ID of the staff member
        period_start, period_end: Date range to check

    Returns:
        float: Total assigned hours in the period
    """
    Staff, Project, Assignment = get_models()

    assignments = Assignment.query.filter_by(staff_id=staff_id).all()
    total_hours = 0

    for assignment in assignments:
        total_hours += calculate_assignment_hours_in_period(assignment, period_start, period_end)

    return total_hours

def calculate_project_staffing_needs(project_id, start_date=None, end_date=None):
    """
    Calculate staffing needs for a project over a date range.

    Args:
        project_id: ID of the project
        start_date, end_date: Date range (defaults to project dates)

    Returns:
        dict: Staffing forecast with weekly breakdowns
    """
    Staff, Project, Assignment = get_models()

    project = Project.query.get(project_id)
    if not project:
        raise ValueError("Project not found")

    # Use project dates if not specified
    if not start_date:
        start_date = project.start_date
    if not end_date:
        end_date = project.end_date

    if not start_date or not end_date:
        raise ValueError("Project must have start and end dates, or dates must be provided")

    # Get all assignments for this project
    assignments = Assignment.query.filter_by(project_id=project_id).all()

    # Group assignments by week
    weekly_staffing = defaultdict(float)
    staff_breakdown = defaultdict(lambda: defaultdict(float))

    current_date = start_date
    while current_date <= end_date:
        week_start = current_date - timedelta(days=current_date.weekday())  # Monday of the week
        week_key = week_start.isoformat()

        for assignment in assignments:
            hours = calculate_assignment_hours_in_period(assignment, week_start, week_start + timedelta(days=6))
            if hours > 0:
                weekly_staffing[week_key] += hours
                staff_breakdown[week_key][assignment.staff_member.name] = hours

        current_date += timedelta(days=7)

    # Calculate total project cost
    total_cost = sum(assignment.estimated_cost for assignment in assignments)

    return {
        'project_id': project_id,
        'project_name': project.name,
        'forecast_period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'weekly_staffing': dict(weekly_staffing),
        'staff_breakdown': {week: dict(staff) for week, staff in staff_breakdown.items()},
        'total_estimated_cost': total_cost,
        'assignments_count': len(assignments)
    }

def calculate_project_cost(project_id):
    """
    Calculate total cost for a project based on all assignments.

    Args:
        project_id: ID of the project

    Returns:
        dict: Cost breakdown
    """
    Staff, Project, Assignment = get_models()

    project = Project.query.get(project_id)
    if not project:
        raise ValueError("Project not found")

    assignments = Assignment.query.filter_by(project_id=project_id).all()

    total_cost = 0
    staff_costs = defaultdict(float)

    for assignment in assignments:
        cost = assignment.estimated_cost
        total_cost += cost
        staff_costs[assignment.staff_member.name] += cost

    return {
        'project_id': project_id,
        'project_name': project.name,
        'total_cost': total_cost,
        'staff_costs': dict(staff_costs),
        'assignments_count': len(assignments),
        'budget': project.budget,
        'budget_variance': (project.budget - total_cost) if project.budget else None
    }

def calculate_organization_forecast(start_date, end_date):
    """
    Calculate organization-wide staffing forecast.

    Args:
        start_date, end_date: Date range for forecast

    Returns:
        dict: Organization-wide forecast
    """
    Staff, Project, Assignment = get_models()

    # Get all active projects
    projects = Project.query.filter(Project.status.in_(['planning', 'active'])).all()

    # Group by week
    weekly_forecast = defaultdict(lambda: {'total_hours': 0, 'projects': defaultdict(float), 'staff': defaultdict(float)})
    project_forecasts = {}
    total_cost = 0

    for project in projects:
        try:
            project_forecast = calculate_project_staffing_needs(project.id, start_date, end_date)
            project_forecasts[project.id] = project_forecast

            # Aggregate weekly data
            for week, hours in project_forecast['weekly_staffing'].items():
                weekly_forecast[week]['total_hours'] += hours
                weekly_forecast[week]['projects'][project.name] += hours

            total_cost += project_forecast['total_estimated_cost']

        except ValueError:
            # Skip projects without dates
            continue

    # Get staff utilization
    staff_utilization = {}
    all_staff = Staff.query.all()

    for staff in all_staff:
        capacity_hours = calculate_staff_capacity_in_period(staff.id, start_date, end_date)
        total_available_hours = ((end_date - start_date).days + 1) / 7.0 * 40  # Assuming 40 hours/week standard

        staff_utilization[staff.name] = {
            'assigned_hours': capacity_hours,
            'available_hours': total_available_hours,
            'utilization_rate': (capacity_hours / total_available_hours) if total_available_hours > 0 else 0,
            'role': staff.role
        }

    return {
        'forecast_period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'weekly_forecast': dict(weekly_forecast),
        'project_forecasts': project_forecasts,
        'staff_utilization': staff_utilization,
        'total_estimated_cost': total_cost,
        'projects_count': len(project_forecasts)
    }

def simulate_scenario(project_id, changes):
    """
    Simulate "what-if" scenarios for project staffing.

    Args:
        project_id: ID of the project
        changes: Dict of changes to simulate

    Returns:
        dict: Comparison of current vs simulated forecast
    """
    # This is a simplified implementation
    # In a real implementation, this would create temporary assignments
    # and calculate the impact

    current_forecast = calculate_project_staffing_needs(project_id)

    # For now, just return the current forecast with a note
    return {
        'current_forecast': current_forecast,
        'simulated_forecast': current_forecast,  # Would be modified based on changes
        'changes_applied': changes,
        'note': 'Scenario simulation not fully implemented yet'
    }

def detect_staffing_gaps(project_id=None, start_date=None, end_date=None):
    """
    Detect potential staffing gaps for projects.

    Args:
        project_id: Specific project to check (optional)
        start_date, end_date: Date range to check

    Returns:
        list: List of detected gaps
    """
    gaps = []

    if project_id:
        # Check specific project
        try:
            forecast = calculate_project_staffing_needs(project_id, start_date, end_date)
            # Simple gap detection: if any week has 0 hours
            for week, hours in forecast['weekly_staffing'].items():
                if hours == 0:
                    gaps.append({
                        'type': 'project_gap',
                        'project_id': project_id,
                        'project_name': forecast['project_name'],
                        'week': week,
                        'message': f'No staffing assigned for week of {week}'
                    })
        except ValueError:
            pass
    else:
        # Check all projects
        Staff, Project, Assignment = get_models()
        projects = Project.query.filter(Project.status.in_(['planning', 'active'])).all()

        for project in projects:
            project_gaps = detect_staffing_gaps(project.id, start_date, end_date)
            gaps.extend(project_gaps)

    return gaps

def calculate_capacity_analysis(staff_id=None, start_date=None, end_date=None):
    """
    Analyze staff capacity and utilization.

    Args:
        staff_id: Specific staff member (optional)
        start_date, end_date: Date range

    Returns:
        dict: Capacity analysis
    """
    Staff, Project, Assignment = get_models()

    if staff_id:
        staff = Staff.query.get(staff_id)
        if not staff:
            raise ValueError("Staff member not found")

        capacity = calculate_staff_capacity_in_period(staff_id, start_date, end_date)
        total_available = ((end_date - start_date).days + 1) / 7.0 * 40  # 40 hours/week

        return {
            'staff_id': staff_id,
            'staff_name': staff.name,
            'role': staff.role,
            'assigned_hours': capacity,
            'available_hours': total_available,
            'utilization_rate': (capacity / total_available) if total_available > 0 else 0,
            'overallocated': capacity > total_available
        }
    else:
        # Analyze all staff
        all_staff = Staff.query.all()
        analysis = {}

        for staff in all_staff:
            analysis[staff.id] = calculate_capacity_analysis(staff.id, start_date, end_date)

        return analysis
