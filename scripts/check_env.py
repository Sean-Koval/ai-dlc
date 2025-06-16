#!/usr/bin/env python3
"""
check_env.py - Environment verification script for AI-DLC Prompt Template Tool

This script performs the following actions for "Subphase 0.1: Project Initialization & Environment Management":
1. Initializes/Ensures a `uv` virtual environment with Python 3.12
2. Uses `uv sync` to install dependencies listed in pyproject.toml (including all extras)
3. Verifies that the Python version within the `uv` environment is Python 3.12
4. Exits with status code 0 only if Python 3.12 setup is successful, non-zero otherwise

:Technology:uv
:Technology:Python 3.12
:Context: Environment setup verification to mitigate :DependencyIssues and :CompatibilityIssue
"""

import subprocess
import sys
import re
from typing import Tuple, Optional


def run_command(cmd: list[str]) -> Tuple[bool, str]:
    """
    Run a shell command and return success status and output.
    
    Args:
        cmd: Command to run as a list of strings
        
    Returns:
        Tuple of (success, output)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def initialize_venv() -> Tuple[bool, str]:
    """
    Initialize or ensure a uv virtual environment with Python 3.12.
    
    Returns:
        Tuple of (success, output)
    """
    print("Initializing uv virtual environment with Python 3.12...")
    
    success, output = run_command(["uv", "venv", "--python", "3.12"])
    if not success:
        return False, f"Failed to initialize virtual environment with Python 3.12:\n{output}"
    
    return True, "Virtual environment initialized successfully with Python 3.12"


def install_dependencies() -> Tuple[bool, str]:
    """
    Install dependencies using uv sync with all extras.
    
    Returns:
        Tuple of (success, output)
    """
    print("Installing dependencies with uv sync...")
    
    success, output = run_command(["uv", "sync", "--all-extras"])
    if not success:
        return False, f"Failed to install dependencies:\n{output}"
    
    return True, "Dependencies installed successfully"


def check_python_version() -> Tuple[bool, str, Optional[str]]:
    """
    Check if the Python version in the uv environment is 3.12.x.
    
    Returns:
        Tuple of (success, message, version)
    """
    print("Checking Python version in uv environment...")
    
    # Use uv run to execute Python within the uv environment
    cmd = ["uv", "run", "python", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"]
    success, output = run_command(cmd)
    if not success:
        return False, f"Failed to get Python version from uv environment:\n{output}", None
    
    # Extract version from output (should be just the version string)
    version = output.strip()
    
    # Validate version format
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        return False, f"Could not parse Python version from output: {output}", None
    
    major_minor = ".".join(version.split(".")[:2])
    
    if major_minor == "3.12":
        return True, f"Python version {version} in uv environment matches required version 3.12", version
    else:
        return False, f"Python version {version} in uv environment does not match required version 3.12", version


def main() -> int:
    """
    Main function to run all checks.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Check 1: Initialize virtual environment with Python 3.12
    venv_success, venv_message = initialize_venv()
    print(venv_message)
    if not venv_success:
        print("\n❌ Failed to initialize virtual environment with Python 3.12.")
        return 1
    
    # Check 2: Install dependencies
    dep_success, dep_message = install_dependencies()
    print(dep_message)
    # Note: We continue even if dependency installation fails, as per requirements
    
    # Check 3: Verify Python version in uv environment
    ver_success, ver_message, version = check_python_version()
    print(ver_message)
    if not ver_success:
        print("\n❌ Python version check failed. Please ensure Python 3.12 is available and configured correctly.")
        return 1
    
    # Final result - we only reach here if venv initialization and Python version check passed
    if dep_success:
        print("\n✅ All environment checks passed!")
    else:
        print("\n⚠️ Environment partially set up. Python 3.12 is correctly configured, but dependency installation failed.")
        print("   This may be due to the known :DependencyIssue (flat-layout).")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())