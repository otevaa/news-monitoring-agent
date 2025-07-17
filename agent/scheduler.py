from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging
from agent.campaign_manager import CampaignManager
from agent.integrations import IntegrationManager
from agent.google_sheets_manager import GoogleSheetsManager
from agent.fetch_rss import fetch_articles_rss

class CampaignScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.campaign_manager = CampaignManager()
        self.integration_manager = IntegrationManager()
        self.sheets_manager = GoogleSheetsManager()
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
                success_count = 0
                
                for integration in integrations:
                    if integration == 'google_sheets':
                        # Use GoogleSheetsManager to save articles
                        if self.sheets_manager.is_google_sheets_connected():
                            spreadsheet_id = campaign.get('spreadsheet_id')
                            if spreadsheet_id:
                                success = self.sheets_manager.save_articles_to_spreadsheet(
                                    spreadsheet_id,
                                    articles,
                                    campaign['name'],
                                    keywords
                                )
                                if success:
                                    success_count += 1
                                    self.logger.info(f"Successfully saved {len(articles)} articles to Google Sheets for campaign '{campaign['name']}'")
                                else:
                                    self.logger.error(f"Failed to save articles to Google Sheets for campaign '{campaign['name']}'")
                            else:
                                self.logger.warning(f"Campaign '{campaign['name']}' has Google Sheets integration but no spreadsheet_id")
                        else:
                            self.logger.warning("Google Sheets not connected - skipping Google Sheets integration")
                    elif integration == 'airtable':
                        # Keep existing airtable logic
                        success = self.integration_manager.send_to_airtable(articles, campaign['name'])
                        if success:
                            success_count += 1
                
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
            import traceback
            traceback.print_exc()
    
    def run_campaign_now(self, campaign_id: str):
        """Manually trigger a campaign run"""
        campaign = self.campaign_manager.get_campaign(campaign_id)
        if campaign:
            self.run_campaign(campaign)
            return True
        return False

# Global scheduler instance
campaign_scheduler = CampaignScheduler()
