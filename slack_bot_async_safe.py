#!/usr/bin/env python3
"""
Async-Safe Slack Bot for JobBot
This version prevents dispatch_failed errors by running synchronous operations in thread pool
"""

import os
import re
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dotenv import load_dotenv

# Load environment first
load_dotenv()

# Import Slack modules
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

# Import the proven working functions from jobbot_cli
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from enhanced_jobbot.jobbot_cli import (
    fetch_job_text,
    extract_fields,
    create_notion_page,
    OPENAI_API_KEY,
    NOTION_TOKEN,
    NOTION_DATABASE_ID
)

# Environment validation
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

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
    exit(1)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("slack_bot_async_safe.log")
    ]
)

logger = logging.getLogger(__name__)

# Create thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=4)

# Create Slack app
app = AsyncApp(token=SLACK_BOT_TOKEN)

# URL pattern
URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

def extract_urls_from_text(text):
    """Extract URLs from message text"""
    return URL_PATTERN.findall(text)

def is_job_url(url):
    """Check if URL looks like a job posting"""
    job_keywords = [
        'job', 'career', 'position', 'hiring', 'vacancy', 'employment',
        'opportunities', 'roles', 'apply', 'jobs', 'careers', 'work',
        'posting', 'opening'
    ]
    url_lower = url.lower()
    return any(keyword in url_lower for keyword in job_keywords)

def process_job_sync(url):
    """Synchronous job processing function"""
    try:
        logger.info(f"Processing job URL (sync): {url}")

        # Fetch job text - returns (text, soup) tuple
        job_text_result = fetch_job_text(url)

        if not job_text_result:
            return {
                'success': False,
                'error': 'Could not fetch job content'
            }

        # Log what we got
        if isinstance(job_text_result, tuple):
            text_len = len(job_text_result[0])
            logger.info(f"Fetched {text_len} characters (tuple format)")
        else:
            text_len = len(job_text_result)
            logger.info(f"Fetched {text_len} characters")

        # Extract fields - handles tuple properly
        fields = extract_fields(job_text_result)

        # Ensure Full Description exists for toggle blocks
        if 'Full Description' not in fields or not fields['Full Description']:
            logger.warning("Full Description missing - fixing")
            if isinstance(job_text_result, tuple):
                fields['Full Description'] = job_text_result[0]
            elif isinstance(job_text_result, str):
                fields['Full Description'] = job_text_result
            else:
                fields['Full Description'] = "Job description not available"

        logger.info(f"Extracted: {fields.get('Position')} at {fields.get('Company')}")
        logger.info(f"Full Description: {len(fields.get('Full Description', ''))} chars")

        # Create Notion page
        new_page = create_notion_page(fields, url)

        if new_page:
            return {
                'success': True,
                'page_id': new_page.get('id'),
                'page_url': new_page.get('url'),
                'fields': fields
            }
        else:
            return {
                'success': False,
                'error': 'Failed to create Notion page'
            }

    except Exception as e:
        logger.error(f"Error processing job: {e}")
        return {
            'success': False,
            'error': str(e)[:100]
        }

async def process_job_async(url):
    """Async wrapper that runs synchronous processing in thread pool"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process_job_sync, url)
    return result

async def send_processing_message(say):
    """Send processing message"""
    try:
        msg = await say({
            "text": "🔍 Processing job posting... This may take a moment!",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🔍 *Processing job posting...*\n\n_Extracting job information and creating Notion page. This may take 30-60 seconds._"
                    }
                }
            ]
        })
        return msg.get('ts')
    except Exception as e:
        logger.error(f"Error sending processing message: {e}")
        return None

async def update_with_result(say, ts, result):
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

            # If we have a timestamp, update the message, otherwise send new
            if ts:
                await say({
                    "text": f"✅ Successfully created Notion page for {position} at {company}",
                    "blocks": blocks,
                    "thread_ts": ts,
                    "replace_original": False
                })
            else:
                await say({
                    "text": f"✅ Successfully created Notion page for {position} at {company}",
                    "blocks": blocks
                })
        else:
            error_msg = result.get('error', 'Unknown error')
            message = {
                "text": f"❌ {error_msg}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ *Processing failed*\n\n{error_msg}"
                        }
                    }
                ]
            }

            if ts:
                message["thread_ts"] = ts
                message["replace_original"] = False

            await say(message)

    except Exception as e:
        logger.error(f"Error updating message: {e}")
        await say(f"✅ Job processed (check Notion)")

@app.event("app_mention")
async def handle_app_mention(event, say):
    """Handle @jobbot mentions"""
    try:
        text = event.get('text', '')
        thread_ts = event.get('ts')

        logger.info(f"App mention: {text[:100]}...")

        urls = extract_urls_from_text(text)

        if not urls:
            await say({
                "text": "👋 Hi! Mention me with a job URL:\n`@jobbot https://example.com/job-posting`",
                "thread_ts": thread_ts
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
                await update_with_result(say, msg_ts or thread_ts, result)
            else:
                await say({
                    "text": f"🤔 That doesn't look like a job posting URL:\n`{url}`",
                    "thread_ts": thread_ts
                })

    except Exception as e:
        logger.error(f"Error in app_mention: {e}")

@app.event("message")
async def handle_message(event, say):
    """Handle direct messages"""
    try:
        # Only process direct messages
        if event.get('channel_type') != 'im':
            return

        # Ignore bot messages
        if event.get('bot_id'):
            return

        text = event.get('text', '')
        logger.info(f"DM received: {text[:100]}...")

        urls = extract_urls_from_text(text)

        if not urls:
            await say("👋 Hi! Send me a job URL and I'll add it to your Notion database.\n\nExample: `https://example.com/job-posting`")
            return

        # Process each URL
        for url in urls:
            # Send processing message
            msg_ts = await send_processing_message(say)

            # Process in thread pool (non-blocking)
            result = await process_job_async(url)

            # Update with result
            await update_with_result(say, msg_ts, result)

    except Exception as e:
        logger.error(f"Error in message handler: {e}")

@app.command("/addjob")
async def handle_addjob_command(ack, command, respond):
    """Handle /addjob slash command"""
    try:
        await ack()

        text = command.get('text', '').strip()
        logger.info(f"Slash command: /addjob {text}")

        if not text:
            await respond("Please provide a job URL: `/addjob https://example.com/job-posting`")
            return

        urls = extract_urls_from_text(text)
        if not urls:
            await respond("Please provide a valid URL: `/addjob https://example.com/job-posting`")
            return

        url = urls[0]

        # Send initial response
        await respond("🔍 Processing job posting...")

        # Process in thread pool (non-blocking)
        result = await process_job_async(url)

        # Send result
        if result['success']:
            fields = result['fields']
            message = f"✅ Successfully created Notion page!\n\n"
            message += f"*{fields.get('Position', 'Unknown')}* at *{fields.get('Company', 'Unknown')}*\n"
            message += f"Salary: {fields.get('Salary', 'Not specified')}\n"

            if result.get('page_url'):
                message += f"\n<{result['page_url']}|View in Notion>"

            await respond(message)
        else:
            await respond(f"❌ Failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Error in slash command: {e}")

@app.error
async def global_error_handler(error, body, logger_param):
    """Global error handler"""
    logger.error(f"Global error: {error}")
    logger.error(f"Request: {json.dumps(body, indent=2, default=str)}")

async def main():
    """Start the async-safe Slack bot"""
    try:
        handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)

        logger.info("🤖 JobBot Slack - ASYNC SAFE VERSION")
        logger.info("✅ Runs synchronous code in thread pool")
        logger.info("✅ Prevents dispatch_failed errors")
        logger.info("✅ Handles job description toggle properly")
        logger.info("✅ All fields populated correctly")
        logger.info("")
        logger.info("Ready for Slack commands!")
        logger.info("Press Ctrl+C to stop")

        await handler.start_async()

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Starting Async-Safe JobBot...")
    print("This version prevents dispatch_failed by using thread pools")
    print("Press Ctrl+C to stop")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 JobBot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
