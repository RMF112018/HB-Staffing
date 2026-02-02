from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import json
from errors import (
    ValidationError, NotFoundError, ConflictError,
    validate_required, validate_date_range, validate_positive_number, validate_enum,
    safe_db_operation, log_api_request, log_api_response
)
from auth import (
    login_user, refresh_access_token, register_user,
    require_role, require_permission, optional_auth, get_current_user
)

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
        except (ValidationError, NotFoundError, ConflictError):
            # These are already handled by the global error handler
            raise
        except Exception as e:
            current_app.logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            raise  # Let the global error handler deal with it
    wrapper.__name__ = f.__name__
    return wrapper

# Validation helpers
def validate_staff_data(data):
    """Validate staff data"""
    validate_required(data, ['name', 'role', 'hourly_rate'])

    validate_positive_number(data['hourly_rate'], 'hourly_rate')

    # Optional date validation and range check
    if 'availability_start' in data and data['availability_start']:
        try:
            datetime.fromisoformat(data['availability_start'])
        except ValueError:
            raise ValidationError("Invalid date format for availability_start")

    if 'availability_end' in data and data['availability_end']:
        try:
            datetime.fromisoformat(data['availability_end'])
        except ValueError:
            raise ValidationError("Invalid date format for availability_end")

    if data.get('availability_start') and data.get('availability_end'):
        start_date = datetime.fromisoformat(data['availability_start']).date()
        end_date = datetime.fromisoformat(data['availability_end']).date()
        validate_date_range(start_date, end_date, "availability_start", "availability_end")

def validate_project_data(data):
    """Validate project data"""
    validate_required(data, ['name', 'status'])

    validate_enum(data['status'], ['planning', 'active', 'completed', 'cancelled', 'on-hold'], 'status')

    # Optional date validation
    if 'start_date' in data and data['start_date']:
        try:
            datetime.fromisoformat(data['start_date'])
        except ValueError:
            raise ValidationError("Invalid date format for start_date")

    if 'end_date' in data and data['end_date']:
        try:
            datetime.fromisoformat(data['end_date'])
        except ValueError:
            raise ValidationError("Invalid date format for end_date")

    if data.get('start_date') and data.get('end_date'):
        start_date = datetime.fromisoformat(data['start_date']).date()
        end_date = datetime.fromisoformat(data['end_date']).date()
        validate_date_range(start_date, end_date, "start_date", "end_date")

    if 'budget' in data and data['budget'] is not None:
        if not isinstance(data['budget'], (int, float)) or data['budget'] < 0:
            raise ValidationError("budget must be a non-negative number")

def validate_assignment_data(data):
    """Validate assignment data"""
    validate_required(data, ['staff_id', 'project_id', 'start_date', 'end_date', 'hours_per_week'])

    # Check if staff exists
    staff = Staff.query.get(data['staff_id'])
    if not staff:
        raise NotFoundError("Staff", data['staff_id'])

    # Check if project exists
    project = Project.query.get(data['project_id'])
    if not project:
        raise NotFoundError("Project", data['project_id'])

    # Date validation
    try:
        start_date = datetime.fromisoformat(data['start_date']).date()
        end_date = datetime.fromisoformat(data['end_date']).date()
    except ValueError:
        raise ValidationError("Invalid date format")

    validate_date_range(start_date, end_date, "start_date", "end_date")
    validate_positive_number(data['hours_per_week'], 'hours_per_week')

# STAFF ENDPOINTS

@api.route('/staff', methods=['GET'])
@handle_errors
@require_permission('read')
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
@require_permission('write')
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

    safe_db_operation(lambda: (db.session.add(staff), db.session.commit())[1], "Failed to create staff member")

    return jsonify(staff.to_dict()), 201

@api.route('/staff/<int:staff_id>', methods=['GET'])
@handle_errors
@require_permission('read')
def get_staff_by_id(staff_id):
    """Get a specific staff member by ID"""
    db, Staff, Project, Assignment = get_models()

    staff = Staff.query.get(staff_id)
    if not staff:
        raise NotFoundError("Staff", staff_id)

    return jsonify(staff.to_dict())

@api.route('/staff/<int:staff_id>', methods=['PUT'])
@handle_errors
@require_permission('write')
def update_staff(staff_id):
    """Update a staff member"""
    db, Staff, Project, Assignment = get_models()

    staff = Staff.query.get(staff_id)
    if not staff:
        raise NotFoundError("Staff", staff_id)

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

    safe_db_operation(db.session.commit, "Failed to update staff member")

    return jsonify(staff.to_dict())

@api.route('/staff/<int:staff_id>', methods=['DELETE'])
@handle_errors
@require_permission('delete')
def delete_staff(staff_id):
    """Delete a staff member"""
    db, Staff, Project, Assignment = get_models()

    staff = Staff.query.get(staff_id)
    if not staff:
        raise NotFoundError("Staff", staff_id)

    # Check if staff has assignments
    if staff.assignments:
        raise ConflictError("Cannot delete staff member with active assignments")

    safe_db_operation(lambda: (db.session.delete(staff), db.session.commit())[1], "Failed to delete staff member")

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

    safe_db_operation(lambda: (db.session.add(project), db.session.commit())[1], "Failed to create project")

    return jsonify(project.to_dict()), 201

@api.route('/projects/<int:project_id>', methods=['GET'])
@handle_errors
def get_project_by_id(project_id):
    """Get a specific project by ID"""
    db, Staff, Project, Assignment = get_models()

    project = Project.query.get(project_id)
    if not project:
        raise NotFoundError("Project", project_id)

    return jsonify(project.to_dict())

@api.route('/projects/<int:project_id>', methods=['PUT'])
@handle_errors
def update_project(project_id):
    """Update a project"""
    db, Staff, Project, Assignment = get_models()

    project = Project.query.get(project_id)
    if not project:
        raise NotFoundError("Project", project_id)

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

    safe_db_operation(db.session.commit, "Failed to update project")

    return jsonify(project.to_dict())

@api.route('/projects/<int:project_id>', methods=['DELETE'])
@handle_errors
def delete_project(project_id):
    """Delete a project"""
    db, Staff, Project, Assignment = get_models()

    project = Project.query.get(project_id)
    if not project:
        raise NotFoundError("Project", project_id)

    # Check if project has assignments
    if project.assignments:
        raise ConflictError("Cannot delete project with active assignments")

    safe_db_operation(lambda: (db.session.delete(project), db.session.commit())[1], "Failed to delete project")

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

    safe_db_operation(lambda: (db.session.add(assignment), db.session.commit())[1], "Failed to create assignment")

    return jsonify(assignment.to_dict()), 201

@api.route('/assignments/<int:assignment_id>', methods=['GET'])
@handle_errors
def get_assignment_by_id(assignment_id):
    """Get a specific assignment by ID"""
    db, Staff, Project, Assignment = get_models()

    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        raise NotFoundError("Assignment", assignment_id)

    return jsonify(assignment.to_dict())

@api.route('/assignments/<int:assignment_id>', methods=['PUT'])
@handle_errors
def update_assignment(assignment_id):
    """Update an assignment"""
    db, Staff, Project, Assignment = get_models()

    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        raise NotFoundError("Assignment", assignment_id)

    data = request.get_json()

    validate_assignment_data(data)

    # Update fields
    assignment.staff_id = data['staff_id']
    assignment.project_id = data['project_id']
    assignment.start_date = datetime.fromisoformat(data['start_date']).date()
    assignment.end_date = datetime.fromisoformat(data['end_date']).date()
    assignment.hours_per_week = data['hours_per_week']
    assignment.role_on_project = data.get('role_on_project')

    safe_db_operation(db.session.commit, "Failed to update assignment")

    return jsonify(assignment.to_dict())

@api.route('/assignments/<int:assignment_id>', methods=['DELETE'])
@handle_errors
def delete_assignment(assignment_id):
    """Delete an assignment"""
    db, Staff, Project, Assignment = get_models()

    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        raise NotFoundError("Assignment", assignment_id)

    safe_db_operation(lambda: (db.session.delete(assignment), db.session.commit())[1], "Failed to delete assignment")

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


# AUTHENTICATION ROUTES

@api.route('/auth/login', methods=['POST'])
@handle_errors
def login():
    """Authenticate user and return tokens"""
    data = request.get_json()

    validate_required(data, ['username', 'password'])

    result = login_user(data['username'], data['password'])
    return jsonify(result), 200


@api.route('/auth/refresh', methods=['POST'])
@handle_errors
def refresh():
    """Refresh access token"""
    result = refresh_access_token()
    return jsonify(result), 200


@api.route('/auth/register', methods=['POST'])
@handle_errors
@require_role('admin')
def register():
    """Register a new user (admin only)"""
    data = request.get_json()

    validate_required(data, ['username', 'email', 'password'])

    user = register_user(
        username=data['username'],
        email=data['email'],
        password=data['password'],
        role=data.get('role', 'preconstruction')
    )

    return jsonify({
        'message': 'User registered successfully',
        'user': user
    }), 201


@api.route('/auth/me', methods=['GET'])
@handle_errors
@require_permission('read')
def get_current_user_info():
    """Get current user information"""
    user = get_current_user()
    return jsonify({'user': user.to_dict()}), 200


@api.route('/auth/logout', methods=['POST'])
@handle_errors
@require_permission('read')
def logout():
    """Logout user (client should discard tokens)"""
    # In a JWT system, logout is typically handled client-side
    # by discarding the tokens. For server-side logout tracking,
    # you could implement a token blacklist, but that's complex.
    return jsonify({'message': 'Logged out successfully'}), 200


# USER MANAGEMENT ROUTES (Admin only)

@api.route('/users', methods=['GET'])
@handle_errors
@require_role('admin')
def get_users():
    """Get all users (admin only)"""
    db, Staff, Project, Assignment = get_models()
    from models import User

    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200


@api.route('/users/<int:user_id>', methods=['GET'])
@handle_errors
@require_role('admin')
def get_user(user_id):
    """Get specific user (admin only)"""
    from models import User

    user = User.query.get(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    return jsonify(user.to_dict()), 200


@api.route('/users/<int:user_id>', methods=['PUT'])
@handle_errors
@require_role('admin')
def update_user(user_id):
    """Update user (admin only)"""
    from models import User

    user = User.query.get(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    data = request.get_json()
    allowed_fields = ['email', 'role', 'is_active']

    for field in allowed_fields:
        if field in data:
            if field == 'role':
                validate_enum(data[field], ['preconstruction', 'leadership', 'admin'], 'role')
            setattr(user, field, data[field])

    if 'password' in data:
        user.set_password(data['password'])

    safe_db_operation(db.session.commit, "Failed to update user")

    return jsonify({
        'message': 'User updated successfully',
        'user': user.to_dict()
    }), 200


@api.route('/users/<int:user_id>', methods=['DELETE'])
@handle_errors
@require_role('admin')
def delete_user(user_id):
    """Delete user (admin only)"""
    db, Staff, Project, Assignment = get_models()
    from models import User

    user = User.query.get(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    # Prevent deleting the last admin
    admin_count = User.query.filter_by(role='admin').count()
    if user.role == 'admin' and admin_count <= 1:
        raise ConflictError("Cannot delete the last admin user")

    safe_db_operation(lambda: (db.session.delete(user), db.session.commit())[1], "Failed to delete user")

    return jsonify({'message': 'User deleted successfully'}), 200
