#!/Users/nicoleeid/jobbot_clean/venv/bin/python3
"""
Robust Slack Bot Runner with Auto-Recovery
Handles dispatch failures and ensures continuous operation
"""

import os
import sys
import json
import logging
import asyncio
import signal
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import openai
from notion_client import Client as NotionClient

# -----------------------------
# Environment Setup
# -----------------------------
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('slack_bot_runtime.log'),
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

# Validate environment
def validate_environment():
    """Check all required environment variables"""
    missing = []
    if not SLACK_BOT_TOKEN: missing.append("SLACK_BOT_TOKEN")
    if not SLACK_APP_TOKEN: missing.append("SLACK_APP_TOKEN")

    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please check your .env file")
        return False

    # Optional services
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set - AI features will be limited")
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        logger.warning("Notion credentials not set - Notion integration disabled")

    return True

# Initialize Slack app
app = AsyncApp(token=SLACK_BOT_TOKEN)

# Initialize optional services
openai_client = None
notion_client = None

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    from openai import OpenAI
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

if NOTION_TOKEN and NOTION_DATABASE_ID:
    notion_client = NotionClient(auth=NOTION_TOKEN)

# -----------------------------
# Job Processing Functions
# -----------------------------

def extract_job_url(text: str) -> Optional[str]:
    """Extract job URL from message text"""
    import re
    url_pattern = r'https?://[^\s<>"\{\}\\^`\[\]]+(?:[/?#][^\s<>"\{\}\\^`\[\]]*)?'
    urls = re.findall(url_pattern, text)

    job_domains = [
        'greenhouse.io', 'lever.co', 'ashbyhq.com',
        'workday.com', 'taleo.net', 'icims.com',
        'linkedin.com/jobs', 'indeed.com', 'notion.so'
    ]

    for url in urls:
        if any(domain in url for domain in job_domains):
            return url.rstrip('>')

    return urls[0] if urls else None

def fetch_job_content(url: str) -> Optional[str]:
    """Fetch job posting content with multiple fallback methods"""
    try:
        # Method 1: Simple requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text(separator='\n', strip=True)

        if len(text) > 500:  # Minimum viable content
            return text[:15000]  # Limit to prevent token overflow

    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")

    return None

def parse_job_with_ai(content: str) -> Dict[str, Any]:
    """Parse job content using OpenAI with robust fallback"""
    if not openai_client or not content:
        return create_fallback_fields(content)

    prompt = f"""Extract the following information from this job posting and return ONLY valid JSON:
{{
  "Position": "Job title",
  "Company": "Company name",
  "Summary": "A 2-3 sentence summary of the role",
  "Salary": "Salary range if mentioned",
  "Location": ["List", "of", "locations"],
  "Commitment": "Full-time, Part-time, Contract, etc",
  "Industry": ["Tech", "Finance", etc]
}}

Job posting:
{content[:3000]}"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )

        text = response.choices[0].message.content
        if not text:
            return create_fallback_fields(content)

        # Clean response
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        fields = json.loads(text)
        fields["Full Description"] = content[:2000]  # Truncate for Notion limit
        return fields

    except Exception as e:
        logger.warning(f"AI parsing failed: {e}")
        return create_fallback_fields(content)

def create_fallback_fields(content: str) -> Dict[str, Any]:
    """Create basic fields when AI parsing fails"""
    lines = content.split('\n') if content else []
    title = "Unknown Position"
    company = "Unknown Company"

    # Try to extract title and company from first few lines
    for line in lines[:10]:
        if len(line) > 10 and len(line) < 100:
            if not title or title == "Unknown Position":
                title = line.strip()
            elif not company or company == "Unknown Company":
                company = line.strip()
                break

    return {
        "Position": title,
        "Company": company,
        "Summary": "Job details available at the link",
        "Salary": "",
        "Location": [],
        "Commitment": "Full-time",
        "Industry": [],
        "Full Description": (content[:1997] + "...") if content and len(content) > 2000 else (content or "")
    }

async def save_to_notion(fields: Dict[str, Any], url: str) -> bool:
    """Save job to Notion with proper error handling"""
    if not notion_client or not NOTION_DATABASE_ID:
        logger.warning("Notion not configured")
        return False

    try:
        # Ensure description fits Notion's limit
        description = fields.get("Full Description", "")
        if len(description) > 2000:
            description = description[:1997] + "..."

        # Create Notion page
        notion_client.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Position": {"title": [{"text": {"content": fields.get("Position", "Unknown")[:100]}}]},
                "Company": {"rich_text": [{"text": {"content": fields.get("Company", "")[:100]}}]},
                "Status": {"select": {"name": "Researching"}},
                "Active v Archived": {"status": {"name": "In progress"}},
                "Job URL": {"url": url},
                "Salary": {"rich_text": [{"text": {"content": fields.get("Salary", "")[:100]}}]},
                "Commitment": {"multi_select": [{"name": fields.get("Commitment", "Full-time")}]},
                "Location": {"multi_select": [{"name": loc[:100]} for loc in fields.get("Location", [])][:5]},
                "Industry": {"multi_select": [{"name": ind[:100]} for ind in fields.get("Industry", [])][:5]},
                "Job Description": {"rich_text": [{"text": {"content": description}}]},
                "Processed": {"checkbox": True}
            }
        )
        logger.info(f"Added to Notion: {fields.get('Position')} at {fields.get('Company')}")
        return True

    except Exception as e:
        logger.error(f"Failed to save to Notion: {e}")
        return False

# -----------------------------
# Slack Event Handlers
# -----------------------------

@app.event("app_mention")
async def handle_mention(event, say, ack):
    """Handle @mentions of the bot"""
    try:
        await ack()

        text = event.get("text", "")
        user = event.get("user", "")

        # Extract URL from message
        url = extract_job_url(text)

        if url:
            await say(f"<@{user}> I found a job link! Let me process that for you... 🔍")

            # Fetch job content
            content = fetch_job_content(url)
            if not content:
                await say(f"Sorry <@{user}>, I couldn't fetch the job posting. The site might require login or have anti-bot measures.")
                return

            # Parse with AI
            fields = parse_job_with_ai(content)

            # Save to Notion
            notion_saved = await save_to_notion(fields, url)

            # Respond with summary
            response = f"""✅ **Job Processed!**
**Position:** {fields.get('Position', 'Unknown')}
**Company:** {fields.get('Company', 'Unknown')}
**Summary:** {fields.get('Summary', 'No summary available')}
**Location:** {', '.join(fields.get('Location', [])) or 'Not specified'}
**Salary:** {fields.get('Salary') or 'Not specified'}"""

            if notion_saved:
                response += "\n\n📝 Saved to your Notion database!"

            await say(response)
        else:
            await say(f"Hi <@{user}>! Send me a job posting URL and I'll help you analyze it. Just mention me with the link!")

    except Exception as e:
        logger.error(f"Error in handle_mention: {e}", exc_info=True)
        try:
            await ack()
            await say("Sorry, I encountered an error. Please try again!")
        except:
            pass

@app.event("message")
async def handle_message(event, ack):
    """Handle direct messages"""
    try:
        await ack()

        # Only process DMs
        if event.get("channel_type") == "im":
            text = event.get("text", "")
            url = extract_job_url(text)

            if url:
                # Process similar to mention handler
                logger.info(f"Processing URL from DM: {url}")

    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await ack()

# -----------------------------
# Main Application
# -----------------------------

async def run_bot():
    """Run the Slack bot with auto-recovery"""
    if not validate_environment():
        logger.error("Environment validation failed. Exiting.")
        return

    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)

    logger.info("Starting JobBot Slack integration...")
    logger.info(f"Notion integration: {'Enabled' if notion_client else 'Disabled'}")
    logger.info(f"AI parsing: {'Enabled' if openai_client else 'Disabled (using fallback)'}")

    retry_count = 0
    max_retries = 5

    while retry_count < max_retries:
        try:
            await handler.start_async()

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            break

        except Exception as e:
            retry_count += 1
            logger.error(f"Bot crashed (attempt {retry_count}/{max_retries}): {e}")

            if retry_count < max_retries:
                wait_time = min(30 * retry_count, 300)  # Max 5 min wait
                logger.info(f"Restarting in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("Max retries reached. Exiting.")
                break

    logger.info("JobBot Slack integration stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}. Shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the bot
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
