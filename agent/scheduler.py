from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging
from agent.campaign_manager import CampaignManager
from agent.integrations import IntegrationManager
from agent.google_sheets_manager import GoogleSheetsManager
from agent.fetch_multi_source import fetch_articles_rss
from agent.fetch_multi_source import fetch_articles_multi_source

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
        """Run a single campaign with AI enhancements"""
        try:
            self.logger.info(f"🚀 Starting campaign: {campaign['name']}")
            
            # Get campaign settings
            keywords = campaign.get('keywords', '')
            max_articles = campaign.get('max_articles', 25)
            
            self.logger.info(f"🔍 Searching with keywords: {keywords}")
            
            # Fetch articles with AI keyword expansion handled automatically
            articles = fetch_articles_multi_source(
                keywords, 
                max_items=max_articles, 
                show_keyword_suggestions=True  # AI expansion handled inside fetch function
            )
            
            if articles:
                self.logger.info(f"📰 Found {len(articles)} articles for campaign '{campaign['name']}'")
                
                # Process integrations
                integrations = campaign.get('integrations', [])
                success_count = 0
                
                for integration in integrations:
                    if integration == 'google_sheets':
                        # Google Sheets integration
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
                                    self.logger.info(f"✅ Saved articles to Google Sheets")
                                else:
                                    self.logger.error(f"❌ Failed to save articles to Google Sheets")
                            else:
                                self.logger.warning(f"⚠️ Campaign has Google Sheets integration but no spreadsheet_id")
                        else:
                            self.logger.warning("⚠️ Google Sheets not connected - skipping integration")
                    
                    elif integration == 'airtable':
                        # Airtable integration
                        success = self.integration_manager.send_to_airtable(articles, campaign['name'])
                        if success:
                            success_count += 1
                            self.logger.info(f"✅ Sent articles to Airtable")
                        else:
                            self.logger.error(f"❌ Failed to send articles to Airtable")
                
                # Update campaign statistics
                self.campaign_manager.update_campaign_stats(
                    campaign['id'], 
                    len(articles), 
                    success_count
                )
                
                self.logger.info(f"✅ Campaign '{campaign['name']}' completed: {len(articles)} articles, {success_count}/{len(integrations)} integrations successful")
                
            else:
                self.logger.info(f"📭 No articles found for campaign '{campaign['name']}'")
                
        except Exception as e:
            self.logger.error(f"❌ Error running campaign '{campaign['name']}': {e}")
            import traceback
            traceback.print_exc()

# Global scheduler instance
campaign_scheduler = CampaignScheduler()

# External function to run a campaign
def run_campaign(campaign_id: str):
    """Run a specific campaign by ID"""
    try:
        campaign_manager = CampaignManager()
        campaign = campaign_manager.get_campaign(campaign_id)
        
        if campaign:
            campaign_scheduler.run_campaign(campaign)
            return True
        else:
            print(f"Campaign {campaign_id} not found")
            return False
            
    except Exception as e:
        print(f"Error running campaign {campaign_id}: {e}")
        return False
