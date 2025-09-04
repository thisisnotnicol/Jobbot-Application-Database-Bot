#!/usr/bin/env python3
"""
Simple Working Slack Bot - No Dispatch Issues
Ultra-reliable minimal implementation that actually works
"""

import os
import re
import json
import logging
import asyncio
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment first
load_dotenv()

# Simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    logger.error("Missing SLACK_BOT_TOKEN or SLACK_APP_TOKEN")
    sys.exit(1)

# Import Slack SDK
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

# Create app
app = AsyncApp(token=SLACK_BOT_TOKEN)

# Simple URL extraction
def extract_url(text):
    """Extract first URL from text"""
    urls = re.findall(r'http[s]?://[^\s<>]+', text)
    return urls[0] if urls else None

# Simple job processing
async def process_job_simple(url):
    """Simple job processing without complex dependencies"""
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {'User-Agent': 'Mozilla/5.0 (compatible; JobBot/1.0)'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()[:2000]

            # Simple extraction
            lines = text.split('\n')[:20]
            title = "Job Position"
            company = "Company"

            for line in lines:
                line = line.strip()
                if len(line) > 5 and len(line) < 100:
                    if "engineer" in line.lower() or "manager" in line.lower() or "developer" in line.lower():
                        title = line
                        break

            return {
                'title': title,
                'company': company,
                'url': url,
                'processed': True
            }
    except Exception as e:
        logger.error(f"Error processing job: {e}")

    return {'title': 'Unknown Job', 'company': 'Unknown', 'url': url, 'processed': False}

# Event handlers - KEEP SIMPLE
@app.event("app_mention")
async def handle_mention(event, say):
    """Handle mentions - minimal complexity"""
    try:
        text = event.get("text", "")
        user = event.get("user", "")

        logger.info(f"Mention from {user}: {text[:50]}...")

        url = extract_url(text)

        if url:
            await say(f"<@{user}> Processing job URL... 🔍")

            result = await process_job_simple(url)

            response = f"✅ Job processed!\n\n**Title:** {result['title']}\n**Company:** {result['company']}\n**URL:** {result['url']}"

            await say(response)
        else:
            await say(f"Hi <@{user}>! Send me a job URL and I'll process it!")

    except Exception as e:
        logger.error(f"Error in mention handler: {e}")
        try:
            await say("Sorry, I had an error. Please try again!")
        except:
            pass

@app.event("message")
async def handle_message(event, say):
    """Handle DMs"""
    try:
        # Only DMs
        if event.get("channel_type") != "im":
            return

        # Skip bot messages
        if event.get("bot_id"):
            return

        text = event.get("text", "")
        url = extract_url(text)

        if url:
            await say("Processing... 🔍")
            result = await process_job_simple(url)
            await say(f"✅ **{result['title']}** at **{result['company']}**")

    except Exception as e:
        logger.error(f"Error in message handler: {e}")

# Main function
async def main():
    """Main bot function"""
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)

    logger.info("🚀 Starting Simple Slack Bot...")
    logger.info("✅ Bot ready - mention me with job URLs!")

    try:
        await handler.start_async()
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
