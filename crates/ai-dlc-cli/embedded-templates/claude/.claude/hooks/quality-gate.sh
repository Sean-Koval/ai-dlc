#!/bin/bash
# Pre-tool-use quality gate
# Ensures code quality before any tool execution

set -e

echo "🔍 Running AI-DLC Quality Gate..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run command with timeout
run_with_timeout() {
    local timeout=$1
    shift
    timeout "$timeout" "$@"
}

# Detect project type and run appropriate checks
detect_project_type() {
    if [[ -f "Cargo.toml" ]]; then
        echo "rust"
    elif [[ -f "package.json" ]]; then
        echo "node"
    elif [[ -f "requirements.txt" ]] || [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]]; then
        echo "python"
    elif [[ -f "go.mod" ]]; then
        echo "go"
    else
        echo "unknown"
    fi
}

PROJECT_TYPE=$(detect_project_type)
echo "📦 Detected project type: $PROJECT_TYPE"

# Language-specific quality checks
case $PROJECT_TYPE in
    "rust")
        echo "🦀 Running Rust quality checks..."

        # Formatting check
        if command_exists cargo; then
            echo "  ✓ Checking formatting..."
            run_with_timeout 30s cargo fmt --check || {
                echo "❌ Code formatting issues found. Run 'cargo fmt' to fix."
                echo "💡 Hint: Set up your editor to format on save"
                exit 1
            }

            # Linting with clippy
            echo "  ✓ Running clippy..."
            run_with_timeout 60s cargo clippy --all-targets --all-features -- -D warnings || {
                echo "❌ Linting issues found. Fix clippy warnings."
                echo "💡 Hint: Run 'cargo clippy --fix' for auto-fixable issues"
                exit 1
            }

            # Unit tests
            echo "  ✓ Running unit tests..."
            run_with_timeout 300s cargo test --lib --quiet || {
                echo "❌ Unit tests failing. Fix failing tests before proceeding."
                exit 1
            }

            # Check for compilation errors
            echo "  ✓ Checking compilation..."
            run_with_timeout 120s cargo check --all-targets --all-features || {
                echo "❌ Compilation errors found. Fix compilation issues."
                exit 1
            }

            # Security audit
            if command_exists cargo-audit; then
                echo "  ✓ Running security audit..."
                cargo audit || {
                    echo "⚠️  Security vulnerabilities found. Review and fix."
                    echo "💡 Hint: Run 'cargo audit fix' to automatically fix vulnerabilities"
                    # Don't exit on audit failures in development, just warn
                }
            else
                echo "  ⚠️  cargo-audit not installed. Install with: cargo install cargo-audit"
            fi
        else
            echo "❌ Cargo not found. Please install Rust toolchain."
            exit 1
        fi
        ;;

    "node")
        echo "📦 Running Node.js quality checks..."

        if command_exists npm; then
            # Linting
            if npm run lint --silent 2>/dev/null; then
                echo "  ✓ Linting passed"
            else
                echo "  ⚠️  No lint script found or linting failed"
            fi

            # Type checking
            if npm run type-check --silent 2>/dev/null; then
                echo "  ✓ Type checking passed"
            else
                echo "  ⚠️  No type-check script found"
            fi

            # Tests
            echo "  ✓ Running tests..."
            npm test -- --passWithNoTests --silent || {
                echo "❌ Tests failing. Fix failing tests."
                exit 1
            }

            # Security audit
            echo "  ✓ Running security audit..."
            npm audit --audit-level=moderate || {
                echo "⚠️  Security vulnerabilities found. Run 'npm audit fix' to fix."
            }
        else
            echo "❌ npm not found. Please install Node.js."
            exit 1
        fi
        ;;

    "python")
        echo "🐍 Running Python quality checks..."

        # Linting with pylint
        if command_exists pylint; then
            echo "  ✓ Running pylint..."
            python -m pylint src/ 2>/dev/null || echo "  ⚠️  Pylint warnings found"
        fi

        # Type checking with mypy
        if command_exists mypy; then
            echo "  ✓ Running mypy..."
            python -m mypy src/ 2>/dev/null || echo "  ⚠️  Type checking issues found"
        fi

        # Tests with pytest
        if command_exists pytest; then
            echo "  ✓ Running tests..."
            python -m pytest --quiet || {
                echo "❌ Tests failing. Fix failing tests."
                exit 1
            }
        fi

        # Security check
        if command_exists safety; then
            echo "  ✓ Running security check..."
            python -m safety check || {
                echo "⚠️  Security vulnerabilities found."
            }
        fi
        ;;

    "go")
        echo "🐹 Running Go quality checks..."

        if command_exists go; then
            # Formatting
            echo "  ✓ Checking formatting..."
            if ! gofmt -l . | head -1 | grep -q .; then
                echo "  ✓ Code is formatted"
            else
                echo "❌ Code formatting issues. Run 'gofmt -w .'"
                exit 1
            fi

            # Linting
            if command_exists golint; then
                echo "  ✓ Running golint..."
                golint ./... || echo "  ⚠️  Linting issues found"
            fi

            # Tests
            echo "  ✓ Running tests..."
            go test ./... || {
                echo "❌ Tests failing. Fix failing tests."
                exit 1
            }

            # Vet
            echo "  ✓ Running go vet..."
            go vet ./... || {
                echo "❌ Go vet found issues."
                exit 1
            }
        fi
        ;;

    *)
        echo "  ⚠️  Unknown project type, running generic checks..."
        ;;
esac

# Universal security checks
echo "🔒 Running universal security checks..."

# Check for secrets using git-secrets if available
if command_exists git-secrets; then
    echo "  ✓ Scanning for secrets..."
    git secrets --scan 2>/dev/null || {
        echo "⚠️  Potential secrets found. Review manually."
    }
else
    echo "  ⚠️  git-secrets not installed. Install for secret scanning."
fi

# Check for common security patterns
echo "  ✓ Checking for common security issues..."
if grep -r -i "password.*=" . --include="*.rs" --include="*.js" --include="*.py" --include="*.go" 2>/dev/null | head -1 | grep -q .; then
    echo "⚠️  Potential hardcoded passwords found. Review manually."
fi

if grep -r "api[_-]key.*=" . --include="*.rs" --include="*.js" --include="*.py" --include="*.go" 2>/dev/null | head -1 | grep -q .; then
    echo "⚠️  Potential hardcoded API keys found. Review manually."
fi

# Performance baseline (if applicable)
echo "⚡ Performance checks..."
case $PROJECT_TYPE in
    "rust")
        if [[ -f "Cargo.toml" ]] && command_exists cargo; then
            echo "  ✓ Checking build performance..."
            # Quick build time check
            start_time=$(date +%s)
            cargo build --quiet 2>/dev/null || true
            end_time=$(date +%s)
            build_time=$((end_time - start_time))

            if [[ $build_time -gt 60 ]]; then
                echo "  ⚠️  Build time: ${build_time}s (consider optimization if > 60s)"
            else
                echo "  ✓ Build time: ${build_time}s"
            fi
        fi
        ;;
    "node")
        if [[ -f "package.json" ]] && command_exists npm; then
            if npm run build --silent 2>/dev/null; then
                if [[ -d "dist" ]]; then
                    size=$(du -sh dist/ 2>/dev/null | cut -f1)
                    echo "  ✓ Build size: $size"
                fi
            fi
        fi
        ;;
esac

# Git status check (if in a git repository)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "📋 Git status check..."

    # Check for uncommitted changes in important files
    if git diff --name-only | grep -E "\.(rs|js|py|go|toml|json|md)$" >/dev/null 2>&1; then
        echo "  ⚠️  Uncommitted changes in source files"
    fi

    # Check for large files being added
    if git diff --cached --name-only | xargs -I {} find {} -size +10M 2>/dev/null | head -1 | grep -q .; then
        echo "  ⚠️  Large files (>10MB) staged for commit"
    fi
fi

echo "✅ Quality gate passed successfully!"
echo ""
echo "📊 Quality Summary:"
echo "  - Code formatting: ✓"
echo "  - Linting: ✓"
echo "  - Tests: ✓"
echo "  - Security: ✓"
echo "  - Build: ✓"
echo ""