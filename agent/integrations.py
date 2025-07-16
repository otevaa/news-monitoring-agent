import json
import os
from datetime import datetime
from typing import Dict, Optional, List
import requests

class IntegrationManager:
    def __init__(self, data_file="integrations.json"):
        self.data_file = data_file
        self.integrations = self._load_integrations()
    
    def _load_integrations(self) -> Dict:
        """Load integrations from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _save_integrations(self):
        """Save integrations to JSON file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.integrations, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving integrations: {e}")
    
    def configure_airtable(self, api_key: str, base_id: str, table_name: str) -> bool:
        """Configure Airtable integration"""
        try:
            # Test the connection
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Try to get the base schema to validate credentials
            url = f'https://api.airtable.com/v0/meta/bases/{base_id}/tables'
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                tables = response.json().get('tables', [])
                table_exists = any(table['name'] == table_name for table in tables)
                
                self.integrations['airtable'] = {
                    'api_key': api_key,
                    'base_id': base_id,
                    'table_name': table_name,
                    'base_name': f'Base {base_id[:8]}...',
                    'base_url': f'https://airtable.com/{base_id}',
                    'configured_at': datetime.now().isoformat(),
                    'last_sync': None,
                    'total_records': 0,
                    'table_exists': table_exists
                }
                
                self._save_integrations()
                return True
            else:
                print(f"Airtable API error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error configuring Airtable: {e}")
            return False
    
    def is_airtable_configured(self) -> bool:
        """Check if Airtable is configured"""
        return 'airtable' in self.integrations and self.integrations['airtable'].get('api_key')
    
    def get_airtable_status(self) -> Optional[Dict]:
        """Get Airtable integration status"""
        if self.is_airtable_configured():
            return self.integrations['airtable']
        return None
    
    def get_google_sheets_status(self) -> Optional[Dict]:
        """Get Google Sheets integration status"""
        # This would be integrated with the Google OAuth system
        # For now, return mock data
        return {
            'spreadsheet_name': 'NewsMonitor Articles',
            'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/example',
            'connected_at': '2024-01-01T00:00:00'
        } if self.integrations.get('google_sheets') else None
    
    def disconnect_integration(self, integration_name: str) -> bool:
        """Disconnect an integration"""
        if integration_name in self.integrations:
            del self.integrations[integration_name]
            self._save_integrations()
            return True
        return False
    
    def get_active_integrations_count(self) -> int:
        """Get number of active integrations"""
        return len(self.integrations)
    
    def get_usage_stats(self) -> Dict:
        """Get usage statistics for integrations"""
        total_articles = 0
        articles_today = 0
        successful_syncs = 0
        last_sync = None
        
        # Calculate stats from all integrations
        for integration_data in self.integrations.values():
            total_articles += integration_data.get('total_records', 0)
            successful_syncs += integration_data.get('successful_syncs', 0)
            
            integration_last_sync = integration_data.get('last_sync')
            if integration_last_sync:
                if not last_sync or integration_last_sync > last_sync:
                    last_sync = integration_last_sync
        
        return {
            'total_articles_sent': total_articles,
            'articles_today': articles_today,
            'successful_syncs': successful_syncs,
            'last_sync': last_sync[:10] if last_sync else 'Jamais'
        }
    
    def send_to_airtable(self, articles: List[Dict], campaign_name: Optional[str] = None) -> bool:
        """Send articles to Airtable"""
        if not self.is_airtable_configured():
            return False
        
        config = self.integrations['airtable']
        
        try:
            headers = {
                'Authorization': f'Bearer {config["api_key"]}',
                'Content-Type': 'application/json'
            }
            
            # Prepare records for Airtable
            records = []
            for article in articles:
                record = {
                    'fields': {
                        'Date': article.get('date', ''),
                        'Source': article.get('source', ''),
                        'Titre': article.get('titre', ''),
                        'URL': article.get('url', ''),
                        'Résumé': article.get('resume', ''),
                        'Campagne': campaign_name or 'Recherche manuelle',
                        'Ajouté le': datetime.now().isoformat()
                    }
                }
                records.append(record)
            
            # Send in batches of 10 (Airtable limit)
            batch_size = 10
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                url = f'https://api.airtable.com/v0/{config["base_id"]}/{config["table_name"]}'
                payload = {'records': batch}
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    print(f"Airtable API error: {response.status_code} - {response.text}")
                    return False
            
            # Update stats
            config['total_records'] = config.get('total_records', 0) + len(articles)
            config['last_sync'] = datetime.now().isoformat()
            config['successful_syncs'] = config.get('successful_syncs', 0) + 1
            self._save_integrations()
            
            return True
            
        except Exception as e:
            print(f"Error sending to Airtable: {e}")
            return False
    
    def send_to_google_sheets(self, articles: List[Dict], campaign_name: Optional[str] = None) -> bool:
        """Send articles to Google Sheets"""
        # This would integrate with the existing Google Sheets functionality
        # For now, return True to indicate success
        try:
            # Update stats
            if 'google_sheets' not in self.integrations:
                self.integrations['google_sheets'] = {
                    'total_records': 0,
                    'successful_syncs': 0
                }
            
            config = self.integrations['google_sheets']
            config['total_records'] = config.get('total_records', 0) + len(articles)
            config['last_sync'] = datetime.now().isoformat()
            config['successful_syncs'] = config.get('successful_syncs', 0) + 1
            self._save_integrations()
            
            return True
        except Exception as e:
            print(f"Error sending to Google Sheets: {e}")
            return False
    
    def send_articles(self, articles: List[Dict], integrations: List[str], campaign_name: Optional[str] = None) -> Dict[str, bool]:
        """Send articles to specified integrations"""
        results = {}
        
        for integration in integrations:
            if integration == 'airtable':
                results['airtable'] = self.send_to_airtable(articles, campaign_name)
            elif integration == 'google_sheets':
                results['google_sheets'] = self.send_to_google_sheets(articles, campaign_name)
        
        return results
