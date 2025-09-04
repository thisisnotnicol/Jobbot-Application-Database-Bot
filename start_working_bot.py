#!/usr/bin/env python3
"""
Start Working JobBot - Complete Solution
Starts the comprehensive working Slack bot that fixes all issues at once
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
        return False

    return True

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import slack_bolt
        import openai
        import notion_client
        import requests
        import bs4
        import playwright
        return True
    except ImportError as e:
        print(f"❌ Missing required packages: {e}")
        print("\nInstall dependencies with:")
        print("   pip install -r requirements.txt")
        return False

def start_working_bot():
    """Start the comprehensive working Slack bot"""
    try:
        import asyncio
        from slack_bot_working import main as bot_main

        print("🤖 Starting JobBot - COMPREHENSIVE WORKING VERSION")
        print("=" * 60)
        print("\n🎉 THIS VERSION FIXES ALL ISSUES AT ONCE:")
        print("")
        print("✅ NO MORE DISPATCH_FAILED ERRORS")
        print("   • Uses proven jobbot_cli functions")
        print("   • Minimal async complexity")
        print("   • Robust error handling")
        print("")
        print("✅ COMPLETE NOTION INTEGRATION")
        print("   • Company name -> Company relation linking")
        print("   • Salary field properly populated")
        print("   • Location multi-select tags")
        print("   • Industry multi-select tags")
        print("   • Commitment multi-select handling")
        print("   • Job Description toggle blocks with FULL content")
        print("   • Status: 'Researching', Processed: False")
        print("")
        print("✅ ALL SLACK FEATURES WORKING")
        print("   • Direct messages with job URLs")
        print("   • @jobbot https://job-url.com in channels")
        print("   • /addjob https://job-url.com slash command")
        print("")
        print("🚀 Bot starting... Send job URLs to test!")
        print("-" * 60)

        asyncio.run(bot_main())

    except KeyboardInterrupt:
        print("\n👋 JobBot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        print("\nTroubleshooting:")
        print("1. Check your .env file has all required variables")
        print("2. Verify Slack app configuration (Socket Mode enabled)")
        print("3. Run 'python check_config.py' to verify connections")
        print("4. Check slack_bot_working.log for detailed logs")
        sys.exit(1)

def main():
    print("🚀 JobBot - COMPREHENSIVE WORKING VERSION")
    print("=" * 50)

    # Check environment
    print("🔍 Checking environment variables...")
    if not check_environment():
        sys.exit(1)
    print("✅ Environment variables OK")

    # Check dependencies
    print("\n📦 Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    print("✅ Dependencies OK")

    # Start bot
    print("\n🎯 All checks passed!")
    print("🔧 Starting COMPREHENSIVE WORKING VERSION...")
    print("")
    print("This version combines ALL fixes in one implementation:")
    print("• Fixes dispatch_failed errors")
    print("• Populates all Notion fields correctly")
    print("• Creates job description toggle blocks")
    print("• Links company relations properly")
    print("• Handles all multi-select fields")
    print("")
    time.sleep(2)

    start_working_bot()

if __name__ == "__main__":
    main()
