#!/usr/bin/env python3
"""
Tests for the check_utils module.

This module tests the functionality of the load_check_rules function and
associated dataclasses for parsing :CustomValidationRule files into Python objects.
"""

import os
import pytest
from pathlib import Path
from cli.check_utils import (
    load_check_rules,
    CustomCheckRule,
    RegexCheckConfig,
    KeywordCheckConfig,
    InvalidCheckRuleError
)


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def valid_checks_file(temp_dir):
    """Create a valid checks file for testing."""
    file_path = temp_dir / "valid_checks.yaml"
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
def empty_checks_file(temp_dir):
    """Create an empty checks file for testing."""
    file_path = temp_dir / "empty_checks.yaml"
    content = "[]"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def not_a_list_checks_file(temp_dir):
    """Create a checks file that is not a list at the root."""
    file_path = temp_dir / "not_a_list_checks.yaml"
    content = "id: \"fail\""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def missing_id_checks_file(temp_dir):
    """Create a checks file with a missing ID."""
    file_path = temp_dir / "missing_id_checks.yaml"
    content = """
- description: "Missing ID."
  type: "regex_match"
  config: { pattern: ".*", should_match: true }
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def wrong_type_id_checks_file(temp_dir):
    """Create a checks file with a wrong type for ID."""
    file_path = temp_dir / "wrong_type_id_checks.yaml"
    content = """
- id: 123
  description: "ID is wrong type."
  type: "regex_match"
  config: { pattern: ".*", should_match: true }
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def unknown_type_checks_file(temp_dir):
    """Create a checks file with an unknown check type."""
    file_path = temp_dir / "unknown_type_checks.yaml"
    content = """
- id: "unknown-type-check"
  description: "Uses an unknown check type."
  type: "non_existent_type"
  config: {}
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def regex_missing_pattern_checks_file(temp_dir):
    """Create a checks file with a regex check missing pattern."""
    file_path = temp_dir / "regex_missing_pattern_checks.yaml"
    content = """
- id: "regex-no-pattern"
  description: "Regex check missing pattern."
  type: "regex_match"
  config: { should_match: true }
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def keyword_empty_list_checks_file(temp_dir):
    """Create a checks file with a keyword check with empty keywords list."""
    file_path = temp_dir / "keyword_empty_list_checks.yaml"
    content = """
- id: "keyword-empty"
  description: "Keyword check with empty keywords list."
  type: "keyword_presence"
  config: { keywords: [], match_all: true, case_sensitive: false }
"""
    file_path.write_text(content)
    return file_path


class TestLoadCheckRules:
    """Tests for the load_check_rules function."""

    def test_valid_rules(self, valid_checks_file):
        """Test loading valid check rules."""
        rules = load_check_rules(valid_checks_file)
        
        # Verify it returns a list of 2 CustomCheckRule objects
        assert len(rules) == 2
        assert all(isinstance(rule, CustomCheckRule) for rule in rules)
        
        # Verify the first rule
        rule1 = rules[0]
        assert rule1.id == "no-personal-email"
        assert rule1.description == "Ensures no personal email addresses (gmail, outlook) are present."
        assert rule1.type == "regex_match"
        assert isinstance(rule1.config, RegexCheckConfig)
        assert rule1.config.pattern == "\\b[A-Za-z0-9._%+-]+@(gmail|outlook)\\.com\\b"
        assert rule1.config.should_match is False
        
        # Verify the second rule
        rule2 = rules[1]
        assert rule2.id == "contains-project-keyword"
        assert rule2.description == "Ensures the term 'Project Alpha' is present."
        assert rule2.type == "keyword_presence"
        assert isinstance(rule2.config, KeywordCheckConfig)
        assert rule2.config.keywords == ["Project Alpha"]
        assert rule2.config.match_all is True
        assert rule2.config.case_sensitive is False

    def test_empty_rules_file(self, empty_checks_file):
        """Test loading an empty rules file."""
        rules = load_check_rules(empty_checks_file)
        assert rules == []

    def test_not_a_list(self, not_a_list_checks_file):
        """Test loading a file that is not a list at the root."""
        with pytest.raises(InvalidCheckRuleError) as excinfo:
            load_check_rules(not_a_list_checks_file)
        assert "must contain a list of check objects" in str(excinfo.value)

    def test_missing_id(self, missing_id_checks_file):
        """Test loading a file with a missing ID."""
        with pytest.raises(InvalidCheckRuleError) as excinfo:
            load_check_rules(missing_id_checks_file)
        assert "missing required field 'id'" in str(excinfo.value)

    def test_wrong_type_id(self, wrong_type_id_checks_file):
        """Test loading a file with a wrong type for ID."""
        with pytest.raises(InvalidCheckRuleError) as excinfo:
            load_check_rules(wrong_type_id_checks_file)
        assert "'id' must be a string" in str(excinfo.value)

    def test_unknown_type(self, unknown_type_checks_file):
        """Test loading a file with an unknown check type."""
        with pytest.raises(InvalidCheckRuleError) as excinfo:
            load_check_rules(unknown_type_checks_file)
        assert "unknown check type" in str(excinfo.value)

    def test_regex_missing_pattern(self, regex_missing_pattern_checks_file):
        """Test loading a file with a regex check missing pattern."""
        with pytest.raises(InvalidCheckRuleError) as excinfo:
            load_check_rules(regex_missing_pattern_checks_file)
        assert "regex_match config missing 'pattern' field" in str(excinfo.value)

    def test_keyword_empty_list(self, keyword_empty_list_checks_file):
        """Test loading a file with a keyword check with empty keywords list."""
        with pytest.raises(InvalidCheckRuleError) as excinfo:
            load_check_rules(keyword_empty_list_checks_file)
        assert "'keywords' list cannot be empty" in str(excinfo.value)

    def test_file_not_found(self, temp_dir):
        """Test loading a non-existent file."""
        non_existent_file = temp_dir / "non_existent.yaml"
        with pytest.raises(InvalidCheckRuleError) as excinfo:
            load_check_rules(non_existent_file)
        assert "Check rules file not found" in str(excinfo.value)