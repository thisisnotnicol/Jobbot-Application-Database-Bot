# JobBot - Intelligent Job Application Database Manager

An AI-powered tool that automatically extracts job information from URLs and creates organized Notion pages. Now with **Slack integration** for the easiest workflow!

## 🚀 Three Ways to Use JobBot

### 1. 💬 Slack Integration (Recommended)
The easiest way to use JobBot - just paste URLs in Slack!

- **Direct Messages**: Send job URLs directly to the bot
- **Channel Mentions**: `@jobbot https://job-url.com` in any channel  
- **Slash Commands**: `/addjob https://job-url.com`
- **Instant Results**: Bot extracts info and creates Notion pages automatically

### 2. 🖥️ Command Line Tool
Perfect for one-off job additions:
```bash
python add_job.py "https://example.com/job-posting"
```

### 3. 🔄 Auto-Monitor Mode (Legacy)
Continuously monitors Notion for unprocessed URLs (old workflow):
```bash
python src/enhanced_jobbot/enhanced_jobbot.py
```

## ✨ Features

### Core Functionality
- **Smart Web Scraping**: Uses Playwright + BeautifulSoup to extract job content from any URL
- **AI-Powered Extraction**: OpenAI GPT-4o-mini extracts structured job data (position, company, salary, location, etc.)
- **Notion Integration**: Creates organized job pages with all extracted information
- **Company Relations**: Automatically finds or creates company pages in linked databases

### Enhanced Features
- ✅ **AI-Generated Summaries**: Creates concise 2-3 sentence job overviews
- ✅ **Complete Text Preservation**: Stores full job descriptions (no character limits)
- ✅ **Smart Text Splitting**: Intelligently breaks long descriptions across multiple fields
- ✅ **Company Management**: Links to company database (creates new companies if needed)
- ✅ **Rich Data Extraction**: Salary ranges, locations, industries, commitment types
- ✅ **Error Recovery**: Robust handling of difficult websites and parsing issues

## 📋 Prerequisites

1. **Python 3.8+**
2. **OpenAI API Key** - Get from [OpenAI Platform](https://platform.openai.com/)
3. **Notion Integration** - Create integration and get database access
4. **uv** (recommended) or pip for package management

## 🛠️ Installation

### Using uv (Recommended)

#### Install uv
```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Via pip (if you prefer)
pip install uv
```

#### Setup Project
```bash
# Clone the repository
git clone <your-repo-url>
cd enhanced-jobbot

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install project dependencies
uv pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

### Using Traditional pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

## 🍓 Raspberry Pi Setup

### Prerequisites
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and required system packages
sudo apt install python3 python3-pip python3-venv git chromium-browser -y

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

### Installation on Raspberry Pi
```bash
# Clone and setup project
git clone <your-repo-url>
cd enhanced-jobbot

# Create virtual environment with uv
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Install Playwright with Chromium (optimized for Pi)
playwright install chromium

# Set environment variable for Playwright on Pi
echo 'export PLAYWRIGHT_BROWSERS_PATH=/home/pi/.cache/ms-playwright' >> ~/.bashrc
source ~/.bashrc
```

### Running as a Service on Raspberry Pi

Create a systemd service for continuous operation:

```bash
# Create service file
sudo nano /etc/systemd/system/jobbot.service
```

Add this content:
```ini
[Unit]
Description=Enhanced JobBot Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/enhanced-jobbot
Environment=PATH=/home/pi/enhanced-jobbot/.venv/bin
ExecStart=/home/pi/enhanced-jobbot/.venv/bin/python -m enhanced_jobbot.enhanced_jobbot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable jobbot.service
sudo systemctl start jobbot.service
sudo systemctl status jobbot.service
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the project root:

**Required for all methods:**
```env
OPENAI_API_KEY=your_openai_api_key_here
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id
```

**Additional for Slack integration:**
```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
```

### Notion Database Setup
Your database needs these **required fields**:
- `Position` (Title)
- `Job Description` (Text) 
- `Job URL` (URL)
- `Processed` (Checkbox)
- `Status` (Select)
- `Salary` (Text)
- `Location` (Multi-select)
- `Industry` (Multi-select)
- `Commitment` (Multi-select)

**Optional enhanced fields** for maximum functionality:
- `Job Summary` (Text) - For AI-generated summaries
- `Job Description Part 2` (Text) - Extended descriptions
- `Job Description Part 3` (Text) - Extended descriptions
- `Job Description Part 4` (Text) - Extended descriptions
- `Job Description Part 5` (Text) - Extended descriptions

## 🎯 Usage

### Method 1: Slack Integration (Recommended)

#### Setup Slack Bot (one-time)
```bash
# Check all configuration
python check_config.py

# Start the Slack bot
python start_slack_bot.py
```

See [SLACK_SETUP.md](SLACK_SETUP.md) for detailed Slack app configuration.

#### Using the Bot in Slack
- **Direct message**: Send job URLs directly to @JobBot
- **Channel mention**: `@jobbot https://jobs.lever.co/company/position`
- **Slash command**: `/addjob https://example.com/careers/job-123`

The bot will:
1. Show "🔍 Processing job posting..."
2. Extract job information with AI
3. Create a new Notion page
4. Show extracted details with "View in Notion" button

### Method 2: Command Line Tool

```bash
# Process a single job URL
python add_job.py "https://example.com/job-posting"

# With verbose logging
python add_job.py --verbose "https://example.com/job-posting"
```

Perfect for:
- One-off job additions
- Batch processing via scripts
- Integration with other tools

### Method 3: Auto-Monitor Mode (Legacy)

```bash
# Run continuous monitoring
python src/enhanced_jobbot/enhanced_jobbot.py
```

This method:
1. Monitors Notion database every 5 minutes
2. Finds unprocessed job URLs (Processed = false)
3. Updates existing pages with extracted data
4. Marks them as processed

**Note**: You must manually create Notion pages with URLs first.

### What Gets Extracted
All methods extract:
- **Position/Job Title**
- **Company Name** (creates company page if using relations)
- **Salary Information** (ranges, hourly rates, etc.)
- **Employment Type** (Full-time, Part-time, Contract, etc.)
- **Industries** (Technology, Healthcare, Finance, etc.)
- **Locations** (Cities, Remote, Hybrid)
- **AI-Generated Summary** (2-3 sentence overview)
- **Full Job Description** (complete text, smartly split across fields)

## 🔄 Workflow Comparison

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **Slack Bot** | Daily use, team collaboration | Instant, user-friendly, no manual pages | Requires Slack setup |
| **Command Line** | Scripts, automation, one-offs | Simple, fast, scriptable | Terminal required |
| **Auto-Monitor** | Legacy workflows | Continuous processing | Must create pages manually |

**Recommendation**: Use **Slack integration** for the best user experience!

## 🔧 Development

### Project Structure
```
enhanced-jobbot/
├── src/enhanced_jobbot/        # Main package
│   ├── __init__.py
│   ├── enhanced_jobbot.py      # Enhanced bot (recommended)
│   └── jobbot.py              # Original bot
├── scripts/                   # Utility scripts
│   ├── check_env.py          # Environment check
│   ├── test_notion_access.py # Notion connectivity test
│   └── playwright_test.py    # Web scraping test
├── requirements.txt          # Dependencies
├── pyproject.toml           # Project configuration
├── README.md               # This file
└── .env                   # Environment variables (create this)
```

### Development Setup
```bash
# Install with development dependencies
uv pip install -r requirements.txt
uv pip install -e ".[dev]"

# Run tests
python -m pytest

# Format code
black src/ scripts/

# Type checking
mypy src/
```

## 🔍 Troubleshooting

### Quick Diagnostics
```bash
# Check all configuration and connections
python check_config.py
```

### Common Issues

**❓ Slack bot doesn't respond**
- Check `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` are set
- Verify Socket Mode is enabled in Slack app
- Ensure bot is installed in workspace
- Check console logs for errors

**❓ "Failed to scrape job content"**
- Some sites block automated scraping
- Try the URL manually in a browser
- Check if the page requires login/authentication
- Test with simple job sites first (LinkedIn, Indeed)

**❓ "Error creating Notion page"**
- Verify Notion integration has database write permissions
- Check that all required fields exist in your database
- Confirm `NOTION_TOKEN` is valid
- Ensure `Company` field is properly configured as relation

**❓ Company field not working**
- Company must be a **Relation** field (not Text)
- Linked database should have a "Name" field
- Bot will create new companies automatically

**❓ Location/Salary not appearing**
- Check these are **Multi-select** fields in Notion
- Verify field names match exactly
- Check console logs for data extraction details

**❓ "Playwright browser not found" (Raspberry Pi)**
```bash
# Reinstall Playwright browsers
playwright install chromium
# Or specify path
export PLAYWRIGHT_BROWSERS_PATH=/home/pi/.cache/ms-playwright
```

### Raspberry Pi Specific Issues

**❓ Memory issues**
```bash
# Increase swap space
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

**❓ Chromium crashes**
```bash
# Use lighter browser settings
export PLAYWRIGHT_CHROMIUM_ARGS="--no-sandbox --disable-dev-shm-usage"
```

## 📈 Advanced Features

### AI Summary Generation
The enhanced bot generates intelligent summaries that capture:
- Role level and key responsibilities
- Most important requirements
- Compensation and location info
- Company context when available

### Smart Text Handling
- Preserves complete job descriptions across multiple fields
- Splits text at natural boundaries (sentences, paragraphs)
- Falls back gracefully if enhanced fields aren't available
- Combines summary with description for maximum information density

## 🛡️ Security & Privacy

- API keys are stored in `.env` files (not committed to version control)
- All processing happens locally on your machine
- Data is only sent to OpenAI for extraction and Notion for storage
- No job data is stored or cached by the bot

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for GPT API
- Notion for database integration
- Microsoft Playwright for reliable web scraping
- Beautiful Soup for HTML parsing fallback

---

## 🚀 Quick Start Guide

### 1. Check Everything Works
```bash
python check_config.py
```

### 2. Choose Your Method

**Slack Integration (Easiest):**
```bash
python start_slack_bot.py
# Then use @jobbot in Slack
```

**Command Line (Simple):**
```bash
python add_job.py "https://job-url.com"
```

**Auto-Monitor (Legacy):**
```bash
python src/enhanced_jobbot/enhanced_jobbot.py
```

### 3. Test with a Job URL
Try with any job posting URL:
- LinkedIn Jobs
- Indeed
- Company career pages
- Lever, Greenhouse, etc.

## 📚 Documentation

- **[SLACK_SETUP.md](SLACK_SETUP.md)** - Complete Slack bot setup guide
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Code organization details
- **Console logs** - Check terminal output for detailed processing info

**Happy job hunting! 🎯✨**