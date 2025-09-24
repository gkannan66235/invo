#!/bin/bash

# Quick Docker Rebuild Script for GST Service Center
# This script rebuilds containers and installs dependencies

echo "🏗️  Rebuilding GST Service Center with updated dependencies..."

# Stop existing containers
echo "⏹️  Stopping existing containers..."
docker-compose down

# Remove existing images to force rebuild
echo "🗑️  Removing existing images..."
docker-compose down --rmi all

# Build with no cache to ensure fresh install
echo "🔨 Building containers with no cache..."
docker-compose build --no-cache

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to start
echo "⏱️  Waiting for services to initialize..."
sleep 15

# Check service health
echo "🏥 Checking service health..."

echo "📋 Service Status:"
docker-compose ps

echo ""
echo "📊 Container Logs (last 10 lines):"
echo "--- Backend Logs ---"
docker-compose logs --tail=10 backend

echo ""
echo "--- Database Logs ---"
docker-compose logs --tail=10 database

echo ""
echo "🌐 Service Endpoints:"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Health Check:     http://localhost:8000/health"
echo "  • Database:         localhost:5432"
echo "  • Prometheus:       http://localhost:9090"

echo ""
echo "✅ Rebuild complete! Check the logs above for any errors."