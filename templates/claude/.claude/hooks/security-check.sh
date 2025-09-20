#!/bin/bash
# Security-focused pre-tool check
# Enhanced security validation before tool execution

set -e

echo "🔒 Running security validation..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check for secrets in files
check_secrets() {
    echo "  🕵️  Scanning for secrets..."

    # Common secret patterns
    local secret_patterns=(
        "password\s*[=:]\s*['\"][^'\"]{8,}['\"]"
        "api[_-]?key\s*[=:]\s*['\"][^'\"]{16,}['\"]"
        "secret[_-]?key\s*[=:]\s*['\"][^'\"]{16,}['\"]"
        "access[_-]?token\s*[=:]\s*['\"][^'\"]{16,}['\"]"
        "private[_-]?key\s*[=:]\s*['\"][^'\"]{32,}['\"]"
        "aws[_-]?secret\s*[=:]\s*['\"][^'\"]{20,}['\"]"
        "bearer\s+[a-zA-Z0-9._-]{20,}"
        "['\"]ssh-rsa\s+[A-Za-z0-9+/]{200,}['\"]"
    )

    local found_secrets=false

    for pattern in "${secret_patterns[@]}"; do
        if grep -r -i -E "$pattern" . \
            --include="*.rs" --include="*.js" --include="*.ts" --include="*.py" \
            --include="*.go" --include="*.java" --include="*.json" --include="*.yaml" \
            --include="*.yml" --include="*.toml" --include="*.env" \
            --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="target" \
            --exclude-dir="build" --exclude-dir="dist" 2>/dev/null | head -3; then
            found_secrets=true
        fi
    done

    if [[ "$found_secrets" == "true" ]]; then
        echo "❌ SECURITY ALERT: Potential secrets found in code!"
        echo "💡 Consider using environment variables or secure secret management."
        echo "💡 Add secrets to .gitignore and use tools like dotenv or vault."
        exit 1
    fi

    echo "  ✓ No obvious secrets detected"
}

# Function to check file permissions
check_file_permissions() {
    echo "  🔐 Checking file permissions..."

    # Check for overly permissive files
    if find . -type f -perm -002 2>/dev/null | grep -v ".git" | head -5 | grep -q .; then
        echo "  ⚠️  World-writable files found:"
        find . -type f -perm -002 2>/dev/null | grep -v ".git" | head -5
        echo "  💡 Consider restricting permissions with: chmod 644 <files>"
    fi

    # Check for executable scripts without proper shebang
    find . -name "*.sh" -executable -type f 2>/dev/null | while read -r script; do
        if ! head -1 "$script" | grep -q "^#!"; then
            echo "  ⚠️  Executable script without shebang: $script"
        fi
    done

    echo "  ✓ File permissions checked"
}

# Function to validate dependencies for known vulnerabilities
check_dependencies() {
    echo "  📦 Checking dependencies for vulnerabilities..."

    # Rust dependencies
    if [[ -f "Cargo.toml" ]] && command_exists cargo; then
        if command_exists cargo-audit; then
            if ! cargo audit --quiet; then
                echo "❌ SECURITY ALERT: Vulnerable dependencies found!"
                echo "💡 Run 'cargo audit' for details and 'cargo audit fix' to attempt fixes."
                exit 1
            fi
            echo "  ✓ Rust dependencies are secure"
        else
            echo "  ⚠️  cargo-audit not installed. Install with: cargo install cargo-audit"
        fi
    fi

    # Node.js dependencies
    if [[ -f "package.json" ]] && command_exists npm; then
        if ! npm audit --audit-level=high --quiet 2>/dev/null; then
            echo "❌ SECURITY ALERT: High-severity vulnerabilities in npm packages!"
            echo "💡 Run 'npm audit' for details and 'npm audit fix' to attempt fixes."
            exit 1
        fi
        echo "  ✓ Node.js dependencies are secure"
    fi

    # Python dependencies
    if [[ -f "requirements.txt" ]] && command_exists safety; then
        if ! python -m safety check --quiet; then
            echo "❌ SECURITY ALERT: Vulnerable Python packages found!"
            echo "💡 Run 'safety check' for details."
            exit 1
        fi
        echo "  ✓ Python dependencies are secure"
    fi
}

# Function to check for insecure coding patterns
check_insecure_patterns() {
    echo "  🧐 Scanning for insecure coding patterns..."

    local issues_found=false

    # SQL injection patterns
    if grep -r -i "format.*sql\|concat.*sql\|\".*\+.*sql" . \
        --include="*.rs" --include="*.js" --include="*.py" --include="*.go" \
        --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="target" \
        2>/dev/null | head -3 | grep -q .; then
        echo "  ⚠️  Potential SQL injection patterns found"
        issues_found=true
    fi

    # Command injection patterns
    if grep -r -i "system\|exec\|shell_exec\|eval" . \
        --include="*.rs" --include="*.js" --include="*.py" --include="*.go" \
        --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="target" \
        2>/dev/null | grep -v "test\|example" | head -3 | grep -q .; then
        echo "  ⚠️  Potential command injection patterns found"
        issues_found=true
    fi

    # Hardcoded crypto keys or salts
    if grep -r -i "salt.*=.*['\"][a-zA-Z0-9]{8,}['\"]" . \
        --include="*.rs" --include="*.js" --include="*.py" --include="*.go" \
        --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="target" \
        2>/dev/null | head -3 | grep -q .; then
        echo "  ⚠️  Potential hardcoded cryptographic material found"
        issues_found=true
    fi

    # Weak random number generation
    if grep -r -i "rand()\|random()\|Math.random" . \
        --include="*.rs" --include="*.js" --include="*.py" --include="*.go" \
        --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="target" \
        2>/dev/null | grep -v "test\|example" | head -3 | grep -q .; then
        echo "  ⚠️  Potentially weak random number generation found"
        echo "  💡 Consider using cryptographically secure random generators"
        issues_found=true
    fi

    # Unsafe deserialization patterns
    if grep -r -i "pickle.loads\|yaml.load[^_]\|eval.*json" . \
        --include="*.py" --include="*.js" \
        --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="target" \
        2>/dev/null | head -3 | grep -q .; then
        echo "  ⚠️  Potentially unsafe deserialization found"
        issues_found=true
    fi

    if [[ "$issues_found" == "false" ]]; then
        echo "  ✓ No obvious insecure patterns detected"
    fi
}

# Function to check git security
check_git_security() {
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        return 0
    fi

    echo "  📂 Checking git security..."

    # Check for large files being committed
    if git diff --cached --name-only | xargs -I {} find {} -size +10M 2>/dev/null | head -1 | grep -q .; then
        echo "  ⚠️  Large files (>10MB) staged for commit"
        echo "  💡 Consider using Git LFS for large files"
    fi

    # Check for binary files that might contain secrets
    if git diff --cached --name-only | xargs file 2>/dev/null | grep -i "executable\|binary" | head -3 | grep -q .; then
        echo "  ⚠️  Binary files being committed - ensure they don't contain secrets"
    fi

    # Check for .env files being committed
    if git diff --cached --name-only | grep -E "\.env$|\.env\." | head -3 | grep -q .; then
        echo "❌ SECURITY ALERT: Environment files (.env) are being committed!"
        echo "💡 Add *.env to .gitignore and remove from staging"
        exit 1
    fi

    # Check for private key files
    if git diff --cached --name-only | grep -E "\.(key|pem|p12|pfx)$" | head -3 | grep -q .; then
        echo "❌ SECURITY ALERT: Private key files are being committed!"
        echo "💡 Remove private keys from staging and add to .gitignore"
        exit 1
    fi

    echo "  ✓ Git security checks passed"
}

# Function to check network security (if applicable)
check_network_security() {
    echo "  🌐 Checking network security patterns..."

    # Check for unencrypted HTTP URLs in production code
    if grep -r "http://[^/]" . \
        --include="*.rs" --include="*.js" --include="*.py" --include="*.go" \
        --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="target" \
        2>/dev/null | grep -v "localhost\|127.0.0.1\|test\|example" | head -3 | grep -q .; then
        echo "  ⚠️  Unencrypted HTTP URLs found in code"
        echo "  💡 Consider using HTTPS for production URLs"
    fi

    # Check for disabled SSL verification
    if grep -r -i "verify.*false\|ssl.*false\|insecure.*true" . \
        --include="*.rs" --include="*.js" --include="*.py" --include="*.go" \
        --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="target" \
        2>/dev/null | head -3 | grep -q .; then
        echo "  ⚠️  Disabled SSL verification found"
        echo "  💡 Ensure SSL verification is enabled in production"
    fi

    echo "  ✓ Network security patterns checked"
}

# Function to validate configuration security
check_config_security() {
    echo "  ⚙️  Checking configuration security..."

    # Check for debug mode in production configs
    if grep -r -i "debug.*true\|development.*mode" . \
        --include="*.toml" --include="*.json" --include="*.yaml" --include="*.yml" \
        --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="target" \
        2>/dev/null | head -3 | grep -q .; then
        echo "  ⚠️  Debug mode enabled in configuration files"
        echo "  💡 Ensure debug mode is disabled in production"
    fi

    # Check for default passwords or keys
    if grep -r -i "password.*123\|password.*admin\|key.*test\|secret.*test" . \
        --include="*.toml" --include="*.json" --include="*.yaml" --include="*.yml" \
        --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="target" \
        2>/dev/null | head -3 | grep -q .; then
        echo "  ⚠️  Default or test passwords/keys found in configuration"
        echo "  💡 Use strong, unique credentials for all environments"
    fi

    echo "  ✓ Configuration security checked"
}

# Main security check execution
main() {
    echo "🔒 Starting comprehensive security validation..."

    # Core security checks
    check_secrets
    check_file_permissions
    check_dependencies
    check_insecure_patterns
    check_git_security
    check_network_security
    check_config_security

    echo "✅ Security validation completed successfully!"
    echo ""
    echo "🔒 Security Summary:"
    echo "  - Secrets scan: ✓"
    echo "  - File permissions: ✓"
    echo "  - Dependencies: ✓"
    echo "  - Code patterns: ✓"
    echo "  - Git security: ✓"
    echo "  - Network patterns: ✓"
    echo "  - Configuration: ✓"
    echo ""
}

# Run main function
main