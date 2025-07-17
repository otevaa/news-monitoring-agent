from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash
from agent.fetch_rss import fetch_articles_rss
from agent.google_oauth import start_auth, finish_auth, get_sheets_service
from agent.google_sheets_manager import GoogleSheetsManager
from agent.campaign_manager import CampaignManager
from agent.integrations import IntegrationManager
from agent.scheduler import campaign_scheduler
import json
from datetime import datetime
import uuid
import atexit

app = Flask(__name__)
app.secret_key = "ta-cle-ultra-secrete"

# Initialize managers
campaign_manager = CampaignManager()
integration_manager = IntegrationManager()
sheets_manager = GoogleSheetsManager()

# Start the campaign scheduler
campaign_scheduler.start()

# Ensure scheduler is stopped when app shuts down
atexit.register(lambda: campaign_scheduler.stop())

@app.route("/")
def home():
    # Update Google Sheets integration status
    google_sheets_connected = sheets_manager.is_google_sheets_connected()
    integration_manager.update_google_sheets_status(google_sheets_connected)
    
    # Mock data for now - replace with actual database queries
    stats = {
        'active_campaigns': len(campaign_manager.get_active_campaigns()),
        'total_articles': campaign_manager.get_total_articles_count(),
        'articles_today': campaign_manager.get_articles_today_count(),
        'integrations_count': integration_manager.get_active_integrations_count()
    }
    
    campaigns = campaign_manager.get_recent_campaigns(limit=5)
    integrations = {
        'google_sheets': google_sheets_connected,
        'airtable': integration_manager.is_airtable_configured()
    }
    
    return render_template("dashboard.html", 
                         stats=stats, 
                         campaigns=campaigns, 
                         integrations=integrations)

@app.route("/veille")
def veille():
    query = request.args.get("q")
    if not query or query.strip() == "":
        # Return to dashboard with error, including all required template variables
        stats = {
            'active_campaigns': len(campaign_manager.get_active_campaigns()),
            'total_articles': campaign_manager.get_total_articles_count(),
            'articles_today': campaign_manager.get_articles_today_count(),
            'integrations_count': integration_manager.get_active_integrations_count()
        }
        
        campaigns = campaign_manager.get_recent_campaigns(limit=5)
        integrations = {
            'google_sheets': session.get('credentials') is not None,
            'airtable': integration_manager.is_airtable_configured()
        }
        
        return render_template("dashboard.html", 
                             articles=[], 
                             error="Veuillez saisir un mot-clé.",
                             stats=stats,
                             campaigns=campaigns,
                             integrations=integrations)

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
    stats = {
        'active_campaigns': len(campaign_manager.get_active_campaigns()),
        'total_articles': campaign_manager.get_total_articles_count(),
        'articles_today': campaign_manager.get_articles_today_count(),
        'integrations_count': integration_manager.get_active_integrations_count()
    }
    
    campaigns = campaign_manager.get_recent_campaigns(limit=5)
    integrations = {
        'google_sheets': session.get('credentials') is not None,
        'airtable': integration_manager.is_airtable_configured()
    }

    return render_template("dashboard.html", 
                         articles=articles,
                         stats=stats,
                         campaigns=campaigns,
                         integrations=integrations)

# Campaign Management Routes
@app.route("/campaigns")
def campaigns():
    all_campaigns = campaign_manager.get_all_campaigns()
    return render_template("campaigns.html", campaigns=all_campaigns)

@app.route("/campaigns/create")
def create_campaign():
    return render_template("campaign_form.html")

@app.route("/campaigns/<campaign_id>/edit")
def edit_campaign(campaign_id):
    campaign = campaign_manager.get_campaign(campaign_id)
    return render_template("campaign_form.html", campaign=campaign)

@app.route("/campaigns/create", methods=["POST"])
@app.route("/campaigns/<campaign_id>/edit", methods=["POST"])
def save_campaign(campaign_id=None):
    data = {
        'name': request.form.get('name'),
        'keywords': request.form.get('keywords'),
        'frequency': request.form.get('frequency'),
        'integrations': request.form.getlist('integrations'),
        'max_articles': int(request.form.get('max_articles', 25)),
        'description': request.form.get('description', '')
    }
    
    if campaign_id:
        campaign_manager.update_campaign(campaign_id, data)
        flash("Campagne mise à jour avec succès !", 'success')
    else:
        new_campaign_id = campaign_manager.create_campaign(data)
        
        # Automatically create Google Sheet for new campaigns if user is authenticated
        if "credentials" in session:
            try:
                # Check if credentials are complete
                if not sheets_manager.is_google_sheets_connected():
                    flash("Campagne créée, mais veuillez vous reconnecter à Google Sheets pour créer la feuille associée.", 'warning')
                else:
                    sheet_info = sheets_manager.create_campaign_spreadsheet(data['name'])
                    
                    if sheet_info:
                        # Store sheet info in campaign data
                        campaign = campaign_manager.get_campaign(new_campaign_id)
                        if campaign:
                            campaign['spreadsheet_id'] = sheet_info['id']
                            campaign['spreadsheet_url'] = sheet_info['url']
                            campaign_manager._save_campaigns()
                            
                        flash(f"Campagne créée avec succès ! Feuille Google Sheets associée : {sheet_info['name']}", 'success')
                    else:
                        flash("Campagne créée, mais impossible de créer la feuille Google Sheets.", 'warning')
            except Exception as e:
                print(f"Error creating spreadsheet: {e}")
                flash("Campagne créée, mais erreur lors de la création de la feuille Google Sheets.", 'warning')
        else:
            flash("Campagne créée avec succès ! Connectez-vous à Google Sheets pour créer une feuille associée.", 'success')
    
    return redirect(url_for('campaigns'))

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

# API Routes
@app.route("/api/preview", methods=["POST"])
def api_preview():
    data = request.get_json()
    keywords = data.get('keywords', '')
    
    try:
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

if __name__=="__main__":
    app.run(debug=True)