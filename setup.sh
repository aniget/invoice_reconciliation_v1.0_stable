#!/bin/bash
# Quick Start Script for Invoice Reconciliation System

echo "=========================================="
echo "Invoice Reconciliation System - Setup"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found. Please install Python 3.7+"
    exit 1
fi

echo "[SUCCESS] Python 3 found: $(python3 --version)"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q -r requirements.txt

if [ $? -eq 0 ]; then
    echo "[SUCCESS] Dependencies installed"
else
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi

# Create example directories
echo ""
echo "Creating directory structure..."
mkdir -p input_evd input_pdf output

echo "[SUCCESS] Directories created"

echo ""
echo "=========================================="
echo "[SUCCESS] Setup Complete!"
echo "=========================================="
echo ""
echo "To start the application:"
echo "  python app.py"
echo ""
echo "Then open your browser to:"
echo "  http://localhost:7860"
echo ""
echo "For help, see:"
echo "  README.md     - Quick start"
echo "  USER_GUIDE.md - Detailed usage"
echo ""
echo "=========================================="
