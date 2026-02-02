from models import Staff, Project, Assignment, User, Role, ProjectRoleRate, AssignmentMonthlyAllocation, ProjectTemplate, TemplateRole, GhostStaff
import json

def init_db():
    """Initialize the database and create all tables"""
    # Import all models to ensure they are registered with SQLAlchemy
    from models import Staff, Project, Assignment, User, Role, AssignmentMonthlyAllocation
    from models import db
    db.create_all()
    print("Database initialized successfully")

def seed_database():
    """Seed the database with sample data for development/testing"""
    from models import db

    # Check if data already exists
    if Staff.query.first():
        print("Database already seeded")
        return

    # Create default roles first - 18 standard project roles
    # default_billable_rate is set to approximately 25% above hourly_cost (internal cost)
    roles_data = [
        {
            'name': 'Project Executive',
            'description': 'Executive oversight of major projects and client relationships',
            'hourly_cost': 150.0,
            'default_billable_rate': 195.0
        },
        {
            'name': 'Senior Project Manager',
            'description': 'Senior-level project management with complex project oversight',
            'hourly_cost': 120.0,
            'default_billable_rate': 155.0
        },
        {
            'name': 'Project Manager - Level 3',
            'description': 'Experienced project manager handling large-scale projects',
            'hourly_cost': 100.0,
            'default_billable_rate': 130.0
        },
        {
            'name': 'Project Manager - Level 2',
            'description': 'Mid-level project manager with proven track record',
            'hourly_cost': 85.0,
            'default_billable_rate': 110.0
        },
        {
            'name': 'Project Manager - Level 1',
            'description': 'Entry-level project manager developing core skills',
            'hourly_cost': 70.0,
            'default_billable_rate': 90.0
        },
        {
            'name': 'Project Administrator',
            'description': 'Administrative support for project documentation and coordination',
            'hourly_cost': 50.0,
            'default_billable_rate': 65.0
        },
        {
            'name': 'Project Accountant',
            'description': 'Financial tracking, billing, and cost management for projects',
            'hourly_cost': 65.0,
            'default_billable_rate': 85.0
        },
        {
            'name': 'Assistant Project Manager',
            'description': 'Supports project managers with day-to-day project tasks',
            'hourly_cost': 60.0,
            'default_billable_rate': 78.0
        },
        {
            'name': 'Superintendent - Level 3',
            'description': 'Senior field superintendent overseeing complex construction',
            'hourly_cost': 95.0,
            'default_billable_rate': 125.0
        },
        {
            'name': 'Superintendent - Level 2',
            'description': 'Experienced superintendent managing field operations',
            'hourly_cost': 80.0,
            'default_billable_rate': 105.0
        },
        {
            'name': 'Superintendent - Level 1',
            'description': 'Field superintendent coordinating on-site activities',
            'hourly_cost': 65.0,
            'default_billable_rate': 85.0
        },
        {
            'name': 'Assistant Superintendent',
            'description': 'Supports superintendents with field coordination',
            'hourly_cost': 55.0,
            'default_billable_rate': 72.0
        },
        {
            'name': 'Quality Control Manager',
            'description': 'Ensures quality standards and compliance on projects',
            'hourly_cost': 75.0,
            'default_billable_rate': 98.0
        },
        {
            'name': 'Foreman',
            'description': 'Leads work crews and coordinates daily tasks',
            'hourly_cost': 55.0,
            'default_billable_rate': 72.0
        },
        {
            'name': 'Accounting',
            'description': 'General accounting support for project financials',
            'hourly_cost': 55.0,
            'default_billable_rate': 72.0
        },
        {
            'name': 'VDC Manager',
            'description': 'Virtual Design and Construction coordination and modeling',
            'hourly_cost': 85.0,
            'default_billable_rate': 110.0
        },
        {
            'name': 'Safety Supervisor/Inspector',
            'description': 'Safety compliance, inspections, and training coordination',
            'hourly_cost': 70.0,
            'default_billable_rate': 90.0
        },
        # Legacy roles for backward compatibility
        {
            'name': 'Senior Estimator',
            'description': 'Leads cost estimation efforts and mentors junior staff',
            'hourly_cost': 70.0,
            'default_billable_rate': 90.0
        },
        {
            'name': 'Estimator',
            'description': 'Performs cost estimation and analysis for projects',
            'hourly_cost': 60.0,
            'default_billable_rate': 78.0
        },
        {
            'name': 'Preconstruction Manager',
            'description': 'Manages preconstruction activities and client relations',
            'hourly_cost': 75.0,
            'default_billable_rate': 98.0
        }
    ]

    roles = {}
    for data in roles_data:
        role = Role(
            name=data['name'],
            hourly_cost=data['hourly_cost'],
            description=data['description'],
            default_billable_rate=data.get('default_billable_rate')
        )
        db.session.add(role)
        db.session.flush()  # Flush to get the ID
        roles[data['name']] = role

    # Create sample staff with role_id references
    staff_data = [
        {
            'name': 'John Smith',
            'role_name': 'Project Manager - Level 2',
            'internal_hourly_cost': 85.0,  # What company pays this staff member
            'skills': ['Leadership', 'Planning', 'Communication']
        },
        {
            'name': 'Sarah Johnson',
            'role_name': 'Estimator',
            'internal_hourly_cost': 60.0,
            'skills': ['Cost Estimation', 'Excel', 'Construction Knowledge']
        },
        {
            'name': 'Mike Davis',
            'role_name': 'Preconstruction Manager',
            'internal_hourly_cost': 75.0,
            'skills': ['Preconstruction', 'Bid Management', 'Client Relations']
        },
        {
            'name': 'Emily Chen',
            'role_name': 'Senior Estimator',
            'internal_hourly_cost': 70.0,
            'skills': ['Advanced Estimation', 'Software Tools', 'Mentoring']
        }
    ]

    staff_members = []
    for data in staff_data:
        role = roles.get(data['role_name'])
        staff = Staff(
            name=data['name'],
            role_id=role.id,
            internal_hourly_cost=data['internal_hourly_cost']
        )
        staff.set_skills_list(data['skills'])
        staff_members.append(staff)
        db.session.add(staff)

    # Create sample projects
    from datetime import date, timedelta
    project_data = [
        {
            'name': 'Downtown Office Complex',
            'start_date': date.today() + timedelta(days=30),
            'end_date': date.today() + timedelta(days=365),
            'status': 'planning',
            'budget': 5000000.0,
            'location': 'Downtown City Center'
        },
        {
            'name': 'Residential Tower Phase 1',
            'start_date': date.today() + timedelta(days=60),
            'end_date': date.today() + timedelta(days=450),
            'status': 'planning',
            'budget': 8000000.0,
            'location': 'Riverside District'
        },
        {
            'name': 'Medical Center Expansion',
            'start_date': date.today() - timedelta(days=30),
            'end_date': date.today() + timedelta(days=270),
            'status': 'active',
            'budget': 3500000.0,
            'location': 'Medical District'
        }
    ]

    projects = []
    for data in project_data:
        project = Project(**data)
        projects.append(project)
        db.session.add(project)

    # Create sample assignments with various allocation types
    assignment_data = [
        {
            'staff_id': 1,  # John Smith
            'project_id': 1,  # Downtown Office Complex
            'start_date': date.today() + timedelta(days=30),
            'end_date': date.today() + timedelta(days=120),
            'hours_per_week': 40.0,
            'role_on_project': 'Project Manager - Level 2',
            'allocation_type': 'full',  # 100% allocated
            'allocation_percentage': 100.0
        },
        {
            'staff_id': 2,  # Sarah Johnson
            'project_id': 1,  # Downtown Office Complex
            'start_date': date.today() + timedelta(days=30),
            'end_date': date.today() + timedelta(days=90),
            'hours_per_week': 35.0,
            'role_on_project': 'Estimator',
            'allocation_type': 'percentage_total',  # 50% allocation
            'allocation_percentage': 50.0
        },
        {
            'staff_id': 3,  # Mike Davis
            'project_id': 3,  # Medical Center Expansion
            'start_date': date.today() - timedelta(days=30),
            'end_date': date.today() + timedelta(days=60),
            'hours_per_week': 45.0,
            'role_on_project': 'Preconstruction Manager',
            'allocation_type': 'split_by_projects',  # Auto-split based on overlapping assignments
            'allocation_percentage': 100.0  # This will be calculated dynamically
        },
        {
            'staff_id': 4,  # Emily Chen
            'project_id': 2,  # Residential Tower Phase 1
            'start_date': date.today() + timedelta(days=60),
            'end_date': date.today() + timedelta(days=150),
            'hours_per_week': 40.0,
            'role_on_project': 'Senior Estimator',
            'allocation_type': 'percentage_monthly',  # Different allocation per month
            'allocation_percentage': 100.0  # Will use monthly allocations
        }
    ]

    assignments = []
    for data in assignment_data:
        assignment = Assignment(**data)
        db.session.add(assignment)
        assignments.append(assignment)
    
    db.session.flush()  # Flush to get assignment IDs
    
    # Add monthly allocations for Emily Chen's assignment (percentage_monthly type)
    emily_assignment = assignments[3]  # Emily's assignment
    if emily_assignment.allocation_type == 'percentage_monthly':
        # Create monthly allocation entries with varying percentages
        start_month = date(emily_assignment.start_date.year, emily_assignment.start_date.month, 1)
        end_month = date(emily_assignment.end_date.year, emily_assignment.end_date.month, 1)
        
        # Example: Ramp up allocation over time
        monthly_percentages = [50, 75, 100, 100]  # Starting at 50%, ramping to 100%
        
        current_month = start_month
        month_index = 0
        while current_month <= end_month:
            allocation_pct = monthly_percentages[min(month_index, len(monthly_percentages) - 1)]
            monthly_alloc = AssignmentMonthlyAllocation(
                assignment_id=emily_assignment.id,
                month=current_month,
                allocation_percentage=allocation_pct
            )
            db.session.add(monthly_alloc)
            
            # Move to next month
            if current_month.month == 12:
                current_month = date(current_month.year + 1, 1, 1)
            else:
                current_month = date(current_month.year, current_month.month + 1, 1)
            month_index += 1

    # Create sample project templates
    templates_data = [
        {
            'name': 'Small Commercial Build-Out',
            'description': 'Template for small commercial tenant improvements and build-outs (under $2M)',
            'project_type': 'Commercial',
            'duration_months': 6,
            'roles': [
                {'role_name': 'Project Manager - Level 1', 'count': 1, 'start_month': 1, 'end_month': 6, 'hours_per_week': 40},
                {'role_name': 'Estimator', 'count': 1, 'start_month': 1, 'end_month': 2, 'hours_per_week': 30},
                {'role_name': 'Project Administrator', 'count': 1, 'start_month': 2, 'end_month': 6, 'hours_per_week': 20}
            ]
        },
        {
            'name': 'Medium Commercial Project',
            'description': 'Template for medium commercial projects ($2M-$10M)',
            'project_type': 'Commercial',
            'duration_months': 12,
            'roles': [
                {'role_name': 'Project Manager - Level 2', 'count': 1, 'start_month': 1, 'end_month': 12, 'hours_per_week': 40},
                {'role_name': 'Project Manager - Level 1', 'count': 1, 'start_month': 3, 'end_month': 12, 'hours_per_week': 40},
                {'role_name': 'Senior Estimator', 'count': 1, 'start_month': 1, 'end_month': 3, 'hours_per_week': 40},
                {'role_name': 'Estimator', 'count': 2, 'start_month': 1, 'end_month': 4, 'hours_per_week': 35},
                {'role_name': 'Project Administrator', 'count': 1, 'start_month': 2, 'end_month': 12, 'hours_per_week': 40},
                {'role_name': 'Project Accountant', 'count': 1, 'start_month': 3, 'end_month': 12, 'hours_per_week': 20}
            ]
        },
        {
            'name': 'Large Commercial Development',
            'description': 'Template for large commercial projects ($10M+)',
            'project_type': 'Commercial',
            'duration_months': 24,
            'roles': [
                {'role_name': 'Project Executive', 'count': 1, 'start_month': 1, 'end_month': 24, 'hours_per_week': 10},
                {'role_name': 'Senior Project Manager', 'count': 1, 'start_month': 1, 'end_month': 24, 'hours_per_week': 40},
                {'role_name': 'Project Manager - Level 3', 'count': 1, 'start_month': 1, 'end_month': 24, 'hours_per_week': 40},
                {'role_name': 'Project Manager - Level 2', 'count': 2, 'start_month': 3, 'end_month': 24, 'hours_per_week': 40},
                {'role_name': 'Preconstruction Manager', 'count': 1, 'start_month': 1, 'end_month': 6, 'hours_per_week': 40},
                {'role_name': 'Chief Estimator', 'count': 1, 'start_month': 1, 'end_month': 4, 'hours_per_week': 40},
                {'role_name': 'Senior Estimator', 'count': 2, 'start_month': 1, 'end_month': 5, 'hours_per_week': 40},
                {'role_name': 'Estimator', 'count': 3, 'start_month': 1, 'end_month': 6, 'hours_per_week': 40},
                {'role_name': 'Project Administrator', 'count': 2, 'start_month': 2, 'end_month': 24, 'hours_per_week': 40},
                {'role_name': 'Project Accountant', 'count': 1, 'start_month': 3, 'end_month': 24, 'hours_per_week': 40}
            ]
        },
        {
            'name': 'Healthcare Facility',
            'description': 'Template for healthcare and medical facility projects',
            'project_type': 'Healthcare',
            'duration_months': 18,
            'roles': [
                {'role_name': 'Project Executive', 'count': 1, 'start_month': 1, 'end_month': 18, 'hours_per_week': 8},
                {'role_name': 'Senior Project Manager', 'count': 1, 'start_month': 1, 'end_month': 18, 'hours_per_week': 40},
                {'role_name': 'Project Manager - Level 2', 'count': 2, 'start_month': 2, 'end_month': 18, 'hours_per_week': 40},
                {'role_name': 'Preconstruction Manager', 'count': 1, 'start_month': 1, 'end_month': 4, 'hours_per_week': 40},
                {'role_name': 'Senior Estimator', 'count': 1, 'start_month': 1, 'end_month': 5, 'hours_per_week': 40},
                {'role_name': 'Estimator', 'count': 2, 'start_month': 1, 'end_month': 6, 'hours_per_week': 40},
                {'role_name': 'Project Administrator', 'count': 1, 'start_month': 3, 'end_month': 18, 'hours_per_week': 40},
                {'role_name': 'Project Accountant', 'count': 1, 'start_month': 4, 'end_month': 18, 'hours_per_week': 30}
            ]
        },
        {
            'name': 'Residential Multi-Family',
            'description': 'Template for multi-family residential projects',
            'project_type': 'Residential',
            'duration_months': 14,
            'roles': [
                {'role_name': 'Project Manager - Level 3', 'count': 1, 'start_month': 1, 'end_month': 14, 'hours_per_week': 40},
                {'role_name': 'Project Manager - Level 2', 'count': 1, 'start_month': 2, 'end_month': 14, 'hours_per_week': 40},
                {'role_name': 'Senior Estimator', 'count': 1, 'start_month': 1, 'end_month': 3, 'hours_per_week': 40},
                {'role_name': 'Estimator', 'count': 2, 'start_month': 1, 'end_month': 4, 'hours_per_week': 35},
                {'role_name': 'Project Administrator', 'count': 1, 'start_month': 2, 'end_month': 14, 'hours_per_week': 40}
            ]
        }
    ]

    for template_data in templates_data:
        template = ProjectTemplate(
            name=template_data['name'],
            description=template_data['description'],
            project_type=template_data['project_type'],
            duration_months=template_data['duration_months'],
            is_active=True
        )
        db.session.add(template)
        db.session.flush()  # Get the template ID
        
        # Add template roles
        for role_data in template_data['roles']:
            role = roles.get(role_data['role_name'])
            if role:
                template_role = TemplateRole(
                    template_id=template.id,
                    role_id=role.id,
                    count=role_data['count'],
                    start_month=role_data['start_month'],
                    end_month=role_data.get('end_month'),
                    hours_per_week=role_data.get('hours_per_week', 40.0)
                )
                db.session.add(template_role)

    db.session.commit()
    print("Database seeded with sample data including allocation examples and project templates")

    # Note: Admin user creation is handled by create_default_admin() in auth.py
    # This ensures admin credentials come from environment variables

# CRUD helper functions
def get_staff_by_id(staff_id):
    """Get staff member by ID"""
    return Staff.query.get(staff_id)

def get_all_staff():
    """Get all staff members"""
    return Staff.query.all()

def get_project_by_id(project_id):
    """Get project by ID"""
    return Project.query.get(project_id)

def get_all_projects():
    """Get all projects"""
    return Project.query.all()

def get_assignment_by_id(assignment_id):
    """Get assignment by ID"""
    return Assignment.query.get(assignment_id)

def get_assignments_by_staff(staff_id):
    """Get all assignments for a staff member"""
    return Assignment.query.filter_by(staff_id=staff_id).all()

def get_assignments_by_project(project_id):
    """Get all assignments for a project"""
    return Assignment.query.filter_by(project_id=project_id).all()

def get_all_assignments():
    """Get all assignments"""
    return Assignment.query.all()

def create_staff(name, role_id, internal_hourly_cost, availability_start=None, availability_end=None, skills=None):
    """Create a new staff member"""
    from models import db
    staff = Staff(name=name, role_id=role_id, internal_hourly_cost=internal_hourly_cost,
                  availability_start=availability_start, availability_end=availability_end)
    if skills:
        staff.set_skills_list(skills)
    db.session.add(staff)
    db.session.commit()
    return staff

def create_project(name, start_date=None, end_date=None, status='planning', budget=None, location=None):
    """Create a new project"""
    project = Project(name=name, start_date=start_date, end_date=end_date,
                     status=status, budget=budget, location=location)
    db.session.add(project)
    db.session.commit()
    return project

def create_assignment(staff_id, project_id, start_date, end_date, hours_per_week=40.0, role_on_project=None):
    """Create a new assignment"""
    assignment = Assignment(staff_id=staff_id, project_id=project_id,
                           start_date=start_date, end_date=end_date,
                           hours_per_week=hours_per_week, role_on_project=role_on_project)
    db.session.add(assignment)
    db.session.commit()
    return assignment

def update_staff(staff_id, **kwargs):
    """Update staff member"""
    staff = Staff.query.get(staff_id)
    if not staff:
        return None

    for key, value in kwargs.items():
        if key == 'skills' and isinstance(value, list):
            staff.set_skills_list(value)
        elif hasattr(staff, key):
            setattr(staff, key, value)

    db.session.commit()
    return staff

def update_project(project_id, **kwargs):
    """Update project"""
    project = Project.query.get(project_id)
    if not project:
        return None

    for key, value in kwargs.items():
        if hasattr(project, key):
            setattr(project, key, value)

    db.session.commit()
    return project

def update_assignment(assignment_id, **kwargs):
    """Update assignment"""
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return None

    for key, value in kwargs.items():
        if hasattr(assignment, key):
            setattr(assignment, key, value)

    db.session.commit()
    return assignment

def delete_staff(staff_id):
    """Delete staff member"""
    staff = Staff.query.get(staff_id)
    if staff:
        db.session.delete(staff)
        db.session.commit()
        return True
    return False

def delete_project(project_id):
    """Delete project"""
    project = Project.query.get(project_id)
    if project:
        db.session.delete(project)
        db.session.commit()
        return True
    return False

def delete_assignment(assignment_id):
    """Delete assignment"""
    assignment = Assignment.query.get(assignment_id)
    if assignment:
        db.session.delete(assignment)
        db.session.commit()
        return True
    return False


# Role CRUD helper functions
def get_role_by_id(role_id):
    """Get role by ID"""
    return Role.query.get(role_id)


def get_role_by_name(name):
    """Get role by name"""
    return Role.query.filter_by(name=name).first()


def get_all_roles(active_only=False):
    """Get all roles"""
    query = Role.query
    if active_only:
        query = query.filter_by(is_active=True)
    return query.all()


def create_role(name, hourly_cost, description=None, default_billable_rate=None, is_active=True):
    """Create a new role"""
    from models import db
    role = Role(name=name, hourly_cost=hourly_cost, description=description, 
                default_billable_rate=default_billable_rate, is_active=is_active)
    db.session.add(role)
    db.session.commit()
    return role


def update_role(role_id, **kwargs):
    """Update role"""
    from models import db
    role = Role.query.get(role_id)
    if not role:
        return None

    for key, value in kwargs.items():
        if hasattr(role, key):
            setattr(role, key, value)

    db.session.commit()
    return role


def delete_role(role_id):
    """Delete role (only if no staff members assigned)"""
    from models import db
    role = Role.query.get(role_id)
    if role:
        if role.staff_members:
            return False  # Cannot delete role with assigned staff
        db.session.delete(role)
        db.session.commit()
        return True
    return False


# ProjectRoleRate CRUD helper functions
def get_project_role_rate(project_id, role_id):
    """Get a specific project role rate"""
    return ProjectRoleRate.query.filter_by(project_id=project_id, role_id=role_id).first()


def get_project_role_rates(project_id):
    """Get all role rates for a project"""
    return ProjectRoleRate.query.filter_by(project_id=project_id).all()


def create_project_role_rate(project_id, role_id, billable_rate):
    """Create a new project role rate"""
    from models import db
    rate = ProjectRoleRate(project_id=project_id, role_id=role_id, billable_rate=billable_rate)
    db.session.add(rate)
    db.session.commit()
    return rate


def update_project_role_rate(project_id, role_id, billable_rate):
    """Update or create a project role rate"""
    from models import db
    rate = get_project_role_rate(project_id, role_id)
    if rate:
        rate.billable_rate = billable_rate
        db.session.commit()
        return rate
    else:
        return create_project_role_rate(project_id, role_id, billable_rate)


def delete_project_role_rate(project_id, role_id):
    """Delete a project role rate"""
    from models import db
    rate = get_project_role_rate(project_id, role_id)
    if rate:
        db.session.delete(rate)
        db.session.commit()
        return True
    return False


def set_project_role_rates(project_id, rates_dict):
    """
    Set multiple role rates for a project at once.
    
    Args:
        project_id: ID of the project
        rates_dict: Dict mapping role_id to billable_rate
        
    Returns:
        List of created/updated ProjectRoleRate objects
    """
    from models import db
    results = []
    for role_id, billable_rate in rates_dict.items():
        rate = update_project_role_rate(project_id, role_id, billable_rate)
        results.append(rate)
    return results
