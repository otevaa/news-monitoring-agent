# 🔍 NewsMonitor Pro - Multi-AI News Monitoring Platform

**A professional news monitoring platform with advanced AI capabilities and multiple provider support**

NewsMonitor Pro helps you track news mentions, monitor industry trends, and collect relevant articles automatically with intelligent AI analysis. Choose from multiple AI providers based on your budget and accuracy needs.

![NewsMonitor Pro Dashboard](https://via.placeholder.com/800x400/2563eb/ffffff?text=NewsMonitor+Pro+Dashboard)

## ✨ Features

### 🎯 **Campaign Management**
- Create unlimited monitoring campaigns
- Flexible keyword-based searches with AI expansion
- Multiple frequency options (15min, hourly, daily, weekly)
- Pause, resume, and modify campaigns anytime
- Real-time statistics and analytics

### 🤖 **Multi-AI Provider Support**
- **OpenAI GPT-3.5/4**: Highest accuracy and advanced analysis
- **HuggingFace BERT**: Free open-source sentiment analysis
- **Ollama Local**: Complete privacy with local LLM processing
- **Anthropic Claude**: Cost-effective alternative to OpenAI
- **Basic Fallback**: Keyword matching when AI is unavailable

### 🧠 **AI-Powered Features**
- **Intelligent Article Filtering**: Relevance scoring with customizable thresholds
- **Smart Keyword Expansion**: Automatically discover related terms
- **Priority Alert System**: Detect breaking news and urgent content
- **Cost Optimization**: Choose free or paid providers based on your needs

### 🔗 **Multiple Integrations**
- **Google Sheets**: Automatic spreadsheet creation and updates
- **Multi-Source Fetching**: RSS, Reddit, Facebook, X/Twitter, LinkedIn
- **Airtable**: Advanced database with custom views and filters
- Easy setup with guided configuration

### 📊 **Professional Dashboard**
- Beautiful, modern interface with responsive design
- Real-time campaign statistics and AI metrics
- Voice command support in French
- Integration status monitoring
- User profile with AI settings management

### 🔄 **Automated Scheduling**
- Background campaign execution with AI processing
- Intelligent frequency management
- Error handling and logging
- Manual campaign triggers

### 🛡️ **Enterprise Features**
- API access for custom integrations
- Multiple AI provider testing
- Data export capabilities
- Secure OAuth authentication
- Professional design and UX

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Google Cloud Console account (for Google Sheets)
- AI Provider API key (OpenAI, Anthropic, etc.) - optional
- Airtable account (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-repo/news-monitoring-agent.git
   cd news-monitoring-agent
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and AI preferences
   ```

5. **Set up AI Provider** (Choose one or multiple):
   
   **Option A: OpenAI (Recommended for accuracy)**
   - Get API key from [OpenAI Platform](https://platform.openai.com/api-keys)
   - Add to `.env`: `OPENAI_API_KEY=your-key-here`
   - Set model: `DEFAULT_AI_MODEL=openai-gpt3.5`

   **Option B: HuggingFace (Free)**
   - No API key required
   - Set model: `DEFAULT_AI_MODEL=huggingface-bert`

   **Option C: Ollama (Local & Private)**
   - Install Ollama from [ollama.ai](https://ollama.ai)
   - Run: `ollama pull llama2`
   - Set model: `DEFAULT_AI_MODEL=ollama-llama2`

   **Option D: Anthropic Claude (Cost-effective)**
   - Get API key from [Anthropic Console](https://console.anthropic.com/)
   - Add to `.env`: `ANTHROPIC_API_KEY=your-key-here`
   - Set model: `DEFAULT_AI_MODEL=anthropic-claude`

6. **Configure Google OAuth** (for Google Sheets integration)
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Google Sheets API and Google Drive API
   - Create OAuth 2.0 credentials
   - Download and save as `client_secret.json` in the project root

7. **Start the application**
   ```bash
   python app.py
   ```

8. **Open your browser**
   Navigate to `http://localhost:5000`

## 🤖 AI Configuration Guide

### Choosing the Right AI Provider

| Provider | Cost | Accuracy | Privacy | Setup Complexity |
|----------|------|----------|---------|------------------|
| OpenAI GPT-4 | $$$$ | ⭐⭐⭐⭐⭐ | ⭐⭐ | Easy |
| OpenAI GPT-3.5 | $$$ | ⭐⭐⭐⭐ | ⭐⭐ | Easy |
| Anthropic Claude | $$$ | ⭐⭐⭐⭐ | ⭐⭐ | Easy |
| HuggingFace BERT | Free | ⭐⭐⭐ | ⭐⭐⭐ | Easy |
| Ollama Local | Free | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Medium |
| Basic Fallback | Free | ⭐⭐ | ⭐⭐⭐⭐⭐ | None |

### AI Features Configuration

#### Relevance Threshold Settings
- **30-50%**: High volume, includes marginally relevant articles
- **60-70%**: Balanced approach (recommended)
- **80-90%**: High precision, only very relevant articles
- **90-95%**: Ultra-precise, minimal false positives

#### Cost Optimization Tips
1. **Start with HuggingFace** for testing campaigns
2. **Use higher thresholds** to reduce API calls
3. **Combine providers**: Free for initial filtering, paid for final analysis
4. **Monitor usage** in the Profile → AI Settings page

## 📱 Usage

### Setting Up AI Preferences

1. **Go to Profile → AI Settings**
2. **Select your preferred AI model**
3. **Adjust relevance threshold** (60-80% recommended)
4. **Test the model** with the built-in test feature
5. **Save settings** - they'll apply to all new campaigns

### Creating Your First Campaign

1. **Connect your Google account** (if using Google Sheets)
   - Click "Se connecter" in the header
   - Follow the OAuth flow

2. **Create a campaign**
   - Click "Nouvelle campagne" on the dashboard
   - Enter campaign name and keywords
   - Select monitoring frequency
   - Choose your integrations (Google Sheets/Airtable)
   - AI settings are automatically applied from your profile
   - Save your campaign

3. **Monitor results**
   - View real-time statistics on the dashboard
   - Articles are automatically scored and filtered by AI
   - Access articles in your connected tools
   - Manage campaigns from the campaigns page

### Voice Commands (French)
- **"Créer une campagne"** - Create a new campaign
- **"Afficher les résultats"** - Show results
- **"Rechercher [keywords]"** - Search for keywords
- **"Paramètres IA"** - Open AI settings

### Integration Setup

#### Google Sheets
- Automatic setup through OAuth
- Creates organized spreadsheets
- Real-time article updates

#### Airtable
1. Get your API key from [Airtable Account](https://airtable.com/account)
2. Create a base and table
3. Configure in the Integrations page
4. Enter your API key, Base ID, and Table name

## 🎨 Interface

NewsMonitor Pro features a modern, professional interface designed for:
- **Clarity**: Clean, uncluttered design
- **Efficiency**: Quick access to all features
- **Trust**: Professional color palette and typography
- **Responsiveness**: Works on desktop, tablet, and mobile

### Color Palette
- Primary Blue: `#2563eb` - Trust and professionalism
- Success Green: `#10b981` - Positive actions
- Warning Orange: `#f59e0b` - Attention items
- Neutral Grays: `#f8fafc` to `#0f172a` - Balance and hierarchy

## 📂 Project Structure

```
news-monitoring-agent/
├── app.py                 # Main Flask application
├── manage.py             # CLI management script
├── requirements.txt      # Python dependencies
├── client_secret.json    # Google OAuth credentials (you create this)
├── campaigns.json        # Campaign data (auto-generated)
├── integrations.json     # Integration settings (auto-generated)
├── agent/
│   ├── __init__.py
│   ├── fetch_rss.py      # RSS feed fetching
│   ├── google_oauth.py   # Google OAuth handling
│   ├── campaign_manager.py # Campaign management
│   ├── integrations.py   # Integration management
│   └── scheduler.py      # Automated scheduling
├── static/
│   └── style.css         # Professional CSS styling
└── templates/
    ├── dashboard.html    # Main dashboard
    ├── campaigns.html    # Campaign management
    ├── campaign_form.html # Campaign creation/editing
    ├── integrations.html # Integration setup
    └── profile.html      # User profile
```

## 🔧 Management Commands

Use the built-in management script for easy administration:

```bash
# Start the server
python manage.py run

# Install dependencies
python manage.py install

# Check system status
python manage.py status

# Reset all data
python manage.py reset

# Show help information
python manage.py info
```

## 🔌 API Access

NewsMonitor Pro provides API endpoints for custom integrations:

- `GET /api/campaigns` - List campaigns
- `POST /api/campaigns` - Create campaign
- `GET /api/articles` - Retrieve articles
- `POST /api/search` - Manual search

Generate your API key in the Profile section.

## 🎯 Use Cases

### Business Intelligence
- Monitor competitor mentions
- Track industry trends
- Collect market research

### Public Relations
- Brand mention monitoring
- Crisis management alerts
- Media coverage tracking

### Research & Academia
- Literature monitoring
- News analysis projects
- Trend identification

### Personal Use
- Topic-specific news feeds
- Professional development
- Investment research

## 🔒 Security

- OAuth 2.0 for Google authentication
- Secure API key management
- No sensitive data stored in plain text
- HTTPS-ready for production deployment

## 🚀 Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Using Docker
```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "app.py"]
```

### Environment Variables
Set these for production:
- `FLASK_ENV=production`
- `SECRET_KEY=your-secret-key`
- `DATABASE_URL=your-database-url` (if using external database)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Available in the app's integrations section
- **Issues**: Report bugs via GitHub Issues
- **Features**: Request features via GitHub Discussions

## 🙏 Acknowledgments

- Google News RSS for news feeds
- Feather Icons for beautiful icons
- Inter font for typography
- Flask framework for web application

---

**Built with ❤️ for professional news monitoring**