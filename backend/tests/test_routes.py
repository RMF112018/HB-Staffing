"""
Unit tests for HB-Staffing API routes
"""

import pytest
import json
from datetime import date
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Staff, Project, Assignment, User, Role


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
def auth_headers(client):
    """Get authentication headers for testing protected routes."""
    # Create a test user
    with client.application.app_context():
        user = User(username="testuser", email="test@example.com", password="testpass", role="admin")
        db.session.add(user)
        db.session.commit()

        # Login to get token
        response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'testpass'
        })
        token = response.get_json()['access_token']

    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def test_roles(app):
    """Create test roles for API testing."""
    with app.app_context():
        role1 = Role(name="Manager", hourly_cost=70.0, description="Project management")
        role2 = Role(name="Estimator", hourly_cost=60.0, description="Cost estimation")
        role3 = Role(name="Developer", hourly_cost=55.0, description="Software development")
        db.session.add(role1)
        db.session.add(role2)
        db.session.add(role3)
        db.session.commit()
        return {'roles': [role1, role2, role3]}


@pytest.fixture
def test_data(app, test_roles):
    """Create test data for API testing."""
    with app.app_context():
        # Get the roles
        manager_role = Role.query.filter_by(name="Manager").first()
        estimator_role = Role.query.filter_by(name="Estimator").first()

        # Create test staff with role_id
        staff1 = Staff(name="John Doe", role_id=manager_role.id, hourly_rate=75.0)
        staff2 = Staff(name="Jane Smith", role_id=estimator_role.id, hourly_rate=65.0)
        db.session.add(staff1)
        db.session.add(staff2)
        db.session.commit()

        # Create test projects
        project1 = Project(
            name="Project Alpha",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            status="active",
            budget=500000.0
        )
        project2 = Project(
            name="Project Beta",
            status="planning"
        )
        db.session.add(project1)
        db.session.add(project2)
        db.session.commit()

        # Create test assignment
        assignment1 = Assignment(
            staff_id=staff1.id,
            project_id=project1.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            hours_per_week=40.0
        )
        db.session.add(assignment1)

        db.session.commit()

        return {
            'staff': [staff1, staff2],
            'projects': [project1, project2],
            'assignments': [assignment1],
            'roles': test_roles['roles']
        }


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, client):
        """Test health endpoint returns correct response"""
        response = client.get('/api/health')
        assert response.status_code == 200

        data = response.get_json()
        assert data['status'] == 'healthy'
        assert 'message' in data


class TestRoleEndpoints:
    """Test role API endpoints"""

    def test_get_roles_list(self, client, test_roles):
        """Test getting list of roles (public endpoint)"""
        response = client.get('/api/roles')
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 3  # At least our test data

    def test_get_roles_active_only(self, client, auth_headers, test_roles):
        """Test getting only active roles"""
        # First deactivate one role
        with client.application.app_context():
            role = Role.query.first()
            role.is_active = False
            db.session.commit()

        response = client.get('/api/roles?active_only=true')
        assert response.status_code == 200

        data = response.get_json()
        # Should have fewer roles than total
        for role in data:
            assert role['is_active'] == True

    def test_create_role(self, client, auth_headers):
        """Test creating a new role"""
        role_data = {
            'name': 'New Role',
            'hourly_cost': 50.0,
            'description': 'A new test role'
        }

        response = client.post('/api/roles', json=role_data, headers=auth_headers)
        assert response.status_code == 201

        data = response.get_json()
        assert data['name'] == 'New Role'
        assert data['hourly_cost'] == 50.0
        assert data['is_active'] == True

    def test_create_role_duplicate_name(self, client, auth_headers, test_roles):
        """Test creating role with duplicate name fails"""
        role_data = {
            'name': 'Manager',  # Already exists
            'hourly_cost': 50.0
        }

        response = client.post('/api/roles', json=role_data, headers=auth_headers)
        assert response.status_code == 409  # Conflict

    def test_create_role_validation_error(self, client, auth_headers):
        """Test creating role with missing required fields"""
        incomplete_data = {'name': 'Incomplete Role'}

        response = client.post('/api/roles', json=incomplete_data, headers=auth_headers)
        assert response.status_code == 400

        data = response.get_json()
        assert 'error' in data

    def test_get_role_by_id(self, client, test_roles):
        """Test getting a specific role"""
        with client.application.app_context():
            role = Role.query.filter_by(name="Manager").first()
            role_id = role.id

        response = client.get(f'/api/roles/{role_id}')
        assert response.status_code == 200

        data = response.get_json()
        assert data['name'] == 'Manager'

    def test_get_role_not_found(self, client):
        """Test getting non-existent role"""
        response = client.get('/api/roles/99999')
        assert response.status_code == 404

    def test_update_role(self, client, auth_headers, test_roles):
        """Test updating a role"""
        with client.application.app_context():
            role = Role.query.filter_by(name="Manager").first()
            role_id = role.id

        update_data = {
            'name': 'Senior Manager',
            'hourly_cost': 85.0,
            'description': 'Updated description'
        }

        response = client.put(f'/api/roles/{role_id}', json=update_data, headers=auth_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['name'] == 'Senior Manager'
        assert data['hourly_cost'] == 85.0

    def test_delete_role_with_no_staff(self, client, auth_headers, test_roles):
        """Test deleting a role with no staff assigned"""
        with client.application.app_context():
            role = Role.query.filter_by(name="Developer").first()  # No staff assigned
            role_id = role.id

        response = client.delete(f'/api/roles/{role_id}', headers=auth_headers)
        assert response.status_code == 200

    def test_delete_role_with_staff_fails(self, client, auth_headers, test_data):
        """Test deleting a role with staff assigned fails"""
        with client.application.app_context():
            role = Role.query.filter_by(name="Manager").first()  # Has staff assigned
            role_id = role.id

        response = client.delete(f'/api/roles/{role_id}', headers=auth_headers)
        assert response.status_code == 409  # Conflict


class TestStaffEndpoints:
    """Test staff API endpoints"""

    def test_get_staff_list(self, client, auth_headers, test_data):
        """Test getting list of staff"""
        response = client.get('/api/staff', headers=auth_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 2  # At least our test data

    def test_create_staff(self, client, auth_headers, test_roles):
        """Test creating a new staff member"""
        with client.application.app_context():
            dev_role = Role.query.filter_by(name="Developer").first()
            role_id = dev_role.id

        staff_data = {
            'name': 'New Employee',
            'role_id': role_id,
            'hourly_rate': 70.0  # Billable rate (higher than role cost)
        }

        response = client.post('/api/staff', json=staff_data, headers=auth_headers)
        assert response.status_code == 201

        data = response.get_json()
        assert data['name'] == 'New Employee'
        assert data['role'] == 'Developer'
        assert data['role_id'] == role_id
        assert data['hourly_rate'] == 70.0
        assert data['role_hourly_cost'] == 55.0  # From role

    def test_create_staff_validation_error(self, client, auth_headers):
        """Test creating staff with missing required fields"""
        incomplete_data = {'name': 'Incomplete Staff'}

        response = client.post('/api/staff', json=incomplete_data, headers=auth_headers)
        assert response.status_code == 400

        data = response.get_json()
        assert 'error' in data

    def test_create_staff_invalid_role_id(self, client, auth_headers):
        """Test creating staff with invalid role_id fails"""
        staff_data = {
            'name': 'Invalid Role Staff',
            'role_id': 99999,  # Non-existent role
            'hourly_rate': 50.0
        }

        response = client.post('/api/staff', json=staff_data, headers=auth_headers)
        assert response.status_code == 404  # Role not found

    def test_get_staff_by_id(self, client, auth_headers, test_data):
        """Test getting a specific staff member"""
        staff_id = test_data['staff'][0].id

        response = client.get(f'/api/staff/{staff_id}', headers=auth_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['id'] == staff_id
        assert data['name'] == 'John Doe'
        assert data['role'] == 'Manager'  # Role name from relationship
        assert 'role_hourly_cost' in data

    def test_get_staff_not_found(self, client, auth_headers):
        """Test getting non-existent staff"""
        response = client.get('/api/staff/99999', headers=auth_headers)
        assert response.status_code == 404

        data = response.get_json()
        assert 'error' in data

    def test_update_staff(self, client, auth_headers, test_data):
        """Test updating a staff member"""
        staff_id = test_data['staff'][0].id
        role_id = test_data['staff'][0].role_id
        update_data = {
            'name': 'Updated Name',
            'role_id': role_id,
            'hourly_rate': 80.0
        }

        response = client.put(f'/api/staff/{staff_id}', json=update_data, headers=auth_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['name'] == 'Updated Name'
        assert data['hourly_rate'] == 80.0

    def test_delete_staff(self, client, auth_headers, test_data):
        """Test deleting a staff member without assignments"""
        # Use staff2 which doesn't have assignments
        staff_id = test_data['staff'][1].id

        response = client.delete(f'/api/staff/{staff_id}', headers=auth_headers)
        assert response.status_code == 200

        # Verify deletion
        response = client.get(f'/api/staff/{staff_id}', headers=auth_headers)
        assert response.status_code == 404


class TestProjectEndpoints:
    """Test project API endpoints"""

    def test_get_projects_list(self, client, auth_headers, test_data):
        """Test getting list of projects"""
        response = client.get('/api/projects', headers=auth_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_create_project(self, client, auth_headers):
        """Test creating a new project"""
        project_data = {
            'name': 'New Test Project',
            'status': 'planning',
            'budget': 250000.0
        }

        response = client.post('/api/projects', json=project_data, headers=auth_headers)
        assert response.status_code == 201

        data = response.get_json()
        assert data['name'] == 'New Test Project'
        assert data['status'] == 'planning'

    def test_create_project_invalid_status(self, client, auth_headers):
        """Test creating project with invalid status"""
        invalid_data = {
            'name': 'Invalid Project',
            'status': 'invalid_status'
        }

        response = client.post('/api/projects', json=invalid_data, headers=auth_headers)
        assert response.status_code == 400

    def test_get_project_by_id(self, client, auth_headers, test_data):
        """Test getting a specific project"""
        project_id = test_data['projects'][0].id

        response = client.get(f'/api/projects/{project_id}', headers=auth_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['id'] == project_id
        assert data['name'] == 'Project Alpha'

    def test_update_project(self, client, auth_headers, test_data):
        """Test updating a project"""
        project_id = test_data['projects'][0].id
        update_data = {
            'name': 'Updated Project Name',
            'status': 'completed'
        }

        response = client.put(f'/api/projects/{project_id}', json=update_data, headers=auth_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['name'] == 'Updated Project Name'
        assert data['status'] == 'completed'


class TestAssignmentEndpoints:
    """Test assignment API endpoints"""

    def test_get_assignments_list(self, client, auth_headers, test_data):
        """Test getting list of assignments"""
        response = client.get('/api/assignments', headers=auth_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)

    def test_create_assignment(self, client, auth_headers, test_data):
        """Test creating a new assignment"""
        assignment_data = {
            'staff_id': test_data['staff'][0].id,
            'project_id': test_data['projects'][0].id,
            'start_date': '2024-04-01',
            'end_date': '2024-06-30',
            'hours_per_week': 35.0,
            'role_on_project': 'Lead Developer'
        }

        response = client.post('/api/assignments', json=assignment_data, headers=auth_headers)
        assert response.status_code == 201

        data = response.get_json()
        assert data['staff_id'] == test_data['staff'][0].id
        assert data['hours_per_week'] == 35.0

    def test_create_assignment_invalid_dates(self, client, auth_headers, test_data):
        """Test creating assignment with invalid date range"""
        invalid_data = {
            'staff_id': test_data['staff'][0].id,
            'project_id': test_data['projects'][0].id,
            'start_date': '2024-06-01',
            'end_date': '2024-05-01',  # End before start
            'hours_per_week': 40.0
        }

        response = client.post('/api/assignments', json=invalid_data, headers=auth_headers)
        assert response.status_code == 400


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_login_success(self, client):
        """Test successful login"""
        # Create test user first
        with client.application.app_context():
            user = User(username="login_test", email="login@test.com", password="testpass")
            db.session.add(user)
            db.session.commit()

        response = client.post('/api/auth/login', json={
            'username': 'login_test',
            'password': 'testpass'
        })
        assert response.status_code == 200

        data = response.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert 'user' in data

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'wrongpass'
        })
        assert response.status_code == 401

        data = response.get_json()
        assert 'error' in data

    def test_register_user(self, client, auth_headers):
        """Test registering a new user (requires admin)"""
        user_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'role': 'preconstruction'
        }

        response = client.post('/api/auth/register', json=user_data, headers=auth_headers)
        assert response.status_code == 201

        data = response.get_json()
        assert data['user']['username'] == 'newuser'

    def test_access_protected_route_without_auth(self, client):
        """Test accessing protected route without authentication"""
        response = client.get('/api/staff')
        assert response.status_code == 401

    def test_access_protected_route_with_auth(self, client, auth_headers):
        """Test accessing protected route with authentication"""
        response = client.get('/api/staff', headers=auth_headers)
        assert response.status_code == 200


class TestForecastingEndpoints:
    """Test forecasting API endpoints"""

    def test_get_project_forecast(self, client, auth_headers, test_data):
        """Test getting project forecast"""
        project_id = test_data['projects'][0].id

        response = client.get(f'/api/projects/{project_id}/forecast', headers=auth_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert 'forecast_period' in data or 'error' not in data

    def test_get_organization_forecast(self, client, auth_headers):
        """Test getting organization-wide forecast"""
        response = client.get('/api/forecasts/organization?start_date=2024-01-01&end_date=2024-12-31',
                             headers=auth_headers)
        assert response.status_code == 200

    def test_simulate_forecast(self, client, auth_headers, test_data):
        """Test forecast simulation"""
        simulation_data = {
            'project_id': test_data['projects'][0].id,
            'changes': {
                'add_staff': [{'role': 'Estimator', 'count': 1}]
            }
        }

        response = client.post('/api/forecasts/simulate', json=simulation_data, headers=auth_headers)
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__])
