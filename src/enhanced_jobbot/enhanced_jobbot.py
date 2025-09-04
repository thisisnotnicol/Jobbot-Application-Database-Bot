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

- Position: Job title
- Company: Company name
- Salary: Full salary range or amount (e.g., "$80,000 - $120,000", "$50/hour", "Competitive", or leave empty if not mentioned)
- Commitment: Employment type (Full time, Part time, Contract, Freelance, Internship)
- Industry: All relevant industries (e.g., ["Technology", "Healthcare", "Finance"])
- Location: All locations mentioned, use "Remote" if remote work is mentioned (e.g., ["New York", "Remote"], ["San Francisco", "Los Angeles"])

IMPORTANT:
- Respond with ONLY valid JSON, no markdown code blocks, no explanations, no backticks
- For Salary: Include the full range if provided, don't abbreviate (e.g. "$80,000-$120,000 per year")
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
{job_text[:4000]}
"""
    text_output = ""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        text_output = response.choices[0].message.content
        if text_output is None or text_output.strip() == "":
            logging.error("OpenAI returned empty or None response")
            fallback_fields = {"Full Description": job_text, "Summary": generate_job_summary(job_text)}
            return fallback_fields

        text_output = text_output.strip()

        # Handle markdown-wrapped JSON responses
        if "```json" in text_output:
            # Find and extract JSON content between ```json and ```
            start_idx = text_output.find("```json") + 7
            end_idx = text_output.find("```", start_idx)
            if end_idx != -1:
                text_output = text_output[start_idx:end_idx].strip()
        elif "```" in text_output:
            # Handle plain ``` wrapper
            parts = text_output.split("```")
            if len(parts) >= 3:
                text_output = parts[1].strip()

        # Remove any remaining newlines at start/end
        text_output = text_output.strip()

        if not text_output:
            logging.error("Empty text after cleaning OpenAI response")
            fallback_fields = {"Full Description": job_text, "Summary": generate_job_summary(job_text)}
            return fallback_fields

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
        logging.error(f"Full raw response that failed to parse: '{text_output}'")
        logging.error(f"Original response before cleaning: '{response.choices[0].message.content}'")
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

def find_or_create_company(company_name):
    """Find existing company or create new one in the linked database"""
    if not company_name or company_name.strip() == "":
        return None

    try:
        # First, we need to get the Company property to find the linked database ID
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
                "property": "Name",  # Assuming the company name field is called "Name"
                "title": {
                    "equals": company_name.strip()
                }
            }
        )

        # If company exists, return its ID
        if search_results.get("results"):
            company_id = search_results["results"][0]["id"]
            logging.info(f"Found existing company: {company_name} (ID: {company_id})")
            return company_id

        # If company doesn't exist, create it
        new_company = notion.pages.create(
            parent={"database_id": company_database_id},
            properties={
                "Name": {"title": [{"text": {"content": company_name.strip()}}]}
            }
        )

        company_id = new_company["id"]
        logging.info(f"Created new company: {company_name} (ID: {company_id})")
        return company_id

    except Exception as e:
        logging.error(f"Error handling company '{company_name}': {e}")
        return None

def check_available_fields():
    """Check what fields are available in the current Notion database"""
    try:
        database_info = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        properties = database_info.get('properties', {})

        # Log all available properties for debugging
        logging.info("Available Notion database fields:")
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get('type', 'unknown')
            logging.info(f"  - {prop_name} ({prop_type})")

        available_fields = {
            'job_summary': 'Job Summary' in properties,
            'job_desc_part_2': 'Job Description Part 2' in properties,
            'job_desc_part_3': 'Job Description Part 3' in properties,
            'job_desc_part_4': 'Job Description Part 4' in properties,
            'job_desc_part_5': 'Job Description Part 5' in properties
        }

        # Check for required fields
        required_fields = ['Position', 'Company', 'Salary', 'Location', 'Industry', 'Commitment', 'Status', 'Job URL', 'Processed']
        missing_fields = []
        for field in required_fields:
            if field not in properties:
                missing_fields.append(field)

        if missing_fields:
            logging.warning(f"Missing required database fields: {missing_fields}")
        else:
            logging.info("All required database fields are present")

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

def add_to_notion(fields, job_url, page_id):
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

        # Validate and clean multi-select fields
        def clean_multiselect_values(values, field_name):
            """Clean and validate multi-select values for Notion"""
            if not values:
                return []

            if isinstance(values, str):
                values = [values]

            cleaned = []
            for value in values:
                if value and isinstance(value, str):
                    # Remove special characters that might cause issues
                    clean_value = str(value).strip()[:100]  # Limit length
                    if clean_value:
                        cleaned.append(clean_value)

            logging.info(f"{field_name} values: {cleaned}")
            return cleaned

        # Clean the multi-select fields
        industry_values = clean_multiselect_values(fields.get("Industry", []), "Industry")
        location_values = clean_multiselect_values(fields.get("Location", []), "Location")
        commitment_values = clean_multiselect_values(commitment_list, "Commitment")

        # Handle company relation
        company_name = fields.get("Company", "")
        company_id = find_or_create_company(company_name) if company_name else None

        # Base properties that every job entry will have
        properties = {
            "Position": {"title": [{"text": {"content": fields.get("Position", "Unknown")}}]},
            "Status": {"select": {"name": "Researching"}},
            "Active v Archived": {"status": {"name": "In progress"}},
            "Job URL": {"url": job_url},
            "Salary": {"rich_text": [{"text": {"content": fields.get("Salary", "")}}]},
            "Commitment": {"multi_select": [{"name": c} for c in commitment_values]},
            "Industry": {"multi_select": [{"name": i} for i in industry_values]},
            "Location": {"multi_select": [{"name": l} for l in location_values]},
            "Processed": {"checkbox": True},
        }

        # Add company relation if we have a company ID
        if company_id:
            properties["Company"] = {"relation": [{"id": company_id}]}

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

        # Log what we're about to update
        logging.info(f"Updating page {page_id} with properties: {list(properties.keys())}")

        notion.pages.update(
            page_id=page_id,
            properties=properties
        )

        # Log results
        parts_used = min(len(description_chunks), len([f for f, available in field_mapping if available]))
        total_chars = len(full_description)

        logging.info(f"Job updated in Notion: {fields.get('Position', 'Unknown')}")
        logging.info(f"Company: {fields.get('Company', 'Not found')} {'(linked)' if company_id else '(not linked)'}")
        logging.info(f"Salary: {fields.get('Salary', 'Not found')}")
        logging.info(f"Location: {fields.get('Location', 'Not found')}")
        logging.info(f"Commitment: {fields.get('Commitment', 'Not found')}")
        logging.info(f"Industry: {fields.get('Industry', 'Not found')}")
        logging.info(f"Summary generated: {'✓' if summary else '✗'}")
        logging.info(f"Description split into {parts_used} part(s)")
        logging.info(f"Total characters preserved: {total_chars}")

        if not available_fields['job_summary']:
            logging.info("💡 Add 'Job Summary' field to Notion for separate summary storage")

        missing_desc_fields = sum(1 for available in available_fields.values() if not available and 'job_desc' in str(available))
        if missing_desc_fields > 0:
            logging.info(f"💡 Add {missing_desc_fields} more 'Job Description Part X' field(s) for full text preservation")

    except Exception as e:
        logging.error(f"Error updating job in Notion: {e}")
        logging.error(f"Fields that were being processed: {fields}")
        logging.error(f"Page ID: {page_id}")
        logging.error(f"Properties that failed: {list(properties.keys()) if 'properties' in locals() else 'properties not created'}")
        # Try to mark as processed anyway to avoid infinite loops
        try:
            notion.pages.update(
                page_id=page_id,
                properties={"Processed": {"checkbox": True}}
            )
            logging.info("Marked page as processed despite error")
        except Exception as inner_e:
            logging.error(f"Failed to mark page as processed: {inner_e}")

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

            unprocessed_pages = query_results.get("results", [])
            logging.info(f"Found {len(unprocessed_pages)} unprocessed pages")

            for page in unprocessed_pages:
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
                add_to_notion(fields_dict, job_url, page["id"])

            logging.info("Cycle complete. Waiting 5 minutes before next check...")
            time.sleep(300)

        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(300)

if __name__ == "__main__":
    main()
