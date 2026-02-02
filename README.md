# HB-Staffing

A lightweight web application for forecasting staffing needs in construction projects. Enables preconstruction teams and leadership to manage staff assignments, predict resource requirements, calculate costs, and generate comprehensive reports.

## Features

- **Staff Management**: Complete CRUD operations for staff members with role and skill tracking
- **Project Management**: Project lifecycle management with status tracking and budget monitoring
- **Assignment Management**: Link staff to projects with date ranges and utilization tracking
- **Forecasting Engine**: Advanced algorithms for predicting staffing needs and costs
- **Interactive Dashboard**: Real-time metrics, charts, and project timelines
- **Reporting System**: CSV/PDF exports, staffing gap analysis, and custom reports
- **User Authentication**: JWT-based authentication with role-based access control
- **Responsive UI**: Modern React interface with loading states and error handling

## Technology Stack

### Backend
- **Python 3.11+**
- **Flask** - Web framework
- **SQLAlchemy** - ORM
- **PostgreSQL** - Production database
- **JWT** - Authentication
- **Flask-Limiter** - Rate limiting

### Frontend
- **React 19** - UI framework
- **Vite** - Build tool
- **Chart.js** - Data visualization
- **Axios** - HTTP client
- **React Router** - Navigation

### Infrastructure
- **Docker** - Containerization
- **Nginx** - Production web server
- **Redis** - Caching and rate limiting
- **Gunicorn** - WSGI server

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Using Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/HB-Staffing.git
   cd HB-Staffing
   ```

2. **Start the application**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - PgAdmin: http://localhost:5050 (admin@hb-staffing.com / admin123)

4. **Default admin credentials**
   - Username: `admin`
   - Password: `admin123!`

### Local Development Setup

1. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp ../env.example .env  # Configure environment variables
   flask run
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Deployment

### Production Deployment Options

#### 1. Heroku Deployment

**Backend:**
```bash
# Install Heroku CLI and login
heroku create your-app-name-backend

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set DATABASE_URL=your_postgres_url
heroku config:set SECRET_KEY=your_secret_key
heroku config:set JWT_SECRET_KEY=your_jwt_secret

# Deploy
git push heroku main
```

**Frontend:**
```bash
# Build and deploy to Netlify/Vercel
npm run build
# Upload dist/ folder to your hosting provider
```

#### 2. AWS Deployment

**Using Elastic Beanstalk:**
```bash
# Install EB CLI
pip install awsebcli

# Initialize EB application
eb init -p python-3.11 hb-staffing-backend

# Create environment
eb create hb-staffing-prod

# Deploy
eb deploy
```

**Frontend on S3 + CloudFront:**
```bash
# Build the frontend
npm run build

# Upload to S3 bucket
aws s3 sync dist/ s3://your-bucket-name --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths "/*"
```

#### 3. DigitalOcean App Platform

1. Connect your GitHub repository
2. Configure environment variables
3. Set build commands and run commands
4. Deploy automatically on push

### Environment Variables

Copy `env.example` to `.env` and configure:

```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-change-this
JWT_SECRET_KEY=your-jwt-secret-key-change-this

# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Redis (for production)
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## API Documentation

### Authentication Endpoints

```bash
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/register  # Admin only
GET  /api/auth/me
POST /api/auth/logout
```

### Core API Endpoints

```bash
# Staff Management
GET    /api/staff
POST   /api/staff
GET    /api/staff/:id
PUT    /api/staff/:id
DELETE /api/staff/:id

# Project Management
GET    /api/projects
POST   /api/projects
GET    /api/projects/:id
PUT    /api/projects/:id
DELETE /api/projects/:id

# Assignment Management
GET    /api/assignments
POST   /api/assignments
GET    /api/assignments/:id
PUT    /api/assignments/:id
DELETE /api/assignments/:id

# Forecasting & Reports
GET    /api/projects/:id/forecast
GET    /api/forecasts/organization
POST   /api/forecasts/simulate
GET    /api/forecasts/gaps
```

## Development

### Running Tests

```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
npm test
```

### Database Migrations

```bash
cd backend
export FLASK_APP=app.py
flask db migrate -m "Migration message"
flask db upgrade
```

### Code Quality

```bash
# Frontend linting
cd frontend
npm run lint

# Format code
npm run format
```

## Security Features

- JWT-based authentication with refresh tokens
- Role-based access control (preconstruction, leadership, admin)
- Rate limiting on API endpoints
- Input validation and sanitization
- CORS protection
- Security headers (CSP, HSTS, etc.)
- Password hashing with bcrypt

## Performance Optimizations

- Database query optimization
- Redis caching for expensive operations
- Frontend code splitting and lazy loading
- Gzip compression
- CDN-ready static asset serving

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please contact:
- Email: support@hb-staffing.com
- Issues: [GitHub Issues](https://github.com/your-username/HB-Staffing/issues)

## Roadmap

- [ ] Mobile app development
- [ ] Advanced analytics with ML
- [ ] Integration with project management tools
- [ ] Real-time notifications
- [ ] Multi-tenant architecture
- [ ] Advanced reporting with custom dashboards