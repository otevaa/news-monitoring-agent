"""
Database-based Campaign Manager
"""
from typing import List, Dict, Optional
import json
from datetime import datetime
from database.models import DatabaseManager
import uuid


class DatabaseCampaignManager:
    """Database-based campaign manager replacing JSON file storage"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_campaign(self, user_id: str, data: Dict) -> Optional[str]:
        """Create a new campaign for a user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            campaign_id = str(uuid.uuid4())
            
            cursor.execute('''
                INSERT INTO campaigns 
                (id, user_id, name, description, keywords, frequency, max_articles, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                campaign_id,
                user_id,
                data['name'],
                data.get('description', ''),
                data['keywords'],
                data['frequency'],
                data.get('max_articles', 25),
                'active'
            ))
            
            # Add integrations
            integrations = data.get('integrations', [])
            for integration_type in integrations:
                integration_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO campaign_integrations 
                    (id, campaign_id, integration_type, is_active)
                    VALUES (?, ?, ?, 1)
                ''', (integration_id, campaign_id, integration_type))
            
            conn.commit()
            conn.close()
            
            return campaign_id
        except Exception as e:
            print(f"Error creating campaign: {e}")
            return None
    
    def get_campaign(self, campaign_id: str, user_id: str) -> Optional[Dict]:
        """Get a specific campaign for a user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM campaigns 
                WHERE id = ? AND user_id = ?
            ''', (campaign_id, user_id))
            
            campaign = cursor.fetchone()
            if not campaign:
                return None
            
            campaign_dict = dict(campaign)
            
            # Get integrations
            cursor.execute('''
                SELECT integration_type FROM campaign_integrations 
                WHERE campaign_id = ? AND is_active = 1
            ''', (campaign_id,))
            
            integrations = [row['integration_type'] for row in cursor.fetchall()]
            campaign_dict['integrations'] = integrations
            
            conn.close()
            return campaign_dict
        except Exception as e:
            print(f"Error getting campaign: {e}")
            return None
    
    def get_user_campaigns(self, user_id: str) -> List[Dict]:
        """Get all campaigns for a user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM campaigns 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
            
            campaigns = []
            for row in cursor.fetchall():
                campaign_dict = dict(row)
                
                # Get integrations for this campaign
                cursor.execute('''
                    SELECT integration_type FROM campaign_integrations 
                    WHERE campaign_id = ? AND is_active = 1
                ''', (campaign_dict['id'],))
                
                integrations = [int_row['integration_type'] for int_row in cursor.fetchall()]
                campaign_dict['integrations'] = integrations
                
                campaigns.append(campaign_dict)
            
            conn.close()
            return campaigns
        except Exception as e:
            print(f"Error getting user campaigns: {e}")
            return []
    
    def get_active_campaigns(self, user_id: str) -> List[Dict]:
        """Get active campaigns for a user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM campaigns 
                WHERE user_id = ? AND status = 'active'
                ORDER BY created_at DESC
            ''', (user_id,))
            
            campaigns = []
            for row in cursor.fetchall():
                campaign_dict = dict(row)
                
                # Get integrations for this campaign
                cursor.execute('''
                    SELECT integration_type FROM campaign_integrations 
                    WHERE campaign_id = ? AND is_active = 1
                ''', (campaign_dict['id'],))
                
                integrations = [int_row['integration_type'] for int_row in cursor.fetchall()]
                campaign_dict['integrations'] = integrations
                
                campaigns.append(campaign_dict)
            
            conn.close()
            return campaigns
        except Exception as e:
            print(f"Error getting active campaigns: {e}")
            return []
    
    def update_campaign(self, campaign_id: str, user_id: str, data: Dict) -> bool:
        """Update a campaign"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE campaigns 
                SET name = ?, description = ?, keywords = ?, frequency = ?, 
                    max_articles = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (
                data['name'],
                data.get('description', ''),
                data['keywords'],
                data['frequency'],
                data.get('max_articles', 25),
                campaign_id,
                user_id
            ))
            
            if cursor.rowcount == 0:
                return False
            
            # Update integrations - remove old ones and add new ones
            cursor.execute('''
                UPDATE campaign_integrations 
                SET is_active = 0 
                WHERE campaign_id = ?
            ''', (campaign_id,))
            
            # Add new integrations
            integrations = data.get('integrations', [])
            for integration_type in integrations:
                integration_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO campaign_integrations 
                    (id, campaign_id, integration_type, is_active)
                    VALUES (?, ?, ?, 1)
                ''', (integration_id, campaign_id, integration_type))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error updating campaign: {e}")
            return False
    
    def delete_campaign(self, campaign_id: str, user_id: str, remove_sheet: bool = False, google_sheets_manager=None) -> bool:
        """Delete a campaign, optionally removing associated Google Sheet from Google Drive"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            # Get spreadsheet_id if exists
            cursor.execute('''
                SELECT spreadsheet_id FROM campaigns WHERE id = ? AND user_id = ?
            ''', (campaign_id, user_id))
            row = cursor.fetchone()
            spreadsheet_id = row['spreadsheet_id'] if row and 'spreadsheet_id' in row else None
            # Delete campaign
            cursor.execute('''
                DELETE FROM campaigns 
                WHERE id = ? AND user_id = ?
            ''', (campaign_id, user_id))
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            # Remove Google Sheet if requested
            if remove_sheet and spreadsheet_id and google_sheets_manager:
                try:
                    google_sheets_manager.delete_sheet(spreadsheet_id)
                except Exception as e:
                    print(f"Error deleting Google Sheet: {e}")
            return success
        except Exception as e:
            print(f"Error deleting campaign: {e}")
            return False
    
    def delete_campaigns(self, campaign_ids: List[str], user_id: str, remove_sheets: bool = False, google_sheets_manager=None) -> int:
        """Delete multiple campaigns, optionally removing associated Google Sheets. Returns count of deleted campaigns."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            deleted_count = 0
            for campaign_id in campaign_ids:
                # Get spreadsheet_id if exists
                cursor.execute('''
                    SELECT spreadsheet_id FROM campaigns WHERE id = ? AND user_id = ?
                ''', (campaign_id, user_id))
                row = cursor.fetchone()
                spreadsheet_id = row['spreadsheet_id'] if row and 'spreadsheet_id' in row else None
                # Delete campaign
                cursor.execute('''
                    DELETE FROM campaigns 
                    WHERE id = ? AND user_id = ?
                ''', (campaign_id, user_id))
                if cursor.rowcount > 0:
                    deleted_count += 1
                    # Remove Google Sheet if requested
                    if remove_sheets and spreadsheet_id and google_sheets_manager:
                        try:
                            google_sheets_manager.delete_sheet(spreadsheet_id)
                        except Exception as e:
                            print(f"Error deleting Google Sheet: {e}")
            conn.commit()
            conn.close()
            return deleted_count
        except Exception as e:
            print(f"Error deleting campaigns: {e}")
            return 0
    
    def pause_campaign(self, campaign_id: str, user_id: str) -> bool:
        """Pause a campaign"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE campaigns 
                SET status = 'paused', updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (campaign_id, user_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
        except Exception as e:
            print(f"Error pausing campaign: {e}")
            return False
    
    def resume_campaign(self, campaign_id: str, user_id: str) -> bool:
        """Resume a paused campaign"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE campaigns 
                SET status = 'active', updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (campaign_id, user_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
        except Exception as e:
            print(f"Error resuming campaign: {e}")
            return False
    
    def update_campaign_stats(self, campaign_id: str, user_id: str, articles_count: int):
        """Update campaign statistics after fetching articles"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get current stats
            cursor.execute('''
                SELECT total_articles, articles_today, last_articles_date 
                FROM campaigns 
                WHERE id = ? AND user_id = ?
            ''', (campaign_id, user_id))
            
            campaign = cursor.fetchone()
            if not campaign:
                return
            
            new_total = (campaign['total_articles'] or 0) + articles_count
            
            # Check if it's a new day
            today = datetime.now().date()
            last_articles_date = None
            if campaign['last_articles_date']:
                last_articles_date = datetime.fromisoformat(campaign['last_articles_date']).date()
            
            if last_articles_date == today:
                new_articles_today = (campaign['articles_today'] or 0) + articles_count
            else:
                new_articles_today = articles_count
            
            cursor.execute('''
                UPDATE campaigns 
                SET total_articles = ?, articles_today = ?, 
                    last_check = CURRENT_TIMESTAMP, last_articles_date = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (new_total, new_articles_today, campaign_id, user_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating campaign stats: {e}")
    
    def update_campaign_spreadsheet(self, campaign_id: str, user_id: str, spreadsheet_id: str, spreadsheet_url: str):
        """Update campaign with Google Sheets information"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE campaigns 
                SET spreadsheet_id = ?, spreadsheet_url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (spreadsheet_id, spreadsheet_url, campaign_id, user_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
        except Exception as e:
            print(f"Error updating campaign spreadsheet: {e}")
            return False
    
    def get_campaigns_for_execution(self) -> List[Dict]:
        """Get campaigns that need to be executed based on their frequency across all users"""
        from datetime import datetime, timedelta
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM campaigns 
                WHERE status = 'active'
                ORDER BY created_at DESC
            ''')
            
            campaigns_to_run = []
            now = datetime.now()
            
            for row in cursor.fetchall():
                campaign_dict = dict(row)
                
                # Get integrations for this campaign
                cursor.execute('''
                    SELECT integration_type FROM campaign_integrations 
                    WHERE campaign_id = ? AND is_active = 1
                ''', (campaign_dict['id'],))
                
                integrations = [int_row['integration_type'] for int_row in cursor.fetchall()]
                campaign_dict['integrations'] = integrations
                
                # Check if campaign should run based on frequency
                last_check = campaign_dict.get('last_check')
                frequency = campaign_dict.get('frequency', 'daily')
                
                if not last_check:
                    # Never run before, add to execution list
                    campaigns_to_run.append(campaign_dict)
                    continue
                
                # Parse last_check datetime
                if isinstance(last_check, str):
                    last_check_dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                else:
                    last_check_dt = last_check
                    
                time_diff = now - last_check_dt
                
                # Check if enough time has passed based on frequency
                should_run = False
                if frequency == '15min' and time_diff >= timedelta(minutes=15):
                    should_run = True
                elif frequency == 'hourly' and time_diff >= timedelta(hours=1):
                    should_run = True
                elif frequency == 'daily' and time_diff >= timedelta(days=1):
                    should_run = True
                elif frequency == 'weekly' and time_diff >= timedelta(weeks=1):
                    should_run = True
                
                if should_run:
                    campaigns_to_run.append(campaign_dict)
            
            conn.close()
            return campaigns_to_run
        except Exception as e:
            print(f"Error getting campaigns for execution: {e}")
            return []

    def get_user_stats(self, user_id: str) -> Dict:
        """Get statistics for a user's campaigns"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_campaigns,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_campaigns,
                    COALESCE(SUM(total_articles), 0) as total_articles,
                    COALESCE(SUM(articles_today), 0) as articles_today
                FROM campaigns 
                WHERE user_id = ?
            ''', (user_id,))
            
            stats = cursor.fetchone()
            conn.close()
            
            return dict(stats) if stats else {
                'total_campaigns': 0,
                'active_campaigns': 0,
                'total_articles': 0,
                'articles_today': 0
            }
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {
                'total_campaigns': 0,
                'active_campaigns': 0,
                'total_articles': 0,
                'articles_today': 0
            }


class DatabaseUserProfileManager:
    """Database-based user profile manager"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_user_profile(self, user_id: str) -> Dict:
        """Get user profile with AI settings"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM user_profiles 
                WHERE user_id = ?
            ''', (user_id,))
            
            profile = cursor.fetchone()
            conn.close()
            
            if profile:
                return dict(profile)
            else:
                # Create default profile if doesn't exist
                return self.create_default_profile(user_id)
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return self.get_default_profile()
    
    def create_default_profile(self, user_id: str) -> Dict:
        """Create default profile for user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            profile_id = str(uuid.uuid4())
            default_profile = {
                'id': profile_id,
                'user_id': user_id,
                'ai_model': 'openai-gpt3.5',
                'ai_filtering_enabled': 1,
                'keyword_expansion_enabled': 1,  # Always enabled by default
                'priority_alerts_enabled': 1,
                'language': 'fr',
                'timezone': 'Europe/Paris'
            }
            
            cursor.execute('''
                INSERT INTO user_profiles 
                (id, user_id, ai_model, ai_filtering_enabled, keyword_expansion_enabled, 
                 priority_alerts_enabled, language, timezone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile_id, user_id, default_profile['ai_model'],
                default_profile['ai_filtering_enabled'],
                default_profile['keyword_expansion_enabled'],
                default_profile['priority_alerts_enabled'],
                default_profile['language'], default_profile['timezone']
            ))
            
            conn.commit()
            conn.close()
            
            return default_profile
        except Exception as e:
            print(f"Error creating default profile: {e}")
            return self.get_default_profile()
    
    def get_default_profile(self) -> Dict:
        """Get default profile settings"""
        return {
            'ai_model': 'openai-gpt3.5',
            'ai_filtering_enabled': True,
            'keyword_expansion_enabled': True,  # Always enabled
            'priority_alerts_enabled': True,
            'language': 'fr',
            'timezone': 'Europe/Paris'
        }
    
    def update_user_profile(self, user_id: str, updates: Dict) -> bool:
        """Update user profile"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Build dynamic update query
            set_clauses = []
            values = []
            
            allowed_fields = ['ai_model', 'ai_filtering_enabled', 'priority_alerts_enabled', 'language', 'timezone']
            # Note: keyword_expansion_enabled is not in allowed_fields as it's always enabled
            
            for field, value in updates.items():
                if field in allowed_fields:
                    set_clauses.append(f"{field} = ?")
                    # Convert boolean to integer for SQLite
                    if isinstance(value, bool):
                        values.append(1 if value else 0)
                    else:
                        values.append(value)
            
            if not set_clauses:
                return False
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(user_id)
            
            query = f"UPDATE user_profiles SET {', '.join(set_clauses)} WHERE user_id = ?"
            cursor.execute(query, values)
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return False


class DatabaseIntegrationManager:
    """Database-based integration manager"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_user_integrations(self, user_id: str) -> List[Dict]:
        """Get all integrations for a user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM user_integrations 
                WHERE user_id = ? AND is_active = 1
                ORDER BY created_at DESC
            ''', (user_id,))
            
            integrations = []
            for row in cursor.fetchall():
                integration_dict = dict(row)
                # Parse config JSON if present
                if integration_dict['integration_config']:
                    try:
                        integration_dict['config'] = json.loads(integration_dict['integration_config'])
                    except json.JSONDecodeError:
                        integration_dict['config'] = {}
                else:
                    integration_dict['config'] = {}
                integrations.append(integration_dict)
            
            conn.close()
            return integrations
        except Exception as e:
            print(f"Error getting user integrations: {e}")
            return []
    
    def is_google_sheets_connected(self, user_id: str) -> bool:
        """Check if user has Google Sheets integration"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as count FROM user_integrations 
                WHERE user_id = ? AND integration_type = 'google_sheets' AND is_active = 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result['count'] > 0
        except Exception as e:
            print(f"Error checking Google Sheets connection: {e}")
            return False
    
    def update_integration(self, user_id: str, integration_type: str, config: Dict, is_active: bool = True) -> bool:
        """Update or create integration for user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if integration exists
            cursor.execute('''
                SELECT id FROM user_integrations 
                WHERE user_id = ? AND integration_type = ?
            ''', (user_id, integration_type))
            
            existing = cursor.fetchone()
            config_json = json.dumps(config)
            
            if existing:
                # Update existing
                cursor.execute('''
                    UPDATE user_integrations 
                    SET integration_config = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP,
                        last_sync = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (config_json, 1 if is_active else 0, existing['id']))
            else:
                # Create new
                integration_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO user_integrations 
                    (id, user_id, integration_type, integration_config, is_active, last_sync)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (integration_id, user_id, integration_type, config_json, 1 if is_active else 0))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error updating integration: {e}")
            return False
    
    def disconnect_integration(self, user_id: str, integration_type: str) -> bool:
        """Disconnect an integration for user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_integrations 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND integration_type = ?
            ''', (user_id, integration_type))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
        except Exception as e:
            print(f"Error disconnecting integration: {e}")
            return False
