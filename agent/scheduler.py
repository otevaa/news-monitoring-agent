from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging
from agent.campaign_manager import CampaignManager
from agent.integrations import IntegrationManager
from agent.fetch_rss import fetch_articles_rss

class CampaignScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.campaign_manager = CampaignManager()
        self.integration_manager = IntegrationManager()
        self.logger = logging.getLogger(__name__)
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        
    def start(self):
        """Start the scheduler"""
        # Run campaign checks every 5 minutes
        self.scheduler.add_job(
            func=self.check_and_run_campaigns,
            trigger=IntervalTrigger(minutes=5),
            id='campaign_checker',
            name='Check and run campaigns',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.logger.info("Campaign scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        self.logger.info("Campaign scheduler stopped")
    
    def check_and_run_campaigns(self):
        """Check which campaigns need to run and execute them"""
        try:
            campaigns_to_run = self.campaign_manager.get_campaigns_for_execution()
            
            for campaign in campaigns_to_run:
                self.logger.info(f"Running campaign: {campaign['name']}")
                self.run_campaign(campaign)
                
        except Exception as e:
            self.logger.error(f"Error checking campaigns: {e}")
    
    def run_campaign(self, campaign):
        """Run a single campaign"""
        try:
            # Fetch articles using the campaign keywords
            keywords = campaign['keywords']
            max_articles = campaign.get('max_articles', 25)
            
            articles = fetch_articles_rss(keywords, max_items=max_articles)
            
            if articles:
                # Send to configured integrations
                integrations = campaign.get('integrations', [])
                if integrations:
                    results = self.integration_manager.send_articles(
                        articles, 
                        integrations, 
                        campaign['name']
                    )
                    
                    success_count = sum(1 for success in results.values() if success)
                    self.logger.info(f"Campaign '{campaign['name']}': {len(articles)} articles sent to {success_count}/{len(integrations)} integrations")
                
                # Update campaign statistics
                self.campaign_manager.update_campaign_stats(
                    campaign['id'], 
                    len(articles)
                )
            else:
                self.logger.info(f"Campaign '{campaign['name']}': No articles found")
                # Still update last check time
                self.campaign_manager.update_campaign_stats(campaign['id'], 0)
                
        except Exception as e:
            self.logger.error(f"Error running campaign '{campaign['name']}': {e}")
    
    def run_campaign_now(self, campaign_id: str):
        """Manually trigger a campaign run"""
        campaign = self.campaign_manager.get_campaign(campaign_id)
        if campaign:
            self.run_campaign(campaign)
            return True
        return False

# Global scheduler instance
campaign_scheduler = CampaignScheduler()
