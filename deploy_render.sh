#!/bin/bash

# Deploy to Render.com using uv package manager
echo "🚀 Deploying NewsMonitor Pro to Render.com with uv..."

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Check if render.yaml exists
if [ ! -f "render.yaml" ]; then
    echo "❌ render.yaml not found!"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with your production environment variables"
    exit 1
fi

# Validate environment variables
echo "🔧 Validating environment variables..."
uv run python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

required_vars = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'FLASK_SECRET_KEY', 'OPENROUTER_API_KEY']
missing = []

for var in required_vars:
    if not os.getenv(var):
        missing.append(var)

if missing:
    print(f'❌ Missing required environment variables: {missing}')
    exit(1)
else:
    print('✅ All required environment variables are set')
"

if [ $? -ne 0 ]; then
    echo "Fix environment variables before deploying"
    exit 1
fi

# Build and test locally first
echo "🏗️ Building and testing locally..."
docker build -t newsmonitor-test .
if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✅ Build successful!"

# Instructions for Render deployment
echo ""
echo "📋 Manual Steps for Render.com Deployment:"
echo "1. Push your code to GitHub"
echo "2. Connect your GitHub repository to Render.com"
echo "3. Set the following environment variables in Render:"
echo "   - GOOGLE_CLIENT_ID"
echo "   - GOOGLE_CLIENT_SECRET"
echo "   - FLASK_SECRET_KEY"
echo "   - OPENROUTER_API_KEY"
echo "   - GOOGLE_REDIRECT_URI (set to your Render URL + /oauth2callback)"
echo "4. Deploy the service"
echo ""
echo "🌐 Remember to:"
echo "- Update OAuth redirect URI in Google Cloud Console"
echo "- Use HTTPS URLs in production"
echo "- Set up monitoring and alerts"
echo ""
echo "✅ Ready for Render.com deployment!"
