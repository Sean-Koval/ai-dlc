#!/usr/bin/env python3
"""
Tests for the validate command.

This module tests the functionality of the validate command
for validating prompt files against custom check rules.
"""

import os
import pytest
from pathlib import Path
from typer.testing import CliRunner
from cli.main import app


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def valid_checks_file(temp_dir):
    """Create a valid checks file for testing."""
    file_path = temp_dir / ".CHECKS.yaml"
    content = """
- id: "no-personal-email"
  description: "Ensures no personal email addresses (gmail, outlook) are present."
  type: "regex_match"
  config:
    pattern: "\\\\b[A-Za-z0-9._%+-]+@(gmail|outlook)\\\\.com\\\\b"
    should_match: false
- id: "contains-project-keyword"
  description: "Ensures the term 'Project Alpha' is present."
  type: "keyword_presence"
  config:
    keywords: ["Project Alpha"]
    match_all: true
    case_sensitive: false
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def valid_prompt_file(temp_dir):
    """Create a valid prompt file that passes all checks."""
    file_path = temp_dir / "valid_prompt.md"
    content = """
# Project Alpha Documentation

This is a sample prompt for Project Alpha.
Contact us at support@company.com for assistance.
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def invalid_prompt_file(temp_dir):
    """Create an invalid prompt file that fails checks."""
    file_path = temp_dir / "invalid_prompt.md"
    content = """
# Project Documentation

This is a sample prompt.
Contact us at john.doe@gmail.com for assistance.
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def prompt_dir(temp_dir, valid_prompt_file, invalid_prompt_file):
    """Create a directory with multiple prompt files."""
    prompt_dir = temp_dir / "prompts"
    prompt_dir.mkdir()
    
    # Create additional prompt files in the directory
    valid_in_dir = prompt_dir / "valid.md"
    valid_in_dir.write_text(valid_prompt_file.read_text())
    
    invalid_in_dir = prompt_dir / "invalid.md"
    invalid_in_dir.write_text(invalid_prompt_file.read_text())
    
    return prompt_dir


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_valid_prompt(self, valid_checks_file, valid_prompt_file):
        """Test validating a valid prompt file."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["validate", "--prompt", str(valid_prompt_file), "--checks", str(valid_checks_file)]
        )
        assert result.exit_code == 0
        assert "All prompts passed custom validation." in result.stdout

    def test_validate_invalid_prompt(self, valid_checks_file, invalid_prompt_file):
        """Test validating an invalid prompt file."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["validate", "--prompt", str(invalid_prompt_file), "--checks", str(valid_checks_file)]
        )
        assert result.exit_code == 1
        assert "Validation failed for" in result.stdout
        assert "Rule 'no-personal-email'" in result.stdout
        assert "Rule 'contains-project-keyword'" in result.stdout
        assert "Custom prompt validation failed for one or more files." in result.stdout

    def test_validate_directory(self, valid_checks_file, prompt_dir):
        """Test validating a directory of prompt files."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["validate", "--prompt", str(prompt_dir), "--checks", str(valid_checks_file)]
        )
        assert result.exit_code == 1
        assert "Validation failed for" in result.stdout
        assert "Custom prompt validation failed for one or more files." in result.stdout

    def test_validate_nonexistent_prompt(self, valid_checks_file, temp_dir):
        """Test validating a non-existent prompt file."""
        nonexistent_file = temp_dir / "nonexistent.md"
        runner = CliRunner()
        result = runner.invoke(
            app, ["validate", "--prompt", str(nonexistent_file), "--checks", str(valid_checks_file)]
        )
        assert result.exit_code == 1
        assert "Error: Prompt path" in result.stdout
        assert "not found" in result.stdout

    def test_validate_nonexistent_checks(self, valid_prompt_file, temp_dir):
        """Test validating with a non-existent checks file."""
        nonexistent_file = temp_dir / "nonexistent.yaml"
        runner = CliRunner()
        result = runner.invoke(
            app, ["validate", "--prompt", str(valid_prompt_file), "--checks", str(nonexistent_file)]
        )
        assert result.exit_code == 1
        assert "Error: Checks file" in result.stdout
        assert "not found" in result.stdout