"""
Enhanced JobBot - Automated Job Application Database Manager

An intelligent Python bot that automatically scrapes job postings, extracts
structured data using AI, and populates your Notion database with comprehensive
job information.

Features:
- Web scraping with Playwright and BeautifulSoup
- AI-powered data extraction using OpenAI GPT
- Notion database integration
- AI-generated job summaries
- Complete job description preservation
- Smart text handling and field management
"""

__version__ = "1.0.0"
__author__ = "Nicole Eid"
__email__ = "hello@nicoleeid.me"

from .enhanced_jobbot import main as enhanced_main
from .jobbot import main as original_main

# Default to enhanced version
main = enhanced_main

__all__ = ["main", "enhanced_main", "original_main"]
