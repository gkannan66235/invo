#!/bin/bash

# GST Service Center Management System - Docker Compose Helper Script
# Usage: ./docker-helper.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker Desktop first."
        exit 1
    fi
}

# Check if ports are available
check_ports() {
    local ports=(5432 6379 8000 9090)
    for port in "${ports[@]}"; do
        if lsof -i :$port > /dev/null 2>&1; then
            log_warning "Port $port is already in use. This may cause conflicts."
        fi
    done
}

# Build and start services
start_services() {
    log_info "Building and starting GST Service Center services..."
    
    check_docker
    check_ports
    
    # Build and start services
    docker-compose up --build -d
    
    log_info "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    if check_health; then
        log_success "All services are running successfully!"
        show_endpoints
    else
        log_error "Some services failed to start. Check logs with: docker-compose logs"
        exit 1
    fi
}

# Stop services
stop_services() {
    log_info "Stopping GST Service Center services..."
    docker-compose down
    log_success "Services stopped successfully!"
}

# Restart services
restart_services() {
    log_info "Restarting GST Service Center services..."
    docker-compose restart
    log_success "Services restarted successfully!"
}

# Check service health
check_health() {
    local healthy=true
    
    # Check database
    if docker-compose exec -T database pg_isready -U gst_user -d gst_service_center > /dev/null 2>&1; then
        log_success "Database is healthy"
    else
        log_error "Database is not healthy"
        healthy=false
    fi
    
    # Check backend API
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Backend API is healthy"
    else
        log_error "Backend API is not healthy"
        healthy=false
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is healthy"
    else
        log_error "Redis is not healthy"
        healthy=false
    fi
    
    $healthy
}

# Show service endpoints
show_endpoints() {
    echo
    log_info "Service Endpoints:"
    echo "  🚀 API Documentation: http://localhost:8000/docs"
    echo "  🏥 Health Check:     http://localhost:8000/health"
    echo "  🗄️  Database:         localhost:5432 (gst_user/gst_password_2023)"
    echo "  📦 Redis:            localhost:6379"
    echo "  📊 Prometheus:       http://localhost:9090"
    echo
}

# View logs
view_logs() {
    local service=${1:-""}
    if [ -z "$service" ]; then
        log_info "Showing logs for all services..."
        docker-compose logs -f --tail=100
    else
        log_info "Showing logs for $service..."
        docker-compose logs -f --tail=100 $service
    fi
}

# Run tests
run_tests() {
    log_info "Running tests in backend container..."
    if docker-compose exec backend pytest --tb=short; then
        log_success "All tests passed!"
    else
        log_error "Some tests failed!"
        exit 1
    fi
}

# Database operations
db_shell() {
    log_info "Opening database shell..."
    docker-compose exec database psql -U gst_user -d gst_service_center
}

db_backup() {
    local backup_file="./database/backups/backup_$(date +%Y%m%d_%H%M%S).sql"
    log_info "Creating database backup: $backup_file"
    docker-compose exec database pg_dump -U gst_user gst_service_center > "$backup_file"
    log_success "Database backup created: $backup_file"
}

# Cleanup
cleanup() {
    log_warning "This will remove all containers, volumes, and images. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        log_info "Cleaning up Docker resources..."
        docker-compose down -v --rmi all --remove-orphans
        log_success "Cleanup completed!"
    else
        log_info "Cleanup cancelled."
    fi
}

# Show help
show_help() {
    echo "GST Service Center Management System - Docker Helper"
    echo
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  start, up        Build and start all services"
    echo "  stop, down       Stop all services"
    echo "  restart          Restart all services"
    echo "  status           Check service health and show endpoints"
    echo "  logs [service]   View logs (optionally for specific service)"
    echo "  test             Run backend tests"
    echo "  db-shell         Open database shell"
    echo "  db-backup        Create database backup"
    echo "  cleanup          Remove all containers, volumes, and images"
    echo "  help             Show this help message"
    echo
    echo "Examples:"
    echo "  $0 start                 # Start all services"
    echo "  $0 logs backend          # View backend logs"
    echo "  $0 test                  # Run tests"
    echo "  $0 db-shell             # Access database"
    echo
}

# Main script logic
case "${1:-help}" in
    "start"|"up")
        start_services
        ;;
    "stop"|"down")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "status")
        check_health
        show_endpoints
        ;;
    "logs")
        view_logs $2
        ;;
    "test")
        run_tests
        ;;
    "db-shell")
        db_shell
        ;;
    "db-backup")
        db_backup
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|*)
        show_help
        ;;
esac