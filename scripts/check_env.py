from dotenv import load_dotenv
import os

# Load .env from the same folder as the script
from pathlib import Path
basedir = Path(__file__).parent
load_dotenv(basedir / ".env")

# Read variables
openai_key = os.getenv("OPENAI_API_KEY")
notion_token = os.getenv("NOTION_TOKEN")
notion_db_id = os.getenv("NOTION_DATABASE_ID")

print("OPENAI_API_KEY:", openai_key)
print("NOTION_TOKEN:", notion_token)
print("NOTION_DATABASE_ID:", notion_db_id)