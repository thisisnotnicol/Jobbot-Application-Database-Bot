#!/usr/bin/env python3
"""
JobBot Slack Integration - Fixed Version
Addresses dispatch_failed errors and JSON parsing issues

Key fixes:
- Robust JSON parsing with multiple fallback strategies
- Proper text length handling for Notion API
- Comprehensive error handling in async event handlers
- Better logging and debugging
- Graceful degradation when services fail
"""

import os
import re
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, Union
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import openai
from notion_client import Client as NotionClient

# Playwright imports with fallback
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# -----------------------------
# Environment Setup
# -----------------------------
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

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
    print("\nPlease set these in your .env file")
    exit(1)

# Initialize clients
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
notion_client = NotionClient(auth=NOTION_TOKEN)

# -----------------------------
# Logging Setup
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("slack_jobbot_fixed.log")
    ]
)

logger = logging.getLogger(__name__)

# -----------------------------
# Slack App Setup
# -----------------------------
app = AsyncApp(token=SLACK_BOT_TOKEN)

# URL regex pattern
URL_PATTERN = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)

# -----------------------------
# Core Functions
# -----------------------------

def fetch_job_text_playwright(url: str) -> Optional[str]:
    """Fetch job text using Playwright with error handling"""
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("Playwright not available")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                logger.info(f"Fetching job content with Playwright: {url}")
                page.goto(url, timeout=20000)
                page.wait_for_timeout(2000)
                text = page.inner_text("body")
                return text.strip() if text else None
            finally:
                browser.close()
    except Exception as e:
        logger.error(f"Playwright fetch failed for {url}: {e}")
        return None

def fetch_job_text_requests(url: str) -> Optional[str]:
    """Fetch job text using requests + BeautifulSoup"""
    try:
        logger.info(f"Fetching job content with requests: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Try to find job content in common containers
        content_selectors = [
            ".job-description",
            ".job-content",
            "[data-job-description]",
            ".posting-content",
            ".job-posting",
            "main",
            ".content"
        ]

        text = ""
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                text = " ".join(elem.get_text() for elem in elements)
                break

        # Fallback to all paragraphs
        if not text:
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text() for p in paragraphs)

        # Final fallback to body text
        if not text:
            text = soup.get_text()

        return text.strip() if text else None

    except Exception as e:
        logger.error(f"Requests fetch failed for {url}: {e}")
        return None

def fetch_job_text(url: str) -> Optional[str]:
    """Fetch job text with multiple fallback strategies"""
    try:
        # Try Playwright first
        text = fetch_job_text_playwright(url)
        if text and len(text.strip()) > 100:  # Ensure we got substantial content
            return text

        # Fallback to requests
        text = fetch_job_text_requests(url)
        if text and len(text.strip()) > 100:
            return text

        logger.warning(f"No substantial content found for {url}")
        return None

    except Exception as e:
        logger.error(f"All fetch methods failed for {url}: {e}")
        return None

def clean_json_response(text: str) -> str:
    """Clean OpenAI response to extract valid JSON"""
    if not text:
        return ""

    text = text.strip()

    # Remove markdown code blocks
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end != -1:
            text = text[start:end].strip()
    elif "```" in text:
        # Handle generic code blocks
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1].strip()
            # Remove language identifier if present
            lines = text.split('\n')
            if lines[0].strip() in ['json', 'JSON']:
                text = '\n'.join(lines[1:])

    # Remove any leading/trailing non-JSON text
    # Find first { and last }
    start_idx = text.find('{')
    end_idx = text.rfind('}')

    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        text = text[start_idx:end_idx + 1]

    return text.strip()

def generate_job_summary(job_text: str) -> str:
    """Generate AI summary with error handling"""
    try:
        prompt = f"""Create a concise 2-3 sentence summary of this job posting.
Focus on: role level, key responsibilities, and important requirements.
Keep under 300 characters.

Job posting:
{job_text[:3000]}"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )

        summary = response.choices[0].message.content
        return summary.strip() if summary else "Job summary not available"

    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        return "Job summary not available"

def extract_fields_robust(job_text: str) -> Dict[str, Any]:
    """Extract fields with robust JSON parsing and error handling"""

    prompt = f"""You are a job posting analyzer. Extract information from this job posting and return ONLY a valid JSON object.

Look for these fields in the job posting text:

1. Position: The job title (e.g., "Software Engineer", "Marketing Manager")
2. Company: The hiring company name
3. Salary: Any compensation information (salary ranges, hourly rates, "competitive", benefits packages)
4. Commitment: Employment type (Full time, Part time, Contract, Freelance, Internship, etc.)
5. Industry: Business sectors (Technology, Healthcare, Finance, Marketing, etc.)
6. Location: Work locations (cities, states, "Remote", "Hybrid", etc.)

Return this exact JSON structure:
{{
  "Position": "exact job title from posting",
  "Company": "company name",
  "Salary": "any compensation details found",
  "Commitment": "employment type",
  "Industry": ["relevant", "industries"],
  "Location": ["work", "locations"]
}}

CRITICAL RULES:
- Look throughout the ENTIRE text for salary/pay information
- For Location: include "Remote" if remote work is mentioned anywhere
- For arrays: always return arrays even for single items
- Use empty string "" for missing text fields
- Use empty array [] for missing array fields
- Return ONLY the JSON - no explanations, no markdown blocks

Job posting text:
{job_text[:8000]}"""

    fallback_data = {
        "Position": "Position Not Specified",
        "Company": "",
        "Salary": "",
        "Commitment": "Full time",
        "Industry": [],
        "Location": []
    }

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        raw_response = response.choices[0].message.content
        logger.info(f"Raw OpenAI response: {raw_response[:200]}...")

        if not raw_response or raw_response.strip() == "":
            logger.error("Empty response from OpenAI")
            return fallback_data

        # Clean the JSON response
        cleaned_json = clean_json_response(raw_response)
        logger.info(f"Cleaned JSON: {cleaned_json[:200]}...")

        if not cleaned_json:
            logger.error("No valid JSON found in response")
            return fallback_data

        # Parse JSON with multiple attempts
        try:
            fields = json.loads(cleaned_json)

            # Validate required fields
            required_fields = ["Position", "Company", "Salary", "Commitment", "Industry", "Location"]
            for field in required_fields:
                if field not in fields:
                    fields[field] = fallback_data[field]

            # Store full description for toggle blocks
            fields["Full Description"] = job_text

            # Clean and validate text fields
            for field in ["Position", "Company", "Salary", "Commitment"]:
                if isinstance(fields[field], list):
                    # Convert list to string if needed
                    fields[field] = ", ".join(str(x) for x in fields[field] if str(x).strip())
                elif not isinstance(fields[field], str):
                    fields[field] = str(fields[field]) if fields[field] is not None else ""

            # Ensure lists are actually lists
            for field in ["Industry", "Location"]:
                if not isinstance(fields[field], list):
                    if isinstance(fields[field], str):
                        fields[field] = [fields[field]] if fields[field].strip() else []
                    else:
                        fields[field] = []

            # Clean location data to avoid commas in multi-select
            if fields.get("Location"):
                cleaned_locations = []
                for loc in fields["Location"]:
                    if isinstance(loc, str) and loc.strip():
                        # Split on comma and clean each part
                        parts = [part.strip() for part in loc.split(',') if part.strip()]
                        cleaned_locations.extend(parts)
                    elif loc:
                        cleaned_locations.append(str(loc))
                fields["Location"] = list(set(cleaned_locations))  # Remove duplicates

            # Clean industry data similarly
            if fields.get("Industry"):
                cleaned_industries = []
                for ind in fields["Industry"]:
                    if isinstance(ind, str) and ind.strip():
                        parts = [part.strip() for part in ind.split(',') if part.strip()]
                        cleaned_industries.extend(parts)
                    elif ind:
                        cleaned_industries.append(str(ind))
                fields["Industry"] = list(set(cleaned_industries))  # Remove duplicates

            logger.info(f"Successfully parsed and cleaned fields")
            return fields

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Failed JSON string: '{cleaned_json}'")

            # Try to fix common JSON issues
            try:
                # Fix common issues like trailing commas, single quotes, etc.
                fixed_json = cleaned_json.replace("'", '"')  # Replace single quotes
                fixed_json = re.sub(r',(\s*[}\]])', r'\1', fixed_json)  # Remove trailing commas
                fields = json.loads(fixed_json)
                logger.info("Successfully parsed JSON after fixing")
                return fields
            except:
                logger.error("Could not fix JSON, using fallback")
                return fallback_data

    except Exception as e:
        logger.error(f"OpenAI extraction failed: {e}")
        return fallback_data

def truncate_text_for_notion(text: str, max_length: int = 2000) -> str:
    """Truncate text to fit Notion's field limits"""
    if len(text) <= max_length:
        return text

    # Try to truncate at a sentence boundary
    truncated = text[:max_length]
    last_period = truncated.rfind('.')
    last_newline = truncated.rfind('\n')

    cut_point = max(last_period, last_newline)
    if cut_point > max_length * 0.8:  # Only use if we're not losing too much
        return truncated[:cut_point + 1]

    # Fallback to hard truncate with ellipsis
    return truncated[:max_length - 3] + "..."

def create_notion_page_robust(fields: Dict[str, Any], job_url: str, job_text: str) -> Optional[Dict[str, Any]]:
    """Create Notion page with robust error handling - matches working jobbot_cli implementation exactly"""

    try:
        # Generate summary
        summary = generate_job_summary(job_text)
        full_description = fields.get("Full Description", job_text)

        # Handle commitment field - convert to list format
        commitment = fields.get("Commitment", "Full time")
        commitment_list = [commitment] if commitment else ["Full time"]

        # Clean multi-select fields (same as working version)
        def clean_multiselect_values(values, field_name):
            if not values:
                return []
            if isinstance(values, str):
                values = [values]

            cleaned = []
            for value in values:
                if value and isinstance(value, str):
                    clean_value = str(value).strip()[:100]
                    if clean_value:
                        cleaned.append(clean_value)
            return cleaned

        industry_values = clean_multiselect_values(fields.get("Industry", []), "Industry")
        location_values = clean_multiselect_values(fields.get("Location", []), "Location")
        commitment_values = clean_multiselect_values(commitment_list, "Commitment")

        # Handle company relation - use the working find_or_create_company function
        company_name = fields.get("Company", "")
        company_id = find_or_create_company_working(company_name) if company_name else None

        # Build properties - match the working version exactly
        properties = {
            "Position": {"title": [{"text": {"content": fields.get("Position", "Unknown")}}]},
            "Status": {"select": {"name": "Researching"}},  # Same as working version
            "Active v Archived": {"status": {"name": "In progress"}},  # Same as working version
            "Job URL": {"url": job_url},
            "Salary": {"rich_text": [{"text": {"content": fields.get("Salary", "")}}]},
            "Commitment": {"multi_select": [{"name": c} for c in commitment_values]},
            "Industry": {"multi_select": [{"name": i} for i in industry_values]},
            "Location": {"multi_select": [{"name": l} for l in location_values]},
            "Job Description": {"rich_text": [{"text": {"content": summary}}]},
        }

        # Add company relation if found/created
        if company_id:
            properties["Company"] = {"relation": [{"id": company_id}]}

        # Create toggle blocks with full job description (like working version)
        content_blocks = [
            {
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": "Job Description"}}],
                    "children": []
                }
            }
        ]

        # Add job description content to toggle - ensure we use the actual job text
        description_text = job_text if job_text else full_description
        if not description_text:
            description_text = "No job description available"

        max_block_size = 2000
        toggle_children = []
        for i in range(0, len(description_text), max_block_size):
            chunk = description_text[i:i+max_block_size]
            if chunk.strip():  # Only add non-empty chunks
                toggle_children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    }
                })
        content_blocks[0]["toggle"]["children"] = toggle_children

        # Log what we're creating
        logger.info(f"Creating Notion page with properties:")
        logger.info(f"  Position: {fields.get('Position', 'Unknown')}")
        logger.info(f"  Company: {company_name} (ID: {company_id})")
        logger.info(f"  Salary: {fields.get('Salary', 'Not specified')}")
        logger.info(f"  Location: {location_values}")
        logger.info(f"  Commitment: {commitment_values}")
        logger.info(f"  Industry: {industry_values}")

        # Create the page with content blocks (like working version)
        new_page = notion_client.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties,
            children=content_blocks
        )

        logger.info(f"Successfully created Notion page: {new_page.get('id')}")
        return new_page

    except Exception as e:
        logger.error(f"Failed to create Notion page: {e}")
        if 'properties' in locals():
            logger.error(f"Properties attempted: {json.dumps(properties, indent=2, default=str)}")
        return None

def find_or_create_company_working(company_name: str) -> Optional[str]:
    """Find existing company or create new one - exact copy from working jobbot_cli"""
    if not company_name or company_name.strip() == "":
        return None

    try:
        database_info = notion_client.databases.retrieve(database_id=NOTION_DATABASE_ID)
        company_prop = database_info.get('properties', {}).get('Company', {})

        if company_prop.get('type') != 'relation':
            logger.warning("Company field is not a relation field")
            return None

        company_database_id = company_prop.get('relation', {}).get('database_id')
        if not company_database_id:
            logger.warning("Could not find Company database ID")
            return None

        # Search for existing company
        search_results = notion_client.databases.query(
            database_id=company_database_id,
            filter={
                "property": "Name",
                "title": {
                    "equals": company_name.strip()
                }
            }
        )

        if search_results.get("results"):
            company_id = search_results["results"][0]["id"]
            logger.info(f"Found existing company: {company_name}")
            return company_id

        # Create new company
        new_company = notion_client.pages.create(
            parent={"database_id": company_database_id},
            properties={
                "Name": {"title": [{"text": {"content": company_name.strip()}}]}
            }
        )

        company_id = new_company["id"]
        logger.info(f"Created new company: {company_name}")
        return company_id

    except Exception as e:
        logger.error(f"Error handling company '{company_name}': {e}")
        return None

# -----------------------------
# Slack Helper Functions
# -----------------------------

def extract_urls_from_text(text: str) -> list:
    """Extract URLs from text"""
    return URL_PATTERN.findall(text)

def is_job_url(url: str) -> bool:
    """Check if URL looks like a job posting"""
    job_keywords = [
        'job', 'career', 'position', 'hiring', 'vacancy', 'employment',
        'opportunities', 'roles', 'apply', 'jobs', 'careers', 'work', 'posting'
    ]
    return any(keyword in url.lower() for keyword in job_keywords)

async def send_processing_message(client, channel: str, thread_ts: Optional[str] = None) -> Optional[str]:
    """Send processing message and return message timestamp"""
    try:
        response = await client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="🔍 Processing job posting... This may take a moment!",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🔍 *Processing job posting...*\n\n_Fetching content, extracting information, and creating Notion page. This may take 30-60 seconds._"
                    }
                }
            ]
        )
        return response.get('ts')
    except Exception as e:
        logger.error(f"Error sending processing message: {e}")
        return None

async def update_message_with_result(client, channel: str, ts: str, success: bool,
                                   result_data: Optional[Dict] = None, error_msg: Optional[str] = None):
    """Update message with processing results"""
    try:
        if success and result_data:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *Successfully created Notion page!*\n\n*{result_data.get('position', 'Unknown Position')}*\n{result_data.get('company', 'Unknown Company')}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Salary:*\n{result_data.get('salary', 'Not specified')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Location:*\n{', '.join(result_data.get('location', ['Not specified']))}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Type:*\n{result_data.get('commitment', 'Not specified')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Industry:*\n{', '.join(result_data.get('industry', ['Not specified']))}"
                        }
                    ]
                }
            ]

            if result_data.get('notion_url'):
                blocks.append({
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View in Notion"},
                            "url": result_data['notion_url'],
                            "action_id": "view_notion"
                        }
                    ]
                })
        else:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *Failed to process job posting*\n\n{error_msg or 'Unknown error occurred'}"
                    }
                }
            ]

        await client.chat_update(channel=channel, ts=ts, blocks=blocks)

    except Exception as e:
        logger.error(f"Error updating message: {e}")

async def process_job_url_safe(url: str, client, channel: str, thread_ts: Optional[str] = None):
    """Process job URL with comprehensive error handling"""
    processing_ts = None

    try:
        # Send processing message
        processing_ts = await send_processing_message(client, channel, thread_ts)
        logger.info(f"Processing job URL: {url}")

        # Fetch job content
        job_text = fetch_job_text(url)
        if not job_text:
            await update_message_with_result(
                client, channel, processing_ts, False,
                error_msg="Could not fetch job content. The page might be protected or inaccessible."
            )
            return

        logger.info(f"Fetched {len(job_text)} characters from {url}")

        # Extract fields
        fields = extract_fields_robust(job_text)
        logger.info(f"Extracted fields:")
        logger.info(f"  Position: {fields.get('Position', 'Not found')}")
        logger.info(f"  Company: {fields.get('Company', 'Not found')}")
        logger.info(f"  Salary: {fields.get('Salary', 'Not found')}")
        logger.info(f"  Location: {fields.get('Location', [])}")
        logger.info(f"  Commitment: {fields.get('Commitment', 'Not found')}")
        logger.info(f"  Industry: {fields.get('Industry', [])}")

        # Create Notion page
        new_page = create_notion_page_robust(fields, url, job_text)

        if new_page:
            # Success! Extract company name for display
            company_name = fields.get('Company', '').strip()
            if not company_name:
                company_name = 'Company not specified'

            result_data = {
                'position': fields.get('Position', 'Position not specified'),
                'company': company_name,
                'salary': fields.get('Salary', 'Not specified'),
                'location': fields.get('Location', []) if fields.get('Location') else ['Not specified'],
                'commitment': fields.get('Commitment', 'Not specified'),
                'industry': fields.get('Industry', []) if fields.get('Industry') else ['Not specified'],
                'notion_url': new_page.get('url')
            }

            await update_message_with_result(client, channel, processing_ts, True, result_data)
            logger.info(f"Successfully processed {url} - Created page for {result_data['position']} at {result_data['company']}")
        else:
            await update_message_with_result(
                client, channel, processing_ts, False,
                error_msg="Failed to create Notion page. Please check your database configuration."
            )

    except Exception as e:
        logger.error(f"Unexpected error processing {url}: {e}")
        if processing_ts:
            await update_message_with_result(
                client, channel, processing_ts, False,
                error_msg=f"Unexpected error: {str(e)[:100]}..."
            )

# -----------------------------
# Slack Event Handlers
# -----------------------------

@app.event("app_mention")
async def handle_app_mention(event, client):
    """Handle @jobbot mentions with robust error handling"""
    try:
        channel = event['channel']
        text = event.get('text', '')
        thread_ts = event.get('ts')
        user = event.get('user')

        logger.info(f"App mention from user {user} in channel {channel}: {text[:100]}...")

        urls = extract_urls_from_text(text)

        if not urls:
            await client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text="👋 Hi! I can help you add job postings to Notion. Just mention me with a job URL:\n`@jobbot https://example.com/job-posting`"
            )
            return

        # Process each URL
        for url in urls:
            if is_job_url(url):
                await process_job_url_safe(url, client, channel, thread_ts)
            else:
                await client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=f"🤔 That doesn't look like a job posting URL. I work best with job/career pages:\n`{url}`"
                )

    except Exception as e:
        logger.error(f"Error in app_mention handler: {e}")
        try:
            await client.chat_postMessage(
                channel=event.get('channel'),
                text="❌ Sorry, I encountered an error processing your request. Please try again."
            )
        except:
            pass  # Don't fail if we can't even send error message

@app.event("message")
async def handle_message(event, client):
    """Handle direct messages with robust error handling"""
    try:
        # Only process direct messages
        if event.get('channel_type') != 'im':
            return

        # Ignore bot messages
        if event.get('bot_id'):
            return

        channel = event['channel']
        text = event.get('text', '')
        user = event.get('user')

        logger.info(f"Direct message from user {user}: {text[:100]}...")

        urls = extract_urls_from_text(text)

        if not urls:
            await client.chat_postMessage(
                channel=channel,
                text="👋 Hi! Send me a job posting URL and I'll extract the information and add it to your Notion database.\n\nExample: `https://example.com/job-posting`"
            )
            return

        # Process each URL
        for url in urls:
            await process_job_url_safe(url, client, channel)

    except Exception as e:
        logger.error(f"Error in message handler: {e}")
        try:
            await client.chat_postMessage(
                channel=event.get('channel'),
                text="❌ Sorry, I encountered an error processing your message. Please try again."
            )
        except:
            pass

@app.command("/addjob")
async def handle_addjob_command(ack, command, client):
    """Handle /addjob slash command with robust error handling"""
    try:
        await ack()

        channel = command['channel_id']
        text = command.get('text', '').strip()
        user = command['user_id']

        logger.info(f"Slash command from user {user}: {text}")

        if not text:
            await client.chat_postEphemeral(
                channel=channel,
                user=user,
                text="Please provide a job URL: `/addjob https://example.com/job-posting`"
            )
            return

        urls = extract_urls_from_text(text)
        if not urls:
            await client.chat_postEphemeral(
                channel=channel,
                user=user,
                text="Please provide a valid URL: `/addjob https://example.com/job-posting`"
            )
            return

        # Process the first URL
        await process_job_url_safe(urls[0], client, channel)

    except Exception as e:
        logger.error(f"Error in addjob command handler: {e}")
        try:
            await client.chat_postEphemeral(
                channel=command.get('channel_id'),
                user=command.get('user_id'),
                text="❌ Sorry, I encountered an error processing your command. Please try again."
            )
        except:
            pass

@app.error
async def handle_errors(error, body, logger_slack):
    """Global error handler"""
    logger.error(f"Slack app error: {error}")
    logger.error(f"Request body: {json.dumps(body, indent=2, default=str)}")

# -----------------------------
# Main Function
# -----------------------------

async def main():
    """Start the Slack bot with comprehensive error handling"""
    try:
        handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)

        logger.info("🤖 JobBot Slack Integration (Fixed Version) starting...")
        logger.info("✓ Robust JSON parsing")
        logger.info("✓ Text length handling")
        logger.info("✓ Comprehensive error handling")
        logger.info("✓ Multiple content fetching strategies")
        logger.info("")
        logger.info("Bot features:")
        logger.info("  ✓ Direct message job URLs")
        logger.info("  ✓ @mention with URLs")
        logger.info("  ✓ /addjob slash command")
        logger.info("  ✓ Automatic Notion page creation")
        logger.info("  ✓ AI-powered job extraction")
        logger.info("  ✓ Graceful error handling")

        await handler.start_async()

    except Exception as e:
        logger.error(f"Failed to start Slack bot: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Starting JobBot Slack Integration (Fixed Version)...")
    print("\n✨ Key improvements:")
    print("• Robust JSON parsing with multiple fallback strategies")
    print("• Proper text length handling for Notion API")
    print("• Comprehensive error handling in all event handlers")
    print("• Better logging and debugging")
    print("• Graceful degradation when services fail")
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
