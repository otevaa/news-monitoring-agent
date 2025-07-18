from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash
from agent.fetch_multi_source import fetch_articles_multi_source, fetch_articles_rss
from agent.google_oauth import start_auth, finish_auth, get_sheets_service
from agent.async_campaign_manager import AsyncCampaignManager
from agent.google_sheets_manager import GoogleSheetsManager
from agent.campaign_manager import CampaignManager
from agent.integrations import IntegrationManager
from agent.scheduler import campaign_scheduler
from agent.user_profile_manager import UserProfileManager
from agent.multi_ai_enhancer import create_ai_enhancer
import json
import atexit
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "ta-cle-ultra-secrete"

# Initialize managers with error handling
try:
    campaign_manager = CampaignManager()
    print("✅ Campaign Manager initialized")
except Exception as e:
    print(f"❌ Campaign Manager initialization failed: {e}")
    # Create a fallback class with safe methods
    class FallbackCampaignManager:
        def get_active_campaigns(self): return []
        def get_total_articles_count(self): return 0
        def get_articles_today_count(self): return 0
        def get_recent_campaigns(self, limit=5): return []
        def get_campaigns(self): return []
        def get_all_campaigns(self): return []
        def get_campaign(self, campaign_id=None): 
            if campaign_id is None:
                return None
            return None
        def get_campaign_by_id(self, id): return None
        def create_campaign(self, data): return None
        def update_campaign(self, id, data): return False
        def delete_campaign(self, id): return False
        def pause_campaign(self, id): return False
        def resume_campaign(self, id): return False
        def get_total_campaigns_count(self): return 0
        def _save_campaigns(self): pass
    campaign_manager = FallbackCampaignManager()

try:
    integration_manager = IntegrationManager()
    print("✅ Integration Manager initialized")
except Exception as e:
    print(f"❌ Integration Manager initialization failed: {e}")
    # Create a fallback class with safe methods
    class FallbackIntegrationManager:
        def is_google_sheets_connected(self): return False
        def update_google_sheets_status(self, status): pass
        def get_active_integrations_count(self): return 0
        def is_airtable_configured(self): return False
        def get_google_sheets_status(self): return None
        def get_airtable_status(self): return None
        def disconnect_integration(self, name): return False
        def configure_airtable(self, api_key, base_id, table_name): return False
        def get_usage_stats(self): return {'total_articles_sent': 0, 'articles_today': 0, 'successful_syncs': 0, 'last_sync': 'Never'}
    integration_manager = FallbackIntegrationManager()

try:
    sheets_manager = GoogleSheetsManager()
    print("✅ Google Sheets Manager initialized")
except Exception as e:
    print(f"❌ Google Sheets Manager initialization failed: {e}")
    # Create a fallback class with safe methods
    class FallbackSheetsManager:
        def is_google_sheets_connected(self): return False
        def get_sheets_service(self): return None
        def get_drive_service(self): return None
        def list_user_spreadsheets(self): return []
        def create_campaign_spreadsheet(self, name): return None
        def save_articles_to_spreadsheet(self, id, articles, campaign_name="", keywords=""): return False
        def get_campaign_spreadsheets(self, campaign_name=None): return []
        def delete_spreadsheet(self, id): return False
        def get_spreadsheet_info(self, id): return None
    sheets_manager = FallbackSheetsManager()

try:
    async_campaign_manager = AsyncCampaignManager()
    print("✅ Async Campaign Manager initialized")
except Exception as e:
    print(f"❌ Async Campaign Manager initialization failed: {e}")
    # Create a fallback class with safe methods  
    class FallbackAsyncCampaignManager:
        def __init__(self): self.tasks = {}
        def get_task_status(self, task_id): return {'status': 'error', 'error': 'Manager not initialized'}
    async_campaign_manager = FallbackAsyncCampaignManager()

try:
    user_profile_manager = UserProfileManager()
    print("✅ User Profile Manager initialized")
except Exception as e:
    print(f"❌ User Profile Manager initialization failed: {e}")
    # Create a fallback class with safe methods
    class FallbackUserProfileManager:
        def get_user_profile(self, user_id='default'): return {}
        def update_user_profile(self, user_id='default', data=None, updates=None): return False
        def get_ai_model(self): return 'openai-gpt3.5'
        def set_ai_model(self, model): return False
        def get_relevance_threshold(self): return 70
        def set_relevance_threshold(self, threshold): return False
        def generate_api_key(self): return 'fallback-key'
        def get_api_key(self): return 'fallback-key'
        def regenerate_api_key(self): return 'fallback-key'
    user_profile_manager = FallbackUserProfileManager()

# Start the campaign scheduler
campaign_scheduler.start()

# Ensure scheduler is stopped when app shuts down
atexit.register(lambda: campaign_scheduler.stop())

# Helper functions to reduce redundancy
def get_dashboard_stats():
    """Get common dashboard statistics"""
    return {
        'active_campaigns': len(campaign_manager.get_active_campaigns()),
        'total_articles': campaign_manager.get_total_articles_count(),
        'articles_today': campaign_manager.get_articles_today_count(),
        'integrations_count': integration_manager.get_active_integrations_count()
    }

def get_dashboard_integrations():
    """Get integration status for dashboard"""
    return {
        'google_sheets': sheets_manager.is_google_sheets_connected(),
        'airtable': integration_manager.is_airtable_configured()
    }

def check_google_sheets_access():
    """Check if Google Sheets is connected and return appropriate response"""
    if not sheets_manager.is_google_sheets_connected():
        return jsonify({'error': 'Not connected to Google Sheets'}), 401
    return None

@app.route("/")
def home():
    # Clear any lingering flash messages to prevent them from appearing on dashboard
    session.pop('_flashes', None)
    
    # Update Google Sheets integration status
    google_sheets_connected = sheets_manager.is_google_sheets_connected()
    integration_manager.update_google_sheets_status(google_sheets_connected)
    
    # Get dashboard data
    stats = get_dashboard_stats()
    campaigns = campaign_manager.get_recent_campaigns(limit=5)
    integrations = get_dashboard_integrations()
    
    return render_template("dashboard.html", 
                         stats=stats, 
                         campaigns=campaigns, 
                         integrations=integrations)

@app.route("/veille")
def veille():
    query = request.args.get("q")
    if not query or query.strip() == "":
        # Return to dashboard with error, including all required template variables
        stats = get_dashboard_stats()
        campaigns = campaign_manager.get_recent_campaigns(limit=5)
        integrations = get_dashboard_integrations()
        
        return render_template("dashboard.html", 
                             articles=[], 
                             error="Veuillez saisir un mot-clé.",
                             stats=stats,
                             campaigns=campaigns,
                             integrations=integrations)

    try:
        articles = fetch_articles_multi_source(query, max_items=25, use_ai_filtering=False, show_keyword_suggestions=False)
    except Exception as e:
        print(f"Error with multi-source fetch, falling back to RSS: {e}")
        articles = fetch_articles_rss(query)
    session["articles"] = articles

    if "credentials" not in session:
        return redirect(url_for("auth"))

    # Save to configured integrations
    if session.get('credentials'):
        sheets = get_sheets_service()
        spreadsheet_id = "TON_SPREADSHEET_ID"  # ou créé dynamiquement
        range_name = "Feuille1!A1"

        values = [
            [a["date"], a["source"], a["titre"], a["url"], a["resume"]]
            for a in articles
        ]
        body = {"values": values}
        try:
            sheets.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
        except Exception as e:
            print(f"Error saving to Google Sheets: {e}")

    # Include all required template variables for successful search
    stats = get_dashboard_stats()
    campaigns = campaign_manager.get_recent_campaigns(limit=5)
    integrations = get_dashboard_integrations()

    return render_template("dashboard.html", 
                         articles=articles,
                         stats=stats,
                         campaigns=campaigns,
                         integrations=integrations)

# Campaign Management Routes
@app.route("/campaigns")
def campaigns():
    # Clear any lingering flash messages to prevent them from appearing on campaigns page
    session.pop('_flashes', None)
    
    all_campaigns = campaign_manager.get_all_campaigns()
    
    # Add spreadsheet URLs for campaigns that have Google Sheets integration
    for campaign in all_campaigns:
        if 'google_sheets' in campaign.get('integrations', []) and campaign.get('spreadsheet_id'):
            campaign['spreadsheet_url'] = f"https://docs.google.com/spreadsheets/d/{campaign['spreadsheet_id']}"
        
    return render_template("campaigns.html", campaigns=all_campaigns)

@app.route("/campaigns/create")
def create_campaign():
    # Get pre-filled parameters from voice commands
    prefill_data = {
        'name': request.args.get('name', ''),
        'keywords': request.args.get('keywords', ''),
        'frequency': request.args.get('frequency', '1440')
    }
    return render_template("campaign_form.html", prefill=prefill_data)

@app.route("/campaigns/<campaign_id>/edit")
def edit_campaign(campaign_id):
    campaign = campaign_manager.get_campaign(campaign_id)
    return render_template("campaign_form.html", campaign=campaign)

@app.route("/campaigns/create", methods=["POST"])
@app.route("/campaigns/<campaign_id>/edit", methods=["POST"])
def save_campaign(campaign_id=None):
    """Save or update a campaign"""
    try:
        # Get user AI preferences
        user_profile = user_profile_manager.get_user_profile(user_id='default')
        
        data = {
            'name': request.form.get('name', '').strip(),
            'keywords': request.form.get('keywords', '').strip(),
            'frequency': request.form.get('frequency', '').strip(),
            'integrations': request.form.getlist('integrations'),
            'max_articles': int(request.form.get('max_articles', 25)),
            'description': request.form.get('description', '').strip(),
            # AI Enhancement Options - now using defaults from user profile
            'ai_filtering_enabled': request.form.get('ai_filtering_enabled', 'false').lower() == 'true',
            'relevance_threshold': user_profile.get('relevance_threshold', 70),
            'keyword_expansion_enabled': request.form.get('keyword_expansion_enabled', 'false').lower() == 'true',
            'priority_alerts_enabled': request.form.get('priority_alerts_enabled', 'false').lower() == 'true',
            'ai_model': user_profile.get('ai_model', 'openai-gpt3.5')
        }
        
        # Add debug logging
        print(f"DEBUG: Form data received:")
        print(f"  Name: '{data['name']}'")
        print(f"  Keywords: '{data['keywords']}'")
        print(f"  Frequency: '{data['frequency']}'")
        print(f"  Max articles: {data['max_articles']}")
        print(f"  AI filtering: {data['ai_filtering_enabled']}")
        
        # Validate basic inputs
        if not data['name']:
            flash("Erreur: Le nom de la campagne ne peut pas être vide", 'error')
            return redirect(url_for("create_campaign"))
        
        if not data['keywords']:
            flash("Erreur: Les mots-clés ne peuvent pas être vides", 'error')
            return redirect(url_for("create_campaign"))
        
        if not data['frequency']:
            flash("Erreur: Veuillez sélectionner une fréquence", 'error')
            return redirect(url_for("create_campaign"))
        
        if campaign_id:
            # Update existing campaign
            campaign_manager.update_campaign(campaign_id, data)
            flash("Campagne mise à jour avec succès !", 'success')
            return redirect(url_for("campaigns"))
        else:
            # Create new campaign
            new_campaign_id = campaign_manager.create_campaign(data)
            
            # Handle Google Sheets integration
            if "credentials" in session and 'google_sheets' in data.get('integrations', []):
                try:
                    if sheets_manager.is_google_sheets_connected():
                        spreadsheet_choice = request.form.get('spreadsheet_choice', 'new')
                        spreadsheet_id = request.form.get('spreadsheet_id')
                        
                        if spreadsheet_choice == 'existing' and spreadsheet_id:
                            # Link existing spreadsheet to campaign
                            if new_campaign_id:
                                campaign = campaign_manager.get_campaign(new_campaign_id)
                                if campaign:
                                    campaign['spreadsheet_id'] = spreadsheet_id
                                    campaign['spreadsheet_url'] = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
                                    campaign_manager._save_campaigns()
                        else:
                            # Create new spreadsheet
                            sheet_info = sheets_manager.create_campaign_spreadsheet(data['name'])
                            if sheet_info and new_campaign_id:
                                campaign = campaign_manager.get_campaign(new_campaign_id)
                                if campaign:
                                    campaign['spreadsheet_id'] = sheet_info['id']
                                    campaign['spreadsheet_url'] = sheet_info['url']
                                    campaign_manager._save_campaigns()
                except Exception as e:
                    print(f"Error setting up Google Sheets for campaign: {e}")
                    flash("Campagne créée, mais erreur lors de la configuration de Google Sheets.", 'warning')
            
            # Run initial campaign fetch
            if new_campaign_id:
                campaign = campaign_manager.get_campaign(new_campaign_id)
                if campaign:
                    from agent.scheduler import campaign_scheduler
                    try:
                        campaign_scheduler.run_campaign(campaign)
                        flash("Campagne créée avec succès ! Articles initiaux récupérés.", 'success')
                    except Exception as e:
                        print(f"Error running initial campaign fetch: {e}")
                        flash("Campagne créée avec succès ! Erreur lors de la récupération initiale des articles.", 'warning')
            
            # Redirect to campaigns list after successful creation
            return redirect(url_for("campaigns"))
            
    except Exception as e:
        print(f"Error saving campaign: {e}")
        flash("Erreur lors de la sauvegarde de la campagne.", 'error')
        return redirect(url_for("create_campaign") if not campaign_id else url_for("campaigns"))

@app.route("/campaigns/<campaign_id>/pause", methods=["POST"])
def pause_campaign(campaign_id):
    success = campaign_manager.pause_campaign(campaign_id)
    return jsonify({'success': success})

@app.route("/campaigns/<campaign_id>/resume", methods=["POST"])
def resume_campaign(campaign_id):
    success = campaign_manager.resume_campaign(campaign_id)
    return jsonify({'success': success})

@app.route("/campaigns/<campaign_id>", methods=["DELETE"])
def delete_campaign(campaign_id):
    data = request.get_json() or {}
    delete_sheet = data.get('delete_sheet', False)
    
    # Get campaign info before deletion
    campaign = campaign_manager.get_campaign(campaign_id)
    
    if campaign and delete_sheet and campaign.get('spreadsheet_id'):
        # Delete the associated Google Sheet
        try:
            from agent.google_sheets_manager import GoogleSheetsManager
            sheets_manager = GoogleSheetsManager()
            if sheets_manager.is_google_sheets_connected():
                # Note: Google Sheets API doesn't allow deletion of sheets via API
                # We'll just remove the reference and log the action
                print(f"Sheet reference removed for campaign '{campaign['name']}' (ID: {campaign.get('spreadsheet_id')})")
            else:
                print("Google Sheets not connected - cannot delete sheet")
        except Exception as e:
            print(f"Error handling sheet deletion: {e}")
    
    success = campaign_manager.delete_campaign(campaign_id)
    return jsonify({'success': success})

# Integration Routes
@app.route("/integrations")
def integrations():
    integrations_status = {
        'google_sheets': integration_manager.get_google_sheets_status(),
        'airtable': integration_manager.get_airtable_status()
    }
    stats = integration_manager.get_usage_stats()
    return render_template("integrations.html", integrations=integrations_status, stats=stats)

@app.route("/integrations/airtable/configure", methods=["POST"])
def configure_airtable():
    api_key = request.form.get('api_key')
    base_id = request.form.get('base_id')
    table_name = request.form.get('table_name')
    
    if not api_key or not base_id or not table_name:
        return jsonify({'success': False, 'error': 'Tous les champs sont requis'})
    
    success = integration_manager.configure_airtable(api_key, base_id, table_name)
    return jsonify({'success': success})

@app.route("/integrations/<integration>/disconnect", methods=["POST"])
def disconnect_integration(integration):
    success = integration_manager.disconnect_integration(integration)
    return jsonify({'success': success})

# Profile Routes
@app.route("/profile")
def profile():
    user_data = {
        'name': 'Utilisateur Demo',
        'email': 'user@example.com',
        'created_at': '2024-01-01',
        'api_key': None
    }
    stats = {
        'total_campaigns': campaign_manager.get_total_campaigns_count(),
        'total_articles': campaign_manager.get_total_articles_count(),
        'integrations_count': integration_manager.get_active_integrations_count()
    }
    return render_template("profile.html", user=user_data, stats=stats)

@app.route("/profile/ai-settings")
def profile_ai_settings():
    user_profile = user_profile_manager.get_user_profile(user_id='default')
    return render_template("profile_ai_settings.html", profile=user_profile)

@app.route("/profile/ai-settings", methods=["POST"])
def save_ai_settings():
    settings = {
        'ai_model': request.form.get('ai_model', 'openai-gpt3.5'),
        'relevance_threshold': int(request.form.get('relevance_threshold', 70)),
        'ai_filtering_enabled': 'ai_filtering_enabled' in request.form,
        'keyword_expansion_enabled': 'keyword_expansion_enabled' in request.form,
        'priority_alerts_enabled': 'priority_alerts_enabled' in request.form
    }
    
    success = user_profile_manager.update_user_profile(user_id='default', updates=settings)
    
    if request.content_type == 'application/json':
        return jsonify({'success': success})
    else:
        if success:
            flash('Paramètres IA sauvegardés avec succès!', 'success')
        else:
            flash('Erreur lors de la sauvegarde des paramètres IA.', 'error')
        
        # Stay on the same page instead of redirecting
        return render_template('profile_ai_settings.html', 
                             user_profile=user_profile_manager.get_user_profile(user_id='default'),
                             settings_saved=success)

@app.route("/api/test-ai-model", methods=["POST"])
def test_ai_model():
    try:
        data = request.get_json()
        model = data.get('model', 'openai-gpt3.5')
        
        # Create AI enhancer with specified model
        ai_enhancer = create_ai_enhancer(model=model)
        
        # Test with a sample article
        test_article = {
            'titre': 'Test d\'intelligence artificielle pour l\'analyse d\'articles',
            'resume': 'Article test pour vérifier le fonctionnement du modèle IA'
        }
        
        import time
        start_time = time.time()
        
        # Test scoring
        score = ai_enhancer.score_article_relevance(test_article, 'intelligence artificielle, test')
        
        end_time = time.time()
        
        return jsonify({
            'success': True,
            'model': model,
            'score': score,
            'time': round((end_time - start_time) * 1000, 2),
            'provider': ai_enhancer.provider
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# API Routes
@app.route("/api/preview", methods=["POST"])
def api_preview():
    data = request.get_json()
    keywords = data.get('keywords', '')
    
    try:
        # AI filtering disabled by default for preview
        use_ai_filtering = data.get('ai_filtering_enabled', False)
        relevance_threshold = data.get('relevance_threshold', 70)
        
        try:
            articles = fetch_articles_multi_source(
                keywords, 
                max_items=25, 
                use_ai_filtering=use_ai_filtering,
                relevance_threshold=relevance_threshold,
                show_keyword_suggestions=False  # Don't show suggestions in preview
            )
        except Exception as e:
            print(f"Error with multi-source fetch, falling back to RSS: {e}")
            articles = fetch_articles_rss(keywords, max_items=5)
        return jsonify({'success': True, 'articles': articles})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/campaigns/status")
def api_campaigns_status():
    campaigns = campaign_manager.get_all_campaigns()
    return jsonify({'campaigns': campaigns})

@app.route("/auth")
def auth():
    return start_auth()

@app.route("/auth/reauth")
def reauth():
    """Force re-authentication to get fresh credentials"""
    # Clear existing credentials
    if "credentials" in session:
        del session["credentials"]
    integration_manager.update_google_sheets_status(False)
    return start_auth()

@app.route("/auth/logout")
def logout():
    """Logout and clear all session data"""
    session.clear()
    integration_manager.update_google_sheets_status(False)
    flash("Déconnexion réussie", 'success')
    return redirect(url_for("home"))

@app.route("/oauth2callback")
def oauth2callback():
    try:
        finish_auth()
        
        # Save credentials to file for background scheduler access
        if "credentials" in session:
            try:
                with open("user_credentials.json", "w") as f:
                    json.dump(session["credentials"], f, indent=2)
                print("Credentials saved to file for scheduler access")
            except Exception as e:
                print(f"Error saving credentials to file: {e}")
        
        # Update integration status
        integration_manager.update_google_sheets_status(True)
        flash("Connexion Google Sheets réussie !", 'success')
        return redirect(url_for("home"))
    except Exception as e:
        print(f"OAuth callback error: {e}")
        flash("Erreur lors de la connexion Google Sheets. Veuillez réessayer.", 'error')
        return redirect(url_for("home"))

@app.route("/debug/session")
def debug_session():
    """Debug session contents"""
    if "credentials" in session:
        creds = session["credentials"]
        return jsonify({
            'authenticated': True,
            'credential_keys': list(creds.keys()),
            'has_token': 'token' in creds,
            'has_refresh_token': 'refresh_token' in creds,
            'has_client_id': 'client_id' in creds,
            'has_client_secret': 'client_secret' in creds,
            'token_preview': creds.get('token', '')[:20] + '...' if creds.get('token') else None
        })
    else:
        return jsonify({'authenticated': False})

# Spreadsheet management routes
@app.route("/api/spreadsheets/list")
def list_spreadsheets():
    """List user's spreadsheets"""
    if "credentials" not in session:
        return jsonify({'error': 'Not connected to Google Sheets'}), 401
    
    error_response = check_google_sheets_access()
    if error_response:
        return error_response
    
    try:
        # Debug: Check what credentials we have
        creds_data = session["credentials"]
        print(f"Credentials keys: {list(creds_data.keys())}")
        
        # Check for required fields
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
        missing_fields = [field for field in required_fields if field not in creds_data]
        
        if missing_fields:
            print(f"Missing credential fields: {missing_fields}")
            return jsonify({'error': f'Missing credential fields: {missing_fields}'}), 401
        
        spreadsheets = sheets_manager.list_user_spreadsheets()
        return jsonify({'spreadsheets': spreadsheets})
    except Exception as e:
        print(f"Error listing spreadsheets: {e}")
        return jsonify({'error': 'Failed to load spreadsheets'}), 500

@app.route("/api/tasks/<task_id>/status")
def get_task_status(task_id):
    """Get the status of an async campaign creation task"""
    status = async_campaign_manager.get_task_status(task_id)
    if status:
        return jsonify(status)
    else:
        return jsonify({"error": "Task not found"}), 404

@app.route("/api/notifications/<page>")
def get_page_notifications(page):
    """Get notifications for a specific page"""
    # This would normally check for page-specific notifications
    # For now, return empty as we're using Flask flash messages
    return jsonify({"notifications": []})

@app.route("/api/spreadsheets/create", methods=["POST"])
def create_spreadsheet():
    """Create new spreadsheet for campaign"""
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
    """Save search results to spreadsheet"""
    if not sheets_manager.is_google_sheets_connected():
        return jsonify({'error': 'Not connected to Google Sheets'}), 401
    
    data = request.get_json()
    spreadsheet_choice = data.get('spreadsheet_choice')  # 'new' or 'existing'
    spreadsheet_id = data.get('spreadsheet_id')  # for existing
    articles = data.get('articles', [])
    campaign_name = data.get('campaign_name', 'Recherche')
    keywords = data.get('keywords', '')
    
    if spreadsheet_choice == 'new':
        # Create new spreadsheet
        sheet_info = sheets_manager.create_campaign_spreadsheet(campaign_name)
        if not sheet_info:
            return jsonify({'success': False, 'error': 'Erreur lors de la création'})
        spreadsheet_id = sheet_info['id']
    
    # Save articles to spreadsheet
    success = sheets_manager.save_articles_to_spreadsheet(
        spreadsheet_id, 
        articles, 
        campaign_name, 
        keywords
    )
    
    if success:
        return jsonify({
            'success': True, 
            'spreadsheet_id': spreadsheet_id,
            'spreadsheet_url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        })
    else:
        return jsonify({'success': False, 'error': 'Erreur lors de la sauvegarde'})

@app.route("/api/campaigns/stats")
def get_campaigns_stats():
    """Get real-time campaign statistics"""
    try:
        campaigns = campaign_manager.get_all_campaigns()
        
        # Calculate overall stats
        total_campaigns = len(campaigns)
        active_campaigns = len([c for c in campaigns if c.get('status') == 'active'])
        total_articles = sum(c.get('total_articles', 0) for c in campaigns)
        articles_today = sum(c.get('articles_today', 0) for c in campaigns)
        
        # Get individual campaign stats
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
        print(f"Error getting campaign stats: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/campaigns/<campaign_id>/save-results", methods=["POST"])
def save_campaign_results(campaign_id):
    """Save campaign results to spreadsheet"""
    if not sheets_manager.is_google_sheets_connected():
        return jsonify({'error': 'Not connected to Google Sheets'}), 401
    
    data = request.get_json()
    spreadsheet_choice = data.get('spreadsheet_choice')  # 'new' or 'existing'
    spreadsheet_id = data.get('spreadsheet_id')  # for existing
    articles = data.get('articles', [])
    
    campaign = campaign_manager.get_campaign(campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), 404
    
    if spreadsheet_choice == 'new':
        # Create new spreadsheet
        sheet_info = sheets_manager.create_campaign_spreadsheet(campaign['name'])
        if not sheet_info:
            return jsonify({'success': False, 'error': 'Erreur lors de la création'})
        spreadsheet_id = sheet_info['id']
    
    # Save articles to spreadsheet
    success = sheets_manager.save_articles_to_spreadsheet(
        spreadsheet_id, 
        articles, 
        campaign['name'], 
        campaign['keywords']
    )
    
    if success:
        return jsonify({
            'success': True, 
            'spreadsheet_id': spreadsheet_id,
            'spreadsheet_url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        })
    else:
        return jsonify({'success': False, 'error': 'Erreur lors de la sauvegarde'})

@app.route("/files")
def file_management():
    """File and folder management page"""
    if not sheets_manager.is_google_sheets_connected():
        return render_template("files.html", 
                             spreadsheets=[], 
                             error="Veuillez vous connecter à Google Sheets pour voir vos fichiers.")
    
    try:
        # Get all spreadsheets
        all_spreadsheets = sheets_manager.list_user_spreadsheets()
        
        # Get campaigns with their associated spreadsheets
        campaigns = campaign_manager.get_all_campaigns()
        campaign_spreadsheets = {c.get('spreadsheet_id'): c['name'] for c in campaigns if c.get('spreadsheet_id')}
        
        # Mark which spreadsheets are associated with campaigns
        for sheet in all_spreadsheets:
            sheet['is_campaign_sheet'] = sheet['id'] in campaign_spreadsheets
            sheet['campaign_name'] = campaign_spreadsheets.get(sheet['id'], '')
        
        return render_template("files.html", 
                             spreadsheets=all_spreadsheets,
                             campaign_count=len(campaigns))
                             
    except Exception as e:
        print(f"Error loading files: {e}")
        return render_template("files.html", 
                             spreadsheets=[], 
                             error="Erreur lors du chargement des fichiers.")

@app.route("/api/files/<file_id>/delete", methods=["DELETE"])
def delete_file(file_id):
    """Delete a spreadsheet file and optionally associated campaign"""
    if not sheets_manager.is_google_sheets_connected():
        return jsonify({'error': 'Not connected to Google Sheets'}), 401
    
    try:
        # Check if user wants to delete the associated campaign
        delete_campaign = request.args.get('delete_campaign', 'false').lower() == 'true'
        
        # Find associated campaign if it exists
        campaign_to_delete = None
        if delete_campaign:
            campaigns = campaign_manager.get_all_campaigns()
            for campaign in campaigns:
                if campaign.get('spreadsheet_id') == file_id:
                    campaign_to_delete = campaign
                    break
        
        # Delete the spreadsheet
        success = sheets_manager.delete_spreadsheet(file_id)
        
        if success:
            # Delete associated campaign if requested
            if campaign_to_delete and delete_campaign:
                campaign_manager.delete_campaign(campaign_to_delete['id'])
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Impossible de supprimer le fichier'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__=="__main__":
    import sys
    port = 5000  # default port
    
    # Check for port argument
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith('--port='):
                try:
                    port = int(arg.split('=')[1])
                except:
                    port = 5000
    
    app.run(debug=True, port=port)