from datetime import datetime, date, timedelta
from collections import defaultdict
import json

def get_models_and_db():
    """Import models and db - call this inside engine functions"""
    from models import Staff, Project, Assignment
    from db import db
    return db, Staff, Project, Assignment


def get_models():
    """Import models - call this inside engine functions"""
    _, Staff, Project, Assignment = get_models_and_db()
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

def calculate_assignment_hours_in_period(assignment, period_start, period_end, apply_allocation=True):
    """
    Calculate how many hours an assignment contributes in a given period.

    Args:
        assignment: Assignment object
        period_start, period_end: Date range to calculate for
        apply_allocation: Whether to apply allocation percentage (default True)

    Returns:
        float: Total hours in the period (optionally adjusted by allocation)
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

    # Calculate raw hours
    raw_hours = weeks_in_period * assignment.hours_per_week
    
    if apply_allocation:
        # Apply allocation percentage for the period
        allocation = assignment.get_allocation_for_period(period_start, period_end) / 100.0
        return raw_hours * allocation
    
    return raw_hours

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
    db, Staff, Project, Assignment = get_models_and_db()

    project = db.session.get(Project, project_id)
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
    weekly_staffing_raw = defaultdict(float)  # Without allocation applied
    staff_breakdown = defaultdict(lambda: defaultdict(float))

    current_date = start_date
    while current_date <= end_date:
        week_start = current_date - timedelta(days=current_date.weekday())  # Monday of the week
        week_key = week_start.isoformat()

        for assignment in assignments:
            # Hours with allocation applied
            hours = calculate_assignment_hours_in_period(assignment, week_start, week_start + timedelta(days=6), apply_allocation=True)
            # Raw hours without allocation
            raw_hours = calculate_assignment_hours_in_period(assignment, week_start, week_start + timedelta(days=6), apply_allocation=False)
            
            if hours > 0:
                weekly_staffing[week_key] += hours
                staff_breakdown[week_key][assignment.staff_member.name] = hours
            if raw_hours > 0:
                weekly_staffing_raw[week_key] += raw_hours

        current_date += timedelta(days=7)

    # Calculate total project costs (both raw and allocated)
    total_cost = sum(assignment.estimated_cost for assignment in assignments)
    total_allocated_cost = sum(assignment.allocated_estimated_cost for assignment in assignments)
    total_internal_cost = sum(assignment.internal_cost for assignment in assignments)
    total_allocated_internal_cost = sum(assignment.allocated_internal_cost for assignment in assignments)

    return {
        'project_id': project_id,
        'project_name': project.name,
        'forecast_period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'weekly_staffing': dict(weekly_staffing),  # Allocated hours
        'weekly_staffing_raw': dict(weekly_staffing_raw),  # Raw hours before allocation
        'staff_breakdown': {week: dict(staff) for week, staff in staff_breakdown.items()},
        # Raw costs (before allocation)
        'total_estimated_cost': total_cost,
        'total_internal_cost': total_internal_cost,
        # Allocated costs (after applying allocation percentage)
        'total_allocated_cost': total_allocated_cost,
        'total_allocated_internal_cost': total_allocated_internal_cost,
        'assignments_count': len(assignments)
    }

def calculate_project_cost(project_id):
    """
    Calculate total cost for a project based on all assignments.
    Uses project role rates when available, falls back to staff hourly rates.
    Includes both raw costs and allocated costs.

    Args:
        project_id: ID of the project

    Returns:
        dict: Cost breakdown with rate source information
    """
    db, Staff, Project, Assignment = get_models_and_db()

    project = db.session.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")

    assignments = Assignment.query.filter_by(project_id=project_id).all()

    # Raw totals
    total_cost = 0
    total_internal_cost = 0
    # Allocated totals
    total_allocated_cost = 0
    total_allocated_internal_cost = 0
    
    staff_costs = defaultdict(float)
    staff_allocated_costs = defaultdict(float)
    role_costs = defaultdict(float)
    role_allocated_costs = defaultdict(float)
    rate_sources = {'project_role_rate': 0, 'inherited_project_role_rate': 0, 'role_default_billable_rate': 0}
    assignment_details = []

    for assignment in assignments:
        # Raw costs
        cost = assignment.estimated_cost
        internal_cost = assignment.internal_cost
        # Allocated costs
        allocated_cost = assignment.allocated_estimated_cost
        allocated_internal_cost = assignment.allocated_internal_cost
        
        rate_info = assignment.get_effective_billable_rate()
        
        # Sum raw totals
        total_cost += cost
        total_internal_cost += internal_cost
        # Sum allocated totals
        total_allocated_cost += allocated_cost
        total_allocated_internal_cost += allocated_internal_cost
        
        staff_costs[assignment.staff_member.name] += cost
        staff_allocated_costs[assignment.staff_member.name] += allocated_cost
        
        if assignment.role_on_project:
            role_costs[assignment.role_on_project] += cost
            role_allocated_costs[assignment.role_on_project] += allocated_cost
        
        rate_sources[rate_info['source']] += 1
        
        assignment_details.append({
            'assignment_id': assignment.id,
            'staff_name': assignment.staff_member.name,
            'role_on_project': assignment.role_on_project,
            'billable_rate': rate_info['rate'],
            'rate_source': rate_info['source'],
            'total_hours': assignment.total_hours,
            'allocation_type': assignment.allocation_type,
            'allocation_percentage': assignment.allocation_percentage,
            'effective_allocation': assignment.effective_allocation,
            # Raw costs
            'cost': cost,
            'internal_cost': internal_cost,
            # Allocated costs
            'allocated_cost': allocated_cost,
            'allocated_internal_cost': allocated_internal_cost
        })

    return {
        'project_id': project_id,
        'project_name': project.name,
        'hierarchy_path': project.hierarchy_path,
        'is_folder': project.is_folder,
        # Raw costs (before allocation)
        'total_cost': total_cost,
        'total_internal_cost': total_internal_cost,
        # Allocated costs (after applying allocation percentage)
        'total_allocated_cost': total_allocated_cost,
        'total_allocated_internal_cost': total_allocated_internal_cost,
        # Margin calculations
        'total_margin': total_cost - total_internal_cost,
        'total_allocated_margin': total_allocated_cost - total_allocated_internal_cost,
        'staff_costs': dict(staff_costs),
        'staff_allocated_costs': dict(staff_allocated_costs),
        'role_costs': dict(role_costs),
        'role_allocated_costs': dict(role_allocated_costs),
        'rate_sources': rate_sources,
        'assignment_details': assignment_details,
        'assignments_count': len(assignments),
        'budget': project.budget,
        'budget_variance': (project.budget - total_allocated_cost) if project.budget else None
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
    total_allocated_cost = 0
    total_internal_cost = 0
    total_allocated_internal_cost = 0

    for project in projects:
        try:
            project_forecast = calculate_project_staffing_needs(project.id, start_date, end_date)
            project_forecasts[project.id] = project_forecast

            # Aggregate weekly data (using allocated hours)
            for week, hours in project_forecast['weekly_staffing'].items():
                weekly_forecast[week]['total_hours'] += hours
                weekly_forecast[week]['projects'][project.name] += hours

            total_cost += project_forecast['total_estimated_cost']
            total_allocated_cost += project_forecast['total_allocated_cost']
            total_internal_cost += project_forecast['total_internal_cost']
            total_allocated_internal_cost += project_forecast['total_allocated_internal_cost']

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
        # Raw costs
        'total_estimated_cost': total_cost,
        'total_internal_cost': total_internal_cost,
        # Allocated costs
        'total_allocated_cost': total_allocated_cost,
        'total_allocated_internal_cost': total_allocated_internal_cost,
        # Margins
        'total_margin': total_cost - total_internal_cost,
        'total_allocated_margin': total_allocated_cost - total_allocated_internal_cost,
        'projects_count': len(project_forecasts)
    }

def simulate_scenario(project_id, changes):
    """
    Simulate "what-if" scenarios for project staffing.

    Args:
        project_id: ID of the project
        changes: Dict of changes to simulate. Supported changes:
            - add_assignments: List of assignment dicts to add
            - remove_assignments: List of assignment IDs to remove
            - modify_hours: Dict mapping assignment_id to new hours_per_week
            - extend_dates: Dict with 'end_date' to extend project end date

    Returns:
        dict: Comparison of current vs simulated forecast
    """
    db, Staff, Project, Assignment = get_models_and_db()

    # Get the project
    project = db.session.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")

    # Calculate current forecast
    current_forecast = calculate_project_staffing_needs(project_id)

    # Get current assignments
    current_assignments = Assignment.query.filter_by(project_id=project_id).all()

    # Build simulated assignment data
    simulated_assignments = []
    for assignment in current_assignments:
        # Check if this assignment should be removed
        if changes.get('remove_assignments') and assignment.id in changes['remove_assignments']:
            continue

        # Get effective billable rate (uses project role rate if available)
        rate_info = assignment.get_effective_billable_rate()
        
        # Create a copy of assignment data for simulation
        assignment_data = {
            'id': assignment.id,
            'staff_id': assignment.staff_id,
            'staff_name': assignment.staff_member.name,
            'billable_rate': rate_info['rate'],  # Use effective billable rate
            'rate_source': rate_info['source'],
            'start_date': assignment.start_date,
            'end_date': assignment.end_date,
            'hours_per_week': assignment.hours_per_week,
            'role_on_project': assignment.role_on_project
        }

        # Apply hours modifications
        if changes.get('modify_hours') and str(assignment.id) in changes['modify_hours']:
            assignment_data['hours_per_week'] = changes['modify_hours'][str(assignment.id)]

        simulated_assignments.append(assignment_data)

    # Add new simulated assignments
    if changes.get('add_assignments'):
        for new_assignment in changes['add_assignments']:
            staff = db.session.get(Staff, new_assignment['staff_id'])
            if staff:
                # Parse dates if they're strings
                sim_start_date = new_assignment['start_date']
                sim_end_date = new_assignment['end_date']
                if isinstance(sim_start_date, str):
                    sim_start_date = datetime.fromisoformat(sim_start_date).date()
                if isinstance(sim_end_date, str):
                    sim_end_date = datetime.fromisoformat(sim_end_date).date()

                # Get billable rate from project role rates if available
                role_on_project = new_assignment.get('role_on_project', '')
                rate_info = None
                if role_on_project:
                    rate_info = project.get_role_rate_by_name(role_on_project)
                
                billable_rate = rate_info['rate'] if rate_info else (staff.default_billable_rate or 0)
                rate_source = rate_info['source'] if rate_info else 'role_default_billable_rate'

                simulated_assignments.append({
                    'id': f'simulated_{len(simulated_assignments)}',
                    'staff_id': staff.id,
                    'staff_name': staff.name,
                    'billable_rate': billable_rate,
                    'rate_source': rate_source,
                    'start_date': sim_start_date,
                    'end_date': sim_end_date,
                    'hours_per_week': new_assignment.get('hours_per_week', 40),
                    'role_on_project': role_on_project
                })

    # Determine date range for simulation
    start_date = project.start_date
    end_date = project.end_date

    # Apply date extension if specified
    if changes.get('extend_dates') and changes['extend_dates'].get('end_date'):
        new_end = changes['extend_dates']['end_date']
        if isinstance(new_end, str):
            new_end = datetime.fromisoformat(new_end).date()
        end_date = new_end

    # Calculate simulated weekly staffing
    weekly_staffing = defaultdict(float)
    staff_breakdown = defaultdict(lambda: defaultdict(float))
    total_cost = 0

    if start_date and end_date:
        current_date = start_date
        while current_date <= end_date:
            week_start = current_date - timedelta(days=current_date.weekday())
            week_key = week_start.isoformat()

            for assignment in simulated_assignments:
                # Calculate overlap
                overlap_days = calculate_date_range_overlap(
                    assignment['start_date'], assignment['end_date'],
                    week_start, week_start + timedelta(days=6)
                )

                if overlap_days > 0:
                    weeks_in_period = overlap_days / 7.0
                    hours = weeks_in_period * assignment['hours_per_week']
                    weekly_staffing[week_key] += hours
                    staff_breakdown[week_key][assignment['staff_name']] = hours

            current_date += timedelta(days=7)

    # Calculate total cost for simulated assignments using billable rates
    for assignment in simulated_assignments:
        if assignment['start_date'] and assignment['end_date']:
            duration_weeks = (assignment['end_date'] - assignment['start_date']).days / 7.0
            total_hours = duration_weeks * assignment['hours_per_week']
            total_cost += total_hours * assignment['billable_rate']

    simulated_forecast = {
        'project_id': project_id,
        'project_name': project.name,
        'forecast_period': {
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None
        },
        'weekly_staffing': dict(weekly_staffing),
        'staff_breakdown': {week: dict(staff) for week, staff in staff_breakdown.items()},
        'total_estimated_cost': total_cost,
        'assignments_count': len(simulated_assignments)
    }

    # Calculate differences
    cost_difference = simulated_forecast['total_estimated_cost'] - current_forecast['total_estimated_cost']
    assignment_difference = simulated_forecast['assignments_count'] - current_forecast['assignments_count']

    return {
        'current_forecast': current_forecast,
        'simulated_forecast': simulated_forecast,
        'changes_applied': changes,
        'impact_analysis': {
            'cost_difference': cost_difference,
            'assignment_difference': assignment_difference,
            'percentage_cost_change': (cost_difference / current_forecast['total_estimated_cost'] * 100) if current_forecast['total_estimated_cost'] > 0 else 0
        }
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
    db, Staff, Project, Assignment = get_models_and_db()

    if staff_id:
        staff = db.session.get(Staff, staff_id)
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


def generate_staff_planning_report(project_id, start_date=None, end_date=None, include_sub_projects=True):
    """
    Generate a comprehensive staff planning report for a project or project folder.
    Includes both real staff assignments and ghost staff placeholders.
    
    Args:
        project_id: ID of the project or project folder
        start_date: Report start date (defaults to earliest project date)
        end_date: Report end date (defaults to latest project date)
        include_sub_projects: If True and project is a folder, include sub-projects
        
    Returns:
        dict: Comprehensive report with monthly breakdowns, costs by role, and staff entries
    """
    from dateutil.relativedelta import relativedelta
    from models import GhostStaff, Role
    db, Staff, Project, Assignment = get_models_and_db()
    
    project = db.session.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")
    
    # Collect all projects to include in report
    projects_to_include = [project]
    sub_projects_data = []
    
    if project.is_folder and include_sub_projects:
        sub_projects = Project.query.filter_by(parent_project_id=project_id).all()
        projects_to_include.extend(sub_projects)
        sub_projects_data = [{'id': sp.id, 'name': sp.name, 'status': sp.status} for sp in sub_projects]
    
    # Collect all project IDs
    project_ids = [p.id for p in projects_to_include]
    
    # Determine date range
    all_dates = []
    for p in projects_to_include:
        if p.start_date:
            all_dates.append(p.start_date)
        if p.end_date:
            all_dates.append(p.end_date)
    
    # Get assignments and ghost staff to also consider their dates
    all_assignments = Assignment.query.filter(Assignment.project_id.in_(project_ids)).all()
    all_ghost_staff = GhostStaff.query.filter(
        GhostStaff.project_id.in_(project_ids),
        GhostStaff.replaced_by_staff_id.is_(None)  # Exclude replaced ghosts
    ).all()
    
    for a in all_assignments:
        if a.start_date:
            all_dates.append(a.start_date)
        if a.end_date:
            all_dates.append(a.end_date)
    
    for g in all_ghost_staff:
        if g.start_date:
            all_dates.append(g.start_date)
        if g.end_date:
            all_dates.append(g.end_date)
    
    if not all_dates:
        raise ValueError("No dates found for project or assignments")
    
    # Use provided dates or calculate from data
    report_start = start_date if start_date else min(all_dates)
    report_end = end_date if end_date else max(all_dates)
    
    # Normalize to first day of month for report_start and last day of month for report_end
    report_start = date(report_start.year, report_start.month, 1)
    # Move to first day of next month, then back one day
    next_month = report_end + relativedelta(months=1)
    report_end = date(next_month.year, next_month.month, 1) - timedelta(days=1)
    
    # Generate list of months in the report period
    months = []
    current_month = report_start
    while current_month <= report_end:
        months.append(current_month.strftime('%Y-%m'))
        current_month = current_month + relativedelta(months=1)
    
    # Initialize data structures
    monthly_breakdown = {m: {'internal_cost': 0, 'billable': 0, 'margin': 0, 'staff_count': 0, 'hours': 0} for m in months}
    roles_data = defaultdict(lambda: {
        'role_id': None,
        'role_name': None,
        'monthly_costs': {m: {'internal': 0, 'billable': 0, 'hours': 0} for m in months},
        'total_internal': 0,
        'total_billable': 0,
        'total_hours': 0
    })
    staff_entries = []
    
    # Helper function to calculate hours/costs for a month
    def calculate_monthly_data(entry_start, entry_end, hours_per_week, internal_rate, billable_rate, month_str):
        """Calculate hours and costs for a specific month"""
        month_date = datetime.strptime(month_str, '%Y-%m').date()
        month_start = date(month_date.year, month_date.month, 1)
        month_end = month_start + relativedelta(months=1) - timedelta(days=1)
        
        # Calculate overlap
        overlap_start = max(entry_start, month_start)
        overlap_end = min(entry_end, month_end)
        
        if overlap_start > overlap_end:
            return {'hours': 0, 'internal': 0, 'billable': 0}
        
        overlap_days = (overlap_end - overlap_start).days + 1
        weeks_in_overlap = overlap_days / 7.0
        hours = weeks_in_overlap * hours_per_week
        
        return {
            'hours': round(hours, 2),
            'internal': round(hours * internal_rate, 2),
            'billable': round(hours * (billable_rate or 0), 2)
        }
    
    # Process real staff assignments
    staff_in_month = {m: set() for m in months}
    
    for assignment in all_assignments:
        staff = assignment.staff_member
        project = assignment.project
        
        # Get billable rate
        rate_info = assignment.get_effective_billable_rate()
        billable_rate = rate_info['rate']
        internal_rate = staff.internal_hourly_cost
        
        # Determine role name (from assignment or staff)
        role_name = assignment.role_on_project or (staff.position_role.name if staff.position_role else 'Unassigned')
        role_id = staff.role_id
        
        # Update roles_data
        if roles_data[role_name]['role_id'] is None:
            roles_data[role_name]['role_id'] = role_id
            roles_data[role_name]['role_name'] = role_name
        
        # Build monthly data for this entry
        entry_monthly_data = {}
        
        for month in months:
            month_data = calculate_monthly_data(
                assignment.start_date,
                assignment.end_date,
                assignment.hours_per_week * (assignment.effective_allocation / 100.0),
                internal_rate,
                billable_rate,
                month
            )
            
            if month_data['hours'] > 0:
                entry_monthly_data[month] = month_data
                
                # Update monthly breakdown
                monthly_breakdown[month]['internal_cost'] += month_data['internal']
                monthly_breakdown[month]['billable'] += month_data['billable']
                monthly_breakdown[month]['hours'] += month_data['hours']
                staff_in_month[month].add(f"real_{assignment.staff_id}")
                
                # Update roles data
                roles_data[role_name]['monthly_costs'][month]['internal'] += month_data['internal']
                roles_data[role_name]['monthly_costs'][month]['billable'] += month_data['billable']
                roles_data[role_name]['monthly_costs'][month]['hours'] += month_data['hours']
                roles_data[role_name]['total_internal'] += month_data['internal']
                roles_data[role_name]['total_billable'] += month_data['billable']
                roles_data[role_name]['total_hours'] += month_data['hours']
        
        if entry_monthly_data:
            staff_entries.append({
                'id': assignment.id,
                'name': staff.name,
                'type': 'real',
                'role_id': role_id,
                'role_name': role_name,
                'project_id': project.id,
                'project_name': project.name,
                'start_date': assignment.start_date.isoformat(),
                'end_date': assignment.end_date.isoformat(),
                'hours_per_week': assignment.hours_per_week,
                'allocation_percentage': assignment.effective_allocation,
                'internal_hourly_cost': internal_rate,
                'billable_rate': billable_rate,
                'monthly_data': entry_monthly_data
            })
    
    # Process ghost staff
    for ghost in all_ghost_staff:
        role = ghost.role
        project = ghost.project
        
        role_name = role.name if role else 'Unassigned'
        role_id = ghost.role_id
        internal_rate = ghost.internal_hourly_cost
        billable_rate = ghost.billable_rate
        
        # Update roles_data
        if roles_data[role_name]['role_id'] is None:
            roles_data[role_name]['role_id'] = role_id
            roles_data[role_name]['role_name'] = role_name
        
        # Build monthly data for this entry
        entry_monthly_data = {}
        
        for month in months:
            month_data = calculate_monthly_data(
                ghost.start_date,
                ghost.end_date,
                ghost.hours_per_week,
                internal_rate,
                billable_rate,
                month
            )
            
            if month_data['hours'] > 0:
                entry_monthly_data[month] = month_data
                
                # Update monthly breakdown
                monthly_breakdown[month]['internal_cost'] += month_data['internal']
                monthly_breakdown[month]['billable'] += month_data['billable']
                monthly_breakdown[month]['hours'] += month_data['hours']
                staff_in_month[month].add(f"ghost_{ghost.id}")
                
                # Update roles data
                roles_data[role_name]['monthly_costs'][month]['internal'] += month_data['internal']
                roles_data[role_name]['monthly_costs'][month]['billable'] += month_data['billable']
                roles_data[role_name]['monthly_costs'][month]['hours'] += month_data['hours']
                roles_data[role_name]['total_internal'] += month_data['internal']
                roles_data[role_name]['total_billable'] += month_data['billable']
                roles_data[role_name]['total_hours'] += month_data['hours']
        
        if entry_monthly_data:
            staff_entries.append({
                'id': ghost.id,
                'name': ghost.name,
                'type': 'ghost',
                'role_id': role_id,
                'role_name': role_name,
                'project_id': project.id,
                'project_name': project.name,
                'start_date': ghost.start_date.isoformat(),
                'end_date': ghost.end_date.isoformat(),
                'hours_per_week': ghost.hours_per_week,
                'allocation_percentage': 100.0,
                'internal_hourly_cost': internal_rate,
                'billable_rate': billable_rate,
                'monthly_data': entry_monthly_data
            })
    
    # Calculate margins and staff counts for monthly breakdown
    for month in months:
        monthly_breakdown[month]['margin'] = monthly_breakdown[month]['billable'] - monthly_breakdown[month]['internal_cost']
        monthly_breakdown[month]['staff_count'] = len(staff_in_month[month])
        # Round values
        monthly_breakdown[month]['internal_cost'] = round(monthly_breakdown[month]['internal_cost'], 2)
        monthly_breakdown[month]['billable'] = round(monthly_breakdown[month]['billable'], 2)
        monthly_breakdown[month]['margin'] = round(monthly_breakdown[month]['margin'], 2)
        monthly_breakdown[month]['hours'] = round(monthly_breakdown[month]['hours'], 2)
    
    # Calculate summary totals
    total_internal_cost = sum(m['internal_cost'] for m in monthly_breakdown.values())
    total_billable = sum(m['billable'] for m in monthly_breakdown.values())
    total_margin = total_billable - total_internal_cost
    margin_percentage = (total_margin / total_billable * 100) if total_billable > 0 else 0
    
    # Count unique staff/ghosts
    all_staff_ids = set()
    all_ghost_ids = set()
    for entry in staff_entries:
        if entry['type'] == 'real':
            all_staff_ids.add(entry['id'])
        else:
            all_ghost_ids.add(entry['id'])
    
    # Convert roles_data to list and round values
    roles_list = []
    for role_name, role_data in roles_data.items():
        if role_data['total_hours'] > 0:  # Only include roles with actual data
            # Round monthly values
            for month in months:
                role_data['monthly_costs'][month]['internal'] = round(role_data['monthly_costs'][month]['internal'], 2)
                role_data['monthly_costs'][month]['billable'] = round(role_data['monthly_costs'][month]['billable'], 2)
                role_data['monthly_costs'][month]['hours'] = round(role_data['monthly_costs'][month]['hours'], 2)
            
            roles_list.append({
                'role_id': role_data['role_id'],
                'role_name': role_data['role_name'],
                'monthly_costs': role_data['monthly_costs'],
                'total_internal': round(role_data['total_internal'], 2),
                'total_billable': round(role_data['total_billable'], 2),
                'total_hours': round(role_data['total_hours'], 2)
            })
    
    # Sort roles by total cost descending
    roles_list.sort(key=lambda x: x['total_billable'], reverse=True)
    
    # Sort staff entries by start date
    staff_entries.sort(key=lambda x: x['start_date'])
    
    return {
        'project': {
            'id': project.id,
            'name': project.name,
            'is_folder': project.is_folder,
            'status': project.status
        },
        'sub_projects': sub_projects_data,
        'period': {
            'start_date': report_start.isoformat(),
            'end_date': report_end.isoformat(),
            'months': months
        },
        'summary': {
            'total_internal_cost': round(total_internal_cost, 2),
            'total_billable': round(total_billable, 2),
            'total_margin': round(total_margin, 2),
            'margin_percentage': round(margin_percentage, 1),
            'total_staff_count': len(all_staff_ids),
            'total_ghost_count': len(all_ghost_ids),
            'total_hours': round(sum(m['hours'] for m in monthly_breakdown.values()), 2)
        },
        'monthly_breakdown': monthly_breakdown,
        'roles': roles_list,
        'staff_entries': staff_entries
    }
