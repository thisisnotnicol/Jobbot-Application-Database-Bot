#!/usr/bin/env python3
"""
Bulletproof Slack Bot for JobBot
Ultra-reliable version with comprehensive error handling and auto-recovery
"""

import os
import sys
import re
import json
import logging
import asyncio
import signal
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import requests
from bs4 import BeautifulSoup

# Load environment
load_dotenv()

# Configure robust logging
LOG_FILE = "slack_bot_bulletproof.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Validate critical environment variables
missing_vars = []
if not SLACK_BOT_TOKEN: missing_vars.append("SLACK_BOT_TOKEN")
if not SLACK_APP_TOKEN: missing_vars.append("SLACK_APP_TOKEN")

if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# Initialize Slack app with error handling
try:
    app = AsyncApp(token=SLACK_BOT_TOKEN)
    logger.info("Slack app initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Slack app: {e}")
    sys.exit(1)

# Initialize optional services
openai_available = bool(OPENAI_API_KEY)
notion_available = bool(NOTION_TOKEN and NOTION_DATABASE_ID)

logger.info(f"OpenAI integration: {'Enabled' if openai_available else 'Disabled'}")
logger.info(f"Notion integration: {'Enabled' if notion_available else 'Disabled'}")

# Job processing functions with comprehensive error handling
def extract_job_url(text: str) -> Optional[str]:
    """Extract job URL from message text with fallback"""
    try:
        # Enhanced URL pattern
        url_pattern = r'https?://[^\s<>"\{\}\\^`\[\]]+(?:[/?#][^\s<>"\{\}\\^`\[\]]*)?'
        urls = re.findall(url_pattern, text)

        # Job site domains (comprehensive list)
        job_domains = [
            'greenhouse.io', 'lever.co', 'ashbyhq.com', 'workday.com',
            'taleo.net', 'icims.com', 'linkedin.com/jobs', 'indeed.com',
            'glassdoor.com', 'monster.com', 'ziprecruiter.com',
            'careers.', 'jobs.', '/careers', '/jobs'
        ]

        # Prioritize job-specific URLs
        job_urls = []
        other_urls = []

        for url in urls:
            url_clean = url.rstrip('>')
            if any(domain in url_clean.lower() for domain in job_domains):
                job_urls.append(url_clean)
            else:
                other_urls.append(url_clean)

        # Return job URLs first, then any URL
        if job_urls:
            return job_urls[0]
        elif other_urls:
            return other_urls[0]

        return None

    except Exception as e:
        logger.error(f"Error extracting URL from text: {e}")
        return None

def fetch_job_content_safe(url: str, max_retries: int = 3) -> Optional[str]:
    """Safely fetch job content with retries and fallbacks"""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching job content (attempt {attempt + 1}/{max_retries}): {url[:60]}...")

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            # Parse content
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove unnecessary elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()

            # Extract text
            text_content = soup.get_text(separator='\n', strip=True)

            if len(text_content) > 300:  # Minimum viable content
                logger.info(f"Successfully fetched {len(text_content)} characters")
                return text_content[:15000]  # Limit to prevent overflow
            else:
                logger.warning(f"Content too short ({len(text_content)} chars), retrying...")

        except requests.RequestException as e:
            logger.warning(f"Network error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            logger.error(f"Unexpected error fetching content: {e}")
            break

    logger.error(f"Failed to fetch content after {max_retries} attempts")
    return None

def extract_job_info_ai(content: str) -> Dict[str, Any]:
    """Extract job information using AI with fallback"""

    if not openai_available or not content:
        return create_basic_job_info(content)

    try:
        import openai
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = f"""Extract job information from this posting and return ONLY valid JSON:
{{
  "Position": "Job title",
  "Company": "Company name",
  "Summary": "Brief 2-sentence summary",
  "Salary": "Salary range if mentioned",
  "Location": ["Location", "list"],
  "Commitment": "Full-time/Part-time/Contract",
  "Industry": ["Industry", "tags"]
}}

Job text:
{content[:4000]}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )

        ai_response = response.choices[0].message.content
        if not ai_response:
            return create_basic_job_info(content)

        # Clean response
        cleaned = ai_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Parse JSON
        job_info = json.loads(cleaned)
        job_info["Full Description"] = content[:2000]  # Truncate for Notion

        logger.info(f"AI extracted job info for: {job_info.get('Position', 'Unknown')}")
        return job_info

    except Exception as e:
        logger.warning(f"AI extraction failed: {e}")
        return create_basic_job_info(content)

def create_basic_job_info(content: str) -> Dict[str, Any]:
    """Create basic job info when AI fails"""

    lines = content.split('\n') if content else []

    # Try to extract basic info from content
    position = "Unknown Position"
    company = "Unknown Company"

    for line in lines[:15]:
        line = line.strip()
        if len(line) > 10 and len(line) < 100:
            if position == "Unknown Position":
                position = line
            elif company == "Unknown Company" and line != position:
                company = line
                break

    return {
        "Position": position,
        "Company": company,
        "Summary": "Job details available at the provided link",
        "Salary": "",
        "Location": [],
        "Commitment": "Full-time",
        "Industry": [],
        "Full Description": content[:2000] if content else "Content not available"
    }

async def save_to_notion_safe(job_info: Dict[str, Any], url: str) -> bool:
    """Safely save to Notion with error handling"""

    if not notion_available:
        logger.info("Notion not configured - skipping save")
        return False

    try:
        from notion_client import Client as NotionClient

        notion = NotionClient(auth=NOTION_TOKEN)

        # Prepare data for Notion
        description = job_info.get("Full Description", "")[:2000]

        properties = {
            "Position": {"title": [{"text": {"content": job_info.get("Position", "Unknown")[:100]}}]},
            "Company": {"rich_text": [{"text": {"content": job_info.get("Company", "")[:100]}}]},
            "Job URL": {"url": url},
            "Status": {"select": {"name": "New"}},
            "Processed": {"checkbox": True}
        }

        # Add optional fields safely
        if job_info.get("Salary"):
            properties["Salary"] = {"rich_text": [{"text": {"content": job_info["Salary"][:100]}}]}

        if job_info.get("Commitment"):
            properties["Commitment"] = {"multi_select": [{"name": job_info["Commitment"][:100]}]}

        if job_info.get("Location"):
            locations = [{"name": loc[:100]} for loc in job_info["Location"][:5] if loc]
            if locations:
                properties["Location"] = {"multi_select": locations}

        if job_info.get("Industry"):
            industries = [{"name": ind[:100]} for ind in job_info["Industry"][:5] if ind]
            if industries:
                properties["Industry"] = {"multi_select": industries}

        if description:
            properties["Job Description"] = {"rich_text": [{"text": {"content": description}}]}

        # Create page
        page = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties
        )

        logger.info(f"Created Notion page for: {job_info.get('Position')} at {job_info.get('Company')}")
        return True

    except Exception as e:
        logger.error(f"Failed to save to Notion: {e}")
        return False

async def process_job_url(url: str) -> Dict[str, Any]:
    """Process job URL with comprehensive error handling"""

    result = {
        "success": False,
        "job_info": None,
        "notion_saved": False,
        "error": None
    }

    try:
        # Fetch content
        content = fetch_job_content_safe(url)
        if not content:
            result["error"] = "Could not fetch job content"
            return result

        # Extract job info
        job_info = extract_job_info_ai(content)
        result["job_info"] = job_info

        # Save to Notion
        notion_saved = await save_to_notion_safe(job_info, url)
        result["notion_saved"] = notion_saved
        result["success"] = True

        return result

    except Exception as e:
        logger.error(f"Error processing job URL: {e}")
        result["error"] = str(e)
        return result

# Slack event handlers with bulletproof error handling

@app.event("app_mention")
async def handle_app_mention(event, say, ack):
    """Handle @mentions with comprehensive error handling"""

    try:
        await ack()

        user = event.get("user", "")
        text = event.get("text", "")

        logger.info(f"Received mention from user {user}: {text[:100]}...")

        # Extract URL
        url = extract_job_url(text)

        if not url:
            await say(f"Hi <@{user}>! Please share a job posting URL and I'll help you analyze it.")
            return

        # Send processing message
        await say(f"<@{user}> Found a job link! Processing now... 🔍")

        # Process the job
        result = await process_job_url(url)

        if result["success"] and result["job_info"]:
            job_info = result["job_info"]

            # Create response
            response_text = f"""✅ **Job Processed Successfully!**

**Position:** {job_info.get('Position', 'Unknown')}
**Company:** {job_info.get('Company', 'Unknown')}
**Location:** {', '.join(job_info.get('Location', [])) or 'Not specified'}
**Salary:** {job_info.get('Salary') or 'Not specified'}

**Summary:** {job_info.get('Summary', 'Job details available at link')}"""

            if result["notion_saved"]:
                response_text += "\n\n📝 **Saved to Notion database!**"
            else:
                response_text += "\n\n⚠️ Processed but not saved to Notion (check configuration)"

            await say(response_text)

        else:
            error_msg = result.get("error", "Unknown error")
            await say(f"<@{user}> Sorry, I couldn't process that job posting. Error: {error_msg}")

    except Exception as e:
        logger.error(f"Error in app_mention handler: {e}")
        try:
            await ack()
            await say("Sorry, I encountered an error processing your request. Please try again!")
        except Exception as inner_e:
            logger.error(f"Failed to send error message: {inner_e}")

@app.event("message")
async def handle_direct_message(event, say, ack):
    """Handle direct messages"""

    try:
        await ack()

        # Only process DMs
        if event.get("channel_type") != "im":
            return

        text = event.get("text", "")
        user = event.get("user", "")

        # Skip bot messages
        if event.get("bot_id"):
            return

        logger.info(f"Received DM from user {user}: {text[:100]}...")

        # Look for URL
        url = extract_job_url(text)

        if url:
            await say("Processing your job posting... 🔍")

            result = await process_job_url(url)

            if result["success"] and result["job_info"]:
                job_info = result["job_info"]

                response = f"""✅ Job processed!

**{job_info.get('Position', 'Unknown')}** at **{job_info.get('Company', 'Unknown')}**
📍 {', '.join(job_info.get('Location', [])) or 'Location not specified'}
💰 {job_info.get('Salary') or 'Salary not specified'}

{job_info.get('Summary', 'Details available at the job link')}"""

                if result["notion_saved"]:
                    response += "\n\n📝 Saved to your Notion database!"

                await say(response)
            else:
                await say(f"Sorry, I couldn't process that job posting: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Error in direct message handler: {e}")
        try:
            await ack()
        except:
            pass

# Main application with robust startup and error handling

class BulletproofSlackBot:
    """Main bot class with enhanced reliability"""

    def __init__(self):
        self.handler = None
        self.running = False
        self.restart_count = 0
        self.max_restarts = 10

    async def start(self):
        """Start the bot with error recovery"""

        logger.info("Starting Bulletproof Slack Bot...")
        logger.info(f"OpenAI: {'Enabled' if openai_available else 'Disabled'}")
        logger.info(f"Notion: {'Enabled' if notion_available else 'Disabled'}")

        self.handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)
        self.running = True

        while self.running and self.restart_count < self.max_restarts:
            try:
                logger.info(f"Bot startup attempt {self.restart_count + 1}")
                await self.handler.start_async()

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                break

            except Exception as e:
                self.restart_count += 1
                logger.error(f"Bot crashed (attempt {self.restart_count}): {e}")

                if self.restart_count < self.max_restarts:
                    wait_time = min(60, 10 * self.restart_count)
                    logger.info(f"Restarting in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max restart attempts reached. Exiting.")
                    break

        logger.info("Bot stopped")

    def stop(self):
        """Stop the bot gracefully"""
        logger.info("Stopping bot...")
        self.running = False

# Signal handlers for graceful shutdown
bot_instance = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    if bot_instance:
        bot_instance.stop()

async def main():
    """Main entry point"""
    global bot_instance

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and start bot
    bot_instance = BulletproofSlackBot()

    try:
        await bot_instance.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)
