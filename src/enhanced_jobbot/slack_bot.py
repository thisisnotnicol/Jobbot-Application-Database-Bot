#!/usr/bin/env python3
"""
JobBot Slack Integration - Async-Safe Version
Prevents dispatch_failed errors by running synchronous operations in thread pool

Setup:
1. Create a Slack app at https://api.slack.com/apps
2. Add Bot Token Scopes: app_mentions:read, chat:write, channels:history, groups:history, im:history, mpim:history
3. Subscribe to bot events: app_mention, message.channels, message.groups, message.im, message.mpim
4. Enable Socket Mode and generate an App-Level Token
5. Install app to workspace and get Bot User OAuth Token
6. Set environment variables: SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET

Usage in Slack:
- @jobbot https://example.com/job-posting
- Direct message with just the URL
- Bot will extract job info and create Notion page automatically
"""

import os
import re
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Dict, Any
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from dotenv import load_dotenv

# Import our existing JobBot functionality
import sys
sys.path.append(os.path.dirname(__file__))
from slack_bot_fixed import (
    fetch_job_text,
    extract_fields_robust as extract_fields,
    create_notion_page_robust as create_notion_page,
    find_or_create_company_working as find_or_create_company,
    OPENAI_API_KEY,
    NOTION_TOKEN,
    NOTION_DATABASE_ID
)

# -----------------------------
# Environment Setup
# -----------------------------
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

# Validate required environment variables
missing_vars = []
if not SLACK_BOT_TOKEN: missing_vars.append("SLACK_BOT_TOKEN")
if not SLACK_APP_TOKEN: missing_vars.append("SLACK_APP_TOKEN")
if not OPENAI_API_KEY: missing_vars.append("OPENAI_API_KEY")
if not NOTION_TOKEN: missing_vars.append("NOTION_TOKEN")
if not NOTION_DATABASE_ID: missing_vars.append("NOTION_DATABASE_ID")

if missing_vars:
    print("❌ Missing required environment variables:")
    for var in missing_vars:
        print(f"   - {var}")
    print("\n✅ Add these to your .env file:")
    print(f"   SLACK_BOT_TOKEN=xoxb-...")
    print(f"   SLACK_APP_TOKEN=xapp-...")
    print(f"   OPENAI_API_KEY=sk-...")
    print(f"   NOTION_TOKEN=secret_...")
    print(f"   NOTION_DATABASE_ID=...")
    exit(1)

# -----------------------------
# Logging Setup
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("slack_jobbot_async_safe.log")
    ]
)

logger = logging.getLogger(__name__)

# -----------------------------
# Thread Pool for Blocking Operations
# -----------------------------
# This is crucial for preventing dispatch_failed errors
executor = ThreadPoolExecutor(max_workers=4)

# -----------------------------
# Slack App Setup
# -----------------------------
app = AsyncApp(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

# URL pattern for extracting URLs from messages
URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

# -----------------------------
# Synchronous Processing Function
# -----------------------------
def process_job_sync(url: str) -> Dict[str, Any]:
    """
    Synchronous job processing function to be run in thread pool.
    This keeps all blocking operations out of the async event loop.
    """
    try:
        logger.info(f"Processing job URL (sync): {url}")

        # Step 1: Fetch job content (blocking operation)
        job_text = fetch_job_text(url)
        if not job_text:
            return {
                'success': False,
                'error': 'Could not fetch job content. The page might be protected or inaccessible.'
            }

        logger.info(f"Fetched {len(job_text)} characters from {url}")

        # Step 2: Extract fields using AI (blocking operation)
        fields = extract_fields(job_text)

        logger.info(f"Extracted fields:")
        logger.info(f"  Position: {fields.get('Position', 'Not found')}")
        logger.info(f"  Company: {fields.get('Company', 'Not found')}")
        logger.info(f"  Salary: {fields.get('Salary', 'Not found')}")
        logger.info(f"  Location: {fields.get('Location', [])}")
        logger.info(f"  Commitment: {fields.get('Commitment', 'Not found')}")
        logger.info(f"  Industry: {fields.get('Industry', [])}")

        # Step 3: Create Notion page (blocking operation)
        new_page = create_notion_page(fields, url, job_text)

        if new_page:
            result = {
                'success': True,
                'fields': fields,
                'page_url': new_page.get('url'),
                'page_id': new_page.get('id')
            }
            logger.info(f"Successfully created Notion page: {result['page_url']}")
            return result
        else:
            return {
                'success': False,
                'error': 'Failed to create Notion page. Please check your database configuration.',
                'fields': fields  # Include fields for debugging
            }

    except Exception as e:
        logger.error(f"Error processing job: {e}")
        return {
            'success': False,
            'error': str(e)[:200]
        }

# -----------------------------
# Async Wrapper Functions
# -----------------------------
async def process_job_async(url: str) -> Dict[str, Any]:
    """
    Async wrapper that runs synchronous processing in thread pool.
    This is the key to preventing dispatch_failed errors.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process_job_sync, url)
    return result

# -----------------------------
# Helper Functions
# -----------------------------
def extract_urls_from_text(text: str) -> list:
    """Extract URLs from text"""
    return URL_PATTERN.findall(text)

def is_job_url(url: str) -> bool:
    """Check if URL looks like a job posting"""
    job_keywords = [
        'job', 'career', 'position', 'hiring', 'vacancy', 'employment',
        'opportunities', 'roles', 'apply', 'jobs', 'careers', 'work',
        'posting', 'opening', 'requisition', 'recruitment'
    ]
    url_lower = url.lower()
    return any(keyword in url_lower for keyword in job_keywords)

# -----------------------------
# Slack Message Helpers
# -----------------------------
async def send_processing_message(say, thread_ts: Optional[str] = None) -> Optional[str]:
    """Send processing message and return message timestamp"""
    try:
        msg = await say({
            "text": "🔍 Processing job posting... This may take a moment!",
            "thread_ts": thread_ts,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🔍 *Processing job posting...*\n\n_Fetching content, extracting information, and creating Notion page. This may take 30-60 seconds._"
                    }
                }
            ]
        })
        return msg.get('ts')
    except Exception as e:
        logger.error(f"Error sending processing message: {e}")
        return None

async def update_with_result(say, ts: Optional[str], result: Dict[str, Any]):
    """Update message with processing result"""
    try:
        if result['success']:
            fields = result['fields']
            position = fields.get('Position', 'Position not specified')
            company = fields.get('Company', 'Company not specified')
            salary = fields.get('Salary', 'Not specified')
            location = fields.get('Location', [])
            industry = fields.get('Industry', [])
            commitment = fields.get('Commitment', 'Not specified')

            # Format location and industry
            location_text = ', '.join(location) if isinstance(location, list) and location else 'Not specified'
            industry_text = ', '.join(industry) if isinstance(industry, list) and industry else 'Not specified'

            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *Successfully created Notion page!*\n\n*{position}*\n{company}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Salary:*\n{salary}"},
                        {"type": "mrkdwn", "text": f"*Location:*\n{location_text}"},
                        {"type": "mrkdwn", "text": f"*Type:*\n{commitment}"},
                        {"type": "mrkdwn", "text": f"*Industry:*\n{industry_text}"}
                    ]
                }
            ]

            if result.get('page_url'):
                blocks.append({
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View in Notion"},
                            "url": result['page_url'],
                            "action_id": "view_notion"
                        }
                    ]
                })

            await say({
                "text": f"✅ Successfully created Notion page for {position} at {company}",
                "blocks": blocks,
                "thread_ts": ts,
                "replace_original": False
            })
        else:
            error_msg = result.get('error', 'Unknown error occurred')
            await say({
                "text": f"❌ {error_msg}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ *Processing failed*\n\n{error_msg}"
                        }
                    }
                ],
                "thread_ts": ts,
                "replace_original": False
            })

    except Exception as e:
        logger.error(f"Error updating message: {e}")
        await say({
            "text": "✅ Job processed (check Notion for details)",
            "thread_ts": ts
        })

# -----------------------------
# Slack Event Handlers
# -----------------------------

@app.event("app_mention")
async def handle_app_mention(event, say):
    """
    Handle @jobbot mentions
    Uses async processing to prevent dispatch_failed errors
    """
    try:
        text = event.get('text', '')
        thread_ts = event.get('ts')
        user = event.get('user')

        logger.info(f"App mention from user {user}: {text[:100]}...")

        urls = extract_urls_from_text(text)

        if not urls:
            await say({
                "text": "👋 Hi! I can help you add job postings to Notion. Just mention me with a job URL:\n`@jobbot https://example.com/job-posting`",
                "thread_ts": thread_ts
            })
            return

        # Process each URL
        for url in urls:
            if is_job_url(url):
                # Send processing message
                msg_ts = await send_processing_message(say, thread_ts)

                # Process in thread pool (non-blocking)
                result = await process_job_async(url)

                # Update with result
                await update_with_result(say, msg_ts or thread_ts, result)
            else:
                await say({
                    "text": f"🤔 That doesn't look like a job posting URL. I work best with job/career pages:\n`{url}`",
                    "thread_ts": thread_ts
                })

    except Exception as e:
        logger.error(f"Error in app_mention handler: {e}")
        # Don't crash the handler - just log the error

@app.event("message")
async def handle_message(event, say):
    """
    Handle direct messages
    Uses async processing to prevent dispatch_failed errors
    """
    try:
        # Only process direct messages
        if event.get('channel_type') != 'im':
            return

        # Ignore bot messages
        if event.get('bot_id'):
            return

        text = event.get('text', '')
        user = event.get('user')

        logger.info(f"Direct message from user {user}: {text[:100]}...")

        urls = extract_urls_from_text(text)

        if not urls:
            await say({
                "text": "👋 Hi! Send me a job posting URL and I'll extract the information and add it to your Notion database.\n\nExample: `https://example.com/job-posting`"
            })
            return

        # Process each URL
        for url in urls:
            if is_job_url(url):
                # Send processing message
                msg_ts = await send_processing_message(say)

                # Process in thread pool (non-blocking)
                result = await process_job_async(url)

                # Update with result
                await update_with_result(say, msg_ts, result)
            else:
                # For non-job URLs in DMs, try anyway
                msg_ts = await send_processing_message(say)
                result = await process_job_async(url)
                await update_with_result(say, msg_ts, result)

    except Exception as e:
        logger.error(f"Error in message handler: {e}")
        # Don't crash the handler - just log the error

@app.command("/addjob")
async def handle_addjob_command(ack, command, say):
    """
    Handle /addjob slash command
    Uses async processing to prevent dispatch_failed errors
    """
    try:
        # Acknowledge command immediately to prevent timeout
        await ack()

        text = command.get('text', '').strip()
        user_id = command.get('user_id')

        logger.info(f"Slash command from user {user_id}: /addjob {text[:100]}...")

        if not text:
            await say({
                "text": "Please provide a job URL. Usage: `/addjob https://example.com/job-posting`"
            })
            return

        urls = extract_urls_from_text(text)

        if not urls:
            await say({
                "text": "No URL found. Please provide a job posting URL:\n`/addjob https://example.com/job-posting`"
            })
            return

        # Process the first URL
        url = urls[0]

        # Send processing message
        msg_ts = await send_processing_message(say)

        # Process in thread pool (non-blocking)
        result = await process_job_async(url)

        # Update with result
        await update_with_result(say, msg_ts, result)

    except Exception as e:
        logger.error(f"Error in slash command handler: {e}")
        await say("❌ An error occurred while processing your request. Please try again.")

@app.error
async def handle_errors(error, body, logger_slack):
    """Global error handler"""
    logger.error(f"Slack app error: {error}")
    logger.error(f"Request body: {json.dumps(body, indent=2, default=str)}")

# -----------------------------
# Main Function
# -----------------------------

async def main():
    """Start the Slack bot with async-safe event handling"""
    try:
        handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)

        logger.info("🤖 JobBot Slack Integration (Async-Safe) starting...")
        logger.info("✓ Thread pool for blocking operations")
        logger.info("✓ Prevents dispatch_failed errors")
        logger.info("✓ Robust JSON parsing and error handling")
        logger.info("✓ AI-powered job extraction")
        logger.info("")
        logger.info("Bot features:")
        logger.info("  ✓ Direct message job URLs")
        logger.info("  ✓ @mention with URLs")
        logger.info("  ✓ /addjob slash command")
        logger.info("  ✓ Automatic Notion page creation")
        logger.info("  ✓ Company relation linking")
        logger.info("  ✓ Full job description in toggle blocks")
        logger.info("")
        logger.info("Ready for Slack commands!")
        logger.info("Press Ctrl+C to stop")

        await handler.start_async()

    except Exception as e:
        logger.error(f"Failed to start Slack bot: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Starting JobBot Slack Integration (Async-Safe Version)...")
    print("\n✨ This version prevents dispatch_failed errors by:")
    print("• Running all blocking operations in thread pool")
    print("• Keeping async handlers lightweight and responsive")
    print("• Acknowledging events immediately")
    print("• Comprehensive error handling without crashing handlers")
    print("\n🤖 Bot is ready! Try these in Slack:")
    print("• DM the bot with job URLs")
    print("• @jobbot https://job-url.com")
    print("• /addjob https://job-url.com")
    print("\nPress Ctrl+C to stop")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 JobBot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        logging.exception("Full error details:")
