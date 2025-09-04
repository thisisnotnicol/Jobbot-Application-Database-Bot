#!/bin/bash

# Simple Bot Manager for JobBot Slack Integration
# Manages the simple working Slack bot without complexity

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BOT_SCRIPT="$SCRIPT_DIR/slack_bot_working.py"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python3"
PID_FILE="$SCRIPT_DIR/simple_bot.pid"
LOG_FILE="$SCRIPT_DIR/slack_bot_working.log"

# Check if bot is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    return 1
}

# Start the bot
start_bot() {
    echo -e "${BLUE}Starting JobBot Slack integration...${NC}"

    if is_running; then
        echo -e "${YELLOW}Bot is already running${NC}"
        return 0
    fi

    # Check if Python script exists
    if [ ! -f "$BOT_SCRIPT" ]; then
        echo -e "${RED}Bot script not found: $BOT_SCRIPT${NC}"
        return 1
    fi

    # Check if Python exists
    if [ ! -f "$PYTHON_PATH" ]; then
        echo -e "${RED}Python not found: $PYTHON_PATH${NC}"
        return 1
    fi

    # Start bot in background
    nohup "$PYTHON_PATH" "$BOT_SCRIPT" > "$LOG_FILE" 2>&1 &
    BOT_PID=$!
    echo $BOT_PID > "$PID_FILE"

    # Wait a moment and check if it started
    sleep 3

    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Bot started successfully (PID: $BOT_PID)${NC}"
        return 0
    else
        echo -e "${RED}❌ Bot failed to start${NC}"
        rm -f "$PID_FILE"
        echo -e "${YELLOW}Last 10 lines of log:${NC}"
        tail -10 "$LOG_FILE" 2>/dev/null
        return 1
    fi
}

# Stop the bot
stop_bot() {
    echo -e "${BLUE}Stopping JobBot...${NC}"

    if ! is_running; then
        echo -e "${YELLOW}Bot is not running${NC}"
        return 0
    fi

    PID=$(cat "$PID_FILE")
    kill $PID

    # Wait for graceful shutdown
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done

    # Force kill if still running
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${YELLOW}Force killing bot...${NC}"
        kill -9 $PID
    fi

    rm -f "$PID_FILE"
    echo -e "${GREEN}✅ Bot stopped${NC}"
}

# Restart the bot
restart_bot() {
    echo -e "${BLUE}Restarting JobBot...${NC}"
    stop_bot
    sleep 2
    start_bot
}

# Check bot status
check_status() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo -e "${GREEN}✅ Bot is running (PID: $PID)${NC}"

        # Check log activity
        if [ -f "$LOG_FILE" ]; then
            LAST_LOG=$(tail -1 "$LOG_FILE" 2>/dev/null)
            if [ -n "$LAST_LOG" ]; then
                echo -e "${BLUE}Last activity: $(echo "$LAST_LOG" | cut -d' ' -f1-2)${NC}"
            fi
        fi
    else
        echo -e "${RED}❌ Bot is not running${NC}"
    fi
}

# View logs
view_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${BLUE}Recent bot activity (last 20 lines):${NC}"
        echo "----------------------------------------"
        tail -20 "$LOG_FILE"
    else
        echo -e "${YELLOW}No log file found${NC}"
    fi
}

# Follow logs in real-time
follow_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${BLUE}Following bot logs (Ctrl+C to stop):${NC}"
        echo "----------------------------------------"
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}No log file found. Starting bot first...${NC}"
        start_bot
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        fi
    fi
}

# Show help
show_help() {
    echo -e "${BLUE}JobBot Simple Manager${NC}"
    echo "===================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start    Start the Slack bot"
    echo "  stop     Stop the Slack bot"
    echo "  restart  Restart the Slack bot"
    echo "  status   Check bot status"
    echo "  logs     View recent logs"
    echo "  follow   Follow logs in real-time"
    echo "  help     Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 start     # Start the bot"
    echo "  $0 status    # Check if running"
    echo "  $0 follow    # Watch logs live"
}

# Main script logic
case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        check_status
        ;;
    logs)
        view_logs
        ;;
    follow)
        follow_logs
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

exit 0
