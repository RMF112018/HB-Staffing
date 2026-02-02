# HB-Staffing API Documentation

## Overview

The HB-Staffing API provides RESTful endpoints for managing construction project staffing, forecasting, and reporting. All endpoints require authentication except for the health check.

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Authentication Endpoints

#### POST /api/auth/login
Authenticate a user and receive access/refresh tokens.

**Request:**
```json
{
  "username": "admin",
  "password": "admin123!"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@hb-staffing.com",
    "role": "admin"
  }
}
```

#### POST /api/auth/refresh
Refresh an access token using a refresh token.

**Response:**
```json
{
  "access_token": "eyJ0eXAi..."
}
```

#### POST /api/auth/register
Register a new user (admin only).

**Request:**
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepassword",
  "role": "preconstruction"
}
```

## Core Resources

### Staff Management

#### GET /api/staff
Get all staff members with optional filtering.

**Query Parameters:**
- `role` - Filter by role
- `available_from` - Filter by availability start date
- `available_to` - Filter by availability end date
- `skills` - Filter by skills (comma-separated)

**Response:**
```json
[
  {
    "id": 1,
    "name": "John Smith",
    "role": "Project Manager",
    "hourly_rate": 75.0,
    "availability_start": "2024-01-01",
    "availability_end": null,
    "skills": ["Leadership", "Planning"],
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### POST /api/staff
Create a new staff member.

**Request:**
```json
{
  "name": "Jane Doe",
  "role": "Estimator",
  "hourly_rate": 65.0,
  "availability_start": "2024-01-01",
  "skills": ["Estimation", "Excel"]
}
```

#### GET /api/staff/:id
Get a specific staff member.

#### PUT /api/staff/:id
Update a staff member.

#### DELETE /api/staff/:id
Delete a staff member (only if no active assignments).

### Project Management

#### GET /api/projects
Get all projects with optional filtering.

**Query Parameters:**
- `status` - Filter by status (planning, active, completed, etc.)

**Response:**
```json
[
  {
    "id": 1,
    "name": "Downtown Office Complex",
    "start_date": "2024-06-01",
    "end_date": "2025-06-01",
    "status": "planning",
    "budget": 5000000.0,
    "location": "Downtown City Center"
  }
]
```

#### POST /api/projects
Create a new project.

**Request:**
```json
{
  "name": "New Construction Project",
  "start_date": "2024-07-01",
  "end_date": "2025-07-01",
  "status": "planning",
  "budget": 3000000.0,
  "location": "Suburb Area"
}
```

### Assignment Management

#### GET /api/assignments
Get all assignments with optional filtering.

**Query Parameters:**
- `staff_id` - Filter by staff member
- `project_id` - Filter by project

**Response:**
```json
[
  {
    "id": 1,
    "staff_id": 1,
    "project_id": 1,
    "start_date": "2024-06-01",
    "end_date": "2024-12-01",
    "hours_per_week": 40.0,
    "role_on_project": "Project Manager",
    "staff_name": "John Smith",
    "project_name": "Downtown Office Complex"
  }
]
```

#### POST /api/assignments
Create a new assignment.

**Request:**
```json
{
  "staff_id": 1,
  "project_id": 1,
  "start_date": "2024-06-01",
  "end_date": "2024-12-01",
  "hours_per_week": 40.0,
  "role_on_project": "Project Manager"
}
```

### Forecasting & Analytics

#### GET /api/projects/:id/forecast
Get staffing forecast for a specific project.

**Query Parameters:**
- `start_date` - Forecast start date
- `end_date` - Forecast end date

**Response:**
```json
{
  "project_id": 1,
  "forecast_period": {
    "start": "2024-06-01",
    "end": "2025-06-01"
  },
  "weekly_forecast": [
    {
      "week_start": "2024-06-01",
      "required_fte": 2.5,
      "available_staff": 2,
      "gap": 0.5
    }
  ],
  "total_cost": 150000.0,
  "recommendations": ["Consider hiring additional estimator"]
}
```

#### GET /api/forecasts/organization
Get organization-wide staffing forecast.

**Query Parameters:**
- `start_date` - Required forecast start date
- `end_date` - Required forecast end date

#### POST /api/forecasts/simulate
Simulate "what-if" scenarios.

**Request:**
```json
{
  "project_id": 1,
  "changes": {
    "add_staff": [
      {
        "role": "Estimator",
        "count": 1,
        "start_date": "2024-07-01"
      }
    ],
    "extend_project": "2025-08-01"
  }
}
```

#### GET /api/forecasts/gaps
Detect staffing gaps across all projects.

**Query Parameters:**
- `project_id` - Specific project (optional)
- `start_date` - Analysis start date
- `end_date` - Analysis end date

### Reporting

#### GET /api/projects/:id/cost
Get cost analysis for a project.

**Response:**
```json
{
  "project_id": 1,
  "total_budget": 5000000.0,
  "allocated_budget": 3500000.0,
  "remaining_budget": 1500000.0,
  "forecast_cost": 4200000.0,
  "variance": -700000.0,
  "staff_costs": [
    {
      "staff_name": "John Smith",
      "role": "Project Manager",
      "hours": 2080,
      "hourly_rate": 75.0,
      "total_cost": 156000.0
    }
  ]
}
```

## Error Handling

The API returns consistent error responses:

```json
{
  "error": {
    "type": "ValidationError",
    "message": "Invalid input data",
    "details": {
      "field": "email"
    }
  }
}
```

### Common Error Types
- `ValidationError` - Invalid input data
- `NotFoundError` - Resource not found
- `UnauthorizedError` - Authentication required
- `ForbiddenError` - Insufficient permissions
- `ConflictError` - Operation conflicts with current state

## Rate Limiting

API endpoints are rate limited:
- General endpoints: 200 requests/day, 50 requests/hour
- Authentication endpoints: 10 requests/hour

## Data Formats

### Dates
All dates are in ISO 8601 format: `YYYY-MM-DD`

### Skills
Skills are stored as JSON arrays of strings

### Pagination
List endpoints support pagination (future enhancement)

## Versioning

The API uses URL versioning. Current version: v1

All endpoints are prefixed with `/api/`

## Support

For API support or questions:
- Email: api-support@hb-staffing.com
- Documentation: https://github.com/your-username/HB-Staffing/docs
