#!/bin/bash

# Deploy with Docker
echo "🐳 Deploying NewsMonitor Pro with Docker..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with your production environment variables"
    exit 1
fi

# Build the Docker image
echo "🏗️ Building Docker image..."
docker build -t newsmonitor-pro .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✅ Docker build successful!"

# Run with Docker Compose
echo "🚀 Starting services with Docker Compose..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Docker Compose failed"
    exit 1
fi

echo "✅ Services started successfully!"
echo ""
echo "📋 Service URLs:"
echo "- Application: http://localhost:5000"
echo "- With Nginx: http://localhost:80"
echo ""
echo "🔧 Management commands:"
echo "- View logs: docker-compose logs -f"
echo "- Stop services: docker-compose down"
echo "- Restart: docker-compose restart"
echo "- Update: docker-compose pull && docker-compose up -d"
echo ""
echo "✅ NewsMonitor Pro is now running!"
