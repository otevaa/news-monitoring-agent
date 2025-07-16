import gspread
from oauth2client.service_account import ServiceAccountCredentials

def save_to_gsheet(rows, spreadsheet_name='Veille resultats'):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open(spreadsheet_name).sheet1
    for row in rows:
        sheet.append_row([row["date"], row["source"], row["titre"], row["url"], row["resume"]])
