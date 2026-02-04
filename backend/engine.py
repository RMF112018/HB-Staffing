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


# =============================================================================
# STAFF AVAILABILITY FORECAST AND SUGGESTION FUNCTIONS
# =============================================================================

def get_staff_allocation_in_period(staff_id, period_start, period_end):
    """
    Calculate total allocation percentage for a staff member in a given period.
    
    Args:
        staff_id: ID of the staff member
        period_start, period_end: Date range to check
        
    Returns:
        dict: Allocation details including total percentage and assignment breakdown
    """
    db, Staff, Project, Assignment = get_models_and_db()
    
    # Get all assignments for this staff member that overlap with the period
    assignments = Assignment.query.filter(
        Assignment.staff_id == staff_id,
        Assignment.start_date <= period_end,
        Assignment.end_date >= period_start
    ).all()
    
    if not assignments:
        return {
            'total_allocation': 0,
            'raw_total_allocation': 0,  # Actual total (can exceed 100)
            'assignments': [],
            'available_allocation': 100.0
        }
    
    # Calculate weighted allocation for the period
    total_allocation = 0
    assignment_details = []
    
    for assignment in assignments:
        # Get allocation for the specific period
        allocation = assignment.get_allocation_for_period(period_start, period_end)
        total_allocation += allocation
        
        assignment_details.append({
            'assignment_id': assignment.id,
            'project_id': assignment.project_id,
            'project_name': assignment.project.name if assignment.project else None,
            'start_date': assignment.start_date.isoformat(),
            'end_date': assignment.end_date.isoformat(),
            'allocation_percentage': allocation,
            'role_on_project': assignment.role_on_project
        })
    
    return {
        'total_allocation': min(total_allocation, 100.0),  # Cap at 100 for display
        'raw_total_allocation': total_allocation,  # Actual total (can exceed 100)
        'assignments': assignment_details,
        'available_allocation': max(0, 100.0 - total_allocation)
    }


def get_staff_availability_forecast(role_id=None, start_date=None, end_date=None):
    """
    Get staff availability forecast for a given role and date range.
    Returns staff members whose current assignments end before or during the period,
    making them available for new assignments.
    
    Args:
        role_id: Optional role ID to filter staff by role
        start_date: Start of the period to check availability
        end_date: End of the period to check availability
        
    Returns:
        dict: Staff availability information including available, partially available, and unavailable staff
    """
    db, Staff, Project, Assignment = get_models_and_db()
    from models import Role
    
    # Default to next 90 days if no dates provided
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = start_date + timedelta(days=90)
    
    # Get staff members, filtered by role if specified
    query = Staff.query
    if role_id:
        query = query.filter(Staff.role_id == role_id)
    
    all_staff = query.all()
    
    available_staff = []
    partially_available_staff = []
    unavailable_staff = []
    
    for staff in all_staff:
        # Check staff availability dates
        if staff.availability_end and staff.availability_end < start_date:
            # Staff not available during this period
            unavailable_staff.append({
                'staff_id': staff.id,
                'name': staff.name,
                'role_id': staff.role_id,
                'role_name': staff.role,
                'reason': 'Staff availability ends before period',
                'availability_end': staff.availability_end.isoformat() if staff.availability_end else None
            })
            continue
        
        if staff.availability_start and staff.availability_start > end_date:
            # Staff not available during this period
            unavailable_staff.append({
                'staff_id': staff.id,
                'name': staff.name,
                'role_id': staff.role_id,
                'role_name': staff.role,
                'reason': 'Staff availability starts after period',
                'availability_start': staff.availability_start.isoformat() if staff.availability_start else None
            })
            continue
        
        # Get allocation info for this staff member
        allocation_info = get_staff_allocation_in_period(staff.id, start_date, end_date)
        
        # Determine staff's last assignment end date
        last_assignment_end = None
        if allocation_info['assignments']:
            last_assignment_end = max(a['end_date'] for a in allocation_info['assignments'])
        
        staff_info = {
            'staff_id': staff.id,
            'name': staff.name,
            'role_id': staff.role_id,
            'role_name': staff.role,
            'internal_hourly_cost': staff.internal_hourly_cost,
            'default_billable_rate': staff.default_billable_rate,
            'current_allocation': allocation_info['raw_total_allocation'],
            'available_allocation': allocation_info['available_allocation'],
            'current_assignments': allocation_info['assignments'],
            'last_assignment_end': last_assignment_end,
            'skills': staff.get_skills_list()
        }
        
        if allocation_info['raw_total_allocation'] == 0:
            # Fully available
            staff_info['availability_status'] = 'available'
            available_staff.append(staff_info)
        elif allocation_info['raw_total_allocation'] < 100:
            # Partially available
            staff_info['availability_status'] = 'partial'
            partially_available_staff.append(staff_info)
        else:
            # Fully allocated or over-allocated
            staff_info['availability_status'] = 'unavailable'
            staff_info['reason'] = 'Fully allocated during period'
            unavailable_staff.append(staff_info)
    
    # Get role info if role_id provided
    role_info = None
    if role_id:
        role = db.session.get(Role, role_id)
        if role:
            role_info = {
                'id': role.id,
                'name': role.name,
                'hourly_cost': role.hourly_cost,
                'default_billable_rate': role.default_billable_rate
            }
    
    return {
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'role': role_info,
        'available': available_staff,
        'partially_available': partially_available_staff,
        'unavailable': unavailable_staff,
        'summary': {
            'total_staff': len(all_staff),
            'available_count': len(available_staff),
            'partial_count': len(partially_available_staff),
            'unavailable_count': len(unavailable_staff)
        }
    }


def suggest_staff_for_role(role_id, start_date, end_date, allocation_percentage=100.0, max_suggestions=10):
    """
    Suggest staff members for a role based on availability and assignment end date alignment.
    Prioritizes staff whose current assignments end close to the role's start date.
    
    Args:
        role_id: ID of the role to fill
        start_date: Start date of the new role/assignment
        end_date: End date of the new role/assignment
        allocation_percentage: Required allocation percentage (default 100%)
        max_suggestions: Maximum number of suggestions to return
        
    Returns:
        dict: Suggested staff with match scores and reasons
    """
    db, Staff, Project, Assignment = get_models_and_db()
    from models import Role
    
    role = db.session.get(Role, role_id)
    if not role:
        raise ValueError("Role not found")
    
    # Get staff members with this role
    staff_with_role = Staff.query.filter(Staff.role_id == role_id).all()
    
    suggestions = []
    
    for staff in staff_with_role:
        # Check basic availability dates
        if staff.availability_end and staff.availability_end < start_date:
            continue
        if staff.availability_start and staff.availability_start > end_date:
            continue
        
        # Get current allocation
        allocation_info = get_staff_allocation_in_period(staff.id, start_date, end_date)
        
        # Check if staff has enough available allocation
        if allocation_info['available_allocation'] < allocation_percentage:
            continue
        
        # Calculate match score based on multiple factors
        match_score = 0
        match_reasons = []
        
        # Factor 1: Availability (40 points max)
        availability_score = (allocation_info['available_allocation'] / 100.0) * 40
        match_score += availability_score
        if allocation_info['available_allocation'] == 100:
            match_reasons.append('Fully available during period')
        else:
            match_reasons.append(f'{allocation_info["available_allocation"]:.0f}% available during period')
        
        # Factor 2: Assignment end date alignment (30 points max)
        # Staff whose assignments end just before the start date get higher scores
        alignment_score = 0
        if allocation_info['assignments']:
            # Find the assignment that ends closest to (but before) the start date
            relevant_end_dates = [
                datetime.fromisoformat(a['end_date']).date() 
                for a in allocation_info['assignments']
                if datetime.fromisoformat(a['end_date']).date() <= start_date
            ]
            
            if relevant_end_dates:
                closest_end = max(relevant_end_dates)
                days_gap = (start_date - closest_end).days
                
                if days_gap <= 0:
                    alignment_score = 30  # Perfect alignment
                    match_reasons.append('Assignment ends on role start date')
                elif days_gap <= 7:
                    alignment_score = 25
                    match_reasons.append(f'Assignment ends {days_gap} days before start')
                elif days_gap <= 14:
                    alignment_score = 20
                    match_reasons.append(f'Assignment ends {days_gap} days before start')
                elif days_gap <= 30:
                    alignment_score = 15
                    match_reasons.append(f'Assignment ends {days_gap} days before start')
                else:
                    alignment_score = 10
        else:
            # No current assignments - available immediately
            alignment_score = 25
            match_reasons.append('No current assignments')
        
        match_score += alignment_score
        
        # Factor 3: Experience with similar projects (20 points max)
        # Check if staff has worked on similar roles recently
        recent_assignments = Assignment.query.filter(
            Assignment.staff_id == staff.id,
            Assignment.end_date >= date.today() - timedelta(days=365)
        ).all()
        
        if recent_assignments:
            experience_score = min(len(recent_assignments) * 5, 20)
            match_score += experience_score
            match_reasons.append(f'{len(recent_assignments)} recent assignment(s)')
        
        # Factor 4: Skills match (10 points max) - placeholder for future enhancement
        skills_score = 10 if staff.get_skills_list() else 5
        match_score += skills_score
        
        suggestions.append({
            'staff_id': staff.id,
            'name': staff.name,
            'role_id': staff.role_id,
            'role_name': staff.role,
            'internal_hourly_cost': staff.internal_hourly_cost,
            'default_billable_rate': staff.default_billable_rate,
            'match_score': round(match_score, 1),
            'match_reasons': match_reasons,
            'current_allocation': allocation_info['raw_total_allocation'],
            'available_allocation': allocation_info['available_allocation'],
            'current_assignments': allocation_info['assignments'],
            'skills': staff.get_skills_list()
        })
    
    # Sort by match score descending
    suggestions.sort(key=lambda x: x['match_score'], reverse=True)
    
    return {
        'role': {
            'id': role.id,
            'name': role.name,
            'hourly_cost': role.hourly_cost,
            'default_billable_rate': role.default_billable_rate
        },
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'required_allocation': allocation_percentage,
        'suggestions': suggestions[:max_suggestions],
        'total_candidates': len(staff_with_role),
        'qualified_candidates': len(suggestions)
    }


def flag_new_hire_needs(role_id, start_date, end_date, required_count=1, allocation_percentage=100.0):
    """
    Identify when no staff are available for a role, flagging the need for new hires.
    
    Args:
        role_id: ID of the role to check
        start_date: Start date of the requirement
        end_date: End date of the requirement
        required_count: Number of staff needed for this role
        allocation_percentage: Required allocation percentage per person
        
    Returns:
        dict: New hire needs analysis including gap count and recommendations
    """
    db, Staff, Project, Assignment = get_models_and_db()
    from models import Role
    
    role = db.session.get(Role, role_id)
    if not role:
        raise ValueError("Role not found")
    
    # Get suggestions for this role
    suggestions = suggest_staff_for_role(role_id, start_date, end_date, allocation_percentage)
    
    # Count how many qualified candidates we have
    qualified_count = len([s for s in suggestions['suggestions'] if s['available_allocation'] >= allocation_percentage])
    
    # Calculate the gap
    gap = required_count - qualified_count
    needs_new_hire = gap > 0
    
    # Calculate estimated cost impact
    duration_weeks = (end_date - start_date).days / 7.0
    hours_per_person = duration_weeks * 40 * (allocation_percentage / 100.0)
    
    estimated_internal_cost = hours_per_person * role.hourly_cost * max(gap, 0)
    estimated_billable = hours_per_person * (role.default_billable_rate or role.hourly_cost) * max(gap, 0)
    
    return {
        'role': {
            'id': role.id,
            'name': role.name,
            'hourly_cost': role.hourly_cost,
            'default_billable_rate': role.default_billable_rate
        },
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'duration_weeks': round(duration_weeks, 1)
        },
        'requirement': {
            'required_count': required_count,
            'allocation_percentage': allocation_percentage
        },
        'availability': {
            'total_staff_with_role': suggestions['total_candidates'],
            'qualified_available': qualified_count,
            'gap': max(gap, 0)
        },
        'needs_new_hire': needs_new_hire,
        'new_hire_count': max(gap, 0),
        'existing_suggestions': suggestions['suggestions'],
        'estimated_impact': {
            'hours_per_person': round(hours_per_person, 1),
            'internal_cost_for_gap': round(estimated_internal_cost, 2),
            'billable_for_gap': round(estimated_billable, 2)
        },
        'recommendations': _generate_hire_recommendations(role, gap, suggestions['suggestions'], start_date)
    }


def _generate_hire_recommendations(role, gap, available_suggestions, start_date):
    """
    Generate recommendations for addressing staffing gaps.
    
    Args:
        role: Role object
        gap: Number of additional staff needed
        available_suggestions: List of available staff suggestions
        start_date: Start date of the requirement
        
    Returns:
        list: Recommendations for addressing the gap
    """
    recommendations = []
    
    if gap > 0:
        # Calculate lead time for hiring
        days_until_start = (start_date - date.today()).days
        
        recommendations.append({
            'type': 'new_hire',
            'priority': 'high' if days_until_start < 60 else 'medium',
            'message': f'Hire {gap} new {role.name}(s) to fill the staffing gap',
            'details': f'Position(s) needed by {start_date.isoformat()}. Allow 4-8 weeks for recruiting and onboarding.'
        })
        
        if days_until_start < 30:
            recommendations.append({
                'type': 'contractor',
                'priority': 'high',
                'message': f'Consider temporary contractors while recruiting permanent staff',
                'details': 'Short timeline may require interim staffing solution.'
            })
        
        # Check if partial allocations could help
        partial_capacity = sum(s['available_allocation'] for s in available_suggestions if s['available_allocation'] > 0)
        if partial_capacity >= 50:
            recommendations.append({
                'type': 'reallocation',
                'priority': 'medium',
                'message': 'Consider splitting requirements across partially available staff',
                'details': f'Combined available capacity: {partial_capacity:.0f}%'
            })
    
    elif available_suggestions:
        recommendations.append({
            'type': 'assign',
            'priority': 'low',
            'message': 'Sufficient staff available - proceed with assignment',
            'details': f'{len(available_suggestions)} qualified candidate(s) available'
        })
    
    return recommendations


# =============================================================================
# OVER-ALLOCATION DETECTION AND VALIDATION FUNCTIONS
# =============================================================================

def get_staff_allocation_timeline(staff_id, start_date, end_date):
    """
    Get a detailed monthly allocation breakdown for a staff member.
    
    Args:
        staff_id: ID of the staff member
        start_date: Start of period
        end_date: End of period
        
    Returns:
        dict: Monthly allocation breakdown with project details
    """
    from dateutil.relativedelta import relativedelta
    db, Staff, Project, Assignment = get_models_and_db()
    
    staff = db.session.get(Staff, staff_id)
    if not staff:
        raise ValueError("Staff member not found")
    
    # Get all assignments for this staff member that overlap with the period
    assignments = Assignment.query.filter(
        Assignment.staff_id == staff_id,
        Assignment.start_date <= end_date,
        Assignment.end_date >= start_date
    ).all()
    
    # Generate monthly breakdown
    monthly_allocations = {}
    current_month = date(start_date.year, start_date.month, 1)
    
    while current_month <= end_date:
        month_key = current_month.strftime('%Y-%m')
        month_end = current_month + relativedelta(months=1) - timedelta(days=1)
        
        month_data = {
            'month': month_key,
            'total_allocation': 0,
            'is_over_allocated': False,
            'assignments': []
        }
        
        for assignment in assignments:
            # Check if assignment overlaps with this month
            overlap_days = calculate_date_range_overlap(
                assignment.start_date, assignment.end_date,
                current_month, month_end
            )
            
            if overlap_days > 0:
                # Get allocation for this specific month
                allocation = assignment.get_allocation_for_period(current_month, month_end)
                month_data['total_allocation'] += allocation
                
                month_data['assignments'].append({
                    'assignment_id': assignment.id,
                    'project_id': assignment.project_id,
                    'project_name': assignment.project.name if assignment.project else None,
                    'role_on_project': assignment.role_on_project,
                    'allocation_percentage': allocation,
                    'overlap_days': overlap_days
                })
        
        month_data['is_over_allocated'] = month_data['total_allocation'] > 100
        month_data['available_allocation'] = max(0, 100 - month_data['total_allocation'])
        monthly_allocations[month_key] = month_data
        
        current_month = current_month + relativedelta(months=1)
    
    return {
        'staff_id': staff_id,
        'staff_name': staff.name,
        'role': staff.role,
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'monthly_allocations': monthly_allocations
    }


def detect_over_allocations(staff_id, start_date, end_date):
    """
    Detect periods where a staff member's cumulative allocation exceeds 100%.
    
    Args:
        staff_id: ID of the staff member
        start_date: Start of period to check
        end_date: End of period to check
        
    Returns:
        dict: Over-allocation details including specific periods and severity
    """
    db, Staff, Project, Assignment = get_models_and_db()
    
    staff = db.session.get(Staff, staff_id)
    if not staff:
        raise ValueError("Staff member not found")
    
    # Get timeline
    timeline = get_staff_allocation_timeline(staff_id, start_date, end_date)
    
    # Find over-allocated periods
    over_allocated_periods = []
    
    for month_key, month_data in timeline['monthly_allocations'].items():
        if month_data['is_over_allocated']:
            over_allocation_amount = month_data['total_allocation'] - 100
            
            over_allocated_periods.append({
                'month': month_key,
                'total_allocation': month_data['total_allocation'],
                'over_allocation_amount': round(over_allocation_amount, 1),
                'severity': 'critical' if over_allocation_amount > 50 else ('high' if over_allocation_amount > 25 else 'moderate'),
                'conflicting_assignments': month_data['assignments']
            })
    
    has_conflicts = len(over_allocated_periods) > 0
    
    # Calculate overall severity
    if not has_conflicts:
        overall_severity = 'none'
    else:
        max_over_allocation = max(p['over_allocation_amount'] for p in over_allocated_periods)
        if max_over_allocation > 50:
            overall_severity = 'critical'
        elif max_over_allocation > 25:
            overall_severity = 'high'
        else:
            overall_severity = 'moderate'
    
    return {
        'staff_id': staff_id,
        'staff_name': staff.name,
        'role': staff.role,
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'has_conflicts': has_conflicts,
        'overall_severity': overall_severity,
        'over_allocated_periods': over_allocated_periods,
        'conflict_count': len(over_allocated_periods),
        'timeline': timeline['monthly_allocations']
    }


def validate_assignment_allocation(staff_id, new_start_date, new_end_date, new_allocation_percentage,
                                   exclude_assignment_id=None):
    """
    Pre-validate a new or modified assignment to check for over-allocation.
    
    Args:
        staff_id: ID of the staff member
        new_start_date: Start date of the proposed assignment
        new_end_date: End date of the proposed assignment
        new_allocation_percentage: Proposed allocation percentage
        exclude_assignment_id: Assignment ID to exclude (for updates)
        
    Returns:
        dict: Validation result with any conflicts detected
    """
    from dateutil.relativedelta import relativedelta
    db, Staff, Project, Assignment = get_models_and_db()
    
    staff = db.session.get(Staff, staff_id)
    if not staff:
        raise ValueError("Staff member not found")
    
    # Parse dates if strings
    if isinstance(new_start_date, str):
        new_start_date = datetime.fromisoformat(new_start_date).date()
    if isinstance(new_end_date, str):
        new_end_date = datetime.fromisoformat(new_end_date).date()
    
    # Get existing assignments for this staff member that overlap with the new period
    query = Assignment.query.filter(
        Assignment.staff_id == staff_id,
        Assignment.start_date <= new_end_date,
        Assignment.end_date >= new_start_date
    )
    
    if exclude_assignment_id:
        query = query.filter(Assignment.id != exclude_assignment_id)
    
    existing_assignments = query.all()
    
    # Check each month in the new assignment period
    conflicts = []
    current_month = date(new_start_date.year, new_start_date.month, 1)
    
    while current_month <= new_end_date:
        month_key = current_month.strftime('%Y-%m')
        month_end = current_month + relativedelta(months=1) - timedelta(days=1)
        
        # Calculate existing allocation for this month
        existing_allocation = 0
        month_assignments = []
        
        for assignment in existing_assignments:
            overlap_days = calculate_date_range_overlap(
                assignment.start_date, assignment.end_date,
                current_month, month_end
            )
            
            if overlap_days > 0:
                allocation = assignment.get_allocation_for_period(current_month, month_end)
                existing_allocation += allocation
                month_assignments.append({
                    'assignment_id': assignment.id,
                    'project_name': assignment.project.name if assignment.project else None,
                    'allocation_percentage': allocation
                })
        
        # Check if adding new assignment would exceed 100%
        projected_total = existing_allocation + new_allocation_percentage
        
        if projected_total > 100:
            conflicts.append({
                'month': month_key,
                'existing_allocation': round(existing_allocation, 1),
                'new_allocation': new_allocation_percentage,
                'projected_total': round(projected_total, 1),
                'over_allocation_amount': round(projected_total - 100, 1),
                'existing_assignments': month_assignments
            })
        
        current_month = current_month + relativedelta(months=1)
    
    is_valid = len(conflicts) == 0
    
    return {
        'is_valid': is_valid,
        'staff_id': staff_id,
        'staff_name': staff.name,
        'proposed_assignment': {
            'start_date': new_start_date.isoformat(),
            'end_date': new_end_date.isoformat(),
            'allocation_percentage': new_allocation_percentage
        },
        'conflicts': conflicts,
        'conflict_count': len(conflicts),
        'can_override': True,  # Always allow override with warning
        'message': 'Assignment would cause over-allocation' if conflicts else 'Assignment is valid'
    }


def get_organization_over_allocations(start_date, end_date):
    """
    Get all over-allocation conflicts across the organization.
    
    Args:
        start_date: Start of period to check
        end_date: End of period to check
        
    Returns:
        dict: Organization-wide over-allocation summary
    """
    db, Staff, Project, Assignment = get_models_and_db()
    
    all_staff = Staff.query.all()
    
    staff_with_conflicts = []
    staff_without_conflicts = []
    
    for staff in all_staff:
        conflicts = detect_over_allocations(staff.id, start_date, end_date)
        
        if conflicts['has_conflicts']:
            staff_with_conflicts.append({
                'staff_id': staff.id,
                'staff_name': staff.name,
                'role': staff.role,
                'severity': conflicts['overall_severity'],
                'conflict_count': conflicts['conflict_count'],
                'over_allocated_periods': conflicts['over_allocated_periods']
            })
        else:
            staff_without_conflicts.append({
                'staff_id': staff.id,
                'staff_name': staff.name,
                'role': staff.role
            })
    
    # Sort by severity
    severity_order = {'critical': 0, 'high': 1, 'moderate': 2}
    staff_with_conflicts.sort(key=lambda x: severity_order.get(x['severity'], 3))
    
    return {
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'summary': {
            'total_staff': len(all_staff),
            'staff_with_conflicts': len(staff_with_conflicts),
            'staff_without_conflicts': len(staff_without_conflicts),
            'critical_count': len([s for s in staff_with_conflicts if s['severity'] == 'critical']),
            'high_count': len([s for s in staff_with_conflicts if s['severity'] == 'high']),
            'moderate_count': len([s for s in staff_with_conflicts if s['severity'] == 'moderate'])
        },
        'conflicts': staff_with_conflicts,
        'clear_staff': staff_without_conflicts
    }


# =============================================================================
# PLANNING EXERCISE FUNCTIONS
# =============================================================================

def get_planning_models():
    """Import planning models"""
    from models import PlanningExercise, PlanningProject, PlanningRole, Role, Staff
    from db import db
    return db, PlanningExercise, PlanningProject, PlanningRole, Role, Staff


def generate_coverage_analysis(exercise_id):
    """
    Generate a monthly breakdown of role requirements across all projects in a planning exercise.
    
    Args:
        exercise_id: ID of the planning exercise
        
    Returns:
        dict: Monthly coverage analysis with role requirements
    """
    from dateutil.relativedelta import relativedelta
    db, PlanningExercise, PlanningProject, PlanningRole, Role, Staff = get_planning_models()
    
    exercise = db.session.get(PlanningExercise, exercise_id)
    if not exercise:
        raise ValueError("Planning exercise not found")
    
    if not exercise.planning_projects:
        return {
            'exercise_id': exercise_id,
            'exercise_name': exercise.name,
            'error': 'No projects in this planning exercise'
        }
    
    # Determine date range across all projects
    all_dates = []
    for project in exercise.planning_projects:
        if project.start_date:
            all_dates.append(project.start_date)
        if project.calculated_end_date:
            all_dates.append(project.calculated_end_date)
        
        # Also consider role offsets
        for planning_role in project.planning_roles:
            if planning_role.calculated_start_date:
                all_dates.append(planning_role.calculated_start_date)
            if planning_role.calculated_end_date:
                all_dates.append(planning_role.calculated_end_date)
    
    if not all_dates:
        raise ValueError("No dates found in planning exercise")
    
    start_date = min(all_dates)
    end_date = max(all_dates)
    
    # Normalize to first day of months
    start_date = date(start_date.year, start_date.month, 1)
    end_date = date(end_date.year, end_date.month, 1) + relativedelta(months=1) - timedelta(days=1)
    
    # Generate list of months
    months = []
    current_month = start_date
    while current_month <= end_date:
        months.append(current_month.strftime('%Y-%m'))
        current_month = current_month + relativedelta(months=1)
    
    # Initialize role coverage tracking
    role_coverage = defaultdict(lambda: {
        'role_id': None,
        'role_name': None,
        'role_hourly_cost': None,
        'role_default_billable_rate': None,
        'monthly_requirements': {m: {'count': 0, 'allocation_total': 0, 'projects': []} for m in months},
        'total_fte': 0  # Full-time equivalent across all months
    })
    
    # Process each project and its roles
    for project in exercise.planning_projects:
        for planning_role in project.planning_roles:
            role = planning_role.role
            if not role:
                continue
            
            role_name = role.name
            
            # Initialize role data if needed
            if role_coverage[role_name]['role_id'] is None:
                role_coverage[role_name]['role_id'] = role.id
                role_coverage[role_name]['role_name'] = role_name
                role_coverage[role_name]['role_hourly_cost'] = role.hourly_cost
                role_coverage[role_name]['role_default_billable_rate'] = role.default_billable_rate
            
            # Calculate which months this role is active
            role_start = planning_role.calculated_start_date
            role_end = planning_role.calculated_end_date
            
            if not role_start or not role_end:
                continue
            
            for month_str in months:
                month_date = datetime.strptime(month_str, '%Y-%m').date()
                month_start = date(month_date.year, month_date.month, 1)
                month_end = month_start + relativedelta(months=1) - timedelta(days=1)
                
                # Check if role overlaps with this month
                if role_start <= month_end and role_end >= month_start:
                    # Add this role's requirement to the month
                    allocation_contribution = planning_role.count * (planning_role.allocation_percentage / 100.0)
                    
                    role_coverage[role_name]['monthly_requirements'][month_str]['count'] += planning_role.count
                    role_coverage[role_name]['monthly_requirements'][month_str]['allocation_total'] += allocation_contribution
                    role_coverage[role_name]['monthly_requirements'][month_str]['projects'].append({
                        'project_id': project.id,
                        'project_name': project.name,
                        'count': planning_role.count,
                        'allocation_percentage': planning_role.allocation_percentage,
                        'overlap_mode': planning_role.overlap_mode
                    })
    
    # Calculate total FTE for each role
    for role_name, role_data in role_coverage.items():
        total_fte_months = 0
        for month_str, month_data in role_data['monthly_requirements'].items():
            total_fte_months += month_data['allocation_total']
        role_data['total_fte'] = round(total_fte_months / len(months), 2) if months else 0
    
    # Convert to list and sort by role name
    roles_list = []
    for role_name, role_data in role_coverage.items():
        roles_list.append({
            'role_id': role_data['role_id'],
            'role_name': role_data['role_name'],
            'role_hourly_cost': role_data['role_hourly_cost'],
            'role_default_billable_rate': role_data['role_default_billable_rate'],
            'monthly_requirements': role_data['monthly_requirements'],
            'total_fte': role_data['total_fte']
        })
    
    roles_list.sort(key=lambda x: x['role_name'])
    
    return {
        'exercise_id': exercise_id,
        'exercise_name': exercise.name,
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'months': months,
            'total_months': len(months)
        },
        'projects': [p.to_dict(include_roles=False) for p in exercise.planning_projects],
        'role_coverage': roles_list
    }


def calculate_minimum_staff_per_role(exercise_id, overlap_mode='efficient'):
    """
    Calculate the minimum number of staff needed per role to cover all projects.
    
    Args:
        exercise_id: ID of the planning exercise
        overlap_mode: 'efficient' (share staff across projects) or 'conservative' (dedicated staff per project)
        
    Returns:
        dict: Minimum staff requirements per role with analysis
    """
    from dateutil.relativedelta import relativedelta
    db, PlanningExercise, PlanningProject, PlanningRole, Role, Staff = get_planning_models()
    
    # Get coverage analysis first
    coverage = generate_coverage_analysis(exercise_id)
    
    if 'error' in coverage:
        return coverage
    
    minimum_staff = []
    
    for role_data in coverage['role_coverage']:
        role_id = role_data['role_id']
        role_name = role_data['role_name']
        
        # Calculate peak requirement
        peak_count = 0
        peak_month = None
        peak_allocation = 0
        
        for month_str, month_data in role_data['monthly_requirements'].items():
            if overlap_mode == 'conservative':
                # Conservative: sum of all role counts across projects
                month_requirement = month_data['count']
            else:
                # Efficient: based on allocation total (allows sharing)
                month_requirement = month_data['allocation_total']
            
            if month_requirement > peak_allocation:
                peak_allocation = month_requirement
                peak_count = month_data['count']
                peak_month = month_str
        
        # Determine minimum staff needed
        if overlap_mode == 'conservative':
            min_staff_needed = peak_count
        else:
            # Efficient mode: round up allocation to get minimum staff
            import math
            min_staff_needed = math.ceil(peak_allocation)
        
        # Get staff suggestions for this role
        suggestions = []
        if role_id and peak_month:
            try:
                # Parse peak month to get date range
                peak_date = datetime.strptime(peak_month, '%Y-%m').date()
                peak_start = date(peak_date.year, peak_date.month, 1)
                peak_end = peak_start + relativedelta(months=1) - timedelta(days=1)
                
                suggestion_result = suggest_staff_for_role(
                    role_id=role_id,
                    start_date=peak_start,
                    end_date=peak_end,
                    allocation_percentage=100.0,
                    max_suggestions=5
                )
                suggestions = suggestion_result.get('suggestions', [])
            except (ValueError, Exception):
                pass
        
        # Determine if new hires are needed
        available_staff_count = len(suggestions)
        new_hires_needed = max(0, min_staff_needed - available_staff_count)
        
        minimum_staff.append({
            'role_id': role_id,
            'role_name': role_name,
            'role_hourly_cost': role_data['role_hourly_cost'],
            'role_default_billable_rate': role_data['role_default_billable_rate'],
            'minimum_staff_needed': min_staff_needed,
            'peak_month': peak_month,
            'peak_count': peak_count,
            'peak_allocation': round(peak_allocation, 2),
            'available_staff_count': available_staff_count,
            'new_hires_needed': new_hires_needed,
            'staff_suggestions': suggestions[:5],
            'average_fte': role_data['total_fte']
        })
    
    # Sort by new hires needed descending
    minimum_staff.sort(key=lambda x: x['new_hires_needed'], reverse=True)
    
    return {
        'exercise_id': exercise_id,
        'exercise_name': coverage['exercise_name'],
        'overlap_mode': overlap_mode,
        'period': coverage['period'],
        'staff_requirements': minimum_staff,
        'summary': {
            'total_roles': len(minimum_staff),
            'total_minimum_staff': sum(r['minimum_staff_needed'] for r in minimum_staff),
            'total_available': sum(r['available_staff_count'] for r in minimum_staff),
            'total_new_hires_needed': sum(r['new_hires_needed'] for r in minimum_staff)
        }
    }


def calculate_planning_costs(exercise_id):
    """
    Calculate total costs and margins for a planning exercise.
    
    Args:
        exercise_id: ID of the planning exercise
        
    Returns:
        dict: Cost breakdown with internal costs, billable amounts, and margins
    """
    from dateutil.relativedelta import relativedelta
    db, PlanningExercise, PlanningProject, PlanningRole, Role, Staff = get_planning_models()
    
    exercise = db.session.get(PlanningExercise, exercise_id)
    if not exercise:
        raise ValueError("Planning exercise not found")
    
    # Get coverage analysis for monthly breakdown
    coverage = generate_coverage_analysis(exercise_id)
    
    if 'error' in coverage:
        return coverage
    
    months = coverage['period']['months']
    
    # Calculate costs by role and by month
    monthly_costs = {m: {'internal_cost': 0, 'billable': 0, 'margin': 0, 'hours': 0} for m in months}
    role_costs = []
    
    for role_data in coverage['role_coverage']:
        role_name = role_data['role_name']
        hourly_cost = role_data['role_hourly_cost'] or 0
        billable_rate = role_data['role_default_billable_rate'] or hourly_cost
        
        role_total_internal = 0
        role_total_billable = 0
        role_total_hours = 0
        role_monthly = {}
        
        for month_str, month_data in role_data['monthly_requirements'].items():
            # Calculate hours: allocation_total * 40 hrs/week * 4.33 weeks/month
            allocation = month_data['allocation_total']
            month_hours = allocation * 40 * 4.33
            
            month_internal = month_hours * hourly_cost
            month_billable = month_hours * billable_rate
            
            role_monthly[month_str] = {
                'hours': round(month_hours, 1),
                'internal_cost': round(month_internal, 2),
                'billable': round(month_billable, 2),
                'margin': round(month_billable - month_internal, 2)
            }
            
            role_total_internal += month_internal
            role_total_billable += month_billable
            role_total_hours += month_hours
            
            # Add to monthly totals
            monthly_costs[month_str]['internal_cost'] += month_internal
            monthly_costs[month_str]['billable'] += month_billable
            monthly_costs[month_str]['hours'] += month_hours
        
        role_costs.append({
            'role_id': role_data['role_id'],
            'role_name': role_name,
            'hourly_cost': hourly_cost,
            'billable_rate': billable_rate,
            'total_hours': round(role_total_hours, 1),
            'total_internal_cost': round(role_total_internal, 2),
            'total_billable': round(role_total_billable, 2),
            'total_margin': round(role_total_billable - role_total_internal, 2),
            'margin_percentage': round(((role_total_billable - role_total_internal) / role_total_billable * 100) if role_total_billable > 0 else 0, 1),
            'monthly_costs': role_monthly
        })
    
    # Calculate margins for monthly totals
    for month_str in months:
        monthly_costs[month_str]['margin'] = monthly_costs[month_str]['billable'] - monthly_costs[month_str]['internal_cost']
        monthly_costs[month_str]['internal_cost'] = round(monthly_costs[month_str]['internal_cost'], 2)
        monthly_costs[month_str]['billable'] = round(monthly_costs[month_str]['billable'], 2)
        monthly_costs[month_str]['margin'] = round(monthly_costs[month_str]['margin'], 2)
        monthly_costs[month_str]['hours'] = round(monthly_costs[month_str]['hours'], 1)
    
    # Calculate grand totals
    total_internal = sum(m['internal_cost'] for m in monthly_costs.values())
    total_billable = sum(m['billable'] for m in monthly_costs.values())
    total_hours = sum(m['hours'] for m in monthly_costs.values())
    total_margin = total_billable - total_internal
    margin_percentage = (total_margin / total_billable * 100) if total_billable > 0 else 0
    
    # Calculate by project
    project_costs = []
    for project in exercise.planning_projects:
        project_internal = 0
        project_billable = 0
        project_hours = 0
        
        for planning_role in project.planning_roles:
            role = planning_role.role
            if not role:
                continue
            
            hourly_cost = role.hourly_cost or 0
            billable_rate = role.default_billable_rate or hourly_cost
            
            # Calculate hours for this role in this project
            duration_months = planning_role.duration_months or 0
            role_hours = planning_role.count * (planning_role.allocation_percentage / 100.0) * planning_role.hours_per_week * 4.33 * duration_months
            
            project_internal += role_hours * hourly_cost
            project_billable += role_hours * billable_rate
            project_hours += role_hours
        
        project_margin = project_billable - project_internal
        
        project_costs.append({
            'project_id': project.id,
            'project_name': project.name,
            'start_date': project.start_date.isoformat() if project.start_date else None,
            'end_date': project.calculated_end_date.isoformat() if project.calculated_end_date else None,
            'duration_months': project.duration_months,
            'total_hours': round(project_hours, 1),
            'total_internal_cost': round(project_internal, 2),
            'total_billable': round(project_billable, 2),
            'total_margin': round(project_margin, 2),
            'margin_percentage': round((project_margin / project_billable * 100) if project_billable > 0 else 0, 1),
            'budget': project.budget,
            'budget_variance': round(project.budget - project_billable, 2) if project.budget else None
        })
    
    # Sort role costs by total billable descending
    role_costs.sort(key=lambda x: x['total_billable'], reverse=True)
    
    return {
        'exercise_id': exercise_id,
        'exercise_name': exercise.name,
        'period': coverage['period'],
        'summary': {
            'total_hours': round(total_hours, 1),
            'total_internal_cost': round(total_internal, 2),
            'total_billable': round(total_billable, 2),
            'total_margin': round(total_margin, 2),
            'margin_percentage': round(margin_percentage, 1)
        },
        'monthly_costs': monthly_costs,
        'role_costs': role_costs,
        'project_costs': project_costs
    }


def apply_planning_exercise(exercise_id, create_real_projects=True):
    """
    Apply a planning exercise by creating real projects and ghost staff.
    
    Args:
        exercise_id: ID of the planning exercise
        create_real_projects: If True, create actual projects. If False, only return preview.
        
    Returns:
        dict: Created projects and ghost staff, or preview data
    """
    from models import GhostStaff, ProjectRoleRate
    db, PlanningExercise, PlanningProject, PlanningRole, Role, Staff = get_planning_models()
    _, _, Project, _ = get_models_and_db()
    
    exercise = db.session.get(PlanningExercise, exercise_id)
    if not exercise:
        raise ValueError("Planning exercise not found")
    
    if not exercise.planning_projects:
        raise ValueError("No projects in this planning exercise")
    
    created_projects = []
    created_ghost_staff = []
    
    for planning_project in exercise.planning_projects:
        # Create the project
        project_data = {
            'name': planning_project.name,
            'start_date': planning_project.start_date,
            'end_date': planning_project.calculated_end_date,
            'status': 'planning',
            'budget': planning_project.budget,
            'location': planning_project.location
        }
        
        if create_real_projects:
            project = Project(
                name=planning_project.name,
                start_date=planning_project.start_date,
                end_date=planning_project.calculated_end_date,
                status='planning',
                budget=planning_project.budget,
                location=planning_project.location
            )
            db.session.add(project)
            db.session.flush()  # Get the project ID
            
            # Create role rates from default rates
            for planning_role in planning_project.planning_roles:
                role = planning_role.role
                if role and role.default_billable_rate:
                    rate = ProjectRoleRate(
                        project_id=project.id,
                        role_id=role.id,
                        billable_rate=role.default_billable_rate
                    )
                    db.session.add(rate)
            
            # Create ghost staff for each role
            ghost_staff_for_project = []
            for planning_role in planning_project.planning_roles:
                role = planning_role.role
                if not role:
                    continue
                
                # Get billable rate
                billable_rate = role.default_billable_rate or role.hourly_cost
                
                # Create ghost staff for each count
                for i in range(planning_role.count):
                    ghost_name = f"{role.name} Placeholder {i + 1}"
                    
                    ghost = GhostStaff(
                        project_id=project.id,
                        role_id=role.id,
                        name=ghost_name,
                        internal_hourly_cost=role.hourly_cost,
                        billable_rate=billable_rate,
                        start_date=planning_role.calculated_start_date,
                        end_date=planning_role.calculated_end_date,
                        hours_per_week=planning_role.hours_per_week * (planning_role.allocation_percentage / 100.0)
                    )
                    db.session.add(ghost)
                    ghost_staff_for_project.append({
                        'name': ghost_name,
                        'role_name': role.name,
                        'start_date': planning_role.calculated_start_date.isoformat() if planning_role.calculated_start_date else None,
                        'end_date': planning_role.calculated_end_date.isoformat() if planning_role.calculated_end_date else None
                    })
            
            created_projects.append({
                'project_id': project.id,
                'name': project.name,
                'start_date': project.start_date.isoformat() if project.start_date else None,
                'end_date': project.end_date.isoformat() if project.end_date else None,
                'ghost_staff_count': len(ghost_staff_for_project),
                'ghost_staff': ghost_staff_for_project
            })
            
            created_ghost_staff.extend(ghost_staff_for_project)
        else:
            # Preview mode - just return what would be created
            ghost_staff_preview = []
            for planning_role in planning_project.planning_roles:
                role = planning_role.role
                if not role:
                    continue
                
                for i in range(planning_role.count):
                    ghost_staff_preview.append({
                        'name': f"{role.name} Placeholder {i + 1}",
                        'role_name': role.name,
                        'start_date': planning_role.calculated_start_date.isoformat() if planning_role.calculated_start_date else None,
                        'end_date': planning_role.calculated_end_date.isoformat() if planning_role.calculated_end_date else None
                    })
            
            created_projects.append({
                'name': planning_project.name,
                'start_date': planning_project.start_date.isoformat() if planning_project.start_date else None,
                'end_date': planning_project.calculated_end_date.isoformat() if planning_project.calculated_end_date else None,
                'ghost_staff_count': len(ghost_staff_preview),
                'ghost_staff': ghost_staff_preview
            })
            
            created_ghost_staff.extend(ghost_staff_preview)
    
    if create_real_projects:
        # Update exercise status
        exercise.status = 'completed'
        db.session.commit()
    
    return {
        'exercise_id': exercise_id,
        'exercise_name': exercise.name,
        'mode': 'created' if create_real_projects else 'preview',
        'projects_created': len(created_projects),
        'ghost_staff_created': len(created_ghost_staff),
        'projects': created_projects,
        'summary': {
            'total_projects': len(created_projects),
            'total_ghost_staff': len(created_ghost_staff)
        }
    }
