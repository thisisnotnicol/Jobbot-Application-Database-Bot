#!/usr/bin/env python3
"""
JobBot Slack Bot Starter
Simple script to start the JobBot Slack integration with proper error handling
"""

import os
import sys
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
sys.path.insert(0, src_dir)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'OPENAI_API_KEY',
        'NOTION_TOKEN',
        'NOTION_DATABASE_ID',
        'SLACK_BOT_TOKEN',
        'SLACK_APP_TOKEN'
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nPlease add these to your .env file")
        print("See SLACK_SETUP.md for detailed setup instructions")
        return False

    return True

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import slack_bolt
        import openai
        import notion_client
        return True
    except ImportError as e:
        print("❌ Missing required packages:")
        print(f"   {e}")
        print("\nInstall dependencies with:")
        print("   pip install -r requirements.txt")
        return False

def start_bot():
    """Start the Slack bot"""
    try:
        # Import and run the bot
        from enhanced_jobbot.slack_bot import main
        import asyncio

        print("🤖 Starting JobBot Slack Integration...")
        print("\nReady to process job URLs! Try:")
        print("• DM the bot with job URLs")
        print("• @jobbot https://job-url.com in channels")
        print("• /addjob https://job-url.com")
        print("\nPress Ctrl+C to stop")
        print("-" * 50)

        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n👋 JobBot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        print("\nTroubleshooting:")
        print("1. Check your .env file has all required variables")
        print("2. Verify Slack app is configured correctly")
        print("3. See SLACK_SETUP.md for detailed setup guide")
        sys.exit(1)

def main():
    print("🚀 JobBot Slack Bot Starter")
    print("=" * 40)

    # Check environment
    print("🔍 Checking environment variables...")
    if not check_environment():
        sys.exit(1)
    print("✅ Environment variables OK")

    # Check dependencies
    print("📦 Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    print("✅ Dependencies OK")

    # Start bot
    print("🎯 All checks passed!")
    time.sleep(1)
    start_bot()

if __name__ == "__main__":
    main()
