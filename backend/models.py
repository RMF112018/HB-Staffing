from datetime import datetime
from db import db
import json
import bcrypt

class Staff(db.Model):
    """Staff member model"""
    __tablename__ = 'staff'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    hourly_rate = db.Column(db.Float, nullable=False)
    availability_start = db.Column(db.Date, nullable=True)
    availability_end = db.Column(db.Date, nullable=True)
    skills = db.Column(db.Text, nullable=True)  # JSON string of skills
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assignments = db.relationship('Assignment', backref='staff_member', lazy=True, cascade='all, delete-orphan')

    def __init__(self, name, role, hourly_rate, availability_start=None, availability_end=None, skills=None):
        self.name = name
        self.role = role
        self.hourly_rate = hourly_rate
        self.availability_start = availability_start
        self.availability_end = availability_end
        self.skills = skills or '[]'  # Default to empty JSON array

    def to_dict(self):
        """Convert staff member to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'hourly_rate': self.hourly_rate,
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
    """Project model"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='planning')  # planning, active, completed, cancelled
    budget = db.Column(db.Float, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assignments = db.relationship('Assignment', backref='project', lazy=True, cascade='all, delete-orphan')

    def __init__(self, name, start_date=None, end_date=None, status='planning', budget=None, location=None):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.status = status
        self.budget = budget
        self.location = location

    def to_dict(self):
        """Convert project to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'budget': self.budget,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def duration_days(self):
        """Calculate project duration in days"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None


class Assignment(db.Model):
    """Staff assignment to project model"""
    __tablename__ = 'assignments'

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    hours_per_week = db.Column(db.Float, nullable=False, default=40.0)
    role_on_project = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, staff_id, project_id, start_date, end_date, hours_per_week=40.0, role_on_project=None):
        self.staff_id = staff_id
        self.project_id = project_id
        self.start_date = start_date
        self.end_date = end_date
        self.hours_per_week = hours_per_week
        self.role_on_project = role_on_project or ''

    def to_dict(self):
        """Convert assignment to dictionary"""
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'project_id': self.project_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'hours_per_week': self.hours_per_week,
            'role_on_project': self.role_on_project,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # Include related data
            'staff_name': self.staff_member.name if self.staff_member else None,
            'project_name': self.project.name if self.project else None
        }

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

    @property
    def estimated_cost(self):
        """Calculate estimated cost based on staff hourly rate"""
        if self.staff_member:
            return self.total_hours * self.staff_member.hourly_rate
        return 0


class User(db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='preconstruction')  # preconstruction, leadership, admin
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
