# Docker Compose Guide - GST Service Center Management System

## 🐳 Building and Running the Application

### Prerequisites

- Docker Desktop installed and running
- Docker Compose v2.0+ (comes with Docker Desktop)
- At least 4GB available RAM
- Ports 5432, 6379, 8000, 9090 available on your machine

### Quick Start

1. **Clone and navigate to the project directory:**

   ```bash
   cd /Users/kannan/Projects/Devops/AI/invo
   ```

2. **Build and start all services:**

   ```bash
   docker-compose up --build -d
   ```

3. **Check service status:**

   ```bash
   docker-compose ps
   ```

4. **View logs:**

   ```bash
   # All services
   docker-compose logs -f

   # Specific service
   docker-compose logs -f backend
   docker-compose logs -f database
   ```

### Step-by-Step Build Process

#### 1. Build Services Individually (Optional)

```bash
# Build database service
docker-compose build database

# Build backend service
docker-compose build backend

# Build all services
docker-compose build
```

#### 2. Start Services in Order

```bash
# Start database first (with dependencies)
docker-compose up -d database

# Wait for database to be healthy, then start backend
docker-compose up -d backend

# Start remaining services
docker-compose up -d redis prometheus
```

#### 3. Or Start Everything at Once

```bash
# Start all services (recommended)
docker-compose up -d

# With build (if code changed)
docker-compose up --build -d
```

### Service Details

#### 🗄️ **PostgreSQL Database**

- **Port:** 5432
- **Database:** gst_service_center
- **User:** gst_user
- **Password:** gst_password_2023
- **Health Check:** Automated with 30s intervals

#### 🚀 **FastAPI Backend**

- **Port:** 8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Auto-reload:** Enabled in development mode

#### 📦 **Redis Cache**

- **Port:** 6379
- **Persistence:** Enabled with AOF
- **Use:** Session management and caching

#### 📊 **Prometheus Monitoring**

- **Port:** 9090
- **Dashboard:** http://localhost:9090
- **Metrics:** Application and infrastructure monitoring

### Environment Configuration

#### Development Environment Variables (docker-compose.yml):

```yaml
DATABASE_URL: postgresql+asyncpg://gst_user:gst_password_2023@database:5432/gst_service_center
SECRET_KEY: your-secret-key-change-in-production
ENVIRONMENT: development
LOG_LEVEL: INFO
CORS_ORIGINS: http://localhost:3000,http://localhost:8080
```

#### Production Environment Variables:

Create a `.env` file for production:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
SECRET_KEY=your-very-secure-secret-key
ENVIRONMENT=production
LOG_LEVEL=WARNING
CORS_ORIGINS=https://yourdomain.com
```

### Common Operations

#### 🔍 **Health Checks**

```bash
# Check all service health
docker-compose ps

# Database health
curl http://localhost:8000/health

# Backend API health
curl http://localhost:8000/health

# Detailed service status
docker-compose exec backend python -c "from src.config.database import check_database_connection; print(check_database_connection())"
```

#### 📊 **Monitoring and Logs**

```bash
# Real-time logs
docker-compose logs -f --tail=100

# Service-specific logs
docker-compose logs -f backend
docker-compose logs -f database

# Log analysis
docker-compose logs backend | grep ERROR
docker-compose logs database | grep FATAL
```

#### 🛠️ **Development Operations**

```bash
# Restart specific service
docker-compose restart backend

# Rebuild and restart after code changes
docker-compose up --build -d backend

# Execute commands in containers
docker-compose exec backend bash
docker-compose exec database psql -U gst_user -d gst_service_center

# Install new Python packages
docker-compose exec backend pip install new-package
docker-compose restart backend
```

#### 🗄️ **Database Operations**

```bash
# Access PostgreSQL CLI
docker-compose exec database psql -U gst_user -d gst_service_center

# Run SQL file
docker-compose exec database psql -U gst_user -d gst_service_center -f /backups/script.sql

# Create database backup
docker-compose exec database pg_dump -U gst_user gst_service_center > backup.sql

# View database logs
docker-compose logs database
```

#### 🧪 **Testing**

```bash
# Run tests in container
docker-compose exec backend pytest

# Run specific test file
docker-compose exec backend pytest tests/contract/test_auth_login.py

# Run with coverage
docker-compose exec backend pytest --cov=src --cov-report=html

# Run performance tests
docker-compose exec backend python -m tests.performance
```

### Data Persistence

#### Volumes Created:

- `postgres_data`: Database files persist across container restarts
- `redis_data`: Redis cache and session data
- `prometheus_data`: Monitoring metrics and configuration
- `./logs`: Application logs mounted from host

#### Backup Strategy:

```bash
# Database backup
docker-compose exec database pg_dump -U gst_user gst_service_center > ./database/backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Volume backup
docker run --rm -v invo_postgres_data:/source -v $(pwd)/database/backups:/backup alpine tar czf /backup/postgres_volume_backup.tar.gz -C /source .
```

### Troubleshooting

#### 🚨 **Common Issues**

1. **Port Already in Use:**

   ```bash
   # Find process using port
   lsof -i :8000
   lsof -i :5432

   # Kill process or change port in docker-compose.yml
   ```

2. **Database Connection Issues:**

   ```bash
   # Check database logs
   docker-compose logs database

   # Verify database is ready
   docker-compose exec database pg_isready -U gst_user -d gst_service_center

   # Restart database service
   docker-compose restart database
   ```

3. **Backend Service Won't Start:**

   ```bash
   # Check backend logs
   docker-compose logs backend

   # Check Python dependencies
   docker-compose exec backend pip list

   # Rebuild with no cache
   docker-compose build --no-cache backend
   ```

4. **Memory Issues:**

   ```bash
   # Check Docker memory usage
   docker stats

   # Increase Docker Desktop memory allocation
   # Docker Desktop > Settings > Resources > Memory
   ```

#### 🔧 **Performance Optimization**

1. **Build Optimization:**

   ```bash
   # Use build cache
   docker-compose build

   # Multi-stage builds already implemented
   # No-cache rebuild only when needed
   docker-compose build --no-cache
   ```

2. **Runtime Optimization:**

   ```bash
   # Monitor resource usage
   docker stats

   # Adjust container limits in docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 512M
         cpus: '0.5'
   ```

### Cleanup

#### 🧹 **Stop and Remove**

```bash
# Stop services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v

# Remove images too
docker-compose down --rmi all

# Complete cleanup
docker-compose down -v --rmi all --remove-orphans
```

### Production Deployment

#### 🚀 **Production Considerations**

1. **Security:**

   - Change default passwords
   - Use secrets management
   - Enable SSL/TLS
   - Configure firewall rules

2. **Performance:**

   - Use production WSGI server (already configured with uvicorn)
   - Enable connection pooling
   - Configure reverse proxy (nginx)
   - Set up load balancing

3. **Monitoring:**
   - Configure log aggregation
   - Set up alerting
   - Monitor resource usage
   - Configure backup automation

#### Example Production Override:

```yaml
# docker-compose.prod.yml
version: "3.8"
services:
  backend:
    environment:
      ENVIRONMENT: production
      LOG_LEVEL: WARNING
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
          cpus: "1.0"

  database:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
```

### API Access

Once running, access the application at:

- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Database:** localhost:5432
- **Redis:** localhost:6379
- **Prometheus:** http://localhost:9090

### Constitutional Compliance ✅

The Docker setup ensures constitutional requirements:

- **<200ms Response Times:** Monitored via health checks and logging
- **High Availability:** Health checks and restart policies
- **Security:** Non-root users, minimal attack surface
- **Observability:** Comprehensive logging and monitoring
- **Performance:** Optimized multi-stage builds and resource limits
