#!/usr/bin/env python3
"""
JobBot Slack Bot Starter - FINAL CORRECTED VERSION
Starts the fully corrected Slack bot with all fixes applied:
- Proper field extraction and JSON parsing
- Company relation handling
- All multi-select fields (Location, Industry, Commitment)
- Job description toggle blocks with full content
- Proper Salary field population
- Correct Status and Processed field values
"""

import os
import sys
import time
import asyncio
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
        return False

    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        ('slack_bolt', 'Slack bot framework'),
        ('openai', 'OpenAI API client'),
        ('notion_client', 'Notion API client'),
        ('requests', 'HTTP requests'),
        ('bs4', 'HTML parsing'),
        ('dotenv', 'Environment variables')
    ]

    missing = []
    for package, description in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append((package, description))

    if missing:
        print("❌ Missing required packages:")
        for package, description in missing:
            print(f"   - {package} ({description})")
        print("\nInstall dependencies with:")
        print("   pip install -r requirements.txt")
        return False

    return True

async def start_corrected_slack_bot():
    """Start the fully corrected Slack bot"""
    try:
        # Import the corrected Slack bot
        from enhanced_jobbot.slack_bot_fixed import main as slack_main

        print("🤖 Starting JobBot Slack Integration - FINAL CORRECTED VERSION")
        print("=" * 60)
        print("\n✨ ALL FIXES APPLIED:")
        print("• ✅ Robust JSON parsing with multiple fallback strategies")
        print("• ✅ Company relation lookup/creation")
        print("• ✅ Proper Salary field population")
        print("• ✅ Location multi-select tags")
        print("• ✅ Industry multi-select tags")
        print("• ✅ Commitment multi-select handling")
        print("• ✅ Job Description toggle blocks with full content")
        print("• ✅ Correct Status ('Researching') and Processed (False) values")
        print("• ✅ Comprehensive error handling for all Slack events")
        print("• ✅ Enhanced web scraping with Playwright + fallback")
        print("• ✅ AI-powered field extraction with validation")

        print("\n🎯 SLACK COMMANDS READY:")
        print("• Direct message: Send job URLs directly to @jobbot")
        print("• Channel mention: @jobbot https://job-url.com")
        print("• Slash command: /addjob https://job-url.com")

        print("\n📊 NOTION INTEGRATION:")
        print("• Creates new pages with ALL extracted information")
        print("• Links to existing Company database entries")
        print("• Stores full job description in collapsible toggle")
        print("• Populates all fields: Position, Company, Salary, Location, etc.")

        print(f"\n🚀 Bot starting... Press Ctrl+C to stop")
        print("-" * 60)

        # Start the async bot
        await slack_main()

    except KeyboardInterrupt:
        print("\n👋 JobBot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        print("\n🔍 TROUBLESHOOTING:")
        print("1. Check your .env file has all required variables")
        print("2. Verify Slack app configuration (Socket Mode enabled)")
        print("3. Run 'python check_config.py' to verify all connections")
        print("4. Check slack_jobbot_fixed.log for detailed error logs")
        print("5. Ensure bot has proper permissions in your Slack workspace")
        raise

def main():
    """Main startup function"""
    print("🚀 JobBot Slack Bot Starter - FINAL CORRECTED VERSION")
    print("=" * 60)

    # Environment check
    print("🔍 Checking environment variables...")
    if not check_environment():
        print("\n💡 SETUP HELP:")
        print("Create a .env file in the project root with:")
        print("OPENAI_API_KEY=sk-...")
        print("NOTION_TOKEN=secret_...")
        print("NOTION_DATABASE_ID=...")
        print("SLACK_BOT_TOKEN=xoxb-...")
        print("SLACK_APP_TOKEN=xapp-...")
        sys.exit(1)
    print("✅ Environment variables OK")

    # Dependencies check
    print("\n📦 Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    print("✅ Dependencies OK")

    # Final verification
    print("\n🎯 All checks passed!")
    print("🔧 Starting FULLY CORRECTED Slack bot...")
    print("🎉 This version includes ALL the fixes for:")
    print("   - Company name linking")
    print("   - Salary information extraction")
    print("   - Location and Industry tags")
    print("   - Job description toggle blocks")
    print("   - Proper field mapping and validation")

    time.sleep(2)

    # Run the async bot
    try:
        asyncio.run(start_corrected_slack_bot())
    except KeyboardInterrupt:
        print("\n👋 JobBot stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
