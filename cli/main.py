#!/usr/bin/env python3
"""
CLI entry point for the ai-dlc tool.

This module implements the main Command-Line Interface using Typer.
"""

import os
import yaml
import json
import re
import difflib
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import typer
import jsonschema
from jinja2 import Environment, Template
from cli.schema_utils import load_and_validate_schema, InvalidSchemaError
from cli.check_utils import load_check_rules, InvalidCheckRuleError, CustomCheckRule
from cli.redact_utils import redact_sensitive_data

# Create a Typer application instance
app = typer.Typer(
    help="AI-DLC: AI-driven Development Lifecycle Companion",
)


@app.command()
def main() -> None:
    """
    Main entry point for the ai-dlc command.
    
    This is the default command that runs when no subcommand is specified.
    """
    typer.echo("Welcome to AI-DLC: AI-driven Development Lifecycle Companion")


@app.command()
def scaffold(
    team_name: str = typer.Argument(..., help="The name of the team to create the library for.")
) -> None:
    """
    Scaffold a new prompt library for a team.
    
    Creates a directory structure for a new prompt library with subdirectories
    for templates, schemas, examples, and checks.
    """
    # Check if the team directory already exists
    if os.path.exists(team_name):
        typer.echo(f"Error: Directory '{team_name}' already exists.", err=True)
        raise typer.Exit(code=1)
    
    # Create the root team directory
    os.makedirs(team_name, exist_ok=False)
    
    # Create subdirectories
    subdirs = ["templates", "schemas", "examples", "checks"]
    for subdir in subdirs:
        subdir_path = os.path.join(team_name, subdir)
        os.makedirs(subdir_path, exist_ok=False)
        
        # Create .gitkeep file in each subdirectory
        gitkeep_path = os.path.join(subdir_path, ".gitkeep")
        with open(gitkeep_path, "w") as f:
            pass  # Create an empty file
    
    # Create a basic README.md in the team root directory
    readme_path = os.path.join(team_name, "README.md")
    with open(readme_path, "w") as f:
        f.write(f"# Prompt Library for {team_name}\n")
    
    typer.echo(f"Successfully scaffolded prompt library for team '{team_name}' at ./{team_name}")


@app.command()
def generate(
    template: Path = typer.Option(
        ...,
        "--template", "-t",
        help="Path to the Jinja2 template file (e.g., template.md.j2)."
    ),
    input_path: Path = typer.Option(
        ...,
        "--input", "-i",
        help="Path to the input YAML data file."
    ),
    schema_path: Path = typer.Option(
        ...,
        "--schema", "-s",
        help="Path to the JSON schema file for input validation."
    ),
) -> None:
    """
    Generate a prompt from a template with validated input data.
    
    Reads a Jinja2 template file, validates input YAML data against a JSON schema,
    and renders the template with the validated data.
    
    This implements the :ArchitecturalPattern:DataValidation and
    :ArchitecturalPattern:Templating Engine interaction.
    """
    # Load and validate the schema
    try:
        loaded_schema = load_and_validate_schema(schema_path)
    except InvalidSchemaError as e:
        typer.echo(f"Error loading schema '{schema_path}': {e}", err=True)
        raise typer.Exit(code=1)
    
    # Load input YAML data
    try:
        # Check if the input file exists
        if not input_path.exists():
            typer.echo(f"Error: Input file '{input_path}' does not exist.", err=True)
            raise typer.Exit(code=1)
        
        # Read the content of the input file
        input_content = input_path.read_text()
        
        # Parse the YAML content
        input_data = yaml.safe_load(input_content)
    except FileNotFoundError:
        typer.echo(f"Error: Input file '{input_path}' not found.", err=True)
        raise typer.Exit(code=1)
    except yaml.YAMLError as e:
        typer.echo(f"Error: Invalid YAML in input file '{input_path}': {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error: Failed to read input file '{input_path}': {e}", err=True)
        raise typer.Exit(code=1)
    
    # Validate input data against schema
    try:
        jsonschema.validate(instance=input_data, schema=loaded_schema)
    except jsonschema.exceptions.ValidationError as e:
        typer.echo(f"Input data validation failed: {e.message} at path {list(e.path)}", err=True)
        raise typer.Exit(code=1)
    
    # Check if the template file exists
    if not template.exists():
        typer.echo(f"Error: Template file '{template}' does not exist.", err=True)
        raise typer.Exit(code=1)
    
    # Render Jinja2 template
    try:
        # Read the content of the template file
        template_content = template.read_text()
        
        # Create Jinja2 Environment and Template
        env = Environment(autoescape=False)
        jinja_template = env.from_string(template_content)
        
        # Render the template with the validated input data
        rendered_output = jinja_template.render(**input_data)
        
        # Output the rendered content
        typer.echo(rendered_output)
    except FileNotFoundError:
        typer.echo(f"Error: Template file '{template}' not found.", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error: Failed to render template '{template}': {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def validate(
    prompt: Path = typer.Option(
        ...,
        "--prompt", "-p",
        help="Path to the generated prompt file or directory of prompt files."
    ),
    checks: Path = typer.Option(
        ...,
        "--checks", "-c",
        help="Path to the .CHECKS.yaml file."
    ),
) -> None:
    """
    Validate prompt files against custom validation rules.
    
    Takes a prompt file (or directory of prompt files) and validates it against
    custom validation rules defined in a .CHECKS.yaml file.
    
    This implements the :ArchitecturalPattern:Rule Engine for :CustomValidationRule
    to address the :Problem:Generated prompts not meeting specific domain requirements
    with the :Solution:Automated custom validation.
    """
    # Load check rules
    try:
        rules = load_check_rules(checks)
    except FileNotFoundError:
        typer.echo(f"Error: Checks file '{checks}' not found.", err=True)
        raise typer.Exit(code=1)
    except InvalidCheckRuleError as e:
        typer.echo(f"Error loading check rules: {e}", err=True)
        raise typer.Exit(code=1)
    
    # Identify prompt files
    prompt_files = []
    try:
        if prompt.is_file():
            # Single file
            prompt_files.append(prompt)
        elif prompt.is_dir():
            # Directory - find all potential prompt files recursively
            # For now, we'll consider .md, .txt files and files without extension as potential prompt files
            for ext in ["*.md", "*.txt", "*"]:
                prompt_files.extend(list(prompt.glob(f"**/{ext}")))
            # Remove duplicates (files without extension might be counted twice)
            prompt_files = list(set(prompt_files))
            # Filter out directories
            prompt_files = [f for f in prompt_files if f.is_file()]
        else:
            typer.echo(f"Error: Prompt path '{prompt}' is neither a file nor a directory.", err=True)
            raise typer.Exit(code=1)
    except FileNotFoundError:
        typer.echo(f"Error: Prompt path '{prompt}' not found.", err=True)
        raise typer.Exit(code=1)
    
    if not prompt_files:
        typer.echo(f"Warning: No prompt files found at '{prompt}'.", err=True)
        raise typer.Exit(code=1)
    
    # Process each prompt file
    any_failures = False
    
    for prompt_file in prompt_files:
        # Read prompt content
        try:
            prompt_content = prompt_file.read_text()
        except Exception as e:
            typer.echo(f"Error reading prompt file '{prompt_file}': {e}", err=True)
            any_failures = True
            continue
        
        # Apply each rule to the prompt content
        file_failures = []
        
        for rule in rules:
            if rule.type == "regex_match":
                # Regex match check
                match = re.search(rule.config.pattern, prompt_content)
                if rule.config.should_match and not match:
                    file_failures.append({
                        "rule_id": rule.id,
                        "message": f"Pattern '{rule.config.pattern}' did not match."
                    })
                elif not rule.config.should_match and match:
                    file_failures.append({
                        "rule_id": rule.id,
                        "message": f"Pattern '{rule.config.pattern}' unexpectedly matched."
                    })
            
            elif rule.type == "keyword_presence":
                # Keyword presence check
                keywords = rule.config.keywords
                case_sensitive = rule.config.case_sensitive
                match_all = rule.config.match_all
                
                # Check for keyword presence using regex with word boundaries for whole word matching
                missing_keywords = []
                found_keywords = []
                
                for keyword in keywords:
                    # Create regex pattern with word boundaries to match whole words only
                    pattern = r"\b" + re.escape(keyword) + r"\b"
                    
                    # Perform search with case sensitivity setting
                    if case_sensitive:
                        match = re.search(pattern, prompt_content)
                    else:
                        match = re.search(pattern, prompt_content, re.IGNORECASE)
                    
                    if match:
                        found_keywords.append(keyword)
                    else:
                        missing_keywords.append(keyword)
                
                # Determine if validation passes or fails based on match_all setting
                if match_all and missing_keywords:
                    # For match_all=True, ANY missing keyword should cause failure
                    file_failures.append({
                        "rule_id": rule.id,
                        "message": f"Not all required keywords present. Missing: {', '.join(missing_keywords)}"
                    })
                elif not match_all and not found_keywords:
                    # For match_all=False, NO found keywords should cause failure
                    file_failures.append({
                        "rule_id": rule.id,
                        "message": f"None of the keywords were found: {', '.join(keywords)}"
                    })
        
        # Report failures for this file
        if file_failures:
            any_failures = True
            typer.echo(f"Validation failed for {prompt_file}:")
            for failure in file_failures:
                typer.echo(f"  - Rule '{failure['rule_id']}': {failure['message']}")
    
    # Overall result
    if any_failures:
        typer.echo("Custom prompt validation failed for one or more files.")
        raise typer.Exit(code=1)
    else:
        typer.echo("All prompts passed custom validation.")
        raise typer.Exit(code=0)


@app.command()
def redact(
    path: Path = typer.Argument(
        ...,
        help="Path to the prompt file or directory of prompt files to redact."
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir", "-o",
        help="Directory to save redacted files. If not provided, files are redacted in-place (with a .bak backup)."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be redacted without modifying files."
    ),
) -> None:
    """
    Redact sensitive data from prompt files.
    
    Takes a prompt file or directory of prompt files and redacts sensitive information
    such as email addresses, API keys, and credit card numbers.
    
    This implements the :SecurityFeature:DataRedaction to mitigate
    :SecurityVulnerability:SensitiveDataLeakage.
    """
    # Identify prompt files
    prompt_files = []
    try:
        if path.is_file():
            # Single file
            prompt_files.append(path)
        elif path.is_dir():
            # Directory - find all files recursively
            prompt_files.extend(list(path.rglob('*')))
            # Filter out directories
            prompt_files = [f for f in prompt_files if f.is_file()]
        else:
            typer.echo(f"Error: Path '{path}' is neither a file nor a directory.", err=True)
            raise typer.Exit(code=1)
    except FileNotFoundError:
        typer.echo(f"Error: Path '{path}' not found.", err=True)
        raise typer.Exit(code=1)
    
    if not prompt_files:
        typer.echo(f"Warning: No files found at '{path}'.", err=True)
        raise typer.Exit(code=1)
    
    # Process each prompt file
    for prompt_file_path in prompt_files:
        # Read prompt content
        try:
            original_content = prompt_file_path.read_text()
        except Exception as e:
            typer.echo(f"Error reading file '{prompt_file_path}': {e}", err=True)
            continue
        
        # Redact sensitive data
        redacted_content = redact_sensitive_data(original_content)
        
        # Check if content was changed
        if original_content == redacted_content and not dry_run:
            typer.echo(f"No sensitive data found in {prompt_file_path}. No changes made.")
            continue
        
        # Handle dry run
        if dry_run:
            typer.echo(f"--- Dry run: Potential redactions for {prompt_file_path} ---")
            if original_content != redacted_content:
                # Generate a simple diff to show changes
                diff = difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    redacted_content.splitlines(keepends=True),
                    fromfile=str(prompt_file_path),
                    tofile=f"{prompt_file_path} (redacted)"
                )
                typer.echo(''.join(diff))
            else:
                typer.echo("No sensitive data found.")
            continue
        
        # Handle actual redaction (not dry run and content was changed)
        if original_content != redacted_content:
            # Determine output path
            if output_dir:
                # Create output directory if it doesn't exist
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Determine relative path if input was a directory
                if path.is_dir():
                    rel_path = prompt_file_path.relative_to(path)
                    output_path = output_dir / rel_path
                    # Create parent directories if needed
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    output_path = output_dir / prompt_file_path.name
                
                # Write redacted content to output path
                output_path.write_text(redacted_content)
                typer.echo(f"Redacted content written to {output_path}.")
            else:
                # In-place redaction with backup
                backup_path = prompt_file_path.with_suffix(prompt_file_path.suffix + '.bak')
                shutil.copy2(prompt_file_path, backup_path)
                prompt_file_path.write_text(redacted_content)
                typer.echo(f"Redacted content written to {prompt_file_path}. Backup saved to {backup_path}.")
    
    # Overall result
    if not dry_run:
        typer.echo("Redaction process complete.")
    else:
        typer.echo("Dry run complete. No files were modified.")


if __name__ == "__main__":
    app()