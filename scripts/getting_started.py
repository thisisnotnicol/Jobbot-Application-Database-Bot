#!/usr/bin/env python3
"""
Enhanced JobBot - Getting Started Guide

This interactive script helps new users get up and running quickly with
the Enhanced JobBot project. It provides step-by-step guidance for
setting up API keys, configuring Notion, and running your first job.
"""

import os
import sys
import subprocess
import webbrowser
from pathlib import Path

def print_banner():
    """Print welcome banner"""
    print("\n" + "🤖" * 20)
    print("   ENHANCED JOBBOT - GETTING STARTED")
    print("🤖" * 20)
    print("\nWelcome to your AI-powered job application assistant!")
    print("This guide will help you set up everything you need.\n")

def print_section(title):
    """Print section header"""
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print("=" * 50)

def print_step(step, title, description=""):
    """Print a numbered step"""
    print(f"\n📋 STEP {step}: {title}")
    if description:
        print(f"   {description}")

def wait_for_user():
    """Wait for user to press Enter"""
    print("\n👉 Press Enter when ready to continue...")
    input()

def check_prerequisites():
    """Check if basic requirements are met"""
    print_step(1, "Checking Prerequisites", "Making sure your system is ready")

    # Check Python version
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} is not supported")
        print("   Please install Python 3.8 or higher")
        return False
    print(f"✅ Python {version.major}.{version.minor} is ready")

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Cannot find project files")
        print("   Make sure you're in the Enhanced JobBot directory")
        return False
    print("✅ Project files found")

    # Check if virtual environment exists
    if Path(".venv").exists() or Path("venv").exists():
        print("✅ Virtual environment detected")
    else:
        print("⚠️  No virtual environment found")
        print("   Run 'python setup.py' to create one")

    return True

def guide_openai_setup():
    """Guide user through OpenAI API setup"""
    print_step(2, "OpenAI API Setup", "Get your API key for AI-powered extraction")

    print("\n🔑 You need an OpenAI API key to extract job data with AI.")
    print("\nWhat the bot uses OpenAI for:")
    print("  • Extract job titles, companies, salaries from job postings")
    print("  • Generate concise summaries of job descriptions")
    print("  • Structure unorganized job data into clean fields")

    print("\n💰 Cost: Typically $0.01-0.05 per job (very affordable!)")

    print("\n📋 To get your API key:")
    print("1. Go to https://platform.openai.com/api-keys")
    print("2. Sign up or log in to your OpenAI account")
    print("3. Click '+ Create new secret key'")
    print("4. Copy the key (starts with 'sk-')")

    print("\n🌐 Would you like me to open the OpenAI website? [Y/n]: ", end="")
    if input().strip().lower() in ['', 'y', 'yes']:
        try:
            webbrowser.open("https://platform.openai.com/api-keys")
            print("✅ OpenAI website opened in your browser")
        except:
            print("⚠️  Couldn't open browser, please visit the URL manually")

    wait_for_user()

def guide_notion_setup():
    """Guide user through Notion integration setup"""
    print_step(3, "Notion Integration Setup", "Connect to your job tracking database")

    print("\n📊 Enhanced JobBot will automatically populate your Notion database.")
    print("\nWhat gets added to Notion:")
    print("  • Job title and company name")
    print("  • Salary and location information")
    print("  • AI-generated job summaries")
    print("  • Complete job descriptions")
    print("  • Industry tags and employment type")

    print("\n🔧 Setup steps:")
    print("1. Create a Notion integration:")
    print("   • Go to https://www.notion.so/my-integrations")
    print("   • Click '+ New integration'")
    print("   • Give it a name like 'JobBot'")
    print("   • Copy the integration token (starts with 'secret_')")

    print("\n🌐 Would you like me to open Notion integrations? [Y/n]: ", end="")
    if input().strip().lower() in ['', 'y', 'yes']:
        try:
            webbrowser.open("https://www.notion.so/my-integrations")
            print("✅ Notion integrations page opened")
        except:
            print("⚠️  Couldn't open browser, please visit the URL manually")

    print("\n2. Connect integration to your database:")
    print("   • Open your job tracking database in Notion")
    print("   • Click '...' menu → 'Connect to' → Select your integration")
    print("   • Copy the database ID from the URL")

    print("\n💡 Database ID is the long string in your database URL:")
    print("   https://notion.so/your-workspace/DATABASE_ID_HERE?v=...")

    wait_for_user()

def guide_database_setup():
    """Guide user through Notion database field setup"""
    print_step(4, "Database Fields Setup", "Ensure your database has the right structure")

    print("\n📋 Your Notion database needs these REQUIRED fields:")

    required_fields = [
        ("Position", "Title", "Job title (e.g., 'Senior Developer')"),
        ("Job Description", "Text", "Full job posting content"),
        ("Job URL", "URL", "Link to the job posting"),
        ("Processed", "Checkbox", "Tracks which jobs the bot has processed"),
        ("Status", "Select", "Application status (Researching, Applied, etc.)"),
        ("Salary", "Text", "Salary range or compensation info"),
        ("Location", "Multi-select", "Job locations and remote options"),
        ("Industry", "Multi-select", "Industry tags"),
        ("Commitment", "Multi-select", "Full-time, Part-time, etc.")
    ]

    print("\n   Field Name           Type          Purpose")
    print("   " + "-" * 55)
    for name, field_type, purpose in required_fields:
        print(f"   {name:<18} {field_type:<12} {purpose}")

    print("\n✨ OPTIONAL fields for enhanced features:")
    optional_fields = [
        ("Job Summary", "Text", "AI-generated job overview"),
        ("Job Description Part 2-5", "Text", "Extended description storage")
    ]

    for name, field_type, purpose in optional_fields:
        print(f"   {name:<18} {field_type:<12} {purpose}")

    print("\n📝 To add fields in Notion:")
    print("1. Open your database")
    print("2. Click '+' next to the last column")
    print("3. Choose the field type and enter the name exactly as shown")

    wait_for_user()

def guide_env_setup():
    """Guide user through .env file setup"""
    print_step(5, "Environment Configuration", "Add your API keys to the project")

    env_file = Path(".env")
    example_file = Path(".env.example")

    if env_file.exists():
        print("✅ .env file already exists")
        print("\n📝 Make sure it contains:")
    else:
        print("📝 Creating .env file from template...")
        if example_file.exists():
            try:
                with open(example_file, 'r') as f:
                    content = f.read()
                with open(env_file, 'w') as f:
                    f.write(content)
                print("✅ Created .env file")
            except Exception as e:
                print(f"❌ Error creating .env file: {e}")
                return False

    print("\nYour .env file needs these values:")
    print("  OPENAI_API_KEY=sk-your_openai_key_here")
    print("  NOTION_TOKEN=secret_your_notion_token_here")
    print("  NOTION_DATABASE_ID=your_database_id_here")

    print(f"\n💡 Edit the .env file now:")
    if sys.platform == "win32":
        print("   notepad .env")
    else:
        print("   nano .env")
        print("   # or use your preferred editor")

    wait_for_user()

def guide_first_run():
    """Guide user through first test run"""
    print_step(6, "First Test Run", "Let's make sure everything works!")

    print("\n🧪 We'll run some tests to verify your setup:")

    # Test 1: Environment check
    print("\n1. Testing environment variables...")
    try:
        result = subprocess.run([sys.executable, "scripts/check_env.py"],
                              capture_output=True, text=True, cwd=".")
        if result.returncode == 0:
            print("✅ Environment variables look good")
        else:
            print("❌ Environment check failed")
            print(f"   Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Couldn't run environment check: {e}")
        return False

    # Test 2: Notion connection
    print("\n2. Testing Notion database connection...")
    try:
        result = subprocess.run([sys.executable, "scripts/test_notion_access.py"],
                              capture_output=True, text=True, cwd=".")
        if result.returncode == 0:
            print("✅ Notion database connection successful")
        else:
            print("❌ Notion connection failed")
            print("   Check your NOTION_TOKEN and NOTION_DATABASE_ID")
            return False
    except Exception as e:
        print(f"❌ Couldn't test Notion connection: {e}")
        return False

    return True

def guide_add_first_job():
    """Guide user through adding their first job"""
    print_step(7, "Add Your First Job", "Let's process a real job posting!")

    print("\n🎯 Time to try the bot with a real job posting!")
    print("\n📋 Steps:")
    print("1. Find a job posting URL (LinkedIn, Indeed, company website, etc.)")
    print("2. Go to your Notion database")
    print("3. Create a new entry with:")
    print("   • Job URL: paste the job posting link")
    print("   • Processed: leave UNCHECKED")
    print("   • Leave other fields empty (the bot will fill them)")

    print("\n💡 Good job sites to try:")
    print("  • jobs.lever.co (startup jobs)")
    print("  • jobs.ashbyhq.com (tech companies)")
    print("  • Company career pages")
    print("  • Most public job posting URLs work!")

    print("\n⚠️  Avoid URLs that require login (like Indeed apply pages)")

    wait_for_user()

def guide_run_bot():
    """Guide user through running the bot"""
    print_step(8, "Run the Bot", "Watch the magic happen!")

    print("\n🚀 Ready to run Enhanced JobBot!")

    print("\n📋 You have two options:")
    print("1. Enhanced Bot (RECOMMENDED)")
    print("   • AI-generated summaries")
    print("   • Complete job description preservation")
    print("   • Smart text handling")

    print("2. Original Bot")
    print("   • Basic extraction")
    print("   • 2000 character limit")

    print("\n💻 Commands to run:")
    print("Enhanced Bot:")
    print(f"   {sys.executable} -m enhanced_jobbot.enhanced_jobbot")
    print("\nOriginal Bot:")
    print(f"   {sys.executable} -m enhanced_jobbot.jobbot")

    print("\n🔄 The bot will:")
    print("  • Check for unprocessed jobs every 5 minutes")
    print("  • Scrape job content from URLs")
    print("  • Extract structured data with AI")
    print("  • Create new Notion entries with all info")
    print("  • Mark original entries as processed")

    print("\n📊 Check your Notion database to see the results!")

    wait_for_user()

def show_next_steps():
    """Show what to do after setup"""
    print_section("🎉 CONGRATULATIONS!")

    print("You're all set up with Enhanced JobBot! 🚀")

    print("\n📋 WHAT TO DO NEXT:")
    print("1. Add more job URLs to your Notion database")
    print("2. Keep 'Processed' checkbox unchecked for new jobs")
    print("3. Run the bot and let it work its magic")
    print("4. Check your database for AI-enhanced job data")

    print("\n🔧 USEFUL COMMANDS:")
    print("  # Check setup anytime")
    print(f"  {sys.executable} scripts/check_env.py")

    print("  # Test Notion connection")
    print(f"  {sys.executable} scripts/test_notion_access.py")

    print("  # Run enhanced bot")
    print(f"  {sys.executable} -m enhanced_jobbot.enhanced_jobbot")

    print("\n💡 TIPS:")
    print("  • The bot runs continuously - stop with Ctrl+C")
    print("  • Check logs for processing status")
    print("  • Add optional database fields for even more features")
    print("  • See README.md for advanced configuration")

    print("\n📞 NEED HELP?")
    print("  • Check README.md for detailed documentation")
    print("  • Review SUMMARY.md for technical details")
    print("  • Look at the scripts/ folder for utilities")

    print("\n🎯 Happy job hunting with your new AI assistant!")

def main():
    """Main getting started workflow"""
    try:
        print_banner()

        print("This interactive guide will help you:")
        print("  ✅ Set up API keys for OpenAI and Notion")
        print("  ✅ Configure your job tracking database")
        print("  ✅ Run your first AI-powered job extraction")
        print("  ✅ Get started with automated job management")

        print("\n⏱️  This should take about 10-15 minutes")
        print("\n👉 Ready to get started? Press Enter...")
        input()

        # Run through all setup steps
        if not check_prerequisites():
            print("\n❌ Prerequisites not met. Please fix the issues above and try again.")
            return 1

        guide_openai_setup()
        guide_notion_setup()
        guide_database_setup()
        guide_env_setup()

        if not guide_first_run():
            print("\n❌ Setup validation failed. Please check your configuration.")
            return 1

        guide_add_first_job()
        guide_run_bot()
        show_next_steps()

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        print("Run this script again anytime to continue setup!")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check the error and try again")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
