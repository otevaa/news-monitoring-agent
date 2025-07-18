from flask import session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import os
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from .secure_credentials import GoogleCredentialsManager

class GoogleSheetsManager:
    def __init__(self):
        self.sheets_data_file = "google_sheets_data.json"
        self.credentials_manager = GoogleCredentialsManager()
        self.sheets_data = self._load_sheets_data()
    
    def _get_credentials(self) -> Optional[Dict]:
        """Get credentials from session or secure storage"""
        # First try to get from Flask session
        try:
            if "credentials" in session:
                return session["credentials"]
        except RuntimeError:
            # We're outside of Flask application context (e.g., in scheduler)
            pass
        
        # Fall back to secure storage
        return self.credentials_manager.get_user_credentials()
    
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
        creds_data = self._get_credentials()
        if not creds_data:
            print("No credentials available")
            return None
        
        try:
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
        creds_data = self._get_credentials()
        if not creds_data:
            print("No credentials available")
            return None
        
        try:
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
            
            # Setup headers (without Keywords column)
            headers = [
                ['Date', 'Source', 'Titre', 'URL', 'Campagne']
            ]
            
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='A1:F1',
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
            
            # Format headers only and set white background for data area
            format_body = {
                'requests': [
                    {
                        'repeatCell': {
                            'range': {
                                'sheetId': 0,
                                'startRowIndex': 0,
                                'endRowIndex': 1,
                                'startColumnIndex': 0,
                                'endColumnIndex': 6
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
                    },
                    {
                        'repeatCell': {
                            'range': {
                                'sheetId': 0,
                                'startRowIndex': 1,
                                'endRowIndex': 1000,
                                'startColumnIndex': 0,
                                'endColumnIndex': 6
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
                                    'textFormat': {
                                        'foregroundColor': {'red': 0.0, 'green': 0.0, 'blue': 0.0},
                                        'bold': False
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                        }
                    },
                    {
                        'updateSheetProperties': {
                            'properties': {
                                'sheetId': 0,
                                'gridProperties': {
                                    'frozenRowCount': 1
                                }
                            },
                            'fields': 'gridProperties.frozenRowCount'
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
            # Filter articles to only include last 2 days
            today = datetime.now().date()
            three_days_ago = today - timedelta(days=2)
            
            filtered_articles = []
            for article in articles:
                article_date_str = article.get('date', '')
                if article_date_str:
                    try:
                        # Parse article date (assuming format like "2025-07-17T10:30:00")
                        article_date = datetime.fromisoformat(article_date_str.replace('Z', '')).date()
                        if article_date >= three_days_ago:
                            filtered_articles.append(article)
                    except:
                        # If date parsing fails, include the article
                        filtered_articles.append(article)
                else:
                    # If no date, include the article
                    filtered_articles.append(article)
            
            if not filtered_articles:
                print(f"No recent articles (last 2 days) to save for campaign '{campaign_name}'")
                return True
            
            # Check for existing articles to avoid duplicates
            existing_articles = set()
            try:
                # Get existing data from spreadsheet
                existing_data = sheets_service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range='A:F'  # Get all columns including title and URL
                ).execute()
                
                existing_values = existing_data.get('values', [])
                if len(existing_values) > 1:  # Skip header row
                    for row in existing_values[1:]:  # Skip header
                        if len(row) >= 4:  # Make sure we have enough columns
                            title = row[2] if len(row) > 2 else ""  # Title column
                            url = row[3] if len(row) > 3 else ""    # URL column
                            
                            # Extract URL from HYPERLINK formula if present
                            if url.startswith('=HYPERLINK('):
                                url_match = re.search(r'=HYPERLINK\("([^"]*)"', url)
                                if url_match:
                                    url = url_match.group(1)
                            
                            # Create identifier using title and URL
                            if title and url:
                                identifier = f"{title.strip()}|{url.strip()}"
                                existing_articles.add(identifier)
                                
                print(f"Found {len(existing_articles)} existing articles in spreadsheet")
            except Exception as e:
                print(f"Warning: Could not check for existing articles: {e}")
            
            # Filter out duplicate articles
            unique_articles = []
            for article in filtered_articles:
                title = article.get('titre', '').strip()
                url = article.get('url', '').strip()
                
                # Extract URL from <a href="URL"> format if needed
                if url:
                    url_match = re.search(r'href="([^"]*)"', url)
                    if url_match:
                        url = url_match.group(1).strip()
                
                identifier = f"{title}|{url}"
                
                if identifier not in existing_articles and title and url:
                    unique_articles.append(article)
                    existing_articles.add(identifier)  # Add to set to avoid duplicates within this batch
                else:
                    print(f"Skipping duplicate article: {title[:50]}...")
            
            if not unique_articles:
                print(f"No new unique articles to save for campaign '{campaign_name}'")
                return True
            
            # Sort articles by date: OLDEST FIRST (chronological order for better timeline)
            unique_articles.sort(key=lambda x: x.get('date', ''), reverse=False)
            
            print(f"Saving {len(unique_articles)} new unique articles (filtered from {len(filtered_articles)} total)")
            print(f"Articles sorted chronologically (oldest first) for better timeline view")
            
            # Prepare values for unique articles only
            values = []
            for article in unique_articles:
                # Use URL as-is (no HYPERLINK formula - Google Sheets will make it clickable automatically)
                url = article.get('url', '')
                if url:
                    # Extract URL from <a href="URL"> format if needed
                    url_match = re.search(r'href="([^"]*)"', url)
                    if url_match:
                        url = url_match.group(1)
                
                # Clean URL - no HYPERLINK formula, just the plain URL
                clean_url = url.replace('"', '').replace("'", "") if url else ""
                
                values.append([
                    article.get('date', ''),
                    article.get('source', ''),
                    article.get('titre', ''),
                    clean_url,  # Just the plain URL - Google Sheets will make it clickable
                    campaign_name
                ])
            
            # Get current row count to know where to insert
            try:
                result = sheets_service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range='A:A'
                ).execute()
                current_rows = len(result.get('values', []))
                start_row = current_rows + 1
            except:
                start_row = 2  # Start after header if we can't get current data
            
            # Append to spreadsheet
            body = {'values': values}
            sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range='A:F',
                valueInputOption='USER_ENTERED',  # Use USER_ENTERED to interpret formulas
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            # Format the newly added data rows to have white background and black text
            if values:
                end_row = start_row + len(values) - 1
                format_body = {
                    'requests': [
                        {
                            'repeatCell': {
                                'range': {
                                    'sheetId': 0,
                                    'startRowIndex': start_row - 1,  # 0-indexed
                                    'endRowIndex': end_row,
                                    'startColumnIndex': 0,
                                    'endColumnIndex': 6
                                },
                                'cell': {
                                    'userEnteredFormat': {
                                        'backgroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
                                        'textFormat': {
                                            'foregroundColor': {'red': 0.0, 'green': 0.0, 'blue': 0.0},
                                            'bold': False
                                        }
                                    }
                                },
                                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                            }
                        },
                        {
                            'repeatCell': {
                                'range': {
                                    'sheetId': 0,
                                    'startRowIndex': start_row - 1,  # 0-indexed
                                    'endRowIndex': end_row,
                                    'startColumnIndex': 3,  # URL column
                                    'endColumnIndex': 4
                                },
                                'cell': {
                                    'userEnteredFormat': {
                                        'backgroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
                                        'textFormat': {
                                            'foregroundColor': {'red': 0.0, 'green': 0.0, 'blue': 1.0},
                                            'underline': True,
                                            'bold': False
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
            
            # Update article count
            if spreadsheet_id in self.sheets_data:
                self.sheets_data[spreadsheet_id]['articles_count'] += len(filtered_articles)
                self.sheets_data[spreadsheet_id]['last_updated'] = datetime.now().isoformat()
                self._save_sheets_data()
            
            print(f"Successfully saved {len(filtered_articles)} recent articles to spreadsheet for '{campaign_name}'")
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
    
    def get_spreadsheet_article_count(self, spreadsheet_id: str) -> int:
        """Get the actual number of articles (rows) in a spreadsheet"""
        sheets_service = self.get_sheets_service()
        if not sheets_service:
            return 0
        
        try:
            # Get all data from the spreadsheet
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='A:A'  # Get all rows in column A
            ).execute()
            
            values = result.get('values', [])
            # Subtract 1 for the header row
            article_count = max(0, len(values) - 1)
            
            return article_count
        except HttpError as e:
            print(f"Error getting spreadsheet article count: {e}")
            return 0
        except Exception as e:
            print(f"Error getting spreadsheet article count: {e}")
            return 0
    
    def get_spreadsheet_articles_today(self, spreadsheet_id: str) -> int:
        """Get the number of articles added today to a spreadsheet"""
        sheets_service = self.get_sheets_service()
        if not sheets_service:
            return 0
        
        try:
            # Get all data from the spreadsheet
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='A:A'  # Get all rows in column A (dates)
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:  # Only header or empty
                return 0
            
            today = datetime.now().date()
            articles_today = 0
            
            # Skip header row and check dates
            for row in values[1:]:
                if row and row[0]:  # If there's a date value
                    try:
                        # Parse article date
                        article_date = datetime.fromisoformat(row[0].replace('Z', '')).date()
                        if article_date == today:
                            articles_today += 1
                    except:
                        # Skip if date parsing fails
                        continue
            
            return articles_today
        except HttpError as e:
            print(f"Error getting today's articles count: {e}")
            return 0
        except Exception as e:
            print(f"Error getting today's articles count: {e}")
            return 0

    def is_google_sheets_connected(self) -> bool:
        """Check if Google Sheets is connected with valid credentials"""
        return self.credentials_manager.has_valid_credentials()
    
    def delete_spreadsheet(self, spreadsheet_id: str) -> bool:
        """Delete a spreadsheet"""
        drive_service = self.get_drive_service()
        if not drive_service:
            return False
        
        try:
            drive_service.files().delete(fileId=spreadsheet_id).execute()
            
            # Remove from local data
            if spreadsheet_id in self.sheets_data:
                del self.sheets_data[spreadsheet_id]
                self._save_sheets_data()
            
            return True
            
        except HttpError as e:
            print(f"Error deleting spreadsheet: {e}")
            return False
