#!/bin/bash

# VYAYAM Strength Training System - Setup Script
# This script sets up the complete Django project

echo "========================================="
echo "VYAYAM Strength Training System Setup"
echo "========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

echo "✓ Virtual environment created and activated"
echo ""

# Install Django
echo "Installing Django..."
pip install --quiet django==4.2

echo "✓ Django installed"
echo ""

# Create necessary directories
echo "Creating project structure..."
mkdir -p strength_app/backend
mkdir -p strength_app/templates/strength_app
mkdir -p strength_app/static/strength_app/{css,js}
mkdir -p media
mkdir -p staticfiles

echo "✓ Directory structure created"
echo ""

# Run Django migrations
echo "Running database migrations..."
cd vyayam_django 2>/dev/null || true
python manage.py makemigrations --no-input
python manage.py migrate --no-input
python manage.py seed_food_database

echo "✓ Database migrations completed"
echo ""

# Create superuser prompt
echo "========================================="
echo "Admin Account Setup"
echo "========================================="
echo ""
echo "Create an admin account for accessing the Django admin panel?"
read -p "Create admin now? (y/n): " create_admin

if [[ $create_admin == "y" || $create_admin == "Y" ]]; then
    python manage.py createsuperuser
    echo ""
    echo "✓ Admin account created"
else
    echo "You can create an admin account later with:"
    echo "  python manage.py createsuperuser"
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "To start the development server:"
echo "  1. Activate virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Start server:"
echo "     cd vyayam_django"
echo "     python manage.py runserver"
echo ""
echo "  3. Access the application:"
echo "     - Main app: http://127.0.0.1:8000/"
echo "     - Admin panel: http://127.0.0.1:8000/admin/"
echo ""
echo "========================================="
