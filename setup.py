#!/usr/bin/env python3
"""
Enhanced JobBot Setup Script

This script helps you get started with the Enhanced JobBot project quickly.
It will guide you through the installation and configuration process.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_step(step, text):
    """Print a formatted step"""
    print(f"\n{step}. {text}")

def run_command(command, description=""):
    """Run a command and handle errors"""
    print(f"   Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        if e.stderr:
            print(f"   Error details: {e.stderr.strip()}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} is not supported")
        print("   Enhanced JobBot requires Python 3.8 or higher")
        print("   Please install a newer version of Python")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_uv_installation():
    """Check if uv is installed"""
    if shutil.which("uv"):
        print("✅ uv is installed")
        return True
    else:
        print("⚠️  uv is not installed")
        print("   uv is the recommended package manager for this project")
        return False

def install_uv():
    """Install uv package manager"""
    print("\nWould you like to install uv? (recommended) [Y/n]: ", end="")
    response = input().strip().lower()

    if response in ['', 'y', 'yes']:
        print("Installing uv...")
        if sys.platform == "win32":
            command = 'powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
        else:
            command = 'curl -LsSf https://astral.sh/uv/install.sh | sh'

        if run_command(command):
            print("✅ uv installed successfully")
            print("   Please restart your terminal or run: source ~/.bashrc")
            return True
        else:
            print("❌ Failed to install uv")
            return False
    return False

def create_virtual_environment():
    """Create virtual environment"""
    print("\nChoose your setup method:")
    print("1. Use uv (recommended)")
    print("2. Use traditional pip/venv")
    print("Choice [1]: ", end="")

    choice = input().strip()
    if not choice:
        choice = "1"

    if choice == "1":
        if not shutil.which("uv"):
            print("❌ uv not found. Installing uv first...")
            if not install_uv():
                print("Falling back to pip/venv...")
                choice = "2"

    if choice == "1":
        print("Creating virtual environment with uv...")
        if run_command("uv venv"):
            print("✅ Virtual environment created with uv")
            if sys.platform == "win32":
                activate_script = ".venv\\Scripts\\activate"
            else:
                activate_script = ".venv/bin/activate"
            print(f"   To activate: source {activate_script}")
            return "uv"

    # Fallback to traditional pip/venv
    print("Creating virtual environment with pip/venv...")
    if run_command(f"{sys.executable} -m venv venv"):
        print("✅ Virtual environment created with pip/venv")
        if sys.platform == "win32":
            activate_script = "venv\\Scripts\\activate"
        else:
            activate_script = "venv/bin/activate"
        print(f"   To activate: source {activate_script}")
        return "pip"

    print("❌ Failed to create virtual environment")
    return None

def install_dependencies(method):
    """Install project dependencies"""
    print("Installing dependencies...")

    if method == "uv":
        commands = [
            "uv pip install -r requirements.txt",
            "playwright install"
        ]
    else:
        if sys.platform == "win32":
            activate = "venv\\Scripts\\activate &&"
        else:
            activate = "source venv/bin/activate &&"

        commands = [
            f"{activate} pip install -r requirements.txt",
            f"{activate} playwright install"
        ]

    success = True
    for command in commands:
        if not run_command(command):
            success = False
            break

    return success

def setup_environment_file():
    """Help user set up environment variables"""
    env_file = Path(".env")
    example_file = Path(".env.example")

    if env_file.exists():
        print("✅ .env file already exists")
        return True

    if not example_file.exists():
        print("⚠️  .env.example file not found")
        return False

    print("Setting up environment variables...")
    print("I'll copy .env.example to .env for you to fill in")

    try:
        shutil.copy(example_file, env_file)
        print("✅ Created .env file from template")
        print("\n📝 IMPORTANT: Edit .env file with your actual API keys:")
        print("   - OPENAI_API_KEY: Get from https://platform.openai.com/api-keys")
        print("   - NOTION_TOKEN: Get from https://www.notion.so/my-integrations")
        print("   - NOTION_DATABASE_ID: Find in your Notion database URL")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def run_environment_check():
    """Run environment check script"""
    print("Running environment check...")

    if run_command(f"{sys.executable} scripts/check_env.py"):
        print("✅ Environment check passed")
        return True
    else:
        print("⚠️  Environment check failed")
        print("   Make sure you've filled in your .env file with valid API keys")
        return False

def show_next_steps(method):
    """Show next steps to user"""
    print_header("🎉 SETUP COMPLETE!")

    print("\n📋 NEXT STEPS:")

    print("\n1. Activate your virtual environment:")
    if method == "uv":
        if sys.platform == "win32":
            print("   .venv\\Scripts\\activate")
        else:
            print("   source .venv/bin/activate")
    else:
        if sys.platform == "win32":
            print("   venv\\Scripts\\activate")
        else:
            print("   source venv/bin/activate")

    print("\n2. Edit your .env file with real API keys:")
    print("   nano .env  # or use your favorite editor")

    print("\n3. Test your configuration:")
    print(f"   {sys.executable} scripts/check_env.py")
    print(f"   {sys.executable} scripts/test_notion_access.py")

    print("\n4. Add job URLs to your Notion database with 'Processed' = unchecked")

    print("\n5. Run the bot:")
    print("   # Enhanced bot (recommended)")
    print(f"   {sys.executable} -m enhanced_jobbot.enhanced_jobbot")
    print("   # Original bot")
    print(f"   {sys.executable} -m enhanced_jobbot.jobbot")

    if method == "uv":
        print("\n   Or with uv:")
        print("   uv run python -m enhanced_jobbot.enhanced_jobbot")

    print("\n📖 For more information, see README.md")
    print("💡 For Raspberry Pi setup, check the Raspberry Pi section in README.md")

def main():
    """Main setup function"""
    print_header("🤖 Enhanced JobBot Setup")
    print("Welcome! This script will help you set up Enhanced JobBot.")
    print("This automated job application database manager uses AI to extract")
    print("and organize job information in your Notion database.")

    # Check Python version
    print_step(1, "Checking Python version...")
    if not check_python_version():
        sys.exit(1)

    # Check current directory
    if not Path("pyproject.toml").exists():
        print("❌ This doesn't appear to be the Enhanced JobBot project directory")
        print("   Make sure you're running this script from the project root")
        sys.exit(1)

    # Check uv installation
    print_step(2, "Checking package manager...")
    has_uv = check_uv_installation()

    # Create virtual environment
    print_step(3, "Setting up virtual environment...")
    method = create_virtual_environment()
    if not method:
        print("❌ Failed to create virtual environment")
        sys.exit(1)

    # Install dependencies
    print_step(4, "Installing dependencies...")
    if not install_dependencies(method):
        print("❌ Failed to install dependencies")
        sys.exit(1)

    print("✅ Dependencies installed successfully")

    # Setup environment file
    print_step(5, "Setting up environment configuration...")
    setup_environment_file()

    # Show final steps
    show_next_steps(method)

    print("\n🎯 Happy job hunting!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check the error and try again")
        sys.exit(1)
