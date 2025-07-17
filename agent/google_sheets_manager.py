from flask import session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime

class GoogleSheetsManager:
    def __init__(self):
        self.sheets_data_file = "google_sheets_data.json"
        self.sheets_data = self._load_sheets_data()
    
    def _load_sheets_data(self) -> Dict:
        """Load Google Sheets data from JSON file"""
        if os.path.exists(self.sheets_data_file):
            try:
                with open(self.sheets_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _save_sheets_data(self):
        """Save Google Sheets data to JSON file"""
        try:
            with open(self.sheets_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.sheets_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving sheets data: {e}")
    
    def get_sheets_service(self):
        """Get authenticated Google Sheets service"""
        if "credentials" not in session:
            print("No credentials in session")
            return None
        
        try:
            creds_data = session["credentials"]
            # Ensure all required fields are present for refresh
            required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
            missing_fields = [field for field in required_fields if field not in creds_data]
            
            if missing_fields:
                print(f"Missing required credential fields: {missing_fields}")
                return None
                
            creds = Credentials(**creds_data)
            return build("sheets", "v4", credentials=creds)
        except Exception as e:
            print(f"Error creating sheets service: {e}")
            return None
    
    def get_drive_service(self):
        """Get authenticated Google Drive service"""
        if "credentials" not in session:
            print("No credentials in session")
            return None
        
        try:
            creds_data = session["credentials"]
            # Ensure all required fields are present for refresh
            required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
            missing_fields = [field for field in required_fields if field not in creds_data]
            
            if missing_fields:
                print(f"Missing required credential fields: {missing_fields}")
                return None
                
            creds = Credentials(**creds_data)
            return build("drive", "v3", credentials=creds)
        except Exception as e:
            print(f"Error creating drive service: {e}")
            return None
    
    def list_user_spreadsheets(self) -> List[Dict]:
        """List all spreadsheets accessible to the user"""
        drive_service = self.get_drive_service()
        if not drive_service:
            return []
        
        try:
            results = drive_service.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                fields="files(id, name, createdTime, modifiedTime)"
            ).execute()
            
            spreadsheets = results.get('files', [])
            return [
                {
                    'id': sheet['id'],
                    'name': sheet['name'],
                    'created_time': sheet['createdTime'],
                    'modified_time': sheet['modifiedTime'],
                    'url': f"https://docs.google.com/spreadsheets/d/{sheet['id']}"
                }
                for sheet in spreadsheets
            ]
        except HttpError as e:
            print(f"Error listing spreadsheets: {e}")
            return []
    
    def create_campaign_spreadsheet(self, campaign_name: str) -> Optional[Dict]:
        """Create a new spreadsheet for a campaign"""
        sheets_service = self.get_sheets_service()
        if not sheets_service:
            return None
        
        try:
            # Create spreadsheet
            spreadsheet_body = {
                'properties': {
                    'title': f'NewsMonitor - {campaign_name}',
                    'locale': 'fr_FR',
                    'timeZone': 'Europe/Paris'
                }
            }
            
            spreadsheet = sheets_service.spreadsheets().create(
                body=spreadsheet_body
            ).execute()
            
            spreadsheet_id = spreadsheet['spreadsheetId']
            
            # Setup headers
            headers = [
                ['Date', 'Source', 'Titre', 'URL', 'Résumé', 'Campagne', 'Mots-clés']
            ]
            
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='A1:G1',
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
            
            # Format headers
            format_body = {
                'requests': [
                    {
                        'repeatCell': {
                            'range': {
                                'sheetId': 0,
                                'startRowIndex': 0,
                                'endRowIndex': 1,
                                'startColumnIndex': 0,
                                'endColumnIndex': 7
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.9},
                                    'textFormat': {
                                        'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
                                        'bold': True
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                        }
                    }
                ]
            }
            
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=format_body
            ).execute()
            
            # Store spreadsheet info
            sheet_info = {
                'id': spreadsheet_id,
                'name': f'NewsMonitor - {campaign_name}',
                'created_at': datetime.now().isoformat(),
                'campaign_name': campaign_name,
                'url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                'articles_count': 0
            }
            
            self.sheets_data[spreadsheet_id] = sheet_info
            self._save_sheets_data()
            
            return sheet_info
            
        except HttpError as e:
            print(f"Error creating spreadsheet: {e}")
            return None
    
    def save_articles_to_spreadsheet(self, spreadsheet_id: str, articles: List[Dict], 
                                   campaign_name: str = "", keywords: str = "") -> bool:
        """Save articles to an existing spreadsheet"""
        sheets_service = self.get_sheets_service()
        if not sheets_service:
            return False
        
        try:
            # Prepare values
            values = []
            for article in articles:
                values.append([
                    article.get('date', ''),
                    article.get('source', ''),
                    article.get('titre', ''),
                    article.get('url', ''),
                    article.get('resume', ''),
                    campaign_name,
                    keywords
                ])
            
            # Append to spreadsheet
            body = {'values': values}
            sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range='A:G',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            # Update article count
            if spreadsheet_id in self.sheets_data:
                self.sheets_data[spreadsheet_id]['articles_count'] += len(articles)
                self.sheets_data[spreadsheet_id]['last_updated'] = datetime.now().isoformat()
                self._save_sheets_data()
            
            return True
            
        except HttpError as e:
            print(f"Error saving to spreadsheet: {e}")
            return False
    
    def get_campaign_spreadsheets(self, campaign_name: Optional[str] = None) -> List[Dict]:
        """Get spreadsheets for a specific campaign or all campaign spreadsheets"""
        if campaign_name:
            return [
                sheet for sheet in self.sheets_data.values() 
                if sheet.get('campaign_name') == campaign_name
            ]
        else:
            return list(self.sheets_data.values())
    
    def get_spreadsheet_info(self, spreadsheet_id: str) -> Optional[Dict]:
        """Get information about a specific spreadsheet"""
        return self.sheets_data.get(spreadsheet_id)
    
    def is_google_sheets_connected(self) -> bool:
        """Check if Google Sheets is connected with valid credentials"""
        if "credentials" not in session:
            return False
        
        creds_data = session["credentials"]
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
        return all(field in creds_data for field in required_fields)
