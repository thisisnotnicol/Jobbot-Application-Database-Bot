#!/bin/bash

# BulletProof JobBot Manager
# Ultimate management script for the JobBot Slack integration with bulletproof reliability

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
KEEPER_SCRIPT="$SCRIPT_DIR/keep_bot_running.py"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python3"
PLIST_FILE="$HOME/Library/LaunchAgents/com.jobbot.keeper.plist"
PLIST_SOURCE="$SCRIPT_DIR/com.jobbot.keeper.plist"
KEEPER_PID_FILE="$SCRIPT_DIR/bot_keeper.pid"
SERVICE_NAME="com.jobbot.keeper"

# Log files
KEEPER_LOG="$SCRIPT_DIR/bot_keeper.log"
BOT_LOG="$SCRIPT_DIR/slack_bot_working.log"
KEEPER_OUTPUT="$SCRIPT_DIR/keeper_output.log"
KEEPER_ERROR="$SCRIPT_DIR/keeper_error.log"

# Functions
print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}    🤖 BulletProof JobBot Management System 🛡️${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
}

print_status() {
    local message="$1"
    local status="$2"

    case "$status" in
        "success") echo -e "${GREEN}✅ $message${NC}" ;;
        "error")   echo -e "${RED}❌ $message${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️  $message${NC}" ;;
        "info")    echo -e "${BLUE}ℹ️  $message${NC}" ;;
        *)         echo -e "$message" ;;
    esac
}

check_prerequisites() {
    echo -e "${PURPLE}🔧 Checking Prerequisites...${NC}"
    echo "----------------------------------------"

    local all_good=true

    # Check Python
    if [ -f "$PYTHON_PATH" ]; then
        local python_version=$("$PYTHON_PATH" --version 2>&1)
        print_status "Python: $python_version" "success"
    else
        print_status "Python virtual environment not found: $PYTHON_PATH" "error"
        all_good=false
    fi

    # Check keeper script
    if [ -f "$KEEPER_SCRIPT" ]; then
        print_status "Bot Keeper script found" "success"
    else
        print_status "Bot Keeper script missing: $KEEPER_SCRIPT" "error"
        all_good=false
    fi

    # Check bot script
    local bot_script="$SCRIPT_DIR/slack_bot_working.py"
    if [ -f "$bot_script" ]; then
        print_status "Slack bot script found" "success"
    else
        print_status "Slack bot script missing: $bot_script" "error"
        all_good=false
    fi

    # Check environment variables
    if [ -f "$SCRIPT_DIR/.env" ]; then
        print_status ".env file found" "success"

        # Source .env and check critical vars
        source "$SCRIPT_DIR/.env"

        if [ -n "$SLACK_BOT_TOKEN" ]; then
            print_status "SLACK_BOT_TOKEN: ${SLACK_BOT_TOKEN:0:12}..." "success"
        else
            print_status "SLACK_BOT_TOKEN missing" "error"
            all_good=false
        fi

        if [ -n "$SLACK_APP_TOKEN" ]; then
            print_status "SLACK_APP_TOKEN: ${SLACK_APP_TOKEN:0:12}..." "success"
        else
            print_status "SLACK_APP_TOKEN missing" "error"
            all_good=false
        fi

        # Optional services
        [ -n "$OPENAI_API_KEY" ] && print_status "OpenAI API: Configured" "info" || print_status "OpenAI API: Not configured" "warning"
        [ -n "$NOTION_TOKEN" ] && print_status "Notion API: Configured" "info" || print_status "Notion API: Not configured" "warning"

    else
        print_status ".env file missing" "error"
        all_good=false
    fi

    echo ""
    if $all_good; then
        print_status "All prerequisites met!" "success"
        return 0
    else
        print_status "Some prerequisites are missing" "error"
        return 1
    fi
}

is_keeper_running() {
    if [ -f "$KEEPER_PID_FILE" ]; then
        local pid=$(cat "$KEEPER_PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$KEEPER_PID_FILE" 2>/dev/null
        fi
    fi
    return 1
}

is_service_loaded() {
    launchctl list | grep -q "$SERVICE_NAME"
}

install_service() {
    echo -e "${PURPLE}📦 Installing BulletProof Service...${NC}"
    echo "----------------------------------------"

    if [ ! -f "$PLIST_SOURCE" ]; then
        print_status "Service plist file not found: $PLIST_SOURCE" "error"
        return 1
    fi

    # Create LaunchAgents directory
    mkdir -p "$HOME/Library/LaunchAgents"

    # Copy plist file
    cp "$PLIST_SOURCE" "$PLIST_FILE"
    print_status "Service definition installed" "success"

    # Load service
    launchctl load "$PLIST_FILE" 2>/dev/null
    print_status "Service loaded into launchd" "success"

    echo ""
    print_status "BulletProof service installed successfully!" "success"
    print_status "The bot will start automatically and restart if it crashes" "info"
}

uninstall_service() {
    echo -e "${PURPLE}🗑️  Uninstalling BulletProof Service...${NC}"
    echo "----------------------------------------"

    # Stop service first
    stop_service

    # Unload service
    if is_service_loaded; then
        launchctl unload "$PLIST_FILE" 2>/dev/null
        print_status "Service unloaded from launchd" "success"
    fi

    # Remove plist file
    if [ -f "$PLIST_FILE" ]; then
        rm -f "$PLIST_FILE"
        print_status "Service definition removed" "success"
    fi

    echo ""
    print_status "BulletProof service uninstalled" "success"
}

start_service() {
    echo -e "${PURPLE}🚀 Starting BulletProof JobBot...${NC}"
    echo "----------------------------------------"

    # Check if service is installed
    if [ ! -f "$PLIST_FILE" ]; then
        print_status "Service not installed. Installing now..." "info"
        install_service
    fi

    # Load service if not loaded
    if ! is_service_loaded; then
        launchctl load "$PLIST_FILE" 2>/dev/null
    fi

    # Start service
    launchctl start "$SERVICE_NAME"

    # Wait a moment for startup
    sleep 3

    if is_keeper_running; then
        local pid=$(cat "$KEEPER_PID_FILE")
        print_status "BulletProof JobBot started successfully! (PID: $pid)" "success"
        print_status "Bot will automatically restart if it crashes" "info"
        return 0
    else
        print_status "Failed to start BulletProof JobBot" "error"
        print_status "Check logs for details:" "info"
        echo "  - Keeper log: $KEEPER_LOG"
        echo "  - Error log: $KEEPER_ERROR"
        return 1
    fi
}

stop_service() {
    echo -e "${PURPLE}🛑 Stopping BulletProof JobBot...${NC}"
    echo "----------------------------------------"

    # Stop service
    launchctl stop "$SERVICE_NAME" 2>/dev/null

    # Kill keeper process if still running
    if is_keeper_running; then
        local pid=$(cat "$KEEPER_PID_FILE")
        print_status "Stopping keeper process (PID: $pid)" "info"
        kill "$pid" 2>/dev/null

        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! ps -p "$pid" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done

        # Force kill if necessary
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -9 "$pid" 2>/dev/null
        fi
    fi

    # Clean up any remaining bot processes
    pkill -f "slack_bot_working.py" 2>/dev/null

    # Remove PID file
    rm -f "$KEEPER_PID_FILE" 2>/dev/null

    print_status "BulletProof JobBot stopped" "success"
}

restart_service() {
    echo -e "${PURPLE}🔄 Restarting BulletProof JobBot...${NC}"
    echo "----------------------------------------"

    stop_service
    sleep 2
    start_service
}

check_status() {
    print_header
    echo ""
    echo -e "${PURPLE}📊 System Status${NC}"
    echo "----------------------------------------"

    # Service installation
    if [ -f "$PLIST_FILE" ]; then
        print_status "Service: Installed" "success"
    else
        print_status "Service: Not installed" "warning"
    fi

    # Service loaded
    if is_service_loaded; then
        print_status "LaunchD: Service loaded" "success"
    else
        print_status "LaunchD: Service not loaded" "warning"
    fi

    # Keeper process
    if is_keeper_running; then
        local pid=$(cat "$KEEPER_PID_FILE")
        local memory=$(ps -o rss= -p "$pid" 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')
        print_status "Bot Keeper: Running (PID: $pid, Memory: $memory)" "success"

        # Check bot process
        local bot_pids=$(pgrep -f "slack_bot_working.py")
        if [ -n "$bot_pids" ]; then
            local bot_pid=$(echo "$bot_pids" | head -1)
            local bot_memory=$(ps -o rss= -p "$bot_pid" 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')
            print_status "Slack Bot: Running (PID: $bot_pid, Memory: $bot_memory)" "success"
        else
            print_status "Slack Bot: Not running (Keeper will restart it)" "warning"
        fi

    else
        print_status "Bot Keeper: Not running" "error"
        print_status "Slack Bot: Not running" "error"
    fi

    echo ""
    echo -e "${PURPLE}📋 Recent Activity${NC}"
    echo "----------------------------------------"

    # Recent keeper activity
    if [ -f "$KEEPER_LOG" ]; then
        local last_keeper=$(tail -1 "$KEEPER_LOG" 2>/dev/null | cut -d' ' -f1-2)
        [ -n "$last_keeper" ] && print_status "Keeper last activity: $last_keeper" "info"
    fi

    # Recent bot activity
    if [ -f "$BOT_LOG" ]; then
        local last_bot=$(tail -1 "$BOT_LOG" 2>/dev/null | cut -d' ' -f1-2)
        [ -n "$last_bot" ] && print_status "Bot last activity: $last_bot" "info"

        # Check for recent errors
        local recent_errors=$(tail -50 "$BOT_LOG" 2>/dev/null | grep -c "ERROR\|dispatch_failed")
        if [ "$recent_errors" -gt 0 ]; then
            print_status "Recent errors detected: $recent_errors" "warning"
        fi
    fi

    echo ""
    echo -e "${PURPLE}📁 Log Files${NC}"
    echo "----------------------------------------"

    local logs=(
        "$KEEPER_LOG:Keeper Activity"
        "$BOT_LOG:Bot Activity"
        "$KEEPER_OUTPUT:Keeper Output"
        "$KEEPER_ERROR:Keeper Errors"
    )

    for log_entry in "${logs[@]}"; do
        IFS=':' read -ra parts <<< "$log_entry"
        local log_file="${parts[0]}"
        local log_desc="${parts[1]}"

        if [ -f "$log_file" ]; then
            local size=$(du -h "$log_file" | cut -f1)
            local lines=$(wc -l < "$log_file")
            print_status "$log_desc: $log_file ($size, $lines lines)" "info"
        else
            print_status "$log_desc: Not found" "warning"
        fi
    done
}

view_logs() {
    local log_type="$1"

    case "$log_type" in
        "keeper"|"k")
            echo -e "${PURPLE}📜 Bot Keeper Logs (last 50 lines)${NC}"
            echo "----------------------------------------"
            if [ -f "$KEEPER_LOG" ]; then
                tail -50 "$KEEPER_LOG"
            else
                print_status "Keeper log file not found" "warning"
            fi
            ;;
        "bot"|"b")
            echo -e "${PURPLE}📜 Slack Bot Logs (last 50 lines)${NC}"
            echo "----------------------------------------"
            if [ -f "$BOT_LOG" ]; then
                tail -50 "$BOT_LOG"
            else
                print_status "Bot log file not found" "warning"
            fi
            ;;
        "error"|"e")
            echo -e "${PURPLE}📜 Error Logs${NC}"
            echo "----------------------------------------"
            if [ -f "$KEEPER_ERROR" ]; then
                echo "Keeper Errors:"
                tail -20 "$KEEPER_ERROR"
            fi
            echo ""
            if [ -f "$BOT_LOG" ]; then
                echo "Bot Errors (recent):"
                grep -i "error\|failed\|exception" "$BOT_LOG" | tail -10
            fi
            ;;
        *)
            echo -e "${PURPLE}📜 All Recent Logs${NC}"
            echo "----------------------------------------"
            echo "=== Keeper Activity ==="
            [ -f "$KEEPER_LOG" ] && tail -20 "$KEEPER_LOG" || echo "No keeper log"
            echo ""
            echo "=== Bot Activity ==="
            [ -f "$BOT_LOG" ] && tail -20 "$BOT_LOG" || echo "No bot log"
            ;;
    esac
}

follow_logs() {
    echo -e "${PURPLE}📊 Following Live Logs (Ctrl+C to stop)${NC}"
    echo "----------------------------------------"

    local log_files=()
    [ -f "$KEEPER_LOG" ] && log_files+=("$KEEPER_LOG")
    [ -f "$BOT_LOG" ] && log_files+=("$BOT_LOG")

    if [ ${#log_files[@]} -gt 0 ]; then
        tail -f "${log_files[@]}"
    else
        print_status "No log files found to follow" "warning"
        print_status "Start the bot first with: $0 start" "info"
    fi
}

run_direct() {
    echo -e "${PURPLE}🔧 Running BulletProof JobBot directly (for testing)${NC}"
    echo "----------------------------------------"

    if ! check_prerequisites; then
        return 1
    fi

    print_status "Starting keeper directly..." "info"
    print_status "Press Ctrl+C to stop" "info"
    echo ""

    exec "$PYTHON_PATH" "$KEEPER_SCRIPT"
}

show_help() {
    print_header
    echo ""
    echo -e "${PURPLE}Available Commands:${NC}"
    echo "----------------------------------------"
    echo "  start       Start the BulletProof JobBot service"
    echo "  stop        Stop the BulletProof JobBot service"
    echo "  restart     Restart the BulletProof JobBot service"
    echo "  status      Show detailed system status"
    echo "  install     Install the background service"
    echo "  uninstall   Remove the background service"
    echo "  logs [type] View logs (keeper|bot|error|all)"
    echo "  follow      Follow live logs"
    echo "  direct      Run directly (for testing)"
    echo "  check       Check prerequisites"
    echo "  help        Show this help"
    echo ""
    echo -e "${PURPLE}Examples:${NC}"
    echo "  $0 start                # Start the bulletproof bot"
    echo "  $0 status               # Check if everything is running"
    echo "  $0 logs bot             # View bot logs"
    echo "  $0 follow               # Watch live activity"
    echo "  $0 direct               # Run in foreground for testing"
    echo ""
    echo -e "${PURPLE}About BulletProof Mode:${NC}"
    echo "• Automatically restarts if the bot crashes"
    echo "• Monitors bot health continuously"
    echo "• Handles network issues gracefully"
    echo "• Prevents dispatch_failed errors"
    echo "• Runs as a background service"
    echo "• Starts automatically on system boot"
}

# Main command processing
case "${1:-help}" in
    start)
        check_prerequisites && start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        check_status
        ;;
    install)
        check_prerequisites && install_service
        ;;
    uninstall)
        uninstall_service
        ;;
    logs)
        view_logs "$2"
        ;;
    follow)
        follow_logs
        ;;
    direct)
        run_direct
        ;;
    check)
        check_prerequisites
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

exit $?
