import os
import time
import json
import logging
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import openai
from notion_client import Client as NotionClient

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

client = openai.OpenAI(api_key=OPENAI_API_KEY)
notion = NotionClient(auth=NOTION_TOKEN)

# -----------------------------
# Helper functions
# -----------------------------
def fetch_job_text_playwright(url):
    if not PLAYWRIGHT_AVAILABLE:
        logging.warning("Playwright not installed, skipping Playwright scraping.")
        return None

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            logging.info(f"Fetching job description via Playwright: {url}")
            page.goto(url, timeout=20000)  # 20 sec timeout
            page.wait_for_timeout(2000)  # small wait for dynamic content
            text = page.inner_text("body")
            browser.close()
            return text.strip()
    except Exception as timeout_error:
        if "TimeoutError" in str(type(timeout_error)):
            logging.warning(f"Playwright timeout for URL: {url}")
        else:
            logging.error(f"Playwright error for URL {url}: {timeout_error}")
        return None


def fetch_job_text_bs(url):
    try:
        logging.info(f"Fetching job description via BeautifulSoup: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text() for p in paragraphs)
        return text.strip()
    except Exception as e:
        logging.error(f"BeautifulSoup fetch failed for {url}: {e}")
        return None

def fetch_job_text(url):
    text = fetch_job_text_playwright(url)
    if text:
        return text
    return fetch_job_text_bs(url)

def generate_job_summary(job_text):
    """Generate a concise AI summary of the job posting"""

    summary_prompt = f"""
Create a concise 2-3 sentence summary of this job posting that captures:
- The role and level
- Key responsibilities
- Most important requirements

Keep it under 300 characters. Be direct and informative.

Job posting:
{job_text[:3000]}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
        )
        summary = response.choices[0].message.content
        if summary:
            summary = summary.strip()
            # Ensure summary fits in Notion (under 2000 chars, but aim for much shorter)
            if len(summary) > 500:
                summary = summary[:497] + "..."
            return summary
        return "Summary not available"
    except Exception as e:
        logging.error(f"Failed to generate summary: {e}")
        return "Summary generation failed"

def extract_fields(job_text):
    prompt = f"""
Extract the following fields from this job posting:

- Position
- Company
- Salary
- Commitment (Full time, Part time, Freelance, 10 hrs/wk)
- Industry (list all that apply)
- Location (city names or 'Remote')

IMPORTANT: Respond with ONLY valid JSON, no markdown code blocks, no explanations, no backticks.

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
{job_text[:4000]}
"""
    text_output = ""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        text_output = response.choices[0].message.content
        if text_output is None:
            logging.error("OpenAI returned empty response")
            return {"Full Description": job_text}

        text_output = text_output.strip()

        # Handle markdown-wrapped JSON responses
        if text_output.startswith("```json"):
            # Remove ```json and ``` wrapper
            text_output = text_output[7:]  # Remove ```json
            if text_output.endswith("```"):
                text_output = text_output[:-3]  # Remove closing ```
            text_output = text_output.strip()
        elif text_output.startswith("```"):
            # Handle plain ``` wrapper
            lines = text_output.split('\n')
            if len(lines) > 2:
                text_output = '\n'.join(lines[1:-1])  # Remove first and last line
            text_output = text_output.strip()

        logging.info(f"Cleaned JSON response: {text_output[:200]}...")
        fields = json.loads(text_output)
        fields["Full Description"] = job_text  # Always include full description

        # Generate summary
        logging.info("Generating job summary...")
        fields["Summary"] = generate_job_summary(job_text)

        # Clean location field to avoid commas in multi-select options
        if "Location" in fields and isinstance(fields["Location"], list):
            cleaned_locations = []
            for location in fields["Location"]:
                # Split locations with commas and clean them
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
        logging.error(f"Raw OpenAI response: {text_output}")
        fallback_fields = {"Full Description": job_text, "Summary": generate_job_summary(job_text)}
        # Clean location field in fallback too
        if "Location" in fallback_fields and isinstance(fallback_fields["Location"], list):
            cleaned_locations = []
            for location in fallback_fields["Location"]:
                if isinstance(location, str):
                    parts = [part.strip() for part in location.split(',')]
                    for part in parts:
                        if part and part not in cleaned_locations:
                            cleaned_locations.append(part)
                else:
                    cleaned_locations.append(location)
            fallback_fields["Location"] = cleaned_locations
        return fallback_fields
    except Exception as e:
        logging.warning(f"Failed to extract fields from OpenAI: {e}")
        fallback_fields = {"Full Description": job_text, "Summary": generate_job_summary(job_text)}
        return fallback_fields

def split_text_for_notion(text, max_chars=1990):
    """Split text into chunks that fit in Notion rich text fields"""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > max_chars:
        # Find a good break point (prefer sentence or paragraph breaks)
        break_point = max_chars

        # Look for sentence endings within the last 100 characters
        for i in range(max_chars - 100, max_chars):
            if i < len(remaining) and remaining[i] in '.!?\n':
                break_point = i + 1
                break

        # If no good break point, look for word boundaries
        if break_point == max_chars:
            for i in range(max_chars - 20, max_chars):
                if i < len(remaining) and remaining[i] == ' ':
                    break_point = i
                    break

        chunk = remaining[:break_point].strip()
        chunks.append(chunk)
        remaining = remaining[break_point:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks

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
    """Create a combined description with summary at top, optimized for available fields"""

    if available_fields['job_summary']:
        # If we have a separate summary field, just return the full description
        return full_description
    else:
        # Combine summary and description in the main field
        separator = "\n" + "="*50 + "\n"
        combined = f"📋 SUMMARY:\n{summary}\n{separator}{full_description}"
        return combined

def add_to_notion(fields, job_url):
    try:
        # Check what fields are available
        available_fields = check_available_fields()

        # Get full job description and summary
        full_description = fields.get("Full Description", "")
        summary = fields.get("Summary", "")

        # Create enhanced description based on available fields
        enhanced_description = create_enhanced_job_description(summary, full_description, available_fields)

        # Split description into chunks
        description_chunks = split_text_for_notion(enhanced_description)

        # Handle commitment field - ensure it's in a list for multi_select
        commitment = fields.get("Commitment", "Full time")
        commitment_list = [commitment] if commitment else ["Full time"]

        # Base properties that every job entry will have
        properties = {
            "Position": {"title": [{"text": {"content": fields.get("Position", "Unknown")}}]},
            "Status": {"select": {"name": "Researching"}},
            "Active v Archived": {"status": {"name": "In progress"}},
            "Job URL": {"url": job_url},
            "Salary": {"rich_text": [{"text": {"content": fields.get("Salary", "")}}]},
            "Commitment": {"multi_select": [{"name": c} for c in commitment_list]},
            "Industry": {"multi_select": [{"name": i} for i in fields.get("Industry", [])]},
            "Location": {"multi_select": [{"name": l} for l in fields.get("Location", [])]},
            "Processed": {"checkbox": True},
        }

        # Add job summary if separate field exists
        if available_fields['job_summary'] and summary:
            properties["Job Summary"] = {"rich_text": [{"text": {"content": summary}}]}

        # Add job description parts based on available fields
        field_mapping = [
            ("Job Description", True),  # Main field always exists
            ("Job Description Part 2", available_fields['job_desc_part_2']),
            ("Job Description Part 3", available_fields['job_desc_part_3']),
            ("Job Description Part 4", available_fields['job_desc_part_4']),
            ("Job Description Part 5", available_fields['job_desc_part_5'])
        ]

        # Add chunks to available fields
        for i, chunk in enumerate(description_chunks):
            if i < len(field_mapping):
                field_name, is_available = field_mapping[i]
                if is_available:
                    properties[field_name] = {"rich_text": [{"text": {"content": chunk}}]}
                else:
                    # If field doesn't exist, combine remaining chunks with the last available field
                    if i > 0:
                        # Find the last available field and append remaining content
                        last_available_idx = i - 1
                        for j in range(i-1, -1, -1):
                            if field_mapping[j][1]:
                                last_available_idx = j
                                break

                        # Combine remaining chunks
                        remaining_chunks = description_chunks[i:]
                        remaining_text = "\n...\n".join(remaining_chunks)

                        last_field_name = field_mapping[last_available_idx][0]
                        current_content = properties[last_field_name]["rich_text"][0]["text"]["content"]

                        # Truncate if necessary to fit in Notion's limit
                        combined_content = current_content + "\n...\n" + remaining_text
                        if len(combined_content) > 1990:
                            combined_content = combined_content[:1987] + "..."

                        properties[last_field_name] = {"rich_text": [{"text": {"content": combined_content}}]}
                    break

        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties
        )

        # Log results
        parts_used = min(len(description_chunks), len([f for f, available in field_mapping if available]))
        total_chars = len(full_description)

        logging.info(f"Job added to Notion: {fields.get('Position', 'Unknown')}")
        logging.info(f"Summary generated: {'✓' if summary else '✗'}")
        logging.info(f"Description split into {parts_used} part(s)")
        logging.info(f"Total characters preserved: {total_chars}")

        if not available_fields['job_summary']:
            logging.info("💡 Add 'Job Summary' field to Notion for separate summary storage")

        missing_desc_fields = sum(1 for available in available_fields.values() if not available and 'job_desc' in str(available))
        if missing_desc_fields > 0:
            logging.info(f"💡 Add {missing_desc_fields} more 'Job Description Part X' field(s) for full text preservation")

    except Exception as e:
        logging.error(f"Error adding job to Notion: {e}")

# -----------------------------
# Main loop
# -----------------------------
def main():
    if not NOTION_DATABASE_ID:
        logging.error("NOTION_DATABASE_ID is not set in environment variables")
        return

    # Check database setup
    logging.info("Checking Notion database compatibility...")
    available_fields = check_available_fields()

    enhanced_features = []
    if available_fields['job_summary']:
        enhanced_features.append("Separate AI summaries")
    else:
        enhanced_features.append("Inline AI summaries")

    available_desc_parts = sum(1 for field in available_fields.values() if field)
    max_chars_preserved = available_desc_parts * 1990 + 1990  # +1990 for main description field
    enhanced_features.append(f"Up to {max_chars_preserved:,} characters preserved")

    logging.info("Enhanced JobBot starting...")
    logging.info("Features enabled:")
    for feature in enhanced_features:
        logging.info(f"  ✓ {feature}")

    if not any(available_fields.values()):
        logging.info("  ✓ Smart description combining (summary + job text)")
        logging.info("  💡 Add extra fields for even more functionality!")

    while True:
        try:
            query_results = notion.databases.query(
                database_id=NOTION_DATABASE_ID,
                filter={"property": "Processed", "checkbox": {"equals": False}}
            )

            for page in query_results.get("results", []):
                job_url_prop = page["properties"].get("Job URL", {})
                job_url = job_url_prop.get("url")
                if not job_url:
                    logging.warning(f"No URL found for page {page['id']}, skipping.")
                    continue

                logging.info(f"Processing URL: {job_url}")
                job_text = fetch_job_text(job_url)
                if not job_text:
                    logging.warning(f"No job text fetched for URL: {job_url}")
                    continue

                logging.info(f"Job text length: {len(job_text)} characters")
                fields_dict = extract_fields(job_text)
                add_to_notion(fields_dict, job_url)

                # Mark original page as processed
                notion.pages.update(
                    page_id=page["id"],
                    properties={"Processed": {"checkbox": True}}
                )

            logging.info("Cycle complete. Waiting 5 minutes before next check...")
            time.sleep(300)

        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(300)

if __name__ == "__main__":
    main()
