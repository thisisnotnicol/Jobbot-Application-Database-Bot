# JobBot Slack Integration Setup Guide

This guide will help you set up the JobBot Slack integration so you can automatically create Notion pages from job URLs posted in Slack.

## 🎯 What This Does

- **Direct Messages**: Send job URLs directly to the bot
- **Channel Mentions**: `@jobbot https://job-url.com` in any channel
- **Slash Command**: `/addjob https://job-url.com`
- **Auto-Processing**: Bot extracts job info and creates Notion pages automatically

## 📋 Prerequisites

1. ✅ JobBot environment already set up (OpenAI API key, Notion token, database)
2. ✅ Slack workspace admin access
3. ✅ Python dependencies installed

## 🚀 Step 1: Create Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. Enter:
   - **App Name**: `JobBot`
   - **Workspace**: Select your workspace
4. Click **"Create App"**

## 🔧 Step 2: Configure App Permissions

### OAuth & Permissions
1. Go to **"OAuth & Permissions"** in the sidebar
2. Under **"Bot Token Scopes"**, add these scopes:
   ```
   app_mentions:read
   chat:write
   channels:history
   groups:history
   im:history
   mpim:history
   commands
   ```
3. Click **"Install to Workspace"**
4. Copy the **"Bot User OAuth Token"** (starts with `xoxb-`)

### App-Level Tokens (for Socket Mode)
1. Go to **"Basic Information"** → **"App-Level Tokens"**
2. Click **"Generate Token and Scopes"**
3. Name: `JobBot Socket Token`
4. Add scope: `connections:write`
5. Click **"Generate"**
6. Copy the token (starts with `xapp-`)

## 📡 Step 3: Enable Socket Mode

1. Go to **"Socket Mode"** in the sidebar
2. Toggle **"Enable Socket Mode"** to ON
3. This allows the bot to run locally without webhooks

## ⚡ Step 4: Configure Events

1. Go to **"Event Subscriptions"**
2. Toggle **"Enable Events"** to ON
3. Under **"Subscribe to bot events"**, add:
   ```
   app_mention
   message.channels
   message.groups
   message.im
   message.mpim
   team_join
   ```

## 🔀 Step 5: Add Slash Command (Optional)

1. Go to **"Slash Commands"**
2. Click **"Create New Command"**
3. Configure:
   - **Command**: `/addjob`
   - **Request URL**: Not needed (using Socket Mode)
   - **Short Description**: `Add job posting to Notion`
   - **Usage Hint**: `https://example.com/job-posting`

## 🔐 Step 6: Update Environment Variables

Add these to your `.env` file:

```env
# Existing variables
OPENAI_API_KEY=your_openai_key
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id

# New Slack variables
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
```

## 🏃‍♂️ Step 7: Install Dependencies

```bash
cd jobbot_clean
pip install -r requirements.txt
```

## ▶️ Step 8: Start the Bot

```bash
python src/enhanced_jobbot/slack_bot.py
```

You should see:
```
🚀 Starting JobBot Slack Integration...
✓ Environment variables configured
✓ Slack app created and configured
✓ Socket Mode enabled
✓ Bot installed in workspace
🤖 Bot is ready!
```

## 💬 Step 9: Test the Bot

### In Slack, try:

1. **Direct Message**:
   - Find the JobBot app in your Slack
   - Send: `https://jobs.lever.co/example/job-123`

2. **Channel Mention**:
   - In any channel where the bot is invited
   - Type: `@JobBot https://jobs.lever.co/example/job-123`

3. **Slash Command**:
   - Type: `/addjob https://jobs.lever.co/example/job-123`

## 🎉 Expected Behavior

1. **Processing Message**: Bot shows "🔍 Processing job posting..."
2. **AI Extraction**: Fetches page content and extracts job details
3. **Notion Creation**: Creates new page in your Jobs database
4. **Success Message**: Shows extracted job details with "View in Notion" button

## 🔧 Troubleshooting

### Bot doesn't respond
- ✅ Check environment variables are set
- ✅ Verify bot token starts with `xoxb-`
- ✅ Ensure Socket Mode is enabled
- ✅ Check bot is installed in workspace

### "Missing permissions" error
- ✅ Add required OAuth scopes (see Step 2)
- ✅ Reinstall bot to workspace
- ✅ Invite bot to channels where you want to use it

### Can't create Notion pages
- ✅ Verify NOTION_TOKEN and NOTION_DATABASE_ID
- ✅ Check Notion integration has write access to database
- ✅ Ensure Company field is set up as relation (if using)

### Bot processes but fails on specific URLs
- ✅ Some job sites block automated access
- ✅ Check logs for specific error messages
- ✅ Try with different job posting URLs

## 🔄 Production Deployment

For production use:

### Option 1: Always-on Server
- Deploy to cloud server (AWS, DigitalOcean, etc.)
- Use process manager (PM2, systemd)
- Set up monitoring and logging

### Option 2: Local Development
- Run locally during work hours
- Use `screen` or `tmux` to keep running
- Perfect for personal/small team use

## 📚 Usage Examples

### Personal Workflow
```
1. Browse job boards
2. Copy interesting job URLs
3. DM them to JobBot in Slack
4. Review organized info in Notion
5. Track application progress
```

### Team Workflow
```
1. Share job postings in #job-hunting channel
2. @mention JobBot with URLs
3. Team sees extracted info immediately
4. All jobs automatically saved to shared Notion
```

## 🆘 Support

If you run into issues:

1. Check the console logs where the bot is running
2. Verify all environment variables are correct
3. Test with simple job URLs first (LinkedIn, Indeed)
4. Check Slack app configuration matches this guide

The bot runs locally, so you'll see detailed logs of what's happening!
