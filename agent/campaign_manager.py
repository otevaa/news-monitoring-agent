import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

class CampaignManager:
    def __init__(self, data_file="campaigns.json"):
        self.data_file = data_file
        self.campaigns = self._load_campaigns()
    
    def _load_campaigns(self) -> List[Dict]:
        """Load campaigns from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
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
    
    def create_campaign(self, data: Dict) -> str:
        """Create a new campaign"""
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
        """Get a specific campaign"""
        for campaign in self.campaigns:
            if campaign['id'] == campaign_id:
                return campaign
        return None
    
    def get_all_campaigns(self) -> List[Dict]:
        """Get all campaigns"""
        return self.campaigns
    
    def get_active_campaigns(self) -> List[Dict]:
        """Get only active campaigns"""
        return [c for c in self.campaigns if c['status'] == 'active']
    
    def get_recent_campaigns(self, limit: int = 5) -> List[Dict]:
        """Get recent campaigns sorted by creation date"""
        sorted_campaigns = sorted(
            self.campaigns, 
            key=lambda x: x['created_at'], 
            reverse=True
        )
        return sorted_campaigns[:limit]
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a campaign"""
        for campaign in self.campaigns:
            if campaign['id'] == campaign_id:
                campaign['status'] = 'paused'
                campaign['updated_at'] = datetime.now().isoformat()
                self._save_campaigns()
                return True
        return False
    
    def resume_campaign(self, campaign_id: str) -> bool:
        """Resume a paused campaign"""
        for campaign in self.campaigns:
            if campaign['id'] == campaign_id:
                campaign['status'] = 'active'
                campaign['updated_at'] = datetime.now().isoformat()
                self._save_campaigns()
                return True
        return False
    
    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign"""
        for i, campaign in enumerate(self.campaigns):
            if campaign['id'] == campaign_id:
                del self.campaigns[i]
                self._save_campaigns()
                return True
        return False
    
    def update_campaign_stats(self, campaign_id: str, articles_count: int):
        """Update campaign statistics after fetching articles"""
        for campaign in self.campaigns:
            if campaign['id'] == campaign_id:
                campaign['total_articles'] = campaign.get('total_articles', 0) + articles_count
                campaign['last_check'] = datetime.now().isoformat()
                
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
        """Get total number of campaigns"""
        return len(self.campaigns)
    
    def get_total_articles_count(self) -> int:
        """Get total number of articles across all campaigns"""
        return sum(c.get('total_articles', 0) for c in self.campaigns)
    
    def get_articles_today_count(self) -> int:
        """Get total number of articles found today"""
        return sum(c.get('articles_today', 0) for c in self.campaigns)
    
    def get_campaigns_for_execution(self) -> List[Dict]:
        """Get campaigns that need to be executed based on their frequency"""
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
