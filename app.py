from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from agent.fetch_rss import fetch_articles_rss
from agent.google_oauth import start_auth, finish_auth, get_sheets_service
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

# Start the campaign scheduler
campaign_scheduler.start()

# Ensure scheduler is stopped when app shuts down
atexit.register(lambda: campaign_scheduler.stop())

@app.route("/")
def home():
    # Mock data for now - replace with actual database queries
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
                         stats=stats, 
                         campaigns=campaigns, 
                         integrations=integrations)

@app.route("/veille")
def veille():
    query = request.args.get("q")
    if not query or query.strip() == "":
        return render_template("dashboard.html", articles=[], error="Veuillez saisir un mot-clé.")

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

    return render_template("dashboard.html", articles=articles)

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
    else:
        campaign_manager.create_campaign(data)
    
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

@app.route("/oauth2callback")
def oauth2callback():
    finish_auth()
    return redirect(url_for("home"))

if __name__=="__main__":
    app.run(debug=True)