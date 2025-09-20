#!/usr/bin/env python3
"""
Tests for the keyword_presence check in the validate command.

This module specifically tests the keyword_presence check logic
to ensure it correctly handles match_all and case_sensitive configurations.
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from ai_dlc.cli.main import app


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def match_all_case_sensitive_checks(temp_dir):
    """Create a checks file with match_all: true and case_sensitive: true."""
    file_path = temp_dir / ".CHECKS.yaml"
    content = """
- id: "contains-required-phrase"
  description: "Ensures both Project-X and Alpha keywords are present."
  type: "keyword_presence"
  config:
    keywords: ["Project-X", "Alpha"]
    match_all: true
    case_sensitive: true
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def missing_keyword_prompt(temp_dir):
    """Create a prompt file that is missing one of the required keywords."""
    file_path = temp_dir / "missing_keyword.md"
    content = """
# This prompt is for Project-X.

The other keyword is not here.
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def all_keywords_prompt(temp_dir):
    """Create a prompt file that contains all required keywords."""
    file_path = temp_dir / "all_keywords.md"
    content = """
# This prompt is for Project-X.

This includes Alpha as well.
"""
    file_path.write_text(content)
    return file_path


class TestKeywordPresenceCheck:
    """Tests for the keyword_presence check logic."""

    def test_match_all_missing_keyword(self, match_all_case_sensitive_checks, missing_keyword_prompt):
        """Test that a prompt missing a required keyword fails when match_all is true."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["validate", "--prompt", str(missing_keyword_prompt), "--checks", str(match_all_case_sensitive_checks)]
        )
        assert result.exit_code == 1
        assert "Validation failed for" in result.stdout
        assert "Rule 'contains-required-phrase'" in result.stdout
        assert "Not all required keywords present" in result.stdout
        assert "Missing: Alpha" in result.stdout

    def test_match_all_all_keywords(self, match_all_case_sensitive_checks, all_keywords_prompt):
        """Test that a prompt with all required keywords passes when match_all is true."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["validate", "--prompt", str(all_keywords_prompt), "--checks", str(match_all_case_sensitive_checks)]
        )
        assert result.exit_code == 0
        assert "All prompts passed custom validation." in result.stdout