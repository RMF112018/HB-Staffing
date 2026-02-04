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
    from models import Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation
    return db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation


def get_role_model():
    """Import Role model - for role-specific endpoints"""
    from db import db
    from models import Role
    return db, Role


def get_project_models():
    """Import Project and related models - for project-specific endpoints"""
    from db import db
    from models import Project, ProjectRoleRate, Role
    return db, Project, ProjectRoleRate, Role

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
def validate_role_data(data, is_update=False):
    """Validate role data"""
    validate_required(data, ['name', 'hourly_cost'])

    validate_positive_number(data['hourly_cost'], 'hourly_cost')

    # Validate optional default_billable_rate
    if 'default_billable_rate' in data and data['default_billable_rate'] is not None:
        validate_positive_number(data['default_billable_rate'], 'default_billable_rate')

    # Check for unique name
    db, Role = get_role_model()
    existing_role = Role.query.filter_by(name=data['name']).first()
    if existing_role:
        if not is_update or (is_update and existing_role.id != data.get('_current_id')):
            raise ConflictError(f"Role with name '{data['name']}' already exists")


def validate_staff_data(data):
    """Validate staff data"""
    validate_required(data, ['name', 'role_id', 'internal_hourly_cost'])

    validate_positive_number(data['internal_hourly_cost'], 'internal_hourly_cost')

    # Check that role_id references a valid role
    db, Role = get_role_model()
    role = db.session.get(Role, data['role_id'])
    if not role:
        raise NotFoundError("Role", data['role_id'])

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

def validate_project_data(data, current_project_id=None):
    """Validate project data including hierarchy rules"""
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
    
    # Hierarchy validation
    db, Project, ProjectRoleRate, Role = get_project_models()
    
    parent_project_id = data.get('parent_project_id')
    is_folder = data.get('is_folder', False)
    
    if parent_project_id:
        # Validate parent project exists
        parent_project = db.session.get(Project, parent_project_id)
        if not parent_project:
            raise NotFoundError("Parent Project", parent_project_id)
        
        # Parent must be a folder
        if not parent_project.is_folder:
            raise ValidationError("Parent project must be a folder (is_folder=True)")
        
        # Prevent circular references
        if current_project_id:
            if parent_project_id == current_project_id:
                raise ValidationError("Project cannot be its own parent")
            # Check if parent_project_id is a descendant of current_project_id
            if is_descendant_of(parent_project_id, current_project_id):
                raise ValidationError("Cannot set parent to a descendant project (circular reference)")
    
    # Sub-projects cannot have sub-projects (must be a folder to have children)
    if current_project_id and not is_folder:
        current_project = db.session.get(Project, current_project_id)
        if current_project and current_project.sub_projects:
            raise ValidationError("Cannot convert a folder with sub-projects to a non-folder")


def is_descendant_of(project_id, potential_ancestor_id):
    """Check if project_id is a descendant of potential_ancestor_id"""
    db, Project, ProjectRoleRate, Role = get_project_models()
    
    project = db.session.get(Project, project_id)
    while project and project.parent_project_id:
        if project.parent_project_id == potential_ancestor_id:
            return True
        project = project.parent_project
    return False

def validate_assignment_data(data, db, Staff, Project):
    """Validate assignment data"""
    validate_required(data, ['staff_id', 'project_id', 'start_date', 'end_date', 'hours_per_week'])

    # Check if staff exists
    staff = db.session.get(Staff, data['staff_id'])
    if not staff:
        raise NotFoundError("Staff", data['staff_id'])

    # Check if project exists
    project = db.session.get(Project, data['project_id'])
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
    
    # Validate allocation fields
    from models import Assignment
    valid_allocation_types = Assignment.ALLOCATION_TYPES
    
    if 'allocation_type' in data:
        if data['allocation_type'] not in valid_allocation_types:
            raise ValidationError(f"Invalid allocation_type. Must be one of: {', '.join(valid_allocation_types)}")
    
    if 'allocation_percentage' in data:
        allocation_pct = data['allocation_percentage']
        if not isinstance(allocation_pct, (int, float)) or allocation_pct < 0 or allocation_pct > 100:
            raise ValidationError("allocation_percentage must be a number between 0 and 100")


# ROLE ENDPOINTS

@api.route('/roles', methods=['GET'])
@handle_errors
def get_roles():
    """Get all roles with optional filtering"""
    db, Role = get_role_model()

    # Optional filter for active only
    active_only = request.args.get('active_only', 'false').lower() == 'true'

    query = Role.query
    if active_only:
        query = query.filter_by(is_active=True)

    roles = query.all()
    return jsonify([role.to_dict() for role in roles])


@api.route('/roles', methods=['POST'])
@handle_errors
def create_role():
    """Create a new role"""
    db, Role = get_role_model()

    data = request.get_json()

    validate_role_data(data)

    role = Role(
        name=data['name'],
        hourly_cost=data['hourly_cost'],
        description=data.get('description'),
        default_billable_rate=data.get('default_billable_rate'),
        is_active=data.get('is_active', True)
    )

    safe_db_operation(lambda: (db.session.add(role), db.session.commit())[1], "Failed to create role")

    return jsonify(role.to_dict()), 201


@api.route('/roles/<int:role_id>', methods=['GET'])
@handle_errors
def get_role_by_id(role_id):
    """Get a specific role by ID"""
    db, Role = get_role_model()

    role = db.session.get(Role, role_id)
    if not role:
        raise NotFoundError("Role", role_id)

    return jsonify(role.to_dict())


@api.route('/roles/<int:role_id>', methods=['PUT'])
@handle_errors
def update_role(role_id):
    """Update a role"""
    db, Role = get_role_model()

    role = db.session.get(Role, role_id)
    if not role:
        raise NotFoundError("Role", role_id)

    data = request.get_json()
    data['_current_id'] = role_id  # Used for unique name validation

    validate_role_data(data, is_update=True)

    # Update fields
    role.name = data['name']
    role.hourly_cost = data['hourly_cost']

    if 'description' in data:
        role.description = data['description']
    if 'default_billable_rate' in data:
        role.default_billable_rate = data['default_billable_rate']
    if 'is_active' in data:
        role.is_active = data['is_active']

    safe_db_operation(db.session.commit, "Failed to update role")

    return jsonify(role.to_dict())


@api.route('/roles/<int:role_id>', methods=['DELETE'])
@handle_errors
def delete_role(role_id):
    """Delete a role"""
    db, Role = get_role_model()

    role = db.session.get(Role, role_id)
    if not role:
        raise NotFoundError("Role", role_id)

    # Check if any staff members are assigned to this role
    if role.staff_members:
        raise ConflictError(f"Cannot delete role '{role.name}' - {len(role.staff_members)} staff member(s) assigned")

    safe_db_operation(lambda: (db.session.delete(role), db.session.commit())[1], "Failed to delete role")

    return jsonify({'message': 'Role deleted successfully'})


# STAFF ENDPOINTS

@api.route('/staff', methods=['GET'])
@handle_errors
def get_staff():
    """Get all staff members with optional filtering"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    # Query parameters for filtering
    role_id = request.args.get('role_id', type=int)
    role_name = request.args.get('role')  # Keep backward compatibility
    available_from = request.args.get('available_from')
    available_to = request.args.get('available_to')
    skills = request.args.get('skills')  # comma-separated skills

    query = Staff.query

    if role_id:
        query = query.filter(Staff.role_id == role_id)
    elif role_name:
        # Filter by role name (through join)
        query = query.join(Role).filter(Role.name.ilike(f'%{role_name}%'))

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
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

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
        role_id=data['role_id'],
        internal_hourly_cost=data['internal_hourly_cost'],
        availability_start=availability_start,
        availability_end=availability_end
    )

    if 'skills' in data:
        staff.set_skills_list(data['skills'])

    safe_db_operation(lambda: (db.session.add(staff), db.session.commit())[1], "Failed to create staff member")

    return jsonify(staff.to_dict()), 201

@api.route('/staff/<int:staff_id>', methods=['GET'])
@handle_errors
def get_staff_by_id(staff_id):
    """Get a specific staff member by ID"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    staff = db.session.get(Staff, staff_id)
    if not staff:
        raise NotFoundError("Staff", staff_id)

    return jsonify(staff.to_dict())

@api.route('/staff/<int:staff_id>', methods=['PUT'])
@handle_errors
def update_staff(staff_id):
    """Update a staff member"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    staff = db.session.get(Staff, staff_id)
    if not staff:
        raise NotFoundError("Staff", staff_id)

    data = request.get_json()

    # Validate data
    validate_staff_data(data)

    # Update fields
    staff.name = data['name']
    staff.role_id = data['role_id']
    staff.internal_hourly_cost = data['internal_hourly_cost']

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
def delete_staff(staff_id):
    """Delete a staff member"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    staff = db.session.get(Staff, staff_id)
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
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    status = request.args.get('status')
    location = request.args.get('location')
    parent_id = request.args.get('parent_id', type=int)
    is_folder = request.args.get('is_folder')
    top_level_only = request.args.get('top_level_only', 'false').lower() == 'true'
    include_children = request.args.get('include_children', 'false').lower() == 'true'

    query = Project.query

    if status:
        query = query.filter(Project.status == status)

    if location:
        query = query.filter(Project.location.ilike(f'%{location}%'))
    
    # Filter by parent project
    if parent_id is not None:
        query = query.filter(Project.parent_project_id == parent_id)
    elif top_level_only:
        # Only return projects with no parent (top-level folders and standalone projects)
        query = query.filter(Project.parent_project_id.is_(None))
    
    # Filter by folder status
    if is_folder is not None:
        is_folder_bool = is_folder.lower() == 'true'
        query = query.filter(Project.is_folder == is_folder_bool)

    projects = query.all()
    return jsonify([project.to_dict(include_children=include_children) for project in projects])

@api.route('/projects', methods=['POST'])
@handle_errors
def create_project():
    """Create a new project or folder"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

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
        location=data.get('location'),
        parent_project_id=data.get('parent_project_id'),
        is_folder=data.get('is_folder', False)
    )

    safe_db_operation(lambda: (db.session.add(project), db.session.commit())[1], "Failed to create project")

    # Auto-populate role rates from active roles with default billable rates
    active_roles = Role.query.filter_by(is_active=True).all()
    for role in active_roles:
        if role.default_billable_rate is not None:
            rate = ProjectRoleRate(
                project_id=project.id,
                role_id=role.id,
                billable_rate=role.default_billable_rate
            )
            db.session.add(rate)
    
    safe_db_operation(db.session.commit, "Failed to auto-populate project role rates")

    return jsonify(project.to_dict(include_children=True)), 201

@api.route('/projects/<int:project_id>', methods=['GET'])
@handle_errors
def get_project_by_id(project_id):
    """Get a specific project by ID with hierarchy information"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    project = db.session.get(Project, project_id)
    if not project:
        raise NotFoundError("Project", project_id)

    include_children = request.args.get('include_children', 'true').lower() == 'true'
    return jsonify(project.to_dict(include_children=include_children))

@api.route('/projects/<int:project_id>', methods=['PUT'])
@handle_errors
def update_project(project_id):
    """Update a project"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    project = db.session.get(Project, project_id)
    if not project:
        raise NotFoundError("Project", project_id)

    data = request.get_json()

    validate_project_data(data, current_project_id=project_id)

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
    
    # Handle hierarchy fields
    if 'parent_project_id' in data:
        project.parent_project_id = data['parent_project_id']
    if 'is_folder' in data:
        project.is_folder = data['is_folder']

    safe_db_operation(db.session.commit, "Failed to update project")

    return jsonify(project.to_dict(include_children=True))

@api.route('/projects/<int:project_id>', methods=['DELETE'])
@handle_errors
def delete_project(project_id):
    """Delete a project"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    project = db.session.get(Project, project_id)
    if not project:
        raise NotFoundError("Project", project_id)

    # Check if project has assignments
    if project.assignments:
        raise ConflictError("Cannot delete project with active assignments")
    
    # Check if project has sub-projects
    if project.sub_projects:
        raise ConflictError("Cannot delete project folder with sub-projects. Delete sub-projects first.")

    safe_db_operation(lambda: (db.session.delete(project), db.session.commit())[1], "Failed to delete project")

    return jsonify({'message': 'Project deleted successfully'})


# PROJECT ROLE RATE ENDPOINTS

@api.route('/projects/<int:project_id>/role-rates', methods=['GET'])
@handle_errors
def get_project_role_rates(project_id):
    """Get all role rates for a project (including inherited from parent)"""
    db, Project, ProjectRoleRate, Role = get_project_models()

    project = db.session.get(Project, project_id)
    if not project:
        raise NotFoundError("Project", project_id)

    # Get all role rates including inherited
    all_rates = project.get_all_role_rates()
    
    # Also return the project's own explicit rates
    explicit_rates = [rate.to_dict() for rate in project.role_rates]

    return jsonify({
        'project_id': project_id,
        'project_name': project.name,
        'is_folder': project.is_folder,
        'parent_project_id': project.parent_project_id,
        'all_rates': all_rates,  # All rates including inherited
        'explicit_rates': explicit_rates  # Only rates set on this project
    })

@api.route('/projects/<int:project_id>/role-rates', methods=['POST'])
@handle_errors
@require_permission('write')
def set_project_role_rates(project_id):
    """Set multiple role rates for a project"""
    db, Project, ProjectRoleRate, Role = get_project_models()

    project = db.session.get(Project, project_id)
    if not project:
        raise NotFoundError("Project", project_id)

    data = request.get_json()
    
    if not data or 'rates' not in data:
        raise ValidationError("'rates' array is required")
    
    rates_data = data['rates']
    created_rates = []
    
    for rate_item in rates_data:
        if 'role_id' not in rate_item or 'billable_rate' not in rate_item:
            raise ValidationError("Each rate must have 'role_id' and 'billable_rate'")
        
        role_id = rate_item['role_id']
        billable_rate = rate_item['billable_rate']
        
        # Validate role exists
        role = db.session.get(Role, role_id)
        if not role:
            raise NotFoundError("Role", role_id)
        
        validate_positive_number(billable_rate, 'billable_rate')
        
        # Check if rate already exists for this project/role
        existing_rate = ProjectRoleRate.query.filter_by(
            project_id=project_id, role_id=role_id
        ).first()
        
        if existing_rate:
            existing_rate.billable_rate = billable_rate
            created_rates.append(existing_rate)
        else:
            new_rate = ProjectRoleRate(
                project_id=project_id,
                role_id=role_id,
                billable_rate=billable_rate
            )
            db.session.add(new_rate)
            created_rates.append(new_rate)
    
    safe_db_operation(db.session.commit, "Failed to set project role rates")
    
    return jsonify({
        'message': f'Successfully set {len(created_rates)} role rate(s)',
        'rates': [rate.to_dict() for rate in created_rates]
    }), 201

@api.route('/projects/<int:project_id>/role-rates/<int:role_id>', methods=['PUT'])
@handle_errors
@require_permission('write')
def update_project_role_rate(project_id, role_id):
    """Update a specific role rate for a project"""
    db, Project, ProjectRoleRate, Role = get_project_models()

    project = db.session.get(Project, project_id)
    if not project:
        raise NotFoundError("Project", project_id)
    
    role = db.session.get(Role, role_id)
    if not role:
        raise NotFoundError("Role", role_id)

    data = request.get_json()
    
    if 'billable_rate' not in data:
        raise ValidationError("'billable_rate' is required")
    
    billable_rate = data['billable_rate']
    validate_positive_number(billable_rate, 'billable_rate')
    
    # Check if rate exists
    rate = ProjectRoleRate.query.filter_by(
        project_id=project_id, role_id=role_id
    ).first()
    
    if rate:
        rate.billable_rate = billable_rate
    else:
        rate = ProjectRoleRate(
            project_id=project_id,
            role_id=role_id,
            billable_rate=billable_rate
        )
        db.session.add(rate)
    
    safe_db_operation(db.session.commit, "Failed to update project role rate")
    
    return jsonify(rate.to_dict())

@api.route('/projects/<int:project_id>/role-rates/<int:role_id>', methods=['DELETE'])
@handle_errors
@require_permission('write')
def delete_project_role_rate(project_id, role_id):
    """Delete a role rate for a project (reverts to parent rate if available)"""
    db, Project, ProjectRoleRate, Role = get_project_models()

    project = db.session.get(Project, project_id)
    if not project:
        raise NotFoundError("Project", project_id)

    rate = ProjectRoleRate.query.filter_by(
        project_id=project_id, role_id=role_id
    ).first()
    
    if not rate:
        raise NotFoundError("ProjectRoleRate", f"project_id={project_id}, role_id={role_id}")
    
    safe_db_operation(lambda: (db.session.delete(rate), db.session.commit())[1], "Failed to delete project role rate")
    
    # Return info about inherited rate if available
    inherited_rate = project.get_role_rate(role_id)
    
    return jsonify({
        'message': 'Role rate deleted successfully',
        'inherited_rate': inherited_rate
    })

# ASSIGNMENT ENDPOINTS

@api.route('/assignments', methods=['GET'])
@handle_errors
def get_assignments():
    """Get all assignments with optional filtering"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

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
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    data = request.get_json()

    validate_assignment_data(data, db, Staff, Project)

    # Convert date strings to date objects
    start_date = datetime.fromisoformat(data['start_date']).date()
    end_date = datetime.fromisoformat(data['end_date']).date()

    assignment = Assignment(
        staff_id=data['staff_id'],
        project_id=data['project_id'],
        start_date=start_date,
        end_date=end_date,
        hours_per_week=data['hours_per_week'],
        role_on_project=data.get('role_on_project'),
        allocation_type=data.get('allocation_type', 'full'),
        allocation_percentage=data.get('allocation_percentage', 100.0)
    )

    safe_db_operation(lambda: (db.session.add(assignment), db.session.commit())[1], "Failed to create assignment")
    
    # Handle monthly allocations if provided and type is percentage_monthly
    if data.get('allocation_type') == 'percentage_monthly' and data.get('monthly_allocations'):
        for ma_data in data['monthly_allocations']:
            month_date = datetime.fromisoformat(ma_data['month']).date()
            monthly_allocation = AssignmentMonthlyAllocation(
                assignment_id=assignment.id,
                month=month_date,
                allocation_percentage=ma_data.get('allocation_percentage', 100.0)
            )
            db.session.add(monthly_allocation)
        safe_db_operation(db.session.commit, "Failed to save monthly allocations")

    return jsonify(assignment.to_dict(include_monthly_allocations=True)), 201

@api.route('/assignments/<int:assignment_id>', methods=['GET'])
@handle_errors
def get_assignment_by_id(assignment_id):
    """Get a specific assignment by ID"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    assignment = db.session.get(Assignment, assignment_id)
    if not assignment:
        raise NotFoundError("Assignment", assignment_id)

    include_monthly = request.args.get('include_monthly_allocations', 'true').lower() == 'true'
    return jsonify(assignment.to_dict(include_monthly_allocations=include_monthly))

@api.route('/assignments/<int:assignment_id>', methods=['PUT'])
@handle_errors
def update_assignment(assignment_id):
    """Update an assignment"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    assignment = db.session.get(Assignment, assignment_id)
    if not assignment:
        raise NotFoundError("Assignment", assignment_id)

    data = request.get_json()

    validate_assignment_data(data, db, Staff, Project)

    # Update fields
    assignment.staff_id = data['staff_id']
    assignment.project_id = data['project_id']
    assignment.start_date = datetime.fromisoformat(data['start_date']).date()
    assignment.end_date = datetime.fromisoformat(data['end_date']).date()
    assignment.hours_per_week = data['hours_per_week']
    assignment.role_on_project = data.get('role_on_project')
    
    # Update allocation fields
    if 'allocation_type' in data:
        assignment.allocation_type = data['allocation_type']
    if 'allocation_percentage' in data:
        assignment.allocation_percentage = data['allocation_percentage']

    safe_db_operation(db.session.commit, "Failed to update assignment")

    return jsonify(assignment.to_dict(include_monthly_allocations=True))

@api.route('/assignments/<int:assignment_id>', methods=['DELETE'])
@handle_errors
def delete_assignment(assignment_id):
    """Delete an assignment"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    assignment = db.session.get(Assignment, assignment_id)
    if not assignment:
        raise NotFoundError("Assignment", assignment_id)

    safe_db_operation(lambda: (db.session.delete(assignment), db.session.commit())[1], "Failed to delete assignment")

    return jsonify({'message': 'Assignment deleted successfully'})


# ASSIGNMENT MONTHLY ALLOCATION ENDPOINTS

@api.route('/assignments/<int:assignment_id>/monthly-allocations', methods=['GET'])
@handle_errors
def get_assignment_monthly_allocations(assignment_id):
    """Get monthly allocations for an assignment"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    assignment = db.session.get(Assignment, assignment_id)
    if not assignment:
        raise NotFoundError("Assignment", assignment_id)

    # Generate month range for the assignment
    from dateutil.relativedelta import relativedelta
    from datetime import date
    
    months = []
    current_month = date(assignment.start_date.year, assignment.start_date.month, 1)
    end_month = date(assignment.end_date.year, assignment.end_date.month, 1)
    
    while current_month <= end_month:
        # Find existing allocation for this month
        existing = next(
            (ma for ma in assignment.monthly_allocations 
             if ma.month.year == current_month.year and ma.month.month == current_month.month),
            None
        )
        
        months.append({
            'month': current_month.isoformat(),
            'allocation_percentage': existing.allocation_percentage if existing else 100.0,
            'id': existing.id if existing else None
        })
        
        current_month = current_month + relativedelta(months=1)

    return jsonify({
        'assignment_id': assignment_id,
        'allocation_type': assignment.allocation_type,
        'months': months
    })


@api.route('/assignments/<int:assignment_id>/monthly-allocations', methods=['PUT'])
@handle_errors
def update_assignment_monthly_allocations(assignment_id):
    """Update monthly allocations for an assignment"""
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()

    assignment = db.session.get(Assignment, assignment_id)
    if not assignment:
        raise NotFoundError("Assignment", assignment_id)

    data = request.get_json()
    
    if not data or 'allocations' not in data:
        raise ValidationError("'allocations' array is required")

    # Set allocation type to percentage_monthly if updating monthly allocations
    assignment.allocation_type = 'percentage_monthly'
    
    # Process each allocation
    for alloc_data in data['allocations']:
        if 'month' not in alloc_data:
            raise ValidationError("Each allocation must have a 'month' field")
        
        month_date = datetime.fromisoformat(alloc_data['month']).date()
        # Normalize to first of month
        month_date = month_date.replace(day=1)
        
        allocation_pct = alloc_data.get('allocation_percentage', 100.0)
        if not isinstance(allocation_pct, (int, float)) or allocation_pct < 0 or allocation_pct > 100:
            raise ValidationError(f"allocation_percentage for {month_date} must be between 0 and 100")
        
        # Find existing or create new
        existing = AssignmentMonthlyAllocation.query.filter_by(
            assignment_id=assignment_id,
            month=month_date
        ).first()
        
        if existing:
            existing.allocation_percentage = allocation_pct
        else:
            new_allocation = AssignmentMonthlyAllocation(
                assignment_id=assignment_id,
                month=month_date,
                allocation_percentage=allocation_pct
            )
            db.session.add(new_allocation)

    safe_db_operation(db.session.commit, "Failed to update monthly allocations")

    return jsonify(assignment.to_dict(include_monthly_allocations=True))


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
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()
    from models import User

    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200


@api.route('/users/<int:user_id>', methods=['GET'])
@handle_errors
@require_role('admin')
def get_user(user_id):
    """Get specific user (admin only)"""
    from models import User
    from db import db

    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError("User", user_id)

    return jsonify(user.to_dict()), 200


@api.route('/users/<int:user_id>', methods=['PUT'])
@handle_errors
@require_role('admin')
def update_user(user_id):
    """Update user (admin only)"""
    from models import User
    from db import db

    user = db.session.get(User, user_id)
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
    db, Staff, Project, Assignment, Role, ProjectRoleRate, AssignmentMonthlyAllocation = get_models()
    from models import User

    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError("User", user_id)

    # Prevent deleting the last admin
    admin_count = User.query.filter_by(role='admin').count()
    if user.role == 'admin' and admin_count <= 1:
        raise ConflictError("Cannot delete the last admin user")

    safe_db_operation(lambda: (db.session.delete(user), db.session.commit())[1], "Failed to delete user")

    return jsonify({'message': 'User deleted successfully'}), 200


# TEMPLATE ENDPOINTS

def get_template_models():
    """Import template-related models"""
    from db import db
    from models import ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate
    return db, ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate


@api.route('/templates', methods=['GET'])
@handle_errors
def get_templates():
    """Get all project templates"""
    db, ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate = get_template_models()
    
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    
    query = ProjectTemplate.query
    if active_only:
        query = query.filter_by(is_active=True)
    
    templates = query.order_by(ProjectTemplate.name).all()
    return jsonify([t.to_dict(include_roles=True) for t in templates])


@api.route('/templates', methods=['POST'])
@handle_errors
def create_template():
    """Create a new project template"""
    db, ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate = get_template_models()
    
    data = request.get_json()
    
    validate_required(data, ['name', 'duration_months'])
    validate_positive_number(data['duration_months'], 'duration_months')
    
    template = ProjectTemplate(
        name=data['name'],
        duration_months=data['duration_months'],
        description=data.get('description'),
        project_type=data.get('project_type'),
        is_active=data.get('is_active', True)
    )
    
    safe_db_operation(lambda: (db.session.add(template), db.session.commit())[1], "Failed to create template")
    
    # Add roles if provided
    if 'roles' in data and data['roles']:
        for role_data in data['roles']:
            validate_required(role_data, ['role_id', 'count', 'start_month'])
            
            # Validate role exists
            role = db.session.get(Role, role_data['role_id'])
            if not role:
                raise NotFoundError("Role", role_data['role_id'])
            
            # Validate months are within duration
            if role_data['start_month'] < 1 or role_data['start_month'] > template.duration_months:
                raise ValidationError(f"start_month must be between 1 and {template.duration_months}")
            
            end_month = role_data.get('end_month')
            if end_month and (end_month < role_data['start_month'] or end_month > template.duration_months):
                raise ValidationError(f"end_month must be between start_month and {template.duration_months}")
            
            template_role = TemplateRole(
                template_id=template.id,
                role_id=role_data['role_id'],
                count=role_data['count'],
                start_month=role_data['start_month'],
                end_month=end_month,
                hours_per_week=role_data.get('hours_per_week', 40.0)
            )
            db.session.add(template_role)
        
        safe_db_operation(db.session.commit, "Failed to add template roles")
    
    return jsonify(template.to_dict(include_roles=True)), 201


@api.route('/templates/<int:template_id>', methods=['GET'])
@handle_errors
def get_template(template_id):
    """Get a specific template by ID"""
    db, ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate = get_template_models()
    
    template = db.session.get(ProjectTemplate, template_id)
    if not template:
        raise NotFoundError("Template", template_id)
    
    return jsonify(template.to_dict(include_roles=True))


@api.route('/templates/<int:template_id>', methods=['PUT'])
@handle_errors
def update_template(template_id):
    """Update a project template"""
    db, ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate = get_template_models()
    
    template = db.session.get(ProjectTemplate, template_id)
    if not template:
        raise NotFoundError("Template", template_id)
    
    data = request.get_json()
    
    # Update basic fields
    if 'name' in data:
        template.name = data['name']
    if 'description' in data:
        template.description = data['description']
    if 'project_type' in data:
        template.project_type = data['project_type']
    if 'duration_months' in data:
        validate_positive_number(data['duration_months'], 'duration_months')
        template.duration_months = data['duration_months']
    if 'is_active' in data:
        template.is_active = data['is_active']
    
    # Update roles if provided (replace all)
    if 'roles' in data:
        # Remove existing roles
        TemplateRole.query.filter_by(template_id=template_id).delete()
        
        # Add new roles
        for role_data in data['roles']:
            validate_required(role_data, ['role_id', 'count', 'start_month'])
            
            role = db.session.get(Role, role_data['role_id'])
            if not role:
                raise NotFoundError("Role", role_data['role_id'])
            
            if role_data['start_month'] < 1 or role_data['start_month'] > template.duration_months:
                raise ValidationError(f"start_month must be between 1 and {template.duration_months}")
            
            end_month = role_data.get('end_month')
            if end_month and (end_month < role_data['start_month'] or end_month > template.duration_months):
                raise ValidationError(f"end_month must be between start_month and {template.duration_months}")
            
            template_role = TemplateRole(
                template_id=template.id,
                role_id=role_data['role_id'],
                count=role_data['count'],
                start_month=role_data['start_month'],
                end_month=end_month,
                hours_per_week=role_data.get('hours_per_week', 40.0)
            )
            db.session.add(template_role)
    
    safe_db_operation(db.session.commit, "Failed to update template")
    
    return jsonify(template.to_dict(include_roles=True))


@api.route('/templates/<int:template_id>', methods=['DELETE'])
@handle_errors
def delete_template(template_id):
    """Delete a project template"""
    db, ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate = get_template_models()
    
    template = db.session.get(ProjectTemplate, template_id)
    if not template:
        raise NotFoundError("Template", template_id)
    
    safe_db_operation(lambda: (db.session.delete(template), db.session.commit())[1], "Failed to delete template")
    
    return jsonify({'message': 'Template deleted successfully'})


@api.route('/projects/from-template', methods=['POST'])
@handle_errors
def create_project_from_template():
    """Create a project from a template with ghost staff"""
    from dateutil.relativedelta import relativedelta
    db, ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate = get_template_models()
    
    data = request.get_json()
    
    validate_required(data, ['template_id', 'name', 'start_date'])
    
    # Get template
    template = db.session.get(ProjectTemplate, data['template_id'])
    if not template:
        raise NotFoundError("Template", data['template_id'])
    
    # Parse start date
    start_date = datetime.fromisoformat(data['start_date']).date()
    
    # Calculate end date from template duration
    end_date = start_date + relativedelta(months=template.duration_months)
    
    # Create the project
    project = Project(
        name=data['name'],
        start_date=start_date,
        end_date=end_date,
        status=data.get('status', 'planning'),
        budget=data.get('budget'),
        location=data.get('location'),
        parent_project_id=data.get('parent_project_id'),
        is_folder=data.get('is_folder', False)
    )
    
    safe_db_operation(lambda: (db.session.add(project), db.session.commit())[1], "Failed to create project")
    
    # Auto-populate role rates from active roles
    active_roles = Role.query.filter_by(is_active=True).all()
    for role in active_roles:
        if role.default_billable_rate is not None:
            rate = ProjectRoleRate(
                project_id=project.id,
                role_id=role.id,
                billable_rate=role.default_billable_rate
            )
            db.session.add(rate)
    
    safe_db_operation(db.session.commit, "Failed to create project role rates")
    
    # Create ghost staff from template roles
    ghost_staff_created = []
    for template_role in template.template_roles:
        role = template_role.role
        
        # Calculate ghost start/end dates
        ghost_start = start_date + relativedelta(months=template_role.start_month - 1)
        if template_role.end_month:
            ghost_end = start_date + relativedelta(months=template_role.end_month)
        else:
            ghost_end = end_date
        
        # Get billable rate from project or role default
        rate_info = project.get_role_rate(role.id)
        billable_rate = rate_info['rate'] if rate_info else role.default_billable_rate
        
        # Create ghost staff for each count
        for i in range(template_role.count):
            ghost_name = f"{role.name} Placeholder {i + 1}"
            
            ghost = GhostStaff(
                project_id=project.id,
                role_id=role.id,
                name=ghost_name,
                internal_hourly_cost=role.hourly_cost,
                billable_rate=billable_rate,
                start_date=ghost_start,
                end_date=ghost_end,
                hours_per_week=template_role.hours_per_week
            )
            db.session.add(ghost)
            ghost_staff_created.append(ghost)
    
    safe_db_operation(db.session.commit, "Failed to create ghost staff")
    
    return jsonify({
        'project': project.to_dict(include_children=True),
        'ghost_staff': [g.to_dict() for g in ghost_staff_created],
        'template_used': template.to_dict(include_roles=False)
    }), 201


# GHOST STAFF ENDPOINTS

@api.route('/projects/<int:project_id>/ghost-staff', methods=['GET'])
@handle_errors
def get_project_ghost_staff(project_id):
    """Get ghost staff for a project"""
    db, ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate = get_template_models()
    
    project = db.session.get(Project, project_id)
    if not project:
        raise NotFoundError("Project", project_id)
    
    include_replaced = request.args.get('include_replaced', 'false').lower() == 'true'
    
    query = GhostStaff.query.filter_by(project_id=project_id)
    if not include_replaced:
        query = query.filter(GhostStaff.replaced_by_staff_id.is_(None))
    
    ghost_staff = query.all()
    
    return jsonify({
        'project_id': project_id,
        'project_name': project.name,
        'ghost_staff': [g.to_dict() for g in ghost_staff],
        'total_count': len(ghost_staff),
        'replaced_count': sum(1 for g in ghost_staff if g.is_replaced)
    })


@api.route('/ghost-staff/<int:ghost_id>', methods=['GET'])
@handle_errors
def get_ghost_staff(ghost_id):
    """Get a specific ghost staff member"""
    db, ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate = get_template_models()
    
    ghost = db.session.get(GhostStaff, ghost_id)
    if not ghost:
        raise NotFoundError("GhostStaff", ghost_id)
    
    return jsonify(ghost.to_dict())


@api.route('/ghost-staff/<int:ghost_id>/replace', methods=['PUT'])
@handle_errors
def replace_ghost_staff(ghost_id):
    """Replace a ghost staff member with a real staff member"""
    from models import Staff, Assignment
    db, ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate = get_template_models()
    
    ghost = db.session.get(GhostStaff, ghost_id)
    if not ghost:
        raise NotFoundError("GhostStaff", ghost_id)
    
    if ghost.is_replaced:
        raise ConflictError(f"Ghost staff '{ghost.name}' has already been replaced")
    
    data = request.get_json()
    validate_required(data, ['staff_id'])
    
    staff = db.session.get(Staff, data['staff_id'])
    if not staff:
        raise NotFoundError("Staff", data['staff_id'])
    
    # Mark ghost as replaced
    ghost.replaced_by_staff_id = staff.id
    
    # Create a real assignment for the staff member
    assignment = Assignment(
        staff_id=staff.id,
        project_id=ghost.project_id,
        start_date=ghost.start_date,
        end_date=ghost.end_date,
        hours_per_week=ghost.hours_per_week,
        role_on_project=ghost.role.name if ghost.role else None,
        allocation_type='full',
        allocation_percentage=100.0
    )
    db.session.add(assignment)
    
    safe_db_operation(db.session.commit, "Failed to replace ghost staff")
    
    return jsonify({
        'message': f"Ghost staff '{ghost.name}' replaced with '{staff.name}'",
        'ghost_staff': ghost.to_dict(),
        'assignment': assignment.to_dict()
    })


@api.route('/ghost-staff/<int:ghost_id>', methods=['DELETE'])
@handle_errors
def delete_ghost_staff(ghost_id):
    """Delete a ghost staff member"""
    db, ProjectTemplate, TemplateRole, Role, Project, GhostStaff, ProjectRoleRate = get_template_models()
    
    ghost = db.session.get(GhostStaff, ghost_id)
    if not ghost:
        raise NotFoundError("GhostStaff", ghost_id)
    
    safe_db_operation(lambda: (db.session.delete(ghost), db.session.commit())[1], "Failed to delete ghost staff")
    
    return jsonify({'message': 'Ghost staff deleted successfully'})


# REPORTS ENDPOINTS

@api.route('/reports/staff-planning', methods=['GET'])
@handle_errors
def get_staff_planning_report():
    """
    Generate a staff planning report for a project or project folder.
    Includes monthly cost breakdowns, role distributions, and staff/ghost staff entries.
    
    Query Parameters:
        project_id (required): ID of the project or project folder
        start_date (optional): Report start date (YYYY-MM-DD)
        end_date (optional): Report end date (YYYY-MM-DD)
        include_sub_projects (optional, default 'true'): Whether to include sub-projects for folders
    """
    from engine import generate_staff_planning_report
    
    project_id = request.args.get('project_id', type=int)
    if not project_id:
        raise ValidationError("project_id parameter is required")
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    include_sub_projects = request.args.get('include_sub_projects', 'true').lower() == 'true'
    
    # Parse dates if provided
    parsed_start = None
    parsed_end = None
    
    if start_date:
        try:
            parsed_start = datetime.fromisoformat(start_date).date()
        except ValueError:
            raise ValidationError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD")
    
    if end_date:
        try:
            parsed_end = datetime.fromisoformat(end_date).date()
        except ValueError:
            raise ValidationError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD")
    
    # Validate date range
    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise ValidationError("start_date must be before end_date")
    
    try:
        report = generate_staff_planning_report(
            project_id=project_id,
            start_date=parsed_start,
            end_date=parsed_end,
            include_sub_projects=include_sub_projects
        )
        return jsonify(report)
    except ValueError as e:
        raise ValidationError(str(e))


# =============================================================================
# STAFF AVAILABILITY AND SUGGESTION ENDPOINTS
# =============================================================================

@api.route('/forecasts/staff-availability', methods=['GET'])
@handle_errors
def get_staff_availability():
    """
    Get staff availability forecast for a given role and date range.
    
    Query Parameters:
        role_id (optional): Filter by role ID
        start_date (optional): Start date (YYYY-MM-DD), defaults to today
        end_date (optional): End date (YYYY-MM-DD), defaults to 90 days from start
    """
    from engine import get_staff_availability_forecast
    
    role_id = request.args.get('role_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Parse dates
    parsed_start = None
    parsed_end = None
    
    if start_date:
        try:
            parsed_start = datetime.fromisoformat(start_date).date()
        except ValueError:
            raise ValidationError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD")
    
    if end_date:
        try:
            parsed_end = datetime.fromisoformat(end_date).date()
        except ValueError:
            raise ValidationError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD")
    
    result = get_staff_availability_forecast(
        role_id=role_id,
        start_date=parsed_start,
        end_date=parsed_end
    )
    return jsonify(result)


@api.route('/forecasts/suggestions', methods=['GET'])
@handle_errors
def get_staff_suggestions():
    """
    Get staff suggestions for a role based on availability and assignment alignment.
    
    Query Parameters:
        role_id (required): ID of the role to fill
        start_date (required): Start date of the role (YYYY-MM-DD)
        end_date (required): End date of the role (YYYY-MM-DD)
        allocation_percentage (optional): Required allocation (default 100)
        max_suggestions (optional): Maximum suggestions to return (default 10)
    """
    from engine import suggest_staff_for_role
    
    role_id = request.args.get('role_id', type=int)
    if not role_id:
        raise ValidationError("role_id parameter is required")
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        raise ValidationError("start_date and end_date parameters are required")
    
    try:
        parsed_start = datetime.fromisoformat(start_date).date()
        parsed_end = datetime.fromisoformat(end_date).date()
    except ValueError:
        raise ValidationError("Invalid date format. Use YYYY-MM-DD")
    
    allocation_percentage = request.args.get('allocation_percentage', type=float, default=100.0)
    max_suggestions = request.args.get('max_suggestions', type=int, default=10)
    
    try:
        result = suggest_staff_for_role(
            role_id=role_id,
            start_date=parsed_start,
            end_date=parsed_end,
            allocation_percentage=allocation_percentage,
            max_suggestions=max_suggestions
        )
        return jsonify(result)
    except ValueError as e:
        raise ValidationError(str(e))


@api.route('/forecasts/new-hire-needs', methods=['GET'])
@handle_errors
def get_new_hire_needs():
    """
    Identify positions requiring new hires.
    
    Query Parameters:
        role_id (required): ID of the role to check
        start_date (required): Start date of the requirement (YYYY-MM-DD)
        end_date (required): End date of the requirement (YYYY-MM-DD)
        required_count (optional): Number of staff needed (default 1)
        allocation_percentage (optional): Required allocation per person (default 100)
    """
    from engine import flag_new_hire_needs
    
    role_id = request.args.get('role_id', type=int)
    if not role_id:
        raise ValidationError("role_id parameter is required")
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        raise ValidationError("start_date and end_date parameters are required")
    
    try:
        parsed_start = datetime.fromisoformat(start_date).date()
        parsed_end = datetime.fromisoformat(end_date).date()
    except ValueError:
        raise ValidationError("Invalid date format. Use YYYY-MM-DD")
    
    required_count = request.args.get('required_count', type=int, default=1)
    allocation_percentage = request.args.get('allocation_percentage', type=float, default=100.0)
    
    try:
        result = flag_new_hire_needs(
            role_id=role_id,
            start_date=parsed_start,
            end_date=parsed_end,
            required_count=required_count,
            allocation_percentage=allocation_percentage
        )
        return jsonify(result)
    except ValueError as e:
        raise ValidationError(str(e))


# =============================================================================
# OVER-ALLOCATION DETECTION ENDPOINTS
# =============================================================================

@api.route('/staff/<int:staff_id>/allocation-conflicts', methods=['GET'])
@handle_errors
def get_staff_allocation_conflicts(staff_id):
    """
    Detect over-allocation conflicts for a staff member.
    
    Query Parameters:
        start_date (required): Start date (YYYY-MM-DD)
        end_date (required): End date (YYYY-MM-DD)
    """
    from engine import detect_over_allocations
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        raise ValidationError("start_date and end_date parameters are required")
    
    try:
        parsed_start = datetime.fromisoformat(start_date).date()
        parsed_end = datetime.fromisoformat(end_date).date()
    except ValueError:
        raise ValidationError("Invalid date format. Use YYYY-MM-DD")
    
    try:
        result = detect_over_allocations(staff_id, parsed_start, parsed_end)
        return jsonify(result)
    except ValueError as e:
        raise ValidationError(str(e))


@api.route('/staff/<int:staff_id>/allocation-timeline', methods=['GET'])
@handle_errors
def get_staff_allocation_timeline(staff_id):
    """
    Get detailed monthly allocation timeline for a staff member.
    
    Query Parameters:
        start_date (required): Start date (YYYY-MM-DD)
        end_date (required): End date (YYYY-MM-DD)
    """
    from engine import get_staff_allocation_timeline as get_timeline
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        raise ValidationError("start_date and end_date parameters are required")
    
    try:
        parsed_start = datetime.fromisoformat(start_date).date()
        parsed_end = datetime.fromisoformat(end_date).date()
    except ValueError:
        raise ValidationError("Invalid date format. Use YYYY-MM-DD")
    
    try:
        result = get_timeline(staff_id, parsed_start, parsed_end)
        return jsonify(result)
    except ValueError as e:
        raise ValidationError(str(e))


@api.route('/organization/over-allocations', methods=['GET'])
@handle_errors
def get_organization_over_allocations_endpoint():
    """
    Get organization-wide over-allocation summary.
    
    Query Parameters:
        start_date (required): Start date (YYYY-MM-DD)
        end_date (required): End date (YYYY-MM-DD)
    """
    from engine import get_organization_over_allocations
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        raise ValidationError("start_date and end_date parameters are required")
    
    try:
        parsed_start = datetime.fromisoformat(start_date).date()
        parsed_end = datetime.fromisoformat(end_date).date()
    except ValueError:
        raise ValidationError("Invalid date format. Use YYYY-MM-DD")
    
    result = get_organization_over_allocations(parsed_start, parsed_end)
    return jsonify(result)


@api.route('/assignments/validate-allocation', methods=['POST'])
@handle_errors
def validate_assignment_allocation_endpoint():
    """
    Pre-validate a proposed assignment for over-allocation conflicts.
    
    Request Body:
        staff_id (required): ID of the staff member
        start_date (required): Proposed start date (YYYY-MM-DD)
        end_date (required): Proposed end date (YYYY-MM-DD)
        allocation_percentage (required): Proposed allocation percentage
        exclude_assignment_id (optional): Assignment ID to exclude (for updates)
    """
    from engine import validate_assignment_allocation
    
    data = request.get_json()
    
    validate_required(data, ['staff_id', 'start_date', 'end_date', 'allocation_percentage'])
    
    try:
        result = validate_assignment_allocation(
            staff_id=data['staff_id'],
            new_start_date=data['start_date'],
            new_end_date=data['end_date'],
            new_allocation_percentage=data['allocation_percentage'],
            exclude_assignment_id=data.get('exclude_assignment_id')
        )
        return jsonify(result)
    except ValueError as e:
        raise ValidationError(str(e))


# =============================================================================
# PLANNING EXERCISE ENDPOINTS
# =============================================================================

def get_planning_models():
    """Import planning-related models"""
    from db import db
    from models import PlanningExercise, PlanningProject, PlanningRole, Role
    return db, PlanningExercise, PlanningProject, PlanningRole, Role


@api.route('/planning-exercises', methods=['GET'])
@handle_errors
def get_planning_exercises():
    """Get all planning exercises with optional filtering"""
    db, PlanningExercise, PlanningProject, PlanningRole, Role = get_planning_models()
    
    status = request.args.get('status')
    include_projects = request.args.get('include_projects', 'true').lower() == 'true'
    
    query = PlanningExercise.query
    
    if status:
        query = query.filter(PlanningExercise.status == status)
    
    exercises = query.order_by(PlanningExercise.updated_at.desc()).all()
    
    return jsonify([e.to_dict(include_projects=include_projects) for e in exercises])


@api.route('/planning-exercises', methods=['POST'])
@handle_errors
def create_planning_exercise():
    """Create a new planning exercise with optional projects"""
    db, PlanningExercise, PlanningProject, PlanningRole, Role = get_planning_models()
    
    data = request.get_json()
    
    validate_required(data, ['name'])
    
    # Validate status if provided
    if 'status' in data and data['status'] not in PlanningExercise.STATUSES:
        raise ValidationError(f"Invalid status. Must be one of: {', '.join(PlanningExercise.STATUSES)}")
    
    exercise = PlanningExercise(
        name=data['name'],
        description=data.get('description'),
        status=data.get('status', 'draft'),
        created_by=data.get('created_by')
    )
    
    safe_db_operation(lambda: (db.session.add(exercise), db.session.commit())[1], "Failed to create planning exercise")
    
    # Create projects if provided
    if 'projects' in data and data['projects']:
        for project_data in data['projects']:
            validate_required(project_data, ['name', 'start_date', 'duration_months'])
            
            # Parse start date
            try:
                start_date = datetime.fromisoformat(project_data['start_date']).date()
            except ValueError:
                raise ValidationError(f"Invalid start_date format: {project_data['start_date']}")
            
            planning_project = PlanningProject(
                exercise_id=exercise.id,
                name=project_data['name'],
                start_date=start_date,
                duration_months=project_data['duration_months'],
                location=project_data.get('location'),
                budget=project_data.get('budget')
            )
            db.session.add(planning_project)
            db.session.flush()  # Get project ID for roles
            
            # Create roles if provided
            if 'roles' in project_data and project_data['roles']:
                for role_data in project_data['roles']:
                    validate_required(role_data, ['role_id', 'count'])
                    
                    # Validate role exists
                    role = db.session.get(Role, role_data['role_id'])
                    if not role:
                        raise NotFoundError("Role", role_data['role_id'])
                    
                    # Validate overlap_mode if provided
                    overlap_mode = role_data.get('overlap_mode', 'efficient')
                    if overlap_mode not in PlanningRole.OVERLAP_MODES:
                        raise ValidationError(f"Invalid overlap_mode. Must be one of: {', '.join(PlanningRole.OVERLAP_MODES)}")
                    
                    planning_role = PlanningRole(
                        planning_project_id=planning_project.id,
                        role_id=role_data['role_id'],
                        count=role_data['count'],
                        start_month_offset=role_data.get('start_month_offset', 0),
                        end_month_offset=role_data.get('end_month_offset'),
                        allocation_percentage=role_data.get('allocation_percentage', 100.0),
                        hours_per_week=role_data.get('hours_per_week', 40.0),
                        overlap_mode=overlap_mode
                    )
                    db.session.add(planning_role)
        
        safe_db_operation(db.session.commit, "Failed to create planning projects and roles")
    
    return jsonify(exercise.to_dict(include_projects=True)), 201


@api.route('/planning-exercises/<int:exercise_id>', methods=['GET'])
@handle_errors
def get_planning_exercise(exercise_id):
    """Get a specific planning exercise by ID"""
    db, PlanningExercise, PlanningProject, PlanningRole, Role = get_planning_models()
    
    exercise = db.session.get(PlanningExercise, exercise_id)
    if not exercise:
        raise NotFoundError("PlanningExercise", exercise_id)
    
    return jsonify(exercise.to_dict(include_projects=True))


@api.route('/planning-exercises/<int:exercise_id>', methods=['PUT'])
@handle_errors
def update_planning_exercise(exercise_id):
    """Update a planning exercise"""
    db, PlanningExercise, PlanningProject, PlanningRole, Role = get_planning_models()
    
    exercise = db.session.get(PlanningExercise, exercise_id)
    if not exercise:
        raise NotFoundError("PlanningExercise", exercise_id)
    
    data = request.get_json()
    
    # Update basic fields
    if 'name' in data:
        exercise.name = data['name']
    if 'description' in data:
        exercise.description = data['description']
    if 'status' in data:
        if data['status'] not in PlanningExercise.STATUSES:
            raise ValidationError(f"Invalid status. Must be one of: {', '.join(PlanningExercise.STATUSES)}")
        exercise.status = data['status']
    
    safe_db_operation(db.session.commit, "Failed to update planning exercise")
    
    return jsonify(exercise.to_dict(include_projects=True))


@api.route('/planning-exercises/<int:exercise_id>', methods=['DELETE'])
@handle_errors
def delete_planning_exercise(exercise_id):
    """Delete a planning exercise"""
    db, PlanningExercise, PlanningProject, PlanningRole, Role = get_planning_models()
    
    exercise = db.session.get(PlanningExercise, exercise_id)
    if not exercise:
        raise NotFoundError("PlanningExercise", exercise_id)
    
    safe_db_operation(lambda: (db.session.delete(exercise), db.session.commit())[1], "Failed to delete planning exercise")
    
    return jsonify({'message': 'Planning exercise deleted successfully'})


# Planning Project endpoints

@api.route('/planning-exercises/<int:exercise_id>/projects', methods=['POST'])
@handle_errors
def create_planning_project(exercise_id):
    """Add a project to a planning exercise"""
    db, PlanningExercise, PlanningProject, PlanningRole, Role = get_planning_models()
    
    exercise = db.session.get(PlanningExercise, exercise_id)
    if not exercise:
        raise NotFoundError("PlanningExercise", exercise_id)
    
    data = request.get_json()
    validate_required(data, ['name', 'start_date', 'duration_months'])
    
    # Parse start date
    try:
        start_date = datetime.fromisoformat(data['start_date']).date()
    except ValueError:
        raise ValidationError(f"Invalid start_date format: {data['start_date']}")
    
    planning_project = PlanningProject(
        exercise_id=exercise_id,
        name=data['name'],
        start_date=start_date,
        duration_months=data['duration_months'],
        location=data.get('location'),
        budget=data.get('budget')
    )
    
    safe_db_operation(lambda: (db.session.add(planning_project), db.session.commit())[1], "Failed to create planning project")
    
    # Create roles if provided
    if 'roles' in data and data['roles']:
        for role_data in data['roles']:
            validate_required(role_data, ['role_id', 'count'])
            
            role = db.session.get(Role, role_data['role_id'])
            if not role:
                raise NotFoundError("Role", role_data['role_id'])
            
            overlap_mode = role_data.get('overlap_mode', 'efficient')
            if overlap_mode not in PlanningRole.OVERLAP_MODES:
                raise ValidationError(f"Invalid overlap_mode. Must be one of: {', '.join(PlanningRole.OVERLAP_MODES)}")
            
            planning_role = PlanningRole(
                planning_project_id=planning_project.id,
                role_id=role_data['role_id'],
                count=role_data['count'],
                start_month_offset=role_data.get('start_month_offset', 0),
                end_month_offset=role_data.get('end_month_offset'),
                allocation_percentage=role_data.get('allocation_percentage', 100.0),
                hours_per_week=role_data.get('hours_per_week', 40.0),
                overlap_mode=overlap_mode
            )
            db.session.add(planning_role)
        
        safe_db_operation(db.session.commit, "Failed to create planning roles")
    
    return jsonify(planning_project.to_dict(include_roles=True)), 201


@api.route('/planning-projects/<int:project_id>', methods=['PUT'])
@handle_errors
def update_planning_project(project_id):
    """Update a planning project"""
    db, PlanningExercise, PlanningProject, PlanningRole, Role = get_planning_models()
    
    planning_project = db.session.get(PlanningProject, project_id)
    if not planning_project:
        raise NotFoundError("PlanningProject", project_id)
    
    data = request.get_json()
    
    # Update fields
    if 'name' in data:
        planning_project.name = data['name']
    if 'start_date' in data:
        try:
            planning_project.start_date = datetime.fromisoformat(data['start_date']).date()
        except ValueError:
            raise ValidationError(f"Invalid start_date format: {data['start_date']}")
    if 'duration_months' in data:
        planning_project.duration_months = data['duration_months']
    if 'location' in data:
        planning_project.location = data['location']
    if 'budget' in data:
        planning_project.budget = data['budget']
    
    safe_db_operation(db.session.commit, "Failed to update planning project")
    
    return jsonify(planning_project.to_dict(include_roles=True))


@api.route('/planning-projects/<int:project_id>', methods=['DELETE'])
@handle_errors
def delete_planning_project(project_id):
    """Delete a planning project"""
    db, PlanningExercise, PlanningProject, PlanningRole, Role = get_planning_models()
    
    planning_project = db.session.get(PlanningProject, project_id)
    if not planning_project:
        raise NotFoundError("PlanningProject", project_id)
    
    safe_db_operation(lambda: (db.session.delete(planning_project), db.session.commit())[1], "Failed to delete planning project")
    
    return jsonify({'message': 'Planning project deleted successfully'})


# Planning Role endpoints

@api.route('/planning-projects/<int:project_id>/roles', methods=['POST'])
@handle_errors
def create_planning_role(project_id):
    """Add a role to a planning project"""
    db, PlanningExercise, PlanningProject, PlanningRole, Role = get_planning_models()
    
    planning_project = db.session.get(PlanningProject, project_id)
    if not planning_project:
        raise NotFoundError("PlanningProject", project_id)
    
    data = request.get_json()
    validate_required(data, ['role_id', 'count'])
    
    role = db.session.get(Role, data['role_id'])
    if not role:
        raise NotFoundError("Role", data['role_id'])
    
    overlap_mode = data.get('overlap_mode', 'efficient')
    if overlap_mode not in PlanningRole.OVERLAP_MODES:
        raise ValidationError(f"Invalid overlap_mode. Must be one of: {', '.join(PlanningRole.OVERLAP_MODES)}")
    
    planning_role = PlanningRole(
        planning_project_id=project_id,
        role_id=data['role_id'],
        count=data['count'],
        start_month_offset=data.get('start_month_offset', 0),
        end_month_offset=data.get('end_month_offset'),
        allocation_percentage=data.get('allocation_percentage', 100.0),
        hours_per_week=data.get('hours_per_week', 40.0),
        overlap_mode=overlap_mode
    )
    
    safe_db_operation(lambda: (db.session.add(planning_role), db.session.commit())[1], "Failed to create planning role")
    
    return jsonify(planning_role.to_dict()), 201


@api.route('/planning-roles/<int:role_id>', methods=['PUT'])
@handle_errors
def update_planning_role(role_id):
    """Update a planning role"""
    db, PlanningExercise, PlanningProject, PlanningRole, Role = get_planning_models()
    
    planning_role = db.session.get(PlanningRole, role_id)
    if not planning_role:
        raise NotFoundError("PlanningRole", role_id)
    
    data = request.get_json()
    
    # Update fields
    if 'role_id' in data:
        role = db.session.get(Role, data['role_id'])
        if not role:
            raise NotFoundError("Role", data['role_id'])
        planning_role.role_id = data['role_id']
    if 'count' in data:
        planning_role.count = data['count']
    if 'start_month_offset' in data:
        planning_role.start_month_offset = data['start_month_offset']
    if 'end_month_offset' in data:
        planning_role.end_month_offset = data['end_month_offset']
    if 'allocation_percentage' in data:
        planning_role.allocation_percentage = data['allocation_percentage']
    if 'hours_per_week' in data:
        planning_role.hours_per_week = data['hours_per_week']
    if 'overlap_mode' in data:
        if data['overlap_mode'] not in PlanningRole.OVERLAP_MODES:
            raise ValidationError(f"Invalid overlap_mode. Must be one of: {', '.join(PlanningRole.OVERLAP_MODES)}")
        planning_role.overlap_mode = data['overlap_mode']
    
    safe_db_operation(db.session.commit, "Failed to update planning role")
    
    return jsonify(planning_role.to_dict())


@api.route('/planning-roles/<int:role_id>', methods=['DELETE'])
@handle_errors
def delete_planning_role(role_id):
    """Delete a planning role"""
    db, PlanningExercise, PlanningProject, PlanningRole, Role = get_planning_models()
    
    planning_role = db.session.get(PlanningRole, role_id)
    if not planning_role:
        raise NotFoundError("PlanningRole", role_id)
    
    safe_db_operation(lambda: (db.session.delete(planning_role), db.session.commit())[1], "Failed to delete planning role")
    
    return jsonify({'message': 'Planning role deleted successfully'})


# Planning Analysis endpoints

@api.route('/planning-exercises/<int:exercise_id>/analysis', methods=['GET'])
@handle_errors
def get_planning_analysis(exercise_id):
    """Get full coverage analysis for a planning exercise"""
    from engine import generate_coverage_analysis
    
    try:
        result = generate_coverage_analysis(exercise_id)
        return jsonify(result)
    except ValueError as e:
        raise ValidationError(str(e))


@api.route('/planning-exercises/<int:exercise_id>/staff-requirements', methods=['GET'])
@handle_errors
def get_planning_staff_requirements(exercise_id):
    """Get minimum staff requirements per role for a planning exercise"""
    from engine import calculate_minimum_staff_per_role
    
    overlap_mode = request.args.get('overlap_mode', 'efficient')
    
    if overlap_mode not in ['efficient', 'conservative']:
        raise ValidationError("overlap_mode must be 'efficient' or 'conservative'")
    
    try:
        result = calculate_minimum_staff_per_role(exercise_id, overlap_mode)
        return jsonify(result)
    except ValueError as e:
        raise ValidationError(str(e))


@api.route('/planning-exercises/<int:exercise_id>/costs', methods=['GET'])
@handle_errors
def get_planning_costs(exercise_id):
    """Get cost and margin breakdown for a planning exercise"""
    from engine import calculate_planning_costs
    
    try:
        result = calculate_planning_costs(exercise_id)
        return jsonify(result)
    except ValueError as e:
        raise ValidationError(str(e))


@api.route('/planning-exercises/<int:exercise_id>/apply', methods=['POST'])
@handle_errors
def apply_planning_exercise_endpoint(exercise_id):
    """
    Apply a planning exercise by creating real projects and ghost staff.
    
    Request Body:
        preview (optional): If true, only return preview without creating (default false)
    """
    from engine import apply_planning_exercise
    
    data = request.get_json() or {}
    preview = data.get('preview', False)
    
    try:
        result = apply_planning_exercise(exercise_id, create_real_projects=not preview)
        return jsonify(result), 201 if not preview else 200
    except ValueError as e:
        raise ValidationError(str(e))
