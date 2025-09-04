#!/usr/bin/env python3
"""
Working Slack Bot for JobBot - Complete Fix
This is a comprehensive rewrite that fixes all issues at once:
- Uses proven jobbot_cli functions
- Minimal async complexity to avoid dispatch_failed
- All field mappings working (company, salary, location, industry, job description toggle)
- Robust error handling
- No breaking changes between fixes
"""

import os
import re
import json
import logging
import asyncio
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
    find_or_create_company,
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
        logging.FileHandler("slack_bot_working.log")
    ]
)

logger = logging.getLogger(__name__)

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

async def send_processing_message(say):
    """Send processing message"""
    try:
        await say({
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
    except Exception as e:
        logger.error(f"Error sending processing message: {e}")
        await say("🔍 Processing job posting...")

async def send_success_message(say, fields, notion_url):
    """Send success message with job details"""
    try:
        position = fields.get('Position', 'Position not specified')
        company = fields.get('Company', 'Company not specified')
        salary = fields.get('Salary', 'Not specified')
        location = fields.get('Location', [])
        industry = fields.get('Industry', [])
        commitment = fields.get('Commitment', 'Not specified')

        # Format location
        if isinstance(location, list):
            location_text = ', '.join(location) if location else 'Not specified'
        else:
            location_text = str(location) if location else 'Not specified'

        # Format industry
        if isinstance(industry, list):
            industry_text = ', '.join(industry) if industry else 'Not specified'
        else:
            industry_text = str(industry) if industry else 'Not specified'

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
                    {
                        "type": "mrkdwn",
                        "text": f"*Salary:*\n{salary}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Location:*\n{location_text}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:*\n{commitment}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Industry:*\n{industry_text}"
                    }
                ]
            }
        ]

        if notion_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Notion"
                        },
                        "url": notion_url,
                        "action_id": "view_notion_page"
                    }
                ]
            })

        await say({
            "text": f"✅ Successfully created Notion page for {position} at {company}",
            "blocks": blocks
        })

    except Exception as e:
        logger.error(f"Error sending success message: {e}")
        await say(f"✅ Successfully created Notion page for {fields.get('Position', 'this job')}!")

async def send_error_message(say, error_msg):
    """Send error message"""
    try:
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
            ]
        })
    except Exception as e:
        logger.error(f"Error sending error message: {e}")
        await say(f"❌ {error_msg}")

async def process_job_url(url, say):
    """Process job URL using the proven working functions"""
    try:
        logger.info(f"Processing job URL: {url}")

        # Send processing message
        await send_processing_message(say)

        # Use the proven working functions from jobbot_cli
        # These functions are synchronous and work perfectly
        # fetch_job_text returns (text, soup) tuple
        job_text_result = fetch_job_text(url)

        if not job_text_result:
            await send_error_message(say, "Could not fetch job content. The page might be behind authentication or not accessible.")
            return

        # Handle both tuple and string returns
        if isinstance(job_text_result, tuple):
            text_len = len(job_text_result[0])
            logger.info(f"Fetched {text_len} characters from {url} (tuple format)")
        else:
            text_len = len(job_text_result)
            logger.info(f"Fetched {text_len} characters from {url}")

        # Extract fields using the working function - it handles tuples properly
        fields = extract_fields(job_text_result)

        logger.info(f"Extracted fields:")
        logger.info(f"  Position: {fields.get('Position', 'Not found')}")
        logger.info(f"  Company: {fields.get('Company', 'Not found')}")
        logger.info(f"  Salary: {fields.get('Salary', 'Not found')}")
        logger.info(f"  Location: {fields.get('Location', 'Not found')}")
        logger.info(f"  Industry: {fields.get('Industry', 'Not found')}")
        logger.info(f"  Commitment: {fields.get('Commitment', 'Not found')}")
        logger.info(f"  Full Description: {len(fields.get('Full Description', ''))} chars")

        # Ensure Full Description exists for toggle blocks
        if 'Full Description' not in fields or not fields['Full Description']:
            logger.warning("Full Description missing - attempting to fix")
            if isinstance(job_text_result, tuple):
                fields['Full Description'] = job_text_result[0]
            elif isinstance(job_text_result, str):
                fields['Full Description'] = job_text_result
            else:
                fields['Full Description'] = "Job description not available"
            logger.info(f"Fixed Full Description: {len(fields['Full Description'])} chars")

        # Create Notion page using the working function
        new_page = create_notion_page(fields, url)

        if new_page:
            notion_url = new_page.get('url')
            await send_success_message(say, fields, notion_url)
            logger.info(f"Successfully processed {url} and created Notion page: {new_page.get('id')}")
        else:
            await send_error_message(say, "Failed to create Notion page. Please check your database configuration and permissions.")

    except Exception as e:
        logger.error(f"Error processing job URL {url}: {e}")
        await send_error_message(say, f"Unexpected error: {str(e)[:100]}...")

# Event handlers with minimal complexity
@app.event("app_mention")
async def handle_app_mention(event, say):
    """Handle @jobbot mentions"""
    try:
        text = event.get('text', '')
        logger.info(f"App mention received: {text[:100]}...")

        urls = extract_urls_from_text(text)

        if not urls:
            await say("👋 Hi! I can help you add job postings to Notion. Just mention me with a job URL:\n`@jobbot https://example.com/job-posting`")
            return

        # Process each URL
        for url in urls:
            if is_job_url(url):
                await process_job_url(url, say)
            else:
                await say(f"🤔 That doesn't look like a job posting URL. I work best with job/career pages:\n`{url}`")

    except Exception as e:
        logger.error(f"Error in app_mention handler: {e}")
        try:
            await say("❌ Sorry, I encountered an error processing your request. Please try again.")
        except:
            logger.error("Failed to send error message for app_mention")

@app.event("message")
async def handle_message(event, say):
    """Handle direct messages"""
    try:
        # Only process direct messages
        channel_type = event.get('channel_type', '')
        if channel_type != 'im':
            return

        # Ignore bot messages
        if event.get('bot_id'):
            return

        text = event.get('text', '')
        logger.info(f"Direct message received: {text[:100]}...")

        urls = extract_urls_from_text(text)

        if not urls:
            await say("👋 Hi! Send me a job posting URL and I'll extract the information and add it to your Notion database.\n\nExample: `https://example.com/job-posting`")
            return

        # Process each URL
        for url in urls:
            await process_job_url(url, say)

    except Exception as e:
        logger.error(f"Error in message handler: {e}")
        try:
            await say("❌ Sorry, I encountered an error processing your message. Please try again.")
        except:
            logger.error("Failed to send error message for direct message")

@app.command("/addjob")
async def handle_addjob_command(ack, command, respond):
    """Handle /addjob slash command"""
    try:
        await ack()

        text = command.get('text', '').strip()
        logger.info(f"Slash command received: /addjob {text}")

        if not text:
            await respond("Please provide a job URL: `/addjob https://example.com/job-posting`")
            return

        urls = extract_urls_from_text(text)
        if not urls:
            await respond("Please provide a valid URL: `/addjob https://example.com/job-posting`")
            return

        # For slash commands, we need to use respond instead of say
        async def respond_wrapper(message):
            if isinstance(message, dict):
                await respond(message)
            else:
                await respond(message)

        # Process the first URL
        url = urls[0]
        await process_job_url(url, respond_wrapper)

    except Exception as e:
        logger.error(f"Error in slash command handler: {e}")
        try:
            await respond("❌ Sorry, I encountered an error processing your command. Please try again.")
        except:
            logger.error("Failed to send error response for slash command")

@app.error
async def global_error_handler(error, body, logger_param):
    """Global error handler to catch any unhandled errors"""
    logger.error("=== GLOBAL ERROR HANDLER ===")
    logger.error(f"Error: {error}")
    logger.error(f"Error type: {type(error)}")
    logger.error(f"Body: {json.dumps(body, indent=2, default=str)}")
    logger.error("=== END GLOBAL ERROR ===")

async def main():
    """Start the Slack bot"""
    try:
        # Create socket mode handler
        handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)

        logger.info("🤖 JobBot Slack Integration - WORKING VERSION")
        logger.info("=" * 60)
        logger.info("✅ Uses proven jobbot_cli functions")
        logger.info("✅ Creates complete Notion pages with:")
        logger.info("   • Position, Company, Salary fields")
        logger.info("   • Location, Industry, Commitment multi-select tags")
        logger.info("   • Job Description toggle blocks with full content")
        logger.info("   • Company relation linking")
        logger.info("   • Proper Status and Processed field values")
        logger.info("")
        logger.info("🎯 Ready to process job URLs via:")
        logger.info("   • Direct messages: Send job URLs to @jobbot")
        logger.info("   • Channel mentions: @jobbot https://job-url.com")
        logger.info("   • Slash commands: /addjob https://job-url.com")
        logger.info("")
        logger.info("Press Ctrl+C to stop")
        logger.info("-" * 60)

        # Start the bot
        await handler.start_async()

    except Exception as e:
        logger.error(f"Error starting Slack bot: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Starting JobBot Slack Integration - WORKING VERSION")
    print("=" * 60)
    print("This version uses the proven jobbot_cli functions with minimal")
    print("async wrapper to avoid dispatch_failed errors while maintaining")
    print("all functionality:")
    print("")
    print("✅ Company name linking to relations")
    print("✅ Salary field population")
    print("✅ Location and Industry multi-select tags")
    print("✅ Job Description toggle blocks with full content")
    print("✅ All field mappings working correctly")
    print("✅ Robust error handling")
    print("")
    print("Ready for Slack! Press Ctrl+C to stop")
    print("-" * 60)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 JobBot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        logging.exception("Full error details:")
