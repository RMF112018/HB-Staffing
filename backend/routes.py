from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import json

api = Blueprint('api', __name__)

def get_models():
    """Import models and db - call this inside route functions"""
    from db import db
    from models import Staff, Project, Assignment
    return db, Staff, Project, Assignment

# Error handling decorator
def handle_errors(f):
    """Decorator to handle common errors and return JSON responses"""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({'error': 'Validation error', 'message': str(e)}), 400
        except KeyError as e:
            return jsonify({'error': 'Missing field', 'message': str(e)}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}")
            return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500
    wrapper.__name__ = f.__name__
    return wrapper

# Validation helpers
def validate_staff_data(data):
    """Validate staff data"""
    required_fields = ['name', 'role', 'hourly_rate']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(data['hourly_rate'], (int, float)) or data['hourly_rate'] <= 0:
        raise ValueError("hourly_rate must be a positive number")

    # Optional date validation
    if 'availability_start' in data and data['availability_start']:
        try:
            datetime.fromisoformat(data['availability_start'])
        except ValueError:
            raise ValueError("Invalid date format for availability_start")

    if 'availability_end' in data and data['availability_end']:
        try:
            datetime.fromisoformat(data['availability_end'])
        except ValueError:
            raise ValueError("Invalid date format for availability_end")

def validate_project_data(data):
    """Validate project data"""
    required_fields = ['name', 'status']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    valid_statuses = ['planning', 'active', 'completed', 'cancelled', 'on-hold']
    if data['status'] not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    # Optional date validation
    if 'start_date' in data and data['start_date']:
        try:
            datetime.fromisoformat(data['start_date'])
        except ValueError:
            raise ValueError("Invalid date format for start_date")

    if 'end_date' in data and data['end_date']:
        try:
            datetime.fromisoformat(data['end_date'])
        except ValueError:
            raise ValueError("Invalid date format for end_date")

    if 'budget' in data and data['budget'] is not None:
        if not isinstance(data['budget'], (int, float)) or data['budget'] < 0:
            raise ValueError("budget must be a non-negative number")

def validate_assignment_data(data):
    """Validate assignment data"""
    required_fields = ['staff_id', 'project_id', 'start_date', 'end_date', 'hours_per_week']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Check if staff exists
    staff = Staff.query.get(data['staff_id'])
    if not staff:
        raise ValueError("Invalid staff_id: staff member not found")

    # Check if project exists
    project = Project.query.get(data['project_id'])
    if not project:
        raise ValueError("Invalid project_id: project not found")

    # Date validation
    try:
        start_date = datetime.fromisoformat(data['start_date'])
        end_date = datetime.fromisoformat(data['end_date'])
    except ValueError:
        raise ValueError("Invalid date format")

    if end_date <= start_date:
        raise ValueError("end_date must be after start_date")

    if not isinstance(data['hours_per_week'], (int, float)) or data['hours_per_week'] <= 0:
        raise ValueError("hours_per_week must be a positive number")

# STAFF ENDPOINTS

@api.route('/staff', methods=['GET'])
@handle_errors
def get_staff():
    """Get all staff members with optional filtering"""
    db, Staff, Project, Assignment = get_models()

    # Query parameters for filtering
    role = request.args.get('role')
    available_from = request.args.get('available_from')
    available_to = request.args.get('available_to')
    skills = request.args.get('skills')  # comma-separated skills

    query = Staff.query

    if role:
        query = query.filter(Staff.role.ilike(f'%{role}%'))

    if available_from:
        try:
            from_date = datetime.fromisoformat(available_from).date()
            query = query.filter(
                (Staff.availability_start <= from_date) |
                (Staff.availability_start.is_(None))
            )
        except ValueError:
            raise ValueError("Invalid date format for available_from")

    if available_to:
        try:
            to_date = datetime.fromisoformat(available_to).date()
            query = query.filter(
                (Staff.availability_end >= to_date) |
                (Staff.availability_end.is_(None))
            )
        except ValueError:
            raise ValueError("Invalid date format for available_to")

    if skills:
        skill_list = [s.strip() for s in skills.split(',')]
        # Filter staff who have any of the requested skills
        staff_with_skills = []
        for staff in query.all():
            staff_skills = staff.get_skills_list()
            if any(skill in staff_skills for skill in skill_list):
                staff_with_skills.append(staff)
        # Convert back to query result format
        staff_members = staff_with_skills
    else:
        staff_members = query.all()

    return jsonify([staff.to_dict() for staff in staff_members])

@api.route('/staff', methods=['POST'])
@handle_errors
def create_staff():
    """Create a new staff member"""
    db, Staff, Project, Assignment = get_models()

    data = request.get_json()

    validate_staff_data(data)

    # Convert date strings to date objects
    availability_start = None
    availability_end = None

    if data.get('availability_start'):
        availability_start = datetime.fromisoformat(data['availability_start']).date()
    if data.get('availability_end'):
        availability_end = datetime.fromisoformat(data['availability_end']).date()

    staff = Staff(
        name=data['name'],
        role=data['role'],
        hourly_rate=data['hourly_rate'],
        availability_start=availability_start,
        availability_end=availability_end
    )

    if 'skills' in data:
        staff.set_skills_list(data['skills'])

    db.session.add(staff)
    db.session.commit()

    return jsonify(staff.to_dict()), 201

@api.route('/staff/<int:staff_id>', methods=['GET'])
@handle_errors
def get_staff_by_id(staff_id):
    """Get a specific staff member by ID"""
    db, Staff, Project, Assignment = get_models()

    staff = Staff.query.get(staff_id)
    if not staff:
        return jsonify({'error': 'Staff member not found'}), 404

    return jsonify(staff.to_dict())

@api.route('/staff/<int:staff_id>', methods=['PUT'])
@handle_errors
def update_staff(staff_id):
    """Update a staff member"""
    staff = Staff.query.get(staff_id)
    if not staff:
        return jsonify({'error': 'Staff member not found'}), 404

    data = request.get_json()

    # Validate data
    validate_staff_data(data)

    # Update fields
    staff.name = data['name']
    staff.role = data['role']
    staff.hourly_rate = data['hourly_rate']

    # Handle dates
    if 'availability_start' in data:
        staff.availability_start = datetime.fromisoformat(data['availability_start']).date() if data['availability_start'] else None
    if 'availability_end' in data:
        staff.availability_end = datetime.fromisoformat(data['availability_end']).date() if data['availability_end'] else None

    # Handle skills
    if 'skills' in data:
        staff.set_skills_list(data['skills'])

    db.session.commit()

    return jsonify(staff.to_dict())

@api.route('/staff/<int:staff_id>', methods=['DELETE'])
@handle_errors
def delete_staff(staff_id):
    """Delete a staff member"""
    staff = Staff.query.get(staff_id)
    if not staff:
        return jsonify({'error': 'Staff member not found'}), 404

    # Check if staff has assignments
    if staff.assignments:
        return jsonify({'error': 'Cannot delete staff member with active assignments'}), 400

    db.session.delete(staff)
    db.session.commit()

    return jsonify({'message': 'Staff member deleted successfully'})

# PROJECT ENDPOINTS

@api.route('/projects', methods=['GET'])
@handle_errors
def get_projects():
    """Get all projects with optional filtering"""
    db, Staff, Project, Assignment = get_models()

    status = request.args.get('status')
    location = request.args.get('location')

    query = Project.query

    if status:
        query = query.filter(Project.status == status)

    if location:
        query = query.filter(Project.location.ilike(f'%{location}%'))

    projects = query.all()
    return jsonify([project.to_dict() for project in projects])

@api.route('/projects', methods=['POST'])
@handle_errors
def create_project():
    """Create a new project"""
    db, Staff, Project, Assignment = get_models()

    data = request.get_json()

    validate_project_data(data)

    # Convert date strings to date objects
    start_date = None
    end_date = None

    if data.get('start_date'):
        start_date = datetime.fromisoformat(data['start_date']).date()
    if data.get('end_date'):
        end_date = datetime.fromisoformat(data['end_date']).date()

    project = Project(
        name=data['name'],
        start_date=start_date,
        end_date=end_date,
        status=data['status'],
        budget=data.get('budget'),
        location=data.get('location')
    )

    db.session.add(project)
    db.session.commit()

    return jsonify(project.to_dict()), 201

@api.route('/projects/<int:project_id>', methods=['GET'])
@handle_errors
def get_project_by_id(project_id):
    """Get a specific project by ID"""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    return jsonify(project.to_dict())

@api.route('/projects/<int:project_id>', methods=['PUT'])
@handle_errors
def update_project(project_id):
    """Update a project"""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()

    validate_project_data(data)

    # Update fields
    project.name = data['name']
    project.status = data['status']

    # Handle dates
    if 'start_date' in data:
        project.start_date = datetime.fromisoformat(data['start_date']).date() if data['start_date'] else None
    if 'end_date' in data:
        project.end_date = datetime.fromisoformat(data['end_date']).date() if data['end_date'] else None

    # Handle optional fields
    if 'budget' in data:
        project.budget = data['budget']
    if 'location' in data:
        project.location = data['location']

    db.session.commit()

    return jsonify(project.to_dict())

@api.route('/projects/<int:project_id>', methods=['DELETE'])
@handle_errors
def delete_project(project_id):
    """Delete a project"""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    # Check if project has assignments
    if project.assignments:
        return jsonify({'error': 'Cannot delete project with active assignments'}), 400

    db.session.delete(project)
    db.session.commit()

    return jsonify({'message': 'Project deleted successfully'})

# ASSIGNMENT ENDPOINTS

@api.route('/assignments', methods=['GET'])
@handle_errors
def get_assignments():
    """Get all assignments with optional filtering"""
    db, Staff, Project, Assignment = get_models()

    staff_id = request.args.get('staff_id', type=int)
    project_id = request.args.get('project_id', type=int)

    query = Assignment.query

    if staff_id:
        query = query.filter(Assignment.staff_id == staff_id)

    if project_id:
        query = query.filter(Assignment.project_id == project_id)

    assignments = query.all()
    return jsonify([assignment.to_dict() for assignment in assignments])

@api.route('/assignments', methods=['POST'])
@handle_errors
def create_assignment():
    """Create a new assignment"""
    db, Staff, Project, Assignment = get_models()

    data = request.get_json()

    validate_assignment_data(data)

    # Convert date strings to date objects
    start_date = datetime.fromisoformat(data['start_date']).date()
    end_date = datetime.fromisoformat(data['end_date']).date()

    assignment = Assignment(
        staff_id=data['staff_id'],
        project_id=data['project_id'],
        start_date=start_date,
        end_date=end_date,
        hours_per_week=data['hours_per_week'],
        role_on_project=data.get('role_on_project')
    )

    db.session.add(assignment)
    db.session.commit()

    return jsonify(assignment.to_dict()), 201

@api.route('/assignments/<int:assignment_id>', methods=['GET'])
@handle_errors
def get_assignment_by_id(assignment_id):
    """Get a specific assignment by ID"""
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({'error': 'Assignment not found'}), 404

    return jsonify(assignment.to_dict())

@api.route('/assignments/<int:assignment_id>', methods=['PUT'])
@handle_errors
def update_assignment(assignment_id):
    """Update an assignment"""
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({'error': 'Assignment not found'}), 404

    data = request.get_json()

    validate_assignment_data(data)

    # Update fields
    assignment.staff_id = data['staff_id']
    assignment.project_id = data['project_id']
    assignment.start_date = datetime.fromisoformat(data['start_date']).date()
    assignment.end_date = datetime.fromisoformat(data['end_date']).date()
    assignment.hours_per_week = data['hours_per_week']
    assignment.role_on_project = data.get('role_on_project')

    db.session.commit()

    return jsonify(assignment.to_dict())

@api.route('/assignments/<int:assignment_id>', methods=['DELETE'])
@handle_errors
def delete_assignment(assignment_id):
    """Delete an assignment"""
    db, Staff, Project, Assignment = get_models()

    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({'error': 'Assignment not found'}), 404

    db.session.delete(assignment)
    db.session.commit()

    return jsonify({'message': 'Assignment deleted successfully'})

# FORECASTING ENDPOINTS

@api.route('/projects/<int:project_id>/forecast', methods=['GET'])
@handle_errors
def get_project_forecast(project_id):
    """Get staffing forecast for a specific project"""
    from engine import calculate_project_staffing_needs

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Convert string dates to date objects
    start = None
    end = None
    if start_date:
        start = datetime.fromisoformat(start_date).date()
    if end_date:
        end = datetime.fromisoformat(end_date).date()

    forecast = calculate_project_staffing_needs(project_id, start, end)
    return jsonify(forecast)

@api.route('/forecasts/organization', methods=['GET'])
@handle_errors
def get_organization_forecast():
    """Get organization-wide staffing forecast"""
    from engine import calculate_organization_forecast

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400

    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()

    forecast = calculate_organization_forecast(start, end)
    return jsonify(forecast)

@api.route('/forecasts/simulate', methods=['POST'])
@handle_errors
def simulate_forecast():
    """Simulate what-if scenarios for forecasting"""
    from engine import simulate_scenario

    data = request.get_json()

    if not data or 'project_id' not in data:
        return jsonify({'error': 'project_id is required'}), 400

    project_id = data['project_id']
    changes = data.get('changes', {})

    result = simulate_scenario(project_id, changes)
    return jsonify(result)

@api.route('/projects/<int:project_id>/cost', methods=['GET'])
@handle_errors
def get_project_cost(project_id):
    """Get cost analysis for a specific project"""
    from engine import calculate_project_cost

    cost_analysis = calculate_project_cost(project_id)
    return jsonify(cost_analysis)

@api.route('/forecasts/gaps', methods=['GET'])
@handle_errors
def get_staffing_gaps():
    """Detect staffing gaps"""
    from engine import detect_staffing_gaps

    project_id = request.args.get('project_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    start = None
    end = None
    if start_date:
        start = datetime.fromisoformat(start_date).date()
    if end_date:
        end = datetime.fromisoformat(end_date).date()

    gaps = detect_staffing_gaps(project_id, start, end)
    return jsonify({'gaps': gaps, 'count': len(gaps)})

@api.route('/capacity/analysis', methods=['GET'])
@handle_errors
def get_capacity_analysis():
    """Get capacity analysis for staff"""
    from engine import calculate_capacity_analysis

    staff_id = request.args.get('staff_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400

    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()

    analysis = calculate_capacity_analysis(staff_id, start, end)
    return jsonify(analysis)
