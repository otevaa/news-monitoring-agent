from flask import Flask, render_template, request, redirect, session, url_for
from agent.fetch_rss import fetch_articles_rss
from agent.google_oauth import start_auth, finish_auth, get_sheets_service

app = Flask(__name__)
app.secret_key = "ta-cle-ultra-secrete"

@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/veille")
def veille():
    query = request.args.get("q")
    if not query or query.strip() == "":
        return render_template("dashboard.html", articles=[], error="Veuillez saisir un mot-clé.")

    articles = fetch_articles_rss(query)
    session["articles"] = articles  # pour y accéder après l'auth

    if "credentials" not in session:
        return redirect(url_for("auth"))

    # Sauvegarde dans le Google Sheet de l'utilisateur connecté
    sheets = get_sheets_service()
    spreadsheet_id = "TON_SPREADSHEET_ID"  # ou créé dynamiquement
    range_name = "Feuille1!A1"

    values = [
        [a["date"], a["source"], a["titre"], a["url"], a["resume"]]
        for a in articles
    ]
    body = {"values": values}
    sheets.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

    return render_template("dashboard.html", articles=articles)

@app.route("/auth")
def auth():
    return start_auth()

@app.route("/oauth2callback")
def oauth2callback():
    finish_auth()
    return redirect(url_for("home"))

if __name__=="__main__":
    app.run(debug=True)