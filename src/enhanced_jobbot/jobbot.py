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
        return fields
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from OpenAI response: {e}")
        logging.error(f"Raw OpenAI response: {text_output}")
        return {"Full Description": job_text}
    except Exception as e:
        logging.warning(f"Failed to extract fields from OpenAI: {e}")
        return {"Full Description": job_text}

def add_to_notion(fields, job_url):
    try:
        # Truncate job description to Notion's 2000 character limit
        job_description = fields.get("Full Description", "")
        if len(job_description) > 2000:
            job_description = job_description[:1997] + "..."

        # Handle commitment field - ensure it's in a list for multi_select
        commitment = fields.get("Commitment", "Full time")
        commitment_list = [commitment] if commitment else ["Full time"]

        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Position": {"title": [{"text": {"content": fields.get("Position", "Unknown")}}]},
                "Status": {"select": {"name": "Researching"}},
                "Active v Archived": {"status": {"name": "In progress"}},
                "Job URL": {"url": job_url},
                "Salary": {"rich_text": [{"text": {"content": fields.get("Salary", "")}}]},
                "Commitment": {"multi_select": [{"name": c} for c in commitment_list]},
                "Industry": {"multi_select": [{"name": i} for i in fields.get("Industry", [])]},
                "Location": {"multi_select": [{"name": l} for l in fields.get("Location", [])]},
                "Job Description": {"rich_text": [{"text": {"content": job_description}}]},
                "Processed": {"checkbox": True},
            }
        )
        logging.info(f"Job added to Notion: {fields.get('Position', 'Unknown')} at {fields.get('Company', 'Unknown')}")
    except Exception as e:
        logging.error(f"Error adding job to Notion: {e}")

# -----------------------------
# Main loop
# -----------------------------
def main():
    if not NOTION_DATABASE_ID:
        logging.error("NOTION_DATABASE_ID is not set in environment variables")
        return

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
