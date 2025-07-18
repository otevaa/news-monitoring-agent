# 🔍 NewsMonitor Pro - AI-Powered News Monitoring Platform

**A production-ready news monitoring platform with advanced AI capabilities and multi-provider support**

NewsMonitor Pro helps you track news mentions, monitor industry trends, and collect relevant articles automatically with intelligent AI analysis using OpenRouter and other providers.

![NewsMonitor Pro](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![OpenRouter](https://img.shields.io/badge/OpenRouter-API-orange.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![Render](https://img.shields.io/badge/Render-Deploy-purple.svg)

## ✨ Features

### 🎯 **Campaign Management**
- Create unlimited monitoring campaigns with custom keywords
- AI-powered keyword expansion using OpenRouter (DeepSeek R1 free model)
- Multiple frequency options (15min, hourly, daily, weekly)
- Pause, resume, and modify campaigns anytime
- Real-time statistics and analytics dashboard

### 🤖 **AI Integration with OpenRouter**
- **OpenRouter API**: Access to multiple AI models including free DeepSeek R1
- **Intelligent Article Filtering**: Relevance scoring with customizable thresholds
- **Smart Keyword Expansion**: Automatically discover related terms
- **Cost-Effective**: Free tier with DeepSeek R1 model included
- **Fallback Support**: OpenAI, Anthropic, and local models available

### 🔗 **Multiple Integrations**
- **Google Sheets**: Automatic spreadsheet creation and updates
- **Multi-Source Fetching**: RSS, Google News, Twitter/X
- **Airtable**: Advanced database with custom views and filters
- **Real-time Data**: Live updates and synchronization

### 📊 **Professional Dashboard**
- Modern, responsive interface with real-time statistics
- Campaign management with visual analytics
- Integration status monitoring
- Voice command support (French)
- User profile with AI settings management

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Git
- OpenRouter API key (free tier available)
- Google Cloud Console account (for Google Sheets integration)

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/news-monitoring-agent.git
cd news-monitoring-agent
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Get API Keys

#### OpenRouter API Key (Required)
1. Go to [OpenRouter](https://openrouter.ai)
2. Sign up for a free account
3. Go to [API Keys](https://openrouter.ai/keys)
4. Create a new API key
5. Copy the key (starts with `sk-or-v1-...`)

#### Google OAuth Setup (Optional - for Google Sheets)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Sheets API and Google Drive API
4. Create OAuth 2.0 credentials (Web application)
5. Add redirect URI: `http://localhost:5000/oauth2callback`
6. Download the JSON file and save as `client_secret.json` in project root

### 5. Configure Environment Variables
Create `.env` file in project root:
```env
# OpenRouter API (Required)
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/oauth2callback

# Flask Settings
FLASK_SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Default AI Model
DEFAULT_AI_MODEL=openrouter-auto
```

### 6. Start the Application
```bash
python app.py
```

### 7. Access the Application
Open your browser and go to `http://localhost:5000`

## 🤖 AI Configuration Guide

### OpenRouter Integration

The application uses OpenRouter as the default AI provider, which gives you access to multiple AI models including free options.

#### Available Models:
- **openrouter-auto** (Default): DeepSeek R1 free model
- **openrouter-gpt-4o-mini**: OpenAI GPT-4o Mini
- **openrouter-claude-3-sonnet**: Anthropic Claude 3 Sonnet
- **openrouter-llama-3-70b**: Meta Llama 3 70B

#### Usage Examples:

**With OpenAI Python Client:**
```python
from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="YOUR_OPENROUTER_API_KEY",
)

completion = client.chat.completions.create(
  extra_headers={
    "HTTP-Referer": "https://newsmonitor-pro.com",
    "X-Title": "NewsMonitor Pro",
  },
  model="deepseek/deepseek-r1-0528-qwen3-8b:free",
  messages=[
    {
      "role": "user",
      "content": "Expand these keywords: technology, AI"
    }
  ]
)
```

**With Requests Library:**
```python
import requests

response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": "Bearer YOUR_OPENROUTER_API_KEY",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://newsmonitor-pro.com",
    "X-Title": "NewsMonitor Pro",
  },
  json={
    "model": "deepseek/deepseek-r1-0528-qwen3-8b:free",
    "messages": [
      {
        "role": "user",
        "content": "Expand these keywords: technology, AI"
      }
    ]
  }
)
```

### AI Features Configuration

#### Relevance Threshold Settings
- **30-50%**: High volume, includes marginally relevant articles
- **60-70%**: Balanced approach (recommended)
- **80-90%**: High precision, only very relevant articles
- **90-95%**: Ultra-precise, minimal false positives

## 📱 Usage

### Setting Up AI Preferences
1. Go to **Profile → AI Settings**
2. Select your preferred AI model (OpenRouter Auto recommended)
3. Adjust relevance threshold (60-80% recommended)
4. Test the model with the built-in test feature
5. Save settings - they'll apply to all new campaigns

### Creating Your First Campaign
1. **Connect Google Sheets** (optional)
   - Click "Se connecter" in the header
   - Follow the OAuth flow to authorize

2. **Create a campaign**
   - Click "Nouvelle campagne" on the dashboard
   - Enter campaign name and keywords
   - Select monitoring frequency
   - Choose integrations (Google Sheets/Airtable)
   - AI settings are automatically applied
   - Save your campaign

3. **Monitor results**
   - View real-time statistics on the dashboard
   - Articles are automatically scored and filtered by AI
   - Access articles in your connected Google Sheets
   - Manage campaigns from the campaigns page

### Voice Commands (French)
- **"Créer une campagne"** - Create a new campaign
- **"Afficher les résultats"** - Show results
- **"Rechercher [keywords]"** - Search for keywords
- **"Paramètres IA"** - Open AI settings

### Integration Setup

#### Google Sheets (Recommended)
1. Complete OAuth setup in step 4 above
2. Click "Se connecter" in the application
3. Authorize Google Sheets access
4. New campaigns will automatically create spreadsheets
5. Articles are added in real-time with AI relevance scores

#### Airtable
1. Create an [Airtable](https://airtable.com) account
2. Create a new base and table
3. Get your API key from [Account Settings](https://airtable.com/account)
4. Get your Base ID from the API documentation
5. Configure in the Integrations page

## 🐳 Production Deployment

### Option 1: Render.com (Recommended)

1. **Prepare for deployment:**
   ```bash
   ./deploy_render.sh
   ```

2. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Deploy to Render"
   git push origin main
   ```

3. **Deploy on Render:**
   - Connect your GitHub repository to Render
   - Set environment variables:
     - `OPENROUTER_API_KEY`
     - `GOOGLE_CLIENT_ID`
     - `GOOGLE_CLIENT_SECRET`
     - `FLASK_SECRET_KEY`
     - `GOOGLE_REDIRECT_URI` (set to your Render URL + /oauth2callback)
   - Deploy the service

4. **Update Google OAuth:**
   - Add your Render URL to OAuth redirect URIs in Google Cloud Console
   - Format: `https://your-app-name.onrender.com/oauth2callback`

### Option 2: Docker Deployment

1. **Build and deploy:**
   ```bash
   ./deploy_docker.sh
   ```

2. **Configure environment:**
   - Edit `docker-compose.yml` with your settings
   - Set environment variables in `.env`

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

4. **Access application:**
   - Local: `http://localhost:5000`
   - Production: Configure domain and SSL

### Environment Variables for Production

```env
# Required
OPENROUTER_API_KEY=sk-or-v1-your-actual-key
FLASK_SECRET_KEY=your-production-secret-key

# Google OAuth (if using Sheets)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/oauth2callback

# Optional
DEFAULT_AI_MODEL=openrouter-auto
FLASK_ENV=production
```

## 📂 Project Structure

```
news-monitoring-agent/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (create this)
├── client_secret.json    # Google OAuth credentials (create this)
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile           # Docker container configuration
├── render.yaml          # Render.com deployment config
├── deploy_render.sh     # Render deployment script
├── deploy_docker.sh     # Docker deployment script
├── nginx.conf           # Nginx configuration for production
├── agent/
│   ├── __init__.py
│   ├── ai_keyword_expander.py    # OpenRouter AI integration
│   ├── fetch_multi_source.py     # Multi-source article fetching
│   ├── google_oauth.py           # Google OAuth handling
│   ├── campaign_manager.py       # Campaign management
│   ├── integrations.py           # Integration management
│   ├── scheduler.py              # Background task scheduling
│   ├── google_sheets_manager.py  # Google Sheets integration
│   ├── user_profile_manager.py   # User settings management
│   └── async_campaign_manager.py # Async campaign processing
├── static/
│   ├── style.css         # Application styling
│   └── app.js           # Frontend JavaScript
├── templates/
│   ├── dashboard.html    # Main dashboard
│   ├── campaigns.html    # Campaign management
│   ├── campaign_form.html # Campaign creation/editing
│   ├── integrations.html # Integration setup
│   └── profile.html      # User profile and AI settings
└── README.md            # This file
```

## 🔧 Management Commands

The application provides several management endpoints and features:

### API Endpoints
- `GET /api/campaigns` - List all campaigns
- `POST /api/campaigns` - Create new campaign
- `GET /api/articles` - Retrieve articles
- `POST /api/preview` - Preview search results
- `GET /api/campaigns/status` - Get campaign status

### Background Tasks
- Campaign execution with AI processing
- Article fetching from multiple sources
- Integration synchronization
- Relevance scoring and filtering

## 🎯 Use Cases

### Business Intelligence
- Monitor competitor mentions across news sources
- Track industry trends and market movements
- Collect market research data automatically
- Generate business intelligence reports

### Public Relations
- Brand mention monitoring across multiple platforms
- Crisis management with real-time alerts
- Media coverage tracking and analysis
- Sentiment analysis of news coverage

### Research & Academia
- Academic literature monitoring
- News analysis for research projects
- Trend identification for studies
- Data collection for analysis

### Personal Use
- Create topic-specific news feeds
- Professional development tracking
- Investment research automation
- Stay updated on specific interests

## 🔒 Security

- **OAuth 2.0** for Google authentication
- **Secure API key management** with environment variables
- **No sensitive data** stored in plain text
- **HTTPS-ready** for production deployment
- **Docker security** with non-root user configuration
- **Rate limiting** for API calls

## 🚀 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Common Issues

**OpenRouter API not working:**
- Check your API key is valid
- Verify the model name is correct
- Check your OpenRouter usage limits

**Google Sheets not connecting:**
- Verify OAuth credentials are set up correctly
- Check redirect URI matches exactly
- Ensure Google Sheets API is enabled

**Docker deployment issues:**
- Check environment variables are set
- Verify ports are available
- Review Docker logs for errors

### Getting Help

- 📧 Email: support@newsmonitor-pro.com
- 💬 Discord: [Join our community](https://discord.gg/newsmonitor)
- 📚 Documentation: [Full documentation](https://docs.newsmonitor-pro.com)
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/news-monitoring-agent/issues)

## 🙏 Acknowledgments

- **OpenRouter** for providing accessible AI model APIs
- **Google** for Sheets and OAuth APIs
- **Flask** community for the excellent framework
- **DeepSeek** for the free R1 model
- **Render** for simple deployment platform

---

**Made with ❤️ for the news monitoring community**

*NewsMonitor Pro - Intelligence at your fingertips*