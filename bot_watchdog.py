#!/usr/bin/env python3
"""
JobBot Watchdog - Bulletproof Safety Net
Ensures the Slack bot stays running 24/7 with multiple safety mechanisms
"""

import os
import sys
import time
import subprocess
import psutil
import logging
import signal
import threading
from datetime import datetime, timedelta
from pathlib import Path
import requests
import json

# Configure logging
LOG_FILE = "bot_watchdog.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SlackBotWatchdog:
    """Robust watchdog for Slack bot with multiple safety mechanisms"""

    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.bot_script = self.script_dir / "slack_bot_working.py"
        self.python_path = self.script_dir / "venv" / "bin" / "python3"

        # Watchdog settings
        self.check_interval = 10  # Check every 10 seconds
        self.restart_cooldown = 30  # Wait 30 seconds before restart
        self.max_restarts_per_hour = 12  # Max restarts per hour
        self.health_check_timeout = 5  # Seconds

        # State tracking
        self.bot_process = None
        self.restart_history = []
        self.last_health_check = None
        self.consecutive_failures = 0
        self.running = True

        # Health check thread
        self.health_thread = None

    def is_bot_running(self):
        """Check if bot process is running and healthy"""
        try:
            # Check if process exists
            if self.bot_process is None:
                return False

            # Check if process is still alive
            if self.bot_process.poll() is not None:
                logger.warning(f"Bot process {self.bot_process.pid} has terminated")
                return False

            # Check if PID actually exists in system
            try:
                psutil.Process(self.bot_process.pid)
            except psutil.NoSuchProcess:
                logger.warning(f"Bot process {self.bot_process.pid} no longer exists in system")
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking bot status: {e}")
            return False

    def check_slack_connection(self):
        """Verify Slack connection is working"""
        try:
            # Look for recent activity in logs
            log_file = self.script_dir / "slack_bot_working.log"
            if log_file.exists():
                # Check if log has been written to recently (last 5 minutes)
                stat = log_file.stat()
                last_modified = datetime.fromtimestamp(stat.st_mtime)
                if datetime.now() - last_modified > timedelta(minutes=5):
                    logger.warning("Bot log hasn't been updated in 5+ minutes")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking Slack connection: {e}")
            return False

    def start_bot(self):
        """Start the Slack bot process"""
        try:
            logger.info("Starting Slack bot...")

            # Kill any existing bot processes
            self.kill_existing_bots()

            # Start new process
            cmd = [str(self.python_path), str(self.bot_script)]

            self.bot_process = subprocess.Popen(
                cmd,
                cwd=str(self.script_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )

            logger.info(f"Bot started with PID: {self.bot_process.pid}")

            # Give it time to initialize
            time.sleep(5)

            # Check if it started successfully
            if self.bot_process.poll() is None:
                logger.info("Bot started successfully")
                self.consecutive_failures = 0
                return True
            else:
                stdout, stderr = self.bot_process.communicate()
                logger.error(f"Bot failed to start. Stdout: {stdout.decode()}, Stderr: {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            return False

    def kill_existing_bots(self):
        """Kill any existing bot processes"""
        try:
            # Find and kill processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and 'slack_bot_working.py' in ' '.join(cmdline):
                        logger.info(f"Killing existing bot process: {proc.pid}")
                        proc.kill()
                        proc.wait(timeout=5)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    pass

        except Exception as e:
            logger.error(f"Error killing existing processes: {e}")

    def restart_bot(self):
        """Restart the bot with safety checks"""
        try:
            # Check restart rate limiting
            now = datetime.now()
            recent_restarts = [r for r in self.restart_history if now - r < timedelta(hours=1)]

            if len(recent_restarts) >= self.max_restarts_per_hour:
                logger.error(f"Too many restarts ({len(recent_restarts)}) in the last hour. Cooling down...")
                time.sleep(300)  # Wait 5 minutes
                return False

            # Add to restart history
            self.restart_history.append(now)

            # Keep only recent restarts
            self.restart_history = [r for r in self.restart_history if now - r < timedelta(hours=1)]

            logger.info(f"Restarting bot (restart #{len(recent_restarts) + 1} this hour)")

            # Stop current process
            if self.bot_process:
                try:
                    os.killpg(os.getpgid(self.bot_process.pid), signal.SIGTERM)
                    self.bot_process.wait(timeout=10)
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    try:
                        os.killpg(os.getpgid(self.bot_process.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                self.bot_process = None

            # Wait before restart
            logger.info(f"Waiting {self.restart_cooldown} seconds before restart...")
            time.sleep(self.restart_cooldown)

            # Start bot
            return self.start_bot()

        except Exception as e:
            logger.error(f"Error during restart: {e}")
            return False

    def health_check_loop(self):
        """Continuous health checking in separate thread"""
        while self.running:
            try:
                # Check process health
                if not self.is_bot_running():
                    logger.warning("Bot process check failed")
                    self.consecutive_failures += 1
                elif not self.check_slack_connection():
                    logger.warning("Slack connection check failed")
                    self.consecutive_failures += 1
                else:
                    # All checks passed
                    if self.consecutive_failures > 0:
                        logger.info("Health checks now passing")
                    self.consecutive_failures = 0

                self.last_health_check = datetime.now()

                # Sleep between checks
                time.sleep(self.health_check_timeout)

            except Exception as e:
                logger.error(f"Error in health check: {e}")
                time.sleep(5)

    def run(self):
        """Main watchdog loop"""
        logger.info("Starting JobBot Watchdog")
        logger.info(f"Bot script: {self.bot_script}")
        logger.info(f"Python path: {self.python_path}")
        logger.info(f"Check interval: {self.check_interval}s")

        # Start health check thread
        self.health_thread = threading.Thread(target=self.health_check_loop, daemon=True)
        self.health_thread.start()

        # Initial bot start
        if not self.start_bot():
            logger.error("Failed to start bot initially")
            return 1

        logger.info("Watchdog active - monitoring bot health")

        try:
            while self.running:
                # Main monitoring loop
                if self.consecutive_failures >= 3:
                    logger.error(f"Bot has failed {self.consecutive_failures} consecutive health checks")

                    if not self.restart_bot():
                        logger.error("Failed to restart bot")
                        # Exponential backoff for failures
                        backoff = min(300, 30 * (2 ** min(self.consecutive_failures - 3, 5)))
                        logger.info(f"Backing off for {backoff} seconds")
                        time.sleep(backoff)

                # Sleep between main loop iterations
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
        finally:
            self.shutdown()

        return 0

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down watchdog...")
        self.running = False

        # Stop bot process
        if self.bot_process:
            try:
                logger.info(f"Terminating bot process {self.bot_process.pid}")
                os.killpg(os.getpgid(self.bot_process.pid), signal.SIGTERM)
                self.bot_process.wait(timeout=10)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    os.killpg(os.getpgid(self.bot_process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass

        logger.info("Watchdog shutdown complete")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    global watchdog
    if watchdog:
        watchdog.shutdown()
    sys.exit(0)

def main():
    """Main entry point"""
    global watchdog

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run watchdog
    watchdog = SlackBotWatchdog()

    try:
        return watchdog.run()
    except Exception as e:
        logger.error(f"Fatal watchdog error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
