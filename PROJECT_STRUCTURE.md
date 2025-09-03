# Enhanced JobBot - Project Structure

## 📁 Directory Layout

```
enhanced-jobbot/
├── src/enhanced_jobbot/           # Main package source code
│   ├── __init__.py               # Package initialization and exports
│   ├── enhanced_jobbot.py        # Enhanced bot with AI summaries (RECOMMENDED)
│   └── jobbot.py                 # Original bot with JSON parsing fixes
├── scripts/                      # Utility and setup scripts
│   ├── check_env.py             # Environment variable validation
│   ├── getting_started.py       # Interactive setup guide for new users
│   ├── playwright_test.py       # Web scraping functionality test
│   ├── test_notion_access.py    # Notion API connection test
│   └── test_notion_rows.py      # Notion database operations test
├── .env.example                  # Environment variables template
├── .gitignore                   # Git ignore rules (excludes .env, cache, etc.)
├── LICENSE                      # MIT License
├── README.md                    # Complete project documentation
├── SUMMARY.md                   # Technical implementation summary
├── PROJECT_STRUCTURE.md         # This file - project organization guide
├── pyproject.toml              # Modern Python project configuration
├── requirements.txt            # Python dependencies list
└── setup.py                    # Automated project setup script
```

## 🧩 Core Components

### Main Package (`src/enhanced_jobbot/`)

**`__init__.py`**
- Package entry point and version info
- Exports main functions for easy importing
- Default points to enhanced bot

**`enhanced_jobbot.py`** ⭐ **RECOMMENDED**
- Complete rewrite with all improvements
- AI-generated job summaries using OpenAI
- Multi-field job description storage (no 2K limit)
- Smart text splitting at natural boundaries
- Backward compatible with existing databases
- Fixed JSON parsing from OpenAI responses
- Enhanced location field handling

**`jobbot.py`** 
- Original bot with critical fixes applied
- JSON parsing improvements
- Maintains original 2K character limit
- All original functionality preserved

### Utility Scripts (`scripts/`)

**`check_env.py`**
- Validates environment variables (.env file)
- Checks API key format and availability
- Quick diagnostic tool

**`getting_started.py`**
- Interactive guide for new users
- Step-by-step setup walkthrough
- Opens relevant websites for API key setup
- Validates configuration

**`test_notion_access.py`**
- Tests Notion API connectivity
- Validates database permissions
- Checks database schema

**`playwright_test.py`**
- Tests web scraping functionality
- Validates Playwright browser installation
- Useful for debugging scraping issues

### Configuration Files

**`pyproject.toml`**
- Modern Python project standards (PEP 518)
- Package metadata and dependencies
- Development tool configurations
- Command-line script definitions

**`requirements.txt`**
- Pin-specified dependencies for reproducible installs
- Compatible with pip, uv, and other package managers
- Includes all necessary packages for full functionality

**`.env.example`**
- Template for environment variables
- Copy to `.env` and fill in your actual API keys
- Includes optional configuration options

## 🚀 Usage Patterns

### Quick Start (New Users)
```bash
# Interactive setup guide
python scripts/getting_started.py

# Automated setup
python setup.py
```

### Development Workflow
```bash
# Check environment
python scripts/check_env.py

# Test connectivity
python scripts/test_notion_access.py

# Run enhanced bot
python -m enhanced_jobbot.enhanced_jobbot
```

### Package Installation
```bash
# With uv (recommended)
uv venv
uv pip install -r requirements.txt

# With pip
python -m venv venv
pip install -r requirements.txt
```

## 🔄 Data Flow

1. **Input**: Job URLs added to Notion database with `Processed = False`
2. **Scraping**: Playwright/BeautifulSoup extracts job content
3. **AI Processing**: OpenAI extracts structured data + generates summary
4. **Storage**: New Notion entries created with all extracted information
5. **Completion**: Original entries marked as `Processed = True`

## 🎯 Key Features by Component

### Enhanced Bot
- ✅ AI summaries for quick job overview
- ✅ Complete job description preservation
- ✅ Smart multi-field text distribution
- ✅ Backward compatibility
- ✅ Advanced error handling

### Original Bot
- ✅ JSON parsing fixes
- ✅ Reliable basic extraction
- ✅ 2000 character limit handling
- ✅ All original functionality

### Setup Scripts
- ✅ Automated environment detection
- ✅ Interactive user guidance
- ✅ Comprehensive validation testing
- ✅ Cross-platform compatibility

## 📦 Dependencies

### Core Runtime
- `openai` - AI-powered data extraction
- `notion-client` - Database integration
- `playwright` - Modern web scraping
- `beautifulsoup4` - HTML parsing fallback
- `requests` - HTTP client
- `python-dotenv` - Environment management

### Development (Optional)
- `pytest` - Testing framework
- `black` - Code formatting
- `mypy` - Type checking
- `flake8` - Linting

## 🔧 Configuration Options

### Environment Variables (.env)
```bash
# Required
OPENAI_API_KEY=sk-...           # OpenAI API access
NOTION_TOKEN=secret_...         # Notion integration token
NOTION_DATABASE_ID=...          # Target database ID

# Optional
LOG_LEVEL=INFO                  # Logging verbosity
PROCESSING_INTERVAL=300         # Seconds between cycles
MAX_RETRIES=3                   # Request retry attempts
```

### Notion Database Schema
**Required Fields:**
- Position (Title)
- Job Description (Text)
- Job URL (URL) 
- Processed (Checkbox)
- Status, Salary, Location, Industry, Commitment

**Optional Enhanced Fields:**
- Job Summary (Text) - AI summaries
- Job Description Part 2-5 (Text) - Extended storage

## 🚀 Deployment Options

### Local Development
```bash
python -m enhanced_jobbot.enhanced_jobbot
```

### Raspberry Pi Service
```bash
sudo systemctl start jobbot.service
```

### Docker (Future Enhancement)
```bash
docker run -d --env-file .env enhanced-jobbot
```

## 🔍 Troubleshooting Guide

### Common File Locations
- Logs: `jobbot.log` (in project root)
- Environment: `.env` (create from `.env.example`)
- Config: `pyproject.toml`
- Dependencies: `requirements.txt`

### Key Scripts for Debugging
- Environment issues: `python scripts/check_env.py`
- Notion problems: `python scripts/test_notion_access.py`
- Scraping issues: `python scripts/playwright_test.py`
- New user setup: `python scripts/getting_started.py`

This structure provides a clean, maintainable, and user-friendly foundation for the Enhanced JobBot project with clear separation of concerns and comprehensive tooling support.