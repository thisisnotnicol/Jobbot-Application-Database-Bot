#!/usr/bin/env python3
"""
Master Startup Script for Bulletproof JobBot
Combines watchdog monitoring with the bulletproof Slack bot for maximum reliability
"""

import os
import sys
import time
import signal
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('bulletproof_startup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BulletproofBotManager:
    """Master manager for the bulletproof bot system"""

    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.venv_python = self.script_dir / "venv" / "bin" / "python3"
        self.bot_script = self.script_dir / "slack_bot_bulletproof.py"
        self.watchdog_script = self.script_dir / "bot_watchdog.py"

        self.bot_process = None
        self.watchdog_process = None
        self.running = False

    def check_environment(self):
        """Verify all requirements are met"""
        logger.info("Checking environment...")

        issues = []

        # Check Python virtual environment
        if not self.venv_python.exists():
            issues.append(f"Virtual environment Python not found: {self.venv_python}")

        # Check bot script
        if not self.bot_script.exists():
            issues.append(f"Bot script not found: {self.bot_script}")

        # Check environment variables
        required_vars = ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN']
        for var in required_vars:
            if not os.getenv(var):
                issues.append(f"Missing required environment variable: {var}")

        # Check optional services
        optional_vars = {
            'OPENAI_API_KEY': 'AI processing',
            'NOTION_TOKEN': 'Notion integration',
            'NOTION_DATABASE_ID': 'Notion database'
        }

        for var, service in optional_vars.items():
            if not os.getenv(var):
                logger.warning(f"Optional service disabled - missing {var}: {service}")

        if issues:
            logger.error("Environment check failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False

        logger.info("Environment check passed ✓")
        return True

    def start_bot_direct(self):
        """Start the bot directly (for testing)"""
        try:
            logger.info("Starting bulletproof bot directly...")

            cmd = [str(self.venv_python), str(self.bot_script)]

            self.bot_process = subprocess.Popen(
                cmd,
                cwd=str(self.script_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            logger.info(f"Bot started with PID: {self.bot_process.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            return False

    def start_with_watchdog(self):
        """Start bot with watchdog monitoring"""
        try:
            logger.info("Starting bot with watchdog monitoring...")

            cmd = [str(self.venv_python), str(self.watchdog_script)]

            self.watchdog_process = subprocess.Popen(
                cmd,
                cwd=str(self.script_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            logger.info(f"Watchdog started with PID: {self.watchdog_process.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to start watchdog: {e}")
            return False

    def stop_all(self):
        """Stop all processes"""
        logger.info("Stopping all processes...")

        processes = [
            ("bot", self.bot_process),
            ("watchdog", self.watchdog_process)
        ]

        for name, process in processes:
            if process and process.poll() is None:
                try:
                    logger.info(f"Stopping {name} process (PID: {process.pid})")
                    process.terminate()
                    process.wait(timeout=10)
                    logger.info(f"{name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning(f"{name} didn't stop gracefully, killing...")
                    process.kill()
                    process.wait()
                except Exception as e:
                    logger.error(f"Error stopping {name}: {e}")

        self.running = False

    def monitor_processes(self):
        """Monitor running processes"""
        logger.info("Starting process monitor...")
        self.running = True

        try:
            while self.running:
                # Check bot process
                if self.bot_process and self.bot_process.poll() is not None:
                    logger.error(f"Bot process died with exit code: {self.bot_process.returncode}")
                    self.running = False
                    break

                # Check watchdog process
                if self.watchdog_process and self.watchdog_process.poll() is not None:
                    logger.error(f"Watchdog process died with exit code: {self.watchdog_process.returncode}")
                    self.running = False
                    break

                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")

        finally:
            self.stop_all()

    def run_interactive_mode(self):
        """Run in interactive mode for testing"""
        logger.info("=== BULLETPROOF JOBBOT STARTUP ===")
        logger.info("Interactive mode - choose startup option:")
        logger.info("")
        logger.info("1. Start bot directly (for testing)")
        logger.info("2. Start with watchdog (production mode)")
        logger.info("3. Run environment check only")
        logger.info("4. Exit")

        while True:
            try:
                choice = input("\nEnter choice (1-4): ").strip()

                if choice == "1":
                    if self.check_environment():
                        if self.start_bot_direct():
                            logger.info("Bot running in direct mode. Press Ctrl+C to stop.")
                            self.monitor_processes()
                        else:
                            logger.error("Failed to start bot")
                    break

                elif choice == "2":
                    if self.check_environment():
                        if self.start_with_watchdog():
                            logger.info("Bot running with watchdog. Press Ctrl+C to stop.")
                            self.monitor_processes()
                        else:
                            logger.error("Failed to start with watchdog")
                    break

                elif choice == "3":
                    self.check_environment()
                    break

                elif choice == "4":
                    logger.info("Exiting...")
                    break

                else:
                    print("Invalid choice. Please enter 1-4.")

            except (KeyboardInterrupt, EOFError):
                logger.info("Interrupted by user")
                break

    def run_production_mode(self):
        """Run in production mode (watchdog automatically)"""
        logger.info("=== BULLETPROOF JOBBOT - PRODUCTION MODE ===")

        if not self.check_environment():
            logger.error("Environment check failed. Cannot start in production mode.")
            return 1

        if not self.start_with_watchdog():
            logger.error("Failed to start watchdog. Cannot start in production mode.")
            return 1

        logger.info("Production mode active. Bot will run with watchdog monitoring.")
        logger.info("Press Ctrl+C to stop.")

        try:
            self.monitor_processes()
            return 0
        except Exception as e:
            logger.error(f"Production mode error: {e}")
            return 1

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    global manager
    if manager:
        manager.stop_all()
    sys.exit(0)

def main():
    """Main entry point"""
    global manager

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create manager
    manager = BulletproofBotManager()

    # Check command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

        if mode == "production" or mode == "prod":
            return manager.run_production_mode()
        elif mode == "direct":
            if manager.check_environment() and manager.start_bot_direct():
                logger.info("Direct mode started. Press Ctrl+C to stop.")
                manager.monitor_processes()
                return 0
            else:
                return 1
        elif mode == "check":
            return 0 if manager.check_environment() else 1
        else:
            logger.error(f"Unknown mode: {mode}")
            logger.error("Usage: python start_bulletproof_bot.py [production|direct|check]")
            return 1
    else:
        # Interactive mode
        manager.run_interactive_mode()
        return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Startup script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in startup script: {e}")
        sys.exit(1)
