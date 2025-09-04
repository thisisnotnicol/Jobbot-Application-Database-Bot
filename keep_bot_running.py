#!/usr/bin/env python3
"""
Bulletproof Bot Keeper - Ensures JobBot Slack Integration Never Dies
Uses the proven working slack_bot_working.py with comprehensive monitoring
"""

import os
import sys
import time
import signal
import subprocess
import psutil
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
LOG_FILE = "bot_keeper.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotKeeper:
    """Bulletproof system to keep the Slack bot running 24/7"""

    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.bot_script = self.script_dir / "slack_bot_working.py"
        self.python_path = self.script_dir / "venv" / "bin" / "python3"
        self.bot_log = self.script_dir / "slack_bot_working.log"
        self.pid_file = self.script_dir / "bot_keeper.pid"

        # Settings
        self.check_interval = 30  # Check every 30 seconds
        self.restart_cooldown = 60  # Wait 1 minute between restarts
        self.max_restarts_per_hour = 10
        self.log_activity_timeout = 300  # 5 minutes without log activity = restart

        # State
        self.bot_process = None
        self.restart_history = []
        self.running = True
        self.startup_time = datetime.now()

    def check_bot_health(self):
        """Comprehensive bot health check"""

        # Check 1: Process exists and is running
        if not self.bot_process or self.bot_process.poll() is not None:
            logger.warning("Bot process is not running or has died")
            return False

        # Check 2: Process PID exists in system
        try:
            psutil.Process(self.bot_process.pid)
        except psutil.NoSuchProcess:
            logger.warning(f"Bot PID {self.bot_process.pid} no longer exists")
            return False

        # Check 3: Log file activity (bot should write logs regularly)
        if self.bot_log.exists():
            try:
                stat = self.bot_log.stat()
                last_modified = datetime.fromtimestamp(stat.st_mtime)
                time_since_log = datetime.now() - last_modified

                if time_since_log > timedelta(seconds=self.log_activity_timeout):
                    logger.warning(f"No log activity for {time_since_log.total_seconds()} seconds")
                    return False
            except Exception as e:
                logger.warning(f"Could not check log activity: {e}")

        # Check 4: Look for error patterns in recent logs
        try:
            if self.bot_log.exists():
                with open(self.bot_log, 'r') as f:
                    recent_logs = f.read()[-5000:]  # Last 5KB

                    error_patterns = [
                        'dispatch_failed',
                        'ClientConnectorError',
                        'Connection refused',
                        'Network is unreachable',
                        'SSL: CERTIFICATE_VERIFY_FAILED'
                    ]

                    for pattern in error_patterns:
                        if pattern in recent_logs:
                            # Check if error is recent (last 2 minutes)
                            lines = recent_logs.split('\n')
                            for line in reversed(lines[-20:]):  # Check last 20 lines
                                if pattern in line and self._is_recent_log_line(line):
                                    logger.warning(f"Recent error detected: {pattern}")
                                    return False
        except Exception as e:
            logger.warning(f"Error checking log patterns: {e}")

        return True

    def _is_recent_log_line(self, line):
        """Check if log line is from the last 2 minutes"""
        try:
            # Extract timestamp from log line (format: YYYY-MM-DD HH:MM:SS,mmm)
            timestamp_str = line.split('[')[0].strip()
            log_time = datetime.strptime(timestamp_str.split(',')[0], '%Y-%m-%d %H:%M:%S')
            return datetime.now() - log_time < timedelta(minutes=2)
        except:
            return False

    def start_bot(self):
        """Start the Slack bot process"""
        try:
            logger.info("Starting Slack bot...")

            # Kill any existing bot processes first
            self._kill_existing_bots()

            # Start the bot
            cmd = [str(self.python_path), str(self.bot_script)]

            self.bot_process = subprocess.Popen(
                cmd,
                cwd=str(self.script_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group for clean killing
            )

            logger.info(f"Bot started with PID: {self.bot_process.pid}")

            # Wait a moment for startup
            time.sleep(10)

            # Check if it started successfully
            if self.bot_process.poll() is None:
                logger.info("✅ Bot started successfully and is running")
                return True
            else:
                stdout, stderr = self.bot_process.communicate()
                logger.error(f"❌ Bot failed to start")
                logger.error(f"Stdout: {stdout.decode()[:500]}")
                logger.error(f"Stderr: {stderr.decode()[:500]}")
                return False

        except Exception as e:
            logger.error(f"Exception starting bot: {e}")
            return False

    def _kill_existing_bots(self):
        """Kill any existing bot processes"""
        try:
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('slack_bot_working.py' in str(arg) for arg in cmdline):
                        logger.info(f"Killing existing bot process: {proc.info['pid']}")
                        proc.kill()
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            pass
                        killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if killed_count > 0:
                logger.info(f"Killed {killed_count} existing bot processes")
                time.sleep(2)  # Wait for cleanup

        except Exception as e:
            logger.error(f"Error killing existing processes: {e}")

    def restart_bot(self):
        """Restart bot with rate limiting"""
        try:
            now = datetime.now()

            # Clean old restart history
            self.restart_history = [r for r in self.restart_history if now - r < timedelta(hours=1)]

            # Check restart rate limit
            if len(self.restart_history) >= self.max_restarts_per_hour:
                logger.error(f"Too many restarts ({len(self.restart_history)}) in last hour")
                logger.info("Cooling down for 10 minutes...")
                time.sleep(600)  # 10 minute cooldown
                self.restart_history = []  # Reset after cooldown

            # Add this restart to history
            self.restart_history.append(now)

            logger.info(f"Restarting bot (restart #{len(self.restart_history)} this hour)")

            # Stop current process
            if self.bot_process:
                try:
                    os.killpg(os.getpgid(self.bot_process.pid), signal.SIGTERM)
                    self.bot_process.wait(timeout=10)
                except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
                    try:
                        os.killpg(os.getpgid(self.bot_process.pid), signal.SIGKILL)
                    except (ProcessLookupError, OSError):
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

    def save_pid(self):
        """Save our PID for external monitoring"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logger.warning(f"Could not save PID file: {e}")

    def cleanup_pid(self):
        """Remove PID file"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception as e:
            logger.warning(f"Could not remove PID file: {e}")

    def run(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting BulletProof JobBot Keeper")
        logger.info(f"Bot script: {self.bot_script}")
        logger.info(f"Python: {self.python_path}")
        logger.info(f"Check interval: {self.check_interval}s")
        logger.info(f"Restart cooldown: {self.restart_cooldown}s")

        # Save our PID
        self.save_pid()

        # Initial bot start
        if not self.start_bot():
            logger.error("❌ Failed to start bot initially")
            return 1

        logger.info("👀 Bot Keeper is now monitoring...")
        logger.info("The bot will be automatically restarted if any issues are detected")

        consecutive_failures = 0

        try:
            while self.running:
                # Health check
                if self.check_bot_health():
                    if consecutive_failures > 0:
                        logger.info(f"✅ Bot health restored after {consecutive_failures} failures")
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    logger.warning(f"⚠️ Bot health check failed ({consecutive_failures} consecutive failures)")

                    # Restart after 2 consecutive failures
                    if consecutive_failures >= 2:
                        logger.error("💀 Bot is unhealthy, restarting...")

                        if self.restart_bot():
                            consecutive_failures = 0
                        else:
                            logger.error("❌ Failed to restart bot")
                            # Exponential backoff on restart failures
                            backoff = min(600, 60 * (2 ** min(consecutive_failures - 2, 4)))
                            logger.info(f"Backing off for {backoff} seconds")
                            time.sleep(backoff)

                # Log periodic status
                uptime = datetime.now() - self.startup_time
                if uptime.total_seconds() % 3600 < self.check_interval:  # Every hour
                    logger.info(f"📊 Status: Bot running for {uptime}, {len(self.restart_history)} restarts this hour")

                # Sleep until next check
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
        except Exception as e:
            logger.error(f"💥 Keeper error: {e}")
        finally:
            self.shutdown()

        return 0

    def shutdown(self):
        """Clean shutdown"""
        logger.info("🔄 Shutting down Bot Keeper...")
        self.running = False

        # Stop bot process
        if self.bot_process:
            try:
                logger.info(f"Terminating bot process {self.bot_process.pid}")
                os.killpg(os.getpgid(self.bot_process.pid), signal.SIGTERM)
                self.bot_process.wait(timeout=15)
            except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
                try:
                    os.killpg(os.getpgid(self.bot_process.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass

        # Cleanup
        self.cleanup_pid()
        logger.info("✅ Bot Keeper shutdown complete")

# Signal handlers
keeper_instance = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"📨 Received signal {signum}")
    global keeper_instance
    if keeper_instance:
        keeper_instance.shutdown()
    sys.exit(0)

def main():
    """Main entry point"""
    global keeper_instance

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Check environment
    script_dir = Path(__file__).parent
    bot_script = script_dir / "slack_bot_working.py"
    python_path = script_dir / "venv" / "bin" / "python3"

    if not bot_script.exists():
        logger.error(f"❌ Bot script not found: {bot_script}")
        return 1

    if not python_path.exists():
        logger.error(f"❌ Python venv not found: {python_path}")
        return 1

    # Check required environment variables
    required_vars = ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN']
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
        return 1

    # Create and run keeper
    keeper_instance = BotKeeper()

    try:
        return keeper_instance.run()
    except Exception as e:
        logger.error(f"💥 Fatal keeper error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
