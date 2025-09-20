#!/usr/bin/env python3
"""
Tests for the generate command of the AI-DLC CLI.
"""

import pytest
from typer.testing import CliRunner
from pathlib import Path
import json
import yaml

from ai_dlc.cli.main import app


def test_generate_command_success(tmp_path: Path):
    """Test that the generate command correctly outputs template content."""
    runner = CliRunner()
    
    # 1. Create dummy schema file
    schema_content = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
    }
    schema_file = tmp_path / "schema.json"
    schema_file.write_text(json.dumps(schema_content))

    # 2. Create dummy input file
    input_content = {"name": "World"}
    input_file = tmp_path / "input.yaml"
    input_file.write_text(yaml.dump(input_content))

    # 3. Create dummy template file
    template_content = "Hello {{ name }}!"
    template_file = tmp_path / "template.j2"
    template_file.write_text(template_content)

    # Run the generate command with all required arguments
    result = runner.invoke(app, [
        "generate",
        "--template", str(template_file),
        "--input", str(input_file),
        "--schema", str(schema_file)
    ])

    # Check that the command executed successfully
    assert result.exit_code == 0
    
    # Check that the output is the rendered template
    assert "Hello World!" in result.stdout


def test_generate_command_file_not_found(tmp_path: Path):
    """Test that the generate command fails when the template file doesn't exist."""
    runner = CliRunner()
    
    # Create dummy files for the valid arguments
    schema_file = tmp_path / "schema.json"
    schema_file.write_text(json.dumps({"type": "object"}))
    input_file = tmp_path / "input.yaml"
    input_file.write_text(yaml.dump({}))
    
    non_existent_template = tmp_path / "non_existent_template.j2"

    # Run the generate command with a non-existent template
    result = runner.invoke(app, [
        "generate",
        "--template", str(non_existent_template),
        "--input", str(input_file),
        "--schema", str(schema_file)
    ])

    # Check that the command failed with the expected error
    assert result.exit_code == 1
