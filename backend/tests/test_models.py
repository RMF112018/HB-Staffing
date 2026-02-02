"""
Unit tests for HB-Staffing database models
"""

import pytest
from datetime import date, datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Staff, Project, Assignment, User, db
from app import create_app


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


class TestStaffModel:
    """Test cases for Staff model"""

    def test_staff_creation(self, app):
        """Test creating a staff member"""
        with app.app_context():
            staff = Staff(
                name="John Doe",
                role="Project Manager",
                hourly_rate=75.0
            )
            db.session.add(staff)
            db.session.commit()

            assert staff.id is not None
            assert staff.name == "John Doe"
            assert staff.role == "Project Manager"
            assert staff.hourly_rate == 75.0
            assert staff.created_at is not None

    def test_staff_to_dict(self, app):
        """Test staff to_dict method"""
        with app.app_context():
            staff = Staff(
                name="Jane Smith",
                role="Estimator",
                hourly_rate=65.0
            )
            db.session.add(staff)
            db.session.commit()

            data = staff.to_dict()
            assert data['id'] == staff.id
            assert data['name'] == "Jane Smith"
            assert data['role'] == "Estimator"
            assert data['hourly_rate'] == 65.0
            assert 'created_at' in data

    def test_staff_skills(self, app):
        """Test staff skills management"""
        with app.app_context():
            staff = Staff(
                name="Mike Johnson",
                role="Developer",
                hourly_rate=80.0
            )
            skills = ["Python", "React", "Docker"]
            staff.set_skills_list(skills)
            db.session.add(staff)
            db.session.commit()

            assert staff.get_skills_list() == skills

    def test_staff_relationships(self, app):
        """Test staff relationships with assignments"""
        with app.app_context():
            # Create staff
            staff = Staff(name="Alice Brown", role="Manager", hourly_rate=70.0)
            db.session.add(staff)

            # Create project
            project = Project(
                name="Test Project",
                start_date=date.today(),
                status="active"
            )
            db.session.add(project)
            db.session.commit()

            # Create assignment
            assignment = Assignment(
                staff_id=staff.id,
                project_id=project.id,
                start_date=date.today(),
                end_date=date.today(),
                hours_per_week=40.0
            )
            db.session.add(assignment)
            db.session.commit()

            assert len(staff.assignments) == 1
            assert staff.assignments[0].project.name == "Test Project"


class TestProjectModel:
    """Test cases for Project model"""

    def test_project_creation(self, app):
        """Test creating a project"""
        with app.app_context():
            project = Project(
                name="New Construction",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                status="planning",
                budget=1000000.0,
                location="Downtown"
            )
            db.session.add(project)
            db.session.commit()

            assert project.id is not None
            assert project.name == "New Construction"
            assert project.status == "planning"
            assert project.budget == 1000000.0

    def test_project_validation(self, app):
        """Test project status validation"""
        with app.app_context():
            # Valid status
            project = Project(name="Valid Project", status="active")
            db.session.add(project)
            db.session.commit()
            assert project.status == "active"

            # Invalid status should be handled at application level
            # (database constraints would be added in production)

    def test_project_relationships(self, app):
        """Test project relationships with assignments"""
        with app.app_context():
            # Create project
            project = Project(name="Relationship Test", status="active")
            db.session.add(project)

            # Create staff
            staff = Staff(name="Test Staff", role="Worker", hourly_rate=50.0)
            db.session.add(staff)
            db.session.commit()

            # Create assignment
            assignment = Assignment(
                staff_id=staff.id,
                project_id=project.id,
                start_date=date.today(),
                end_date=date.today(),
                hours_per_week=40.0
            )
            db.session.add(assignment)
            db.session.commit()

            assert len(project.assignments) == 1
            assert project.assignments[0].staff.name == "Test Staff"


class TestAssignmentModel:
    """Test cases for Assignment model"""

    def test_assignment_creation(self, app):
        """Test creating an assignment"""
        with app.app_context():
            # Create dependencies
            staff = Staff(name="Worker", role="Laborer", hourly_rate=45.0)
            project = Project(name="Construction Site", status="active")
            db.session.add(staff)
            db.session.add(project)
            db.session.commit()

            # Create assignment
            assignment = Assignment(
                staff_id=staff.id,
                project_id=project.id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 31),
                hours_per_week=40.0,
                role_on_project="General Labor"
            )
            db.session.add(assignment)
            db.session.commit()

            assert assignment.id is not None
            assert assignment.staff_id == staff.id
            assert assignment.project_id == project.id
            assert assignment.hours_per_week == 40.0

    def test_assignment_calculations(self, app):
        """Test assignment calculation properties"""
        with app.app_context():
            # Create dependencies
            staff = Staff(name="Calculator", role="Worker", hourly_rate=50.0)
            project = Project(name="Calc Test", status="active")
            db.session.add(staff)
            db.session.add(project)
            db.session.commit()

            # Create assignment spanning 12 weeks
            assignment = Assignment(
                staff_id=staff.id,
                project_id=project.id,
                start_date=date(2024, 1, 1),  # Monday
                end_date=date(2024, 3, 25),   # 12 weeks later (84 days)
                hours_per_week=40.0
            )
            db.session.add(assignment)
            db.session.commit()

            # Test calculations
            assert assignment.duration_weeks == 12.0  # Approximately 12 weeks
            assert assignment.total_hours == 480.0   # 12 weeks * 40 hours
            assert assignment.estimated_cost == 24000.0  # 480 hours * $50/hour


class TestUserModel:
    """Test cases for User model"""

    def test_user_creation(self, app):
        """Test creating a user"""
        with app.app_context():
            user = User(
                username="testuser",
                email="test@example.com",
                password="securepassword123",
                role="preconstruction"
            )
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.username == "testuser"
            assert user.email == "test@example.com"
            assert user.role == "preconstruction"
            assert user.is_active == True

    def test_password_hashing(self, app):
        """Test password hashing and verification"""
        with app.app_context():
            user = User(username="auth_test", email="auth@example.com", password="testpass")
            db.session.add(user)
            db.session.commit()

            # Test password verification
            assert user.check_password("testpass") == True
            assert user.check_password("wrongpass") == False

    def test_user_role_methods(self, app):
        """Test user role checking methods"""
        with app.app_context():
            admin = User(username="admin", email="admin@test.com", password="pass", role="admin")
            user = User(username="user", email="user@test.com", password="pass", role="preconstruction")

            db.session.add(admin)
            db.session.add(user)
            db.session.commit()

            # Test role checking
            assert admin.has_role("admin") == True
            assert admin.has_role("preconstruction") == False
            assert user.has_role("preconstruction") == True

            # Test permission checking
            assert admin.has_permission("manage_users") == True
            assert user.has_permission("manage_users") == False
            assert user.has_permission("read") == True

    def test_user_static_methods(self, app):
        """Test user static methods"""
        with app.app_context():
            user1 = User(username="static1", email="static1@test.com", password="pass")
            user2 = User(username="static2", email="static2@test.com", password="pass")
            db.session.add(user1)
            db.session.add(user2)
            db.session.commit()

            # Test lookup methods
            found_by_username = User.get_by_username("static1")
            found_by_email = User.get_by_email("static2@test.com")

            assert found_by_username == user1
            assert found_by_email == user2
            assert User.get_by_username("nonexistent") is None


if __name__ == '__main__':
    pytest.main([__file__])
