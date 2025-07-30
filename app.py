from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash
from functools import wraps
from agent.fetch_multi_source import fetch_articles_multi_source, fetch_articles_rss
from agent.google_oauth import start_auth, finish_auth, get_sheets_service, get_user_info
from agent.async_campaign_manager import AsyncCampaignManager
from agent.google_sheets_manager import GoogleSheetsManager
from agent.scheduler import campaign_scheduler
from database.models import DatabaseManager, UserManager
from database.managers import DatabaseCampaignManager, DatabaseUserProfileManager, DatabaseIntegrationManager
from auth.auth_manager import EnhancedAuthManager
from auth.security_manager import SecurityManager
import json
import atexit
import os
import sys
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())

# Initialize secure database system
try:
    db_manager = DatabaseManager()
    auth_manager = EnhancedAuthManager()
    user_manager = UserManager(db_manager)
    campaign_manager = DatabaseCampaignManager(db_manager)
    profile_manager = DatabaseUserProfileManager(db_manager) 
    integration_manager = DatabaseIntegrationManager(db_manager)
    security_manager = SecurityManager()
    
    # Debug: Check database file and persistence
    import os
    db_path = db_manager.db_path
    db_abs_path = os.path.abspath(db_path)
    db_dir = os.path.dirname(db_abs_path)
    
    print(f"✅ Database file location: {db_abs_path}")
    print(f"✅ Database directory: {db_dir}")
    print(f"✅ Database exists: {os.path.exists(db_abs_path)}")
    print(f"✅ Database directory exists: {os.path.exists(db_dir)}")
    print(f"✅ Database directory writable: {os.access(db_dir, os.W_OK)}")
    
    if os.path.exists(db_abs_path):
        print(f"✅ Database size: {os.path.getsize(db_abs_path)} bytes")
        
        # Test database connection and show stats
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Count users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"✅ Current users in database: {user_count}")
        
        # Show recent users (for debugging)
        if user_count > 0:
            cursor.execute("SELECT email, created_at FROM users ORDER BY created_at DESC LIMIT 3")
            recent_users = cursor.fetchall()
            print(f"✅ Recent users: {[dict(user) for user in recent_users]}")
        
        conn.close()
    else:
        print("⚠️  Database file does not exist - will be created")
    
    print("✅ Secure database system initialized")
except Exception as e:
    print(f"❌ Database system initialization failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    # Use database-based integration manager
    db_manager = DatabaseManager()
    integration_manager = DatabaseIntegrationManager(db_manager)
    print("✅ Database Integration Manager initialized")
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
        def create_campaign_spreadsheet_for_user(self, user_id, name): return None
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
    user_profile_manager = DatabaseUserProfileManager(db_manager)
    print("✅ User Profile Manager initialized")
except Exception as e:
    print(f"❌ User Profile Manager initialization failed: {e}")
    # Create a fallback class with safe methods
    class FallbackUserProfileManager:
        def get_user_profile(self, user_id='default'): return {}
        def update_user_profile(self, user_id='default', data=None, updates=None): return False
        def get_ai_model(self): return 'ollama-deepseek-r1:1.5b'
        def set_ai_model(self, model): return False
        def get_priority_alerts(self): return False
        def set_priority_alerts(self, enabled): return False
        def generate_api_key(self): return 'fallback-key'
        def get_api_key(self): return 'fallback-key'
        def regenerate_api_key(self): return 'fallback-key'
    user_profile_manager = FallbackUserProfileManager()

# Start the campaign scheduler
campaign_scheduler.start()

# Ensure scheduler is stopped when app shuts down
atexit.register(lambda: campaign_scheduler.stop())

# Helper functions to reduce redundancy
def get_dashboard_stats(user_id: str):
    """Get dashboard statistics for a specific user"""
    try:
        stats = campaign_manager.get_user_stats(user_id)
        return {
            'active_campaigns': stats.get('active_campaigns', 0),
            'total_articles': stats.get('total_articles', 0),
            'articles_today': stats.get('articles_today', 0),
            'total_campaigns': stats.get('total_campaigns', 0)
        }
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return {
            'active_campaigns': 0,
            'total_articles': 0,
            'articles_today': 0,
            'total_campaigns': 0
        }

def get_dashboard_integrations(user_id: str):
    """Get integration status for dashboard"""
    try:
        db_integration_manager = DatabaseIntegrationManager(db_manager)
        return {
            'google_sheets': db_integration_manager.is_google_sheets_connected(user_id),
            'airtable': False  # Will implement later
        }
    except Exception as e:
        print(f"Error getting integrations: {e}")
        return {
            'google_sheets': False,
            'airtable': False
        }

def check_google_sheets_access(user_id: str):
    """Check if Google Sheets is connected and return appropriate response"""
    db_integration_manager = DatabaseIntegrationManager(db_manager)
    if not db_integration_manager.is_google_sheets_connected(user_id):
        return jsonify({'error': 'Not connected to Google Sheets'}), 401
    return None

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth_page'))
        return f(*args, **kwargs)
    return decorated_function

# Health check endpoint
@app.route("/health")
def health():
    """Health check endpoint for monitoring"""
    return jsonify({"status": "healthy", "service": "news-monitoring-agent", "timestamp": datetime.now().isoformat()})

# Debug endpoint
@app.route("/debug")
def debug():
    """Debug endpoint to check Flask status"""
    return jsonify({
        "status": "Flask is running!",
        "timestamp": datetime.now().isoformat(),
        "routes": [str(rule) for rule in app.url_map.iter_rules()][:10]  # Show first 10 routes
    })

# Database debug endpoint
@app.route("/db-status")
def db_status():
    """Debug endpoint to check database status"""
    try:
        import os
        db_path = db_manager.db_path
        db_abs_path = os.path.abspath(db_path)
        
        # Get database stats
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Count records in all main tables
        stats = {}
        for table in ['users', 'campaigns', 'integrations', 'user_profiles']:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            except:
                stats[table] = "table_not_found"
        
        # Get recent users
        recent_users = []
        try:
            cursor.execute("SELECT email, created_at, is_active, email_verified FROM users ORDER BY created_at DESC LIMIT 5")
            recent_users = [{"email": row[0], "created_at": row[1], "is_active": row[2], "email_verified": row[3]} for row in cursor.fetchall()]
        except:
            recent_users = []
        
        # Check if /app/db directory exists and is writable
        app_db_exists = os.path.exists('/app/db')
        app_db_writable = os.access('/app/db', os.W_OK) if app_db_exists else False
        
        conn.close()
        
        return jsonify({
            "database_path": db_abs_path,
            "database_exists": os.path.exists(db_abs_path),
            "database_size": os.path.getsize(db_abs_path) if os.path.exists(db_abs_path) else 0,
            "database_writable": os.access(os.path.dirname(db_abs_path), os.W_OK),
            "app_db_directory_exists": app_db_exists,
            "app_db_directory_writable": app_db_writable,
            "current_working_directory": os.getcwd(),
            "environment_database_path": os.getenv('DATABASE_PATH'),
            "table_counts": stats,
            "recent_users": recent_users,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        import os  # Import here in case it's not available globally
        return jsonify({
            "error": str(e), 
            "database_path": getattr(db_manager, 'db_path', 'unknown'),
            "current_working_directory": os.getcwd(),
            "app_db_exists": os.path.exists('/app/db') if os.path.exists('/app') else "app_directory_not_found",
            "timestamp": datetime.now().isoformat()
        }), 500

# Test login endpoint for debugging
@app.route("/test-login")
def test_login():
    """Test endpoint to verify login with existing user"""
    try:
        # Test with the user from db-status
        test_email = "baruchdakpovi.dev@gmail.com"
        
        # Try different common passwords
        test_passwords = ["password123", "test123", "123456", "password", "74FNpKDcDFhSfNc"]
        
        results = []
        for test_password in test_passwords:
            print(f"Testing login with {test_email} / {test_password}")
            user = auth_manager.user_manager.authenticate_user(test_email, test_password)
            results.append({
                "password_tried": test_password,
                "authentication_result": dict(user) if user else None
            })
        
        # Also check if user exists in database
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, name, is_active, email_verified FROM users WHERE email = ?", (test_email,))
        user_in_db = cursor.fetchone()
        conn.close()
        
        return jsonify({
            "test_email": test_email,
            "user_in_database": dict(user_in_db) if user_in_db else None,
            "password_tests": results,
            "note": "If all password tests fail, the issue is likely password hashing"
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# Debug password hash endpoint
@app.route("/debug-password-hash")
def debug_password_hash():
    """Debug endpoint to inspect password hashes in database"""
    try:
        test_email = "baruchdakpovi.dev@gmail.com"
        
        # Get user from database
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash FROM users WHERE email = ?", (test_email,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({"error": "User not found"})
        
        password_hash = user['password_hash']
        
        # Analyze the hash format
        hash_analysis = {
            "email": user['email'],
            "hash_length": len(password_hash),
            "hash_preview": password_hash[:30] + "...",
            "contains_dollar": '$' in password_hash,
            "starts_with_bcrypt_prefix": password_hash.startswith(('$2a$', '$2b$', '$2x$', '$2y$')),
            "contains_pbkdf2": 'pbkdf2' in password_hash,
            "hash_format_detected": "unknown"
        }
        
        # Determine likely format
        if password_hash.startswith(('$2a$', '$2b$', '$2x$', '$2y$')):
            hash_analysis["hash_format_detected"] = "bcrypt"
        elif 'pbkdf2$' in password_hash:
            hash_analysis["hash_format_detected"] = "pbkdf2_new"
        elif '$' in password_hash and not password_hash.startswith('$'):
            hash_analysis["hash_format_detected"] = "pbkdf2_legacy"
        
        # Test with a known password to see if we can create a matching hash
        test_password = "test123"
        
        # Create new hash with current system
        from auth.security_manager import SecurityManager
        security = SecurityManager()
        new_hash = security.hash_password(test_password)
        
        hash_analysis.update({
            "new_hash_sample": new_hash[:30] + "...",
            "new_hash_format": "bcrypt" if new_hash.startswith(('$2a$', '$2b$', '$2x$', '$2y$')) else "pbkdf2"
        })
        
        return jsonify(hash_analysis)
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# Home and authentication routes
@app.route("/")
def home():
    """Home page with quick search - redirect to dashboard if authenticated"""
    # If user is already authenticated, redirect to dashboard
    if auth_manager.is_authenticated():
        return redirect(url_for('dashboard'))
    
    return render_template('home.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    """Sign in page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"Login attempt - Email: {email}")  # Debug log
        
        if not email or not password:
            print("Missing email or password")  # Debug log
            flash('Email et mot de passe requis', 'error')
            return render_template('auth.html')
        
        print(f"Calling auth_manager.login_user...")  # Debug log
        success, message = auth_manager.login_user(email, password, request)
        print(f"Login result - Success: {success}, Message: {message}")  # Debug log
        
        if success:
            print("Login successful, redirecting to dashboard")  # Debug log
            # Don't flash success messages for login
            return redirect(url_for('dashboard'))
        else:
            print(f"Login failed: {message}")  # Debug log
            flash(message, 'error')
    
    return render_template('auth.html')

@app.route('/signup', methods=['GET', 'POST']) 
def signup():
    """Sign up page"""
    # Check if there's a pending Google registration
    pending_google = session.get('pending_google_registration')
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        terms = request.form.get('terms')
        
        # If this is a Google-initiated signup, pre-fill from session data
        if pending_google and not name:
            name = pending_google.get('name')
        if pending_google and not email:
            email = pending_google.get('email')
        
        if not all([name, email, password, confirm_password]):
            flash('Tous les champs sont requis', 'error')
            return render_template('auth.html', pending_google=pending_google)
        
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas', 'error')
            return render_template('auth.html', pending_google=pending_google)
        
        if not terms:
            flash('Vous devez accepter les conditions d\'utilisation', 'error')
            return render_template('auth.html', pending_google=pending_google)
        
        # Type checks to satisfy linter
        if not isinstance(name, str) or not isinstance(email, str) or not isinstance(password, str):
            flash('Données invalides', 'error')
            return render_template('auth.html', pending_google=pending_google)
        
        user_id = auth_manager.register_user(email, password, name)
        print(f"Signup attempt - Email: {email}, User ID returned: {user_id}")  # Debug log
        
        if user_id:
            print(f"User created successfully with ID: {user_id}")  # Debug log
            # If this was a Google-initiated signup, connect Google Sheets automatically
            if pending_google and pending_google.get('credentials'):
                try:
                    db_integration_manager = DatabaseIntegrationManager(db_manager)
                    db_integration_manager.update_integration(
                        user_id, 
                        'google_sheets', 
                        pending_google['credentials'],
                        is_active=True
                    )
                    print(f"Auto-connected Google Sheets for new user {user_id}")
                except Exception as e:
                    print(f"Error auto-connecting Google Sheets for new user: {e}")
                
                # Clear pending registration
                session.pop('pending_google_registration', None)
                
            flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('signin'))
        else:
            flash('Erreur lors de la création du compte. Cet email est peut-être déjà utilisé.', 'error')
    
    return render_template('auth.html', pending_google=pending_google)

@app.route('/logout')
def logout():
    """Logout user"""
    auth_manager.logout_user()
    # Don't flash logout message
    return redirect(url_for('home'))

# Public SaaS pages
@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/team')
def team():
    """Team page"""
    return render_template('team.html')

@app.route('/pricing')
def pricing():
    """Pricing page"""
    return render_template('pricing.html')

@app.route('/api/quick-search', methods=['POST'])
def quick_search():
    """Quick search for home page"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        limit = data.get('limit', 3)
        
        if not query:
            return jsonify({'articles': []})
        
        # Perform quick search (limited results for non-authenticated users)
        current_user = session.get('user_id')
        articles = fetch_articles_multi_source(query, max_items=limit, user_id=current_user)
        
        # Format articles for display
        formatted_articles = []
        for article in articles[:limit]:
            formatted_articles.append({
                'title': article.get('title', ''),
                'source': article.get('source', ''),
                'date': article.get('date', ''),
                'summary': article.get('summary', article.get('description', ''))[:150] + '...'
            })
        
        return jsonify({'articles': formatted_articles})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Secured routes (require authentication)
@app.route("/dashboard")
@auth_manager.require_auth
def dashboard():
    """Dashboard page - secured"""
    # Get current user
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    
    # Get dashboard data
    stats = get_dashboard_stats(user_id)
    campaigns = campaign_manager.get_user_campaigns(user_id)[:5]  # Recent campaigns
    integrations = get_dashboard_integrations(user_id)
    
    return render_template("dashboard.html", 
                         stats=stats, 
                         campaigns=campaigns, 
                         integrations=integrations,
                         user=current_user)

@app.route("/veille")
@auth_manager.require_auth
def veille():
    """Monitoring page - secured"""
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    query = request.args.get("q")
    
    if not query or query.strip() == "":
        # Return to dashboard with error, including all required template variables
        stats = get_dashboard_stats(user_id)
        campaigns = campaign_manager.get_user_campaigns(user_id)[:5]
        integrations = get_dashboard_integrations(user_id)
        
        return render_template("dashboard.html", 
                             articles=[], 
                             error="Veuillez saisir un mot-clé.",
                             stats=stats,
                             campaigns=campaigns,
                             integrations=integrations,
                             user=current_user)

    try:
        articles = fetch_articles_multi_source(query, max_items=25, show_keyword_suggestions=False, user_id=user_id)
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
            [a["date"], a["source"], a["titre"], a["url"]]
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
    stats = get_dashboard_stats(user_id)
    campaigns = campaign_manager.get_user_campaigns(user_id)[:5]
    integrations = get_dashboard_integrations(user_id)

    return render_template("dashboard.html", 
                         articles=articles,
                         stats=stats,
                         campaigns=campaigns,
                         integrations=integrations,
                         user=current_user)

# Campaign Management Routes
@app.route("/campaigns")
@auth_manager.require_auth
def campaigns():
    """Campaigns management page - secured"""
    # Clear any lingering flash messages to prevent them from appearing on campaigns page
    session.pop('_flashes', None)
    
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    all_campaigns = campaign_manager.get_user_campaigns(user_id)
    
    # Add spreadsheet URLs for campaigns that have Google Sheets integration
    for campaign in all_campaigns:
        if 'google_sheets' in campaign.get('integrations', []) and campaign.get('spreadsheet_id'):
            campaign['spreadsheet_url'] = f"https://docs.google.com/spreadsheets/d/{campaign['spreadsheet_id']}"
        
    return render_template("campaigns.html", campaigns=all_campaigns, user=current_user)

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
@auth_manager.require_auth
def edit_campaign(campaign_id):
    """Edit campaign form - secured"""
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
    """Save or update a campaign - secured"""
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    
    try:
        # Get user AI preferences from the database
        try:
            user_profile = profile_manager.get_user_profile(user_id)
        except:
            user_profile = {}
        
        # Campaign data - keyword expansion enabled by default
        data = {
            'name': request.form.get('name', '').strip(),
            'keywords': request.form.get('keywords', '').strip(),
            'frequency': request.form.get('frequency', '').strip(),
            'integrations': request.form.getlist('integrations'),
            'max_articles': int(request.form.get('max_articles', 25)),
            'description': request.form.get('description', '').strip(),
            # AI Enhancement Options - keyword expansion enabled by default, others removed
            'keyword_expansion_enabled': True,  # Always enabled - core feature
            'ai_model': user_profile.get('ai_model', 'ollama-deepseek-r1:1.5b') if user_profile else 'ollama-deepseek-r1:1.5b'
        }

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
            campaign_manager.update_campaign(campaign_id, user_id, data)
            flash("Campagne mise à jour avec succès !", 'success')
            return redirect(url_for("campaigns"))
        else:
            # Create new campaign
            new_campaign_id = campaign_manager.create_campaign(user_id, data)
            
            # Handle Google Sheets integration
            if 'google_sheets' in data.get('integrations', []):
                try:
                    # Check if user has Google Sheets connected in database
                    db_integration_manager = DatabaseIntegrationManager(db_manager)
                    if db_integration_manager.is_google_sheets_connected(user_id):
                        spreadsheet_choice = request.form.get('spreadsheet_choice', 'new')
                        spreadsheet_id = request.form.get('spreadsheet_id')
                        
                        if spreadsheet_choice == 'existing' and spreadsheet_id:
                            # Link existing spreadsheet to campaign
                            if new_campaign_id:
                                campaign_manager.update_campaign_spreadsheet(new_campaign_id, user_id, spreadsheet_id, f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
                        else:
                            # Create new spreadsheet
                            sheet_info = sheets_manager.create_campaign_spreadsheet_for_user(user_id, data['name'])
                            if sheet_info and new_campaign_id:
                                campaign_manager.update_campaign_spreadsheet(new_campaign_id, user_id, sheet_info['id'], sheet_info['url'])
                    else:
                        print(f"User {user_id} does not have Google Sheets connected")
                except Exception as e:
                    print(f"Error setting up Google Sheets for campaign: {e}")
                    flash("Campagne créée, mais erreur lors de la configuration de Google Sheets.", 'warning')
            
            # Step 2: Initial campaign fetch with expanded keywords
            if new_campaign_id:
                campaign = campaign_manager.get_campaign(new_campaign_id, user_id)
                if campaign:
                    try:
                        # Run initial campaign with expanded keywords
                        campaign_scheduler.run_campaign(campaign)
                        flash("Campagne créée avec succès ! Articles initiaux récupérés avec mots-clés étendus.", 'success')
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
@auth_manager.require_auth
def pause_campaign(campaign_id):
    """Pause campaign - secured"""
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    success = campaign_manager.pause_campaign(campaign_id, user_id)
    return jsonify({'success': success})

@app.route("/campaigns/<campaign_id>/resume", methods=["POST"])
@auth_manager.require_auth
def resume_campaign(campaign_id):
    """Resume campaign - secured"""
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    success = campaign_manager.resume_campaign(campaign_id, user_id)
    return jsonify({'success': success})

@app.route("/campaigns/<campaign_id>", methods=["DELETE"])
@auth_manager.require_auth
def delete_campaign(campaign_id):
    """Delete campaign - secured"""
    current_user = auth_manager.get_current_user()
    if not current_user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    user_id = current_user['id']
    data = request.get_json() or {}
    delete_sheet = data.get('delete_sheet', False)
    
    # Get campaign info before deletion to verify ownership
    campaign = campaign_manager.get_campaign(campaign_id, user_id)
    if not campaign:
        return jsonify({'success': False, 'error': 'Campaign not found or access denied'}), 404

    if campaign and delete_sheet and campaign.get('spreadsheet_id'):
        # Delete the associated Google Sheet
        try:
            if sheets_manager.is_google_sheets_connected():
                success = sheets_manager.delete_spreadsheet(campaign['spreadsheet_id'])
                if success:
                    print(f"Successfully deleted spreadsheet for campaign '{campaign['name']}' (ID: {campaign.get('spreadsheet_id')})")
                else:
                    print(f"Failed to delete spreadsheet for campaign '{campaign['name']}' (ID: {campaign.get('spreadsheet_id')})")
            else:
                print("Google Sheets not connected - cannot delete spreadsheet")
        except Exception as e:
            print(f"Error deleting spreadsheet: {e}")
    
    success = campaign_manager.delete_campaign(campaign_id, user_id)
    return jsonify({'success': success})# Integration Routes
@app.route("/integrations")
@login_required
def integrations():
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    db_integration_manager = DatabaseIntegrationManager(db_manager)
    
    integrations_status = {
        'google_sheets': db_integration_manager.is_google_sheets_connected(user_id),
        'airtable': bool(db_integration_manager.get_integration(user_id, 'airtable'))
    }
    
    # Basic stats
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
        integration_manager = IntegrationManager()
        
        success = integration_manager.configure_airtable(current_user['id'], api_key, base_id, table_name)
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
    db_integration_manager = DatabaseIntegrationManager(db_manager)
    success = db_integration_manager.disconnect_integration(user_id, integration)
    return jsonify({'success': success})

# Profile Routes
@app.route("/profile")
def profile():
    if 'user_id' not in session:
        return redirect('/auth')
    
    user_id = session['user_id']
    
    # Get real user data from database
    user = user_manager.get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect('/auth')
    
    user_data = {
        'name': user['name'],
        'email': user['email'],
        'created_at': user['created_at'][:10] if user.get('created_at') else '2024-01-01',
        'api_key': None  # Add API key handling if needed
    }
    
    # Get user statistics from database
    user_stats = campaign_manager.get_user_stats(user_id)
    
    # Check actual integrations status
    integrations_count = 0
    try:
        # Check Google Sheets integration
        if 'credentials' in session:
            integrations_count += 1
    except:
        pass
    
    stats = {
        'total_campaigns': user_stats.get('total_campaigns', 0),
        'total_articles': user_stats.get('total_articles', 0),
        'integrations_count': integrations_count
    }
    
    # Get user profile for AI settings
    user_profile = user_profile_manager.get_user_profile(user_id=user_id)
    
    return render_template("profile.html", user=user_data, stats=stats, profile=user_profile)

@app.route("/profile/ai-settings")
def profile_ai_settings():
    if 'user_id' not in session:
        return redirect('/auth')
    user_id = session['user_id']
    user_profile = user_profile_manager.get_user_profile(user_id=user_id)
    return render_template("profile_ai_settings.html", profile=user_profile)

@app.route("/profile/ai-settings", methods=["POST"])
def save_ai_settings():
    """Save AI settings - keyword expansion enabled by default"""
    if 'user_id' not in session:
        return redirect('/auth')
    user_id = session['user_id']
    
    settings = {
        'ai_model': request.form.get('ai_model', 'ollama-deepseek-r1:1.5b'),
        'keyword_expansion_enabled': True,  # Always enabled - core feature
    }
    
    success = user_profile_manager.update_user_profile(user_id=user_id, updates=settings)
    
    if request.content_type == 'application/json':
        return jsonify({'success': success})
    else:
        if success:
            flash('Paramètres IA sauvegardés avec succès!', 'success')
        else:
            flash('Erreur lors de la sauvegarde des paramètres IA.', 'error')
        
        # Redirect to profile page after successful save
        return redirect(url_for('profile'))

# API Routes
@app.route("/api/preview", methods=["POST"])
def api_preview():
    data = request.get_json()
    keywords = data.get('keywords', '')
    
    try:
        try:
            articles = fetch_articles_multi_source(
                keywords, 
                max_items=25, 
                show_keyword_suggestions=False,  # Don't show suggestions in preview
                user_id=None  # No user context in preview
            )
        except Exception as e:
            print(f"Error with multi-source fetch, falling back to RSS: {e}")
            articles = fetch_articles_rss(keywords, max_items=5)
        return jsonify({'success': True, 'articles': articles})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/campaigns/status")
def api_campaigns_status():
    campaigns = campaign_manager.get_user_campaigns('default')
    return jsonify({'campaigns': campaigns})

@app.route('/health')
def health_check():
    """Health check endpoint for production monitoring"""
    try:
        # Check database connection
        db_status = "ok"
        try:
            db_manager.get_connection().close()
        except:
            db_status = "error"
        
        # Check Ollama if available
        ollama_status = "not_configured"
        try:
            import requests
            response = requests.get("http://localhost:11434/api/version", timeout=5)
            ollama_status = "ok" if response.status_code == 200 else "error"
        except:
            ollama_status = "unavailable"
        
        # Check scheduler status
        scheduler_status = "ok"  # Assume OK since it's hard to check APScheduler status
        try:
            if hasattr(campaign_scheduler, 'scheduler') and hasattr(campaign_scheduler.scheduler, 'running'):
                scheduler_status = "ok" if campaign_scheduler.scheduler.running else "stopped"
        except:
            scheduler_status = "unknown"
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {
                'database': db_status,
                'ollama': ollama_status,
                'scheduler': scheduler_status,
                'flask': 'ok'
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route("/auth")
def auth():
    return start_auth()

@app.route("/auth/reauth")
def reauth():
    """Force re-authentication to get fresh credentials"""
    # Clear existing credentials
    if "credentials" in session:
        del session["credentials"]
    # Note: We don't need to update integration status here as it will be set during OAuth callback
    return start_auth()

@app.route("/oauth2callback")
def oauth2callback():
    try:
        finish_auth()
        
        # Get Google user info from session
        google_user_info = session.get("google_user_info")
        
        # Check if user is already authenticated
        if auth_manager.is_authenticated():
            # User is logged in - store Google credentials for their account
            current_user = auth_manager.get_current_user()
            if not current_user:
                flash("Erreur d'authentification. Veuillez vous reconnecter.", 'error')
                return redirect(url_for("signin"))
            
            user_id = current_user['id']
            
            # Store Google credentials in database
            if "credentials" in session:
                try:
                    db_integration_manager = DatabaseIntegrationManager(db_manager)
                    success = db_integration_manager.update_integration(
                        user_id, 
                        'google_sheets', 
                        session["credentials"],
                        is_active=True
                    )
                    if success:
                        print(f"Google credentials stored securely for user {user_id}")
                        return redirect(url_for("integrations"))
                    else:
                        raise Exception("Failed to store credentials")
                except Exception as e:
                    print(f"Error storing credentials in database: {e}")
                    flash("Erreur lors de la sauvegarde des identifiants.", 'error')
                    return redirect(url_for("integrations"))
        
        else:
            # User is not logged in - try to find/create account based on Google email
            if google_user_info and google_user_info.get('email'):
                google_email = google_user_info['email']
                google_name = google_user_info.get('name', google_email.split('@')[0])
                
                # Check if user exists with this email
                user = user_manager.get_user_by_email(google_email)
                
                if user:
                    # User exists - log them in automatically
                    session['user_id'] = user['id']
                    session['username'] = user['email']
                    session['client_fingerprint'] = auth_manager.security.get_client_fingerprint()
                    
                    # Create session in database
                    session_token = auth_manager.session_manager.create_session(
                        user['id'], 
                        request.environ.get('REMOTE_ADDR', 'unknown'),
                        request.headers.get('User-Agent', 'Unknown')
                    )
                    session['session_token'] = session_token
                    
                    # Update last login
                    user_manager.update_last_login(user['id'])
                    
                    # Store Google credentials
                    if "credentials" in session:
                        db_integration_manager = DatabaseIntegrationManager(db_manager)
                        db_integration_manager.update_integration(
                            user['id'], 
                            'google_sheets', 
                            session["credentials"],
                            is_active=True
                        )
                    
                    return redirect(url_for("dashboard"))
                else:
                    # Store Google info in session for registration
                    session['pending_google_registration'] = {
                        'email': google_email,
                        'name': google_name,
                        'credentials': session.get("credentials")
                    }
                    flash(f"Compte Google détecté ({google_email}). Veuillez créer votre compte pour continuer.", 'info')
                    return redirect(url_for("signup"))
            else:
                # No Google user info - redirect to signin
                    flash("Veuillez vous connecter à votre compte pour connecter Google Sheets.", 'info')
                    return redirect(url_for("signin"))
        
        # Fallback - should never reach here but ensure we return a response
        flash("Erreur inattendue lors de la connexion.", 'error')
        return redirect(url_for("signin"))
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        flash("Erreur lors de la connexion Google Sheets. Veuillez réessayer.", 'error')
        return redirect(url_for("signin"))

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
    # Check authentication first
    if not auth_manager.is_authenticated():
        return jsonify({'error': 'Authentication required'}), 401
    
    current_user = auth_manager.get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401
    
    user_id = current_user['id']
    
    # Check Google Sheets connection
    error_response = check_google_sheets_access(user_id)
    if error_response:
        return error_response
    
    try:
        # Debug: Check what credentials we have
        creds_data = session.get("credentials")
        if not creds_data:
            return jsonify({'error': 'No credentials in session'}), 401
            
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
        campaigns = campaign_manager.get_user_campaigns('default')
        
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
    
    campaign = campaign_manager.get_campaign(campaign_id, 'default')
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
@login_required
def file_management():
    """File and folder management page"""
    # Get current user
    current_user = auth_manager.get_current_user()
    if not current_user:
        return redirect(url_for('signin'))
    
    user_id = current_user['id']
    
    # Check if user has Google Sheets connected
    db_integration_manager = DatabaseIntegrationManager(db_manager)
    if not db_integration_manager.is_google_sheets_connected(user_id):
        return render_template("files.html", 
                             spreadsheets=[], 
                             error="Veuillez vous connecter à Google Sheets pour voir vos fichiers.")
    
    try:
        # Get all spreadsheets for this user
        all_spreadsheets = []
        
        # Try to get user's spreadsheets using their credentials
        try:
            # Get user credentials from session first, then database
            if "credentials" in session:
                all_spreadsheets = sheets_manager.list_user_spreadsheets()
            else:
                # Use user-specific credentials from database
                integrations = db_integration_manager.get_user_integrations(user_id)
                google_integration = None
                for integration in integrations:
                    if integration['integration_type'] == 'google_sheets' and integration['is_active']:
                        google_integration = integration
                        break
                
                if google_integration:
                    # Temporarily set credentials in session for this request
                    session["credentials"] = google_integration['config']
                    all_spreadsheets = sheets_manager.list_user_spreadsheets()
        except Exception as e:
            print(f"Error getting user spreadsheets: {e}")
            all_spreadsheets = []
        
        # Get campaigns with their associated spreadsheets for this user
        campaigns = campaign_manager.get_user_campaigns(user_id)
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
            campaigns = campaign_manager.get_user_campaigns('default')
            for campaign in campaigns:
                if campaign.get('spreadsheet_id') == file_id:
                    campaign_to_delete = campaign
                    break
        
        # Delete the spreadsheet
        success = sheets_manager.delete_spreadsheet(file_id)
        
        if success:
            # Delete associated campaign if requested
            if campaign_to_delete and delete_campaign:
                campaign_manager.delete_campaign(campaign_to_delete['id'], 'default')
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Impossible de supprimer le fichier'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__=="__main__":
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