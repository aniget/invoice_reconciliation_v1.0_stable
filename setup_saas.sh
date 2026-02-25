#!/bin/bash
# SaaS Setup Script
# Sets up the multi-tenant SaaS infrastructure

set -e

echo "========================================="
echo "Invoice Reconciliation SaaS Setup"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements-saas.txt
echo "✓ Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    
    # Generate random secrets
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Update .env with generated secrets
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/dev-secret-key-CHANGE-IN-PRODUCTION-to-random-string/$SECRET_KEY/" .env
        sed -i '' "s/jwt-secret-key-CHANGE-IN-PRODUCTION-to-random-string/$JWT_SECRET_KEY/" .env
    else
        # Linux
        sed -i "s/dev-secret-key-CHANGE-IN-PRODUCTION-to-random-string/$SECRET_KEY/" .env
        sed -i "s/jwt-secret-key-CHANGE-IN-PRODUCTION-to-random-string/$JWT_SECRET_KEY/" .env
    fi
    
    echo "✓ .env file created with random secrets"
else
    echo "✓ .env file already exists"
fi

# Create necessary directories
echo ""
echo "Creating storage directories..."
mkdir -p uploads reports temp logs
echo "✓ Storage directories created"

# Initialize database
echo ""
echo "Initializing database..."
python3 -c "
from saas_config import init_db
init_db()
print('✓ Database initialized')
"

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start the API server:"
echo "   python -m saas_api.main"
echo ""
echo "2. Visit the API docs:"
echo "   http://localhost:8000/docs"
echo ""
echo "3. Register your first tenant:"
echo "   curl -X POST http://localhost:8000/api/v1/auth/register \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{...}'"
echo ""
echo "4. See SAAS_ARCHITECTURE.md for more details"
echo ""
