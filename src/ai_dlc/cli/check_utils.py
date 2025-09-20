#!/usr/bin/env python3
"""
Utilities for loading and validating custom prompt validation rules.

This module provides dataclasses and functions for loading and validating
custom prompt validation rules from .CHECKS.yaml files as part of the
:ArchitecturalPattern:Rule Engine implementation for :CustomValidationRule.
"""

import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Union, Dict, Any


class InvalidCheckRuleError(ValueError):
    """
    Exception raised when a check rule is invalid.
    
    This can occur due to:
    - File not found
    - Invalid YAML syntax
    - Missing required fields
    - Invalid field types
    - Unknown check type
    """
    pass


@dataclass
class RegexCheckConfig:
    """
    Configuration for regex-based validation checks.
    
    Attributes:
        pattern: Regular expression pattern to match against
        should_match: Whether the pattern should match (True) or not match (False)
    """
    pattern: str
    should_match: bool


@dataclass
class KeywordCheckConfig:
    """
    Configuration for keyword-based validation checks.
    
    Attributes:
        keywords: List of keywords to check for
        match_all: Whether all keywords must be present (True) or any keyword (False)
        case_sensitive: Whether keyword matching should be case-sensitive
    """
    keywords: List[str]
    match_all: bool
    case_sensitive: bool


@dataclass
class CustomCheckRule:
    """
    Represents a custom validation rule for prompt content.
    
    Attributes:
        id: Unique identifier for the rule
        description: Human-readable description of the rule
        type: Type of check ('regex_match' or 'keyword_presence')
        config: Configuration specific to the check type
    """
    id: str
    description: str
    type: str
    config: Union[RegexCheckConfig, KeywordCheckConfig]


def load_check_rules(rules_path: Path) -> List[CustomCheckRule]:
    """
    Load and validate custom check rules from a .CHECKS.yaml file.
    
    Args:
        rules_path: Path object pointing to the .CHECKS.yaml file
        
    Returns:
        List of validated CustomCheckRule objects
        
    Raises:
        InvalidCheckRuleError: If the file doesn't exist, contains invalid YAML,
                              or contains invalid rule definitions
    """
    # Check if the file exists
    if not rules_path.exists():
        raise InvalidCheckRuleError(f"Check rules file not found: {rules_path}")
    
    try:
        # Read and parse the YAML content
        with open(rules_path, 'r') as file:
            yaml_content = yaml.safe_load(file)
    except yaml.YAMLError as e:
        raise InvalidCheckRuleError(f"File contains invalid YAML: {e}")
    except Exception as e:
        raise InvalidCheckRuleError(f"Error reading check rules file: {e}")
    
    # Validate that the root is a list
    if yaml_content is None:
        # Empty file or only comments
        return []
    
    if not isinstance(yaml_content, list):
        raise InvalidCheckRuleError(
            f"Check rules file must contain a list of check objects, got {type(yaml_content).__name__}"
        )
    
    # Empty list is valid (no rules)
    if len(yaml_content) == 0:
        return []
    
    # Process each check rule
    rules = []
    for i, check in enumerate(yaml_content):
        # Validate that each check is a dictionary
        if not isinstance(check, dict):
            raise InvalidCheckRuleError(
                f"Check rule at index {i} must be an object, got {type(check).__name__}"
            )
        
        # Validate required fields are present
        required_fields = ['id', 'description', 'type', 'config']
        for field in required_fields:
            if field not in check:
                raise InvalidCheckRuleError(
                    f"Check rule at index {i} is missing required field '{field}'"
                )
        
        # Validate field types
        if not isinstance(check['id'], str):
            raise InvalidCheckRuleError(
                f"Check rule at index {i}: 'id' must be a string, got {type(check['id']).__name__}"
            )
        
        if not isinstance(check['description'], str):
            raise InvalidCheckRuleError(
                f"Check rule at index {i}: 'description' must be a string, got {type(check['description']).__name__}"
            )
        
        if not isinstance(check['type'], str):
            raise InvalidCheckRuleError(
                f"Check rule at index {i}: 'type' must be a string, got {type(check['type']).__name__}"
            )
        
        if not isinstance(check['config'], dict):
            raise InvalidCheckRuleError(
                f"Check rule at index {i}: 'config' must be an object, got {type(check['config']).__name__}"
            )
        
        # Process based on check type
        check_type = check['type']
        config = check['config']
        
        if check_type == 'regex_match':
            # Validate regex_match config
            if 'pattern' not in config:
                raise InvalidCheckRuleError(
                    f"Check rule '{check['id']}': regex_match config missing 'pattern' field"
                )
            
            if 'should_match' not in config:
                raise InvalidCheckRuleError(
                    f"Check rule '{check['id']}': regex_match config missing 'should_match' field"
                )
            
            if not isinstance(config['pattern'], str):
                raise InvalidCheckRuleError(
                    f"Check rule '{check['id']}': 'pattern' must be a string, got {type(config['pattern']).__name__}"
                )
            
            if not isinstance(config['should_match'], bool):
                raise InvalidCheckRuleError(
                    f"Check rule '{check['id']}': 'should_match' must be a boolean, got {type(config['should_match']).__name__}"
                )
            
            # Create RegexCheckConfig
            check_config = RegexCheckConfig(
                pattern=config['pattern'],
                should_match=config['should_match']
            )
            
        elif check_type == 'keyword_presence':
            # Validate keyword_presence config
            if 'keywords' not in config:
                raise InvalidCheckRuleError(
                    f"Check rule '{check['id']}': keyword_presence config missing 'keywords' field"
                )
            
            if 'match_all' not in config:
                raise InvalidCheckRuleError(
                    f"Check rule '{check['id']}': keyword_presence config missing 'match_all' field"
                )
            
            if 'case_sensitive' not in config:
                raise InvalidCheckRuleError(
                    f"Check rule '{check['id']}': keyword_presence config missing 'case_sensitive' field"
                )
            
            if not isinstance(config['keywords'], list):
                raise InvalidCheckRuleError(
                    f"Check rule '{check['id']}': 'keywords' must be a list, got {type(config['keywords']).__name__}"
                )
            
            # Validate that keywords list is not empty
            if len(config['keywords']) == 0:
                raise InvalidCheckRuleError(
                    f"Check rule '{check['id']}': 'keywords' list cannot be empty"
                )
            
            # Validate that all keywords are non-empty strings
            for j, keyword in enumerate(config['keywords']):
                if not isinstance(keyword, str):
                    raise InvalidCheckRuleError(
                        f"Check rule '{check['id']}': keyword at index {j} must be a string, got {type(keyword).__name__}"
                    )
                if not keyword:
                    raise InvalidCheckRuleError(
                        f"Check rule '{check['id']}': keyword at index {j} cannot be an empty string"
                    )
            
            if not isinstance(config['match_all'], bool):
                raise InvalidCheckRuleError(
                    f"Check rule '{check['id']}': 'match_all' must be a boolean, got {type(config['match_all']).__name__}"
                )
            
            if not isinstance(config['case_sensitive'], bool):
                raise InvalidCheckRuleError(
                    f"Check rule '{check['id']}': 'case_sensitive' must be a boolean, got {type(config['case_sensitive']).__name__}"
                )
            
            # Create KeywordCheckConfig
            check_config = KeywordCheckConfig(
                keywords=config['keywords'],
                match_all=config['match_all'],
                case_sensitive=config['case_sensitive']
            )
            
        else:
            # Unknown check type
            raise InvalidCheckRuleError(
                f"Check rule '{check['id']}': unknown check type '{check_type}'"
            )
        
        # Create CustomCheckRule
        rule = CustomCheckRule(
            id=check['id'],
            description=check['description'],
            type=check_type,
            config=check_config
        )
        
        rules.append(rule)
    
    return rules