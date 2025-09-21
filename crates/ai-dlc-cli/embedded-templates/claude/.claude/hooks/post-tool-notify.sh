#!/bin/bash
# Post-tool-use notification and cleanup
# Runs after successful tool execution

set -e

# Get tool information from environment or parameters
TOOL_NAME="${TOOL_NAME:-${1:-unknown}}"
TOOL_STATUS="${TOOL_STATUS:-${2:-completed}}"
TOOL_DURATION="${TOOL_DURATION:-${3:-unknown}}"
TOOL_OUTPUT="${TOOL_OUTPUT:-}"

# Configuration (can be overridden by settings.local.json)
DESKTOP_NOTIFICATIONS=${DESKTOP_NOTIFICATIONS:-true}
SLACK_NOTIFICATIONS=${SLACK_NOTIFICATIONS:-false}
AUTO_FORMAT=${AUTO_FORMAT:-true}
AUTO_STAGE=${AUTO_STAGE:-true}
ACTIVITY_LOGGING=${ACTIVITY_LOGGING:-true}

echo "📝 Post-tool cleanup and notifications..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to send desktop notification
send_desktop_notification() {
    local title="$1"
    local message="$2"
    local urgency="${3:-normal}"

    if [[ "$DESKTOP_NOTIFICATIONS" != "true" ]]; then
        return 0
    fi

    # Try different notification systems
    if command_exists notify-send; then
        notify-send --urgency="$urgency" "$title" "$message"
    elif command_exists osascript; then
        # macOS
        osascript -e "display notification \"$message\" with title \"$title\""
    elif command_exists powershell.exe; then
        # Windows (WSL)
        powershell.exe -Command "New-BurntToastNotification -Text '$title', '$message'"
    else
        echo "📱 $title: $message"
    fi
}

# Function to send Slack notification
send_slack_notification() {
    local message="$1"
    local channel="${2:-general}"
    local urgency="${3:-normal}"

    if [[ "$SLACK_NOTIFICATIONS" != "true" ]] || [[ -z "$SLACK_WEBHOOK_URL" ]]; then
        return 0
    fi

    local emoji
    case $urgency in
        "critical") emoji=":red_circle:" ;;
        "warning") emoji=":warning:" ;;
        "success") emoji=":white_check_mark:" ;;
        *) emoji=":information_source:" ;;
    esac

    local payload=$(cat <<EOF
{
    "channel": "#$channel",
    "text": "$emoji $message",
    "username": "AI-DLC Bot"
}
EOF
)

    curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK_URL" 2>/dev/null || echo "⚠️  Slack notification failed"
}

# Determine notification based on tool and status
case $TOOL_NAME in
    "Edit"|"Write"|"MultiEdit")
        if [[ "$TOOL_STATUS" == "completed" ]]; then
            send_desktop_notification "Claude Code" "Code changes completed" "normal"

            # Auto-format if enabled
            if [[ "$AUTO_FORMAT" == "true" ]]; then
                echo "  🎨 Auto-formatting code..."

                if [[ -f "Cargo.toml" ]] && command_exists cargo; then
                    cargo fmt 2>/dev/null || echo "  ⚠️  Formatting failed"
                elif [[ -f "package.json" ]] && command_exists npm; then
                    npm run format 2>/dev/null || npm run prettier 2>/dev/null || echo "  ⚠️  No format script found"
                elif [[ -f "pyproject.toml" ]] && command_exists black; then
                    black . 2>/dev/null || echo "  ⚠️  Black formatting failed"
                fi
            fi

            # Auto-stage formatting changes
            if [[ "$AUTO_STAGE" == "true" ]] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
                if ! git diff --quiet; then
                    git add -A 2>/dev/null || true
                    echo "  📝 Auto-staged formatting changes"
                fi
            fi
        fi
        ;;

    "Bash")
        if [[ "$TOOL_STATUS" == "completed" ]]; then
            # Check if it was a deployment or build command
            if echo "$TOOL_OUTPUT" | grep -qi "deploy\|build\|release"; then
                send_desktop_notification "Claude Code" "Build/Deploy completed" "normal"
                send_slack_notification "🚀 Deployment completed via Claude Code" "deployments" "success"
            fi
        fi
        ;;

    "Test"|"Coverage")
        if [[ "$TOOL_STATUS" == "completed" ]]; then
            send_desktop_notification "Claude Code" "Tests completed" "normal"
        elif [[ "$TOOL_STATUS" == "failed" ]]; then
            send_desktop_notification "Claude Code" "Tests failed" "critical"
            send_slack_notification "❌ Tests failing in AI-DLC project" "code-quality" "critical"
        fi
        ;;

    "Deploy")
        if [[ "$TOOL_STATUS" == "completed" ]]; then
            send_desktop_notification "Claude Code" "🚀 Deployment completed" "normal"
            send_slack_notification "🚀 Deployment completed via Claude Code" "deployments" "success"
        elif [[ "$TOOL_STATUS" == "failed" ]]; then
            send_desktop_notification "Claude Code" "❌ Deployment failed" "critical"
            send_slack_notification "🚨 Deployment failed in AI-DLC project" "deployments" "critical"
        fi
        ;;

    "Security"|"Audit")
        if [[ "$TOOL_STATUS" == "completed" ]]; then
            if echo "$TOOL_OUTPUT" | grep -qi "vulnerabilit\|security.*issue"; then
                send_desktop_notification "Claude Code" "⚠️ Security issues found" "warning"
                send_slack_notification "🔒 Security audit found issues" "security-alerts" "warning"
            else
                send_desktop_notification "Claude Code" "🔒 Security audit clean" "normal"
            fi
        fi
        ;;

    *)
        # Generic notification for other tools
        if [[ "$TOOL_STATUS" == "completed" ]]; then
            send_desktop_notification "Claude Code" "Tool '$TOOL_NAME' completed" "normal"
        fi
        ;;
esac

# Update activity log
if [[ "$ACTIVITY_LOGGING" == "true" ]]; then
    echo "  📊 Updating activity log..."

    # Create .claude directory if it doesn't exist
    mkdir -p .claude

    # Log activity with timestamp
    local timestamp=$(date -Iseconds)
    local log_entry="$timestamp: $TOOL_NAME $TOOL_STATUS"

    if [[ -n "$TOOL_DURATION" ]] && [[ "$TOOL_DURATION" != "unknown" ]]; then
        log_entry="$log_entry (${TOOL_DURATION}s)"
    fi

    echo "$log_entry" >> .claude/activity.log

    # Keep only last 1000 entries to prevent log from growing too large
    if [[ -f .claude/activity.log ]]; then
        tail -n 1000 .claude/activity.log > .claude/activity.log.tmp
        mv .claude/activity.log.tmp .claude/activity.log
    fi
fi

# Performance tracking
if [[ -n "$TOOL_DURATION" ]] && [[ "$TOOL_DURATION" != "unknown" ]]; then
    echo "  ⏱️  Tool execution time: ${TOOL_DURATION}s"

    # Warn about slow operations
    if [[ $TOOL_DURATION -gt 30 ]]; then
        echo "  ⚠️  Slow operation detected (${TOOL_DURATION}s). Consider optimization."
        send_desktop_notification "Claude Code" "Slow operation: $TOOL_NAME (${TOOL_DURATION}s)" "warning"
    fi
fi

# Project health check (if git repository)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "  📋 Project health check..."

    # Check for large number of uncommitted files
    local uncommitted_count=$(git status --porcelain | wc -l)
    if [[ $uncommitted_count -gt 20 ]]; then
        echo "  ⚠️  Large number of uncommitted files ($uncommitted_count). Consider committing."
    fi

    # Check if branch is behind origin
    if git status --porcelain=v1 --branch | grep -q "behind"; then
        echo "  ⚠️  Branch is behind origin. Consider pulling latest changes."
    fi
fi

# Check disk space (warn if low)
if command_exists df; then
    local disk_usage=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
    if [[ $disk_usage -gt 90 ]]; then
        echo "  ⚠️  Low disk space (${disk_usage}% used). Consider cleanup."
        send_desktop_notification "Claude Code" "Low disk space warning (${disk_usage}% used)" "warning"
    fi
fi

# Memory usage check (warn if high)
if command_exists free; then
    local memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [[ $memory_usage -gt 85 ]]; then
        echo "  ⚠️  High memory usage (${memory_usage}%). Consider closing unused applications."
    fi
fi

# Cleanup temporary files if any were created
if [[ -d "/tmp/claude-workspace" ]]; then
    echo "  🧹 Cleaning up temporary files..."
    find /tmp/claude-workspace -type f -mtime +1 -delete 2>/dev/null || true
fi

echo "✅ Post-tool cleanup completed"

# Summary statistics (if activity log exists)
if [[ -f .claude/activity.log ]]; then
    local total_activities=$(wc -l < .claude/activity.log)
    local today_activities=$(grep "$(date +%Y-%m-%d)" .claude/activity.log | wc -l)

    echo ""
    echo "📈 Session Summary:"
    echo "  - Today's activities: $today_activities"
    echo "  - Total activities: $total_activities"
    echo "  - Last tool: $TOOL_NAME ($TOOL_STATUS)"
fi