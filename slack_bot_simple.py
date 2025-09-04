#!/usr/bin/env python3
"""
Simple Slack Bot for JobBot
Uses the proven jobbot_cli functions in a minimal async wrapper to avoid dispatch_failed errors
"""

import os
import re
import logging
import asyncio
from datetime import datetime
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from dotenv import load_dotenv

# Import working functions from jobbot_cli
import sys
src_dir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_dir)

try:
    from enhanced_jobbot.jobbot_cli import fetch_job_text, extract_fields, create_notion_page
    print("✅ Successfully imported working jobbot_cli functions")
except ImportError as e:
    print(f"❌ Failed to import jobbot_cli: {e}")
    sys.exit(1)

# Environment setup
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    print("❌ Missing Slack tokens")
    sys.exit(1)

# Simple logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("slack_bot_simple.log")
    ]
)

logger = logging.getLogger(__name__)

# Create app
app = AsyncApp(token=SLACK_BOT_TOKEN)

# URL regex
URL_PATTERN = re.compile(r'http[s]?://[^\s<>"]{1,}')

def extract_urls(text):
    """Extract URLs from text"""
    return URL_PATTERN.findall(text)

def is_job_url(url):
    """Simple check if URL looks like a job posting"""
    job_keywords = ['job', 'career', 'position', 'hiring', 'work', 'apply']
    url_lower = url.lower()
    return any(keyword in url_lower for keyword in job_keywords)

async def process_job_safely(url, say, logger):
    """Process job URL using working jobbot_cli functions"""
    try:
        # Send processing message
        await say("🔍 Processing job posting... This may take a moment!")
        logger.info(f"Processing: {url}")

        # Use working jobbot_cli functions (these work synchronously)
        job_text = fetch_job_text(url)

        if not job_text:
            await say("❌ Could not fetch job content. Please check the URL.")
            return

        logger.info(f"Fetched {len(job_text)} characters")

        # Extract fields using working function
        fields = extract_fields(job_text)
        logger.info(f"Extracted fields: {fields}")

        # Create Notion page using working function
        new_page = create_notion_page(fields, url)

        if new_page:
            # Success message
            position = fields.get('Position', 'Unknown Position')
            company = fields.get('Company', 'Unknown Company')
            salary = fields.get('Salary', 'Not specified')
            location = fields.get('Location', [])

            location_str = ', '.join(location) if isinstance(location, list) else str(location)
            if not location_str:
                location_str = 'Not specified'

            success_msg = f"✅ **Job Added to Notion!**\n\n"
            success_msg += f"**Position:** {position}\n"
            success_msg += f"**Company:** {company}\n"
            success_msg += f"**Salary:** {salary}\n"
            success_msg += f"**Location:** {location_str}\n"

            if new_page.get('url'):
                success_msg += f"\n🔗 [View in Notion]({new_page['url']})"

            await say(success_msg)
            logger.info(f"Successfully processed: {url}")
        else:
            await say("❌ Failed to create Notion page. Please check your database configuration.")

    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        await say(f"❌ Error processing job: {str(e)[:100]}...")

@app.event("app_mention")
async def handle_mention(event, say, logger):
    """Handle @mentions"""
    try:
        text = event.get('text', '')
        urls = extract_urls(text)

        if not urls:
            await say("👋 Hi! Mention me with a job URL and I'll add it to Notion:\n`@jobbot https://job-url.com`")
            return

        for url in urls:
            if is_job_url(url):
                await process_job_safely(url, say, logger)
            else:
                await say(f"🤔 That doesn't look like a job URL: {url}")

    except Exception as e:
        logger.error(f"Error in mention handler: {e}")
        try:
            await say("❌ Sorry, I encountered an error. Please try again.")
        except:
            pass

@app.event("message")
async def handle_message(event, say, logger):
    """Handle direct messages"""
    try:
        # Only handle DMs
        if event.get('channel_type') != 'im':
            return

        # Ignore bot messages
        if event.get('bot_id'):
            return

        text = event.get('text', '')
        urls = extract_urls(text)

        if not urls:
            await say("👋 Hi! Send me a job URL and I'll add it to your Notion database.\n\nExample: `https://example.com/job-posting`")
            return

        for url in urls:
            await process_job_safely(url, say, logger)

    except Exception as e:
        logger.error(f"Error in message handler: {e}")
        try:
            await say("❌ Sorry, I encountered an error. Please try again.")
        except:
            pass

@app.command("/addjob")
async def handle_slash_command(ack, command, respond, logger):
    """Handle /addjob slash command"""
    try:
        await ack()

        text = command.get('text', '').strip()

        if not text:
            await respond("Please provide a job URL: `/addjob https://example.com/job`")
            return

        urls = extract_urls(text)
        if not urls:
            await respond("Please provide a valid URL: `/addjob https://example.com/job`")
            return

        url = urls[0]
        await respond("🔍 Processing job posting...")

        # Use a simple response function for slash commands
        async def slash_say(message):
            await respond(message)

        await process_job_safely(url, slash_say, logger)

    except Exception as e:
        logger.error(f"Error in slash command: {e}")
        try:
            await respond("❌ Error processing command. Please try again.")
        except:
            pass

@app.error
async def global_error_handler(error, body, logger):
    """Global error handler"""
    logger.error(f"Global error: {error}")
    logger.error(f"Request body: {body}")

async def main():
    """Start the simple bot"""
    try:
        handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)

        logger.info("🤖 Simple JobBot starting...")
        logger.info("✓ Uses proven jobbot_cli functions")
        logger.info("✓ Minimal async complexity")
        logger.info("✓ Robust error handling")
        logger.info("")
        logger.info("Ready for:")
        logger.info("• Direct messages with job URLs")
        logger.info("• @mentions: @jobbot https://job-url.com")
        logger.info("• Slash commands: /addjob https://job-url.com")

        await handler.start_async()

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Starting Simple JobBot...")
    print("Uses the working jobbot_cli functions with minimal async wrapper")
    print("Press Ctrl+C to stop")
    print("-" * 50)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
