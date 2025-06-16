#!/bin/bash
# check_env.sh - Environment verification script for AI-DLC Prompt Template Tool
#
# This script performs the following actions for "Subphase 0.1: Project Initialization & Environment Management":
# 1. Uses `uv` to install dependencies listed in pyproject.toml (both main and dev dependencies)
# 2. Verifies that the active Python version within the `uv` environment is Python 3.12
# 3. Exits with status code 0 if both checks pass, non-zero otherwise
#
# :Technology:uv
# :Technology:Python 3.12
# :Context: Environment setup verification to mitigate :DependencyIssues and :CompatibilityIssue

# Set error handling
set -e
set -o pipefail

# Function to print colored output
print_status() {
  local status=$1
  local message=$2
  
  if [ $status -eq 0 ]; then
    echo -e "\033[32m✅ $message\033[0m"  # Green
  else
    echo -e "\033[31m❌ $message\033[0m"  # Red
  fi
}

# Track overall status
OVERALL_STATUS=0

echo "=== AI-DLC Environment Check ==="
echo "Checking environment for Subphase 0.1: Project Initialization & Environment Management"
echo ""

# Step 1: Install dependencies with uv
echo "Step 1: Installing dependencies with uv..."
echo "Installing main dependencies..."
if uv pip install -e .; then
  print_status 0 "Main dependencies installed successfully"
else
  print_status 1 "Failed to install main dependencies"
  OVERALL_STATUS=1
fi

echo "Installing dev dependencies..."
if uv pip install -e ".[dev]"; then
  print_status 0 "Dev dependencies installed successfully"
else
  print_status 1 "Failed to install dev dependencies"
  OVERALL_STATUS=1
fi

echo ""

# Step 2: Check Python version
echo "Step 2: Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1)
PYTHON_VERSION_STATUS=$?

if [ $PYTHON_VERSION_STATUS -ne 0 ]; then
  print_status 1 "Failed to get Python version"
  OVERALL_STATUS=1
else
  # Extract major and minor version using regex
  if [[ $PYTHON_VERSION =~ Python\ ([0-9]+)\.([0-9]+) ]]; then
    MAJOR=${BASH_REMATCH[1]}
    MINOR=${BASH_REMATCH[2]}
    
    if [ "$MAJOR" = "3" ] && [ "$MINOR" = "12" ]; then
      print_status 0 "Python version $PYTHON_VERSION matches required version 3.12"
    else
      print_status 1 "Python version $PYTHON_VERSION does not match required version 3.12"
      OVERALL_STATUS=1
    fi
  else
    print_status 1 "Could not parse Python version from output: $PYTHON_VERSION"
    OVERALL_STATUS=1
  fi
fi

echo ""

# Final status
if [ $OVERALL_STATUS -eq 0 ]; then
  echo -e "\033[32m✅ All environment checks passed!\033[0m"
else
  echo -e "\033[31m❌ Some environment checks failed. Please fix the issues above.\033[0m"
fi

exit $OVERALL_STATUS