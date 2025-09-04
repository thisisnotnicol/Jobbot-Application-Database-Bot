#!/usr/bin/env python3
"""
JobBot - Simple command line tool to add job postings to Notion

Usage:
    python add_job.py "https://example.com/job-posting"
"""

import sys
import os

# Add the src directory to Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from enhanced_jobbot.jobbot_cli import main

    if __name__ == "__main__":
        main()

except ImportError as e:
    print("❌ Error importing JobBot CLI module")
    print(f"   {e}")
    print("\nMake sure you're running this from the jobbot_clean directory")
    print("and that all dependencies are installed:")
    print("   pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
