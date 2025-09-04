# JobBot Slack Integration Guide

## ✅ Current Status

Your JobBot Slack integration is now **running automatically** as a background service on your Mac!

- **Service Status**: Running (PID: 16527)
- **Memory Usage**: ~78 MB
- **Auto-restart**: Enabled (will restart if it crashes)
- **Start on login**: Enabled

## 🎯 How It Works

The bot continuously monitors your Slack workspace and:

1. **Listens for mentions** - When you @ mention the bot with a job URL
2. **Processes job postings** - Extracts key information using AI
3. **Saves to Notion** - Automatically creates entries in your Notion database
4. **Responds in Slack** - Provides a summary of the processed job

## 💬 Using the Bot in Slack

### Method 1: Mention the bot
```
@jobbot check out this job: https://jobs.ashbyhq.com/notion/...
```

### Method 2: Direct Message
Send a job URL directly to the bot in a DM - no mention needed!

### What the bot extracts:
- **Position** - Job title
- **Company** - Company name  
- **Summary** - 2-3 sentence description
- **Location** - Job locations
- **Salary** - If mentioned
- **Commitment** - Full-time, Part-time, etc.
- **Industry** - Relevant industries

## 🛠 Managing the Service

The bot runs automatically in the background. Use these commands to manage it:

### Check Status
```bash
./manage_bot.sh status
```

### View Logs
```bash
./manage_bot.sh logs        # Last 50 lines
./manage_bot.sh follow      # Real-time logs (Ctrl+C to exit)
```

### Control the Service
```bash
./manage_bot.sh start       # Start the bot
./manage_bot.sh stop        # Stop the bot
./manage_bot.sh restart     # Restart the bot
```

### Test Configuration
```bash
./manage_bot.sh test        # Check all dependencies
```

## 🔧 Troubleshooting

### "Dispatch Failed" Error in Slack

This error means Slack couldn't deliver the event to your bot. The bot now handles this automatically by:

1. **Auto-reconnecting** when connection is lost
2. **Retrying** failed operations (up to 5 times)
3. **Logging** all errors for debugging
4. **Restarting** automatically if it crashes

If you still see this error:

1. Check if the bot is running:
   ```bash
   ./manage_bot.sh status
   ```

2. Restart the bot:
   ```bash
   ./manage_bot.sh restart
   ```

3. Check the error log:
   ```bash
   tail -50 slack_bot_error.log
   ```

### Bot Not Responding

1. **Check Slack App Settings**:
   - Go to https://api.slack.com/apps
   - Select your app (JobBot)
   - Ensure **Socket Mode** is ON
   - Check **Event Subscriptions** is ON
   - Verify OAuth scopes include: `app_mentions:read`, `chat:write`

2. **Verify Environment Variables**:
   ```bash
   grep "SLACK" .env
   ```
   Should show both `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN`

3. **Check Recent Logs**:
   ```bash
   ./manage_bot.sh logs
   ```

### Notion Not Updating

1. **Check Notion Connection**:
   - Verify `NOTION_TOKEN` is set in `.env`
   - Confirm `NOTION_DATABASE_ID` is correct
   - Check the database has required properties

2. **Look for Notion Errors**:
   ```bash
   grep -i notion slack_bot_runtime.log | tail -20
   ```

### Job Content Not Extracted

Some sites block automated access. The bot will:
- Try multiple extraction methods
- Provide a fallback summary if extraction fails
- Still save the job URL to Notion for manual review

## 📊 Monitoring

### Log Files

- **Main Log**: `slack_bot_runtime.log` - All bot activity
- **Error Log**: `slack_bot_error.log` - Errors and exceptions
- **Job Processing**: `jobbot.log` - Detailed job processing

### Health Checks

The bot automatically:
- Pings Slack every 30 seconds to maintain connection
- Reconnects if disconnected
- Restarts after crashes (max 5 attempts)
- Logs all activities for debugging

## 🚀 Advanced Features

### Processing Multiple Jobs

You can send multiple job URLs in one message:
```
@jobbot Please check these:
https://job-url-1.com
https://job-url-2.com
https://job-url-3.com
```

### Job Description Limits

- Notion has a 2000 character limit for rich text fields
- The bot automatically truncates long descriptions
- Full descriptions are kept in the first 2000 characters

## 🔄 Updates and Maintenance

### Update the Bot Code

1. Make changes to `run_slack_bot.py`
2. Restart the service:
   ```bash
   ./manage_bot.sh restart
   ```

### Clear Logs

```bash
echo "" > slack_bot_runtime.log
echo "" > slack_bot_error.log
```

### Uninstall the Service

```bash
./manage_bot.sh uninstall
```

## 📝 Quick Reference

| Command | Description |
|---------|-------------|
| `./manage_bot.sh status` | Check if bot is running |
| `./manage_bot.sh restart` | Fix most issues |
| `./manage_bot.sh follow` | Watch live activity |
| `./manage_bot.sh test` | Verify setup |

## ✨ Tips

1. **Test the bot** by mentioning it with a simple message first
2. **Use job-specific domains** for best results (greenhouse.io, lever.co, ashbyhq.com)
3. **Check Notion** after processing to verify data quality
4. **Monitor logs** occasionally to catch any issues early

## 🆘 Need Help?

1. Run diagnostics: `./manage_bot.sh test`
2. Check recent errors: `tail -30 slack_bot_error.log`
3. Restart the service: `./manage_bot.sh restart`
4. Review this guide for common issues

The bot is designed to be resilient and self-healing. Most issues resolve automatically within 30 seconds to 5 minutes.

---

**Last Updated**: September 3, 2025
**Status**: ✅ Running and Monitoring for Jobs