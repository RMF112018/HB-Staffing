# HB-Staffing Deployment Guide

This guide provides detailed instructions for deploying the HB-Staffing application to various platforms.

## Prerequisites

- Docker and Docker Compose (recommended)
- Git repository access
- Environment variables configured

## Environment Setup

### 1. Environment Variables

Copy the example environment file:
```bash
cp env.example .env
```

Edit `.env` with your production values:

```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-this-in-production
JWT_ACCESS_TOKEN_EXPIRES=900
JWT_REFRESH_TOKEN_EXPIRES=604800

# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/database

# CORS Configuration
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Redis Configuration
REDIS_URL=redis://your-redis-host:6379/0

# Logging
LOG_LEVEL=WARNING
```

### 2. Database Setup

#### PostgreSQL Setup
```sql
-- Create database
CREATE DATABASE hb_staffing;

-- Create user
CREATE USER hb_user WITH PASSWORD 'your_secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE hb_staffing TO hb_user;
```

#### Database Migrations
```bash
cd backend
export FLASK_APP=app.py
flask db upgrade
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

#### Production Docker Compose
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: hb_staffing
      POSTGRES_USER: hb_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - hb_network

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - hb_network

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://hb_user:${DB_PASSWORD}@db:5432/hb_staffing
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
    depends_on:
      - db
      - redis
    networks:
      - hb_network

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    environment:
      - REACT_APP_API_URL=https://api.yourdomain.com
    depends_on:
      - backend
    networks:
      - hb_network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - backend
      - frontend
    networks:
      - hb_network

volumes:
  postgres_data:
  redis_data:

networks:
  hb_network:
    driver: bridge
```

#### Deploy Commands
```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale services
docker-compose up -d --scale backend=3
```

### Option 2: Heroku Deployment

#### Backend Deployment
1. **Create Heroku Apps**
   ```bash
   heroku create hb-staffing-backend
   heroku create hb-staffing-frontend
   ```

2. **Configure Backend**
   ```bash
   # Set environment variables
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set JWT_SECRET_KEY=your-jwt-secret
   heroku config:set DATABASE_URL=your-heroku-postgres-url

   # Add PostgreSQL add-on
   heroku addons:create heroku-postgresql:hobby-dev

   # Deploy backend
   git push heroku main
   ```

3. **Configure Frontend**
   ```bash
   # Set API URL
   heroku config:set REACT_APP_API_URL=https://hb-staffing-backend.herokuapp.com

   # Deploy frontend (static build)
   cd frontend
   npm run build
   # Upload dist/ to Heroku or use buildpack
   ```

#### Heroku Buildpacks (for Frontend)
```bash
# Create static.json in frontend/
{
  "root": "dist/",
  "routes": {
    "/**": "index.html"
  }
}
```

### Option 3: AWS Deployment

#### Using Elastic Beanstalk

1. **Backend Deployment**
   ```bash
   # Install EB CLI
   pip install awsebcli

   # Initialize application
   cd backend
   eb init -p python-3.11 hb-staffing-backend

   # Create environment
   eb create production

   # Deploy
   eb deploy
   ```

2. **Frontend Deployment (S3 + CloudFront)**
   ```bash
   # Build frontend
   cd frontend
   npm run build

   # Create S3 bucket
   aws s3 mb s3://hb-staffing-frontend

   # Upload build files
   aws s3 sync dist/ s3://hb-staffing-frontend --delete

   # Enable static website hosting
   aws s3 website s3://hb-staffing-frontend --index-document index.html

   # Create CloudFront distribution
   aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
   ```

#### CloudFront Configuration
```json
{
  "CallerReference": "hb-staffing-frontend",
  "Origins": {
    "Quantity": 1,
    "Items": [{
      "DomainName": "hb-staffing-frontend.s3.amazonaws.com",
      "Id": "S3-hb-staffing-frontend",
      "CustomOriginConfig": {
        "HTTPPort": 80,
        "HTTPSPort": 443,
        "OriginProtocolPolicy": "http-only"
      }
    }]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-hb-staffing-frontend",
    "ViewerProtocolPolicy": "redirect-to-https",
    "MinTTL": 0,
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {
        "Forward": "none"
      }
    }
  },
  "Enabled": true
}
```

### Option 4: DigitalOcean App Platform

1. **Connect Repository**
   - Go to DigitalOcean App Platform
   - Connect your GitHub repository

2. **Configure Backend Service**
   ```yaml
   name: hb-staffing-backend
   source_dir: backend/
   github:
     repo: your-username/HB-Staffing
     branch: main
   run_command: gunicorn app:create_app() --bind 0.0.0.0:$PORT
   environment_slug: python
   instance_count: 1
   instance_size_slug: basic-xxs
   envs:
     - key: FLASK_ENV
       value: production
     - key: DATABASE_URL
       value: ${database.DATABASE_URL}
   databases:
     - name: hb-staffing-db
       engine: PG
       version: "15"
   ```

3. **Configure Frontend Service**
   ```yaml
   name: hb-staffing-frontend
   source_dir: frontend/
   github:
     repo: your-username/HB-Staffing
     branch: main
   build_command: npm run build
   static_site_generator: create-react-app
   envs:
     - key: REACT_APP_API_URL
       value: ${hb-staffing-backend.PUBLIC_URL}
   ```

## SSL/TLS Configuration

### Let's Encrypt (Automated)
```bash
# Using Certbot with Docker
docker run -it --rm --name certbot \
  -v "/etc/letsencrypt:/etc/letsencrypt" \
  -v "/var/lib/letsencrypt:/var/lib/letsencrypt" \
  --network host \
  certbot/certbot certonly --standalone -d yourdomain.com
```

### Nginx SSL Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Monitoring & Logging

### Application Monitoring
```bash
# Health check endpoint
curl https://yourdomain.com/api/health

# Application logs
docker-compose logs -f backend

# Database monitoring
docker stats
```

### Log Aggregation
```python
# In backend/app.py
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('logs/hb_staffing.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
```

## Backup & Recovery

### Database Backup
```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U hb_user hb_staffing > backup_$DATE.sql

# Upload to S3
aws s3 cp backup_$DATE.sql s3://your-backup-bucket/
```

### Recovery
```bash
# Restore from backup
psql -h localhost -U hb_user hb_staffing < backup_file.sql
```

## Performance Optimization

### Database Optimization
```sql
-- Create indexes for better performance
CREATE INDEX idx_staff_role ON staff(role);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_assignments_staff_project ON assignments(staff_id, project_id);

-- Analyze tables
ANALYZE staff, projects, assignments;
```

### Caching Strategy
```python
from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL')
})

@cache.memoize(timeout=300)  # Cache for 5 minutes
def expensive_forecast_calculation(project_id):
    # Expensive calculation here
    pass
```

## Security Checklist

- [ ] Environment variables configured securely
- [ ] Database credentials rotated
- [ ] SSL/TLS certificates installed
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Security headers set
- [ ] Database backups scheduled
- [ ] Monitoring alerts configured
- [ ] Regular security updates applied

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check database connectivity
   docker-compose exec db pg_isready -U hb_user -d hb_staffing
   ```

2. **Application Won't Start**
   ```bash
   # Check logs
   docker-compose logs backend

   # Verify environment variables
   docker-compose exec backend env
   ```

3. **Frontend Build Fails**
   ```bash
   # Clear npm cache
   cd frontend && npm cache clean --force && npm install
   ```

4. **SSL Certificate Issues**
   ```bash
   # Renew certificates
   certbot renew

   # Restart nginx
   docker-compose restart nginx
   ```

## Support

For deployment support:
- Email: deployment@hb-staffing.com
- Issues: [GitHub Issues](https://github.com/your-username/HB-Staffing/issues)
- Documentation: [Main README](../README.md)
