#!/bin/bash

# Simple Bot Monitor - Ensures JobBot stays running 24/7
# This script checks if the bot is running and restarts it if needed
# Run this via cron every minute for bulletproof reliability

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BOT_MANAGER="$SCRIPT_DIR/simple_bot_manager.sh"
MONITOR_LOG="$SCRIPT_DIR/monitor.log"
MAX_LOG_LINES=1000

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$MONITOR_LOG"
}

# Function to trim log file
trim_log() {
    if [ -f "$MONITOR_LOG" ] && [ $(wc -l < "$MONITOR_LOG") -gt $MAX_LOG_LINES ]; then
        tail -n $((MAX_LOG_LINES/2)) "$MONITOR_LOG" > "$MONITOR_LOG.tmp"
        mv "$MONITOR_LOG.tmp" "$MONITOR_LOG"
    fi
}

# Check if bot manager exists
if [ ! -f "$BOT_MANAGER" ]; then
    log_message "ERROR: Bot manager not found at $BOT_MANAGER"
    exit 1
fi

# Make sure bot manager is executable
chmod +x "$BOT_MANAGER"

# Check if bot is running
if "$BOT_MANAGER" status > /dev/null 2>&1; then
    # Bot is running - check if it's healthy
    RECENT_ACTIVITY=$(grep "$(date '+%Y-%m-%d %H:%M')" "$SCRIPT_DIR/slack_bot_working.log" 2>/dev/null | wc -l)

    if [ "$RECENT_ACTIVITY" -eq 0 ]; then
        # No recent activity in last minute - check last 5 minutes
        FIVE_MIN_AGO=$(date -v-5M '+%Y-%m-%d %H:%M' 2>/dev/null || date -d '5 minutes ago' '+%Y-%m-%d %H:%M' 2>/dev/null)
        if [ -n "$FIVE_MIN_AGO" ]; then
            RECENT_ACTIVITY=$(grep -c "$FIVE_MIN_AGO" "$SCRIPT_DIR/slack_bot_working.log" 2>/dev/null)

            if [ "$RECENT_ACTIVITY" -eq 0 ]; then
                log_message "WARNING: No bot activity in last 5 minutes, restarting..."
                "$BOT_MANAGER" restart >> "$MONITOR_LOG" 2>&1
                log_message "Bot restart completed"
            fi
        fi
    fi
else
    # Bot is not running - start it
    log_message "Bot not running - starting now..."
    "$BOT_MANAGER" start >> "$MONITOR_LOG" 2>&1

    if [ $? -eq 0 ]; then
        log_message "Bot started successfully"
    else
        log_message "ERROR: Failed to start bot"
    fi
fi

# Check for dispatch_failed errors in recent logs
DISPATCH_ERRORS=$(tail -100 "$SCRIPT_DIR/slack_bot_working.log" 2>/dev/null | grep -c "dispatch_failed\|ClientConnectorError" || echo "0")

if [ "$DISPATCH_ERRORS" -gt 5 ]; then
    log_message "WARNING: Multiple dispatch errors detected ($DISPATCH_ERRORS), restarting bot..."
    "$BOT_MANAGER" restart >> "$MONITOR_LOG" 2>&1
    log_message "Bot restart due to dispatch errors completed"
fi

# Trim log file to prevent it from growing too large
trim_log

# Exit successfully
exit 0
