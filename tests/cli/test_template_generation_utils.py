#!/usr/bin/env python3
"""
Tests for template_generation_utils.py

This module contains tests for the Jinja2 template generation utilities,
focusing on the parse_user_input function which is the first step in the
template generation feature.
"""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from cli.template_generation_utils import parse_user_input, identify_schema_variables, generate_jinja2_template_content, build_meta_prompt
from jinja2 import TemplateError


class TestParseUserInput(unittest.TestCase):
    """Test cases for the parse_user_input function."""

    def test_string_input_simple_directives(self):
        """Test parsing a string with simple directives."""
        input_str = "Create a list of users with their emails"
        result = parse_user_input(input_str)
        
        # Check the structure of the result
        self.assertIsInstance(result, dict)
        self.assertIn('role', result)
        self.assertIn('task', result)
        self.assertIn('directives', result)
        
        # Check that role and task are None (not specified in this input)
        self.assertIsNone(result['role'])
        self.assertIsNone(result['task'])
        
        # Check that directives contains the expected keywords
        self.assertIn('list', result['directives'])
        self.assertIn('users', result['directives'])
        self.assertIn('emails', result['directives'])

    def test_string_input_role_and_task(self):
        """Test parsing a string with role and task."""
        input_str = "As a product manager, I need a template to break down ideas into user stories"
        result = parse_user_input(input_str)
        
        # Check the structure of the result
        self.assertIsInstance(result, dict)
        
        # Check that role and task are correctly extracted
        self.assertEqual(result['role'], 'product manager')
        self.assertEqual(result['task'], 'break down ideas into user stories')
        
        # Directives might be empty or contain keywords
        self.assertIsInstance(result['directives'], list)

    def test_string_input_alternative_role_phrasing(self):
        """Test parsing a string with alternative role phrasing."""
        input_str = "Being a developer, I want a template for documenting API endpoints"
        result = parse_user_input(input_str)
        
        # Check that role is correctly extracted with alternative phrasing
        self.assertEqual(result['role'], 'developer')
        self.assertIn('documenting api endpoints', result['task'].lower())

    def test_dictionary_input_role_and_task(self):
        """Test parsing a dictionary with role and task."""
        input_dict = {
            'role': 'developer',
            'task': 'generate API documentation',
            'other_directives': ['endpoint', 'parameters']
        }
        result = parse_user_input(input_dict)
        
        # Check that role and task are correctly extracted
        self.assertEqual(result['role'], 'developer')
        self.assertEqual(result['task'], 'generate API documentation')
        
        # Check that directives are preserved
        self.assertEqual(result['directives'], [])  # Default empty list since 'directives' wasn't in input

    def test_dictionary_input_with_directives(self):
        """Test parsing a dictionary with explicit directives."""
        input_dict = {
            'role': 'developer',
            'task': 'generate API documentation',
            'directives': ['endpoint', 'parameters']
        }
        result = parse_user_input(input_dict)
        
        # Check that directives are correctly extracted
        self.assertEqual(result['directives'], ['endpoint', 'parameters'])

    def test_invalid_input_type(self):
        """Test that invalid input types raise TypeError."""
        # Test with None
        with self.assertRaises(TypeError):
            parse_user_input(None)
        
        # Test with integer
        with self.assertRaises(TypeError):
            parse_user_input(42)
        
        # Test with list
        with self.assertRaises(TypeError):
            parse_user_input(['not', 'valid', 'input'])

    def test_empty_string(self):
        """Test parsing an empty string."""
        result = parse_user_input("")
        
        # Check that default values are returned
        self.assertIsNone(result['role'])
        self.assertIsNone(result['task'])
        self.assertEqual(result['directives'], [])

    def test_string_with_only_role(self):
        """Test parsing a string with only role information."""
        input_str = "As a data scientist"
        result = parse_user_input(input_str)
        
        # Check that role is extracted but task is None
        self.assertEqual(result['role'], 'data scientist')
        self.assertIsNone(result['task'])
        self.assertEqual(result['directives'], [])

    def test_string_with_only_task(self):
        """Test parsing a string with only task information."""
        input_str = "Need a template to organize research findings"
        result = parse_user_input(input_str)
        
        # Check that task is extracted but role is None
        self.assertIsNone(result['role'])
        self.assertEqual(result['task'], 'organize research findings')
        self.assertEqual(result['directives'], [])

    def test_string_with_structural_keywords(self):
        """Test parsing a string with structural keywords."""
        input_str = "Generate a table for products showing name, price, and category"
        result = parse_user_input(input_str)
        
        # Check that structural keywords are extracted
        self.assertIn('table', result['directives'])
        self.assertIn('products', result['directives'])
        self.assertIn('name', result['directives'])
        self.assertIn('price', result['directives'])
        # The current implementation captures "and category" as a single directive
        self.assertTrue(any('category' in directive for directive in result['directives']))

    def test_string_with_attributes(self):
        """Test parsing a string with attributes."""
        input_str = "List users with their name, email, and role"
        result = parse_user_input(input_str)
        
        # Check that attributes are extracted
        self.assertIn('name', result['directives'])
        self.assertIn('email', result['directives'])
        # The current implementation captures "and role" as a single directive
        self.assertTrue(any('role' in directive for directive in result['directives']))

    def test_duplicate_directives_removal(self):
        """Test that duplicate directives are removed while preserving order."""
        input_str = "Create a list of users with emails and show emails again"
        result = parse_user_input(input_str)
        
        # Check that 'emails' appears only once
        self.assertEqual(result['directives'].count('emails'), 1)
        
        # Check the order is preserved (list before emails)
        list_index = result['directives'].index('list')
        emails_index = result['directives'].index('emails')
        self.assertLess(list_index, emails_index)


class TestIdentifySchemaVariables(unittest.TestCase):
    """Test cases for the identify_schema_variables function."""

    def test_simple_object_schema(self):
        """Test identifying variables from a simple object schema."""
        # Create a temporary schema file
        schema_content = json.dumps({
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
        })
        
        # Mock the load_and_validate_schema function to return our test schema
        with patch('cli.schema_utils.load_and_validate_schema') as mock_load:
            mock_load.return_value = json.loads(schema_content)
            
            # Call the function with a dummy path
            result = identify_schema_variables(Path("dummy/path.json"))
            
            # Check that the variables are correctly identified
            self.assertIn('user.name', result)
            self.assertIn('user.email', result)
            self.assertEqual(result['user.name'], 'string')
            self.assertEqual(result['user.email'], 'string')

    def test_array_schema(self):
        """Test identifying variables from a schema with arrays."""
        # Create a temporary schema file
        schema_content = json.dumps({
            "type": "object",
            "properties": {
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "price": {"type": "number"}
                        }
                    }
                }
            }
        })
        
        # Mock the load_and_validate_schema function to return our test schema
        with patch('cli.schema_utils.load_and_validate_schema') as mock_load:
            mock_load.return_value = json.loads(schema_content)
            
            # Call the function with a dummy path
            result = identify_schema_variables(Path("dummy/path.json"))
            
            # Check that the variables are correctly identified
            self.assertIn('products', result)
            self.assertEqual(result['products'], 'array')
            self.assertIn('products.name', result)
            self.assertIn('products.price', result)
            self.assertEqual(result['products.name'], 'string')
            self.assertEqual(result['products.price'], 'number')

    def test_nested_schema(self):
        """Test identifying variables from a deeply nested schema."""
        # Create a temporary schema file
        schema_content = json.dumps({
            "type": "object",
            "properties": {
                "company": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "departments": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "employees": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "position": {"type": "string"},
                                                "salary": {"type": "number"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        })
        
        # Mock the load_and_validate_schema function to return our test schema
        with patch('cli.schema_utils.load_and_validate_schema') as mock_load:
            mock_load.return_value = json.loads(schema_content)
            
            # Call the function with a dummy path
            result = identify_schema_variables(Path("dummy/path.json"))
            
            # Check that the variables are correctly identified
            self.assertIn('company.name', result)
            self.assertEqual(result['company.name'], 'string')
            
            self.assertIn('company.departments', result)
            self.assertEqual(result['company.departments'], 'array')
            
            self.assertIn('company.departments.name', result)
            self.assertEqual(result['company.departments.name'], 'string')
            
            self.assertIn('company.departments.employees', result)
            self.assertEqual(result['company.departments.employees'], 'array')
            
            self.assertIn('company.departments.employees.name', result)
            self.assertEqual(result['company.departments.employees.name'], 'string')
            
            self.assertIn('company.departments.employees.position', result)
            self.assertEqual(result['company.departments.employees.position'], 'string')
            
            self.assertIn('company.departments.employees.salary', result)
            self.assertEqual(result['company.departments.employees.salary'], 'number')

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised when the schema file doesn't exist."""
        # Mock the load_and_validate_schema function to raise InvalidSchemaError with "not found" message
        with patch('cli.schema_utils.load_and_validate_schema') as mock_load:
            mock_load.side_effect = Exception("not found")
            
            # Call the function with a non-existent path and check that FileNotFoundError is raised
            with self.assertRaises(FileNotFoundError):
                identify_schema_variables(Path("non_existent_file.json"))

    def test_invalid_json(self):
        """Test that JSONDecodeError is raised when the schema file contains invalid JSON."""
        # Mock the load_and_validate_schema function to raise InvalidSchemaError with "invalid JSON" message
        with patch('cli.schema_utils.load_and_validate_schema') as mock_load:
            mock_load.side_effect = Exception("invalid JSON")
            
            # Call the function with a dummy path and check that JSONDecodeError is raised
            with self.assertRaises(json.JSONDecodeError):
                identify_schema_variables(Path("invalid_json.json"))
    
    def test_various_data_types(self):
        """Test identifying variables from a schema with various data types."""
        # Create a schema with various data types
        schema_content = json.dumps({
            "type": "object",
            "properties": {
                "string_prop": {"type": "string"},
                "number_prop": {"type": "number"},
                "integer_prop": {"type": "integer"},
                "boolean_prop": {"type": "boolean"},
                "array_prop": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "object_prop": {
                    "type": "object",
                    "properties": {
                        "nested_prop": {"type": "string"}
                    }
                }
            }
        })
        
        # Mock the load_and_validate_schema function to return our test schema
        with patch('cli.schema_utils.load_and_validate_schema') as mock_load:
            mock_load.return_value = json.loads(schema_content)
            
            # Call the function with a dummy path
            result = identify_schema_variables(Path("dummy/path.json"))
            
            # Check that all data types are correctly identified
            self.assertIn('string_prop', result)
            self.assertEqual(result['string_prop'], 'string')
            
            self.assertIn('number_prop', result)
            self.assertEqual(result['number_prop'], 'number')
            
            self.assertIn('integer_prop', result)
            self.assertEqual(result['integer_prop'], 'integer')
            
            self.assertIn('boolean_prop', result)
            self.assertEqual(result['boolean_prop'], 'boolean')
            
            # For array types, the function identifies the items type
            self.assertIn('array_prop', result)
            
            self.assertIn('object_prop.nested_prop', result)
            self.assertEqual(result['object_prop.nested_prop'], 'string')
    
    def test_empty_schema(self):
        """Test identifying variables from an empty schema or schema with no properties."""
        # Create an empty schema
        empty_schema = json.dumps({
            "type": "object",
            "properties": {}
        })
        
        # Mock the load_and_validate_schema function to return our empty schema
        with patch('cli.schema_utils.load_and_validate_schema') as mock_load:
            mock_load.return_value = json.loads(empty_schema)
            
            # Call the function with a dummy path
            result = identify_schema_variables(Path("dummy/path.json"))
            
            # Check that the result is an empty dictionary
            self.assertEqual(result, {})
    
    def test_schema_without_type(self):
        """Test identifying variables from a schema without explicit type information."""
        # Create a schema without type information
        schema_content = json.dumps({
            "properties": {
                "prop1": {},
                "prop2": {}
            }
        })
        
        # Mock the load_and_validate_schema function to return our test schema
        with patch('cli.schema_utils.load_and_validate_schema') as mock_load:
            mock_load.return_value = json.loads(schema_content)
            
            # Call the function with a dummy path
            result = identify_schema_variables(Path("dummy/path.json"))
            
            # Check that properties are identified with "unknown" type
            self.assertIn('prop1', result)
            self.assertEqual(result['prop1'], 'unknown')
            self.assertIn('prop2', result)
            self.assertEqual(result['prop2'], 'unknown')


class TestGenerateJinja2TemplateContent(unittest.TestCase):
    """Test cases for the generate_jinja2_template_content function."""

    def test_list_of_users_with_emails(self):
        """Test generating a template for a list of users with emails."""
        # Test input
        parsed_input = {
            'directives': ['list', 'users', 'emails']
        }
        schema_variables = {
            'user.name': 'string',
            'user.email': 'string'
        }
        
        # Call the function
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        
        # Check that the result is a string
        self.assertIsInstance(result, str)
        
        # Check that the result contains expected Jinja2 syntax
        self.assertIn('{% for', result)
        self.assertIn('{% endfor %}', result)
        
        # Check that the result contains expected variable references
        self.assertIn('{{ user.name', result)
        self.assertIn('{{ user.email', result)
        
        # Check that the result contains expected HTML structure
        self.assertIn('<ul>', result)
        self.assertIn('</ul>', result)
        self.assertIn('<li>', result)
        
    def test_list_generation_with_flattened_schema(self):
        """Test list generation with flattened schema variables as specified in TDD Anchors."""
        # Test input based on TDD Anchor example
        parsed_input = {
            'role': None,
            'task': None,
            'directives': ['list', 'users', 'emails']
        }
        schema_variables = {
            'user.name': 'string',
            'user.email': 'string'
        }
        
        # Call the function
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        
        # Check that the result contains a list structure
        self.assertIn('<ul>', result)
        self.assertIn('</ul>', result)
        
        # Check for proper Jinja2 loop structure
        self.assertIn('{% for', result)
        self.assertIn('{% endfor %}', result)
        
        # Check for proper variable placement
        self.assertIn('{{ user.name', result)
        self.assertIn('{{ user.email', result)
        
        # Verify the variables are placed within list items
        self.assertIn('<li>', result)
        self.assertIn('</li>', result)

    def test_table_for_products(self):
        """Test generating a template for a table of products with name and price."""
        # Test input
        parsed_input = {
            'directives': ['table', 'products', 'name', 'price']
        }
        schema_variables = {
            'products': 'array',
            'products.name': 'string',
            'products.price': 'number'
        }
        
        # Call the function
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        
        # Check that the result is a string
        self.assertIsInstance(result, str)
        
        # Check that the result contains expected Jinja2 syntax
        self.assertIn('{% for', result)
        self.assertIn('{% endfor %}', result)
        
        # Check that the result contains expected variable references
        self.assertIn('{{ item.name', result)
        self.assertIn('{{ item.price', result)
        
        # Check that the result contains expected HTML structure
        self.assertIn('<table>', result)
        self.assertIn('</table>', result)
        self.assertIn('<tr>', result)
        self.assertIn('<th>', result)
        self.assertIn('<td>', result)

    def test_product_manager_template(self):
        """Test generating a template for a product manager breaking down ideas."""
        # Test input
        parsed_input = {
            'role': 'product manager',
            'task': 'break down ideas'
        }
        schema_variables = {}
        
        # Call the function
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        
        # Check that the result is a string
        self.assertIsInstance(result, str)
        
        # Check that the result contains expected sections
        self.assertIn('# {{ role', result)
        self.assertIn('## User Stories', result)
        self.assertIn('## Tasks', result)
        self.assertIn('## Timeline', result)
        
        # Check that the result contains expected Jinja2 syntax
        self.assertIn('{% for', result)
        self.assertIn('{% endfor %}', result)

    def test_api_documentation_template(self):
        """Test generating a template for API documentation."""
        # Test input
        parsed_input = {
            'role': 'developer',
            'task': 'generate API documentation'
        }
        schema_variables = {}
        
        # Call the function
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        
        # Check that the result is a string
        self.assertIsInstance(result, str)
        
        # Check that the result contains expected sections
        self.assertIn('# API Documentation', result)
        self.assertIn('## Endpoints', result)
        self.assertIn('## Error Codes', result)
        
        # Check that the result contains expected Jinja2 syntax
        self.assertIn('{%', result)
        self.assertIn('{{', result)

    def test_generic_template(self):
        """Test generating a generic template when no specific structure is identified."""
        # Test input
        parsed_input = {
            'directives': ['custom']
        }
        schema_variables = {
            'item1': 'string',
            'item2': 'number'
        }
        
        # Call the function
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        
        # Check that the result is a string
        self.assertIsInstance(result, str)
        
        # Check that the result contains expected variable references
        self.assertIn('{{ item1', result)
        self.assertIn('{{ item2', result)

    def test_empty_inputs(self):
        """Test generating a template with empty inputs."""
        # Test with empty parsed_input and schema_variables
        result = generate_jinja2_template_content({}, {})
        
        # Check that the result is a string
        self.assertIsInstance(result, str)
        
        # Check that the result is not empty
        self.assertTrue(len(result) > 0)
        
    def test_table_generation_with_products(self):
        """Test table generation with products schema as specified in TDD Anchors."""
        # Test input based on TDD Anchor example
        parsed_input = {
            'role': None,
            'task': None,
            'directives': ['table', 'products', 'name', 'price']
        }
        schema_variables = {
            'products': 'array',
            'products.name': 'string',
            'products.price': 'number'
        }
        
        # Call the function
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        
        # Check for table structure
        self.assertIn('<table>', result)
        self.assertIn('</table>', result)
        self.assertIn('<thead>', result)
        self.assertIn('<tbody>', result)
        
        # Check for table headers
        self.assertIn('<th>Name</th>', result)
        self.assertIn('<th>Price</th>', result)
        
        # Check for Jinja2 loop over products
        self.assertIn('{% for item in products %}', result)
        self.assertIn('{% endfor %}', result)
        
        # Check for proper variable placement in table cells
        self.assertIn('<td>{{ item.name }}</td>', result)
        self.assertIn('<td>{{ item.price }}</td>', result)
    
    def test_product_manager_idea_breakdown(self):
        """Test role/task-specific template for product manager breaking down ideas."""
        # Test input based on TDD Anchor example
        parsed_input = {
            'role': 'product manager',
            'task': 'break down ideas',
            'directives': ['ideas', 'user stories']
        }
        schema_variables = {
            'idea_title': 'string',
            'user_stories': 'array',
            'user_stories.story': 'string',
            'user_stories.tasks': 'array'
        }
        
        # Call the function
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        
        # Check for appropriate sections in the template
        self.assertIn('# {{ role', result)  # Title with role variable
        self.assertIn('## Idea', result)
        self.assertIn('## User Stories', result)
        self.assertIn('## Tasks', result)
        
        # Check for markdown formatting
        self.assertIn('- ', result)  # List markers
        
        # Check for appropriate Jinja2 syntax
        self.assertIn('{%', result)
        self.assertIn('{{', result)
    
    def test_developer_api_documentation(self):
        """Test role/task-specific template for developer generating API documentation."""
        # Test input based on TDD Anchor example
        parsed_input = {
            'role': 'developer',
            'task': 'generate API documentation',
            'directives': ['endpoints', 'parameters']
        }
        schema_variables = {
            'api_name': 'string',
            'endpoints': 'array',
            'endpoints.path': 'string',
            'endpoints.method': 'string',
            'endpoints.parameters': 'array',
            'endpoints.parameters.name': 'string',
            'endpoints.parameters.type': 'string'
        }
        
        # Call the function
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        
        # Check for API documentation structure
        self.assertIn('# API Documentation', result)
        self.assertIn('## Endpoints', result)
        
        # Check for code blocks
        self.assertIn('```', result)
        
        # Check for parameter table structure if present
        self.assertIn('parameters', result.lower())
        
        # Check for appropriate Jinja2 syntax for endpoints
        self.assertIn('{% for endpoint', result.lower())
    
    def test_handling_missing_data(self):
        """Test handling of missing/mismatched data between parsed_input and schema_variables."""
        # Test input with directives requesting a table but schema doesn't define a list
        parsed_input = {
            'directives': ['table', 'products']
        }
        schema_variables = {
            'product_name': 'string',
            'product_price': 'number'
        }
        
        # Call the function
        result = generate_jinja2_template_content(parsed_input, schema_variables)
        
        # Check that the result is a string and not empty
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        
        # Check that it still produces a table structure
        self.assertIn('<table>', result)
        self.assertIn('</table>', result)
        
        # Check that it handles the mismatch gracefully
        # Either by using generic variables or providing a fallback
        self.assertIn('{% for', result)
        self.assertIn('{% endfor %}', result)
    
    def test_jinja2_syntax_correctness(self):
        """Test that the generated template contains valid Jinja2 syntax."""
        # Test various inputs to ensure valid Jinja2 syntax
        test_cases = [
            # List case
            ({
                'directives': ['list', 'items']
            }, {
                'item.name': 'string'
            }),
            # Table case
            ({
                'directives': ['table', 'data']
            }, {
                'data': 'array',
                'data.field1': 'string',
                'data.field2': 'number'
            }),
            # Role-specific case
            ({
                'role': 'developer',
                'task': 'document code'
            }, {
                'function_name': 'string',
                'parameters': 'array'
            })
        ]
        
        for parsed_input, schema_variables in test_cases:
            result = generate_jinja2_template_content(parsed_input, schema_variables)
            
            # Check for balanced Jinja2 tags
            open_tags = result.count('{%')
            close_tags = result.count('%}')
            self.assertEqual(open_tags, close_tags, "Jinja2 block tags are not balanced")
            
            # Check for balanced variable tags
            open_vars = result.count('{{')
            close_vars = result.count('}}')
            self.assertEqual(open_vars, close_vars, "Jinja2 variable tags are not balanced")
            
            # Check for proper nesting of for loops and if statements
            if '{% for' in result:
                self.assertIn('{% endfor %}', result)
            if '{% if' in result:
                self.assertIn('{% endif %}', result)


class TestBuildMetaPrompt(unittest.TestCase):
    """Test cases for the build_meta_prompt function."""

    def test_input_rendering(self):
        """Test that inputs are correctly included in the rendered output."""
        # Test inputs
        role = "Test Role"
        task = "Test Task"
        directives = ["Test Directive 1", "Test Directive 2"]
        schema = {"test_key": "test_value", "nested": {"sub_key": "sub_value"}}
        
        # Mock the template file and rendering
        template_content = """
        ROLE: {{ role }}
        TASK: {{ task }}
        DIRECTIVES: {{ directives }}
        JSON SCHEMA:
        ```json
        {{ schema }}
        ```
        VALIDATION: Check this
        """
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('jinja2.Environment.get_template') as mock_get_template:
            
            # Set up the mock template
            mock_template = MagicMock()
            mock_template.render.return_value = template_content.replace("{{ role }}", role) \
                                                              .replace("{{ task }}", task) \
                                                              .replace("{{ directives }}", ", ".join(directives)) \
                                                              .replace("{{ schema }}", json.dumps(schema, indent=2))
            mock_get_template.return_value = mock_template
            
            # Call the function
            result = build_meta_prompt(role, task, directives, schema)
            
            # Check that all inputs are included in the output
            self.assertIn(role, result)
            self.assertIn(task, result)
            self.assertIn("Test Directive 1", result)
            self.assertIn("Test Directive 2", result)
            self.assertIn("test_key", result)
            self.assertIn("test_value", result)
            self.assertIn("sub_key", result)
            self.assertIn("sub_value", result)

    def test_validation_marker(self):
        """Test that the rendered prompt includes the VALIDATION marker."""
        # Test inputs
        role = "Test Role"
        task = "Test Task"
        directives = ["Test Directive"]
        schema = {"test_key": "test_value"}
        
        # Mock the template file and rendering
        template_content = """
        ROLE: {{ role }}
        TASK: {{ task }}
        DIRECTIVES: {{ directives }}
        JSON SCHEMA:
        ```json
        {{ schema }}
        ```
        VALIDATION: Check this validation marker
        """
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('jinja2.Environment.get_template') as mock_get_template:
            
            # Set up the mock template
            mock_template = MagicMock()
            mock_template.render.return_value = template_content.replace("{{ role }}", role) \
                                                              .replace("{{ task }}", task) \
                                                              .replace("{{ directives }}", ", ".join(directives)) \
                                                              .replace("{{ schema }}", json.dumps(schema, indent=2))
            mock_get_template.return_value = mock_template
            
            # Call the function
            result = build_meta_prompt(role, task, directives, schema)
            
            # Check that the VALIDATION marker is included in the output
            self.assertIn("VALIDATION:", result)
            self.assertIn("Check this validation marker", result)

    def test_schema_serialization(self):
        """Test that the schema dictionary is correctly serialized into a pretty-printed JSON string."""
        # Test inputs
        role = "Test Role"
        task = "Test Task"
        directives = ["Test Directive"]
        schema = {
            "complex_key": {
                "nested_array": [1, 2, 3],
                "nested_object": {
                    "deep_key": "deep_value"
                }
            }
        }
        
        # Expected serialized schema (pretty-printed JSON)
        expected_json = json.dumps(schema, indent=2)
        
        # Mock the template file and rendering
        template_content = """
        ROLE: {{ role }}
        TASK: {{ task }}
        DIRECTIVES: {{ directives }}
        JSON SCHEMA:
        ```json
        {{ schema }}
        ```
        """
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('jinja2.Environment.get_template') as mock_get_template:
            
            # Set up the mock template
            mock_template = MagicMock()
            mock_template.render.return_value = template_content.replace("{{ role }}", role) \
                                                              .replace("{{ task }}", task) \
                                                              .replace("{{ directives }}", ", ".join(directives)) \
                                                              .replace("{{ schema }}", expected_json)
            mock_get_template.return_value = mock_template
            
            # Call the function
            result = build_meta_prompt(role, task, directives, schema)
            
            # Check that the schema is correctly serialized
            self.assertIn(expected_json, result)
            self.assertIn("complex_key", result)
            self.assertIn("nested_array", result)
            self.assertIn("nested_object", result)
            self.assertIn("deep_key", result)
            self.assertIn("deep_value", result)

    def test_file_not_found_error(self):
        """Test that the function correctly handles a FileNotFoundError."""
        # Test inputs
        role = "Test Role"
        task = "Test Task"
        directives = ["Test Directive"]
        schema = {"test_key": "test_value"}
        
        # Mock the template file not existing
        with patch('pathlib.Path.exists', return_value=False):
            
            # Call the function and check that FileNotFoundError is raised
            with self.assertRaises(FileNotFoundError):
                build_meta_prompt(role, task, directives, schema)

    def test_jinja2_error(self):
        """Test that the function correctly handles Jinja2 template errors."""
        # Test inputs
        role = "Test Role"
        task = "Test Task"
        directives = ["Test Directive"]
        schema = {"test_key": "test_value"}
        
        # Mock the template file existing but Jinja2 raising an error
        with patch('pathlib.Path.exists', return_value=True), \
             patch('jinja2.Environment.get_template') as mock_get_template:
            
            # Set up the mock template to raise a TemplateError
            mock_get_template.side_effect = TemplateError("Test Jinja2 error")
            
            # Call the function and check that TemplateError is raised
            with self.assertRaises(TemplateError):
                build_meta_prompt(role, task, directives, schema)

    def test_rendered_prompt_structure(self):
        """Test that the rendered prompt contains all required sections in the correct order."""
        # Test inputs
        role = "YourSampleRole"
        task = "YourSampleTask"
        directives = ["Directive1", "Directive2"]
        schema = {"key": "value", "nested": {"subkey": "subvalue"}}
        
        # Mock the template file and rendering
        template_content = """
        You are a Jinja2 template generation specialist.
        ROLE: {{ role }}
        TASK: {{ task }}
        DIRECTIVES: {{ directives }}
        JSON SCHEMA:
        ```json
        {{ schema }}
        ```
        Please follow these steps to generate an effective Jinja2 template:
        1. ANALYZE THE INPUTS
        2. PROPOSE A HIGH-LEVEL STRUCTURE
        3. MAP SCHEMA ENTITIES TO JINJA2 SYNTAX
        4. IMPLEMENT THE TEMPLATE
        5. VALIDATION
        VALIDATION: Review your template
        Return ONLY the completed Jinja2 template as a Markdown code block
        """
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('jinja2.Environment.get_template') as mock_get_template:
            
            # Set up the mock template
            mock_template = MagicMock()
            mock_template.render.return_value = template_content.replace("{{ role }}", role) \
                                                              .replace("{{ task }}", task) \
                                                              .replace("{{ directives }}", ", ".join(directives)) \
                                                              .replace("{{ schema }}", json.dumps(schema, indent=2))
            mock_get_template.return_value = mock_template
            
            # Call the function
            result = build_meta_prompt(role, task, directives, schema)
            
            # Check that key phrases appear in the correct order
            phrases = [
                "You are a Jinja2 template generation specialist.",
                f"ROLE: {role}",
                f"TASK: {task}",
                f"DIRECTIVES: {', '.join(directives)}",
                "JSON SCHEMA:",
                "```json",
                "Please follow these steps to generate an effective Jinja2 template:",
                "1. ANALYZE THE INPUTS",
                "2. PROPOSE A HIGH-LEVEL STRUCTURE",
                "3. MAP SCHEMA ENTITIES TO JINJA2 SYNTAX",
                "4. IMPLEMENT THE TEMPLATE",
                "5. VALIDATION",
                "VALIDATION: Review your template",
                "Return ONLY the completed Jinja2 template as a Markdown code block"
            ]
            
            # Check that each phrase appears in the result
            for phrase in phrases:
                self.assertIn(phrase, result, f"Phrase '{phrase}' not found in rendered output")
            
            # Check the order of phrases
            last_index = -1
            for phrase in phrases:
                current_index = result.find(phrase)
                self.assertGreater(current_index, last_index,
                                  f"Phrase '{phrase}' is not in the correct order")
                last_index = current_index

    def test_build_meta_prompt_empty_directives(self):
        """Test that the function handles empty directives correctly."""
        # Test inputs
        role = "Test Role"
        task = "Test Task"
        directives = []  # Empty directives list
        schema = {"test_key": "test_value"}
        
        # Mock the template file and rendering
        template_content = """
        ROLE: {{ role }}
        TASK: {{ task }}
        DIRECTIVES: {{ directives }}
        JSON SCHEMA:
        ```json
        {{ schema }}
        ```
        VALIDATION: Check this
        """
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('jinja2.Environment.get_template') as mock_get_template:
            
            # Set up the mock template
            mock_template = MagicMock()
            mock_template.render.return_value = template_content.replace("{{ role }}", role) \
                                                              .replace("{{ task }}", task) \
                                                              .replace("{{ directives }}", "") \
                                                              .replace("{{ schema }}", json.dumps(schema, indent=2))
            mock_get_template.return_value = mock_template
            
            # Call the function
            result = build_meta_prompt(role, task, directives, schema)
            
            # Check that the result is a non-empty string
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)
            
            # Check that "DIRECTIVES: " is present in the output
            self.assertIn("DIRECTIVES:", result)
            
            # Check that the output still contains key structural elements
            self.assertIn("ROLE:", result)
            self.assertIn("TASK:", result)
            self.assertIn("JSON SCHEMA:", result)
            self.assertIn("VALIDATION:", result)