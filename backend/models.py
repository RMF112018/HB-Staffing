from datetime import datetime, timezone
from db import db
import json
import bcrypt


def utc_now():
    """Return current UTC time (timezone-aware)"""
    return datetime.now(timezone.utc)


class Role(db.Model):
    """Role/Position Title model with associated hourly costs"""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    hourly_cost = db.Column(db.Float, nullable=False)  # Internal company cost per hour
    default_billable_rate = db.Column(db.Float, nullable=True)  # Default billable rate for projects
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    staff_members = db.relationship('Staff', backref='position_role', lazy=True)

    def __init__(self, name, hourly_cost, description=None, default_billable_rate=None, is_active=True):
        self.name = name
        self.hourly_cost = hourly_cost
        self.description = description
        self.default_billable_rate = default_billable_rate
        self.is_active = is_active

    def to_dict(self):
        """Convert role to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'hourly_cost': self.hourly_cost,
            'default_billable_rate': self.default_billable_rate,
            'is_active': self.is_active,
            'staff_count': len(self.staff_members) if self.staff_members else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def get_by_name(name):
        """Get role by name"""
        return Role.query.filter_by(name=name).first()


class Staff(db.Model):
    """Staff member model"""
    __tablename__ = 'staff'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    internal_hourly_cost = db.Column(db.Float, nullable=False)  # What company pays this staff member per hour
    availability_start = db.Column(db.Date, nullable=True)
    availability_end = db.Column(db.Date, nullable=True)
    skills = db.Column(db.Text, nullable=True)  # JSON string of skills
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    assignments = db.relationship('Assignment', backref='staff_member', lazy=True, cascade='all, delete-orphan')

    def __init__(self, name, role_id, internal_hourly_cost, availability_start=None, availability_end=None, skills=None):
        self.name = name
        self.role_id = role_id
        self.internal_hourly_cost = internal_hourly_cost
        self.availability_start = availability_start
        self.availability_end = availability_end
        self.skills = skills or '[]'  # Default to empty JSON array

    @property
    def role(self):
        """Get the role name for backward compatibility"""
        return self.position_role.name if self.position_role else None

    @property
    def default_billable_rate(self):
        """Get the default billable rate from the assigned role"""
        return self.position_role.default_billable_rate if self.position_role else None

    def to_dict(self):
        """Convert staff member to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'role_id': self.role_id,
            'role': self.position_role.name if self.position_role else None,
            'role_hourly_cost': self.position_role.hourly_cost if self.position_role else None,
            'internal_hourly_cost': self.internal_hourly_cost,
            'default_billable_rate': self.default_billable_rate,
            'availability_start': self.availability_start.isoformat() if self.availability_start else None,
            'availability_end': self.availability_end.isoformat() if self.availability_end else None,
            'skills': json.loads(self.skills) if self.skills else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def get_skills_list(self):
        """Get skills as a list"""
        return json.loads(self.skills) if self.skills else []

    def set_skills_list(self, skills_list):
        """Set skills from a list"""
        self.skills = json.dumps(skills_list) if skills_list else '[]'


class Project(db.Model):
    """Project model with hierarchical folder/sub-project support"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='planning')  # planning, active, completed, cancelled
    budget = db.Column(db.Float, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    
    # Hierarchy fields
    parent_project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    is_folder = db.Column(db.Boolean, default=False)  # True for parent folders, False for sub-projects
    
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    assignments = db.relationship('Assignment', backref='project', lazy=True, cascade='all, delete-orphan')
    sub_projects = db.relationship('Project', backref=db.backref('parent_project', remote_side=[id]), lazy=True)
    role_rates = db.relationship('ProjectRoleRate', backref='project', lazy=True, cascade='all, delete-orphan')

    # Cache for role rate lookups
    _role_rate_cache = None

    def __init__(self, name, start_date=None, end_date=None, status='planning', budget=None, location=None,
                 parent_project_id=None, is_folder=False):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.status = status
        self.budget = budget
        self.location = location
        self.parent_project_id = parent_project_id
        self.is_folder = is_folder

    def to_dict(self, include_children=False):
        """Convert project to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'budget': self.budget,
            'location': self.location,
            'parent_project_id': self.parent_project_id,
            'is_folder': self.is_folder,
            'parent_project_name': self.parent_project.name if self.parent_project else None,
            'sub_projects_count': len(self.sub_projects) if self.sub_projects else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_children and self.sub_projects:
            data['sub_projects'] = [sp.to_dict(include_children=False) for sp in self.sub_projects]
        return data

    @property
    def duration_days(self):
        """Calculate project duration in days"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None

    @property
    def hierarchy_path(self):
        """Get the full hierarchy path as a string (e.g., 'Parent > Sub-Project')"""
        if self.parent_project:
            return f"{self.parent_project.hierarchy_path} > {self.name}"
        return self.name

    def get_role_rate(self, role_id):
        """
        Get the billable rate for a specific role on this project.
        Checks project's own rates first, then recursively checks parent projects.
        
        Args:
            role_id: ID of the role to look up
            
        Returns:
            dict with 'rate' and 'is_inherited' keys, or None if no rate found
        """
        # Check if this project has an explicit rate for the role
        for rate in self.role_rates:
            if rate.role_id == role_id:
                return {'rate': rate.billable_rate, 'is_inherited': False, 'source_project_id': self.id}
        
        # If not, check parent project recursively
        if self.parent_project:
            parent_rate = self.parent_project.get_role_rate(role_id)
            if parent_rate:
                return {'rate': parent_rate['rate'], 'is_inherited': True, 'source_project_id': parent_rate['source_project_id']}
        
        return None

    def get_role_rate_by_name(self, role_name):
        """
        Get the billable rate for a role by name on this project.
        
        Args:
            role_name: Name of the role to look up
            
        Returns:
            dict with 'rate' and 'is_inherited' keys, or None if no rate found
        """
        role = Role.query.filter_by(name=role_name).first()
        if role:
            return self.get_role_rate(role.id)
        return None

    def get_all_role_rates(self):
        """
        Get all role rates for this project, including inherited rates from parent.
        
        Returns:
            list of dicts with role info and rates
        """
        all_roles = Role.query.filter_by(is_active=True).all()
        rates = []
        
        for role in all_roles:
            rate_info = self.get_role_rate(role.id)
            rates.append({
                'role_id': role.id,
                'role_name': role.name,
                'billable_rate': rate_info['rate'] if rate_info else None,
                'is_inherited': rate_info['is_inherited'] if rate_info else None,
                'source_project_id': rate_info['source_project_id'] if rate_info else None
            })
        
        return rates


class ProjectRoleRate(db.Model):
    """Project-specific billable rates per role"""
    __tablename__ = 'project_role_rates'
    __table_args__ = (
        db.UniqueConstraint('project_id', 'role_id', name='unique_project_role_rate'),
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    billable_rate = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    role = db.relationship('Role', backref='project_rates', lazy=True)

    def __init__(self, project_id, role_id, billable_rate):
        self.project_id = project_id
        self.role_id = role_id
        self.billable_rate = billable_rate

    def to_dict(self):
        """Convert project role rate to dictionary"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'role_id': self.role_id,
            'role_name': self.role.name if self.role else None,
            'billable_rate': self.billable_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Assignment(db.Model):
    """Staff assignment to project model"""
    __tablename__ = 'assignments'

    # Allocation type constants
    ALLOCATION_FULL = 'full'
    ALLOCATION_SPLIT_BY_PROJECTS = 'split_by_projects'
    ALLOCATION_PERCENTAGE_TOTAL = 'percentage_total'
    ALLOCATION_PERCENTAGE_MONTHLY = 'percentage_monthly'

    ALLOCATION_TYPES = [
        ALLOCATION_FULL,
        ALLOCATION_SPLIT_BY_PROJECTS,
        ALLOCATION_PERCENTAGE_TOTAL,
        ALLOCATION_PERCENTAGE_MONTHLY
    ]

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    hours_per_week = db.Column(db.Float, nullable=False, default=40.0)
    role_on_project = db.Column(db.String(100), nullable=True)
    
    # Allocation fields
    allocation_type = db.Column(db.String(30), nullable=False, default='full')
    allocation_percentage = db.Column(db.Float, nullable=False, default=100.0)  # Used for percentage_total type
    
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    monthly_allocations = db.relationship('AssignmentMonthlyAllocation', backref='assignment', lazy=True, cascade='all, delete-orphan')

    def __init__(self, staff_id, project_id, start_date, end_date, hours_per_week=40.0, role_on_project=None,
                 allocation_type='full', allocation_percentage=100.0):
        self.staff_id = staff_id
        self.project_id = project_id
        self.start_date = start_date
        self.end_date = end_date
        self.hours_per_week = hours_per_week
        self.role_on_project = role_on_project or ''
        self.allocation_type = allocation_type
        self.allocation_percentage = allocation_percentage

    def to_dict(self, include_monthly_allocations=False):
        """Convert assignment to dictionary"""
        billable_rate_info = self.get_effective_billable_rate()
        data = {
            'id': self.id,
            'staff_id': self.staff_id,
            'project_id': self.project_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'hours_per_week': self.hours_per_week,
            'role_on_project': self.role_on_project,
            # Allocation fields
            'allocation_type': self.allocation_type,
            'allocation_percentage': self.allocation_percentage,
            'effective_allocation': self.effective_allocation,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # Include related data
            'staff_name': self.staff_member.name if self.staff_member else None,
            'project_name': self.project.name if self.project else None,
            'project_hierarchy_path': self.project.hierarchy_path if self.project else None,
            # Billable rate info
            'billable_rate': billable_rate_info['rate'],
            'billable_rate_source': billable_rate_info['source'],
            # Raw costs (before allocation)
            'estimated_cost': self.estimated_cost,
            'internal_cost': self.internal_cost,
            # Allocated costs (after applying allocation percentage)
            'allocated_estimated_cost': self.allocated_estimated_cost,
            'allocated_internal_cost': self.allocated_internal_cost
        }
        
        if include_monthly_allocations and self.allocation_type == self.ALLOCATION_PERCENTAGE_MONTHLY:
            data['monthly_allocations'] = [ma.to_dict() for ma in self.monthly_allocations]
        
        return data

    @property
    def duration_weeks(self):
        """Calculate assignment duration in weeks"""
        if self.start_date and self.end_date:
            return ((self.end_date - self.start_date).days) / 7.0
        return 0

    @property
    def total_hours(self):
        """Calculate total hours for this assignment"""
        return self.duration_weeks * self.hours_per_week

    def get_effective_billable_rate(self):
        """
        Get the effective billable rate for this assignment.
        Priority:
        1. Project role rate (if role_on_project matches a defined role)
        2. Staff member's role default_billable_rate as fallback
        
        Returns:
            dict with 'rate' and 'source' keys
        """
        # Try to get rate from project role rates based on role_on_project
        if self.project and self.role_on_project:
            rate_info = self.project.get_role_rate_by_name(self.role_on_project)
            if rate_info:
                source = 'project_role_rate'
                if rate_info['is_inherited']:
                    source = 'inherited_project_role_rate'
                return {'rate': rate_info['rate'], 'source': source}
        
        # Fallback to staff member's role default billable rate
        if self.staff_member and self.staff_member.default_billable_rate:
            return {'rate': self.staff_member.default_billable_rate, 'source': 'role_default_billable_rate'}
        
        return {'rate': 0, 'source': 'none'}

    @property
    def estimated_cost(self):
        """Calculate estimated cost based on project role rate or staff billable hourly rate"""
        rate_info = self.get_effective_billable_rate()
        return self.total_hours * rate_info['rate']

    @property
    def internal_cost(self):
        """Calculate internal cost based on staff role's hourly cost"""
        if self.staff_member:
            return self.total_hours * self.staff_member.internal_hourly_cost
        return 0

    def get_allocation_for_period(self, period_start=None, period_end=None):
        """
        Get the effective allocation percentage for a given period.
        
        Args:
            period_start: Start date of period (defaults to assignment start_date)
            period_end: End date of period (defaults to assignment end_date)
            
        Returns:
            float: Allocation percentage (0-100)
        """
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        if period_start is None:
            period_start = self.start_date
        if period_end is None:
            period_end = self.end_date
            
        if self.allocation_type == self.ALLOCATION_FULL:
            return 100.0
            
        elif self.allocation_type == self.ALLOCATION_PERCENTAGE_TOTAL:
            return self.allocation_percentage
            
        elif self.allocation_type == self.ALLOCATION_SPLIT_BY_PROJECTS:
            # Count overlapping assignments for the same staff member
            overlapping_assignments = Assignment.query.filter(
                Assignment.staff_id == self.staff_id,
                Assignment.start_date <= period_end,
                Assignment.end_date >= period_start
            ).all()
            
            if len(overlapping_assignments) > 0:
                return 100.0 / len(overlapping_assignments)
            return 100.0
            
        elif self.allocation_type == self.ALLOCATION_PERCENTAGE_MONTHLY:
            # Calculate weighted average allocation based on monthly allocations
            if not self.monthly_allocations:
                return 100.0
                
            # Get all months in the period
            total_days = 0
            weighted_allocation = 0
            
            current_month = date(period_start.year, period_start.month, 1)
            while current_month <= period_end:
                # Find allocation for this month
                month_allocation = next(
                    (ma.allocation_percentage for ma in self.monthly_allocations 
                     if ma.month.year == current_month.year and ma.month.month == current_month.month),
                    100.0  # Default to 100% if not specified
                )
                
                # Calculate days in this month that overlap with the period
                month_start = max(current_month, period_start)
                next_month = current_month + relativedelta(months=1)
                month_end = min(next_month - relativedelta(days=1), period_end)
                
                days_in_period = (month_end - month_start).days + 1
                if days_in_period > 0:
                    total_days += days_in_period
                    weighted_allocation += days_in_period * month_allocation
                
                current_month = next_month
            
            if total_days > 0:
                return weighted_allocation / total_days
            return 100.0
            
        return 100.0

    def get_monthly_allocation(self, year, month):
        """
        Get the allocation percentage for a specific month.
        
        Args:
            year: Year of the month
            month: Month number (1-12)
            
        Returns:
            float: Allocation percentage for that month
        """
        if self.allocation_type != self.ALLOCATION_PERCENTAGE_MONTHLY:
            return self.get_allocation_for_period()
            
        for ma in self.monthly_allocations:
            if ma.month.year == year and ma.month.month == month:
                return ma.allocation_percentage
        return 100.0  # Default if not found

    @property
    def effective_allocation(self):
        """Get the overall effective allocation percentage for the entire assignment"""
        return self.get_allocation_for_period()

    @property
    def allocated_estimated_cost(self):
        """Calculate estimated cost adjusted by allocation percentage"""
        allocation = self.effective_allocation / 100.0
        return self.estimated_cost * allocation

    @property
    def allocated_internal_cost(self):
        """Calculate internal cost adjusted by allocation percentage"""
        allocation = self.effective_allocation / 100.0
        return self.internal_cost * allocation


class AssignmentMonthlyAllocation(db.Model):
    """Monthly allocation percentages for assignments using percentage_monthly type"""
    __tablename__ = 'assignment_monthly_allocations'
    __table_args__ = (
        db.UniqueConstraint('assignment_id', 'month', name='unique_assignment_month'),
    )

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    month = db.Column(db.Date, nullable=False)  # First day of the month
    allocation_percentage = db.Column(db.Float, nullable=False, default=100.0)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    def __init__(self, assignment_id, month, allocation_percentage=100.0):
        self.assignment_id = assignment_id
        self.month = month
        self.allocation_percentage = allocation_percentage

    def to_dict(self):
        """Convert monthly allocation to dictionary"""
        return {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'month': self.month.isoformat() if self.month else None,
            'allocation_percentage': self.allocation_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class User(db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='preconstruction')  # preconstruction, leadership, admin
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    last_login = db.Column(db.DateTime, nullable=True)

    def __init__(self, username, email, password, role='preconstruction'):
        self.username = username
        self.email = email
        self.role = role
        self.set_password(password)

    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        """Verify the password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        if include_sensitive:
            data['password_hash'] = self.password_hash
        return data

    def has_role(self, role):
        """Check if user has specific role"""
        return self.role == role

    def has_permission(self, permission):
        """Check if user has permission based on role"""
        role_permissions = {
            'admin': ['read', 'write', 'delete', 'manage_users', 'view_reports', 'export_data'],
            'leadership': ['read', 'write', 'delete', 'view_reports', 'export_data'],
            'preconstruction': ['read', 'write', 'view_basic_reports']
        }
        return permission in role_permissions.get(self.role, [])

    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        return User.query.filter_by(email=email).first()


class ProjectTemplate(db.Model):
    """Template for creating projects with predefined roles and durations"""
    __tablename__ = 'project_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    project_type = db.Column(db.String(100), nullable=True)  # e.g., "Commercial", "Residential", "Healthcare"
    duration_months = db.Column(db.Integer, nullable=False, default=12)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    template_roles = db.relationship('TemplateRole', backref='template', lazy=True, cascade='all, delete-orphan')

    def __init__(self, name, duration_months=12, description=None, project_type=None, is_active=True):
        self.name = name
        self.duration_months = duration_months
        self.description = description
        self.project_type = project_type
        self.is_active = is_active

    def to_dict(self, include_roles=True):
        """Convert template to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'project_type': self.project_type,
            'duration_months': self.duration_months,
            'is_active': self.is_active,
            'role_count': len(self.template_roles) if self.template_roles else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_roles and self.template_roles:
            data['roles'] = [tr.to_dict() for tr in self.template_roles]
        return data


class TemplateRole(db.Model):
    """Roles required in a project template"""
    __tablename__ = 'template_roles'

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('project_templates.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    count = db.Column(db.Integer, nullable=False, default=1)  # Number of staff needed
    start_month = db.Column(db.Integer, nullable=False, default=1)  # Month number when role starts (1-based)
    end_month = db.Column(db.Integer, nullable=True)  # Month number when role ends (null = project end)
    hours_per_week = db.Column(db.Float, nullable=False, default=40.0)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    role = db.relationship('Role', backref='template_roles', lazy=True)

    def __init__(self, template_id, role_id, count=1, start_month=1, end_month=None, hours_per_week=40.0):
        self.template_id = template_id
        self.role_id = role_id
        self.count = count
        self.start_month = start_month
        self.end_month = end_month
        self.hours_per_week = hours_per_week

    def to_dict(self):
        """Convert template role to dictionary"""
        return {
            'id': self.id,
            'template_id': self.template_id,
            'role_id': self.role_id,
            'role_name': self.role.name if self.role else None,
            'role_hourly_cost': self.role.hourly_cost if self.role else None,
            'role_default_billable_rate': self.role.default_billable_rate if self.role else None,
            'count': self.count,
            'start_month': self.start_month,
            'end_month': self.end_month,
            'hours_per_week': self.hours_per_week,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class GhostStaff(db.Model):
    """Placeholder staff for project planning purposes"""
    __tablename__ = 'ghost_staff'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Auto-generated name (e.g., "PM Placeholder 1")
    internal_hourly_cost = db.Column(db.Float, nullable=False)  # Copied from role
    billable_rate = db.Column(db.Float, nullable=True)  # From project role rate or role default
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    hours_per_week = db.Column(db.Float, nullable=False, default=40.0)
    replaced_by_staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=True)  # When replaced with real staff
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    project = db.relationship('Project', backref='ghost_staff', lazy=True)
    role = db.relationship('Role', backref='ghost_staff', lazy=True)
    replaced_by = db.relationship('Staff', backref='replaced_ghosts', lazy=True)

    def __init__(self, project_id, role_id, name, internal_hourly_cost, billable_rate, start_date, end_date, hours_per_week=40.0):
        self.project_id = project_id
        self.role_id = role_id
        self.name = name
        self.internal_hourly_cost = internal_hourly_cost
        self.billable_rate = billable_rate
        self.start_date = start_date
        self.end_date = end_date
        self.hours_per_week = hours_per_week

    @property
    def duration_weeks(self):
        """Calculate duration in weeks"""
        if self.start_date and self.end_date:
            return ((self.end_date - self.start_date).days) / 7.0
        return 0

    @property
    def total_hours(self):
        """Calculate total hours"""
        return self.duration_weeks * self.hours_per_week

    @property
    def estimated_cost(self):
        """Calculate estimated billable cost"""
        return self.total_hours * (self.billable_rate or 0)

    @property
    def internal_cost(self):
        """Calculate internal cost"""
        return self.total_hours * self.internal_hourly_cost

    @property
    def is_replaced(self):
        """Check if this ghost has been replaced with real staff"""
        return self.replaced_by_staff_id is not None

    def to_dict(self):
        """Convert ghost staff to dictionary"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'role_id': self.role_id,
            'role_name': self.role.name if self.role else None,
            'name': self.name,
            'internal_hourly_cost': self.internal_hourly_cost,
            'billable_rate': self.billable_rate,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'hours_per_week': self.hours_per_week,
            'duration_weeks': self.duration_weeks,
            'total_hours': self.total_hours,
            'estimated_cost': self.estimated_cost,
            'internal_cost': self.internal_cost,
            'is_replaced': self.is_replaced,
            'replaced_by_staff_id': self.replaced_by_staff_id,
            'replaced_by_staff_name': self.replaced_by.name if self.replaced_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
