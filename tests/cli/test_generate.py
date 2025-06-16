#!/usr/bin/env python3
"""
Tests for the generate command of the AI-DLC CLI.

This module tests the functionality of the generate command
as implemented in cli/main.py.
"""

import os
import pytest
from typer.testing import CliRunner
from cli.main import app


def test_generate_command_success():
    """Test that the generate command correctly outputs template content."""
    runner = CliRunner()
    template_name = "dummy_template.md.j2"
    template_content = "Hello {{ name }}!\nThis is a basic Jinja2 template."
    
    # Create a temporary template file
    try:
        with open(template_name, "w") as f:
            f.write(template_content)
        
        # Run the generate command
        result = runner.invoke(app, ["generate", "--template", template_name])
        
        # Check that the command executed successfully
        assert result.exit_code == 0
        
        # Check that the output matches the template content
        assert template_content in result.stdout
        
    finally:
        # Clean up the temporary template file
        if os.path.exists(template_name):
            os.remove(template_name)


def test_generate_command_file_not_found():
    """Test that the generate command fails when the template file doesn't exist."""
    runner = CliRunner()
    non_existent_template = "non_existent_template.md.j2"
    
    # Make sure the file doesn't exist
    if os.path.exists(non_existent_template):
        os.remove(non_existent_template)
    
    # Run the generate command with a non-existent template
    result = runner.invoke(app, ["generate", "--template", non_existent_template])
    
    # Check that the command failed with the expected error
    assert result.exit_code == 1
    assert f"Error: Template file '{non_existent_template}' does not exist." in result.stderr


if __name__ == "__main__":
    pytest.main(["-v", __file__])