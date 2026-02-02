"""
Unit tests for HB-Staffing database models
"""

import pytest
from datetime import date, datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Staff, Project, Assignment, User, Role, ProjectRoleRate, db
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


@pytest.fixture
def sample_role(app):
    """Create a sample role for testing."""
    with app.app_context():
        role = Role(
            name="Project Manager",
            hourly_cost=80.0,
            description="Oversees project planning and execution"
        )
        db.session.add(role)
        db.session.commit()
        db.session.refresh(role)
        return role.id


class TestRoleModel:
    """Test cases for Role model"""

    def test_role_creation(self, app):
        """Test creating a role"""
        with app.app_context():
            role = Role(
                name="Senior Estimator",
                hourly_cost=70.0,
                description="Leads cost estimation efforts"
            )
            db.session.add(role)
            db.session.commit()

            assert role.id is not None
            assert role.name == "Senior Estimator"
            assert role.hourly_cost == 70.0
            assert role.is_active == True
            assert role.created_at is not None

    def test_role_to_dict(self, app):
        """Test role to_dict method"""
        with app.app_context():
            role = Role(
                name="Estimator",
                hourly_cost=60.0,
                description="Performs cost estimation"
            )
            db.session.add(role)
            db.session.commit()

            data = role.to_dict()
            assert data['id'] == role.id
            assert data['name'] == "Estimator"
            assert data['hourly_cost'] == 60.0
            assert data['is_active'] == True
            assert data['staff_count'] == 0
            assert 'created_at' in data

    def test_role_unique_name(self, app):
        """Test that role names must be unique"""
        with app.app_context():
            role1 = Role(name="Unique Role", hourly_cost=50.0)
            db.session.add(role1)
            db.session.commit()

            # Attempting to add duplicate should fail
            role2 = Role(name="Unique Role", hourly_cost=60.0)
            db.session.add(role2)
            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()

    def test_role_staff_relationship(self, app):
        """Test role relationship with staff members"""
        with app.app_context():
            role = Role(name="Test Role", hourly_cost=55.0)
            db.session.add(role)
            db.session.commit()

            # Create staff with this role
            staff1 = Staff(name="Staff One", role_id=role.id, hourly_rate=70.0)
            staff2 = Staff(name="Staff Two", role_id=role.id, hourly_rate=75.0)
            db.session.add(staff1)
            db.session.add(staff2)
            db.session.commit()

            # Refresh role to get updated relationship
            db.session.refresh(role)
            assert len(role.staff_members) == 2

    def test_role_get_by_name(self, app):
        """Test role get_by_name static method"""
        with app.app_context():
            role = Role(name="Searchable Role", hourly_cost=65.0)
            db.session.add(role)
            db.session.commit()

            found = Role.get_by_name("Searchable Role")
            assert found is not None
            assert found.name == "Searchable Role"

            not_found = Role.get_by_name("Nonexistent Role")
            assert not_found is None


class TestStaffModel:
    """Test cases for Staff model"""

    def test_staff_creation(self, app, sample_role):
        """Test creating a staff member"""
        with app.app_context():
            staff = Staff(
                name="John Doe",
                role_id=sample_role,
                hourly_rate=95.0
            )
            db.session.add(staff)
            db.session.commit()

            assert staff.id is not None
            assert staff.name == "John Doe"
            assert staff.role_id == sample_role
            assert staff.hourly_rate == 95.0
            assert staff.created_at is not None

    def test_staff_to_dict(self, app, sample_role):
        """Test staff to_dict method"""
        with app.app_context():
            staff = Staff(
                name="Jane Smith",
                role_id=sample_role,
                hourly_rate=85.0
            )
            db.session.add(staff)
            db.session.commit()

            data = staff.to_dict()
            assert data['id'] == staff.id
            assert data['name'] == "Jane Smith"
            assert data['role_id'] == sample_role
            assert data['role'] == "Project Manager"  # From the sample_role fixture
            assert data['hourly_rate'] == 85.0
            assert data['role_hourly_cost'] == 80.0  # From the sample_role fixture
            assert 'created_at' in data

    def test_staff_internal_hourly_cost(self, app, sample_role):
        """Test staff internal_hourly_cost property"""
        with app.app_context():
            staff = Staff(
                name="Cost Test",
                role_id=sample_role,
                hourly_rate=100.0  # Billable rate
            )
            db.session.add(staff)
            db.session.commit()

            # Internal cost should come from role
            assert staff.internal_hourly_cost == 80.0  # From sample_role
            # Billable rate is different
            assert staff.hourly_rate == 100.0

    def test_staff_skills(self, app, sample_role):
        """Test staff skills management"""
        with app.app_context():
            staff = Staff(
                name="Mike Johnson",
                role_id=sample_role,
                hourly_rate=80.0
            )
            skills = ["Python", "React", "Docker"]
            staff.set_skills_list(skills)
            db.session.add(staff)
            db.session.commit()

            assert staff.get_skills_list() == skills

    def test_staff_relationships(self, app, sample_role):
        """Test staff relationships with assignments"""
        with app.app_context():
            # Create staff
            staff = Staff(name="Alice Brown", role_id=sample_role, hourly_rate=70.0)
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
            # Create role first
            role = Role(name="Worker", hourly_cost=45.0)
            db.session.add(role)
            db.session.commit()

            # Create project
            project = Project(name="Relationship Test", status="active")
            db.session.add(project)

            # Create staff
            staff = Staff(name="Test Staff", role_id=role.id, hourly_rate=50.0)
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
            assert project.assignments[0].staff_member.name == "Test Staff"


class TestAssignmentModel:
    """Test cases for Assignment model"""

    def test_assignment_creation(self, app):
        """Test creating an assignment"""
        with app.app_context():
            # Create role first
            role = Role(name="Laborer", hourly_cost=40.0)
            db.session.add(role)
            db.session.commit()

            # Create dependencies
            staff = Staff(name="Worker", role_id=role.id, hourly_rate=45.0)
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
            # Create role first
            role = Role(name="Calculator Role", hourly_cost=45.0)
            db.session.add(role)
            db.session.commit()

            # Create dependencies
            staff = Staff(name="Calculator", role_id=role.id, hourly_rate=50.0)
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
            assert assignment.estimated_cost == 24000.0  # 480 hours * $50/hour (billable)
            assert assignment.internal_cost == 21600.0  # 480 hours * $45/hour (internal)


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


class TestProjectHierarchy:
    """Test cases for Project hierarchy (folders and sub-projects)"""

    def test_project_folder_creation(self, app):
        """Test creating a project folder"""
        with app.app_context():
            folder = Project(
                name="Development Folder",
                status="active",
                is_folder=True
            )
            db.session.add(folder)
            db.session.commit()

            assert folder.id is not None
            assert folder.is_folder == True
            assert folder.parent_project_id is None

    def test_sub_project_creation(self, app):
        """Test creating a sub-project under a folder"""
        with app.app_context():
            # Create parent folder
            folder = Project(name="Parent Folder", status="active", is_folder=True)
            db.session.add(folder)
            db.session.commit()

            # Create sub-project
            sub_project = Project(
                name="Sub Project 1",
                status="planning",
                is_folder=False,
                parent_project_id=folder.id
            )
            db.session.add(sub_project)
            db.session.commit()

            assert sub_project.parent_project_id == folder.id
            assert sub_project.parent_project.name == "Parent Folder"
            assert len(folder.sub_projects) == 1

    def test_hierarchy_path(self, app):
        """Test project hierarchy_path property"""
        with app.app_context():
            # Create folder
            folder = Project(name="Main Project", status="active", is_folder=True)
            db.session.add(folder)
            db.session.commit()

            # Create sub-project
            sub = Project(name="Phase 1", status="planning", parent_project_id=folder.id)
            db.session.add(sub)
            db.session.commit()

            assert folder.hierarchy_path == "Main Project"
            assert sub.hierarchy_path == "Main Project > Phase 1"

    def test_to_dict_includes_hierarchy(self, app):
        """Test that to_dict includes hierarchy information"""
        with app.app_context():
            folder = Project(name="Folder", status="active", is_folder=True)
            db.session.add(folder)
            db.session.commit()

            sub = Project(name="Sub", status="planning", parent_project_id=folder.id)
            db.session.add(sub)
            db.session.commit()

            # Refresh to get relationships
            db.session.refresh(folder)
            db.session.refresh(sub)

            folder_dict = folder.to_dict(include_children=True)
            sub_dict = sub.to_dict()

            assert folder_dict['is_folder'] == True
            assert folder_dict['sub_projects_count'] == 1
            assert 'sub_projects' in folder_dict
            
            assert sub_dict['is_folder'] == False
            assert sub_dict['parent_project_id'] == folder.id
            assert sub_dict['parent_project_name'] == "Folder"


class TestProjectRoleRate:
    """Test cases for ProjectRoleRate model"""

    def test_project_role_rate_creation(self, app):
        """Test creating a project role rate"""
        with app.app_context():
            # Create role
            role = Role(name="Test PM", hourly_cost=80.0)
            db.session.add(role)
            db.session.commit()

            # Create project
            project = Project(name="Rate Test", status="active", is_folder=True)
            db.session.add(project)
            db.session.commit()

            # Create role rate
            rate = ProjectRoleRate(
                project_id=project.id,
                role_id=role.id,
                billable_rate=120.0
            )
            db.session.add(rate)
            db.session.commit()

            assert rate.id is not None
            assert rate.billable_rate == 120.0
            assert rate.role.name == "Test PM"

    def test_project_role_rate_unique_constraint(self, app):
        """Test that project-role combination is unique"""
        with app.app_context():
            role = Role(name="Unique Test Role", hourly_cost=50.0)
            db.session.add(role)
            project = Project(name="Unique Test", status="active")
            db.session.add(project)
            db.session.commit()

            rate1 = ProjectRoleRate(project_id=project.id, role_id=role.id, billable_rate=100.0)
            db.session.add(rate1)
            db.session.commit()

            # Attempting to add duplicate should fail
            rate2 = ProjectRoleRate(project_id=project.id, role_id=role.id, billable_rate=150.0)
            db.session.add(rate2)
            with pytest.raises(Exception):
                db.session.commit()

    def test_get_role_rate(self, app):
        """Test project get_role_rate method"""
        with app.app_context():
            role = Role(name="Rate Lookup Role", hourly_cost=60.0)
            db.session.add(role)
            project = Project(name="Lookup Test", status="active")
            db.session.add(project)
            db.session.commit()

            rate = ProjectRoleRate(project_id=project.id, role_id=role.id, billable_rate=90.0)
            db.session.add(rate)
            db.session.commit()

            # Refresh to get relationships
            db.session.refresh(project)

            result = project.get_role_rate(role.id)
            assert result is not None
            assert result['rate'] == 90.0
            assert result['is_inherited'] == False

    def test_rate_inheritance(self, app):
        """Test that sub-projects inherit rates from parent"""
        with app.app_context():
            role = Role(name="Inherited Role", hourly_cost=70.0)
            db.session.add(role)

            # Create parent folder with rate
            parent = Project(name="Parent", status="active", is_folder=True)
            db.session.add(parent)
            db.session.commit()

            parent_rate = ProjectRoleRate(project_id=parent.id, role_id=role.id, billable_rate=110.0)
            db.session.add(parent_rate)

            # Create sub-project without rate
            child = Project(name="Child", status="planning", parent_project_id=parent.id)
            db.session.add(child)
            db.session.commit()

            # Refresh to get relationships
            db.session.refresh(parent)
            db.session.refresh(child)

            # Parent should have explicit rate
            parent_result = parent.get_role_rate(role.id)
            assert parent_result['rate'] == 110.0
            assert parent_result['is_inherited'] == False

            # Child should inherit from parent
            child_result = child.get_role_rate(role.id)
            assert child_result['rate'] == 110.0
            assert child_result['is_inherited'] == True


class TestAssignmentWithProjectRates:
    """Test cases for Assignment cost calculations with project role rates"""

    def test_assignment_uses_project_role_rate(self, app):
        """Test that assignment uses project role rate when available"""
        with app.app_context():
            role = Role(name="PM Role", hourly_cost=80.0)
            db.session.add(role)
            db.session.commit()

            staff = Staff(name="PM Staff", role_id=role.id, hourly_rate=100.0)
            db.session.add(staff)

            project = Project(name="Rate Project", status="active")
            db.session.add(project)
            db.session.commit()

            # Set project role rate
            project_rate = ProjectRoleRate(project_id=project.id, role_id=role.id, billable_rate=150.0)
            db.session.add(project_rate)
            db.session.commit()

            # Create assignment with matching role
            assignment = Assignment(
                staff_id=staff.id,
                project_id=project.id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 8),  # 1 week
                hours_per_week=40.0,
                role_on_project="PM Role"
            )
            db.session.add(assignment)
            db.session.commit()

            rate_info = assignment.get_effective_billable_rate()
            assert rate_info['rate'] == 150.0  # Uses project rate
            assert rate_info['source'] == 'project_role_rate'

    def test_assignment_falls_back_to_staff_rate(self, app):
        """Test that assignment falls back to staff rate when no project rate"""
        with app.app_context():
            role = Role(name="Fallback Role", hourly_cost=60.0)
            db.session.add(role)
            db.session.commit()

            staff = Staff(name="Fallback Staff", role_id=role.id, hourly_rate=75.0)
            db.session.add(staff)

            project = Project(name="No Rate Project", status="active")
            db.session.add(project)
            db.session.commit()

            # Create assignment without matching project role rate
            assignment = Assignment(
                staff_id=staff.id,
                project_id=project.id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 8),
                hours_per_week=40.0,
                role_on_project="Some Other Role"
            )
            db.session.add(assignment)
            db.session.commit()

            rate_info = assignment.get_effective_billable_rate()
            assert rate_info['rate'] == 75.0  # Falls back to staff rate
            assert rate_info['source'] == 'staff_hourly_rate'

    def test_assignment_to_dict_includes_rate_info(self, app):
        """Test that assignment to_dict includes billable rate information"""
        with app.app_context():
            role = Role(name="Dict Test Role", hourly_cost=50.0)
            db.session.add(role)
            db.session.commit()

            staff = Staff(name="Dict Test Staff", role_id=role.id, hourly_rate=65.0)
            db.session.add(staff)

            project = Project(name="Dict Test Project", status="active")
            db.session.add(project)
            db.session.commit()

            assignment = Assignment(
                staff_id=staff.id,
                project_id=project.id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 8),
                hours_per_week=40.0
            )
            db.session.add(assignment)
            db.session.commit()

            data = assignment.to_dict()
            assert 'billable_rate' in data
            assert 'billable_rate_source' in data
            assert 'estimated_cost' in data
            assert 'project_hierarchy_path' in data


if __name__ == '__main__':
    pytest.main([__file__])
