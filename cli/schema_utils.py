#!/usr/bin/env python3
"""
Utilities for loading and validating JSON schema files.

This module provides functions for loading and validating JSON schema files
as part of the :ArchitecturalPattern:DataValidation implementation.
"""

import json
from pathlib import Path
from typing import Dict, Any

import jsonschema
from jsonschema.validators import validator_for


class InvalidSchemaError(ValueError):
    """
    Exception raised when a schema file is invalid.
    
    This can occur due to:
    - File not found
    - Invalid JSON syntax
    - Invalid JSON Schema structure
    """
    pass


def load_and_validate_schema(schema_path: Path) -> Dict[str, Any]:
    """
    Load and validate a JSON schema file.
    
    Args:
        schema_path: Path object pointing to the schema file
        
    Returns:
        The loaded schema as a Python dictionary
        
    Raises:
        InvalidSchemaError: If the file doesn't exist, contains invalid JSON,
                           or is not a valid JSON Schema document
    """
    # Check if the file exists
    if not schema_path.exists():
        raise InvalidSchemaError(f"Schema file not found: {schema_path}")
    
    try:
        # Read the content of the file
        schema_content = schema_path.read_text()
    except Exception as e:
        raise InvalidSchemaError(f"Error reading schema file: {e}")
    
    try:
        # Parse the content as JSON
        loaded_schema = json.loads(schema_content)
    except json.JSONDecodeError as e:
        raise InvalidSchemaError(f"Schema file contains invalid JSON: {e}")
    
    try:
        # Validate that the loaded data is a structurally valid JSON Schema document
        validator_class = validator_for(loaded_schema)
        validator_class.check_schema(loaded_schema)
    except jsonschema.exceptions.SchemaError as e:
        raise InvalidSchemaError(f"Schema file is not a valid JSON Schema document: {e}")
    
    return loaded_schema