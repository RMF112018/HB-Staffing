# HB-Staffing Documentation

This directory contains comprehensive documentation for the HB-Staffing application.

## Documentation Index

### API Documentation
- [API Reference](API.md) - Complete API endpoint documentation with examples
- [Authentication Guide](API.md#authentication) - JWT authentication details

### Deployment Documentation
- [Deployment Guide](DEPLOYMENT.md) - Multi-platform deployment instructions
- [Docker Setup](DEPLOYMENT.md#option-1-docker-compose-recommended) - Containerization guide
- [Production Configuration](DEPLOYMENT.md#environment-setup) - Environment variables and settings

### Development Documentation
- [Main README](../README.md) - Installation, setup, and usage guide
- [Makefile](../Makefile) - Development commands and shortcuts
- [Testing](README.md#testing) - Test suite documentation

## Quick Start

### For Developers
1. Clone the repository
2. Follow the [installation guide](../README.md#quick-start)
3. Run `make dev` to start development servers
4. Run `make test` to execute test suite

### For Deployment
1. Review [deployment prerequisites](DEPLOYMENT.md#prerequisites)
2. Choose deployment platform
3. Follow platform-specific instructions
4. Configure environment variables

## Architecture Overview

```
HB-Staffing/
├── backend/          # Flask API server
│   ├── app.py       # Main application
│   ├── models.py    # Database models
│   ├── routes.py    # API endpoints
│   ├── auth.py      # Authentication & authorization
│   ├── engine.py    # Forecasting algorithms
│   └── tests/       # Test suite
├── frontend/         # React client application
│   ├── src/         # Source code
│   └── dist/        # Production build
├── docs/            # Documentation
└── docker/          # Containerization files
```

## Key Features

### Backend Features
- **RESTful API** with comprehensive endpoints
- **JWT Authentication** with role-based access control
- **Advanced Forecasting** engine for staffing predictions
- **Database Migrations** with Flask-Migrate
- **Rate Limiting** and security headers
- **Comprehensive Testing** suite with pytest

### Frontend Features
- **Modern React** application with hooks
- **Responsive Design** for all device types
- **Interactive Charts** with Chart.js
- **Form Validation** with error handling
- **Loading States** and error boundaries
- **API Integration** with retry logic

### DevOps Features
- **Docker Support** for consistent environments
- **Production Builds** optimized for performance
- **Environment Configuration** for different stages
- **Health Checks** and monitoring endpoints
- **Multi-platform Deployment** support

## Support

- **Issues**: [GitHub Issues](https://github.com/your-username/HB-Staffing/issues)
- **Documentation**: [Main README](../README.md)
- **API Docs**: [API Reference](API.md)
- **Deployment**: [Deployment Guide](DEPLOYMENT.md)

## Contributing

See the main README for contribution guidelines and development setup instructions.
