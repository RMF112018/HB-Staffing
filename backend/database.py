from models import Staff, Project, Assignment
import json

def init_db():
    """Initialize the database and create all tables"""
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

    # Create sample staff
    staff_data = [
        {
            'name': 'John Smith',
            'role': 'Project Manager',
            'hourly_rate': 75.0,
            'skills': ['Leadership', 'Planning', 'Communication']
        },
        {
            'name': 'Sarah Johnson',
            'role': 'Estimator',
            'hourly_rate': 65.0,
            'skills': ['Cost Estimation', 'Excel', 'Construction Knowledge']
        },
        {
            'name': 'Mike Davis',
            'role': 'Preconstruction Manager',
            'hourly_rate': 80.0,
            'skills': ['Preconstruction', 'Bid Management', 'Client Relations']
        },
        {
            'name': 'Emily Chen',
            'role': 'Senior Estimator',
            'hourly_rate': 70.0,
            'skills': ['Advanced Estimation', 'Software Tools', 'Mentoring']
        }
    ]

    staff_members = []
    for data in staff_data:
        staff = Staff(
            name=data['name'],
            role=data['role'],
            hourly_rate=data['hourly_rate']
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

    # Create sample assignments
    assignment_data = [
        {
            'staff_id': 1,  # John Smith
            'project_id': 1,  # Downtown Office Complex
            'start_date': date.today() + timedelta(days=30),
            'end_date': date.today() + timedelta(days=120),
            'hours_per_week': 40.0,
            'role_on_project': 'Project Manager'
        },
        {
            'staff_id': 2,  # Sarah Johnson
            'project_id': 1,  # Downtown Office Complex
            'start_date': date.today() + timedelta(days=30),
            'end_date': date.today() + timedelta(days=90),
            'hours_per_week': 35.0,
            'role_on_project': 'Lead Estimator'
        },
        {
            'staff_id': 3,  # Mike Davis
            'project_id': 3,  # Medical Center Expansion
            'start_date': date.today() - timedelta(days=30),
            'end_date': date.today() + timedelta(days=60),
            'hours_per_week': 45.0,
            'role_on_project': 'Preconstruction Manager'
        },
        {
            'staff_id': 4,  # Emily Chen
            'project_id': 2,  # Residential Tower Phase 1
            'start_date': date.today() + timedelta(days=60),
            'end_date': date.today() + timedelta(days=150),
            'hours_per_week': 40.0,
            'role_on_project': 'Senior Estimator'
        }
    ]

    for data in assignment_data:
        assignment = Assignment(**data)
        db.session.add(assignment)

    db.session.commit()
    print("Database seeded with sample data")

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

def create_staff(name, role, hourly_rate, availability_start=None, availability_end=None, skills=None):
    """Create a new staff member"""
    staff = Staff(name=name, role=role, hourly_rate=hourly_rate,
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
