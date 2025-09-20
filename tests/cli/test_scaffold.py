#!/usr/bin/env python3
"""
Tests for the scaffold command of the AI-DLC CLI.

This module tests the functionality of the scaffold command
as implemented in cli/main.py.
"""

import os
import shutil
import pytest
from typer.testing import CliRunner
from ai_dlc.cli.main import app


def test_scaffold_command_success():
    """Test that the scaffold command creates the expected directory structure."""
    runner = CliRunner()
    team_name = "test_team_scaffold"
    
    # Clean up any existing test directory from previous test runs
    if os.path.exists(team_name):
        shutil.rmtree(team_name)
    
    try:
        # Run the scaffold command
        result = runner.invoke(app, ["scaffold", team_name])
        
        # Check that the command executed successfully
        assert result.exit_code == 0
        assert f"Successfully scaffolded prompt library for team '{team_name}'" in result.stdout
        
        # Check that the team directory was created
        assert os.path.exists(team_name)
        assert os.path.isdir(team_name)
        
        # Check that the subdirectories were created
        subdirs = ["templates", "schemas", "examples", "checks"]
        for subdir in subdirs:
            subdir_path = os.path.join(team_name, subdir)
            assert os.path.exists(subdir_path)
            assert os.path.isdir(subdir_path)
            
            # Check that .gitkeep files were created in each subdirectory
            gitkeep_path = os.path.join(subdir_path, ".gitkeep")
            assert os.path.exists(gitkeep_path)
            assert os.path.isfile(gitkeep_path)
        
        # Check that README.md was created
        readme_path = os.path.join(team_name, "README.md")
        assert os.path.exists(readme_path)
        assert os.path.isfile(readme_path)
        
        # Check README.md content
        with open(readme_path, "r") as f:
            content = f.read()
            assert f"# Prompt Library for {team_name}" in content
    
    finally:
        # Clean up the test directory
        if os.path.exists(team_name):
            shutil.rmtree(team_name)


def test_scaffold_command_directory_exists():
    """Test that the scaffold command fails when the directory already exists."""
    runner = CliRunner()
    team_name = "test_team_scaffold"
    
    # Create the directory first
    os.makedirs(team_name, exist_ok=True)
    
    try:
        # Run the scaffold command
        result = runner.invoke(app, ["scaffold", team_name])
        
        # Check that the command failed with the expected error
        assert result.exit_code == 1
        assert f"Error: Directory '{team_name}' already exists." in result.stderr
    
    finally:
        # Clean up the test directory
        if os.path.exists(team_name):
            shutil.rmtree(team_name)


if __name__ == "__main__":
    pytest.main(["-v", __file__])