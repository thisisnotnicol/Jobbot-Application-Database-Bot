#!/usr/bin/env python3
"""
JobBot Configuration Checker
Validates that all required services and configurations are working correctly
"""

import os
import sys
import json
from dotenv import load_dotenv

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_status(message, status="info"):
    """Print colored status messages"""
    if status == "success":
        print(f"{Colors.GREEN}✅ {message}{Colors.END}")
    elif status == "error":
        print(f"{Colors.RED}❌ {message}{Colors.END}")
    elif status == "warning":
        print(f"{Colors.YELLOW}⚠️ {message}{Colors.END}")
    elif status == "info":
        print(f"{Colors.BLUE}ℹ️ {message}{Colors.END}")
    else:
        print(message)

def check_environment_variables():
    """Check if all required environment variables are set"""
    print(f"\n{Colors.BOLD}🔐 Environment Variables{Colors.END}")
    print("-" * 40)

    load_dotenv()

    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API access',
        'NOTION_TOKEN': 'Notion integration token',
        'NOTION_DATABASE_ID': 'Notion database ID'
    }

    optional_vars = {
        'SLACK_BOT_TOKEN': 'Slack bot functionality',
        'SLACK_APP_TOKEN': 'Slack socket mode'
    }

    all_good = True

    # Check required variables
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            masked_value = f"{value[:8]}..." if len(value) > 8 else "***"
            print_status(f"{var}: {masked_value} ({description})", "success")
        else:
            print_status(f"{var}: Missing ({description})", "error")
            all_good = False

    # Check optional variables
    slack_configured = True
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            masked_value = f"{value[:8]}..." if len(value) > 8 else "***"
            print_status(f"{var}: {masked_value} ({description})", "success")
        else:
            print_status(f"{var}: Not set ({description})", "warning")
            slack_configured = False

    if not slack_configured:
        print_status("Slack integration will not work without bot tokens", "warning")

    return all_good

def check_python_dependencies():
    """Check if required Python packages are installed"""
    print(f"\n{Colors.BOLD}📦 Python Dependencies{Colors.END}")
    print("-" * 40)

    required_packages = [
        ('openai', 'OpenAI API client'),
        ('notion_client', 'Notion API client'),
        ('requests', 'HTTP requests'),
        ('bs4', 'HTML parsing'),
        ('dotenv', 'Environment variables')
    ]

    optional_packages = [
        ('playwright', 'Advanced web scraping'),
        ('slack_bolt', 'Slack bot framework'),
        ('slack_sdk', 'Slack API client')
    ]

    all_required = True

    # Check required packages
    for package, description in required_packages:
        try:
            __import__(package)
            print_status(f"{package}: Installed ({description})", "success")
        except ImportError:
            print_status(f"{package}: Missing ({description})", "error")
            all_required = False

    # Check optional packages
    for package, description in optional_packages:
        try:
            __import__(package)
            print_status(f"{package}: Installed ({description})", "success")
        except ImportError:
            print_status(f"{package}: Not installed ({description})", "warning")

    return all_required

def check_openai_connection():
    """Test OpenAI API connection"""
    print(f"\n{Colors.BOLD}🤖 OpenAI API Connection{Colors.END}")
    print("-" * 40)

    try:
        import openai
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            print_status("OPENAI_API_KEY not set", "error")
            return False

        client = openai.OpenAI(api_key=api_key)

        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test successful'"}],
            max_tokens=10
        )

        if response.choices[0].message.content:
            print_status("OpenAI API connection successful", "success")
            print_status(f"Model: gpt-4o-mini", "info")
            return True
        else:
            print_status("OpenAI API returned empty response", "error")
            return False

    except ImportError:
        print_status("OpenAI package not installed", "error")
        return False
    except Exception as e:
        print_status(f"OpenAI API error: {str(e)}", "error")
        return False

def check_notion_connection():
    """Test Notion API connection and database access"""
    print(f"\n{Colors.BOLD}📝 Notion API Connection{Colors.END}")
    print("-" * 40)

    try:
        from notion_client import Client

        token = os.getenv("NOTION_TOKEN")
        database_id = os.getenv("NOTION_DATABASE_ID")

        if not token:
            print_status("NOTION_TOKEN not set", "error")
            return False

        if not database_id:
            print_status("NOTION_DATABASE_ID not set", "error")
            return False

        notion = Client(auth=token)

        # Test database access
        try:
            database_info = notion.databases.retrieve(database_id=database_id)
            print_status("Notion API connection successful", "success")

            # Check database properties
            properties = database_info.get('properties', {})
            print_status(f"Database title: {database_info.get('title', [{}])[0].get('plain_text', 'Unknown')}", "info")
            print_status(f"Found {len(properties)} properties", "info")

            # Check for key properties
            required_props = ['Position', 'Job URL', 'Status']
            optional_props = ['Company', 'Salary', 'Location', 'Industry', 'Job Description']

            for prop in required_props:
                if prop in properties:
                    prop_type = properties[prop].get('type', 'unknown')
                    print_status(f"✓ {prop} ({prop_type})", "success")
                else:
                    print_status(f"✗ {prop} (missing)", "error")

            for prop in optional_props:
                if prop in properties:
                    prop_type = properties[prop].get('type', 'unknown')
                    print_status(f"✓ {prop} ({prop_type})", "info")
                else:
                    print_status(f"- {prop} (not found)", "warning")

            # Check if Company is a relation
            company_prop = properties.get('Company', {})
            if company_prop.get('type') == 'relation':
                company_db_id = company_prop.get('relation', {}).get('database_id')
                if company_db_id:
                    print_status("Company field is properly configured as relation", "success")
                else:
                    print_status("Company relation missing database_id", "warning")
            elif 'Company' in properties:
                print_status("Company field exists but is not a relation", "warning")

            return True

        except Exception as e:
            print_status(f"Database access error: {str(e)}", "error")
            return False

    except ImportError:
        print_status("notion-client package not installed", "error")
        return False
    except Exception as e:
        print_status(f"Notion connection error: {str(e)}", "error")
        return False

def check_slack_connection():
    """Test Slack API connection (if configured)"""
    print(f"\n{Colors.BOLD}💬 Slack API Connection{Colors.END}")
    print("-" * 40)

    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")

    if not bot_token or not app_token:
        print_status("Slack tokens not configured - skipping", "warning")
        print_status("Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN to enable Slack integration", "info")
        return True  # Not an error, just not configured

    try:
        from slack_sdk import WebClient

        client = WebClient(token=bot_token)

        # Test API connection
        response = client.auth_test()

        if response.get("ok"):
            print_status("Slack API connection successful", "success")
            print_status(f"Bot user: @{response.get('user')}", "info")
            print_status(f"Team: {response.get('team')}", "info")
            return True
        else:
            print_status(f"Slack API error: {response.get('error', 'Unknown error')}", "error")
            return False

    except ImportError:
        print_status("Slack packages not installed", "warning")
        print_status("Install with: pip install slack-bolt slack-sdk", "info")
        return True  # Not required for basic functionality
    except Exception as e:
        print_status(f"Slack connection error: {str(e)}", "error")
        return False

def check_web_scraping():
    """Test web scraping capabilities"""
    print(f"\n{Colors.BOLD}🌐 Web Scraping Test{Colors.END}")
    print("-" * 40)

    all_good = True

    # Test basic requests
    try:
        import requests
        response = requests.get("https://httpbin.org/get", timeout=10)
        if response.status_code == 200:
            print_status("Basic HTTP requests working", "success")
        else:
            print_status(f"HTTP request failed: {response.status_code}", "warning")
            all_good = False
    except Exception as e:
        print_status(f"Requests error: {str(e)}", "error")
        all_good = False

    # Test BeautifulSoup
    try:
        from bs4 import BeautifulSoup
        html = "<html><body><h1>Test</h1></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        if soup.find('h1'):
            print_status("BeautifulSoup HTML parsing working", "success")
        else:
            print_status("BeautifulSoup parsing failed", "error")
            all_good = False
    except Exception as e:
        print_status(f"BeautifulSoup error: {str(e)}", "error")
        all_good = False

    # Test Playwright (optional)
    try:
        from playwright.sync_api import sync_playwright
        print_status("Playwright available for advanced scraping", "success")
        print_status("Run 'playwright install' if you haven't already", "info")
    except ImportError:
        print_status("Playwright not installed (optional)", "warning")
        print_status("Install with: pip install playwright && playwright install", "info")

    return all_good

def main():
    """Run all configuration checks"""
    print(f"{Colors.BOLD}🔍 JobBot Configuration Checker{Colors.END}")
    print("=" * 50)

    checks = [
        ("Environment Variables", check_environment_variables),
        ("Python Dependencies", check_python_dependencies),
        ("OpenAI Connection", check_openai_connection),
        ("Notion Connection", check_notion_connection),
        ("Slack Connection", check_slack_connection),
        ("Web Scraping", check_web_scraping)
    ]

    results = {}

    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_status(f"Check failed with error: {str(e)}", "error")
            results[name] = False

    # Summary
    print(f"\n{Colors.BOLD}📊 Configuration Summary{Colors.END}")
    print("-" * 40)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for name, result in results.items():
        status = "success" if result else "error"
        print_status(f"{name}: {'PASS' if result else 'FAIL'}", status)

    print(f"\n{Colors.BOLD}Result: {passed}/{total} checks passed{Colors.END}")

    if passed == total:
        print_status("🎉 All checks passed! JobBot is ready to use.", "success")
        print("\nYou can now run:")
        print("• python add_job.py 'https://job-url.com'  (Command line)")
        print("• python start_slack_bot.py  (Slack integration)")
    else:
        print_status("❌ Some checks failed. Please fix the issues above.", "error")
        print("\nSee README.md or SLACK_SETUP.md for setup instructions.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
