#!/usr/bin/env python3
"""
JobBot CLI - Command line tool to process job URLs and create Notion pages

Usage:
    python jobbot_cli.py "https://example.com/job-posting"
    python jobbot_cli.py --help
"""

import os
import sys
import argparse
import logging
import json
import re
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from notion_client import Client as NotionClient
import openai
from openai import OpenAI
try:
    from .job_formatter import format_job_description
except ImportError:
    from job_formatter import format_job_description

# Playwright imports
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# -----------------------------
# Logging Setup
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not all([OPENAI_API_KEY, NOTION_TOKEN, NOTION_DATABASE_ID]):
    print("❌ Missing required environment variables:")
    if not OPENAI_API_KEY: print("   - OPENAI_API_KEY")
    if not NOTION_TOKEN: print("   - NOTION_TOKEN")
    if not NOTION_DATABASE_ID: print("   - NOTION_DATABASE_ID")
    print("\nPlease set these in your .env file")
    sys.exit(1)

client = openai.OpenAI(api_key=OPENAI_API_KEY)
notion = NotionClient(auth=NOTION_TOKEN)

# -----------------------------
# Helper functions (reused from enhanced_jobbot.py)
# -----------------------------

def fetch_job_text_playwright(url):
    """Fetch job text using Playwright for dynamic sites"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Set a more realistic user agent
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })

            page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for the JavaScript content to load
            try:
                # Wait for job content to appear (common selectors for job sites)
                page.wait_for_selector('h1, [class*="job"], [class*="title"], [id*="job"], main, article', timeout=15000)

                # Additional wait for dynamic content
                page.wait_for_timeout(3000)

                # Try to wait for specific job content indicators
                page.wait_for_function(
                    """() => {
                        const text = document.body.innerText;
                        return text.length > 1000 &&
                               !text.includes('You need to enable JavaScript') &&
                               (text.includes('About') || text.includes('Role') || text.includes('Responsibilities') || text.includes('Requirements'));
                    }""",
                    timeout=10000
                )
            except:
                # If specific selectors fail, just wait a bit longer
                page.wait_for_timeout(5000)

            content = page.content()
            browser.close()

            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)

            # Check if we still got the JavaScript error
            if "You need to enable JavaScript" in text and len(text) < 500:
                logging.warning("Still getting JavaScript error, content may not have loaded")
                return None, None

            return text, soup  # Return both text and soup for formatting
    except Exception as e:
        logging.warning(f"Playwright failed: {e}")
        return None, None

def fetch_job_text_bs(url):
    """Fallback: Fetch job text using requests + BeautifulSoup"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        return text, soup  # Return both text and soup for formatting
    except Exception as e:
        logging.error(f"BeautifulSoup failed: {e}")
        return None, None

def fetch_job_text(url):
    """Fetch job posting text, try Playwright first, fallback to BeautifulSoup"""
    if PLAYWRIGHT_AVAILABLE:
        text, soup = fetch_job_text_playwright(url)
        if text: return text, soup

    return fetch_job_text_bs(url)

def generate_job_summary(job_text):
    """Generate a concise job summary using OpenAI"""
    try:
        prompt = f"""
Create a concise 2-3 sentence summary of this job posting that captures:
1. The role and main responsibilities
2. Key requirements or qualifications
3. Any standout benefits or company info

Job posting:
{job_text[:3000]}
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.warning(f"Failed to generate summary: {e}")
        return ""

def extract_fields(job_text):
    """Extract structured fields from job posting using OpenAI"""
    prompt = f"""
Extract the following fields from this job posting:

- Position: Job title
- Company: Company name
- Salary: Full salary range or amount (e.g., "$80,000 - $120,000", "$50/hour", "Competitive", or leave empty if not mentioned)
- Commitment: Employment type (Full time, Part time, Contract, Freelance, Internship)
- Industry: All relevant industries (e.g., ["Technology", "Healthcare", "Finance"])
- Location: All locations mentioned, use "Remote" if remote work is mentioned (e.g., ["New York", "Remote"], ["San Francisco", "Los Angeles"])

IMPORTANT:
- Respond with ONLY valid JSON, no markdown code blocks, no explanations, no backticks
- For Salary: Look carefully throughout the text for salary, compensation, pay range, or base salary information
- For Location: Always use an array, even for single locations
- If information is not found, use empty string for strings or empty array for arrays

Output JSON exactly like this format:

{{
  "Position": "",
  "Company": "",
  "Salary": "",
  "Commitment": "",
  "Industry": [],
  "Location": []
}}

Job posting:
{job_text[:8000]}
"""

    text_output = ""
    try:
        if client:
            # Use new OpenAI client
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            text_output = response.choices[0].message.content
        else:
            # Fallback to old OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.2
            )
            text_output = response.choices[0].message.content

        if text_output is None or text_output.strip() == "":
            logging.error("OpenAI returned empty or None response")
            return create_fallback_fields(job_text)

        text_output = text_output.strip()

        # Handle markdown-wrapped JSON responses
        if "```json" in text_output:
            start_idx = text_output.find("```json") + 7
            end_idx = text_output.find("```", start_idx)
            if end_idx != -1:
                text_output = text_output[start_idx:end_idx].strip()
        elif "```" in text_output:
            parts = text_output.split("```")
            if len(parts) >= 3:
                text_output = parts[1].strip()
                # Remove language identifier if present
                lines = text_output.split('\n')
                if lines[0].strip() in ['json', 'JSON']:
                    text_output = '\n'.join(lines[1:])

        # Clean up any remaining non-JSON content
        start_idx = text_output.find('{')
        end_idx = text_output.rfind('}')

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            text_output = text_output[start_idx:end_idx + 1]

        text_output = text_output.strip()

        if not text_output:
            logging.error("Empty text after cleaning OpenAI response")
            return create_fallback_fields(job_text)

        logging.info(f"Cleaned JSON response: {text_output[:200]}...")

        try:
            fields = json.loads(text_output)
        except json.JSONDecodeError as e:
            logging.error(f"Initial JSON decode failed: {e}")
            # Try to fix common JSON issues
            try:
                # Fix common issues like trailing commas, single quotes, etc.
                fixed_json = text_output.replace("'", '"')  # Replace single quotes
                fixed_json = re.sub(r',(\s*[}\]])', r'\1', fixed_json)  # Remove trailing commas
                fields = json.loads(fixed_json)
                logging.info("Successfully parsed JSON after fixing")
            except json.JSONDecodeError as e2:
                logging.error(f"Could not fix JSON: {e2}")
                logging.error(f"Failed JSON string: '{text_output}'")
                return create_fallback_fields(job_text)
        # Store both text and soup for later formatting use
        if isinstance(job_text, tuple):
            fields["Full Description"] = job_text[0]
            fields["HTML_SOUP"] = job_text[1]
            text_for_summary = job_text[0]
        else:
            fields["Full Description"] = job_text
            fields["HTML_SOUP"] = None
            text_for_summary = job_text
        fields["Summary"] = generate_job_summary(text_for_summary)

        # Apply enhanced formatting
        formatted_result = format_job_description(
            content=fields["Full Description"],
            soup=fields.get("HTML_SOUP"),
            summary=fields.get("Summary")
        )
        fields["formatted_description"] = formatted_result['rich_text']
        fields["notion_blocks"] = formatted_result['blocks']
        fields["key_bullets"] = formatted_result['bullets']

        # Clean location field to avoid commas in multi-select options
        if "Location" in fields and isinstance(fields["Location"], list):
            cleaned_locations = []
            for location in fields["Location"]:
                if isinstance(location, str):
                    parts = [part.strip() for part in location.split(',')]
                    for part in parts:
                        if part and part not in cleaned_locations:
                            cleaned_locations.append(part)
                else:
                    cleaned_locations.append(location)
            fields["Location"] = cleaned_locations

        return fields

    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from OpenAI response: {e}")
        logging.error(f"Full raw response: '{text_output}'")
        return create_fallback_fields(job_text)
    except Exception as e:
        logging.warning(f"Failed to extract fields from OpenAI: {e}")
        return create_fallback_fields(job_text)

def create_fallback_fields(job_text):
    """Create fallback fields when OpenAI extraction fails"""
    # Handle job_text being a tuple (text, soup) or just text
    if isinstance(job_text, tuple):
        text_content = job_text[0]
        soup_content = job_text[1]
    else:
        text_content = job_text
        soup_content = None

    return {
        "Full Description": text_content,
        "HTML_SOUP": soup_content,
        "Summary": generate_job_summary(text_content),
        "Position": "Unknown Position",
        "Company": "",
        "Salary": "",
        "Commitment": "Full time",
        "Industry": [],
        "Location": []
    }

def split_text_for_notion(text, max_chars=1990):
    """Split text into chunks that fit in Notion rich text fields"""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > max_chars:
        break_point = max_chars

        # Try to break at sentence end
        for i in range(max_chars - 100, max_chars):
            if i < len(remaining) and remaining[i] in '.!?':
                break_point = i + 1
                break

        # Try to break at paragraph
        if break_point == max_chars:
            for i in range(max_chars - 200, max_chars):
                if i < len(remaining) and remaining[i:i+2] == '\n\n':
                    break_point = i
                    break

        chunks.append(remaining[:break_point].strip())
        remaining = remaining[break_point:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks

def text_to_notion_blocks(text):
    """Convert plain text to Notion blocks with smart pattern recognition"""
    if not text:
        return []

    blocks = []
    lines = text.split('\n')

    # Common section headers to detect
    section_headers = [
        'about', 'overview', 'role', 'position', 'responsibilities', 'requirements',
        'qualifications', 'skills', 'experience', 'benefits', 'compensation',
        'what you', 'who you', 'we are looking', 'job description', 'duties',
        'preferred', 'bonus', 'nice to have', 'location', 'salary'
    ]

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check if this line looks like a section header
        is_header = False
        line_lower = line.lower()

        # Detect headers by common patterns
        if (line.endswith(':') and len(line) < 80 and
            any(header in line_lower for header in section_headers)):
            is_header = True
        elif (line.isupper() and len(line) < 80 and len(line) > 5):
            is_header = True
        elif (line.startswith('##') or line.startswith('**')):
            is_header = True
            line = line.replace('#', '').replace('*', '').strip()

        if is_header:
            # Add as heading
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": line[:2000]}}]
                }
            })
        else:
            # Check if line looks like a bullet point
            if (line.startswith('•') or line.startswith('-') or line.startswith('*') or
                re.match(r'^\d+[\.\)]\s', line)):
                # Remove bullet markers and add as bullet list
                clean_line = re.sub(r'^[•\-\*\d+\.\)\s]+', '', line).strip()
                if clean_line:
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": clean_line[:2000]}}]
                        }
                    })
            else:
                # Add as paragraph, but group consecutive lines
                paragraph_lines = [line]
                j = i + 1

                # Collect consecutive non-empty, non-header lines
                while (j < len(lines) and lines[j].strip() and
                       not any(header in lines[j].lower() for header in section_headers) and
                       not lines[j].strip().endswith(':') and
                       not lines[j].startswith(('•', '-', '*')) and
                       not re.match(r'^\d+[\.\)]\s', lines[j])):
                    paragraph_lines.append(lines[j].strip())
                    j += 1

                # Combine into paragraph
                paragraph_text = ' '.join(paragraph_lines)
                if paragraph_text and len(paragraph_text) > 10:  # Skip very short paragraphs
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": paragraph_text[:2000]}}]
                        }
                    })

                i = j - 1  # Adjust index since we processed multiple lines

        i += 1

    return blocks[:50]  # Limit to 50 blocks to avoid API limits

def find_or_create_company(company_name):
    """Find existing company or create new one in the linked database"""
    if not company_name or company_name.strip() == "":
        return None

    try:
        database_info = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        company_prop = database_info.get('properties', {}).get('Company', {})

        if company_prop.get('type') != 'relation':
            logging.warning("Company field is not a relation field")
            return None

        company_database_id = company_prop.get('relation', {}).get('database_id')
        if not company_database_id:
            logging.warning("Could not find Company database ID")
            return None

        # Search for existing company
        search_results = notion.databases.query(
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
            logging.info(f"Found existing company: {company_name}")
            return company_id

        # Create new company
        new_company = notion.pages.create(
            parent={"database_id": company_database_id},
            properties={
                "Name": {"title": [{"text": {"content": company_name.strip()}}]}
            }
        )

        company_id = new_company["id"]
        logging.info(f"Created new company: {company_name}")
        return company_id

    except Exception as e:
        logging.error(f"Error handling company '{company_name}': {e}")
        return None

def check_available_fields():
    """Check what fields are available in the current Notion database"""
    try:
        database_info = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        properties = database_info.get('properties', {})

        available_fields = {
            'job_summary': 'Job Summary' in properties,
            'job_desc_part_2': 'Job Description Part 2' in properties,
            'job_desc_part_3': 'Job Description Part 3' in properties,
            'job_desc_part_4': 'Job Description Part 4' in properties,
            'job_desc_part_5': 'Job Description Part 5' in properties
        }

        return available_fields
    except Exception as e:
        logging.error(f"Error checking database fields: {e}")
        return {
            'job_summary': False,
            'job_desc_part_2': False,
            'job_desc_part_3': False,
            'job_desc_part_4': False,
            'job_desc_part_5': False
        }

def create_enhanced_job_description(summary, full_description, available_fields):
    """Create enhanced description based on available fields"""
    # Use the new formatter for better bullet handling
    formatted = format_job_description(
        content=full_description,
        summary=summary if not available_fields['job_summary'] else None
    )
    return formatted['rich_text']

def create_notion_page(fields, job_url):
    """Create a new Notion page with extracted job information"""
    try:
        available_fields = check_available_fields()

        full_description = fields.get("Full Description", "")
        summary = fields.get("Summary", "")

        # Use pre-formatted description if available, otherwise create one
        formatted_description = fields.get("formatted_description")
        if formatted_description:
            enhanced_description = formatted_description
        else:
            enhanced_description = create_enhanced_job_description(summary, full_description, available_fields)
        description_chunks = split_text_for_notion(enhanced_description)

        # Handle commitment field
        commitment = fields.get("Commitment", "Full time")
        commitment_list = [commitment] if commitment else ["Full time"]

        # Clean multi-select fields
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

        # Handle company relation
        company_name = fields.get("Company", "")
        company_id = find_or_create_company(company_name) if company_name else None

        # Build properties
        properties = {
            "Position": {"title": [{"text": {"content": fields.get("Position", "Unknown")}}]},
            "Status": {"select": {"name": "Researching"}},
            "Active v Archived": {"status": {"name": "In progress"}},
            "Job URL": {"url": job_url},
            "Salary": {"rich_text": [{"text": {"content": fields.get("Salary", "")}}]},
            "Commitment": {"multi_select": [{"name": c} for c in commitment_values]},
            "Industry": {"multi_select": [{"name": i} for i in industry_values]},
            "Location": {"multi_select": [{"name": l} for l in location_values]},
            "Job Description": {"rich_text": [{"text": {"content": summary}}]},
        }

        if company_id:
            properties["Company"] = {"relation": [{"id": company_id}]}

        # Add job summary if separate field exists
        if available_fields['job_summary']:
            properties["Job Summary"] = {"rich_text": [{"text": {"content": summary}}]}

        # Always use toggle block with smart formatting inside
        formatted_blocks = text_to_notion_blocks(full_description)

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

        if formatted_blocks and len(formatted_blocks) > 5:
            # Use smart formatted blocks inside toggle
            content_blocks[0]["toggle"]["children"] = formatted_blocks
        else:
            # Fallback to plain text chunks inside toggle
            max_block_size = 2000
            toggle_children = []
            for i in range(0, len(full_description), max_block_size):
                chunk = full_description[i:i+max_block_size]
                if chunk.strip():  # Only add non-empty chunks
                    toggle_children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        }
                    })
            content_blocks[0]["toggle"]["children"] = toggle_children

        # Create the page with full job description in content
        new_page = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties,
            children=content_blocks
        )

        return new_page

    except Exception as e:
        logging.error(f"Error creating Notion page: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(
        description="JobBot CLI - Extract job information and create Notion pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python jobbot_cli.py "https://example.com/job-posting"
  python jobbot_cli.py --verbose "https://another-job.com"
        """
    )

    parser.add_argument("url", help="Job posting URL to process")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    job_url = args.url.strip()

    if not job_url.startswith(('http://', 'https://')):
        print("❌ Please provide a valid URL starting with http:// or https://")
        sys.exit(1)

    try:
        print(f"🔍 Processing job URL: {job_url}")

        # Fetch job text
        print("📥 Fetching job posting content...")
        job_result = fetch_job_text(job_url)

        if not job_result or not job_result[0]:
            print("❌ Failed to fetch job posting content")
            sys.exit(1)

        job_text = job_result  # This is now (text, soup) tuple
        text_length = len(job_text[0]) if isinstance(job_text, tuple) else len(job_text)
        print(f"✅ Fetched {text_length} characters")

        # Extract fields
        print("🤖 Extracting job information with AI...")
        fields = extract_fields(job_text)

        # Display extracted info
        print("\n📋 Extracted Information:")
        print(f"   Position: {fields.get('Position', 'Not found')}")
        print(f"   Company: {fields.get('Company', 'Not found')}")
        print(f"   Salary: {fields.get('Salary', 'Not found')}")
        print(f"   Location: {fields.get('Location', 'Not found')}")
        print(f"   Commitment: {fields.get('Commitment', 'Not found')}")
        print(f"   Industry: {fields.get('Industry', 'Not found')}")

        # Create Notion page
        print("\n📝 Creating Notion page...")
        new_page = create_notion_page(fields, job_url)

        page_url = new_page.get('url', 'URL not available')
        print(f"✅ Successfully created Notion page!")
        print(f"🔗 Page URL: {page_url}")

    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        logging.exception("Full error details:")
        sys.exit(1)

if __name__ == "__main__":
    main()
