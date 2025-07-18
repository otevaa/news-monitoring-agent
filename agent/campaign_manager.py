import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
from .google_sheets_manager import GoogleSheetsManager

class CampaignManager:
    def __init__(self, data_file="campaigns.json"):
        self.data_file = data_file
        self.campaigns = self._load_campaigns()
    
    def _load_campaigns(self) -> List[Dict]:
        """Load campaigns from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Ensure we return a list, not a dict
                    if isinstance(data, dict):
                        return []  # Convert empty dict to empty list
                    return data if isinstance(data, list) else []
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []
    
    def _save_campaigns(self):
        """Save campaigns to JSON file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.campaigns, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving campaigns: {e}")
    
    def _update_campaign_stats(self, campaign: Dict) -> Dict:
        """Update campaign statistics with actual spreadsheet data"""
        if campaign.get('spreadsheet_id'):
            try:
                sheets_manager = GoogleSheetsManager()
                
                # Get actual article counts from spreadsheet
                total_articles = sheets_manager.get_spreadsheet_article_count(campaign['spreadsheet_id'])
                articles_today = sheets_manager.get_spreadsheet_articles_today(campaign['spreadsheet_id'])
                
                # Update campaign stats
                campaign['total_articles'] = total_articles
                campaign['articles_today'] = articles_today
                
            except Exception as e:
                print(f"Error updating campaign stats for {campaign['name']}: {e}")
                # Keep existing stats if error occurs
                pass
        
        return campaign
    
    def create_campaign(self, data: Dict) -> str:
        """Create a new campaign"""
        self.campaigns = self._load_campaigns()  # Reload from file for fresh data
        campaign_id = str(uuid.uuid4())
        campaign = {
            'id': campaign_id,
            'name': data['name'],
            'keywords': data['keywords'],
            'frequency': data['frequency'],
            'integrations': data.get('integrations', []),
            'max_articles': data.get('max_articles', 25),
            'description': data.get('description', ''),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'total_articles': 0,
            'articles_today': 0,
            'last_check': None
        }
        
        self.campaigns.append(campaign)
        self._save_campaigns()
        return campaign_id
    
    def update_campaign(self, campaign_id: str, data: Dict) -> bool:
        """Update an existing campaign"""
        self.campaigns = self._load_campaigns()  # Reload from file for fresh data
        for campaign in self.campaigns:
            if campaign['id'] == campaign_id:
                campaign.update({
                    'name': data['name'],
                    'keywords': data['keywords'],
                    'frequency': data['frequency'],
                    'integrations': data.get('integrations', []),
                    'max_articles': data.get('max_articles', 25),
                    'description': data.get('description', ''),
                    'updated_at': datetime.now().isoformat()
                })
                self._save_campaigns()
                return True
        return False
    
    def get_campaign(self, campaign_id: str) -> Optional[Dict]:
        """Get a specific campaign - always reload from file for fresh data"""
        self.campaigns = self._load_campaigns()  # Reload from file
        for campaign in self.campaigns:
            if campaign['id'] == campaign_id:
                return self._update_campaign_stats(campaign)
        return None
    
    def get_all_campaigns(self) -> List[Dict]:
        """Get all campaigns - always reload from file for fresh data"""
        self.campaigns = self._load_campaigns()  # Reload from file
        return [self._update_campaign_stats(campaign) for campaign in self.campaigns]
    
    def get_active_campaigns(self) -> List[Dict]:
        """Get only active campaigns - always reload from file for fresh data"""
        self.campaigns = self._load_campaigns()  # Reload from file
        active_campaigns = [c for c in self.campaigns if c['status'] == 'active']
        return [self._update_campaign_stats(campaign) for campaign in active_campaigns]
    
    def get_recent_campaigns(self, limit: int = 5) -> List[Dict]:
        """Get recent campaigns sorted by creation date - always reload from file for fresh data"""
        self.campaigns = self._load_campaigns()  # Reload from file
        sorted_campaigns = sorted(
            self.campaigns, 
            key=lambda x: x['created_at'], 
            reverse=True
        )
        limited_campaigns = sorted_campaigns[:limit]
        return [self._update_campaign_stats(campaign) for campaign in limited_campaigns]
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a campaign"""
        self.campaigns = self._load_campaigns()  # Reload from file for fresh data
        for campaign in self.campaigns:
            if campaign['id'] == campaign_id:
                campaign['status'] = 'paused'
                campaign['updated_at'] = datetime.now().isoformat()
                self._save_campaigns()
                return True
        return False
    
    def resume_campaign(self, campaign_id: str) -> bool:
        """Resume a paused campaign"""
        self.campaigns = self._load_campaigns()  # Reload from file for fresh data
        for campaign in self.campaigns:
            if campaign['id'] == campaign_id:
                campaign['status'] = 'active'
                campaign['updated_at'] = datetime.now().isoformat()
                self._save_campaigns()
                return True
        return False
    
    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign"""
        self.campaigns = self._load_campaigns()  # Reload from file for fresh data
        for i, campaign in enumerate(self.campaigns):
            if campaign['id'] == campaign_id:
                del self.campaigns[i]
                self._save_campaigns()
                return True
        return False
    
    def update_campaign_stats(self, campaign_id: str, articles_count: int, success_count: int = 0):
        """Update campaign statistics after fetching articles"""
        self.campaigns = self._load_campaigns()  # Reload from file for fresh data
        for campaign in self.campaigns:
            if campaign['id'] == campaign_id:
                campaign['total_articles'] = campaign.get('total_articles', 0) + articles_count
                campaign['last_check'] = datetime.now().isoformat()
                campaign['last_execution'] = datetime.now().isoformat()
                
                # Update today's count if it's the same day
                today = datetime.now().date()
                last_check_date = None
                if campaign.get('last_articles_date'):
                    last_check_date = datetime.fromisoformat(campaign['last_articles_date']).date()
                
                if last_check_date == today:
                    campaign['articles_today'] = campaign.get('articles_today', 0) + articles_count
                else:
                    campaign['articles_today'] = articles_count
                    campaign['last_articles_date'] = datetime.now().isoformat()
                
                self._save_campaigns()
                break
    
    def get_total_campaigns_count(self) -> int:
        """Get total number of campaigns - always reload from file for fresh data"""
        self.campaigns = self._load_campaigns()  # Reload from file
        return len(self.campaigns)
    
    def get_total_articles_count(self) -> int:
        """Get total number of articles across all campaigns - always reload from file for fresh data"""
        self.campaigns = self._load_campaigns()  # Reload from file
        return sum(c.get('total_articles', 0) for c in self.campaigns)
    
    def get_articles_today_count(self) -> int:
        """Get total number of articles found today - always reload from file for fresh data"""
        self.campaigns = self._load_campaigns()  # Reload from file
        return sum(c.get('articles_today', 0) for c in self.campaigns)
    
    def get_campaigns_for_execution(self) -> List[Dict]:
        """Get campaigns that need to be executed based on their frequency - always reload from file for fresh data"""
        self.campaigns = self._load_campaigns()  # Reload from file
        active_campaigns = self.get_active_campaigns()
        campaigns_to_run = []
        
        now = datetime.now()
        
        for campaign in active_campaigns:
            last_check = campaign.get('last_check')
            frequency = campaign.get('frequency', 'daily')
            
            if not last_check:
                # Never run before, add to execution list
                campaigns_to_run.append(campaign)
                continue
                
            last_check_dt = datetime.fromisoformat(last_check)
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
                campaigns_to_run.append(campaign)
        
        return campaigns_to_run
