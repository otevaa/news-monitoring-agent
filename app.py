from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash
from functools import wraps
import atexit
import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

# Agent imports
from agent.fetch_multi_source import fetch_articles_multi_source, fetch_articles_rss
from agent.google_oauth import start_auth, finish_auth, get_sheets_service
from agent.async_campaign_manager import AsyncCampaignManager
from agent.google_sheets_manager import GoogleSheetsManager
from agent.scheduler import campaign_scheduler

# Database imports
from database.models import DatabaseManager, UserManager
from database.managers import DatabaseCampaignManager, DatabaseUserProfileManager, DatabaseIntegrationManager

# Auth imports
from auth.auth_manager import EnhancedAuthManager
from auth.security_manager import SecurityManager

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())

# Initialize core managers
def initialize_managers():
    """Initialize all core managers with error handling"""
    try:
        db_manager = DatabaseManager()
        auth_manager = EnhancedAuthManager()
        user_manager = UserManager(db_manager)
        campaign_manager = DatabaseCampaignManager(db_manager)
        profile_manager = DatabaseUserProfileManager(db_manager)
        integration_manager = DatabaseIntegrationManager(db_manager)
        security_manager = SecurityManager()
        
        return {
            'db_manager': db_manager,
            'auth_manager': auth_manager,
            'user_manager': user_manager,
            'campaign_manager': campaign_manager,
            'profile_manager': profile_manager,
            'integration_manager': integration_manager,
            'security_manager': security_manager
        }
    except Exception as e:
        print(f"Manager initialization failed: {e}")
        sys.exit(1)

def initialize_services():
    """Initialize external services with fallback handlers"""
    services = {}
    
    # Google Sheets Manager
    try:
        services['sheets_manager'] = GoogleSheetsManager()
    except Exception:
        class FallbackSheetsManager:
            def is_google_sheets_connected(self): return False
            def list_user_spreadsheets(self): return []
            def create_campaign_spreadsheet_for_user(self, user_id, name): return None
            def save_articles_to_spreadsheet(self, id, articles, campaign_name="", keywords=""): return False
            def delete_spreadsheet(self, id): return False
        services['sheets_manager'] = FallbackSheetsManager()
    
    # Async Campaign Manager
    try:
        services['async_campaign_manager'] = AsyncCampaignManager()
    except Exception:
        class FallbackAsyncCampaignManager:
            def get_task_status(self, task_id): return {'status': 'error', 'error': 'Manager not initialized'}
        services['async_campaign_manager'] = FallbackAsyncCampaignManager()
    
    return services

# Initialize all components
managers = initialize_managers()
services = initialize_services()

# Extract managers for global use
db_manager = managers['db_manager']
auth_manager = managers['auth_manager']
user_manager = managers['user_manager']
campaign_manager = managers['campaign_manager']
profile_manager = managers['profile_manager']
integration_manager = managers['integration_manager']
security_manager = managers['security_manager']

# Extract services for global use
sheets_manager = services['sheets_manager']
async_campaign_manager = services['async_campaign_manager']

# Start campaign scheduler
campaign_scheduler.start()
atexit.register(lambda: campaign_scheduler.stop())

# Utility functions
def get_dashboard_stats(user_id: str):
    """Get dashboard statistics for a user"""
    try:
        stats = campaign_manager.get_user_stats(user_id)
        return {
            'active_campaigns': stats.get('active_campaigns', 0),
            'total_articles': stats.get('total_articles', 0),
            'articles_today': stats.get('articles_today', 0),
            'total_campaigns': stats.get('total_campaigns', 0)
        }
    except Exception:
        return {'active_campaigns': 0, 'total_articles': 0, 'articles_today': 0, 'total_campaigns': 0}

def get_dashboard_integrations(user_id: str):
    """Get integration status for dashboard"""
    try:
        return {
            'google_sheets': integration_manager.is_google_sheets_connected(user_id),
            'airtable': bool(integration_manager.get_integration(user_id, 'airtable'))
        }
    except Exception:
        return {'google_sheets': False, 'airtable': False}

def check_google_sheets_access(user_id: str):
    """Check if Google Sheets is connected"""
    if not integration_manager.is_google_sheets_connected(user_id):
        return jsonify({'error': 'Not connected to Google Sheets'}), 401
    return None

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('signin'))
        return f(*args, **kwargs)
    return decorated_function

# Health check endpoint (minimal)
@app.route("/health")
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# Public routes
@app.route("/")
def home():
    if auth_manager.is_authenticated():
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/team")
def team():
    return render_template('team.html')

@app.route("/pricing")
def pricing():
    return render_template('pricing.html')

# Authentication routes
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        # Basic CSRF protection - check referer
        if request.referrer and not request.referrer.startswith(request.host_url):
            flash('Requête non autorisée', 'error')
            return render_template('auth.html')
            
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validate input
        if not email or not password:
            flash('Email et mot de passe requis', 'error')
            return render_template('auth.html')
            
        if not security_manager.validate_input(email, 254) or '@' not in email:
            flash('Email invalide', 'error')
            return render_template('auth.html')
        
        success, message = auth_manager.login_user(email, password, request)
        
        if success:
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'error')
    
    return render_template('auth.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    pending_google = session.get('pending_google_registration')
    
    if request.method == 'POST':
        # Basic CSRF protection
        if request.referrer and not request.referrer.startswith(request.host_url):
            flash('Requête non autorisée', 'error')
            return render_template('auth.html', pending_google=pending_google)
            
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        terms = request.form.get('terms')
        
        # Pre-fill from Google data if available
        if pending_google:
            name = name or pending_google.get('name', '')
            email = email or pending_google.get('email', '')
        
        # Enhanced input validation
        if not all([name, email, password, confirm_password]):
            flash('Tous les champs sont requis', 'error')
            return render_template('auth.html', pending_google=pending_google)
            
        # Validate input security
        if not security_manager.validate_input(name, 100) or len(name) < 2:
            flash('Nom invalide (2-100 caractères, pas de caractères spéciaux)', 'error')
            return render_template('auth.html', pending_google=pending_google)
            
        if not security_manager.validate_input(email, 254) or '@' not in email or '.' not in email.split('@')[1]:
            flash('Adresse email invalide', 'error')
            return render_template('auth.html', pending_google=pending_google)
            
        if len(password) < 8:
            flash('Le mot de passe doit contenir au moins 8 caractères', 'error')
            return render_template('auth.html', pending_google=pending_google)
        
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas', 'error')
            return render_template('auth.html', pending_google=pending_google)
        
        if not terms:
            flash('Vous devez accepter les conditions d\'utilisation', 'error')
            return render_template('auth.html', pending_google=pending_google)
        
        user_id = auth_manager.register_user(email, password, name)
        
        if user_id:
            # Auto-connect Google Sheets if available
            if pending_google and pending_google.get('credentials'):
                try:
                    integration_manager.update_integration(
                        user_id, 'google_sheets', 
                        pending_google['credentials'], is_active=True
                    )
                except Exception:
                    pass
                session.pop('pending_google_registration', None)
            
            flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('signin'))
        else:
            flash('Erreur lors de la création du compte. Cet email est peut-être déjà utilisé.', 'error')
    
    return render_template('auth.html', pending_google=pending_google)

@app.route('/logout')
def logout():
    auth_manager.logout_user()
    return redirect(url_for('home'))

# Quick search for public access
@app.route('/api/quick-search', methods=['POST'])
def quick_search():
    try:
        # Rate limiting for search
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        if auth_manager.rate_limiter.is_rate_limited(f"search_{client_ip}", max_attempts=10, window_minutes=5):
            return jsonify({'error': 'Trop de requêtes. Essayez plus tard.'}), 429
        
        auth_manager.rate_limiter.record_attempt(f"search_{client_ip}")
        
        data = request.get_json()
        if not data:
            return jsonify({'articles': []})
            
        query = data.get('query', '').strip()
        limit = min(int(data.get('limit', 3)), 10)  # Limit maximum results
        
        if not query or not security_manager.validate_input(query, 200):
            return jsonify({'articles': []})
        
        current_user = session.get('user_id')
        articles = fetch_articles_multi_source(query, max_items=limit, user_id=current_user)
        
        formatted_articles = []
        for article in articles[:limit]:
            # Sanitize article data to prevent XSS
            title = security_manager.validate_input(article.get('title', ''), 200) and article.get('title', '')[:200]
            source = security_manager.validate_input(article.get('source', ''), 100) and article.get('source', '')[:100]
            summary = security_manager.validate_input(article.get('summary', article.get('description', '')), 300) and article.get('summary', article.get('description', ''))[:150]
            
            if title and source:  # Only include valid articles
                formatted_articles.append({
                    'title': title,
                    'source': source,
                    'date': article.get('date', ''),
                    'summary': summary + '...' if summary else ''
                })
        
        return jsonify({'articles': formatted_articles})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Secured routes
@app.route("/dashboard")
@auth_manager.require_auth
def dashboard():
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    stats = get_dashboard_stats(user_id)
    campaigns = campaign_manager.get_user_campaigns(user_id)[:5]
    integrations = get_dashboard_integrations(user_id)
    
    return render_template("dashboard.html", 
                         stats=stats, campaigns=campaigns, 
                         integrations=integrations, user=current_user)

@app.route("/veille")
@auth_manager.require_auth
def veille():
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    query = request.args.get("q")
    
    if not query or query.strip() == "":
        stats = get_dashboard_stats(user_id)
        campaigns = campaign_manager.get_user_campaigns(user_id)[:5]
        integrations = get_dashboard_integrations(user_id)
        
        return render_template("dashboard.html", 
                             articles=[], error="Veuillez saisir un mot-clé.",
                             stats=stats, campaigns=campaigns, 
                             integrations=integrations, user=current_user)

    try:
        articles = fetch_articles_multi_source(query, max_items=25, show_keyword_suggestions=False, user_id=user_id)
    except Exception:
        articles = fetch_articles_rss(query)
    
    session["articles"] = articles

    # Save to Google Sheets if connected
    if session.get('credentials'):
        try:
            sheets = get_sheets_service()
            spreadsheet_id = "TON_SPREADSHEET_ID"
            range_name = "Feuille1!A1"
            values = [[a["date"], a["source"], a["titre"], a["url"]] for a in articles]
            body = {"values": values}
            sheets.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id, range=range_name,
                valueInputOption="RAW", insertDataOption="INSERT_ROWS", body=body
            ).execute()
        except Exception:
            pass

    stats = get_dashboard_stats(user_id)
    campaigns = campaign_manager.get_user_campaigns(user_id)[:5]
    integrations = get_dashboard_integrations(user_id)

    return render_template("dashboard.html", articles=articles,
                         stats=stats, campaigns=campaigns, 
                         integrations=integrations, user=current_user)

# Campaign management routes
@app.route("/campaigns")
@auth_manager.require_auth
def campaigns():
    session.pop('_flashes', None)
    
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    all_campaigns = campaign_manager.get_user_campaigns(user_id)
    
    # Add spreadsheet URLs
    for campaign in all_campaigns:
        if 'google_sheets' in campaign.get('integrations', []) and campaign.get('spreadsheet_id'):
            campaign['spreadsheet_url'] = f"https://docs.google.com/spreadsheets/d/{campaign['spreadsheet_id']}"
        
    return render_template("campaigns.html", campaigns=all_campaigns, user=current_user)

@app.route("/campaigns/create")
def create_campaign():
    prefill_data = {
        'name': request.args.get('name', ''),
        'keywords': request.args.get('keywords', ''),
        'frequency': request.args.get('frequency', '1440')
    }
    return render_template("campaign_form.html", prefill=prefill_data)

@app.route("/campaigns/<campaign_id>/edit")
@auth_manager.require_auth
def edit_campaign(campaign_id):
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    campaign = campaign_manager.get_campaign(campaign_id, user_id)
    
    if not campaign:
        flash('Campagne non trouvée', 'error')
        return redirect(url_for('campaigns'))
    
    return render_template("campaign_form.html", campaign=campaign, user=current_user)

@app.route("/campaigns/create", methods=["POST"])
@app.route("/campaigns/<campaign_id>/edit", methods=["POST"])
@auth_manager.require_auth
def save_campaign(campaign_id=None):
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    
    try:
        # Get user AI preferences
        try:
            user_profile = profile_manager.get_user_profile(user_id)
        except:
            user_profile = {}
        
        data = {
            'name': security_manager.validate_input(request.form.get('name', '').strip(), 100) and request.form.get('name', '').strip(),
            'keywords': security_manager.validate_input(request.form.get('keywords', '').strip(), 500) and request.form.get('keywords', '').strip(),
            'frequency': request.form.get('frequency', '').strip(),
            'integrations': request.form.getlist('integrations'),
            'max_articles': min(int(request.form.get('max_articles', 25)), 100),  # Limit max articles
            'description': security_manager.validate_input(request.form.get('description', '').strip(), 1000) and request.form.get('description', '').strip(),
            'keyword_expansion_enabled': True,
            'ai_model': user_profile.get('ai_model', 'ollama-deepseek-r1:1.5b') if user_profile else 'ollama-deepseek-r1:1.5b'
        }

        # Validate inputs securely
        if not data['name'] or len(data['name']) > 100:
            flash("Erreur: Le nom de la campagne ne peut pas être vide ou dépasser 100 caractères", 'error')
            return redirect(url_for("create_campaign"))
        
        if not data['keywords'] or len(data['keywords']) > 500:
            flash("Erreur: Les mots-clés ne peuvent pas être vides ou dépasser 500 caractères", 'error')
            return redirect(url_for("create_campaign"))
        
        if not data['frequency'] or data['frequency'] not in ['15min', 'hourly', 'daily', 'weekly']:
            flash("Erreur: Veuillez sélectionner une fréquence valide", 'error')
            return redirect(url_for("create_campaign"))
        
        if campaign_id:
            # Update existing campaign
            campaign_manager.update_campaign(campaign_id, user_id, data)
            flash("Campagne mise à jour avec succès !", 'success')
            return redirect(url_for("campaigns"))
        else:
            # Create new campaign
            new_campaign_id = campaign_manager.create_campaign(user_id, data)
            
            # Handle Google Sheets integration
            if 'google_sheets' in data.get('integrations', []):
                try:
                    if integration_manager.is_google_sheets_connected(user_id):
                        spreadsheet_choice = request.form.get('spreadsheet_choice', 'new')
                        spreadsheet_id = request.form.get('spreadsheet_id')
                        
                        if spreadsheet_choice == 'existing' and spreadsheet_id:
                            if new_campaign_id:
                                campaign_manager.update_campaign_spreadsheet(
                                    new_campaign_id, user_id, spreadsheet_id, 
                                    f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
                                )
                        else:
                            sheet_info = sheets_manager.create_campaign_spreadsheet_for_user(user_id, data['name'])
                            if sheet_info and new_campaign_id:
                                campaign_manager.update_campaign_spreadsheet(
                                    new_campaign_id, user_id, sheet_info['id'], sheet_info['url']
                                )
                except Exception:
                    flash("Campagne créée, mais erreur lors de la configuration de Google Sheets.", 'warning')
            
            # Run initial campaign fetch
            if new_campaign_id:
                campaign = campaign_manager.get_campaign(new_campaign_id, user_id)
                if campaign:
                    try:
                        campaign_scheduler.run_campaign(campaign)
                        flash("Campagne créée avec succès ! Articles initiaux récupérés avec mots-clés étendus.", 'success')
                    except Exception:
                        flash("Campagne créée avec succès ! Erreur lors de la récupération initiale des articles.", 'warning')
            
            return redirect(url_for("campaigns"))
            
    except Exception:
        flash("Erreur lors de la sauvegarde de la campagne.", 'error')
        return redirect(url_for("create_campaign") if not campaign_id else url_for("campaigns"))

@app.route("/campaigns/<campaign_id>/pause", methods=["POST"])
@auth_manager.require_auth
def pause_campaign(campaign_id):
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    success = campaign_manager.pause_campaign(campaign_id, user_id)
    return jsonify({'success': success})

@app.route("/campaigns/<campaign_id>/resume", methods=["POST"])
@auth_manager.require_auth
def resume_campaign(campaign_id):
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    success = campaign_manager.resume_campaign(campaign_id, user_id)
    return jsonify({'success': success})

@app.route("/campaigns/<campaign_id>", methods=["DELETE"])
@auth_manager.require_auth
def delete_campaign(campaign_id):
    current_user = auth_manager.get_current_user()
    if not current_user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    user_id = current_user['id']
    
    # Validate campaign_id format (UUID)
    if not security_manager.validate_input(campaign_id, 50):
        return jsonify({'success': False, 'error': 'Invalid campaign ID'}), 400
    
    try:
        data = request.get_json() or {}
        delete_sheet = bool(data.get('delete_sheet', False))
    except:
        return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400
    
    # Verify campaign ownership before deletion
    campaign = campaign_manager.get_campaign(campaign_id, user_id)
    if not campaign:
        return jsonify({'success': False, 'error': 'Campaign not found or access denied'}), 404

    if campaign and delete_sheet and campaign.get('spreadsheet_id'):
        try:
            sheets_manager.delete_spreadsheet(campaign['spreadsheet_id'])
        except Exception:
            pass
    
    success = campaign_manager.delete_campaign(campaign_id, user_id)
    return jsonify({'success': success})

# Integration routes
@app.route("/integrations")
@login_required
def integrations():
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    
    integrations_status = {
        'google_sheets': integration_manager.is_google_sheets_connected(user_id),
        'airtable': bool(integration_manager.get_integration(user_id, 'airtable'))
    }
    
    stats = {
        'total_articles_sent': 0,
        'articles_today': 0,
        'successful_syncs': 0,
        'last_sync': 'Never'
    }
    
    return render_template("integrations.html", integrations=integrations_status, stats=stats)

@app.route("/integrations/airtable/configure", methods=["POST"])
def configure_airtable():
    current_user = auth_manager.get_current_user()
    if not current_user:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        base_id = data.get('base_id')
        table_name = data.get('table_name')
        
        if not all([api_key, base_id, table_name]):
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        from agent.integrations import IntegrationManager
        integration_mgr = IntegrationManager()
        
        success = integration_mgr.configure_airtable(current_user['id'], api_key, base_id, table_name)
        if success:
            return jsonify({'success': True, 'message': 'Airtable configured successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to configure Airtable'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/integrations/<integration>/disconnect", methods=["POST"])
def disconnect_integration(integration):
    current_user = auth_manager.get_current_user()
    if not current_user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    user_id = current_user['id']
    success = integration_manager.disconnect_integration(user_id, integration)
    return jsonify({'success': success})

# Profile routes
@app.route("/profile")
def profile():
    if 'user_id' not in session:
        return redirect('/signin')
    
    user_id = session['user_id']
    user = user_manager.get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect('/signin')
    
    user_data = {
        'name': user['name'],
        'email': user['email'],
        'created_at': user['created_at'][:10] if user.get('created_at') else '2024-01-01',
        'api_key': None
    }
    
    user_stats = campaign_manager.get_user_stats(user_id)
    
    integrations_count = 0
    try:
        if 'credentials' in session:
            integrations_count += 1
    except:
        pass
    
    stats = {
        'total_campaigns': user_stats.get('total_campaigns', 0),
        'total_articles': user_stats.get('total_articles', 0),
        'integrations_count': integrations_count
    }
    
    user_profile = profile_manager.get_user_profile(user_id=user_id)
    
    return render_template("profile.html", user=user_data, stats=stats, profile=user_profile)

@app.route("/profile/ai-settings")
def profile_ai_settings():
    if 'user_id' not in session:
        return redirect('/signin')
    user_id = session['user_id']
    user_profile = profile_manager.get_user_profile(user_id=user_id)
    return render_template("profile_ai_settings.html", profile=user_profile)

@app.route("/profile/ai-settings", methods=["POST"])
def save_ai_settings():
    if 'user_id' not in session:
        return redirect('/signin')
    user_id = session['user_id']
    
    settings = {
        'ai_model': request.form.get('ai_model', 'ollama-deepseek-r1:1.5b'),
        'keyword_expansion_enabled': True,
    }
    
    success = profile_manager.update_user_profile(user_id=user_id, updates=settings)
    
    if request.content_type == 'application/json':
        return jsonify({'success': success})
    else:
        if success:
            flash('Paramètres IA sauvegardés avec succès!', 'success')
        else:
            flash('Erreur lors de la sauvegarde des paramètres IA.', 'error')
        
        return redirect(url_for('profile'))

# API routes
@app.route("/api/preview", methods=["POST"])
def api_preview():
    data = request.get_json()
    keywords = data.get('keywords', '')
    
    try:
        try:
            articles = fetch_articles_multi_source(
                keywords, max_items=25, show_keyword_suggestions=False, user_id=None
            )
        except Exception:
            articles = fetch_articles_rss(keywords, max_items=5)
        return jsonify({'success': True, 'articles': articles})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/campaigns/status")
def api_campaigns_status():
    campaigns = campaign_manager.get_user_campaigns('default')
    return jsonify({'campaigns': campaigns})

@app.route("/api/campaigns/stats")
def get_campaigns_stats():
    try:
        campaigns = campaign_manager.get_user_campaigns('default')
        
        total_campaigns = len(campaigns)
        active_campaigns = len([c for c in campaigns if c.get('status') == 'active'])
        total_articles = sum(c.get('total_articles', 0) for c in campaigns)
        articles_today = sum(c.get('articles_today', 0) for c in campaigns)
        
        campaign_stats = []
        for campaign in campaigns:
            campaign_data = {
                'id': campaign['id'],
                'name': campaign['name'],
                'total_articles': campaign.get('total_articles', 0),
                'articles_today': campaign.get('articles_today', 0),
                'last_check': campaign.get('last_check', ''),
                'status': campaign.get('status', 'inactive'),
                'spreadsheet_url': f"https://docs.google.com/spreadsheets/d/{campaign['spreadsheet_id']}" if campaign.get('spreadsheet_id') else None
            }
            campaign_stats.append(campaign_data)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_campaigns': total_campaigns,
                'active_campaigns': active_campaigns,
                'total_articles': total_articles,
                'articles_today': articles_today
            },
            'campaigns': campaign_stats,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/tasks/<task_id>/status")
def get_task_status(task_id):
    status = async_campaign_manager.get_task_status(task_id)
    if status:
        return jsonify(status)
    else:
        return jsonify({"error": "Task not found"}), 404

@app.route("/api/notifications/<page>")
def get_page_notifications(page):
    return jsonify({"notifications": []})

# Google OAuth routes
@app.route("/auth")
def auth():
    return start_auth()

@app.route("/auth/reauth")
def reauth():
    if "credentials" in session:
        del session["credentials"]
    return start_auth()

@app.route("/oauth2callback")
def oauth2callback():
    try:
        finish_auth()
        
        google_user_info = session.get("google_user_info")
        
        if auth_manager.is_authenticated():
            # User is logged in - store Google credentials
            current_user = auth_manager.get_current_user()
            if not current_user:
                flash("Erreur d'authentification. Veuillez vous reconnecter.", 'error')
                return redirect(url_for("signin"))
            
            user_id = current_user['id']
            
            if "credentials" in session:
                try:
                    success = integration_manager.update_integration(
                        user_id, 'google_sheets', 
                        session["credentials"], is_active=True
                    )
                    if success:
                        return redirect(url_for("integrations"))
                    else:
                        raise Exception("Failed to store credentials")
                except Exception:
                    flash("Erreur lors de la sauvegarde des identifiants.", 'error')
                    return redirect(url_for("integrations"))
        
        else:
            # User is not logged in - try to find/create account
            if google_user_info and google_user_info.get('email'):
                google_email = google_user_info['email']
                google_name = google_user_info.get('name', google_email.split('@')[0])
                
                user = user_manager.get_user_by_email(google_email)
                
                if user:
                    # User exists - log them in automatically
                    session['user_id'] = user['id']
                    session['username'] = user['email']
                    session['client_fingerprint'] = auth_manager.security.get_client_fingerprint()
                    
                    session_token = auth_manager.session_manager.create_session(
                        user['id'], 
                        request.environ.get('REMOTE_ADDR', 'unknown'),
                        request.headers.get('User-Agent', 'Unknown')
                    )
                    session['session_token'] = session_token
                    
                    user_manager.update_last_login(user['id'])
                    
                    if "credentials" in session:
                        integration_manager.update_integration(
                            user['id'], 'google_sheets', 
                            session["credentials"], is_active=True
                        )
                    
                    return redirect(url_for("dashboard"))
                else:
                    # Store Google info for registration
                    session['pending_google_registration'] = {
                        'email': google_email,
                        'name': google_name,
                        'credentials': session.get("credentials")
                    }
                    flash(f"Compte Google détecté ({google_email}). Veuillez créer votre compte pour continuer.", 'info')
                    return redirect(url_for("signup"))
            else:
                flash("Veuillez vous connecter à votre compte pour connecter Google Sheets.", 'info')
                return redirect(url_for("signin"))
        
        flash("Erreur inattendue lors de la connexion.", 'error')
        return redirect(url_for("signin"))
        
    except Exception:
        flash("Erreur lors de la connexion Google Sheets. Veuillez réessayer.", 'error')
        return redirect(url_for("signin"))

# Spreadsheet management
@app.route("/api/spreadsheets/list")
def list_spreadsheets():
    if not auth_manager.is_authenticated():
        return jsonify({'error': 'Authentication required'}), 401
    
    current_user = auth_manager.get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401
    
    user_id = current_user['id']
    error_response = check_google_sheets_access(user_id)
    if error_response:
        return error_response
    
    try:
        creds_data = session.get("credentials")
        if not creds_data:
            return jsonify({'error': 'No credentials in session'}), 401
            
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
        missing_fields = [field for field in required_fields if field not in creds_data]
        
        if missing_fields:
            return jsonify({'error': f'Missing credential fields: {missing_fields}'}), 401
        
        spreadsheets = sheets_manager.list_user_spreadsheets()
        return jsonify({'spreadsheets': spreadsheets})
    except Exception:
        return jsonify({'error': 'Failed to load spreadsheets'}), 500

@app.route("/api/spreadsheets/create", methods=["POST"])
def create_spreadsheet():
    if not sheets_manager.is_google_sheets_connected():
        return jsonify({'error': 'Not connected to Google Sheets'}), 401
    
    data = request.get_json()
    campaign_name = data.get('campaign_name', 'Nouvelle Campagne')
    
    sheet_info = sheets_manager.create_campaign_spreadsheet(campaign_name)
    if sheet_info:
        return jsonify({'success': True, 'spreadsheet': sheet_info})
    else:
        return jsonify({'success': False, 'error': 'Erreur lors de la création'})

@app.route("/api/search-results/save", methods=["POST"])
def save_search_results():
    if not sheets_manager.is_google_sheets_connected():
        return jsonify({'error': 'Not connected to Google Sheets'}), 401
    
    data = request.get_json()
    spreadsheet_choice = data.get('spreadsheet_choice')
    spreadsheet_id = data.get('spreadsheet_id')
    articles = data.get('articles', [])
    campaign_name = data.get('campaign_name', 'Recherche')
    keywords = data.get('keywords', '')
    
    if spreadsheet_choice == 'new':
        sheet_info = sheets_manager.create_campaign_spreadsheet(campaign_name)
        if not sheet_info:
            return jsonify({'success': False, 'error': 'Erreur lors de la création'})
        spreadsheet_id = sheet_info['id']
    
    success = sheets_manager.save_articles_to_spreadsheet(
        spreadsheet_id, articles, campaign_name, keywords
    )
    
    if success:
        return jsonify({
            'success': True, 
            'spreadsheet_id': spreadsheet_id,
            'spreadsheet_url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        })
    else:
        return jsonify({'success': False, 'error': 'Erreur lors de la sauvegarde'})

@app.route("/api/campaigns/<campaign_id>/save-results", methods=["POST"])
def save_campaign_results(campaign_id):
    if not sheets_manager.is_google_sheets_connected():
        return jsonify({'error': 'Not connected to Google Sheets'}), 401
    
    data = request.get_json()
    spreadsheet_choice = data.get('spreadsheet_choice')
    spreadsheet_id = data.get('spreadsheet_id')
    articles = data.get('articles', [])
    
    campaign = campaign_manager.get_campaign(campaign_id, 'default')
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), 404
    
    if spreadsheet_choice == 'new':
        sheet_info = sheets_manager.create_campaign_spreadsheet(campaign['name'])
        if not sheet_info:
            return jsonify({'success': False, 'error': 'Erreur lors de la création'})
        spreadsheet_id = sheet_info['id']
    
    success = sheets_manager.save_articles_to_spreadsheet(
        spreadsheet_id, articles, campaign['name'], campaign['keywords']
    )
    
    if success:
        return jsonify({
            'success': True, 
            'spreadsheet_id': spreadsheet_id,
            'spreadsheet_url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        })
    else:
        return jsonify({'success': False, 'error': 'Erreur lors de la sauvegarde'})

# Files management
@app.route("/files")
@login_required
def file_management():
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    
    if not integration_manager.is_google_sheets_connected(user_id):
        return render_template("files.html", 
                             spreadsheets=[], 
                             error="Veuillez vous connecter à Google Sheets pour voir vos fichiers.")
    
    try:
        all_spreadsheets = []
        
        try:
            if "credentials" in session:
                all_spreadsheets = sheets_manager.list_user_spreadsheets()
        except Exception:
            pass
        
        campaigns = campaign_manager.get_user_campaigns(user_id)
        campaign_spreadsheets = {c.get('spreadsheet_id'): c['name'] for c in campaigns if c.get('spreadsheet_id')}
        
        for sheet in all_spreadsheets:
            sheet['campaign_name'] = campaign_spreadsheets.get(sheet['id'])
        
        return render_template("files.html", 
                             spreadsheets=all_spreadsheets,
                             campaign_count=len(campaigns))
                             
    except Exception:
        return render_template("files.html", 
                             spreadsheets=[], 
                             error="Erreur lors du chargement des fichiers.")

@app.route("/api/files/<file_id>/delete", methods=["DELETE"])
def delete_file(file_id):
    if not sheets_manager.is_google_sheets_connected():
        return jsonify({'error': 'Not connected to Google Sheets'}), 401
    
    try:
        success = sheets_manager.delete_spreadsheet(file_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == "__main__":
    port = 5000
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith('--port='):
                port = int(arg.split('=')[1])
    
    # Security: Disable debug mode in production
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, port=port, host='0.0.0.0')
