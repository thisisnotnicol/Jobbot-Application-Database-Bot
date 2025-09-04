#!/usr/bin/env python3
"""
Slack Configuration Diagnostic Script
Diagnoses dispatch_failed errors and Slack bot configuration issues
"""

import os
import sys
import json
import asyncio
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("slack_diagnostic.log")
    ]
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check Slack environment variables"""
    print("🔍 Checking Slack Environment Variables")
    print("-" * 50)

    load_dotenv()

    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")

    if not bot_token:
        print("❌ SLACK_BOT_TOKEN is missing")
        return False
    elif not bot_token.startswith("xoxb-"):
        print(f"❌ SLACK_BOT_TOKEN format invalid: {bot_token[:10]}...")
        print("   Should start with 'xoxb-'")
        return False
    else:
        print(f"✅ SLACK_BOT_TOKEN: {bot_token[:10]}...{bot_token[-4:]}")

    if not app_token:
        print("❌ SLACK_APP_TOKEN is missing")
        return False
    elif not app_token.startswith("xapp-"):
        print(f"❌ SLACK_APP_TOKEN format invalid: {app_token[:10]}...")
        print("   Should start with 'xapp-'")
        return False
    else:
        print(f"✅ SLACK_APP_TOKEN: {app_token[:10]}...{app_token[-4:]}")

    return True

def test_slack_imports():
    """Test Slack library imports"""
    print("\n📦 Testing Slack Library Imports")
    print("-" * 50)

    try:
        import slack_bolt
        try:
            print(f"✅ slack-bolt version: {slack_bolt.__version__}")
        except AttributeError:
            print("✅ slack-bolt imported (version detection unavailable)")
    except ImportError as e:
        print(f"❌ Failed to import slack-bolt: {e}")
        return False

    try:
        import slack_sdk
        try:
            print(f"✅ slack-sdk version: {slack_sdk.__version__}")
        except AttributeError:
            print("✅ slack-sdk imported (version detection unavailable)")
    except ImportError as e:
        print(f"❌ Failed to import slack-sdk: {e}")
        return False

    try:
        from slack_bolt.async_app import AsyncApp
        from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
        print("✅ Async Slack modules imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import async Slack modules: {e}")
        return False

    return True

async def test_slack_connection():
    """Test basic Slack API connection"""
    print("\n🔌 Testing Slack API Connection")
    print("-" * 50)

    try:
        from slack_sdk.web.async_client import AsyncWebClient

        bot_token = os.getenv("SLACK_BOT_TOKEN")
        client = AsyncWebClient(token=bot_token)

        # Test auth
        auth_response = await client.auth_test()

        if auth_response["ok"]:
            print("✅ Slack API authentication successful")
            print(f"   Bot User ID: {auth_response.get('user_id')}")
            print(f"   Bot User: @{auth_response.get('user')}")
            print(f"   Team: {auth_response.get('team')}")
            print(f"   Team ID: {auth_response.get('team_id')}")
            return True
        else:
            print(f"❌ Slack API authentication failed: {auth_response.get('error')}")
            return False

    except Exception as e:
        print(f"❌ Slack API connection failed: {e}")
        logger.exception("Full connection error:")
        return False

def test_socket_mode_requirements():
    """Check Socket Mode configuration requirements"""
    print("\n🔧 Checking Socket Mode Requirements")
    print("-" * 50)

    app_token = os.getenv("SLACK_APP_TOKEN")

    if not app_token:
        print("❌ SLACK_APP_TOKEN required for Socket Mode")
        return False

    print("✅ App-level token present")

    # Check token scopes (basic validation)
    if len(app_token) < 50:
        print("⚠️  App token seems short - verify it's complete")

    print("ℹ️  Socket Mode Checklist:")
    print("   • Slack app has Socket Mode enabled")
    print("   • App-level token has connections:write scope")
    print("   • Bot token has required OAuth scopes")
    print("   • Event subscriptions are configured")

    return True

async def test_minimal_bot():
    """Test a minimal bot to isolate dispatch issues"""
    print("\n🤖 Testing Minimal Bot")
    print("-" * 50)

    try:
        from slack_bolt.async_app import AsyncApp
        from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

        bot_token = os.getenv("SLACK_BOT_TOKEN")
        app_token = os.getenv("SLACK_APP_TOKEN")

        # Create minimal app
        app = AsyncApp(token=bot_token, logger=logger)

        # Add minimal event handler that should never fail
        @app.event("app_mention")
        async def test_mention(event, say):
            logger.info(f"Test mention received: {event}")
            try:
                await say("🧪 Diagnostic bot test - mention received")
                logger.info("Test mention response sent")
            except Exception as e:
                logger.error(f"Error in test mention: {e}")
                raise

        @app.event("message")
        async def test_message(event, say):
            # Only handle DMs
            if event.get('channel_type') != 'im':
                return
            if event.get('bot_id'):
                return

            logger.info(f"Test DM received: {event}")
            try:
                await say("🧪 Diagnostic bot test - DM received")
                logger.info("Test DM response sent")
            except Exception as e:
                logger.error(f"Error in test DM: {e}")
                raise

        # Global error handler
        @app.error
        async def test_error_handler(error, body, logger_param):
            logger.error("=== DISPATCH ERROR DETECTED ===")
            logger.error(f"Error: {error}")
            logger.error(f"Error type: {type(error)}")
            logger.error(f"Request body: {json.dumps(body, indent=2, default=str)}")
            logger.error("=== END DISPATCH ERROR ===")

        # Create handler
        handler = AsyncSocketModeHandler(app, app_token)

        print("✅ Minimal bot created successfully")
        print("🔄 Testing connection (5 second timeout)...")

        # Test connection with timeout
        try:
            await asyncio.wait_for(
                handler.connect_async(),
                timeout=5.0
            )
            print("✅ Socket Mode connection established")

            # Disconnect immediately
            await handler.disconnect_async()
            print("✅ Socket Mode disconnection successful")
            return True

        except asyncio.TimeoutError:
            print("⚠️  Connection timeout - this may indicate network issues")
            return False

    except Exception as e:
        print(f"❌ Minimal bot test failed: {e}")
        logger.exception("Full minimal bot error:")
        return False

def check_common_issues():
    """Check for common dispatch_failed causes"""
    print("\n🔍 Common Dispatch Failed Causes")
    print("-" * 50)

    issues = []

    # Check Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")

    if python_version < (3, 7):
        issues.append("Python version too old (need 3.7+)")

    # Check async/await patterns
    print("ℹ️  Common causes of dispatch_failed:")
    print("   • Synchronous code in async handlers")
    print("   • Unhandled exceptions in event handlers")
    print("   • Network timeouts or connection issues")
    print("   • Invalid event handler signatures")
    print("   • Missing required Slack app permissions")
    print("   • Incorrect OAuth scopes")
    print("   • Socket Mode not properly enabled")

    if issues:
        print("\n❌ Issues detected:")
        for issue in issues:
            print(f"   • {issue}")
        return False

    return True

def print_debugging_guide():
    """Print debugging steps for dispatch_failed"""
    print("\n📋 Dispatch Failed Debugging Guide")
    print("-" * 50)
    print("1. Check Slack App Configuration:")
    print("   • Go to https://api.slack.com/apps")
    print("   • Select your app")
    print("   • Socket Mode: ON")
    print("   • Event Subscriptions: ON")
    print("   • OAuth Scopes: app_mentions:read, chat:write, channels:history, groups:history, im:history, mpim:history")
    print("   • Events: app_mention, message.channels, message.groups, message.im, message.mpim")

    print("\n2. Check App Installation:")
    print("   • App is installed in your workspace")
    print("   • Bot user is present (@your-bot-name)")
    print("   • App has necessary permissions")

    print("\n3. Check Network:")
    print("   • No firewall blocking Slack connections")
    print("   • Stable internet connection")
    print("   • No VPN interfering with WebSocket connections")

    print("\n4. Check Code:")
    print("   • All async functions properly await operations")
    print("   • No synchronous blocking code in event handlers")
    print("   • Proper exception handling in all handlers")
    print("   • Handler function signatures match Slack SDK requirements")

async def main():
    """Run all diagnostic tests"""
    print("🩺 Slack Bot Dispatch Failed Diagnostics")
    print("=" * 60)

    results = []

    # Environment check
    results.append(("Environment Variables", check_environment()))

    # Import check
    results.append(("Library Imports", test_slack_imports()))

    # Connection check
    if results[-1][1]:  # Only if imports worked
        results.append(("Slack API Connection", await test_slack_connection()))

    # Socket Mode check
    results.append(("Socket Mode Config", test_socket_mode_requirements()))

    # Minimal bot test
    if all(result[1] for result in results):
        results.append(("Minimal Bot Test", await test_minimal_bot()))

    # Common issues check
    results.append(("Common Issues", check_common_issues()))

    # Results summary
    print("\n📊 Diagnostic Results")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All diagnostics passed!")
        print("If you're still getting dispatch_failed, the issue may be:")
        print("• Specific to your event handler implementation")
        print("• Network or timing related")
        print("• Slack app configuration on their end")
    else:
        print("\n❌ Issues detected that may cause dispatch_failed")
        print_debugging_guide()

    print(f"\n📝 Full diagnostic log saved to: slack_diagnostic.log")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Diagnostics interrupted")
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        logging.exception("Diagnostic error:")
