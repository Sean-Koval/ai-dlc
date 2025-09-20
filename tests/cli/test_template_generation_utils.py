#!/usr/bin/env python3
"""
Tests for template_generation_utils.py
"""

import unittest
import json
from pathlib import Path
from unittest.mock import patch

from ai_dlc.cli.template_generation_utils import (
    parse_user_input,
    identify_schema_variables,
    generate_jinja2_template_content,
    InvalidUserInputError,
    SchemaMismatchError,
    _validate_directives_consistency
)


class TestParseUserInput(unittest.TestCase):
    """Test cases for the parse_user_input function."""

    def test_string_input_simple_directives(self):
        """Test parsing a string with simple directives."""
        input_str = "Create a list of users with their emails"
        result = parse_user_input(input_str)
        self.assertIsNone(result['role'])
        self.assertIsNone(result['task'])
        self.assertIn('list', result['directives'])
        self.assertIn('users', result['directives'])
        self.assertIn('emails', result['directives'])

    def test_string_input_role_and_task(self):
        """Test parsing a string with role and task."""
        input_str = "As a product manager, I need a template to break down ideas into user stories"
        result = parse_user_input(input_str)
        self.assertEqual(result['role'], 'product manager')
        self.assertEqual(result['task'], 'break down ideas into user stories')

    def test_contradictory_directives(self):
        """Test that contradictory directives raise InvalidUserInputError."""
        input_str = "Create a list and table of users with their emails"
        with self.assertRaises(InvalidUserInputError) as context:
            parse_user_input(input_str)
        self.assertIn("Contradictory structural directives", str(context.exception))


class TestIdentifySchemaVariables(unittest.TestCase):
    """Test cases for the identify_schema_variables function."""

    def test_simple_object_schema(self):
        """Test identifying variables from a simple object schema."""
        schema_content = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"}
                    }
                }
            }
        }
        with patch('ai_dlc.cli.schema_utils.load_and_validate_schema') as mock_load:
            mock_load.return_value = schema_content
            result = identify_schema_variables(Path("dummy/path.json"))
            self.assertEqual(result, {'user.name': 'string', 'user.email': 'string'})


class TestGenerateJinja2TemplateContent(unittest.TestCase):
    """Test cases for the generate_jinja2_template_content function."""

    def test_list_of_users_with_emails(self):
        parsed_input = {'directives': ['list', 'users', 'name', 'email']}
        schema_variables = {
            'users': 'array',
            'users.name': 'string',
            'users.email': 'string'
        }
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        self.assertIn('{% for user in users %}', result)
        self.assertIn('{{ user.name }}', result)
        self.assertIn('{{ user.email }}', result)

    def test_table_for_products(self):
        """Test generating a template for a table of products with name and price."""
        parsed_input = {'directives': ['table', 'products', 'name', 'price']}
        schema_variables = {
            'products': 'array',
            'products.name': 'string',
            'products.price': 'number'
        }
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        self.assertIn('{% for item in products %}', result)
        self.assertIn('{{ item.name }}', result)
        self.assertIn('{{ item.price }}', result)

    def test_handling_missing_data_raises_error(self):
        """Test that missing data raises SchemaMismatchError."""
        parsed_input = {'directives': ['table', 'products']}
        schema_variables = {
            'product_name': 'string',
            'product_price': 'number'
        }
        with self.assertRaises(SchemaMismatchError):
            generate_jinja2_template_content(parsed_input, schema_variables)

    def test_jinja2_syntax_correctness_raises_error_on_mismatch(self):
        """Test that a schema mismatch in the syntax correctness check raises an error."""
        parsed_input = {'directives': ['list', 'items']}
        schema_variables = {'item.name': 'string'} # 'items' array is missing
        with self.assertRaises(SchemaMismatchError):
            generate_jinja2_template_content(parsed_input, schema_variables)

    def test_jinja2_syntax_validation(self):
        """Test that the function validates Jinja2 syntax using the Jinja2 library."""
        with patch('ai_dlc.cli.template_generation_utils._generate_generic_template', return_value=["{% for i in items %}"]): # Missing endfor
            with self.assertRaises(ValueError) as context:
                generate_jinja2_template_content({}, {})
            self.assertIn("syntax error", str(context.exception).lower())


class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling in template generation utilities."""

    def test_contradictory_directives_in_parsed_input(self):
        """Test that contradictory directives in parsed input raise InvalidUserInputError."""
        parsed_input = {'directives': ['list', 'table', 'users']}
        with self.assertRaises(InvalidUserInputError):
            _validate_directives_consistency(parsed_input['directives'])

    def test_schema_variable_not_found(self):
        """Test that requesting variables not in schema raises SchemaMismatchError."""
        parsed_input = {'directives': ['list', 'users', 'emails']}
        schema_variables = {'products': 'array'}
        with self.assertRaises(SchemaMismatchError):
            generate_jinja2_template_content(parsed_input, schema_variables)

    def test_property_not_found_in_schema(self):
        """Test that requesting properties not in schema raises SchemaMismatchError."""
        parsed_input = {'directives': ['table', 'products', 'name', 'nonexistent_property']}
        schema_variables = {
            'products': 'array',
            'products.name': 'string',
            'products.price': 'number'
        }
        with self.assertRaises(SchemaMismatchError):
            generate_jinja2_template_content(parsed_input, schema_variables)

    def test_no_error_on_valid_cases(self):
        """Test that valid inputs do not raise exceptions."""
        parsed_input = {'directives': ['list', 'users']}
        schema_variables = {
            'users': 'array',
            'users.name': 'string',
            'users.email': 'string'
        }
        try:
            generate_jinja2_template_content(parsed_input, schema_variables)
        except SchemaMismatchError:
            self.fail("generate_jinja2_template_content() raised SchemaMismatchError unexpectedly!")


if __name__ == '__main__':
    unittest.main()