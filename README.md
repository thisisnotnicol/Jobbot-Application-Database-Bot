# Enhanced JobBot - Automated Job Application Database Manager

An intelligent Python bot that automatically scrapes job postings, extracts structured data using AI, and populates your Notion database with comprehensive job information.

## 🚀 Features

### Core Functionality
- **Web Scraping**: Uses Playwright (with BeautifulSoup fallback) to extract job content from any URL
- **AI-Powered Extraction**: OpenAI GPT-4o-mini extracts structured job data (position, salary, location, etc.)
- **Notion Integration**: Automatically creates and updates entries in your job application database
- **Continuous Processing**: Monitors database every 5 minutes for new unprocessed job URLs

### Enhanced Features
- ✅ **AI-Generated Summaries**: Creates concise 2-3 sentence job overviews
- ✅ **Complete Text Preservation**: No more 2000 character limits - stores full job descriptions
- ✅ **Smart Text Splitting**: Intelligently breaks long descriptions across multiple fields
- ✅ **JSON Parsing Fix**: Resolved OpenAI markdown response parsing issues
- ✅ **Backward Compatibility**: Works with existing database structures

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
```env
OPENAI_API_KEY=your_openai_api_key_here
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id
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

### Quick Start
```bash
# Activate virtual environment
source .venv/bin/activate  # uv
# OR
source venv/bin/activate   # traditional pip

# Check environment setup
python scripts/check_env.py

# Test Notion access
python scripts/test_notion_access.py

# Run the enhanced bot (recommended)
python -m enhanced_jobbot.enhanced_jobbot

# OR run the original bot
python -m enhanced_jobbot.jobbot
```

### Using uv run (Alternative)
```bash
# Run enhanced bot
uv run python -m enhanced_jobbot.enhanced_jobbot

# Run original bot  
uv run python -m enhanced_jobbot.jobbot
```

### What Happens
1. Bot finds unprocessed job URLs in your database
2. Scrapes job content from each URL
3. Uses AI to extract structured data:
   - Position/Job Title
   - Company Name
   - Salary Information
   - Employment Type (Full-time, Part-time, etc.)
   - Industries
   - Locations
   - AI-generated summary
4. Creates new Notion entries with all extracted data
5. Marks original entries as processed
6. Repeats every 5 minutes

## 📊 Bot Comparison

| Feature | Original Bot | Enhanced Bot |
|---------|--------------|--------------|
| Web Scraping | ✅ | ✅ |
| AI Extraction | ✅ | ✅ |
| JSON Fix | ✅ | ✅ |
| AI Summaries | ❌ | ✅ |
| Full Text Preservation | ❌ (2K limit) | ✅ (10K+ chars) |
| Multi-part Descriptions | ❌ | ✅ |
| Smart Text Splitting | ❌ | ✅ |

**Recommendation**: Use `enhanced_jobbot.py` - it's backward compatible and includes all improvements.

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

### Common Issues

**❓ "No unprocessed jobs found"**
- Add job URLs to Notion with `Processed` = unchecked
- Verify `NOTION_DATABASE_ID` is correct

**❓ "Failed to scrape job content"**
- Some sites block automated scraping
- Try the URL manually in a browser
- Check if the page requires login/authentication

**❓ "Error adding job to Notion"**
- Verify Notion integration has database write permissions
- Check that all required fields exist in your database
- Confirm `NOTION_TOKEN` is valid

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

## Quick Reference Commands

```bash
# Environment setup
python scripts/check_env.py

# Test Notion access
python scripts/test_notion_access.py

# Run enhanced bot (recommended)
python -m enhanced_jobbot.enhanced_jobbot

# Run original bot
python -m enhanced_jobbot.jobbot

# Run with uv
uv run python -m enhanced_jobbot.enhanced_jobbot
```

**Happy job hunting! 🎯**