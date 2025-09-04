#!/bin/bash

# JobBot Slack Service Manager
# Manages the JobBot Slack integration as a background service on macOS

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVICE_NAME="com.jobbot.slackbot"
PLIST_FILE="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"
BOT_SCRIPT="$SCRIPT_DIR/run_slack_bot.py"
LOG_FILE="$SCRIPT_DIR/slack_bot_runtime.log"
ERROR_LOG="$SCRIPT_DIR/slack_bot_error.log"

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}This script is designed for macOS only.${NC}"
    exit 1
fi

# Function to check if service is installed
is_installed() {
    [ -f "$PLIST_FILE" ]
}

# Function to check if service is running
is_running() {
    launchctl list | grep -q "$SERVICE_NAME"
}

# Function to install the service
install_service() {
    echo -e "${BLUE}Installing JobBot Slack service...${NC}"

    # Check if Python script exists
    if [ ! -f "$BOT_SCRIPT" ]; then
        echo -e "${RED}Bot script not found at: $BOT_SCRIPT${NC}"
        echo -e "${YELLOW}Creating bot script...${NC}"
        # The script should already exist from previous creation
        exit 1
    fi

    # Check for .env file
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        echo -e "${RED}Warning: .env file not found!${NC}"
        echo -e "${YELLOW}Please create a .env file with your Slack tokens before starting the bot.${NC}"
    fi

    # Create LaunchAgents directory if it doesn't exist
    mkdir -p "$HOME/Library/LaunchAgents"

    # Create the plist file
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${SERVICE_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${SCRIPT_DIR}/venv/bin/python3</string>
        <string>${BOT_SCRIPT}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>

    <key>StandardOutPath</key>
    <string>${LOG_FILE}</string>

    <key>StandardErrorPath</key>
    <string>${ERROR_LOG}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>

    <key>ThrottleInterval</key>
    <integer>30</integer>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
        <key>PYTHONPATH</key>
        <string>${SCRIPT_DIR}:${SCRIPT_DIR}/src</string>
    </dict>
</dict>
</plist>
EOF

    # Load the service
    launchctl load "$PLIST_FILE" 2>/dev/null

    echo -e "${GREEN}Service installed successfully!${NC}"
    echo -e "${BLUE}The bot will start automatically on login.${NC}"
}

# Function to uninstall the service
uninstall_service() {
    echo -e "${BLUE}Uninstalling JobBot Slack service...${NC}"

    if is_running; then
        stop_service
    fi

    if is_installed; then
        launchctl unload "$PLIST_FILE" 2>/dev/null
        rm -f "$PLIST_FILE"
        echo -e "${GREEN}Service uninstalled successfully!${NC}"
    else
        echo -e "${YELLOW}Service is not installed.${NC}"
    fi
}

# Function to start the service
start_service() {
    echo -e "${BLUE}Starting JobBot Slack service...${NC}"

    if ! is_installed; then
        echo -e "${YELLOW}Service not installed. Installing now...${NC}"
        install_service
    fi

    if is_running; then
        echo -e "${YELLOW}Service is already running.${NC}"
    else
        launchctl load "$PLIST_FILE" 2>/dev/null
        launchctl start "$SERVICE_NAME"
        sleep 2

        if is_running; then
            echo -e "${GREEN}Service started successfully!${NC}"
        else
            echo -e "${RED}Failed to start service. Check logs for details.${NC}"
            tail -n 20 "$ERROR_LOG" 2>/dev/null
        fi
    fi
}

# Function to stop the service
stop_service() {
    echo -e "${BLUE}Stopping JobBot Slack service...${NC}"

    if is_running; then
        launchctl stop "$SERVICE_NAME"
        launchctl unload "$PLIST_FILE" 2>/dev/null
        echo -e "${GREEN}Service stopped successfully!${NC}"
    else
        echo -e "${YELLOW}Service is not running.${NC}"
    fi
}

# Function to restart the service
restart_service() {
    echo -e "${BLUE}Restarting JobBot Slack service...${NC}"
    stop_service
    sleep 2
    start_service
}

# Function to check service status
check_status() {
    echo -e "${BLUE}JobBot Slack Service Status${NC}"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if is_installed; then
        echo -e "Installation: ${GREEN}✓ Installed${NC}"
        echo -e "Location: $PLIST_FILE"
    else
        echo -e "Installation: ${RED}✗ Not installed${NC}"
    fi

    if is_running; then
        echo -e "Status: ${GREEN}● Running${NC}"

        # Get PID
        PID=$(launchctl list | grep "$SERVICE_NAME" | awk '{print $1}')
        if [ "$PID" != "-" ]; then
            echo -e "PID: $PID"

            # Get memory usage
            if command -v ps &> /dev/null; then
                MEM=$(ps -o rss= -p "$PID" 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')
                [ -n "$MEM" ] && echo -e "Memory: $MEM"
            fi
        fi
    else
        echo -e "Status: ${RED}○ Stopped${NC}"
    fi

    # Check log files
    echo -e "\nLog Files:"
    if [ -f "$LOG_FILE" ]; then
        LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
        LOG_LINES=$(wc -l < "$LOG_FILE")
        echo -e "  Main log: $LOG_FILE (${LOG_SIZE}, ${LOG_LINES} lines)"
    fi

    if [ -f "$ERROR_LOG" ]; then
        ERROR_SIZE=$(du -h "$ERROR_LOG" | cut -f1)
        ERROR_LINES=$(wc -l < "$ERROR_LOG")
        echo -e "  Error log: $ERROR_LOG (${ERROR_SIZE}, ${ERROR_LINES} lines)"
    fi

    # Check last activity
    if [ -f "$LOG_FILE" ]; then
        LAST_LOG=$(tail -1 "$LOG_FILE" 2>/dev/null | cut -d' ' -f1-2)
        [ -n "$LAST_LOG" ] && echo -e "\nLast activity: $LAST_LOG"
    fi
}

# Function to view logs
view_logs() {
    echo -e "${BLUE}JobBot Slack Logs (last 50 lines)${NC}"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [ -f "$LOG_FILE" ]; then
        tail -50 "$LOG_FILE"
    else
        echo -e "${YELLOW}No log file found.${NC}"
    fi

    if [ -f "$ERROR_LOG" ] && [ -s "$ERROR_LOG" ]; then
        echo -e "\n${RED}Recent Errors:${NC}"
        tail -10 "$ERROR_LOG"
    fi
}

# Function to follow logs in real-time
follow_logs() {
    echo -e "${BLUE}Following JobBot Slack logs (Ctrl+C to stop)...${NC}"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}No log file found. Waiting for bot to start...${NC}"
        while [ ! -f "$LOG_FILE" ]; do
            sleep 1
        done
        tail -f "$LOG_FILE"
    fi
}

# Function to test the bot
test_bot() {
    echo -e "${BLUE}Testing JobBot configuration...${NC}"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Check Python
    echo -n "Python 3: "
    PYTHON_BIN="${SCRIPT_DIR}/venv/bin/python3"
    if [ -f "$PYTHON_BIN" ]; then
        PYTHON_VERSION=$("$PYTHON_BIN" --version 2>&1)
        echo -e "${GREEN}✓${NC} ($PYTHON_VERSION from venv)"
    elif command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        echo -e "${YELLOW}✓${NC} ($PYTHON_VERSION - system python, venv recommended)"
    else
        echo -e "${RED}✗ Not found${NC}"
        exit 1
    fi

    # Check .env file
    echo -n ".env file: "
    if [ -f "$SCRIPT_DIR/.env" ]; then
        echo -e "${GREEN}✓${NC}"

        # Check for required variables
        source "$SCRIPT_DIR/.env"

        echo -n "SLACK_BOT_TOKEN: "
        [ -n "$SLACK_BOT_TOKEN" ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗ Missing${NC}"

        echo -n "SLACK_APP_TOKEN: "
        [ -n "$SLACK_APP_TOKEN" ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗ Missing${NC}"

        echo -n "OPENAI_API_KEY: "
        [ -n "$OPENAI_API_KEY" ] && echo -e "${GREEN}✓ (AI enabled)${NC}" || echo -e "${YELLOW}○ (AI disabled)${NC}"

        echo -n "NOTION_TOKEN: "
        [ -n "$NOTION_TOKEN" ] && echo -e "${GREEN}✓ (Notion enabled)${NC}" || echo -e "${YELLOW}○ (Notion disabled)${NC}"
    else
        echo -e "${RED}✗ Not found${NC}"
        echo -e "${YELLOW}Please create .env file with your credentials${NC}"
    fi

    # Try to import required packages
    echo -e "\nChecking Python packages:"
    PYTHON_CHECK="${PYTHON_BIN:-python3}"
    "$PYTHON_CHECK" -c "import slack_bolt; print('  slack_bolt: ✓')" 2>/dev/null || echo -e "  slack_bolt: ${RED}✗ Not installed${NC}"
    "$PYTHON_CHECK" -c "import openai; print('  openai: ✓')" 2>/dev/null || echo -e "  openai: ${YELLOW}○ Not installed (optional)${NC}"
    "$PYTHON_CHECK" -c "import notion_client; print('  notion_client: ✓')" 2>/dev/null || echo -e "  notion_client: ${YELLOW}○ Not installed (optional)${NC}"
    "$PYTHON_CHECK" -c "import requests; print('  requests: ✓')" 2>/dev/null || echo -e "  requests: ${RED}✗ Not installed${NC}"
    "$PYTHON_CHECK" -c "import bs4; print('  beautifulsoup4: ✓')" 2>/dev/null || echo -e "  beautifulsoup4: ${RED}✗ Not installed${NC}"
    "$PYTHON_CHECK" -c "import dotenv; print('  python-dotenv: ✓')" 2>/dev/null || echo -e "  python-dotenv: ${RED}✗ Not installed${NC}"
}

# Function to display help
show_help() {
    echo -e "${BLUE}JobBot Slack Service Manager${NC}"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "\nUsage: $0 [command]"
    echo -e "\nCommands:"
    echo -e "  ${GREEN}start${NC}     Start the bot service"
    echo -e "  ${GREEN}stop${NC}      Stop the bot service"
    echo -e "  ${GREEN}restart${NC}   Restart the bot service"
    echo -e "  ${GREEN}status${NC}    Check service status"
    echo -e "  ${GREEN}install${NC}   Install as a background service"
    echo -e "  ${GREEN}uninstall${NC} Remove the background service"
    echo -e "  ${GREEN}logs${NC}      View recent logs"
    echo -e "  ${GREEN}follow${NC}    Follow logs in real-time"
    echo -e "  ${GREEN}test${NC}      Test bot configuration"
    echo -e "  ${GREEN}help${NC}      Show this help message"
    echo -e "\nExamples:"
    echo -e "  $0 start    # Start the bot and keep it running"
    echo -e "  $0 status   # Check if the bot is running"
    echo -e "  $0 follow   # Watch logs in real-time"
}

# Main script logic
case "$1" in
    start)
        start_service
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
        install_service
        ;;
    uninstall)
        uninstall_service
        ;;
    logs)
        view_logs
        ;;
    follow)
        follow_logs
        ;;
    test)
        test_bot
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        if [ -n "$1" ]; then
            echo -e "${RED}Unknown command: $1${NC}\n"
        fi
        show_help
        exit 1
        ;;
esac

exit 0
