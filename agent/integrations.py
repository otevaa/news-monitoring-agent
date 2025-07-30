"""
Integration Manager - Database-based integration management
"""
from datetime import datetime
from typing import Dict, Optional, List
import requests
from database.managers import get_integration_manager


class IntegrationManager:
    """Wrapper class for database-based integration management"""
    
    def __init__(self):
        self.db_integration_manager = get_integration_manager()
    
    def configure_airtable(self, user_id: str, api_key: str, base_id: str, table_name: str) -> bool:
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
                
                config = {
                    'api_key': api_key,
                    'base_id': base_id,
                    'table_name': table_name,
                    'base_name': f'Base {base_id[:8]}...',
                    'base_url': f'https://airtable.com/{base_id}',
                    'table_exists': table_exists
                }
                
                return self.db_integration_manager.connect_integration(
                    user_id, 'airtable', config, True
                )
            else:
                print(f"Airtable API error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error configuring Airtable: {e}")
            return False
    
    def is_airtable_configured(self, user_id: str) -> bool:
        """Check if Airtable is configured"""
        integration = self.db_integration_manager.get_integration(user_id, 'airtable')
        return integration is not None and integration.get('is_active', False)
    
    def get_airtable_status(self, user_id: str) -> Optional[Dict]:
        """Get Airtable integration status"""
        integration = self.db_integration_manager.get_integration(user_id, 'airtable')
        if integration and integration.get('is_active'):
            config = integration.get('config', {})
            return {
                'api_key': config.get('api_key'),
                'base_id': config.get('base_id'),
                'table_name': config.get('table_name'),
                'base_name': config.get('base_name'),
                'base_url': config.get('base_url'),
                'configured_at': integration.get('created_at'),
                'last_sync': integration.get('updated_at'),
                'total_records': config.get('total_records', 0),
                'table_exists': config.get('table_exists', False)
            }
        return None
    
    def get_google_sheets_status(self, user_id: str) -> Optional[Dict]:
        """Get Google Sheets integration status"""
        integration = self.db_integration_manager.get_integration(user_id, 'google_sheets')
        if integration and integration.get('is_active'):
            config = integration.get('config', {})
            return {
                'connected': True,
                'connected_at': integration.get('created_at'),
                'total_records': config.get('total_records', 0),
                'successful_syncs': config.get('successful_syncs', 0),
                'last_sync': integration.get('updated_at')
            }
        return None
    
    def disconnect_integration(self, user_id: str, integration_name: str) -> bool:
        """Disconnect an integration"""
        return self.db_integration_manager.disconnect_integration(user_id, integration_name)
    
    def get_active_integrations_count(self, user_id: str) -> int:
        """Get number of active integrations"""
        integrations = self.db_integration_manager.get_user_integrations(user_id)
        return len([i for i in integrations if i.get('is_active', False)])
    
    def update_google_sheets_status(self, user_id: str, connected: bool):
        """Update Google Sheets connection status"""
        if connected:
            config = {'connected': True}
            self.db_integration_manager.connect_integration(
                user_id, 'google_sheets', config, True
            )
        else:
            self.db_integration_manager.disconnect_integration(user_id, 'google_sheets')
    
    def get_usage_stats(self, user_id: str) -> Dict:
        """Get usage statistics for integrations"""
        integrations = self.db_integration_manager.get_user_integrations(user_id)
        
        total_articles = 0
        articles_today = 0
        successful_syncs = 0
        last_sync = None
        
        # Calculate stats from all integrations
        for integration in integrations:
            if integration.get('is_active'):
                config = integration.get('config', {})
                total_articles += config.get('total_records', 0)
                successful_syncs += config.get('successful_syncs', 0)
                
                integration_last_sync = integration.get('updated_at')
                if integration_last_sync:
                    if not last_sync or integration_last_sync > last_sync:
                        last_sync = integration_last_sync
        
        return {
            'total_articles_sent': total_articles,
            'articles_today': articles_today,
            'successful_syncs': successful_syncs,
            'last_sync': last_sync[:10] if last_sync else 'Jamais'
        }
    
    def send_to_airtable(self, user_id: str, articles: List[Dict], campaign_name: Optional[str] = None) -> bool:
        """Send articles to Airtable"""
        integration = self.db_integration_manager.get_integration(user_id, 'airtable')
        if not integration or not integration.get('is_active'):
            return False
        
        config = integration.get('config', {})
        
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
            config['successful_syncs'] = config.get('successful_syncs', 0) + 1
            
            self.db_integration_manager.connect_integration(
                user_id, 'airtable', config, True
            )
            
            return True
            
        except Exception as e:
            print(f"Error sending to Airtable: {e}")
            return False
    
    def send_to_google_sheets(self, user_id: str, articles: List[Dict], campaign_name: Optional[str] = None) -> bool:
        """Send articles to Google Sheets"""
        try:
            integration = self.db_integration_manager.get_integration(user_id, 'google_sheets')
            if not integration:
                # Create initial integration
                config = {'total_records': 0, 'successful_syncs': 0}
                self.db_integration_manager.connect_integration(
                    user_id, 'google_sheets', config, True
                )
            else:
                config = integration.get('config', {})
            
            # Update stats
            config['total_records'] = config.get('total_records', 0) + len(articles)
            config['successful_syncs'] = config.get('successful_syncs', 0) + 1
            
            self.db_integration_manager.connect_integration(
                user_id, 'google_sheets', config, True
            )
            
            return True
        except Exception as e:
            print(f"Error sending to Google Sheets: {e}")
            return False
    
    def send_articles(self, user_id: str, articles: List[Dict], integrations: List[str], campaign_name: Optional[str] = None) -> Dict[str, bool]:
        """Send articles to specified integrations"""
        results = {}
        
        for integration in integrations:
            if integration == 'airtable':
                results['airtable'] = self.send_to_airtable(user_id, articles, campaign_name)
            elif integration == 'google_sheets':
                results['google_sheets'] = self.send_to_google_sheets(user_id, articles, campaign_name)
        
        return results
